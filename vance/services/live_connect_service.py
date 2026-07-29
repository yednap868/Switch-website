"""
Service for Live Connect V2 — screen-first, parallel-call bridging.

Flow:
1. Call candidate via Vobiz → Jyoti screens them (experience, location, salary)
2. Search jobhai_jobs for matching employers
3. Call ALL employers in parallel (up to 20 simultaneously)
4. Each answering employer gets its own AI pitch running concurrently
5. First employer to accept wins → claim_winner() → conference bridge
6. All other calls are hung up
7. Same pattern for reverse flow (business→candidate)
8. Save per-attempt data to Firestore subcollection
"""

import asyncio
import audioop
import io
import json
import os
import threading
import time
import traceback
import uuid
import wave
from typing import Optional

import anthropic
import requests
from google.cloud import storage as gcs

from models.switch_models import LiveConnectSession, LiveConnectStatus
from services.vobiz_service import vobiz_service
from twilio.rest import Client as TwilioClient
from utils.db import fs
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


# In-memory session store (safe with single uvicorn worker)
_sessions: dict[str, dict] = {}

# Max session duration before force-ending
MAX_SESSION_TTL = 15 * 60  # 15 minutes

# How long to wait for each employer to pick up
BUSINESS_RING_TIMEOUT = 25  # seconds

# How long to wait for each candidate to pick up
CANDIDATE_RING_TIMEOUT = 25  # seconds

# Max simultaneous calls (first batch)
MAX_PARALLEL_CALLS = 10

# How many jobs to fetch upfront for incremental calling
JOB_POOL_LIMIT = 200

# How many calls to fire in each incremental batch after the first
INCREMENTAL_BATCH_SIZE = 3

# Category aliases for fuzzy matching candidate language → jobhai categories
CATEGORY_ALIASES: dict[str, list[str]] = {
    "Housekeeping": ["cleaner", "safai", "office boy", "laundry", "housekeeping"],
    "Field Sales": ["sales", "field executive", "field sales"],
    "Warehouse / Logistics": ["packing", "picker", "loader", "warehouse", "logistics", "godown", "storekeeper", "inventory"],
    "Security Guard": ["guard", "security", "watchman", "chowkidar"],
    "Delivery": ["delivery boy", "delivery executive", "delivery", "courier", "rider", "zomato", "swiggy", "blinkit"],
    "Labour/Helper": [
        "helper", "labour", "mazdoor", "labor",
        "waiter", "cook", "chef", "captain", "steward", "kitchen", "restaurant", "hotel",
    ],
    "Manufacturing": ["factory", "welder", "machine operator", "manufacturing", "fitter", "operator", "technician", "mechanic"],
    "Driver": ["driver", "chalak", "chauffeur", "auto"],
    "Sales / Business Development": ["telecaller", "telesales", "sales executive", "bde", "business development", "customer support"],
}


# City aliases for resolving candidate location → Firestore city values
CITY_ALIASES: dict[str, list[str]] = {
    "Delhi": ["delhi", "new delhi", "north delhi", "south delhi", "east delhi", "west delhi", "dilli"],
    "Gurgaon": ["gurgaon", "gurugram", "ggn"],
    "Noida": ["noida"],
    "Greater Noida": ["greater noida"],
    "Faridabad": ["faridabad"],
    "Ghaziabad": ["ghaziabad"],
}

# All Firestore city values — used when we can't resolve a specific city
ALL_CITIES = list(CITY_ALIASES.keys())


def _resolve_cities(candidate_city: str) -> list[str]:
    """
    Resolve a candidate's stated city to Firestore city values.
    Returns list of city strings to query Firestore with.
    NCR / unknown → search all cities (widest net).
    """
    if not candidate_city:
        return ALL_CITIES

    candidate_lower = candidate_city.lower().strip()

    # Check if it's a known alias
    for firestore_city, aliases in CITY_ALIASES.items():
        if candidate_lower == firestore_city.lower():
            return [firestore_city]
        for alias in aliases:
            if alias in candidate_lower or candidate_lower in alias:
                return [firestore_city]

    # NCR-like terms → search everywhere
    if any(term in candidate_lower for term in ("ncr", "national capital")):
        return ALL_CITIES

    # Unknown city → search all cities to cast widest net
    return ALL_CITIES


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


def _get_previously_called_phones(candidate_phone: str) -> set[str]:
    """Get business phones this candidate was actually connected to (winner only) in past sessions."""
    phones = set()
    try:
        sessions = fs.collection("live_connect_sessions") \
            .where("candidate_phone", "==", candidate_phone) \
            .stream()
        for doc in sessions:
            data = doc.to_dict()
            bp = data.get("business_phone", "") or data.get("winner_phone", "")
            if bp:
                phones.add(_normalize_phone(bp))
    except Exception as e:
        print(f"⚠️ [LIVE_CONNECT] Failed to fetch previously called phones: {e}")
    if phones:
        print(f"🔍 [LIVE_CONNECT] Found {len(phones)} previously-connected phones for {candidate_phone}")
    return phones


def get_session(session_id: str) -> Optional[dict]:
    """Get a live connect session from the in-memory store."""
    return _sessions.get(session_id)


def update_session_status(session_id: str, status: LiveConnectStatus) -> None:
    """Update session status in memory and Firestore (non-blocking)."""
    session = _sessions.get(session_id)
    if not session:
        return
    session["status"] = status.value
    session["updated_at"] = time.time()

    def _write():
        try:
            fs.collection("live_connect_sessions").document(session_id).update({
                "status": status.value,
                "updated_at": time.time(),
            })
        except Exception as e:
            print(f"⚠️ [LIVE_CONNECT] Failed to update Firestore status: {e}")

    threading.Thread(target=_write, daemon=True).start()


def _resolve_category(candidate_category: str) -> list[str]:
    """
    Resolve a candidate's stated category to matching jobhai category names.
    Returns list of exact category strings to query Firestore with.
    """
    if not candidate_category:
        return []

    candidate_lower = candidate_category.lower().strip()

    # Direct match first
    for category in CATEGORY_ALIASES:
        if candidate_lower == category.lower():
            return [category]

    # Alias match
    matched = []
    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if alias in candidate_lower or candidate_lower in alias:
                if category not in matched:
                    matched.append(category)

    return matched


def search_matching_jobs(
    city: str,
    category: str,
    salary_min: int = 0,
    limit: int = 20,
    experience_level: str = "",
    exclude_phones: set[str] | None = None,
) -> list[dict]:
    """
    Search Firestore jobhai_jobs collection for matching jobs.
    Resolves city via aliases, queries ALL jobs in those cities,
    then uses category for ranking (matched first, then others).
    Sorts by salary_max descending within each group.
    Deduplicates by phone, returns top `limit` matches.
    Excludes any job whose normalized phone is in exclude_phones (cross-session dedup).
    """
    print(f"🔍 [LIVE_CONNECT] Searching jobs: city={city}, category={category}, salary_min={salary_min}")

    # Resolve candidate city to Firestore city values
    cities = _resolve_cities(city)
    print(f"🔍 [LIVE_CONNECT] Resolved city '{city}' → {cities}")

    # Resolve candidate category to jobhai category names (for ranking)
    categories = _resolve_category(category)
    categories_set = set(categories)
    print(f"🔍 [LIVE_CONNECT] Resolved category '{category}' → {list(categories_set) or ['(all — no match)']}")

    # Query ALL jobs in resolved cities (no category filter at query level)
    all_jobs = []
    for c in cities:
        query = fs.collection("jobhai_jobs").where("city", "==", c)
        docs = list(query.stream())
        for doc in docs:
            job = doc.to_dict()
            if salary_min > 0 and job.get("salary_max", 0) < salary_min:
                continue
            all_jobs.append(job)

    # Rank: category-matched jobs first, then others — salary_max descending within each group
    category_matched = []
    other_jobs = []
    for job in all_jobs:
        if categories_set and job.get("category") in categories_set:
            category_matched.append(job)
        else:
            other_jobs.append(job)

    category_matched.sort(key=lambda j: j.get("salary_max", 0), reverse=True)
    other_jobs.sort(key=lambda j: j.get("salary_max", 0), reverse=True)
    ranked = category_matched + other_jobs

    # Deduplicate by phone (don't call same HR twice) + cross-session dedup
    seen_phones = set()
    excluded_count = 0
    unique_results = []
    for job in ranked:
        phone = job.get("phone", "")
        if not phone or phone in seen_phones:
            continue
        seen_phones.add(phone)
        if exclude_phones and _normalize_phone(phone) in exclude_phones:
            excluded_count += 1
            continue
        unique_results.append(job)
    if excluded_count:
        print(f"🔍 [LIVE_CONNECT] Excluded {excluded_count} previously-called phones")

    results = unique_results[:limit]
    print(f"🔍 [LIVE_CONNECT] Found {len(all_jobs)} total, {len(category_matched)} category-matched, {len(unique_results)} unique phones, returning top {len(results)}")
    for i, job in enumerate(results):
        print(f"  #{i+1}: {job.get('title')} @ {job.get('company')} — ₹{job.get('salary_max')} — {job.get('phone')}")

    return results


# ============================================================================
# SMS fallback
# ============================================================================


def _send_sms(to_phone: str, body: str) -> bool:
    """Send an SMS via Twilio. Returns True on success."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    debug = {"to": to_phone, "from_number": from_number, "body_len": len(body), "time": time.time()}

    if not account_sid or not auth_token or not from_number:
        debug["error"] = f"not_configured: sid={bool(account_sid)} token={bool(auth_token)} from={bool(from_number)}"
        print(f"❌ [SMS_FALLBACK] Twilio not configured, skipping SMS")
        fs.collection("debug_webhooks").document("last_sms_attempt").set(debug)
        return False

    if not to_phone.startswith("+"):
        to_phone = "+91" + to_phone if not to_phone.startswith("91") else "+" + to_phone
    debug["to_normalized"] = to_phone

    try:
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(body=body, from_=from_number, to=to_phone)
        debug["status"] = "sent"
        debug["sid"] = message.sid
        print(f"✅ [SMS_FALLBACK] SMS sent to {to_phone} — SID: {message.sid}")
        fs.collection("debug_webhooks").document("last_sms_attempt").set(debug)
        return True
    except Exception as e:
        debug["status"] = "failed"
        debug["error"] = str(e)
        print(f"❌ [SMS_FALLBACK] Failed to send SMS to {to_phone}: {e}")
        traceback.print_exc()
        fs.collection("debug_webhooks").document("last_sms_attempt").set(debug)
        return False


def _send_fallback_sms_to_candidate(session: dict) -> None:
    """Send candidate top 5 job details with HR phone numbers."""
    candidate_phone = session.get("candidate_phone", "")
    candidate_name = session.get("candidate_name", "") or "Candidate"
    jobs = (session.get("matching_jobs") or [])[:5]

    if not candidate_phone or not jobs:
        return

    job_lines = []
    for i, job in enumerate(jobs, 1):
        title = job.get("title", "Job")
        company = job.get("company", "")
        salary = job.get("salary_max", "")
        phone = job.get("phone", "")
        salary_str = f"Rs {salary}/month" if salary else ""
        job_lines.append(f"{i}. {title} @ {company} - {salary_str} - HR: +{phone}")

    jobs_text = "\n".join(job_lines)

    body = (
        f"Hi {candidate_name}, Jyoti from Switch.\n"
        f"Abhi employer phone nahi utha paya, lekin ye jobs match karti hain:\n\n"
        f"{jobs_text}\n\n"
        f"Inhe directly call kar sakte hain. All the best! - Jyoti, Switch"
    )
    _send_sms(candidate_phone, body)


def _send_fallback_sms_to_businesses(session: dict) -> None:
    """Send each of top 5 HRs the candidate's name, phone, and summary."""
    candidate_phone = session.get("candidate_phone", "")
    candidate_name = session.get("candidate_name", "") or "Candidate"
    summary = session.get("screening_summary", "") or session.get("screening_data", {}).get("candidate_summary", "")
    jobs = (session.get("matching_jobs") or [])[:5]

    if not candidate_phone or not jobs:
        return

    for job in jobs:
        hr_phone = job.get("phone", "")
        if not hr_phone:
            continue

        body = (
            f"Switch - Candidate Lead\n\n"
            f"Name: {candidate_name}\n"
            f"Phone: +{candidate_phone}\n"
            f"Profile: {summary}\n\n"
            f"Humne unhe aapka number bhej diya hai.\n"
            f"Aap bhi unhe call kar sakte hain. - Jyoti, Switch"
        )
        _send_sms(hr_phone, body)


def _send_fallback_sms_to_business_caller(session: dict) -> None:
    """Send business caller top 5 candidate details with phone numbers."""
    business_phone = session.get("business_phone", "")
    candidates = (session.get("matching_candidates") or [])[:5]

    if not business_phone or not candidates:
        return

    candidate_lines = []
    for i, cand in enumerate(candidates, 1):
        name = cand.get("name", "Candidate")
        phone = cand.get("phone", "")
        area = cand.get("area", "")
        exp = cand.get("experience", "")
        details = f"{name} - {area}" + (f" - {exp}" if exp else "") + f" - +{phone}"
        candidate_lines.append(f"{i}. {details}")

    candidates_text = "\n".join(candidate_lines)

    body = (
        f"Switch - Candidate Leads\n\n"
        f"Abhi koi candidate phone nahi utha paya, lekin ye candidates match karte hain:\n\n"
        f"{candidates_text}\n\n"
        f"Inhe directly call kar sakte hain. - Jyoti, Switch"
    )
    _send_sms(business_phone, body)


def _send_bridge_success_sms(session: dict) -> None:
    """After a successful bridge, send both sides each other's details."""
    direction = session.get("direction", "candidate_to_business")
    candidate_phone = session.get("candidate_phone", "")
    candidate_name = session.get("candidate_name", "") or "Candidate"
    business_phone = session.get("business_phone", "")
    business_name = session.get("business_name", "") or "Employer"

    if not candidate_phone or not business_phone:
        return

    if direction == "business_to_candidate":
        # Business called candidate
        screening_data = session.get("screening_data", {})
        role = screening_data.get("role_needed", "")
        candidate = session.get("current_candidate", {})
        cand_area = candidate.get("area", "")

        # SMS to business: candidate details
        to_biz = (
            f"Switch - Connected!\n\n"
            f"Aapne abhi baat ki:\n"
            f"Name: {candidate_name}\n"
            f"Phone: +{candidate_phone}\n"
            + (f"Area: {cand_area}\n" if cand_area else "")
            + f"\nInhe dubara call kar sakte hain. - Jyoti, Switch"
        )
        _send_sms(business_phone, to_biz)

        # SMS to candidate: business details
        to_cand = (
            f"Hi {candidate_name}, Jyoti from Switch.\n"
            f"Aapne abhi {business_name} se baat ki"
            + (f" ({role} ke liye)" if role else "")
            + f".\nHR Phone: +{business_phone}\n\n"
            f"Inhe dubara call kar sakte hain. All the best! - Jyoti, Switch"
        )
        _send_sms(candidate_phone, to_cand)
    else:
        # Candidate called business (default flow)
        job = session.get("current_job", {})
        title = job.get("title", "")
        company = job.get("company", business_name)
        salary = job.get("salary_max", "")
        summary = session.get("screening_summary", "")

        # SMS to candidate: job + HR details
        salary_str = f" - Rs {salary}/month" if salary else ""
        to_cand = (
            f"Hi {candidate_name}, Jyoti from Switch.\n"
            f"Aapne abhi {company} se baat ki"
            + (f" ({title}{salary_str})" if title else "")
            + f".\nHR Phone: +{business_phone}\n\n"
            f"Inhe dubara call kar sakte hain. All the best! - Jyoti, Switch"
        )
        _send_sms(candidate_phone, to_cand)

        # SMS to business HR: candidate details
        to_biz = (
            f"Switch - Connected!\n\n"
            f"Aapne abhi baat ki:\n"
            f"Name: {candidate_name}\n"
            f"Phone: +{candidate_phone}\n"
            + (f"Profile: {summary}\n" if summary else "")
            + f"\nInhe dubara call kar sakte hain. - Jyoti, Switch"
        )
        _send_sms(business_phone, to_biz)

    print(f"📱 [SMS_BRIDGE] Sent bridge success SMS to both parties for session {session.get('id', '')}")


def _send_fallback_sms_to_candidates(session: dict) -> None:
    """Send each of top 5 candidates the business details and HR phone."""
    business_phone = session.get("business_phone", "")
    business_name = session.get("business_name", "") or "Employer"
    screening_data = session.get("screening_data", {})
    role = screening_data.get("role_needed", "")
    city = screening_data.get("city", "")
    candidates = (session.get("matching_candidates") or [])[:5]

    if not business_phone or not candidates:
        return

    for cand in candidates:
        cand_phone = cand.get("phone", "")
        cand_name = cand.get("name", "Candidate")
        if not cand_phone:
            continue

        body = (
            f"Hi {cand_name}, Jyoti from Switch.\n"
            f"{business_name} ko {role} chahiye ({city}).\n"
            f"HR Phone: +{business_phone}\n\n"
            f"Unhe directly call kar sakte hain. All the best! - Jyoti, Switch"
        )
        _send_sms(cand_phone, body)


# ============================================================================
# Post-bridge analysis — transcription, AI analysis, admin notification
# ============================================================================

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
ADMIN_WHATSAPP_PHONE = os.getenv("ADMIN_WHATSAPP_PHONE", "")


def _transcribe_audio(audio_bytes: bytes, content_type: str = "audio/wav") -> str:
    """Transcribe audio using Deepgram Nova-3 (Hindi). Supports WAV and MP3. Sync."""
    if not DEEPGRAM_API_KEY:
        print("⚠️ [TRANSCRIPTION] DEEPGRAM_API_KEY not set, skipping transcription")
        return ""
    try:
        resp = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true&language=hi",
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": content_type,
            },
            data=audio_bytes,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        transcript = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
        print(f"✅ [TRANSCRIPTION] Got transcript ({len(transcript)} chars)")
        return transcript
    except Exception as e:
        print(f"❌ [TRANSCRIPTION] Failed: {type(e).__name__}: {e}")
        return ""


def _analyze_bridge_transcript(transcript: str, session_context: dict) -> dict:
    """Analyze bridge transcript with Claude to determine if interview was confirmed. Sync."""
    if not transcript:
        return {"interview_confirmed": False, "summary": "No transcript available"}

    candidate_name = session_context.get("candidate_name", "Unknown")
    job_title = session_context.get("job_title", "Unknown")
    company = session_context.get("business_name", "Unknown")

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            system="You analyze phone call transcripts between job candidates and employers in India. Respond ONLY with valid JSON, no markdown.",
            messages=[{
                "role": "user",
                "content": (
                    f"Candidate: {candidate_name}\n"
                    f"Job: {job_title} at {company}\n\n"
                    f"Transcript:\n{transcript}\n\n"
                    "Analyze this call and return JSON with these fields:\n"
                    '- "interview_confirmed": boolean (was an interview/meeting confirmed?)\n'
                    '- "interview_date": string or null (date if mentioned)\n'
                    '- "interview_time": string or null (time if mentioned)\n'
                    '- "interview_location": string or null (location/address if mentioned)\n'
                    '- "summary": string (1-2 sentence summary of what was discussed/agreed in the call)'
                ),
            }],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)
        print(f"✅ [BRIDGE_ANALYSIS] interview_confirmed={result.get('interview_confirmed')}")
        return result
    except Exception as e:
        print(f"❌ [BRIDGE_ANALYSIS] Failed: {type(e).__name__}: {e}")
        return {"interview_confirmed": False, "summary": f"Analysis failed: {e}"}


def _notify_admin_bridge_result(session_context: dict, analysis: dict) -> None:
    """Send bridge result notification to admin via WhatsApp. Sync."""
    admin_phone = ADMIN_WHATSAPP_PHONE
    if not admin_phone:
        print("⚠️ [BRIDGE_NOTIFY] ADMIN_WHATSAPP_PHONE not set, skipping notification")
        return

    candidate_name = session_context.get("candidate_name", "Unknown")
    candidate_phone = session_context.get("candidate_phone", "")
    business_name = session_context.get("business_name", "Unknown")
    business_phone = session_context.get("business_phone", "")
    job_title = session_context.get("job_title", "")
    duration = session_context.get("bridge_duration_seconds", 0)
    recording_url = session_context.get("recording_url", "")

    confirmed = analysis.get("interview_confirmed", False)
    status_str = "YES" if confirmed else "NO"
    summary = analysis.get("summary", "")

    lines = [
        f"*Bridge Result — {status_str}*",
        "",
        f"Candidate: {candidate_name} ({candidate_phone})",
        f"Business: {business_name} ({business_phone})",
    ]
    if job_title:
        lines.append(f"Role: {job_title}")
    if duration:
        lines.append(f"Duration: {round(duration)}s")
    lines.append(f"Interview confirmed: {status_str}")

    if confirmed:
        date = analysis.get("interview_date")
        time_str = analysis.get("interview_time")
        location = analysis.get("interview_location")
        if date:
            lines.append(f"Date: {date}")
        if time_str:
            lines.append(f"Time: {time_str}")
        if location:
            lines.append(f"Location: {location}")

    if summary:
        lines.append(f"\nSummary: {summary}")
    if recording_url:
        lines.append(f"\nRecording: {recording_url}")

    message = "\n".join(lines)

    try:
        msg_data = MsgComponents.text_scaffold(to=admin_phone, text=message)
        WhatsAppSender.send(msg_data)
        print(f"✅ [BRIDGE_NOTIFY] Sent bridge result to admin {admin_phone}")
    except Exception as e:
        print(f"❌ [BRIDGE_NOTIFY] Failed to send WhatsApp: {type(e).__name__}: {e}")


def analyze_conference_recording(session_id: str, mp3_bytes: bytes, recording_url: str) -> None:
    """
    Transcribe + analyze a conference recording (MP3 from Vobiz).
    Called from the recording callback in live_connect_routes.py.
    Pulls session context from Firestore since in-memory session may be gone. Sync.
    """
    try:
        doc = fs.collection("telephonic_interviews").document(session_id).get()
        if not doc.exists:
            session_doc = fs.collection("live_connect_sessions").document(session_id).get()
            if not session_doc.exists:
                print(f"⚠️ [CONFERENCE_ANALYSIS] No Firestore doc found for {session_id}")
                return
            data = session_doc.to_dict()
        else:
            data = doc.to_dict()

        session_context = {
            "session_id": session_id,
            "candidate_name": data.get("candidate_name", ""),
            "candidate_phone": data.get("candidate_phone", ""),
            "business_name": data.get("business_name", ""),
            "business_phone": data.get("business_phone", ""),
            "job_title": data.get("job_title", ""),
            "screening_summary": data.get("screening_summary", ""),
            "bridge_duration_seconds": data.get("bridge_duration_seconds", 0),
            "recording_url": recording_url,
        }

        transcript = _transcribe_audio(mp3_bytes, content_type="audio/mpeg")

        analysis = _analyze_bridge_transcript(transcript, session_context)

        analysis_data = {
            "transcript": transcript,
            "interview_confirmed": analysis.get("interview_confirmed", False),
            "interview_date": analysis.get("interview_date"),
            "interview_time": analysis.get("interview_time"),
            "interview_location": analysis.get("interview_location"),
            "analysis_summary": analysis.get("summary", ""),
        }
        fs.collection("telephonic_interviews").document(session_id).set(
            analysis_data, merge=True
        )
        print(f"✅ [CONFERENCE_ANALYSIS] Saved analysis for {session_id}")

        _notify_admin_bridge_result(session_context, analysis)

    except Exception as e:
        print(f"❌ [CONFERENCE_ANALYSIS] Failed for {session_id}: {type(e).__name__}: {e}")
        traceback.print_exc()


# ============================================================================
# Recording — save call audio as WAV to Firebase Storage
# ============================================================================


def _mix_mulaw_to_wav(candidate_audio: bytes, business_audio: bytes) -> bytes:
    """Mix two mulaw 8kHz mono streams into a single PCM 16-bit WAV file."""
    cand_pcm = audioop.ulaw2lin(candidate_audio, 2) if candidate_audio else b""
    biz_pcm = audioop.ulaw2lin(business_audio, 2) if business_audio else b""

    max_len = max(len(cand_pcm), len(biz_pcm))
    if len(cand_pcm) < max_len:
        cand_pcm += b"\x00" * (max_len - len(cand_pcm))
    if len(biz_pcm) < max_len:
        biz_pcm += b"\x00" * (max_len - len(biz_pcm))

    if cand_pcm and biz_pcm:
        mixed = audioop.add(cand_pcm, biz_pcm, 2)
        mixed = audioop.mul(mixed, 2, 0.5)
    elif cand_pcm:
        mixed = cand_pcm
    else:
        mixed = biz_pcm

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(mixed)
    return buf.getvalue()


def _upload_recording(session_id: str, wav_bytes: bytes) -> str:
    """Upload WAV to GCS and return the public URL."""
    bucket_name = os.getenv("GCS_RECORDING_BUCKET", "relay-15824-recordings")
    client = gcs.Client()
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        bucket = client.create_bucket(bucket_name, location="asia-south1")
    blob_path = f"recordings/live_connect/{session_id}.wav"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(wav_bytes, content_type="audio/wav")
    blob.make_public()
    return blob.public_url


async def _save_recording(
    session_id: str,
    candidate_audio: bytes,
    business_audio: bytes,
    session_context: dict | None = None,
) -> None:
    """Create WAV from recorded audio, upload, then transcribe + analyze + notify."""
    try:
        print(f"🎙️ [RECORDING] Processing recording for session {session_id}")
        print(f"🎙️ [RECORDING] Audio: candidate={len(candidate_audio)}B, business={len(business_audio)}B")

        wav_bytes = await asyncio.to_thread(
            _mix_mulaw_to_wav, candidate_audio, business_audio
        )
        duration_sec = round(len(wav_bytes) / (8000 * 2), 1)
        print(f"🎙️ [RECORDING] WAV created: {len(wav_bytes)} bytes ({duration_sec}s)")

        recording_url = await asyncio.to_thread(
            _upload_recording, session_id, wav_bytes
        )
        print(f"🎙️ [RECORDING] Uploaded: {recording_url}")

        await asyncio.to_thread(
            fs.collection("telephonic_interviews").document(session_id).update,
            {"recording_url": recording_url},
        )
        print(f"✅ [RECORDING] Saved recording URL for session {session_id}")

        # Post-bridge analysis pipeline: transcribe → analyze → save → notify
        if session_context:
            session_context["recording_url"] = recording_url

            transcript = await asyncio.to_thread(_transcribe_audio, wav_bytes)

            analysis = await asyncio.to_thread(
                _analyze_bridge_transcript, transcript, session_context
            )

            analysis_data = {
                "transcript": transcript,
                "interview_confirmed": analysis.get("interview_confirmed", False),
                "interview_date": analysis.get("interview_date"),
                "interview_time": analysis.get("interview_time"),
                "interview_location": analysis.get("interview_location"),
                "analysis_summary": analysis.get("summary", ""),
            }
            await asyncio.to_thread(
                fs.collection("telephonic_interviews").document(session_id).update,
                analysis_data,
            )
            print(f"✅ [RECORDING] Saved analysis for session {session_id}")

            await asyncio.to_thread(
                _notify_admin_bridge_result, session_context, analysis
            )

    except Exception as e:
        print(f"❌ [RECORDING] Failed for {session_id}: {type(e).__name__}: {e}")
        traceback.print_exc()


# ============================================================================
# Race resolution
# ============================================================================


def claim_winner(session: dict, phone: str) -> bool:
    """
    Atomically claim a winner for the parallel calling race.

    Uses asyncio's cooperative scheduling guarantee — no preemption between
    the check and the set within a single event loop tick.

    Returns True if this phone won, False if another phone already won.
    """
    if session.get("_winner_phone") is not None:
        return False
    session["_winner_phone"] = phone
    # Disconnect all OTHER bridges' AIs
    for other_phone, attempt in session.get("_attempts", {}).items():
        if other_phone != phone and attempt.get("disconnect_signal"):
            attempt["disconnect_signal"].set()
    session["_winner_found"].set()
    return True


async def _safe_hangup(call_uuid: str) -> None:
    """Try to hang up a call, swallowing any errors."""
    if not call_uuid:
        return
    try:
        await vobiz_service.hangup_call(call_uuid)
    except Exception as e:
        print(f"⚠️ [LIVE_CONNECT] Safe hangup failed for {call_uuid}: {e}")


# ============================================================================
# Firestore data capture
# ============================================================================


def _save_attempts_to_firestore(session_id: str, attempts: dict, direction: str = "candidate_to_business") -> None:
    """
    Write each attempt to Firestore subcollection:
    live_connect_sessions/{session_id}/attempts/{phone}
    Also update the main session doc with summary stats.
    """
    try:
        session_ref = fs.collection("live_connect_sessions").document(session_id)
        attempts_ref = session_ref.collection("attempts")

        total = 0
        answered = 0
        accepted = 0
        declined = 0
        no_answer = 0
        lost_race = 0

        for phone, attempt in attempts.items():
            total += 1
            outcome = attempt.get("outcome", "unknown")
            if outcome == "accepted":
                accepted += 1
                answered += 1
            elif outcome == "declined":
                declined += 1
                answered += 1
            elif outcome == "lost_race":
                lost_race += 1
                answered += 1
            elif outcome == "no_answer":
                no_answer += 1
            elif outcome in ("timeout", "call_failed"):
                pass
            else:
                if attempt.get("answered_at"):
                    answered += 1

            # Build serializable attempt data
            attempt_data = {
                "phone": phone,
                "name": attempt.get("name", ""),
                "outcome": outcome,
                "call_uuid": attempt.get("call_uuid", ""),
                "conversation_id": attempt.get("conversation_id", ""),
                "call_initiated_at": attempt.get("call_initiated_at"),
                "answered_at": attempt.get("answered_at"),
                "pitch_ended_at": attempt.get("pitch_ended_at"),
            }

            # Add direction-specific fields
            if direction == "candidate_to_business":
                job = attempt.get("job") or {}
                attempt_data["job_id"] = job.get("job_id", "")
                attempt_data["company"] = job.get("company", "")
                attempt_data["job_title"] = job.get("title", "")
            else:
                candidate = attempt.get("candidate") or {}
                attempt_data["candidate_name"] = candidate.get("name", "")
                attempt_data["candidate_area"] = candidate.get("area", "")

            # Compute durations
            initiated = attempt.get("call_initiated_at")
            answered_at = attempt.get("answered_at")
            pitch_ended = attempt.get("pitch_ended_at")
            if initiated and answered_at:
                attempt_data["ring_duration_sec"] = round(answered_at - initiated, 1)
            if answered_at and pitch_ended:
                attempt_data["pitch_duration_sec"] = round(pitch_ended - answered_at, 1)

            attempts_ref.document(phone).set(attempt_data)

        # Update main session doc with summary
        session_ref.update({
            "parallel": True,
            "total_attempts": total,
            "attempts_summary": {
                "total": total,
                "answered": answered,
                "accepted": accepted,
                "declined": declined,
                "no_answer": no_answer,
                "lost_race": lost_race,
            },
        })

        print(f"✅ [LIVE_CONNECT] Saved {total} attempts to Firestore (answered={answered}, accepted={accepted})")

    except Exception as e:
        print(f"⚠️ [LIVE_CONNECT] Failed to save attempts to Firestore: {e}")


# ============================================================================
# Session lifecycle
# ============================================================================


async def initiate_session(
    candidate_phone: str,
    candidate_name: str = "",
    candidate_id: str = "",
    test_business_phone: str = "",
) -> dict:
    """
    Create a live connect session and call the candidate via Vobiz.
    No job_id or business_phone needed — those come after screening.
    """
    session_id = f"lc_{uuid.uuid4().hex[:12]}"
    candidate_phone = _normalize_phone(candidate_phone)

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    answer_url = f"https://{server_host}/api/live-connect/answer/candidate?session_id={session_id}"
    hangup_url = f"https://{server_host}/api/live-connect/hangup?session_id={session_id}&party=candidate"

    session = LiveConnectSession(
        id=session_id,
        candidate_id=candidate_id,
        candidate_phone=candidate_phone,
        candidate_name=candidate_name,
        status=LiveConnectStatus.CALLING_CANDIDATE,
    )
    session_dict = session.model_dump()

    # Add asyncio signaling events (not serialized)
    session_dict["_candidate_ready"] = asyncio.Event()
    session_dict["_business_ready"] = asyncio.Event()
    session_dict["_business_bridge_ready"] = asyncio.Event()
    session_dict["_session_ended"] = asyncio.Event()
    session_dict["_matching_started"] = False
    session_dict["_test_business_phone"] = _normalize_phone(test_business_phone) if test_business_phone else ""
    session_dict["_candidate_vobiz_ws"] = None
    session_dict["_candidate_stream_id"] = None

    # Parallel calling state
    session_dict["_attempts"] = {}
    session_dict["_winner_phone"] = None
    session_dict["_winner_found"] = asyncio.Event()

    _sessions[session_id] = session_dict

    # Save to Firestore (without internal fields)
    firestore_data = {k: v for k, v in session_dict.items() if not k.startswith("_")}
    fs.collection("live_connect_sessions").document(session_id).set(firestore_data)

    print(f"📞 [LIVE_CONNECT] Session {session_id} created. Calling candidate {candidate_phone}...")

    # Make outbound call to candidate
    try:
        call_result = await vobiz_service.make_call(
            to_number=candidate_phone,
            answer_url=answer_url,
            hangup_url=hangup_url,
        )
        call_uuid = call_result.get("call_uuid") or call_result.get("request_uuid") or ""
        session_dict["candidate_call_uuid"] = call_uuid
        fs.collection("live_connect_sessions").document(session_id).update({
            "candidate_call_uuid": call_uuid,
        })
        print(f"📞 [LIVE_CONNECT] Candidate call initiated: {call_uuid}")
    except Exception as e:
        print(f"❌ [LIVE_CONNECT] Failed to call candidate: {e}")
        update_session_status(session_id, LiveConnectStatus.FAILED)
        session_dict["outcome"] = f"Failed to call candidate: {e}"
        return session_dict

    # Schedule TTL watchdog
    asyncio.create_task(_session_ttl_watchdog(session_id))

    return session_dict


async def create_inbound_session(
    candidate_phone: str,
    candidate_name: str = "",
    candidate_call_uuid: str = "",
    test_business_phone: str = "",
) -> dict:
    """
    Create a live connect session for an inbound caller (already on the phone).

    Unlike initiate_session(), this does NOT make an outbound call to the candidate.
    The candidate is already connected via the inbound Vobiz call.
    _candidate_ready is NOT pre-set — the candidate bridge handles the inbound first
    connection by setting it when the candidate actually arrives at the LC bridge.
    """
    session_id = f"lc_{uuid.uuid4().hex[:12]}"
    candidate_phone = _normalize_phone(candidate_phone)

    session = LiveConnectSession(
        id=session_id,
        candidate_id="",
        candidate_phone=candidate_phone,
        candidate_name=candidate_name,
        status=LiveConnectStatus.CANDIDATE_HOLD,
    )
    session_dict = session.model_dump()

    # Add asyncio signaling events (not serialized)
    session_dict["_candidate_ready"] = asyncio.Event()
    # Do NOT pre-set _candidate_ready — candidate bridge needs to handle inbound first connection
    session_dict["_business_ready"] = asyncio.Event()
    session_dict["_business_bridge_ready"] = asyncio.Event()
    session_dict["_session_ended"] = asyncio.Event()
    session_dict["_matching_started"] = False  # Set to True when call_businesses actually fires
    session_dict["_test_business_phone"] = _normalize_phone(test_business_phone) if test_business_phone else ""
    session_dict["_candidate_vobiz_ws"] = None
    session_dict["_candidate_stream_id"] = None
    session_dict["_candidate_ws_connected"] = False  # True once candidate actually connects to LC bridge
    session_dict["_businesses_exhausted"] = None  # Set to reason string if all businesses fail before candidate arrives
    session_dict["candidate_call_uuid"] = candidate_call_uuid
    session_dict["inbound"] = True

    # Parallel calling state
    session_dict["_attempts"] = {}
    session_dict["_winner_phone"] = None
    session_dict["_winner_found"] = asyncio.Event()

    _sessions[session_id] = session_dict

    # Save to Firestore (without internal fields)
    firestore_data = {k: v for k, v in session_dict.items() if not k.startswith("_")}
    fs.collection("live_connect_sessions").document(session_id).set(firestore_data)

    print(f"📞 [LIVE_CONNECT] Inbound session {session_id} created for {candidate_phone} (already on call)")

    # Schedule TTL watchdog
    asyncio.create_task(_session_ttl_watchdog(session_id))

    return session_dict


# ============================================================================
# Parallel business calling (candidate→business flow)
# ============================================================================


async def call_businesses(session_id: str, screening_data: dict) -> dict:
    """
    Called when candidate screening is complete. Searches for matching jobs
    and calls ALL employers in parallel. First to accept wins.
    """
    try:
        return await _call_businesses_inner(session_id, screening_data)
    except Exception as e:
        print(f"❌ [LIVE_CONNECT] call_businesses CRASHED: {type(e).__name__}: {e}")
        traceback.print_exc()
        try:
            fs.collection("live_connect_sessions").document(session_id).update({
                "call_businesses_error": f"{type(e).__name__}: {e}",
                "call_businesses_error_at": time.time(),
            })
        except Exception:
            pass
        session = _sessions.get(session_id)
        if session:
            await handle_business_unreachable(session_id, reason=f"call_businesses_crash: {e}")
        return session or {"error": str(e)}


async def _call_businesses_inner(session_id: str, screening_data: dict) -> dict:
    """Inner implementation of call_businesses with full error propagation."""
    debug_ref = fs.collection("debug_webhooks").document(f"parallel_calls_{session_id}")
    debug_log = {"session_id": session_id, "started_at": time.time(), "steps": []}

    def _log_step(step: str, data: dict = None):
        entry = {"step": step, "time": time.time()}
        if data:
            entry.update(data)
        debug_log["steps"].append(entry)
        threading.Thread(target=debug_ref.set, args=(dict(debug_log),), daemon=True).start()
        print(f"📊 [PARALLEL_DEBUG] [{session_id}] {step}: {data or ''}")

    session = _sessions.get(session_id)
    if not session:
        _log_step("SESSION_NOT_FOUND")
        return {"error": "Session not found"}

    _log_step("SESSION_FOUND", {"candidate_phone": session.get("candidate_phone", "")})

    # Store screening data
    candidate_summary = screening_data.get("candidate_summary", "")
    session["screening_summary"] = candidate_summary
    session["screening_data"] = screening_data
    update_session_status(session_id, LiveConnectStatus.CANDIDATE_HOLD)

    # Cross-session dedup: get all phones this candidate was already matched with
    candidate_phone = session.get("candidate_phone", "")
    exclude_phones = await asyncio.to_thread(_get_previously_called_phones, candidate_phone)

    # Test override: use specific business phone instead of searching
    test_phone = session.get("_test_business_phone", "")
    if test_phone:
        print(f"🧪 [LIVE_CONNECT] TEST MODE: using override business phone {test_phone}")
        matching_jobs = [{
            "phone": test_phone,
            "company": "Test Business",
            "title": "Test Position",
            "city": screening_data.get("candidate_city", "Gurgaon"),
            "category": screening_data.get("candidate_category", ""),
            "salary_max": 0,
            "job_id": "test_job",
        }]
    else:
        # Search for matching jobs (large pool for incremental calling)
        city = screening_data.get("candidate_city", "Gurgaon")
        category = screening_data.get("candidate_category", "")
        salary_min = int(screening_data.get("candidate_salary_min", 0) or 0)
        experience_level = screening_data.get("candidate_experience_level", "")

        _log_step("SEARCHING_JOBS", {"city": city, "category": category, "salary_min": salary_min, "experience_level": experience_level, "exclude_phones": len(exclude_phones)})

        matching_jobs = await asyncio.to_thread(
            search_matching_jobs,
            city=city,
            category=category,
            salary_min=salary_min,
            limit=JOB_POOL_LIMIT,
            experience_level=experience_level,
            exclude_phones=exclude_phones,
        )

        _log_step("SEARCH_DONE", {
            "jobs_found": len(matching_jobs),
            "phones": [j.get("phone", "") for j in matching_jobs[:5]],
        })

    if not matching_jobs:
        _log_step("NO_MATCHING_JOBS")
        print(f"⚠️ [LIVE_CONNECT] No matching jobs found for session {session_id}")
        session["outcome"] = "No matching jobs found"
        await handle_business_unreachable(session_id, reason="no_matching_jobs")
        return session

    session["matching_jobs"] = matching_jobs

    # Save matching jobs to Firestore (background — don't block event loop)
    def _save_jobs():
        try:
            fs.collection("live_connect_sessions").document(session_id).update({
                "screening_summary": candidate_summary,
                "screening_data": screening_data,
                "matching_jobs": matching_jobs,
            })
        except Exception as e:
            print(f"⚠️ [LIVE_CONNECT] Failed to save matching jobs: {e}")

    threading.Thread(target=_save_jobs, daemon=True).start()

    # Split job pool: first batch (up to MAX_PARALLEL_CALLS) + incremental pool (rest)
    initial_batch_jobs = matching_jobs[:MAX_PARALLEL_CALLS]
    incremental_pool = matching_jobs[MAX_PARALLEL_CALLS:]

    # Initialize shared attempt tracking and session-level race events
    attempts = {}
    session["_attempts"] = attempts
    session["_winner_phone"] = None
    session["_winner_found"] = asyncio.Event()

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    update_session_status(session_id, LiveConnectStatus.CALLING_BUSINESS)

    def _init_attempt(job: dict) -> str | None:
        """Create attempt tracking for a job, return normalized phone or None."""
        phone = _normalize_phone(job.get("phone", ""))
        if not phone or phone in attempts:
            return None
        attempts[phone] = {
            "answered": asyncio.Event(),
            "bridge_ready": asyncio.Event(),
            "declined": asyncio.Event(),
            "disconnect_signal": asyncio.Event(),
            "accepted": None,
            "call_uuid": "",
            "stream_id": "",
            "vobiz_ws": None,
            "conversation_id": "",
            "job": job,
            "name": job.get("company", ""),
            "call_initiated_at": None,
            "answered_at": None,
            "pitch_ended_at": None,
            "outcome": "",
        }
        return phone

    async def _run_attempt(phone: str, job: dict) -> None:
        """Run a single business call attempt."""
        attempt = attempts[phone]
        business_phone = phone

        answer_url = (
            f"https://{server_host}/api/live-connect/answer/business"
            f"?session_id={session_id}&attempt_phone={business_phone}"
        )
        hangup_url = (
            f"https://{server_host}/api/live-connect/hangup"
            f"?session_id={session_id}&party=business&attempt_phone={business_phone}"
        )

        print(f"📞 [LIVE_CONNECT] Calling business {job.get('company')} ({business_phone}) for {job.get('title')}")
        attempt["call_initiated_at"] = time.time()

        # Make the call
        try:
            call_result = await vobiz_service.make_call(
                to_number=business_phone,
                answer_url=answer_url,
                hangup_url=hangup_url,
            )
            call_uuid = call_result.get("call_uuid") or call_result.get("request_uuid") or ""
            attempt["call_uuid"] = call_uuid
            _log_step(f"CALL_FIRED_{business_phone}", {"call_uuid": call_uuid, "company": job.get("company", "")})
            print(f"📞 [LIVE_CONNECT] Business call initiated: {call_uuid} → {business_phone}")
        except Exception as e:
            _log_step(f"CALL_FAILED_{business_phone}", {"error": str(e)})
            print(f"❌ [LIVE_CONNECT] Failed to call {business_phone}: {e}")
            attempt["outcome"] = "call_failed"
            return

        # Wait for answer (Vobiz answer webhook sets attempt["answered"])
        try:
            await asyncio.wait_for(
                attempt["answered"].wait(),
                timeout=BUSINESS_RING_TIMEOUT,
            )
        except asyncio.TimeoutError:
            print(f"⏰ [LIVE_CONNECT] {business_phone} didn't answer in {BUSINESS_RING_TIMEOUT}s")
            attempt["outcome"] = "no_answer"
            await _safe_hangup(attempt["call_uuid"])
            return

        # Check if someone already won while we were ringing
        if session.get("_winner_phone") is not None:
            print(f"🏁 [LIVE_CONNECT] {business_phone} answered but race already won")
            attempt["outcome"] = "lost_race"
            attempt["answered_at"] = time.time()
            await _safe_hangup(attempt["call_uuid"])
            return

        attempt["answered_at"] = time.time()
        print(f"✅ [LIVE_CONNECT] Business {business_phone} answered!")

        # Wait for AI pitch result: bridge_ready (won), declined, session_ended, or timeout
        bridge_task = asyncio.create_task(attempt["bridge_ready"].wait())
        decline_task = asyncio.create_task(attempt["declined"].wait())
        ended_task = asyncio.create_task(session["_session_ended"].wait())
        winner_task = asyncio.create_task(session["_winner_found"].wait())

        try:
            done, pending = await asyncio.wait_for(
                asyncio.wait(
                    [bridge_task, decline_task, ended_task, winner_task],
                    return_when=asyncio.FIRST_COMPLETED,
                ),
                timeout=90,
            )
            for t in pending:
                t.cancel()
        except asyncio.TimeoutError:
            for t in [bridge_task, decline_task, ended_task, winner_task]:
                t.cancel()
            print(f"⏰ [LIVE_CONNECT] {business_phone} AI pitch timed out after 90s")
            attempt["outcome"] = "timeout"
            attempt["pitch_ended_at"] = time.time()
            attempt["disconnect_signal"].set()
            await _safe_hangup(attempt["call_uuid"])
            return

        attempt["pitch_ended_at"] = time.time()

        # Determine outcome
        if attempt["bridge_ready"].is_set() and session.get("_winner_phone") == phone:
            attempt["outcome"] = "accepted"
            print(f"✅ [LIVE_CONNECT] Business {business_phone} accepted and won!")
        elif attempt["declined"].is_set():
            attempt["outcome"] = "declined"
            print(f"⚠️ [LIVE_CONNECT] Business {business_phone} declined")
        elif session["_winner_found"].is_set() and session.get("_winner_phone") != phone:
            attempt["outcome"] = "lost_race"
            print(f"🏁 [LIVE_CONNECT] Business {business_phone} lost race to {session.get('_winner_phone')}")
            await _safe_hangup(attempt["call_uuid"])
        elif session["_session_ended"].is_set():
            attempt["outcome"] = "session_ended"
            print(f"⚠️ [LIVE_CONNECT] Session ended during pitch to {business_phone}")
        else:
            attempt["outcome"] = "unknown"

    async def _fire_batch(batch_jobs: list[dict], batch_label: str) -> bool:
        """
        Fire a batch of calls and wait for winner or all done.
        Returns True if a winner was found or session ended (stop calling).
        """
        batch_phones = []
        for job in batch_jobs:
            phone = _init_attempt(job)
            if phone:
                batch_phones.append(phone)

        if not batch_phones:
            return False

        _log_step(f"FIRING_{batch_label}", {"count": len(batch_phones), "phones": batch_phones})
        print(f"📞 [LIVE_CONNECT] Firing {len(batch_phones)} calls ({batch_label}) for session {session_id}")

        batch_tasks = [
            asyncio.create_task(_run_attempt(phone, attempts[phone]["job"]))
            for phone in batch_phones
        ]

        winner_waiter = asyncio.create_task(session["_winner_found"].wait())

        async def _gather_batch():
            return await asyncio.gather(*batch_tasks, return_exceptions=True)

        all_done = asyncio.create_task(_gather_batch())
        session_ended = asyncio.create_task(session["_session_ended"].wait())

        _log_step(f"WAITING_{batch_label}", {"tasks_count": len(batch_tasks)})

        done, pending = await asyncio.wait(
            [winner_waiter, all_done, session_ended],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for t in pending:
            t.cancel()

        outcomes = {p: attempts[p].get("outcome", "pending") for p in batch_phones}
        _log_step(f"BATCH_DONE_{batch_label}", {
            "winner_found": session["_winner_found"].is_set(),
            "session_ended": session["_session_ended"].is_set(),
            "outcomes": outcomes,
        })

        return session["_winner_found"].is_set() or session["_session_ended"].is_set()

    # --- Fire initial batch ---
    stop = await _fire_batch(initial_batch_jobs, "INITIAL_BATCH")

    # --- Incremental batches: fire INCREMENTAL_BATCH_SIZE at a time from remaining pool ---
    batch_num = 0
    while not stop and incremental_pool:
        batch_num += 1
        next_batch = incremental_pool[:INCREMENTAL_BATCH_SIZE]
        incremental_pool = incremental_pool[INCREMENTAL_BATCH_SIZE:]
        stop = await _fire_batch(next_batch, f"INCREMENTAL_{batch_num}")

    # --- Fallback re-search with progressively relaxed criteria if pool exhausted ---
    if not stop:
        already_tried = set(attempts.keys())
        city = screening_data.get("candidate_city", "Gurgaon")
        category = screening_data.get("candidate_category", "")
        salary_min_orig = int(screening_data.get("candidate_salary_min", 0) or 0)
        resolved_cities = _resolve_cities(city)
        is_already_all_cities = set(resolved_cities) == set(ALL_CITIES)

        fallback_strategies = []
        if salary_min_orig > 0:
            fallback_strategies.append(("DROP_SALARY", city, category, 0))
        if not is_already_all_cities:
            fallback_strategies.append(("ALL_CITIES_SAME_CAT", "", category, 0))
        fallback_strategies.append(("ALL_CITIES_ALL_JOBS", "", "", 0))

        for strategy_label, fb_city, fb_category, fb_salary in fallback_strategies:
            if stop:
                break
            print(f"🔄 [LIVE_CONNECT] Fallback re-search: {strategy_label} for session {session_id}")
            fb_exclude = (exclude_phones or set()) | already_tried
            fallback_jobs = await asyncio.to_thread(
                search_matching_jobs,
                city=fb_city,
                category=fb_category,
                salary_min=fb_salary,
                limit=JOB_POOL_LIMIT,
                experience_level="",
                exclude_phones=fb_exclude,
            )
            print(f"🔄 [LIVE_CONNECT] Fallback {strategy_label}: found {len(fallback_jobs)} new jobs")
            if not fallback_jobs:
                continue

            fb_pool = fallback_jobs
            while not stop and fb_pool:
                batch_num += 1
                next_batch = fb_pool[:INCREMENTAL_BATCH_SIZE]
                fb_pool = fb_pool[INCREMENTAL_BATCH_SIZE:]
                stop = await _fire_batch(next_batch, f"FALLBACK_{strategy_label}_{batch_num}")
                already_tried.update(attempts.keys())

    # --- All batches done — resolve final outcome ---
    outcomes = {phone: attempt.get("outcome", "pending") for phone, attempt in attempts.items()}
    _log_step("RACE_FINISHED", {
        "winner_found": session["_winner_found"].is_set(),
        "session_ended": session["_session_ended"].is_set(),
        "total_attempts": len(attempts),
        "outcomes": outcomes,
    })

    if session["_winner_found"].is_set():
        winner_phone = session.get("_winner_phone", "")
        winner_attempt = attempts.get(winner_phone, {})
        winner_job = winner_attempt.get("job", {})

        # Update session with winner info
        session["business_phone"] = winner_phone
        session["business_name"] = winner_job.get("company", "")
        session["job_id"] = winner_job.get("job_id", "")
        session["current_job"] = winner_job

        _log_step("WINNER", {"phone": winner_phone, "company": winner_job.get("company", "")})
        print(f"🏆 [LIVE_CONNECT] Winner: {winner_phone} ({winner_job.get('company', '')})")

        # Wait briefly for remaining tasks to settle, then hang up losers
        await asyncio.sleep(2)
        for phone, attempt in attempts.items():
            if phone != winner_phone and attempt.get("call_uuid") and attempt["outcome"] not in ("no_answer", "declined", "call_failed"):
                attempt["disconnect_signal"].set()
                await _safe_hangup(attempt["call_uuid"])
                if not attempt["outcome"]:
                    attempt["outcome"] = "lost_race"

        # Update Firestore with winner (background thread — don't block event loop)
        def _save_winner():
            try:
                fs.collection("live_connect_sessions").document(session_id).update({
                    "business_phone": winner_phone,
                    "business_name": winner_job.get("company", ""),
                    "job_id": winner_job.get("job_id", ""),
                    "current_job": winner_job,
                    "winner_phone": winner_phone,
                    "winner_name": winner_job.get("company", ""),
                })
            except Exception:
                pass
        threading.Thread(target=_save_winner, daemon=True).start()

    elif session["_session_ended"].is_set():
        print(f"⚠️ [LIVE_CONNECT] Session ended during parallel business calls")
        for phone, attempt in attempts.items():
            if attempt.get("call_uuid") and not attempt["outcome"]:
                attempt["disconnect_signal"].set()
                await _safe_hangup(attempt["call_uuid"])
                attempt["outcome"] = "session_ended"
        # Still send SMS fallback — candidate and HRs can call each other directly
        if session.get("matching_jobs") and not session.get("sms_fallback_sent"):
            print(f"📱 [SMS_FALLBACK] Session ended early — sending SMS fallback for {session_id}")
            _send_fallback_sms_to_candidate(session)
            _send_fallback_sms_to_businesses(session)
            session["sms_fallback_sent"] = True
    else:
        # All batches exhausted — no winner found
        print(f"⚠️ [LIVE_CONNECT] All {len(attempts)} employers exhausted (incl. incremental) for session {session_id}")
        await handle_business_unreachable(session_id, reason="all_employers_exhausted")

    # Save attempt data to Firestore (background thread — don't block event loop)
    threading.Thread(
        target=_save_attempts_to_firestore,
        args=(session_id, attempts, "candidate_to_business"),
        daemon=True,
    ).start()

    return session


async def end_session(session_id: str, outcome: str = "completed") -> None:
    """End a live connect session and record final state to Firestore."""
    session = _sessions.get(session_id)
    if not session:
        return

    session["outcome"] = outcome
    session["bridge_ended_at"] = time.time()

    # Calculate bridge duration
    bridge_started = session.get("bridge_started_at")
    if bridge_started:
        session["bridge_duration_seconds"] = round(time.time() - bridge_started, 1)

    # Signal all waiting coroutines
    session["_session_ended"].set()

    update_session_status(session_id, LiveConnectStatus.COMPLETED)

    # Send both parties each other's details if bridge was active
    was_bridged = bridge_started is not None
    sms_sent = False
    if was_bridged:
        try:
            _send_bridge_success_sms(session)
            sms_sent = True
        except Exception as e:
            print(f"⚠️ [LIVE_CONNECT] Failed to send bridge SMS: {e}")

    # Trigger recording processing + AI analysis in background
    if was_bridged:
        candidate_audio = session.get("_recording_candidate_audio")
        business_audio = session.get("_recording_business_audio")
        has_recording = (candidate_audio and len(candidate_audio) > 0) or (
            business_audio and len(business_audio) > 0
        )
        if has_recording:
            direction = session.get("direction", "candidate_to_business")
            if direction == "business_to_candidate":
                sc_data = session.get("screening_data", {})
                job_title = sc_data.get("role_needed", "")
            else:
                job = session.get("current_job") or {}
                job_title = job.get("title", "")

            session_context = {
                "session_id": session_id,
                "candidate_name": session.get("candidate_name", "") or "",
                "candidate_phone": session.get("candidate_phone", ""),
                "business_name": session.get("business_name", "") or "",
                "business_phone": session.get("business_phone", ""),
                "job_title": job_title,
                "screening_summary": session.get("screening_summary", ""),
                "bridge_duration_seconds": session.get("bridge_duration_seconds", 0),
            }

            asyncio.create_task(
                _save_recording(
                    session_id,
                    bytes(candidate_audio) if candidate_audio else b"",
                    bytes(business_audio) if business_audio else b"",
                    session_context=session_context,
                )
            )

    # Final Firestore update (background thread — don't block event loop)
    firestore_data = {k: v for k, v in session.items() if not k.startswith("_")}
    firestore_data["status"] = LiveConnectStatus.COMPLETED.value
    firestore_data["updated_at"] = time.time()

    def _save_final():
        try:
            fs.collection("live_connect_sessions").document(session_id).set(
                firestore_data, merge=True
            )
        except Exception as e:
            print(f"⚠️ [LIVE_CONNECT] Failed to save final session state: {e}")

        # Save successful bridge as telephonic interview record
        if was_bridged:
            try:
                direction = session.get("direction", "candidate_to_business")
                candidate_phone = session.get("candidate_phone", "")
                candidate_name = session.get("candidate_name", "") or ""
                business_phone = session.get("business_phone", "")
                business_name = session.get("business_name", "") or ""

                if direction == "business_to_candidate":
                    screening_data = session.get("screening_data", {})
                    job_title = screening_data.get("role_needed", "")
                    job_city = screening_data.get("city", "")
                    company = business_name
                    salary = ""
                    requirements = screening_data.get("requirements", "")
                else:
                    job = session.get("current_job") or {}
                    job_title = job.get("title", "")
                    job_city = job.get("city", "")
                    company = job.get("company", business_name)
                    salary = job.get("salary_max", "")
                    requirements = job.get("requirements", "")

                interview_doc = {
                    "session_id": session_id,
                    "direction": direction,
                    "candidate_phone": candidate_phone,
                    "candidate_name": candidate_name,
                    "business_phone": business_phone,
                    "business_name": company,
                    "job_title": job_title,
                    "job_city": job_city,
                    "salary": salary,
                    "requirements": requirements,
                    "screening_summary": session.get("screening_summary", ""),
                    "bridge_started_at": bridge_started,
                    "bridge_ended_at": session.get("bridge_ended_at"),
                    "bridge_duration_seconds": session.get("bridge_duration_seconds"),
                    "outcome": outcome,
                    "sms_sent": sms_sent,
                    "created_at": time.time(),
                }
                rec_url = session.get("recording_url", "")
                if rec_url:
                    interview_doc["recording_url"] = rec_url
                fs.collection("telephonic_interviews").document(session_id).set(
                    interview_doc, merge=True
                )
                print(f"✅ [LIVE_CONNECT] Saved telephonic interview record for session {session_id}")
            except Exception as e:
                print(f"⚠️ [LIVE_CONNECT] Failed to save telephonic interview: {e}")

    threading.Thread(target=_save_final, daemon=True).start()

    print(f"✅ [LIVE_CONNECT] Session {session_id} ended: {outcome}")

    # Clean up in-memory session after a delay (allow pending reads)
    # Longer delay for inbound sessions to allow late-arriving candidate transfers
    cleanup_delay = 60 if session.get("inbound") else 5
    await asyncio.sleep(cleanup_delay)
    _sessions.pop(session_id, None)


async def handle_business_unreachable(session_id: str, reason: str = "no_answer") -> None:
    """Handle business not picking up or declining — fall back to SMS scheduling."""
    session = _sessions.get(session_id)
    if not session:
        return

    if reason == "declined":
        update_session_status(session_id, LiveConnectStatus.BUSINESS_DECLINED)
    elif reason == "all_employers_exhausted":
        update_session_status(session_id, LiveConnectStatus.BUSINESS_NO_ANSWER)
    elif reason == "no_matching_jobs":
        update_session_status(session_id, LiveConnectStatus.FAILED)
    else:
        update_session_status(session_id, LiveConnectStatus.BUSINESS_NO_ANSWER)

    session["outcome"] = f"Business unreachable: {reason}"

    print(f"⚠️ [LIVE_CONNECT] Business unreachable ({reason}) for session {session_id}")

    # For inbound sessions where candidate hasn't connected to LC bridge yet:
    # Keep session alive so the candidate can arrive and hear a "sorry" TTS.
    is_inbound_waiting = session.get("inbound") and not session.get("_candidate_ws_connected")

    if is_inbound_waiting:
        # Store failure reason — candidate bridge will check this on connection
        session["_businesses_exhausted"] = reason
        # Signal session ended so HOLD exits if candidate is already waiting
        session["_session_ended"].set()
        print(f"⚠️ [LIVE_CONNECT] Inbound session {session_id}: candidate not yet connected, keeping session alive (120s)")
    else:
        # Normal case: signal session ended
        session["_session_ended"].set()

    # SMS fallback: send job details to candidate + candidate details to HRs
    if reason not in ("declined", "no_matching_jobs") and not session.get("sms_fallback_sent"):
        print(f"📱 [SMS_FALLBACK] Sending SMS fallback ({reason}) for session {session_id}")
        _send_fallback_sms_to_candidate(session)
        _send_fallback_sms_to_businesses(session)
        session["sms_fallback_sent"] = True

    # Save to Firestore in background thread (avoid blocking event loop)
    firestore_data = {k: v for k, v in session.items() if not k.startswith("_")}
    firestore_data["updated_at"] = time.time()
    sms_will_send = reason not in ("declined", "no_matching_jobs") and not session.get("sms_fallback_sent")

    def _write_firestore():
        try:
            fs.collection("debug_webhooks").document("last_sms_decision").set({
                "session_id": session_id,
                "reason": reason,
                "candidate_phone": session.get("candidate_phone", ""),
                "matching_jobs_count": len(session.get("matching_jobs") or []),
                "sms_fallback_sent_already": session.get("sms_fallback_sent", False),
                "will_send": sms_will_send,
                "time": time.time(),
            })
        except Exception as e:
            print(f"⚠️ [LIVE_CONNECT] Failed to save SMS decision debug: {e}")
        try:
            fs.collection("live_connect_sessions").document(session_id).set(
                firestore_data, merge=True
            )
        except Exception as e:
            print(f"⚠️ [LIVE_CONNECT] Failed to save session: {e}")

    threading.Thread(target=_write_firestore, daemon=True).start()

    # Clean up after delay — longer for inbound waiting (candidate may still arrive)
    cleanup_delay = 120 if is_inbound_waiting else 5
    await asyncio.sleep(cleanup_delay)

    # For inbound waiting: re-check if candidate connected during the wait
    if is_inbound_waiting and session.get("_candidate_ws_connected"):
        print(f"⚠️ [LIVE_CONNECT] Candidate connected during cleanup wait for {session_id}, letting bridge handle cleanup")
        return

    _sessions.pop(session_id, None)


# ============================================================================
# Reverse flow: business→candidate
# ============================================================================


async def create_inbound_business_session(
    business_phone: str,
    business_name: str = "",
    business_call_uuid: str = "",
    test_candidate_phone: str = "",
) -> dict:
    """
    Create a live connect session for an inbound business caller (already on the phone).

    Unlike create_inbound_session(), the BUSINESS is the inbound caller.
    Direction is reversed: we search for candidates and call them.
    Sets _business_screening_done immediately since screening happened on the inbound call.
    """
    session_id = f"lc_{uuid.uuid4().hex[:12]}"
    business_phone = _normalize_phone(business_phone)

    session = LiveConnectSession(
        id=session_id,
        candidate_id="",
        candidate_phone="",
        business_phone=business_phone,
        business_name=business_name,
        status=LiveConnectStatus.BUSINESS_HOLD,
    )
    session_dict = session.model_dump()

    # Add asyncio signaling events
    session_dict["_candidate_bridge_ready"] = asyncio.Event()
    session_dict["_session_ended"] = asyncio.Event()
    session_dict["_business_screening_done"] = True
    session_dict["_test_candidate_phone"] = _normalize_phone(test_candidate_phone) if test_candidate_phone else ""
    session_dict["_candidate_vobiz_ws"] = None
    session_dict["_business_vobiz_ws"] = None
    session_dict["_candidate_stream_id"] = None
    session_dict["_business_stream_id"] = None
    session_dict["business_call_uuid"] = business_call_uuid
    session_dict["direction"] = "business_to_candidate"
    session_dict["inbound"] = True

    # Parallel calling state
    session_dict["_attempts"] = {}
    session_dict["_winner_phone"] = None
    session_dict["_winner_found"] = asyncio.Event()

    _sessions[session_id] = session_dict

    # Save to Firestore (without internal fields)
    firestore_data = {k: v for k, v in session_dict.items() if not k.startswith("_")}
    fs.collection("live_connect_sessions").document(session_id).set(firestore_data)

    print(f"📞 [LIVE_CONNECT] Inbound business session {session_id} created for {business_phone} (already on call)")

    # Schedule TTL watchdog
    asyncio.create_task(_session_ttl_watchdog(session_id))

    return session_dict


# Role aliases for matching candidates to business requirements
ROLE_ALIASES: dict[str, list[str]] = {
    "waiter": ["waiter", "server", "steward", "f&b", "captain"],
    "helper": ["helper", "assistant", "support"],
    "sales": ["sales", "retail", "shop", "counter"],
    "kitchen": ["kitchen", "cook", "chef", "cooking"],
    "delivery": ["delivery", "driver", "courier"],
    "security": ["security", "guard", "watchman"],
    "housekeeping": ["cleaner", "safai", "housekeeping", "office boy"],
}

# NCR area aliases for location matching
NCR_AREAS: dict[str, list[str]] = {
    "delhi": ["delhi", "new delhi", "ncr"],
    "noida": ["noida", "greater noida", "ncr"],
    "gurgaon": ["gurgaon", "gurugram", "ncr"],
    "ghaziabad": ["ghaziabad", "ncr"],
    "faridabad": ["faridabad", "ncr"],
}


def _matches_role(candidate_roles: list[str], job_role: str) -> bool:
    """Check if candidate's preferred roles match the required role."""
    if not candidate_roles:
        return True

    job_role_lower = job_role.lower()

    job_aliases = set()
    for key, aliases in ROLE_ALIASES.items():
        if any(alias in job_role_lower for alias in aliases):
            job_aliases.update(aliases)
    if not job_aliases:
        job_aliases = {job_role_lower}

    for preferred in candidate_roles:
        preferred_lower = preferred.lower()
        if job_role_lower in preferred_lower or preferred_lower in job_role_lower:
            return True
        if any(alias in preferred_lower for alias in job_aliases):
            return True

    return False


def _matches_location(candidate_area: str, job_city: str) -> bool:
    """Check if candidate's area matches job city (NCR-aware)."""
    if not candidate_area or not job_city:
        return True

    candidate_lower = candidate_area.lower()
    job_lower = job_city.lower()

    if job_lower in candidate_lower or candidate_lower in job_lower:
        return True

    job_in_ncr = any(alias in job_lower for aliases in NCR_AREAS.values() for alias in aliases)
    candidate_in_ncr = any(alias in candidate_lower for aliases in NCR_AREAS.values() for alias in aliases)

    if job_in_ncr and candidate_in_ncr:
        return True

    return False


def search_matching_candidates(
    role: str,
    city: str,
    salary_max: int = 0,
    limit: int = 20,
) -> list[dict]:
    """
    Search Firestore switch_users collection for matching candidates.
    Filters by role, location, and availability.
    Returns list of dicts: {phone, name, area, experience, preferred_roles, photo_url}.
    """
    print(f"🔍 [LIVE_CONNECT] Searching candidates: role={role}, city={city}, salary_max={salary_max}")

    all_candidates = []
    try:
        docs = list(fs.collection("switch_users").stream())
        print(f"🔍 [LIVE_CONNECT] Total switch_users: {len(docs)}")

        for doc in docs:
            user_data = doc.to_dict()
            profile = user_data.get("profile", {}) or {}

            # Must be available
            if not profile.get("isAvailable", False):
                continue

            # Must have name
            name = profile.get("name") or user_data.get("name") or ""
            if not name:
                continue

            # Resolve fields with multi-field fallbacks
            photo_url = (
                profile.get("photoURL") or profile.get("photo_url")
                or profile.get("profilePhoto") or profile.get("imageUrl")
                or user_data.get("photoURL") or ""
            )
            area = (
                profile.get("location") or profile.get("area")
                or profile.get("city") or profile.get("currentLocation")
                or user_data.get("location") or ""
            )
            experience = (
                profile.get("experience") or profile.get("experienceLevel")
                or profile.get("workExperience") or profile.get("totalExperience")
                or user_data.get("experience") or ""
            )
            preferred_roles = profile.get("preferredRoles") or profile.get("preferred_roles") or []
            phone = doc.id

            # Filter by role
            if not _matches_role(preferred_roles, role):
                continue

            # Filter by location
            if not _matches_location(area, city):
                continue

            all_candidates.append({
                "phone": phone,
                "name": name,
                "area": area,
                "experience": experience,
                "preferred_roles": preferred_roles,
                "photo_url": photo_url,
            })

    except Exception as e:
        print(f"❌ [LIVE_CONNECT] Error searching candidates: {e}")
        return []

    # Sort: has photo → has experience → name
    all_candidates.sort(key=lambda c: (
        bool(c.get("photo_url")),
        bool(c.get("experience")),
        c.get("name", ""),
    ), reverse=True)

    results = all_candidates[:limit]
    print(f"🔍 [LIVE_CONNECT] Found {len(all_candidates)} matching candidates, returning top {len(results)}")
    for i, cand in enumerate(results):
        print(f"  #{i+1}: {cand['name']} — {cand['area']} — {cand['experience']} — {cand['phone']}")

    return results


# ============================================================================
# Parallel candidate calling (business→candidate flow)
# ============================================================================


async def call_candidates(session_id: str, screening_data: dict) -> dict:
    """
    Called when business screening is complete. Searches for matching candidates
    and calls ALL of them in parallel. First to accept wins.
    """
    try:
        return await _call_candidates_inner(session_id, screening_data)
    except Exception as e:
        print(f"❌ [LIVE_CONNECT] call_candidates CRASHED: {type(e).__name__}: {e}")
        traceback.print_exc()
        try:
            fs.collection("live_connect_sessions").document(session_id).update({
                "call_candidates_error": f"{type(e).__name__}: {e}",
                "call_candidates_error_at": time.time(),
            })
        except Exception:
            pass
        session = _sessions.get(session_id)
        if session:
            await handle_candidate_unreachable(session_id, reason=f"call_candidates_crash: {e}")
        return session or {"error": str(e)}


async def _call_candidates_inner(session_id: str, screening_data: dict) -> dict:
    """Inner implementation of call_candidates with full error propagation."""
    debug_ref = fs.collection("debug_webhooks").document(f"parallel_calls_rev_{session_id}")
    debug_log = {"session_id": session_id, "direction": "business_to_candidate", "started_at": time.time(), "steps": []}

    def _log_step(step: str, data: dict = None):
        entry = {"step": step, "time": time.time()}
        if data:
            entry.update(data)
        debug_log["steps"].append(entry)
        debug_ref.set(debug_log)
        print(f"📊 [PARALLEL_DEBUG_REV] [{session_id}] {step}: {data or ''}")

    session = _sessions.get(session_id)
    if not session:
        _log_step("SESSION_NOT_FOUND")
        return {"error": "Session not found"}

    _log_step("SESSION_FOUND", {"business_phone": session.get("business_phone", "")})

    session["screening_data"] = screening_data
    update_session_status(session_id, LiveConnectStatus.CALLING_CANDIDATES)

    role = screening_data.get("role_needed", "")
    city = screening_data.get("city", "Gurgaon")
    salary_max = int(screening_data.get("salary_max", 0) or 0)

    _log_step("SEARCHING_CANDIDATES", {"role": role, "city": city, "salary_max": salary_max})

    # Test override: use specific candidate phone instead of searching
    test_phone = session.get("_test_candidate_phone", "")
    if test_phone:
        print(f"🧪 [LIVE_CONNECT] TEST MODE: using override candidate phone {test_phone}")
        matching_candidates = [{
            "phone": test_phone,
            "name": "Test Candidate",
            "area": city,
            "experience": "",
            "preferred_roles": [],
            "photo_url": "",
        }]
    else:
        matching_candidates = search_matching_candidates(
            role=role,
            city=city,
            salary_max=salary_max,
            limit=MAX_PARALLEL_CALLS,
        )

    _log_step("SEARCH_DONE", {
        "candidates_found": len(matching_candidates),
        "phones": [c.get("phone", "") for c in matching_candidates[:5]],
    })

    if not matching_candidates:
        _log_step("NO_MATCHING_CANDIDATES")
        print(f"⚠️ [LIVE_CONNECT] No matching candidates found for session {session_id}")
        session["outcome"] = "No matching candidates found"
        await handle_candidate_unreachable(session_id, reason="no_matching_candidates")
        return session

    session["matching_candidates"] = matching_candidates

    # Save to Firestore
    try:
        fs.collection("live_connect_sessions").document(session_id).update({
            "screening_data": screening_data,
            "matching_candidates": matching_candidates,
        })
    except Exception as e:
        print(f"⚠️ [LIVE_CONNECT] Failed to save matching candidates: {e}")

    # Initialize per-attempt tracking
    attempts = {}
    for candidate in matching_candidates:
        phone = _normalize_phone(candidate.get("phone", ""))
        if not phone:
            continue
        attempts[phone] = {
            "answered": asyncio.Event(),
            "bridge_ready": asyncio.Event(),
            "declined": asyncio.Event(),
            "disconnect_signal": asyncio.Event(),
            "accepted": None,
            "call_uuid": "",
            "stream_id": "",
            "vobiz_ws": None,
            "conversation_id": "",
            "candidate": candidate,
            "name": candidate.get("name", ""),
            "call_initiated_at": None,
            "answered_at": None,
            "pitch_ended_at": None,
            "outcome": "",
        }

    session["_attempts"] = attempts
    session["_winner_phone"] = None
    session["_winner_found"] = asyncio.Event()

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")

    _log_step("FIRING_CALLS", {"count": len(attempts), "phones": list(attempts.keys())})
    print(f"📞 [LIVE_CONNECT] Firing {len(attempts)} parallel candidate calls for session {session_id}")

    async def _run_attempt(phone: str, candidate: dict) -> None:
        """Run a single candidate call attempt."""
        attempt = attempts[phone]
        candidate_phone = phone

        answer_url = (
            f"https://{server_host}/api/live-connect/answer/reverse-candidate"
            f"?session_id={session_id}&attempt_phone={candidate_phone}"
        )
        hangup_url = (
            f"https://{server_host}/api/live-connect/hangup"
            f"?session_id={session_id}&party=candidate&attempt_phone={candidate_phone}"
        )

        print(f"📞 [LIVE_CONNECT] Calling candidate {candidate.get('name')} ({candidate_phone})")
        attempt["call_initiated_at"] = time.time()

        # Make the call
        try:
            call_result = await vobiz_service.make_call(
                to_number=candidate_phone,
                answer_url=answer_url,
                hangup_url=hangup_url,
            )
            call_uuid = call_result.get("call_uuid") or call_result.get("request_uuid") or ""
            attempt["call_uuid"] = call_uuid
            _log_step(f"CALL_FIRED_{candidate_phone}", {"call_uuid": call_uuid, "name": candidate.get("name", "")})
            print(f"📞 [LIVE_CONNECT] Candidate call initiated: {call_uuid} → {candidate_phone}")
        except Exception as e:
            _log_step(f"CALL_FAILED_{candidate_phone}", {"error": str(e)})
            print(f"❌ [LIVE_CONNECT] Failed to call {candidate_phone}: {e}")
            attempt["outcome"] = "call_failed"
            return

        # Wait for answer
        try:
            await asyncio.wait_for(
                attempt["answered"].wait(),
                timeout=CANDIDATE_RING_TIMEOUT,
            )
        except asyncio.TimeoutError:
            print(f"⏰ [LIVE_CONNECT] {candidate_phone} didn't answer in {CANDIDATE_RING_TIMEOUT}s")
            attempt["outcome"] = "no_answer"
            await _safe_hangup(attempt["call_uuid"])
            return

        # Check if someone already won while we were ringing
        if session.get("_winner_phone") is not None:
            print(f"🏁 [LIVE_CONNECT] {candidate_phone} answered but race already won")
            attempt["outcome"] = "lost_race"
            attempt["answered_at"] = time.time()
            await _safe_hangup(attempt["call_uuid"])
            return

        attempt["answered_at"] = time.time()
        print(f"✅ [LIVE_CONNECT] Candidate {candidate_phone} answered!")

        # Wait for AI pitch result
        bridge_task = asyncio.create_task(attempt["bridge_ready"].wait())
        decline_task = asyncio.create_task(attempt["declined"].wait())
        ended_task = asyncio.create_task(session["_session_ended"].wait())
        winner_task = asyncio.create_task(session["_winner_found"].wait())

        try:
            done, pending = await asyncio.wait_for(
                asyncio.wait(
                    [bridge_task, decline_task, ended_task, winner_task],
                    return_when=asyncio.FIRST_COMPLETED,
                ),
                timeout=90,
            )
            for t in pending:
                t.cancel()
        except asyncio.TimeoutError:
            for t in [bridge_task, decline_task, ended_task, winner_task]:
                t.cancel()
            print(f"⏰ [LIVE_CONNECT] {candidate_phone} AI pitch timed out after 90s")
            attempt["outcome"] = "timeout"
            attempt["pitch_ended_at"] = time.time()
            attempt["disconnect_signal"].set()
            await _safe_hangup(attempt["call_uuid"])
            return

        attempt["pitch_ended_at"] = time.time()

        # Determine outcome
        if attempt["bridge_ready"].is_set() and session.get("_winner_phone") == phone:
            attempt["outcome"] = "accepted"
            print(f"✅ [LIVE_CONNECT] Candidate {candidate_phone} accepted and won!")
        elif attempt["declined"].is_set():
            attempt["outcome"] = "declined"
            print(f"⚠️ [LIVE_CONNECT] Candidate {candidate_phone} declined")
        elif session["_winner_found"].is_set() and session.get("_winner_phone") != phone:
            attempt["outcome"] = "lost_race"
            print(f"🏁 [LIVE_CONNECT] Candidate {candidate_phone} lost race")
            await _safe_hangup(attempt["call_uuid"])
        elif session["_session_ended"].is_set():
            attempt["outcome"] = "session_ended"
        else:
            attempt["outcome"] = "unknown"

    # Fire all calls in parallel
    tasks = [
        asyncio.create_task(_run_attempt(phone, attempts[phone]["candidate"]))
        for phone in attempts
    ]

    # Wait for either a winner or all attempts to complete
    winner_waiter = asyncio.create_task(session["_winner_found"].wait())

    async def _gather_all():
        return await asyncio.gather(*tasks, return_exceptions=True)

    all_done = asyncio.create_task(_gather_all())
    session_ended = asyncio.create_task(session["_session_ended"].wait())

    _log_step("WAITING_FOR_RESULT", {"tasks_count": len(tasks)})

    done, pending = await asyncio.wait(
        [winner_waiter, all_done, session_ended],
        return_when=asyncio.FIRST_COMPLETED,
    )

    outcomes = {phone: attempt.get("outcome", "pending") for phone, attempt in attempts.items()}
    _log_step("RACE_FINISHED", {
        "winner_found": session["_winner_found"].is_set(),
        "session_ended": session["_session_ended"].is_set(),
        "outcomes": outcomes,
    })

    if session["_winner_found"].is_set():
        winner_phone = session.get("_winner_phone", "")
        winner_attempt = attempts.get(winner_phone, {})
        winner_candidate = winner_attempt.get("candidate", {})

        # Update session with winner info
        session["candidate_phone"] = winner_phone
        session["candidate_name"] = winner_candidate.get("name", "")
        session["current_candidate"] = winner_candidate

        _log_step("WINNER", {"phone": winner_phone, "name": winner_candidate.get("name", "")})
        print(f"🏆 [LIVE_CONNECT] Winner: {winner_phone} ({winner_candidate.get('name', '')})")

        # Wait briefly for remaining tasks to settle, then hang up losers
        await asyncio.sleep(2)
        for phone, attempt in attempts.items():
            if phone != winner_phone and attempt.get("call_uuid") and attempt["outcome"] not in ("no_answer", "declined", "call_failed"):
                attempt["disconnect_signal"].set()
                await _safe_hangup(attempt["call_uuid"])
                if not attempt["outcome"]:
                    attempt["outcome"] = "lost_race"

        # Update Firestore with winner
        try:
            fs.collection("live_connect_sessions").document(session_id).update({
                "candidate_phone": winner_phone,
                "candidate_name": winner_candidate.get("name", ""),
                "current_candidate": winner_candidate,
                "winner_phone": winner_phone,
                "winner_name": winner_candidate.get("name", ""),
            })
        except Exception:
            pass

    elif session["_session_ended"].is_set():
        print(f"⚠️ [LIVE_CONNECT] Session ended during parallel candidate calls")
        for t in pending:
            t.cancel()
        for phone, attempt in attempts.items():
            if attempt.get("call_uuid") and not attempt["outcome"]:
                attempt["disconnect_signal"].set()
                await _safe_hangup(attempt["call_uuid"])
                attempt["outcome"] = "session_ended"
        # Still send SMS fallback — business and candidates can call each other directly
        if session.get("matching_candidates") and not session.get("sms_fallback_sent"):
            print(f"📱 [SMS_FALLBACK] Session ended early — sending SMS fallback for {session_id}")
            _send_fallback_sms_to_business_caller(session)
            _send_fallback_sms_to_candidates(session)
            session["sms_fallback_sent"] = True
    else:
        # all_done completed — no winner found
        print(f"⚠️ [LIVE_CONNECT] All {len(attempts)} candidates exhausted for session {session_id}")
        await handle_candidate_unreachable(session_id, reason="all_candidates_exhausted")

    # Cancel remaining watchers
    for t in pending:
        t.cancel()

    # Save attempt data to Firestore
    _save_attempts_to_firestore(session_id, attempts, direction="business_to_candidate")

    return session


async def handle_candidate_unreachable(session_id: str, reason: str = "no_answer") -> None:
    """Handle candidate not picking up or declining — signal session ended."""
    session = _sessions.get(session_id)
    if not session:
        return

    if reason == "declined":
        update_session_status(session_id, LiveConnectStatus.CANDIDATE_DECLINED)
    elif reason == "all_candidates_exhausted":
        update_session_status(session_id, LiveConnectStatus.CANDIDATE_NO_ANSWER)
    elif reason == "no_matching_candidates":
        update_session_status(session_id, LiveConnectStatus.FAILED)
    else:
        update_session_status(session_id, LiveConnectStatus.CANDIDATE_NO_ANSWER)

    session["outcome"] = f"Candidate unreachable: {reason}"

    # Signal session ended so business bridge can resume
    session["_session_ended"].set()

    print(f"⚠️ [LIVE_CONNECT] Candidate unreachable ({reason}) for session {session_id}")

    # SMS fallback: send candidate details to business + business details to candidates
    if reason not in ("declined", "no_matching_candidates") and not session.get("sms_fallback_sent"):
        print(f"📱 [SMS_FALLBACK] Sending SMS fallback ({reason}) for session {session_id}")
        _send_fallback_sms_to_business_caller(session)
        _send_fallback_sms_to_candidates(session)
        session["sms_fallback_sent"] = True

    # Save to Firestore
    firestore_data = {k: v for k, v in session.items() if not k.startswith("_")}
    firestore_data["updated_at"] = time.time()
    try:
        fs.collection("live_connect_sessions").document(session_id).set(
            firestore_data, merge=True
        )
    except Exception as e:
        print(f"⚠️ [LIVE_CONNECT] Failed to save session: {e}")

    # Clean up after delay
    await asyncio.sleep(5)
    _sessions.pop(session_id, None)


async def _session_ttl_watchdog(session_id: str) -> None:
    """Force-end session after MAX_SESSION_TTL to prevent resource leaks."""
    try:
        await asyncio.sleep(MAX_SESSION_TTL)
        session = _sessions.get(session_id)
        if session and session.get("status") != LiveConnectStatus.COMPLETED.value:
            print(f"⏰ [LIVE_CONNECT] Session {session_id} exceeded TTL, force-ending")
            await end_session(session_id, outcome="ttl_expired")
    except asyncio.CancelledError:
        pass
