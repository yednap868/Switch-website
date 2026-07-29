"""
Webhook endpoints for ElevenLabs and extraction tools.

Inbound call flow (via vobiz_bridge.py):
  Worker calls Vobiz number (+91 8037565248)
  → Vobiz POSTs to /vobiz/answer → returns XML with <Stream> WebSocket URL
  → Vobiz opens WebSocket to /vobiz/ws
  → Our server opens WebSocket to ElevenLabs (wss://api.elevenlabs.io/v1/convai/conversation)
  → Audio bridged: Vobiz mulaw 8kHz ↔ server ↔ ElevenLabs PCM 16kHz
  → Post-call webhook fires → /elevenlabs/webhook/post-call → processes transcript, sends SMS
"""

import asyncio
import hmac
import json
import os
import re
import threading
import time
import traceback
from hashlib import sha256

from anthropic import Anthropic
from fastapi import APIRouter, BackgroundTasks, Request
from twilio.rest import Client as TwilioClient

from models.switch_models import LiveConnectStatus

from api.vobiz_routes import _inbound_call_uuids
from services.live_connect_service import call_businesses, call_candidates, claim_winner, create_inbound_business_session, create_inbound_session, end_session, get_session, handle_business_unreachable, update_session_status
from services.vobiz_service import vobiz_service
from services.post_call_workflow import PostCallWorkflow
from services.profile_audio_service import profile_audio_service
from services.voice_extraction_service import voice_extraction_service
from utils.db import fs, get_extraction_data, get_user_profile
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


_router = APIRouter(tags=["Tools"])

# In-memory cache: maps call_id/conversation_id → caller phone number
# Populated by initiation webhook, consumed by post-call webhook
_call_phone_cache: dict = {}

# Maps ElevenLabs conversation_id → employer outbound call_id
# Shared with employer_outbound_bridge (which writes) and post-call webhook (which reads)
_employer_conversation_cache: dict[str, str] = {}


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


def _compute_profile_completeness(profile: dict) -> int:
    """Compute a 0-100 completeness score for a candidate profile."""
    fields_and_weights = [
        ("name", 15),
        ("city", 15),
        ("desired_role", 15),
        ("experience_years", 10),
        ("experience_level", 5),
        ("salary_min", 10),
        ("previous_roles", 10),
        ("languages", 5),
        ("education", 5),
        ("availability", 5),
        ("employment_status", 5),
    ]
    score = 0
    for field, weight in fields_and_weights:
        val = profile.get(field)
        if val and val != 0 and val != []:
            score += weight
    return min(score, 100)


def _merge_profiles(old: dict, new: dict) -> dict:
    """
    Merge a new profile extraction into an existing profile.

    Rules:
    - Non-empty scalar fields in new override old
    - List fields are unioned (deduplicated, case-insensitive)
    - Zero/empty values in new do NOT overwrite existing values
    - profile_completeness is recomputed after merge
    """
    list_fields = {"previous_roles", "previous_employers", "desired_roles", "preferred_areas", "languages"}
    int_fields = {"salary_min", "salary_max"}

    merged = dict(old)

    for key, new_val in new.items():
        if key == "profile_completeness":
            continue
        if key in list_fields:
            old_list = old.get(key, []) or []
            new_list = new_val if isinstance(new_val, list) else []
            if new_list:
                existing_lower = {item.lower() for item in old_list}
                combined = list(old_list)
                for item in new_list:
                    if item and item.lower() not in existing_lower:
                        combined.append(item)
                        existing_lower.add(item.lower())
                merged[key] = combined
        elif key in int_fields:
            if isinstance(new_val, (int, float)) and new_val > 0:
                merged[key] = int(new_val)
        else:
            if new_val and isinstance(new_val, str) and new_val.strip():
                merged[key] = new_val.strip()

    merged["profile_completeness"] = _compute_profile_completeness(merged)
    return merged


def _get_stored_candidate_profile(phone: str) -> dict:
    """
    Read the structured profile from caller_memory (Postgres) for a phone number.
    Returns the profile dict or empty dict if not found.
    """
    from models.sql_models import CallerMemory
    from utils.postgres import get_db
    normalized = _normalize_phone(phone)
    try:
        db = get_db()
        try:
            row = db.query(CallerMemory).filter(CallerMemory.phone == normalized).first()
            if row and row.profile:
                return json.loads(row.profile) or {}
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ [STORED_PROFILE] Error reading profile for {normalized}: {e}")
    return {}


async def _save_switch_caller_memory(payload: dict):
    """
    Save caller memory after each call for returning caller awareness.

    Generates a summary via Claude Haiku, extracts mentioned jobs,
    determines outcome, and upserts to switch_caller_memory/{phone}.
    """
    data = payload.get("data", {}) or {}
    conversation_id = data.get("conversation_id") or payload.get("conversation_id") or ""
    call_id = payload.get("call_id") or conversation_id

    # Skip employer outbound calls — they get their own memory via _save_employer_memory
    if conversation_id and conversation_id in _employer_conversation_cache:
        print(f"ℹ️ [CALLER_MEMORY] Skipping — employer outbound call (conv_id={conversation_id})")
        return

    # Get caller phone from cache
    caller_phone = (
        _call_phone_cache.get(call_id, "")
        or _call_phone_cache.get(conversation_id, "")
        or data.get("caller_id", "")
        or data.get("from_number", "")
        or payload.get("caller_id", "")
        or payload.get("conversation_initiation_client_data", {}).get("dynamic_variables", {}).get("caller_phone", "")
    )

    if not caller_phone:
        print("⚠️ [CALLER_MEMORY] No caller phone found — cannot save memory")
        return

    normalized = _normalize_phone(caller_phone)

    # Get transcript
    transcript = (
        data.get("transcript", "")
        or payload.get("transcript", "")
        or payload.get("conversation_transcript", "")
    )
    if not transcript:
        print("⚠️ [CALLER_MEMORY] No transcript found — cannot generate summary")
        return

    # ElevenLabs sometimes sends transcript as a list of turn objects
    if isinstance(transcript, list):
        transcript = " ".join(
            turn.get("text", "") if isinstance(turn, dict) else str(turn)
            for turn in transcript
        )

    print(f"🧠 [CALLER_MEMORY] Generating memory for {normalized}...")

    # Generate summary via Claude Haiku
    summary = ""
    caller_name = ""
    outcome = "unknown"
    known_details = {}
    profile = {}
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            client = Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": (
                        "Analyze this call transcript between Jyoti (recruiter) and a caller. "
                        "Return ONLY valid JSON with these fields:\n"
                        '- "summary": 1-2 sentence summary of the conversation\n'
                        '- "caller_name": caller\'s name if mentioned (empty string if not)\n'
                        '- "outcome": one of "interested", "not_interested", "callback", "completed", "unknown"\n'
                        '- "known_details": dict of facts learned about the caller (e.g. location, experience, current_job, skills)\n'
                        '- "profile": structured candidate profile with these fields (use empty string/list/0 if unknown):\n'
                        '    "name": full name\n'
                        '    "experience_years": e.g. "2 years", "fresher", "6 months"\n'
                        '    "experience_level": one of "Fresher", "1-2 yrs", "3-5 yrs", "5+ yrs", ""\n'
                        '    "previous_roles": list of past job roles e.g. ["waiter", "delivery boy"]\n'
                        '    "previous_employers": list of past employers e.g. ["Haldiram", "Zomato"]\n'
                        '    "desired_role": primary role wanted\n'
                        '    "desired_roles": all mentioned roles as list\n'
                        '    "city": current city\n'
                        '    "preferred_areas": specific localities mentioned as list\n'
                        '    "salary_min": monthly minimum salary as integer (0 if unknown)\n'
                        '    "salary_max": monthly maximum salary as integer (0 if unknown)\n'
                        '    "languages": languages spoken as list e.g. ["Hindi", "English"]\n'
                        '    "availability": one of "immediate", "1 week", "notice period", ""\n'
                        '    "employment_status": one of "employed", "unemployed", ""\n'
                        '    "education": e.g. "10th pass", "12th pass", "graduate", ""\n'
                        f"\nTranscript:\n{transcript[:3000]}"
                    ),
                }],
            )
            raw = resp.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            summary = parsed.get("summary", "")
            caller_name = parsed.get("caller_name", "")
            outcome = parsed.get("outcome", "unknown")
            known_details = parsed.get("known_details", {})
            profile = parsed.get("profile", {})
    except Exception as e:
        print(f"⚠️ [CALLER_MEMORY] Claude summary failed: {e}")
        summary = transcript[:200] + "..." if len(transcript) > 200 else transcript

    # Match mentioned PG jobs from transcript
    mentioned_jobs = []
    try:
        from services.pg_jobs_service import get_all_pg_jobs
        transcript_lower = transcript.lower()
        for job in get_all_pg_jobs():
            if job["pg_name"].lower() in transcript_lower:
                roles = " + ".join(job["roles"])
                label = f"{job['pg_name']} - {roles}"
                if label not in mentioned_jobs:
                    mentioned_jobs.append(label)
    except Exception as e:
        print(f"⚠️ [CALLER_MEMORY] Job matching failed: {e}")

    # Upsert to caller_memory Postgres table
    from models.sql_models import CallerMemory
    from utils.postgres import get_db
    now = time.time()

    db = get_db()
    try:
        existing = db.query(CallerMemory).filter(CallerMemory.phone == normalized).first()
        if existing:
            total_calls = existing.total_calls + 1
            # Merge known_details
            old_known = json.loads(existing.known_details) if existing.known_details else {}
            old_known.update({k: v for k, v in known_details.items() if v})
            known_details = old_known
            if not caller_name:
                caller_name = existing.name or ""
            first_call_at = existing.first_call_at or now
            # Merge profile
            old_profile = json.loads(existing.profile) if existing.profile else {}
            if profile:
                profile = _merge_profiles(old_profile, profile)
            elif old_profile:
                profile = old_profile

            existing.name = caller_name
            existing.total_calls = total_calls
            existing.last_call_at = now
            existing.last_conversation_summary = summary
            existing.known_details = json.dumps(known_details)
            existing.profile = json.dumps(profile)
            existing.last_jobs_pitched = json.dumps(mentioned_jobs)
            existing.last_outcome = outcome
            existing.last_conversation_id = conversation_id or call_id
            existing.updated_at = now
        else:
            total_calls = 1
            first_call_at = now
            if profile:
                profile["profile_completeness"] = _compute_profile_completeness(profile)
            row = CallerMemory(
                phone=normalized,
                name=caller_name,
                caller_type="candidate",
                total_calls=1,
                first_call_at=now,
                last_call_at=now,
                last_conversation_summary=summary,
                known_details=json.dumps(known_details),
                profile=json.dumps(profile),
                last_jobs_pitched=json.dumps(mentioned_jobs),
                last_outcome=outcome,
                last_conversation_id=conversation_id or call_id,
                updated_at=now,
            )
            db.add(row)

        db.commit()
    except Exception as e:
        print(f"⚠️ [CALLER_MEMORY] Postgres upsert failed: {e}")
        db.rollback()
    finally:
        db.close()

    completeness = profile.get("profile_completeness", 0) if profile else 0
    print(f"✅ [CALLER_MEMORY] Saved memory for {normalized} (call #{total_calls}, outcome={outcome}, profile_completeness={completeness}%)")


def _save_employer_memory(payload: dict):
    """
    Save employer memory after an employer outbound call.

    Generates a summary via Claude Haiku and upserts to employer_memory/{phone}.
    Tracks call history, interview slots, positions, and contact info across calls.
    """
    data = payload.get("data", {}) or {}
    conversation_id = data.get("conversation_id") or payload.get("conversation_id") or ""

    if not conversation_id:
        return

    call_id = _employer_conversation_cache.get(conversation_id)
    if not call_id:
        return

    employer_phone = _call_phone_cache.get(conversation_id) or _call_phone_cache.get(call_id, "")
    if not employer_phone:
        print("⚠️ [EMP_MEMORY] No employer phone found — cannot save memory")
        return

    normalized = _normalize_phone(employer_phone)

    # Get transcript
    transcript = (
        data.get("transcript", "")
        or payload.get("transcript", "")
        or payload.get("conversation_transcript", "")
    )
    if not transcript:
        print("⚠️ [EMP_MEMORY] No transcript found — cannot generate memory")
        return

    if isinstance(transcript, list):
        transcript = " ".join(
            turn.get("text", "") if isinstance(turn, dict) else str(turn)
            for turn in transcript
        )

    # Get call record for job context
    try:
        call_doc = fs.collection("employer_outbound_calls").document(call_id).get()
        call_data = call_doc.to_dict() if call_doc.exists else {}
    except Exception:
        call_data = {}

    company = call_data.get("company", "")
    job_title = call_data.get("job_title", "")
    city = call_data.get("city", "")

    # Wait briefly for extraction to complete (it runs in parallel)
    time.sleep(3)

    # Read extraction results
    try:
        call_doc = fs.collection("employer_outbound_calls").document(call_id).get()
        if call_doc.exists:
            call_data = call_doc.to_dict()
    except Exception:
        pass

    call_outcome = call_data.get("call_outcome", "unknown")
    extraction_summary = call_data.get("extraction_summary", "")
    extraction_data = call_data.get("extraction_data", {})
    slot_id = call_data.get("slot_id", "")

    print(f"🧠 [EMP_MEMORY] Saving employer memory for {normalized} (call_id={call_id})")

    now = time.time()
    doc_ref = fs.collection("employer_memory").document(normalized)

    call_entry = {
        "call_id": call_id,
        "date": now,
        "outcome": call_outcome,
        "summary": extraction_summary,
        "job_title": extraction_data.get("updated_title") or job_title,
        "slot_created": bool(slot_id),
    }

    try:
        existing = doc_ref.get()
    except Exception:
        existing = None

    if existing and existing.exists:
        existing_data = existing.to_dict() or {}
        total_calls = existing_data.get("total_calls", 0) + 1
        first_call_at = existing_data.get("first_call_at", now)
        call_history = existing_data.get("call_history", [])
        call_history.append(call_entry)
        call_history = call_history[-20:]
        interview_slots = existing_data.get("interview_slots_created", [])
        if slot_id and slot_id not in interview_slots:
            interview_slots.append(slot_id)
        positions = set(existing_data.get("positions_hiring", []))
        if job_title:
            positions.add(job_title)
        if extraction_data.get("updated_title"):
            positions.add(extraction_data["updated_title"])
        contact_person = extraction_data.get("contact_person") or existing_data.get("contact_person", "")
        notes = existing_data.get("notes", "")
    else:
        total_calls = 1
        first_call_at = now
        call_history = [call_entry]
        interview_slots = [slot_id] if slot_id else []
        positions = {job_title} if job_title else set()
        if extraction_data.get("updated_title"):
            positions.add(extraction_data["updated_title"])
        contact_person = extraction_data.get("contact_person", "")
        notes = ""

    if extraction_data.get("requirements"):
        req = extraction_data["requirements"]
        if notes and req not in notes:
            notes = f"{notes}; {req}"
        elif not notes:
            notes = req

    memory_data = {
        "phone": normalized,
        "company": company,
        "total_calls": total_calls,
        "first_call_at": first_call_at,
        "last_call_at": now,
        "last_call_summary": extraction_summary,
        "last_call_outcome": call_outcome,
        "call_history": call_history,
        "interview_slots_created": interview_slots,
        "positions_hiring": list(positions),
        "city": city,
        "contact_person": contact_person,
        "notes": notes,
        "updated_at": now,
    }

    doc_ref.set(memory_data, merge=True)
    print(f"✅ [EMP_MEMORY] Saved employer memory for {normalized} (call #{total_calls}, outcome={call_outcome})")


async def _send_profile_link_to_candidate(uid: str):
    """
    Send profile link to candidate/job seeker after first call via WhatsApp template.
    
    Uses phone number from resume if available, otherwise falls back to existing phone.
    Sends via WhatsApp template message with candidate name and profile URL.
    """
    try:
        print(f"📤 [PROFILE_LINK] Checking if profile link should be sent to {uid}")
        
        # Get user profile to check user type
        user_profile = get_user_profile(uid)
        if not user_profile:
            print(f"⚠️ [PROFILE_LINK] No user profile found for {uid}")
            return
        
        user_type = user_profile.get("profile", {}).get("user_type", "general")
        if user_type not in {"job_seeker", "candidate"}:
            print(f"ℹ️ [PROFILE_LINK] Skipping - user_type is '{user_type}' (not job_seeker/candidate)")
            return
        
        # Check if this is the first call
        # Note: save_call_memory (step 3) runs before this, so call count is already incremented
        # If total_calls == 1, this is the first call that just completed
        call_summary_doc = fs.collection("user_call_summaries").document(uid).get()
        is_first_call = False
        total_calls = 0
        if call_summary_doc.exists:
            call_summary = call_summary_doc.to_dict() or {}
            total_calls = call_summary.get("total_calls", 0)
            # If total_calls == 1, this is the first call that just completed
            is_first_call = total_calls == 1
        else:
            # No call summary means this is likely the first call
            is_first_call = True
        
        print(f"🔍 [PROFILE_LINK] Call count check: total_calls={total_calls}, is_first_call={is_first_call}")
        
        if not is_first_call:
            print(f"ℹ️ [PROFILE_LINK] Not first call, skipping")
            return
        
        # Check idempotency
        status_doc = fs.collection("post_call_profile_links").document(uid).get()
        if status_doc.exists:
            print(f"ℹ️ [PROFILE_LINK] Already sent profile link to {uid}")
            return
        
        # Get profile document for slug and WhatsApp ID
        profile_doc = fs.collection("user_profiles").document(uid).get()
        if not profile_doc.exists:
            print(f"⚠️ [PROFILE_LINK] No user_profiles document for {uid}, attempting to create...")
            # Try to create profile if it doesn't exist
            from services.voice_extraction_service import voice_extraction_service
            extraction_data = get_extraction_data(uid) or {}
            if extraction_data:
                try:
                    voice_extraction_service._sync_job_seeker_profile(uid, extraction_data)
                    print(f"✅ [PROFILE_LINK] Created profile for {uid}")
                    # Re-fetch the profile
                    profile_doc = fs.collection("user_profiles").document(uid).get()
                except Exception as e:
                    print(f"❌ [PROFILE_LINK] Failed to create profile: {e}")
                    import traceback
                    traceback.print_exc()
                    return
            else:
                print(f"⚠️ [PROFILE_LINK] No extraction data available to create profile")
                return
        else:
            # Profile exists, but ensure it has all required fields (especially slug and linkedin_url)
            profile_data = profile_doc.to_dict() or {}
            needs_update = False
            update_data = {}
            
            # Ensure slug exists
            if not profile_data.get("slug"):
                print(f"⚠️ [PROFILE_LINK] Profile missing slug, will regenerate...")
                from services.voice_extraction_service import voice_extraction_service
                extraction_data = get_extraction_data(uid) or {}
                if extraction_data:
                    try:
                        voice_extraction_service._sync_job_seeker_profile(uid, extraction_data)
                        print(f"✅ [PROFILE_LINK] Regenerated profile with slug")
                        profile_doc = fs.collection("user_profiles").document(uid).get()
                        profile_data = profile_doc.to_dict() or {}
                    except Exception as e:
                        print(f"⚠️ [PROFILE_LINK] Failed to regenerate profile: {e}")
            
            # Ensure linkedin_url is synced from user profile
            user_profile = get_user_profile(uid) or {}
            user_linkedin = user_profile.get("linkedin_url", "")
            if user_linkedin and not profile_data.get("linkedin_url"):
                update_data["linkedin_url"] = user_linkedin
                needs_update = True
            
            if needs_update:
                fs.collection("user_profiles").document(uid).update(update_data)
                print(f"✅ [PROFILE_LINK] Updated profile with missing fields")
                profile_doc = fs.collection("user_profiles").document(uid).get()
                profile_data = profile_doc.to_dict() or {}
        
        profile_data = profile_doc.to_dict() or {}
        slug = (
            profile_data.get("slug")
            or profile_data.get("public_slug")
            or profile_data.get("username")
            or uid
        )
        profile_url = f"https://profiles.vance.so/{slug}"
        
        # Extract phone number from resume if available
        extraction_data = profile_data.get("extraction_data", {})
        resume_numbers = extraction_data.get("resume_extracted_numbers", {})
        resume_phone = resume_numbers.get("phone_number") if isinstance(resume_numbers, dict) else None
        
        # Format phone number: if 10 digits, add 91 prefix
        if resume_phone:
            # Clean phone number
            clean_phone = re.sub(r'[^\d]', '', str(resume_phone))
            if len(clean_phone) == 10:
                resume_phone = '91' + clean_phone
            elif len(clean_phone) == 12 and clean_phone.startswith('91'):
                resume_phone = clean_phone
            else:
                resume_phone = clean_phone
        
        # Candidate's WhatsApp id / phone – prioritize resume phone
        wa_id = (
            resume_phone  # Use resume phone first
            or profile_data.get("whatsapp")
            or profile_data.get("phone")
            or profile_data.get("phone_number")
            or extraction_data.get("phone_number")
            or profile_data.get("whatsapp_number")
            or uid  # fallback
        )
        
        if not wa_id:
            print(f"⚠️ [PROFILE_LINK] No WhatsApp ID found for {uid}")
            return
        
        # Log which phone source was used
        if resume_phone:
            print(f"📱 [PROFILE_LINK] Using phone from resume: {wa_id}")
        else:
            print(f"📱 [PROFILE_LINK] Using phone from profile: {wa_id}")
        
        # Get candidate name for template
        candidate_name = (
            profile_data.get("name")
            or extraction_data.get("name")
            or user_profile.get("name", "")
            or "there"
        )
        
        # Use WhatsApp template message
        # Template name: "profile_ready" (registered in WhatsApp Business Manager)
        # Template format: "Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you."
        # Parameters: [candidate_name, profile_url]
        template_name = "profile_ready"
        sender = WhatsAppSender()
        use_template = False
        
        try:
            payload = MsgComponents.template_scaffold(
                to=wa_id,
                template_name=template_name,
                language_code="en",
                body_parameters=[candidate_name, profile_url],
            )
            result = sender.send(data=payload)
            use_template = True
            print(f"✅ [PROFILE_LINK] Sent via template '{template_name}'")
        except Exception as template_error:
            # Fallback to text if template fails
            print(f"⚠️ [PROFILE_LINK] Template '{template_name}' failed, falling back to text: {template_error}")
            text = (
                f"Hey {candidate_name}, it's Vance. I've just created your profile from our call.\n\n"
                f"{profile_url}\n\n"
                "This is what I'll share with founders when I introduce you."
            )
            result = sender.send(data=MsgComponents.text_scaffold(to=wa_id, text=text))
            use_template = False
        
        # Store with tracking
        link_data = {
            "sent_at": time.time(),
            "profile_url": profile_url,
            "wa_id": wa_id,
            "is_first_call": True,
            "used_template": use_template,
            "phone_source": "resume" if resume_phone else "profile",
        }
        
        if isinstance(result, dict) and result.get("status") == "success":
            message_id = result.get("message_id")
            if message_id:
                link_data["message_id"] = message_id
                link_data["delivery_status"] = "sent"
                print(f"📱 [PROFILE_LINK] Message ID: {message_id}")
            link_data["delivery_status"] = "sent"
        else:
            error = result.get("error") if isinstance(result, dict) else "Unknown error"
            link_data["delivery_status"] = "failed"
            link_data["error"] = error
            print(f"❌ [PROFILE_LINK] Failed to send: {error}")
        
        fs.collection("post_call_profile_links").document(uid).set(link_data)
        print(f"✅ [PROFILE_LINK] Profile link sent to {uid} at {wa_id} (first call)")
        
    except Exception as e:
        print(f"⚠️ [PROFILE_LINK] Error sending profile link: {e}")
        import traceback
        traceback.print_exc()


async def _try_send_interview_sms_from_transcript(payload: dict):
    """
    After a call ends, check if the candidate confirmed interest in a job.
    If yes, send interview details via SMS using the caller's phone number.

    Gets phone number from:
    1. _call_phone_cache (stored during initiation webhook)
    2. payload metadata fields
    3. conversation_initiation_client_data.dynamic_variables.caller_phone
    """
    data = payload.get("data", {}) or {}
    conversation_id = data.get("conversation_id") or payload.get("conversation_id") or ""
    call_id = payload.get("call_id") or conversation_id

    # 1. Get caller phone — try all sources
    caller_phone = (
        _call_phone_cache.pop(call_id, "")
        or _call_phone_cache.pop(conversation_id, "")
        or data.get("caller_id", "")
        or data.get("from_number", "")
        or payload.get("caller_id", "")
        or payload.get("conversation_initiation_client_data", {}).get("dynamic_variables", {}).get("caller_phone", "")
    )

    print(f"📱 [INTERVIEW_SMS] Call ended. call_id={call_id}, caller_phone={caller_phone}")

    if not caller_phone:
        print("⚠️ [INTERVIEW_SMS] No caller phone found — cannot send SMS")
        return

    # 2. Get transcript
    transcript = (
        data.get("transcript", "")
        or payload.get("transcript", "")
        or payload.get("conversation_transcript", "")
    )
    if not transcript:
        print("⚠️ [INTERVIEW_SMS] No transcript found — cannot check for confirmation")
        return

    # ElevenLabs sometimes sends transcript as a list of turn objects
    if isinstance(transcript, list):
        transcript = " ".join(
            turn.get("text", "") if isinstance(turn, dict) else str(turn)
            for turn in transcript
        )

    transcript_lower = transcript.lower()

    # 3. Check if interview was confirmed — look for business names + confirmation signals
    confirmation_words = ["haan", "yes", "interested", "theek", "okay", "badiya", "interview", "bhej do", "bhej diye"]
    confirmed_biz_name = None
    confirmed_role_name = None
    confirmed_address = None
    confirmed_timing = None

    # 3a. Check switch_jobs collection first (real jobs)
    switch_jobs_query = fs.collection("switch_jobs").where("status", "==", "active").stream()
    for sj_doc in switch_jobs_query:
        sj = sj_doc.to_dict()
        biz_name = (sj.get("business_name") or "").lower()
        position = (sj.get("position") or "").lower()
        if biz_name and biz_name in transcript_lower and position and position in transcript_lower:
            if any(w in transcript_lower for w in confirmation_words):
                confirmed_biz_name = sj.get("business_name", "")
                confirmed_role_name = sj.get("position", "")
                confirmed_address = sj.get("google_maps_url") or sj.get("location", "")
                confirmed_timing = "Kal shaam 4 baje"
                break

    # 3b. Fallback to businesses + jobs collections
    if not confirmed_biz_name:
        businesses_query = fs.collection("businesses").stream()
        for biz_doc in businesses_query:
            biz_data = biz_doc.to_dict()
            biz_name = (biz_data.get("name") or "").lower()
            if not biz_name or biz_name not in transcript_lower:
                continue
            jobs_query = fs.collection("jobs").where("status", "==", "OPEN").where("business_id", "==", biz_doc.id).stream()
            for job_doc in jobs_query:
                job_data = job_doc.to_dict()
                role = (job_data.get("role") or "").lower()
                if role in transcript_lower:
                    if any(w in transcript_lower for w in confirmation_words):
                        confirmed_biz_name = biz_data.get("name", "")
                        confirmed_role_name = job_data.get("role", "")
                        confirmed_address = job_data.get("interview_address") or biz_data.get("address", "")
                        confirmed_timing = job_data.get("interview_timing") or "Kal shaam 4 se 6 baje ke beech"
                        break
            if confirmed_biz_name:
                break

    if not confirmed_biz_name or not confirmed_role_name:
        print(f"📱 [INTERVIEW_SMS] No confirmed interview found in transcript")
        return

    print(f"📱 [INTERVIEW_SMS] Interview confirmed: {confirmed_role_name} at {confirmed_biz_name} for {caller_phone}")

    # 4. Send SMS
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not twilio_account_sid or not twilio_auth_token or not twilio_phone_number:
        print("❌ [INTERVIEW_SMS] Twilio not configured")
        return

    phone = caller_phone
    if not phone.startswith("+"):
        phone = "+91" + phone if not phone.startswith("91") else "+" + phone

    interview_address = confirmed_address
    interview_timing = confirmed_timing

    sms_body = (
        f"Switch - Interview Details\n\n"
        f"{confirmed_biz_name}\n"
        f"{interview_address}\n"
        f"Samay: {interview_timing}\n\n"
        f"Pahunch kr inhe call krna: +91 8368828660\n"
        f"Saaf suthra aana, time pe pahunchna. All the best! - Jyoti, Switch\n\n"
        f"---\n\n"
        f"Switch - इंटरव्यू जानकारी\n\n"
        f"{confirmed_biz_name}\n"
        f"{interview_address}\n"
        f"समय: {interview_timing}\n\n"
        f"पहुँच कर इन्हें कॉल करना: +91 8368828660\n"
        f"साफ़ सुथरा आना, टाइम पे पहुँचना। All the best! - ज्योति, Switch"
    )

    try:
        client = TwilioClient(twilio_account_sid, twilio_auth_token)
        message = client.messages.create(body=sms_body, from_=twilio_phone_number, to=phone)
        print(f"✅ [INTERVIEW_SMS] SMS sent to {phone} — SID: {message.sid}")
    except Exception as e:
        print(f"❌ [INTERVIEW_SMS] Failed to send SMS: {e}")
        traceback.print_exc()


async def _extract_employer_interview_slot(payload: dict):
    """
    After an employer outbound call ends, extract interview slot data from transcript.
    Only processes calls that have a conversation_id in _employer_conversation_cache.
    """
    data = payload.get("data", {}) or {}
    conversation_id = data.get("conversation_id") or payload.get("conversation_id") or ""

    if not conversation_id:
        return

    call_id = _employer_conversation_cache.get(conversation_id)
    if not call_id:
        return

    print(f"📋 [EMP_SLOT] Extracting interview slot for call_id={call_id} conversation_id={conversation_id}")

    # Get job context from Firestore
    try:
        call_doc = fs.collection("employer_outbound_calls").document(call_id).get()
        if not call_doc.exists:
            print(f"⚠️ [EMP_SLOT] No call record found for {call_id}")
            return
        call_data = call_doc.to_dict()
    except Exception as e:
        print(f"⚠️ [EMP_SLOT] Error reading call record: {e}")
        return

    # Get transcript
    transcript = (
        data.get("transcript", "")
        or payload.get("transcript", "")
        or payload.get("conversation_transcript", "")
    )
    if not transcript:
        print("⚠️ [EMP_SLOT] No transcript found")
        return

    if isinstance(transcript, list):
        transcript = " ".join(
            turn.get("text", "") if isinstance(turn, dict) else str(turn)
            for turn in transcript
        )

    # Save transcript to call record
    try:
        fs.collection("employer_outbound_calls").document(call_id).update({
            "transcript": transcript[:10000],
        })
        print(f"✅ [EMP_SLOT] Saved transcript to employer_outbound_calls/{call_id}")
    except Exception as e:
        print(f"⚠️ [EMP_SLOT] Error saving transcript: {e}")

    # Extract slot data via Claude Haiku
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("⚠️ [EMP_SLOT] No ANTHROPIC_API_KEY")
            return

        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": (
                    "Analyze this call between Jyoti (recruiter from Switch) and an employer/HR.\n"
                    "Return ONLY valid JSON with these fields:\n"
                    '- "employer_agreed": bool (did they agree to receive candidates for interview?)\n'
                    '- "interview_date": str (e.g. "kal", "17 Feb", "Monday", "")\n'
                    '- "interview_time": str (e.g. "11 baje", "4-6 PM", "subah", "")\n'
                    '- "interview_address": str (full address mentioned, or "")\n'
                    '- "contact_person": str (HR/manager name if mentioned, or "")\n'
                    '- "contact_phone": str (if they gave a different phone to call, or "")\n'
                    '- "candidates_wanted": int (how many candidates they want, 0 if not mentioned)\n'
                    '- "requirements": str (e.g. "Aadhaar card laao", "experience chahiye", "")\n'
                    '- "updated_salary_min": int (if they mentioned a different min salary, else 0)\n'
                    '- "updated_salary_max": int (if they mentioned a different max salary, else 0)\n'
                    '- "updated_openings": int (if they mentioned current openings count, else 0)\n'
                    '- "updated_title": str (if the actual role name differs from what Jyoti said, else "")\n'
                    '- "call_back_later": bool (did they say to call back at another time?)\n'
                    '- "call_back_when": str (when to call back, e.g. "kal subah", "Monday", "")\n'
                    '- "not_hiring": bool (did they say they are not hiring anymore?)\n'
                    '- "wrong_number": bool (was this a wrong number or unrelated person?)\n'
                    '- "summary": str (1 sentence call summary in English)\n'
                    f"\nTranscript:\n{transcript[:3000]}"
                ),
            }],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        extracted = json.loads(raw)
    except Exception as e:
        print(f"⚠️ [EMP_SLOT] Claude extraction failed: {e}")
        return

    employer_agreed = extracted.get("employer_agreed", False)
    summary = extracted.get("summary", "")
    not_hiring = extracted.get("not_hiring", False)
    wrong_number = extracted.get("wrong_number", False)
    call_back_later = extracted.get("call_back_later", False)

    print(f"📋 [EMP_SLOT] Extraction: agreed={employer_agreed} not_hiring={not_hiring} wrong_number={wrong_number} callback={call_back_later} summary={summary[:100]}")

    # Determine call outcome
    if employer_agreed:
        call_outcome = "agreed"
    elif not_hiring:
        call_outcome = "not_hiring"
    elif wrong_number:
        call_outcome = "wrong_number"
    elif call_back_later:
        call_outcome = "call_back"
    else:
        call_outcome = "declined"

    # Always update the call record with extraction results
    try:
        fs.collection("employer_outbound_calls").document(call_id).update({
            "slot_extracted": True,
            "employer_agreed": employer_agreed,
            "call_outcome": call_outcome,
            "extraction_summary": summary,
            "extraction_data": extracted,
        })
    except Exception as e:
        print(f"⚠️ [EMP_SLOT] Error updating call record: {e}")

    # Sync extracted data back to the original jobhai_jobs document
    job_id = call_data.get("job_id", "")
    if job_id:
        try:
            job_update = {
                "last_called_at": time.time(),
                "last_call_outcome": call_outcome,
                "last_call_summary": summary,
            }
            if extracted.get("contact_person"):
                job_update["contact_person"] = extracted["contact_person"]
            if extracted.get("contact_phone"):
                job_update["contact_phone"] = extracted["contact_phone"]
            if extracted.get("interview_address"):
                job_update["interview_address"] = extracted["interview_address"]
            if extracted.get("updated_salary_min") and extracted["updated_salary_min"] > 0:
                job_update["salary_min"] = extracted["updated_salary_min"]
            if extracted.get("updated_salary_max") and extracted["updated_salary_max"] > 0:
                job_update["salary_max"] = extracted["updated_salary_max"]
            if extracted.get("updated_openings") and extracted["updated_openings"] > 0:
                job_update["openings"] = extracted["updated_openings"]
            if extracted.get("updated_title"):
                job_update["verified_title"] = extracted["updated_title"]
            if not_hiring:
                job_update["status"] = "not_hiring"
            if wrong_number:
                job_update["phone_status"] = "wrong_number"
            if call_back_later:
                job_update["call_back_when"] = extracted.get("call_back_when", "")
            if employer_agreed:
                job_update["interview_confirmed"] = True
                job_update["interview_date"] = extracted.get("interview_date", "")
                job_update["interview_time"] = extracted.get("interview_time", "")

            fs.collection("jobhai_jobs").document(job_id).update(job_update)
            print(f"✅ [EMP_SLOT] Synced to jobhai_jobs/{job_id}: outcome={call_outcome}")
        except Exception as e:
            print(f"⚠️ [EMP_SLOT] Error syncing to jobhai_jobs: {e}")

    if not employer_agreed:
        print(f"📋 [EMP_SLOT] Employer did not agree — no slot created")
        return

    # Store interview slot
    slot_data = {
        "call_id": call_id,
        "job_id": job_id,
        "employer_phone": call_data.get("employer_phone", ""),
        "company": call_data.get("company", ""),
        "job_title": extracted.get("updated_title") or call_data.get("job_title", ""),
        "job_category": call_data.get("job_category", ""),
        "city": call_data.get("city", ""),
        "salary_max": extracted.get("updated_salary_max") or call_data.get("salary_max", 0),
        "interview_date": extracted.get("interview_date", ""),
        "interview_time": extracted.get("interview_time", ""),
        "interview_address": extracted.get("interview_address", ""),
        "contact_person": extracted.get("contact_person", ""),
        "contact_phone": extracted.get("contact_phone", ""),
        "candidates_wanted": extracted.get("candidates_wanted", 0),
        "requirements": extracted.get("requirements", ""),
        "employer_agreed": True,
        "status": "pending",
        "matched_candidates": [],
        "created_at": time.time(),
    }

    try:
        slot_ref = fs.collection("interview_slots").document(call_id)
        slot_ref.set(slot_data)
        fs.collection("employer_outbound_calls").document(call_id).update({
            "slot_id": call_id,
        })
        print(f"✅ [EMP_SLOT] Interview slot created: {call_id} — {call_data.get('company', '')} {slot_data['job_title']}")
    except Exception as e:
        print(f"❌ [EMP_SLOT] Error saving slot: {e}")


def _extract_and_store_pg_candidate(payload: dict):
    """
    Extract PG candidate data from the call transcript via Claude Haiku,
    store in PostgreSQL pg_candidates table, and send confirmation SMS
    if joining was confirmed.
    """
    from services.fast2sms_service import send_sms
    from models.sql_models import PgCandidate
    from utils.postgres import get_db

    data = payload.get("data", {}) or {}
    conversation_id = data.get("conversation_id") or payload.get("conversation_id") or ""
    call_id = payload.get("call_id") or conversation_id

    # Get caller phone
    caller_phone = (
        _call_phone_cache.get(call_id, "")
        or _call_phone_cache.get(conversation_id, "")
        or data.get("caller_id", "")
        or data.get("from_number", "")
        or payload.get("caller_id", "")
        or payload.get("conversation_initiation_client_data", {}).get("dynamic_variables", {}).get("caller_phone", "")
    )

    if not caller_phone:
        print("⚠️ [PG_EXTRACT] No caller phone — skipping")
        return

    # Get transcript
    transcript = (
        data.get("transcript", "")
        or payload.get("transcript", "")
        or payload.get("conversation_transcript", "")
    )
    if not transcript:
        print("⚠️ [PG_EXTRACT] No transcript — skipping")
        return

    if isinstance(transcript, list):
        transcript = " ".join(
            turn.get("text", "") if isinstance(turn, dict) else str(turn)
            for turn in transcript
        )

    # Normalize phone to 10-digit
    normalized = caller_phone.replace("+", "").replace("-", "").replace(" ", "")
    if normalized.startswith("91") and len(normalized) == 12:
        normalized = normalized[2:]
    full_phone = "91" + normalized if len(normalized) == 10 else normalized

    print(f"🏠 [PG_EXTRACT] Extracting PG candidate data for {full_phone}...")

    # Extract structured data via Claude Haiku
    candidate = {}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            client = Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=[{
                    "role": "user",
                    "content": (
                        "Extract PG job candidate data from this call transcript between Jyoti (recruiter) "
                        "and a job seeker. Return ONLY valid JSON, no explanation:\n"
                        '{\n'
                        '  "name": string or null,\n'
                        '  "city": string or null,\n'
                        '  "current_location": string or null,\n'
                        '  "currently_employed": true/false/null,\n'
                        '  "current_employer": string or null,\n'
                        '  "experience_years": string or null,\n'
                        '  "interested_role": string or null,\n'
                        '  "salary_expectation": string or null,\n'
                        '  "joining_confirmed": true/false,\n'
                        '  "joining_date": "today"/"tomorrow"/"this_week"/null,\n'
                        '  "matched_pg_name": string or null,\n'
                        '  "matched_pg_location": string or null,\n'
                        '  "matched_salary": string or null\n'
                        '}\n\n'
                        f"Transcript:\n{transcript[:3000]}"
                    ),
                }],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            candidate = json.loads(raw)
        except Exception as e:
            print(f"⚠️ [PG_EXTRACT] Claude extraction failed: {e}")

    # Store in PostgreSQL
    sms_sent = False
    try:
        db = get_db()
        try:
            row = PgCandidate(
                phone=full_phone,
                conversation_id=conversation_id or "",
                call_id=call_id or "",
                name=candidate.get("name") or "",
                city=candidate.get("city") or "",
                current_location=candidate.get("current_location") or "",
                currently_employed=candidate.get("currently_employed"),
                current_employer=candidate.get("current_employer") or "",
                experience_years=candidate.get("experience_years") or "",
                interested_role=candidate.get("interested_role") or "",
                salary_expectation=candidate.get("salary_expectation") or "",
                joining_confirmed=bool(candidate.get("joining_confirmed")),
                joining_date=candidate.get("joining_date") or "",
                matched_pg_name=candidate.get("matched_pg_name") or "",
                matched_pg_location=candidate.get("matched_pg_location") or "",
                matched_salary=candidate.get("matched_salary") or "",
                sms_sent=False,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            record_id = row.id
            print(f"✅ [PG_EXTRACT] Stored pg_candidates row #{record_id} for {full_phone}: name={row.name}, confirmed={row.joining_confirmed}")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ [PG_EXTRACT] Postgres write failed: {e}")
        return

    # Send SMS only if joining confirmed
    if not candidate.get("joining_confirmed"):
        print(f"ℹ️ [PG_SMS] Joining not confirmed for {full_phone} — no SMS sent")
        return

    name = candidate.get("name") or "Aap"
    role = candidate.get("interested_role") or "selected role"
    pg_name = candidate.get("matched_pg_name") or "PG"
    pg_location = candidate.get("matched_pg_location") or "location"
    salary = candidate.get("matched_salary") or ""
    joining_date_raw = candidate.get("joining_date") or "jald se jald"

    joining_map = {"today": "aaj", "tomorrow": "kal", "this_week": "is hafte"}
    joining_date = joining_map.get(joining_date_raw, joining_date_raw)

    salary_line = f"Salary: {salary}/month\n" if salary else ""

    candidate_sms = (
        f"Namaste {name}!\n\n"
        f"Switch - Naukri Confirm:\n"
        f"{pg_name}, {pg_location}\n"
        f"Role: {role}\n"
        f"{salary_line}"
        f"Khana + Rehna: FREE\n\n"
        f"Joining: {joining_date}\n\n"
        f"Sawaal? Call: +918037565248\n"
        f"- Jyoti, Switch"
    )

    sms_sent = send_sms(full_phone, candidate_sms)

    # Admin alert SMS
    admin_phone = os.getenv("ADMIN_WHATSAPP_PHONE", "919650098888")
    exp = candidate.get("experience_years") or "?"
    sal_exp = candidate.get("salary_expectation") or "?"
    city = candidate.get("city") or "?"
    employed = "haan" if candidate.get("currently_employed") else "nahi"

    admin_sms = (
        f"PG Joining Confirm!\n"
        f"{name} | +91{full_phone}\n"
        f"City: {city} | Employed: {employed}\n"
        f"Role: {role} | Exp: {exp}\n"
        f"Sal. exp: {sal_exp}\n"
        f"PG: {pg_name}, {pg_location}\n"
        f"Joining: {joining_date}"
    )

    send_sms(admin_phone, admin_sms)

    # Mark sms_sent in DB
    if sms_sent:
        try:
            db = get_db()
            try:
                db.query(PgCandidate).filter(PgCandidate.id == record_id).update({"sms_sent": True})
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ [PG_SMS] Could not update sms_sent flag: {e}")


def _handle_post_call_webhook(payload: dict):
    """
    Handle ElevenLabs post-call webhook using the refactored workflow.
    All heavy work runs in daemon threads to avoid blocking the event loop.
    """
    # Save caller memory in a background thread (Claude API + Postgres — can block 10s+)
    def _save_memory():
        try:
            asyncio.run(_save_switch_caller_memory(payload))
        except Exception as e:
            print(f"⚠️ [CALLER_MEMORY] Error saving caller memory: {e}")

    threading.Thread(target=_save_memory, daemon=True).start()

    # Try to send interview SMS in background thread (Claude + Firestore — blocks event loop)
    def _send_sms():
        try:
            asyncio.run(_try_send_interview_sms_from_transcript(payload))
        except Exception as e:
            print(f"⚠️ [INTERVIEW_SMS] Error in post-call SMS check: {e}")

    threading.Thread(target=_send_sms, daemon=True).start()

    # Extract employer interview slot data in background thread
    def _extract_slot():
        try:
            asyncio.run(_extract_employer_interview_slot(payload))
        except Exception as e:
            print(f"⚠️ [EMP_SLOT] Error in employer slot extraction: {e}")

    threading.Thread(target=_extract_slot, daemon=True).start()

    # Save employer memory in background thread (waits for extraction to finish)
    def _emp_memory():
        try:
            _save_employer_memory(payload)
        except Exception as e:
            print(f"⚠️ [EMP_MEMORY] Error saving employer memory: {e}")

    threading.Thread(target=_emp_memory, daemon=True).start()

    # Extract PG candidate data + send confirmation SMS (background thread)
    def _pg_extract():
        try:
            _extract_and_store_pg_candidate(payload)
        except Exception as e:
            print(f"⚠️ [PG_EXTRACT] Error: {e}")

    threading.Thread(target=_pg_extract, daemon=True).start()

    print(
        f"🚀 [POSTCALL] Background task started with payload keys: {list(payload.keys())}"
    )

    # Run PostCallWorkflow + profile link in a background thread.
    # workflow.run() does sync Claude + Firestore calls that block the event loop.
    def _run_workflow():
        try:
            uid = payload.get("data", {}).get("user_id") or payload.get("user_id")
            if uid == "default":
                dyn = payload.get("conversation_initiation_client_data", {}).get("dynamic_variables", {})
                actual = dyn.get("user_id")
                if actual and actual != "default":
                    uid = actual

            workflow = PostCallWorkflow()
            result = asyncio.run(workflow.run(payload))

            if result.uid and result.uid != "default" and len(str(result.uid)) >= 5:
                workflow_uid = result.uid
                print(f"🔄 [PROFILE_LINK] Workflow completed, sending profile link for {workflow_uid}")
                asyncio.run(_send_profile_link_to_candidate(workflow_uid))

            if result.errors:
                print(f"[POSTCALL] Workflow completed with {len(result.errors)} error(s):")
                for step, error in result.errors:
                    print(f"  ❌ [{step}] {error}")

            if result.step_timings:
                total_time = sum(result.step_timings.values())
                print(f"[POSTCALL] Total time: {total_time:.2f}s")
        except Exception as e:
            print(f"❌ [POSTCALL] Background task failed: {e}")
            traceback.print_exc()

    threading.Thread(target=_run_workflow, daemon=True).start()


def _handle_post_call_audio(payload: dict):
    """
    Handle ElevenLabs post-call audio webhook.
    Runs entirely in a background thread to avoid blocking the event loop.
    """
    def _run_audio():
        try:
            fs.collection("debug_webhooks").document("last_post_call_audio").set(
                {"payload": payload, "created_at": time.time()}
            )
            print("✅ [AUDIO_DEBUG] Stored last_post_call_audio payload for inspection")
        except Exception as e:
            print(f"⚠️ [AUDIO_DEBUG] Failed to store audio debug payload: {e}")

        data = payload.get("data", {}) or {}
        conversation_id = data.get("conversation_id")

        if not conversation_id:
            print("⚠️ [AUDIO] No conversation_id in audio payload")
            return

        try:
            query = (
                fs.collection_group("calls")
                .where("conversation_id", "==", conversation_id)
                .limit(1)
            )
            docs = list(query.stream())

            if not docs:
                print(f"⚠️ [AUDIO] No matching call found for conversation_id={conversation_id}")
                profiles_with_conv = fs.collection("user_profiles").where("audio_conversation_id", "==", conversation_id).limit(1).stream()
                for profile_doc in profiles_with_conv:
                    user_id = profile_doc.id
                    print(f"🔄 [AUDIO] Found user_id={user_id} from profile audio_conversation_id")
                    asyncio.run(profile_audio_service.attach_call_recording_to_profile(
                        user_id=user_id, payload=payload
                    ))
                    return
                return

            call_doc = docs[0]
            user_doc_ref = call_doc.reference.parent.parent
            user_id = user_doc_ref.id if user_doc_ref is not None else None

            if not user_id:
                print(
                    f"⚠️ [AUDIO] Could not resolve user_id for conversation_id={conversation_id}"
                )
                return

            print(
                f"🎧 [AUDIO] Attaching audio for user_id={user_id}, conversation_id={conversation_id}"
            )
            asyncio.run(profile_audio_service.attach_call_recording_to_profile(
                user_id=user_id, payload=payload
            ))
        except Exception as e:
            print(
                f"⚠️ [AUDIO] Failed to attach audio for conversation_id={conversation_id}: {e}"
            )
            traceback.print_exc()

    threading.Thread(target=_run_audio, daemon=True).start()


# =============================================================================
# ElevenLabs Webhooks
# =============================================================================


@_router.post("/elevenlabs/webhook/post-call")
async def elevenlabs_postcall_webhook(
    request: Request, background_tasks: BackgroundTasks
):
    """
    Handle ElevenLabs post-call webhook.
    """
    try:
        payload = await request.body()
        headers = request.headers.get("elevenlabs-signature")

        # For testing: bypass signature validation if no signature provided
        if headers is None:
            payload_dict = json.loads(payload)
            # Route based on event type
            event_type = payload_dict.get("type")
            if event_type == "post_call_audio":
                background_tasks.add_task(_handle_post_call_audio, payload_dict)
            else:
                background_tasks.add_task(_handle_post_call_webhook, payload_dict)
            return {
                "status": "success",
                "message": f"Webhook processed (no signature, type={event_type})",
            }

        # TEMPORARY: Always process webhook regardless of signature validation
        # TODO: Fix signature validation in production
        payload_dict = json.loads(payload)
        event_type = payload_dict.get("type")
        if event_type == "post_call_audio":
            background_tasks.add_task(_handle_post_call_audio, payload_dict)
        else:
            background_tasks.add_task(_handle_post_call_webhook, payload_dict)
        return {
            "status": "success",
            "message": f"Webhook processed (signature bypassed, type={event_type})",
        }

        # Validate signature for production (unreachable for now)
        timestamp = headers.split(",")[0][2:]
        hmac_signature = headers.split(",")[1]

        tolerance = int(time.time()) - 30 * 60
        if int(timestamp) < tolerance:
            return {"status": "error", "message": "Timestamp too old"}

        full_payload_to_sign = f"{timestamp}.{payload.decode('utf-8')}"
        secret = os.getenv("ELEVENLABS_WH_SECRET")

        if not secret:
            return {"status": "error", "message": "Webhook secret not configured"}

        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=full_payload_to_sign.encode("utf-8"),
            digestmod=sha256,
        )
        digest = "v0=" + mac.hexdigest()

        if hmac_signature != digest:
            return {"status": "error", "message": "Invalid signature"}

        payload_dict = json.loads(payload)
        background_tasks.add_task(_handle_post_call_webhook, payload_dict)
        return {"status": "success", "message": "Webhook processed"}

    except Exception as e:
        return {"status": "error", "message": f"Webhook processing error: {e}"}


@_router.get("/elevenlabs/initiation/webhook")
def elevenlabs_initiation_webhook_get(request: Request):
    """
    GET endpoint for ElevenLabs initiation webhook status.
    """
    return {
        "message": "ElevenLabs initiation webhook endpoint",
        "status": "active",
        "method": "POST",
    }


@_router.post("/elevenlabs/initiation/webhook")
async def elevenlabs_initiation_webhook(request: Request):
    """
    Handle ElevenLabs call initiation webhook.
    Fetches open jobs from Firestore and injects them as dynamic variables
    into the agent prompt at call start (zero mid-call latency).
    Also passes caller_phone so the agent can use it with tools.
    """
    try:
        payload = await request.json()
        print(f"📞 [ELEVENLABS] Initiation webhook received: {payload}")

        call_id = payload.get("call_id")
        if call_id:
            print(f"📞 [ELEVENLABS] Call initiated - ID: {call_id}")

        caller_phone = payload.get("caller_id") or payload.get("from_number") or payload.get("from") or ""
        print(f"📞 [ELEVENLABS] Caller phone: {caller_phone}")
        print(f"📞 [ELEVENLABS] Full initiation payload keys: {list(payload.keys())}")

        # Cache caller phone for post-call SMS
        if call_id and caller_phone:
            _call_phone_cache[call_id] = caller_phone
            print(f"📞 [ELEVENLABS] Cached caller phone {caller_phone} for call {call_id}")

        open_jobs_text = _fetch_open_jobs_for_prompt()

        return {
            "dynamic_variables": {
                "open_jobs": open_jobs_text,
                "caller_phone": caller_phone,
            },
        }
    except Exception as e:
        print(f"❌ [ELEVENLABS] Initiation webhook error: {e}")
        return {
            "dynamic_variables": {
                "open_jobs": "No jobs available right now.",
                "caller_phone": "",
            },
        }


def _fetch_open_jobs_for_prompt() -> str:
    """Fetch all open jobs from Firestore (both jobs and switch_jobs) and format as a readable table."""
    try:
        rows = []

        # 1. switch_jobs collection (primary — real jobs)
        switch_jobs_query = fs.collection("switch_jobs").where("status", "==", "active").stream()
        for sj_doc in switch_jobs_query:
            sj = sj_doc.to_dict()
            salary_max = sj.get("salary_max", 0)
            salary_str = f"₹{salary_max:,}" if salary_max else "—"
            rows.append(
                f"| {sj.get('business_name', 'Unknown')} "
                f"| {sj.get('location', '')} "
                f"| {sj.get('position', '')} "
                f"| {salary_str} |"
            )

        # 2. jobs collection (legacy)
        jobs_query = fs.collection("jobs").where("status", "==", "OPEN").stream()
        biz_cache = {}
        for job_doc in jobs_query:
            job_data = job_doc.to_dict()
            biz_id = job_data.get("business_id", "")
            if biz_id not in biz_cache:
                biz_doc = fs.collection("businesses").document(biz_id).get()
                biz_cache[biz_id] = biz_doc.to_dict() if biz_doc.exists else {}
            biz_data = biz_cache[biz_id]
            if not biz_data.get("name"):
                continue
            salary_max = job_data.get("salary_max", 0)
            salary_str = f"₹{salary_max:,}" if salary_max else "—"
            rows.append(
                f"| {biz_data.get('name', 'Unknown')} "
                f"| {job_data.get('location', '')} "
                f"| {job_data.get('role', '')} "
                f"| {salary_str} |"
            )

        parts = []
        if rows:
            header = "| Restaurant | Location | Role | Salary |\n|-----------|----------|------|--------|\n"
            parts.append(header + "\n".join(rows))
            print(f"📋 [ELEVENLABS] Injecting {len(rows)} switch/legacy jobs into prompt")

        jobhai_summary = _fetch_jobhai_jobs_summary()
        if jobhai_summary:
            parts.append(jobhai_summary)
            print(f"📋 [ELEVENLABS] Injecting jobhai jobs summary into prompt")

        return "\n\n".join(parts) if parts else "No open positions right now."

    except Exception as e:
        print(f"❌ [ELEVENLABS] Error fetching open jobs for prompt: {e}")
        return "No open positions right now."


# Cached jobhai summary — built in background thread, never blocks request path
_jobhai_cache: dict[str, object] = {"text": "", "fetched_at": 0}
_JOBHAI_CACHE_TTL = 600  # 10 minutes


def _build_jobhai_summary() -> str:
    """Build jobhai jobs grouped summary from Firestore. Runs in background thread only."""
    grouped: dict[str, dict[str, dict]] = {}
    docs = list(fs.collection("jobhai_jobs").stream())
    if not docs:
        return ""

    for doc in docs:
        job = doc.to_dict()
        city = job.get("city", "Unknown")
        category = job.get("category", "Other")
        company = job.get("company", "")
        location = job.get("location", "")
        salary_max = job.get("salary_max", 0) or 0

        if city not in grouped:
            grouped[city] = {}
        if category not in grouped[city]:
            grouped[city][category] = {"count": 0, "max_salary": 0, "companies": set(), "locations": set()}

        g = grouped[city][category]
        g["count"] += 1
        if salary_max > g["max_salary"]:
            g["max_salary"] = salary_max
        if company:
            g["companies"].add(company)
        if location:
            g["locations"].add(location)

    lines = [f"\n### JobHai Database — {len(docs)} total jobs\n"]
    for city in sorted(grouped.keys()):
        lines.append(f"\n**{city}:**")
        categories = grouped[city]
        for cat in sorted(categories.keys(), key=lambda c: categories[c]["count"], reverse=True):
            info = categories[cat]
            salary_str = f"up to ₹{info['max_salary']:,}/month" if info["max_salary"] else ""
            sample_companies = list(info["companies"])[:5]
            companies_str = ", ".join(sample_companies)
            sample_locations = list(info["locations"])[:3]
            locations_str = ", ".join(sample_locations)
            lines.append(
                f"- {cat}: {info['count']} jobs {salary_str}"
                + (f" — e.g. {companies_str}" if companies_str else "")
                + (f" ({locations_str})" if locations_str else "")
            )

    lines.append("\nWhen candidate tells you their preferred role/category and city, use the start_live_connect tool to search and connect them with matching employers from this database.")
    return "\n".join(lines)


def _warm_jobhai_cache() -> None:
    """Rebuild jobhai cache in a background thread."""
    try:
        result = _build_jobhai_summary()
        _jobhai_cache["text"] = result
        _jobhai_cache["fetched_at"] = time.time()
        print(f"📋 [JOBHAI_CACHE] Refreshed: {len(result)} chars")
    except Exception as e:
        print(f"❌ [JOBHAI_CACHE] Failed to refresh: {e}")


def _fetch_jobhai_jobs_summary() -> str:
    """Return cached jobhai summary. Never blocks — returns stale/empty if cache not ready."""
    now = time.time()
    if _jobhai_cache["text"] and (now - _jobhai_cache["fetched_at"]) < _JOBHAI_CACHE_TTL:
        return _jobhai_cache["text"]
    threading.Thread(target=_warm_jobhai_cache, daemon=True).start()
    return _jobhai_cache["text"]


# Warm cache on module load (background thread — does not block import)
threading.Thread(target=_warm_jobhai_cache, daemon=True).start()


# =============================================================================
# Extraction Tools (called by ElevenLabs voice agent)
# =============================================================================


@_router.post("/tools/log_extraction_data/{user_id}")
async def log_extraction_data_endpoint(user_id: str, data: dict):
    """
    Log extraction data from voice calls.

    Supports three user types: general, job_seeker, job_provider.
    Routes to VoiceExtractionService for processing.
    """
    try:
        print(f"📝 [TOOLS] Logging extraction data for {user_id}")

        if not user_id or user_id == "default" or len(user_id) < 5:
            return {"status": "error", "message": f"Invalid user_id: {user_id}"}

        user_profile = get_user_profile(user_id)
        if not user_profile:
            return {"status": "error", "message": f"No user profile found: {user_id}"}

        user_type = user_profile.get("profile", {}).get("user_type", "general")
        print(f"👤 [TOOLS] User type: {user_type}")

        existing_data = get_extraction_data(user_id)

        return voice_extraction_service.handle_extraction(
            user_id=user_id,
            data=data,
            user_type=user_type,
            existing_data=existing_data,
        )

    except Exception as e:
        print(f"❌ [TOOLS] Error logging extraction data: {e}")
        return {"status": "error", "message": f"Error: {e}"}


@_router.get("/tools/extraction_status/{user_id}")
async def get_extraction_status_endpoint(user_id: str):
    """
    Get extraction completion status for a user.
    """
    try:
        return voice_extraction_service.get_status(user_id)
    except Exception as e:
        print(f"❌ [TOOLS] Error getting extraction status: {e}")
        return {"status": "error", "message": f"Error: {e}"}


@_router.post("/tools/log_arbitrary_data/{user_id}")
async def log_arbitrary_data_endpoint(user_id: str, data: dict):
    """
    Log arbitrary key-value data for a user.
    """
    try:
        print(f"📝 [TOOLS] Logging arbitrary data for {user_id}")

        doc_ref = fs.collection("users").document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            doc_data = doc.to_dict()
            assert doc_data is not None
            existing = doc_data.get("arbitrary", {})
            existing.update(data)
            doc_ref.update({"arbitrary": existing})
        else:
            doc_ref.set({"arbitrary": data})

        return {"status": "success", "message": f"Logged: {list(data.keys())}"}
    except Exception as e:
        print(f"❌ [TOOLS] Error logging arbitrary data: {e}")
        return {"status": "error", "message": f"Error: {e}"}


@_router.post("/tools/get_open_jobs")
@_router.post("/api/webhooks/tools/get_open_jobs")
async def get_open_jobs_endpoint(data: dict = None):
    """
    Return all open jobs from Firestore (both switch_jobs and jobs collections).
    Called by ElevenLabs agent (Jyoti) to know what to pitch to candidates.
    """
    try:
        open_jobs = []

        # 1. switch_jobs collection (primary — real jobs)
        switch_jobs_query = fs.collection("switch_jobs").where("status", "==", "active").stream()
        for sj_doc in switch_jobs_query:
            sj = sj_doc.to_dict()
            salary_max = sj.get("salary_max", 0)
            salary_str = f"₹{salary_max:,}" if salary_max else "negotiable"
            open_jobs.append({
                "restaurant": sj.get("business_name", "Unknown"),
                "location": sj.get("location", ""),
                "role": sj.get("position", ""),
                "salary": salary_str,
            })

        # 2. jobs collection (legacy)
        jobs_query = fs.collection("jobs").where("status", "==", "OPEN").stream()
        biz_cache = {}
        for job_doc in jobs_query:
            job_data = job_doc.to_dict()
            biz_id = job_data.get("business_id", "")
            if biz_id not in biz_cache:
                biz_doc = fs.collection("businesses").document(biz_id).get()
                biz_cache[biz_id] = biz_doc.to_dict() if biz_doc.exists else {}
            biz_data = biz_cache[biz_id]
            if not biz_data.get("name"):
                continue
            salary_max = job_data.get("salary_max", 0)
            salary_str = f"₹{salary_max:,}" if salary_max else "negotiable"
            open_jobs.append({
                "restaurant": biz_data.get("name", "Unknown"),
                "location": job_data.get("location", ""),
                "role": job_data.get("role", ""),
                "salary": salary_str,
            })

        print(f"📋 [TOOLS] Returning {len(open_jobs)} open jobs")
        return {"status": "success", "jobs": open_jobs}

    except Exception as e:
        print(f"❌ [TOOLS] Error fetching open jobs: {e}")
        return {"status": "error", "message": f"Error: {e}", "jobs": []}


@_router.post("/tools/send_interview_details")
@_router.post("/api/webhooks/tools/send_interview_details")
@_router.post("/tools/send_interview_details/{user_id}")
@_router.post("/api/webhooks/tools/send_interview_details/{user_id}")
async def send_interview_details_endpoint(request: Request, user_id: str = ""):
    """
    Send interview details to candidate via SMS.
    Called by ElevenLabs agent (Jyoti) when candidate confirms interest in a job.

    Expected body:
        restaurant_name: str - e.g. "Burma Burma"
        role: str - e.g. "Captain"
        phone_number: str - candidate phone (optional if user_id in URL)
        interview_time: str - e.g. "Kal shaam 4:30 baje" (optional)
    """
    try:
        data = await request.json()
        restaurant_name = data.get("restaurant_name", "").strip()
        role = data.get("role", "").strip()
        phone_number = data.get("phone_number", "").strip() or user_id
        interview_time = data.get("interview_time", "").strip()

        print(f"📨 [TOOLS] send_interview_details called — restaurant: {restaurant_name}, role: {role}, phone: {phone_number}")

        if not restaurant_name or not role:
            return {"status": "error", "message": "restaurant_name and role are required"}

        if not phone_number:
            print("⚠️ [TOOLS] No phone_number provided — SMS skipped, returning success to agent")
            return {"status": "success", "message": f"Interview confirmed for {role} at {restaurant_name}. Details will be shared."}

        twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

        if not twilio_account_sid or not twilio_auth_token or not twilio_phone_number:
            print("❌ [TOOLS] Twilio not configured")
            return {"status": "success", "message": f"Interview confirmed for {role} at {restaurant_name}. SMS service not available."}

        # Format candidate phone to E.164
        candidate_phone = phone_number
        if not candidate_phone.startswith("+"):
            candidate_phone = "+91" + candidate_phone if not candidate_phone.startswith("91") else "+" + candidate_phone

        # Find the matching job in Firestore (check switch_jobs first, then jobs)
        matched_job = None
        matched_business_name = None
        matched_address = None
        matched_timing = None

        # 1. Check switch_jobs collection first
        switch_jobs_query = fs.collection("switch_jobs").where("status", "==", "active").stream()
        for sj_doc in switch_jobs_query:
            sj = sj_doc.to_dict()
            biz_name = (sj.get("business_name") or "").lower()
            job_position = (sj.get("position") or "").lower()
            if restaurant_name.lower() in biz_name or biz_name in restaurant_name.lower():
                if role.lower() in job_position or job_position in role.lower():
                    matched_job = sj
                    matched_business_name = sj.get("business_name", restaurant_name)
                    matched_address = sj.get("google_maps_url") or sj.get("location", "")
                    matched_timing = interview_time or "Kal shaam 4 se 6 baje ke beech"
                    break

        # 2. Fallback to jobs collection
        if not matched_job:
            jobs_query = fs.collection("jobs").where("status", "==", "OPEN").stream()
            for job_doc in jobs_query:
                job_data = job_doc.to_dict()
                biz_doc = fs.collection("businesses").document(job_data.get("business_id", "")).get()
                if not biz_doc.exists:
                    continue
                biz_data = biz_doc.to_dict()
                biz_name = (biz_data.get("name") or "").lower()
                job_role = (job_data.get("role") or "").lower()
                if restaurant_name.lower() in biz_name or biz_name in restaurant_name.lower():
                    if role.lower() in job_role or job_role in role.lower():
                        matched_job = job_data
                        matched_business_name = biz_data.get("name", restaurant_name)
                        matched_address = job_data.get("interview_address") or biz_data.get("address", "")
                        matched_timing = interview_time or job_data.get("interview_timing") or "Kal shaam 4 se 6 baje ke beech"
                        break

        # Build SMS message — Hindi format with contact number
        default_timing = interview_time or "Kal shaam 4 se 6 baje ke beech"
        if matched_job:
            biz_name_display = matched_business_name
            sms_body = (
                f"Switch - Interview Details\n\n"
                f"{biz_name_display}\n"
                f"{matched_address}\n"
                f"Samay: {matched_timing}\n\n"
                f"Pahunch kr inhe call krna: +91 8368828660\n"
                f"Saaf suthra aana, time pe pahunchna. All the best! - Jyoti, Switch\n\n"
                f"---\n\n"
                f"Switch - इंटरव्यू जानकारी\n\n"
                f"{biz_name_display}\n"
                f"{matched_address}\n"
                f"समय: {matched_timing}\n\n"
                f"पहुँच कर इन्हें कॉल करना: +91 8368828660\n"
                f"साफ़ सुथरा आना, टाइम पे पहुँचना। All the best! - ज्योति, Switch"
            )
        else:
            sms_body = (
                f"Switch - Interview Details\n\n"
                f"{restaurant_name}\n"
                f"{restaurant_name}, Cyberhub, DLF Cyber City, Gurgaon\n"
                f"Samay: {default_timing}\n\n"
                f"Pahunch kr inhe call krna: +91 8368828660\n"
                f"Saaf suthra aana, time pe pahunchna. All the best! - Jyoti, Switch\n\n"
                f"---\n\n"
                f"Switch - इंटरव्यू जानकारी\n\n"
                f"{restaurant_name}\n"
                f"{restaurant_name}, Cyberhub, DLF Cyber City, Gurgaon\n"
                f"समय: {default_timing}\n\n"
                f"पहुँच कर इन्हें कॉल करना: +91 8368828660\n"
                f"साफ़ सुथरा आना, टाइम पे पहुँचना। All the best! - ज्योति, Switch"
            )

        # Send SMS via Twilio
        client = TwilioClient(twilio_account_sid, twilio_auth_token)
        message = client.messages.create(
            body=sms_body,
            from_=twilio_phone_number,
            to=candidate_phone
        )
        print(f"✅ [TOOLS] SMS sent to {candidate_phone} — SID: {message.sid}")
        return {"status": "success", "message": f"Interview details SMS sent for {role} at {restaurant_name}"}

    except Exception as e:
        print(f"❌ [TOOLS] Error sending interview details SMS: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}


# =============================================================================
# Inbound Live Connect — transfer inbound callers to live connect bridge
# =============================================================================

# Maps normalized phone → session_id for pending inbound live connect transfers.
# Populated by start_live_connect, consumed by vobiz_bridge finally block.
_inbound_lc_sessions: dict[str, str] = {}


async def _delayed_transfer_to_lc(normalized_phone: str, session_id: str, call_uuid: str, delay: int = 3):
    """End the ElevenLabs bridge after a delay so <Redirect> can transfer to LC."""
    await asyncio.sleep(delay)
    pending = _inbound_lc_sessions.get(normalized_phone, "")
    if not pending or pending == "__transferred__":
        print(f"🔗 [LC_INBOUND] Delayed transfer: already handled for {normalized_phone}")
        return
    # Signal the bridge to stop — this closes the stream, triggering <Redirect>
    # which hits stream-ended endpoint and returns LC candidate stream XML.
    from api.vobiz_bridge import _bridge_stop_events
    stop_event = _bridge_stop_events.get(normalized_phone)
    if stop_event:
        print(f"🔗 [LC_INBOUND] Setting bridge stop event for {normalized_phone} → session {session_id}")
        stop_event.set()
    else:
        print(f"⚠️ [LC_INBOUND] No bridge stop event found for {normalized_phone} — bridge may have already closed")


@_router.post("/tools/start_live_connect")
@_router.post("/api/webhooks/tools/start_live_connect")
async def start_live_connect_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Called by inbound Jyoti agent when candidate wants live connection to an employer.
    Creates an inbound session (no outbound call needed) and kicks off business calling.

    Expected body:
        caller_phone: str - Candidate's phone number
        candidate_name: str - Candidate's name
        candidate_city: str - City for job search
        candidate_category: str - Job category
        candidate_salary_min: int - Minimum salary (optional)
        candidate_summary: str - Brief screening summary (optional)
    """
    try:
        data = await request.json()
        caller_phone = data.get("caller_phone", "").strip()
        candidate_name = data.get("candidate_name", "").strip()
        candidate_city = data.get("candidate_city", "Gurgaon")
        candidate_category = data.get("candidate_category", "")
        candidate_salary_min = data.get("candidate_salary_min", 0)
        candidate_summary = data.get("candidate_summary", "")

        if not caller_phone:
            return {"status": "error", "message": "caller_phone is required"}

        normalized = _normalize_phone(caller_phone)

        # Enrich missing fields from stored candidate profile
        stored_profile = _get_stored_candidate_profile(normalized)
        if stored_profile:
            if not candidate_name:
                candidate_name = stored_profile.get("name", "")
            if not candidate_city or candidate_city == "Gurgaon":
                stored_city = stored_profile.get("city", "")
                if stored_city:
                    candidate_city = stored_city
            if not candidate_category:
                candidate_category = stored_profile.get("desired_role", "")
            if not candidate_salary_min:
                candidate_salary_min = stored_profile.get("salary_min", 0)
            print(f"📞 [LC_INBOUND] Enriched from stored profile: name={candidate_name}, city={candidate_city}, category={candidate_category}, salary_min={candidate_salary_min}")

        print(f"📞 [LC_INBOUND] start_live_connect: phone={caller_phone}, name={candidate_name}, city={candidate_city}, category={candidate_category}")

        # Look up the inbound CallUUID
        call_uuid = _inbound_call_uuids.get(normalized, "")
        if not call_uuid:
            print(f"⚠️ [LC_INBOUND] No inbound CallUUID found for {normalized}")
            return {"status": "error", "message": "No active inbound call found for this phone number"}

        # Check for test business phone override
        test_business_phone = data.get("test_business_phone", "")

        # Build screening data with experience level from stored profile
        candidate_experience_level = stored_profile.get("experience_level", "") if stored_profile else ""

        # Check if start_matching already created a session for this phone
        existing_session_id = _inbound_lc_sessions.get(normalized, "")
        existing_session = get_session(existing_session_id) if existing_session_id else None

        if existing_session:
            # Reuse existing session — start_matching already fired call_businesses
            session_id = existing_session_id
            session = existing_session
            session["candidate_name"] = candidate_name
            session["screening_summary"] = candidate_summary
            print(f"📞 [LC_INBOUND] Reusing session {session_id} from start_matching (calls already in progress)")
        else:
            # No existing session — create new and fire business calls
            session = await create_inbound_session(
                candidate_phone=normalized,
                candidate_name=candidate_name,
                candidate_call_uuid=call_uuid,
                test_business_phone=test_business_phone,
            )
            session_id = session["id"]

            # Store pending transfer so vobiz_bridge finally block can also handle it
            _inbound_lc_sessions[normalized] = session_id

            # Kick off business calling in background
            session["_matching_started"] = True
            screening_data = {
                "candidate_summary": candidate_summary,
                "candidate_city": candidate_city,
                "candidate_category": candidate_category,
                "candidate_salary_min": candidate_salary_min,
                "candidate_experience_level": candidate_experience_level,
                "candidate_name": candidate_name,
            }
            background_tasks.add_task(call_businesses, session_id, screening_data)

        # Schedule delayed transfer (3s to let ElevenLabs say goodbye)
        # This transfers the inbound call to the LC candidate bridge independently of ElevenLabs ending.
        asyncio.create_task(_delayed_transfer_to_lc(normalized, session_id, call_uuid, delay=3))

        print(f"✅ [LC_INBOUND] Session {session_id} ready, delayed transfer scheduled")

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Live connect started. Tell the candidate to hold while we connect them to an employer.",
        }

    except Exception as e:
        print(f"❌ [LC_INBOUND] start_live_connect error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}


# =============================================================================
# Live Connect Tool Endpoints (called by ElevenLabs voice agent)
# =============================================================================


@_router.post("/tools/start_matching")
@_router.post("/api/webhooks/tools/start_matching")
async def start_matching_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Called by ElevenLabs agent early — once role + city known, before full screening.
    Kicks off job search + business calling in the background while AI continues talking.

    Expected body:
        session_id: str - Live connect session ID
        candidate_city: str - City for job search (e.g. "Gurgaon", "Delhi")
        candidate_category: str - Job category (e.g. "Housekeeping", "Warehouse")
        candidate_salary_min: int - Minimum salary expectation (optional)
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        caller_phone = data.get("caller_phone", "").strip()
        candidate_city = data.get("candidate_city", "Gurgaon")
        candidate_category = data.get("candidate_category", "")
        candidate_salary_min = data.get("candidate_salary_min", 0)

        # Enrich missing fields from stored candidate profile
        stored_profile = {}
        if caller_phone:
            stored_profile = _get_stored_candidate_profile(_normalize_phone(caller_phone))
            if stored_profile:
                if not candidate_city or candidate_city == "Gurgaon":
                    stored_city = stored_profile.get("city", "")
                    if stored_city:
                        candidate_city = stored_city
                if not candidate_category:
                    candidate_category = stored_profile.get("desired_role", "")
                if not candidate_salary_min:
                    candidate_salary_min = stored_profile.get("salary_min", 0)
                print(f"📞 [LC_TOOLS] start_matching: enriched from stored profile: city={candidate_city}, category={candidate_category}, salary_min={candidate_salary_min}")

        print(f"📞 [LC_TOOLS] start_matching: session={session_id}, caller_phone={caller_phone}, city={candidate_city}, category={candidate_category}, salary_min={candidate_salary_min}")

        # If no session_id but caller_phone provided, create inbound session early
        if not session_id and caller_phone:
            normalized = _normalize_phone(caller_phone)

            # Check if session already exists for this phone
            existing_session_id = _inbound_lc_sessions.get(normalized, "")
            existing_session = get_session(existing_session_id) if existing_session_id else None

            if existing_session:
                session_id = existing_session_id
                session = existing_session
                print(f"📞 [LC_TOOLS] start_matching: reusing existing session {session_id} for {normalized}")
            else:
                call_uuid = _inbound_call_uuids.get(normalized, "")
                session = await create_inbound_session(
                    candidate_phone=normalized,
                    candidate_name=data.get("candidate_name", ""),
                    candidate_call_uuid=call_uuid,
                    test_business_phone=data.get("test_business_phone", ""),
                )
                session_id = session["id"]
                _inbound_lc_sessions[normalized] = session_id
                print(f"📞 [LC_TOOLS] start_matching: created inbound session {session_id} for {normalized}")
        elif not session_id:
            return {"status": "error", "message": "session_id or caller_phone is required"}
        else:
            session = get_session(session_id)
            if not session:
                return {"status": "error", "message": f"Session {session_id} not found"}

        if session.get("_matching_started"):
            print(f"📞 [LC_TOOLS] start_matching: already started for {session_id}, skipping")
            return {"status": "success", "message": "Matching already in progress.", "session_id": session_id}

        session["_matching_started"] = True

        candidate_experience_level = stored_profile.get("experience_level", "") if stored_profile else ""
        screening_data = {
            "candidate_summary": "",
            "candidate_city": candidate_city,
            "candidate_category": candidate_category,
            "candidate_salary_min": candidate_salary_min,
            "candidate_experience_level": candidate_experience_level,
        }

        background_tasks.add_task(call_businesses, session_id, screening_data)

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Matching started! Keep chatting with the candidate while we search.",
        }

    except Exception as e:
        print(f"❌ [LC_TOOLS] start_matching error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}


@_router.post("/tools/connect_to_business")
@_router.post("/api/webhooks/tools/connect_to_business")
async def connect_to_business_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Called by ElevenLabs agent when candidate is interested in live connect.
    Signals the candidate bridge to enter HOLD mode and kicks off multi-call business search.

    Expected body:
        session_id: str - Live connect session ID
        candidate_interested: bool - Whether candidate agreed
        candidate_summary: str - Brief screening summary
        candidate_city: str - City for job search (e.g. "Gurgaon", "Delhi")
        candidate_category: str - Job category (e.g. "Housekeeping", "Warehouse")
        candidate_salary_min: int - Minimum salary expectation
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        candidate_interested = data.get("candidate_interested", True)
        candidate_summary = data.get("candidate_summary", "")
        candidate_city = data.get("candidate_city", "Gurgaon")
        candidate_category = data.get("candidate_category", "")
        candidate_salary_min = data.get("candidate_salary_min", 0)

        print(f"📞 [LC_TOOLS] connect_to_business: session={session_id}, interested={candidate_interested}, city={candidate_city}, category={candidate_category}, salary_min={candidate_salary_min}")

        if not session_id:
            return {"status": "error", "message": "session_id is required"}

        session = get_session(session_id)
        if not session:
            return {"status": "error", "message": f"Session {session_id} not found"}

        if not candidate_interested:
            update_session_status(session_id, LiveConnectStatus.CANDIDATE_DECLINED)
            background_tasks.add_task(end_session, session_id, "candidate_declined")
            return {"status": "success", "message": "Candidate declined. Session ending."}

        # Signal candidate bridge to enter HOLD mode
        session["_candidate_ready"].set()
        session["screening_summary"] = candidate_summary

        if session.get("candidate_name") and candidate_summary:
            print(f"📞 [LC_TOOLS] Candidate {session.get('candidate_name')}: {candidate_summary[:100]}")

        if session.get("_matching_started"):
            # Parallel path: start_matching already kicked off call_businesses.
            # Just update the screening summary so the business AI has full context.
            print(f"📞 [LC_TOOLS] Matching already started — updating screening summary only")
            return {
                "status": "success",
                "message": "Candidate is on hold. Employers are already being contacted.",
            }

        # Sequential path (fallback if start_matching wasn't called)
        screening_data = {
            "candidate_summary": candidate_summary,
            "candidate_city": candidate_city,
            "candidate_category": candidate_category,
            "candidate_salary_min": candidate_salary_min,
        }

        background_tasks.add_task(call_businesses, session_id, screening_data)

        return {
            "status": "success",
            "message": "Candidate is on hold. Searching for matching employers and calling them now. Tell the candidate to hold for about a minute.",
        }

    except Exception as e:
        print(f"❌ [LC_TOOLS] connect_to_business error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}


@_router.post("/tools/accept_connect")
@_router.post("/api/webhooks/tools/accept_connect")
async def accept_connect_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Called by ElevenLabs agent when business agrees/declines to connect with candidate.
    With parallel calling, uses caller_phone to identify which attempt this is and
    claim_winner() for race resolution.

    Expected body:
        session_id: str - Live connect session ID
        business_agreed: bool - Whether business agreed to connect
        caller_phone: str - Phone number of this business attempt
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        business_agreed = data.get("business_agreed", True)
        caller_phone = data.get("caller_phone", "")

        print(f"📞 [LC_TOOLS] accept_connect: session={session_id}, agreed={business_agreed}, caller_phone={caller_phone}")

        if not session_id:
            return {"status": "error", "message": "session_id is required"}

        session = get_session(session_id)
        if not session:
            return {"status": "error", "message": f"Session {session_id} not found"}

        # Look up per-attempt dict
        attempt = session.get("_attempts", {}).get(caller_phone) if caller_phone else None

        if not business_agreed:
            if attempt:
                attempt["accepted"] = False
                attempt["outcome"] = "declined"
                attempt["pitch_ended_at"] = time.time()
                attempt["declined"].set()
                attempt["disconnect_signal"].set()
            return {"status": "success", "message": "Business declined. Trying next employer."}

        # Business agreed — try to claim winner
        if caller_phone and attempt:
            won = claim_winner(session, caller_phone)
            attempt["pitch_ended_at"] = time.time()
            if won:
                attempt["accepted"] = True
                attempt["outcome"] = "accepted"
                attempt["bridge_ready"].set()
                attempt["disconnect_signal"].set()
                print(f"📞 [LC_TOOLS] {caller_phone} WON the race for session {session_id}")

                # Fast path: if candidate is still in AI mode, disconnect them now
                if not session["_candidate_ready"].is_set():
                    print(f"📞 [LC_TOOLS] FAST PATH: business agreed before screening done — disconnecting candidate AI")
                    session["_candidate_ready"].set()

                return {
                    "status": "success",
                    "message": "Both parties connected! Do a brief warm intro then disconnect. They can talk directly now.",
                }
            else:
                attempt["accepted"] = True
                attempt["outcome"] = "lost_race"
                attempt["disconnect_signal"].set()
                print(f"📞 [LC_TOOLS] {caller_phone} LOST the race for session {session_id}")
                return {
                    "status": "success",
                    "message": "Another employer was faster and is already connected. Thank you for your time, goodbye!",
                }
        else:
            # Fallback for calls without caller_phone (shouldn't happen in parallel mode)
            print(f"⚠️ [LC_TOOLS] accept_connect without caller_phone — using legacy flow")
            session["_business_accepted"] = True
            if hasattr(session.get("_business_ready"), "set"):
                session["_business_ready"].set()
            if not session["_candidate_ready"].is_set():
                session["_candidate_ready"].set()
            return {
                "status": "success",
                "message": "Both parties connected! Do a brief warm intro then disconnect. They can talk directly now.",
            }

    except Exception as e:
        print(f"❌ [LC_TOOLS] accept_connect error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}


# =============================================================================
# Inbound Business Live Connect — reverse flow (business→candidate)
# =============================================================================

# Maps normalized phone → session_id for pending inbound business live connect transfers.
# Populated by start_business_live_connect, consumed by vobiz_bridge finally block.
_inbound_lc_business_sessions: dict[str, str] = {}


@_router.post("/tools/start_business_live_connect")
@_router.post("/api/webhooks/tools/start_business_live_connect")
async def start_business_live_connect_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Called by inbound Jyoti agent when business owner wants live connection to a candidate.
    Creates an inbound business session (no outbound call needed) and kicks off candidate calling.

    Expected body:
        caller_phone: str - Business owner's phone number
        business_name: str - Business name
        role_needed: str - Role they're hiring for
        city: str - City for candidate search
        salary_max: int - Max salary offered (optional)
        requirement_summary: str - Brief summary of requirements
    """
    try:
        data = await request.json()
        caller_phone = data.get("caller_phone", "").strip()
        business_name = data.get("business_name", "").strip()
        role_needed = data.get("role_needed", "").strip()
        city = data.get("city", "Gurgaon")
        salary_max = data.get("salary_max", 0)
        requirement_summary = data.get("requirement_summary", "")

        print(f"📞 [LC_BIZ_INBOUND] start_business_live_connect: phone={caller_phone}, biz={business_name}, role={role_needed}, city={city}")

        if not caller_phone:
            return {"status": "error", "message": "caller_phone is required"}

        normalized = _normalize_phone(caller_phone)

        # Look up the inbound CallUUID
        call_uuid = _inbound_call_uuids.get(normalized, "")
        if not call_uuid:
            print(f"⚠️ [LC_BIZ_INBOUND] No inbound CallUUID found for {normalized}")
            return {"status": "error", "message": "No active inbound call found for this phone number"}

        test_candidate_phone = data.get("test_candidate_phone", "")

        # Create inbound business session (no outbound call — business already on phone)
        session = await create_inbound_business_session(
            business_phone=normalized,
            business_name=business_name,
            business_call_uuid=call_uuid,
            test_candidate_phone=test_candidate_phone,
        )
        session_id = session["id"]

        # Store pending transfer so vobiz_bridge can pick it up
        _inbound_lc_business_sessions[normalized] = session_id

        # Kick off candidate calling in background
        screening_data = {
            "role_needed": role_needed,
            "city": city,
            "salary_max": salary_max,
            "requirement_summary": requirement_summary,
            "business_name": business_name,
        }
        background_tasks.add_task(call_candidates, session_id, screening_data)

        print(f"✅ [LC_BIZ_INBOUND] Session {session_id} created, candidate calling started")

        return {
            "status": "success",
            "session_id": session_id,
            "message": "Live connect started. Tell the business to hold while we find a candidate.",
        }

    except Exception as e:
        print(f"❌ [LC_BIZ_INBOUND] start_business_live_connect error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}


@_router.post("/tools/accept_candidate_connect")
@_router.post("/api/webhooks/tools/accept_candidate_connect")
async def accept_candidate_connect_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Called by ElevenLabs agent when candidate agrees/declines to connect with business (reverse flow).
    With parallel calling, uses caller_phone to identify which attempt this is and
    claim_winner() for race resolution.

    Expected body:
        session_id: str - Live connect session ID
        candidate_agreed: bool - Whether candidate agreed to connect
        caller_phone: str - Phone number of this candidate attempt
    """
    try:
        data = await request.json()
        session_id = data.get("session_id", "")
        candidate_agreed = data.get("candidate_agreed", True)
        caller_phone = data.get("caller_phone", "")

        print(f"📞 [LC_TOOLS] accept_candidate_connect: session={session_id}, agreed={candidate_agreed}, caller_phone={caller_phone}")

        if not session_id:
            return {"status": "error", "message": "session_id is required"}

        session = get_session(session_id)
        if not session:
            return {"status": "error", "message": f"Session {session_id} not found"}

        # Look up per-attempt dict
        attempt = session.get("_attempts", {}).get(caller_phone) if caller_phone else None

        if not candidate_agreed:
            if attempt:
                attempt["accepted"] = False
                attempt["outcome"] = "declined"
                attempt["pitch_ended_at"] = time.time()
                attempt["declined"].set()
                attempt["disconnect_signal"].set()
            return {"status": "success", "message": "Candidate declined. Trying next candidate."}

        # Candidate agreed — try to claim winner
        if caller_phone and attempt:
            won = claim_winner(session, caller_phone)
            attempt["pitch_ended_at"] = time.time()
            if won:
                attempt["accepted"] = True
                attempt["outcome"] = "accepted"
                attempt["bridge_ready"].set()
                attempt["disconnect_signal"].set()
                print(f"📞 [LC_TOOLS] {caller_phone} WON the race for session {session_id}")
                return {
                    "status": "success",
                    "message": "Both parties connected! Do a brief warm intro then disconnect. They can talk directly now.",
                }
            else:
                attempt["accepted"] = True
                attempt["outcome"] = "lost_race"
                attempt["disconnect_signal"].set()
                print(f"📞 [LC_TOOLS] {caller_phone} LOST the race for session {session_id}")
                return {
                    "status": "success",
                    "message": "Another candidate was faster and is already connected. Thank you for your time, goodbye!",
                }
        else:
            # Fallback for calls without caller_phone (shouldn't happen in parallel mode)
            print(f"⚠️ [LC_TOOLS] accept_candidate_connect without caller_phone — using legacy flow")
            session["_candidate_accepted"] = True
            if hasattr(session.get("_candidate_bridge_ready"), "set"):
                session["_candidate_bridge_ready"].set()
            return {
                "status": "success",
                "message": "Both parties connected! Do a brief warm intro then disconnect. They can talk directly now.",
            }

    except Exception as e:
        print(f"❌ [LC_TOOLS] accept_candidate_connect error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error: {e}"}
