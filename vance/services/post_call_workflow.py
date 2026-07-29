"""
Post-call workflow orchestrator.

Handles all post-call processing in a clean, step-by-step manner.
This replaces the monolithic _handle_post_call_webhook() function
with a structured workflow that's easier to debug, test, and extend.

Usage:
    workflow = PostCallWorkflow()
    result = await workflow.run(payload)
"""

import base64
import io
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests

from services import claude_profile_service
from services.founder_referral_service import founder_referral_service
from services.hybrid_matching_service import MatchedProfile, hybrid_matching_service
from services.interview_scheduling_service import notify_candidate_profile_presented
from services.profile_audio_service import profile_audio_service
from services.compensation_insight_service import compensation_insight_service
from utils.db import fs, get_extraction_data, get_user_profile
from utils.qdrant import Search
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


@dataclass
class PostCallContext:
    """Shared context passed through all workflow steps."""

    uid: str
    payload: dict
    user_profile: Optional[dict] = None
    extraction_data: Optional[dict] = None
    user_name: str = ""
    user_email: str = ""
    linkedin_url: str = ""
    should_send_profiles: bool = False
    decision_reason: str = ""
    matched_profiles: Optional[List[MatchedProfile]] = None
    errors: List[Tuple[str, str]] = field(default_factory=list)
    step_timings: Dict[str, float] = field(default_factory=dict)


class PostCallWorkflow:
    """
    Orchestrates post-call processing with clear steps:

    1. identify_user     - Extract and validate user ID from payload
    2. load_user_data    - Load user profile and extraction data
    3. save_call_memory  - Save call transcript and metadata
    4. store_extraction  - Store to Firestore + Qdrant
    5. send_referrals    - Send referral messages (first-time only)
    6. decide_profiles   - Decide if user should receive candidate profiles
    7. find_matches      - Find matching candidates using hybrid search
    8. send_profiles     - Send matched profiles via WhatsApp

    Each step returns bool indicating whether to continue to next step.
    """

    def __init__(self):
        self.sender = WhatsAppSender()

        # Map step names directly to handler functions
        # Note: send_profile_to_candidate is now handled directly in webhook handler
        # but kept here as backup/fallback
        self.steps = [
            ("identify_user", self._step_identify_user),
            ("load_user_data", self._step_load_user_data),
            ("save_call_memory", self._step_save_call_memory),
            ("attach_profile_audio", self._step_attach_profile_audio),
            ("store_extraction", self._step_store_extraction),
            # New: send compensation insight card for compensation-focused job seekers
            ("send_compensation_insight", self._step_send_compensation_insight),
            # Profile link sending moved to webhook handler for reliability
            # ("send_profile_to_candidate", self._step_send_profile_to_candidate),
            ("decide_profiles", self._step_decide_send_profiles),
            ("find_matches", self._step_find_matches),
            ("send_profiles", self._step_send_profiles),
            # Send referrals AFTER profiles are sent (only if profiles were successfully sent)
            ("send_referrals", self._step_send_referrals),
        ]

    async def run(self, payload: dict) -> PostCallContext:
        """Execute the full post-call workflow."""
        ctx = PostCallContext(uid="", payload=payload)

        print(f"🔍 [POSTCALL] Payload keys: {list(payload.keys())}")

        total_steps = len(self.steps)
        for i, (step_name, step_fn) in enumerate(self.steps, 1):
            step_start = time.time()

            try:
                print(f"[POSTCALL] Step {i}/{total_steps}: {step_name}...")
                should_continue = await step_fn(ctx)
                elapsed = time.time() - step_start
                ctx.step_timings[step_name] = elapsed

                if should_continue:
                    print(
                        f"[POSTCALL] Step {i}/{total_steps}: {step_name} ✓ ({elapsed:.2f}s)"
                    )
                else:
                    print(
                        f"[POSTCALL] Step {i}/{total_steps}: {step_name} → stopped ({elapsed:.2f}s)"
                    )
                    break

            except Exception as e:
                elapsed = time.time() - step_start
                ctx.step_timings[step_name] = elapsed
                ctx.errors.append((step_name, str(e)))
                print(
                    f"[POSTCALL] Step {i}/{total_steps}: {step_name} ✗ ({elapsed:.2f}s) - {e}"
                )

                # Critical steps that should stop the workflow on failure
                critical_steps = {"identify_user", "load_user_data", "find_matches"}
                if step_name in critical_steps:
                    break
                # Non-critical steps: log error but continue

        return ctx

    # =========================================================================
    # WORKFLOW STEPS
    # =========================================================================

    async def _step_identify_user(self, ctx: PostCallContext) -> bool:
        """Extract and validate user ID from payload."""
        payload = ctx.payload

        # Try multiple locations for user_id
        uid = payload.get("data", {}).get("user_id") or payload.get("user_id")

        # Handle "default" user_id edge case
        if uid == "default":
            dyn = payload.get("conversation_initiation_client_data", {}).get(
                "dynamic_variables", {}
            )
            actual = dyn.get("user_id")
            if actual and actual != "default":
                print(f"⚠️ [FIX] default → {actual}")
                uid = actual

        # Validate
        if not uid or uid == "default" or len(uid) < 5:
            print(f"❌ [POSTCALL] Invalid user_id: {uid}")
            return False

        ctx.uid = uid
        print(f"👤 [USER] Processing post-call for {uid}")
        return True

    async def _step_load_user_data(self, ctx: PostCallContext) -> bool:
        """Load user profile and extraction data from Firestore."""
        ctx.user_profile = get_user_profile(ctx.uid)
        ctx.extraction_data = get_extraction_data(ctx.uid)

        if not ctx.extraction_data:
            print(f"❌ [POSTCALL] No extraction data for {ctx.uid}")
            return False

        # Extract common fields
        if ctx.user_profile:
            ctx.user_name = ctx.user_profile.get("name", "")
            ctx.user_email = ctx.user_profile.get("email", "")
            ln = ctx.user_profile.get("linkedin", "")
            ctx.linkedin_url = str(
                ln.get("linkedin_url") if isinstance(ln, dict) else ln
            )

        print(f"📦 [EXTRACTION] Loaded {len(ctx.extraction_data)} fields")
        return True

    async def _step_save_call_memory(self, ctx: PostCallContext) -> bool:
        """Save call transcript and metadata to call memory."""
        from api.whatsapp_modules.call_memory import call_memory

        payload = ctx.payload or {}
        data = payload.get("data", {}) or {}

        # Prefer explicit IDs from nested data (post_call_transcription/post_call_audio)
        conversation_id = data.get("conversation_id") or payload.get("conversation_id")
        
        # If conversation_id is missing, try to fetch from ElevenLabs API using user phone
        if not conversation_id or not conversation_id.strip():
            print(f"⚠️ [CALL_MEMORY] conversation_id missing from webhook payload, attempting to find from ElevenLabs...")
            try:
                from services.profile_audio_service import profile_audio_service
                from utils.db import get_user_profile
                
                user_profile = get_user_profile(ctx.uid) or {}
                user_phone = (
                    user_profile.get("wa_id")
                    or user_profile.get("phone")
                    or ctx.uid
                )
                
                # List conversations from ElevenLabs
                conversation_ids = await profile_audio_service._list_conversations_by_user(str(user_phone))
                if conversation_ids:
                    # Use the most recent conversation_id
                    conversation_id = conversation_ids[0]
                    print(f"✅ [CALL_MEMORY] Found conversation_id from ElevenLabs: {conversation_id}")
                else:
                    print(f"⚠️ [CALL_MEMORY] No conversations found in ElevenLabs for {user_phone}")
            except Exception as e:
                print(f"⚠️ [CALL_MEMORY] Error fetching conversation_id from ElevenLabs: {e}")
        
        call_id = payload.get("call_id") or conversation_id

        duration = payload.get("duration") or data.get("duration") or 0

        transcript = (
            payload.get("transcript")
            or payload.get("conversation_transcript")
            or data.get("transcript")
            or ""
        )

        agent_messages = payload.get("agent_messages") or data.get("agent_messages") or []
        user_messages = payload.get("user_messages") or data.get("user_messages") or []
        key_insights = payload.get("key_insights") or data.get("key_insights") or {}

        call_data = {
            "call_id": call_id,
            "conversation_id": conversation_id or call_id,
            "duration": duration,
            "transcript": transcript,
            "agent_messages": agent_messages,
            "user_messages": user_messages,
            "key_insights": key_insights,
            "extraction_data": ctx.extraction_data,
        }

        await call_memory.save_complete_call_log(ctx.uid, call_data)
        print(f"🧠 [CALL_MEMORY] Saved call log for {ctx.uid}")
        return True

    async def _step_attach_profile_audio(self, ctx: PostCallContext) -> bool:
        """
        Attach ElevenLabs call recording URL to the user's profile if present.

        This is a best-effort, non-critical step. It will not stop the workflow on failure.
        """
        try:
            # Try to get conversation_id from payload, or from the call we just saved
            payload = ctx.payload or {}
            data = payload.get("data", {}) or {}
            conversation_id = data.get("conversation_id") or payload.get("conversation_id")
            
            # If conversation_id is missing, try to get it from the most recent call
            if not conversation_id:
                print(f"🔍 [PROFILE_AUDIO] No conversation_id in payload, checking saved call memory...")
                try:
                    from firebase_admin import firestore
                    calls_ref = fs.collection("user_calls").document(ctx.uid).collection("calls")
                    # Get the most recent call (should be the one we just saved)
                    calls = list(calls_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream())
                    if calls:
                        recent_call = calls[0].to_dict() or {}
                        conversation_id = recent_call.get("conversation_id")
                        if conversation_id:
                            print(f"✅ [PROFILE_AUDIO] Found conversation_id from call memory: {conversation_id}")
                            # Update payload with conversation_id for audio service
                            if "data" not in payload:
                                payload["data"] = {}
                            payload["data"]["conversation_id"] = conversation_id
                except Exception as e:
                    print(f"⚠️ [PROFILE_AUDIO] Could not retrieve conversation_id from call memory: {e}")
            
            await profile_audio_service.attach_call_recording_to_profile(
                user_id=ctx.uid,
                payload=payload,
            )
        except Exception as e:
            print(f"⚠️ [PROFILE_AUDIO] Error attaching recording for {ctx.uid}: {e}")
            import traceback
            traceback.print_exc()

        # Always continue – this should never block the rest of the workflow
        return True

    async def _step_store_extraction(self, ctx: PostCallContext) -> bool:
        """Store extraction data to Firestore and Qdrant."""
        try:
            # For job seekers/candidates, ensure full profile is created with slug
            user_profile = get_user_profile(ctx.uid) or {}
            user_type = user_profile.get("profile", {}).get("user_type", "general")
            
            if user_type in {"job_seeker", "candidate"}:
                # Use voice_extraction_service to create complete profile with slug
                from services.voice_extraction_service import voice_extraction_service
                try:
                    voice_extraction_service._sync_job_seeker_profile(
                        user_id=ctx.uid,
                        extraction_data=ctx.extraction_data
                    )
                    print(f"✅ [STORAGE] Created complete profile with slug for {ctx.uid}")
                except Exception as e:
                    print(f"⚠️ [STORAGE] Failed to sync job seeker profile: {e}")
                    # Fallback to basic storage
                    fs.collection("user_profiles").document(ctx.uid).set(
                        {
                            "name": ctx.user_name,
                            "email": ctx.user_email,
                            "linkedin_url": ctx.linkedin_url,
                            "extraction_data": ctx.extraction_data,
                            "updated_at": time.time(),
                        },
                        merge=True,
                    )
            else:
                # For other user types, just store basic data
                fs.collection("user_profiles").document(ctx.uid).set(
                    {
                        "name": ctx.user_name,
                        "email": ctx.user_email,
                        "linkedin_url": ctx.linkedin_url,
                        "extraction_data": ctx.extraction_data,
                        "updated_at": time.time(),
                    },
                    merge=True,
                )

            # Qdrant
            Search("UserProfiles").add(
                user_id=ctx.uid,
                datalist=[
                    {
                        "id": uuid.uuid4().hex,
                        "extraction_data": ctx.extraction_data,
                        "metadata": {
                            "name": ctx.user_name,
                            "email": ctx.user_email,
                        },
                    }
                ],
            )

            print(f"💾 [STORAGE] Stored extraction in Firestore + Qdrant")
            
            # Check if this call was initiated from a profile intro request
            # If so, automatically send intro request after call completes
            try:
                call_tracking_doc = fs.collection("profile_intro_calls").document(ctx.uid).get()
                if call_tracking_doc.exists:
                    call_tracking = call_tracking_doc.to_dict() or {}
                    candidate_user_id = call_tracking.get("candidate_user_id")
                    candidate_name = call_tracking.get("candidate_name", "the candidate")
                    
                    if candidate_user_id and not call_tracking.get("intro_requested"):
                        # Auto-send intro request
                        from utils.whatsapp.whatsapp import WhatsAppSender
                        from utils.whatsapp.components import MsgComponents
                        
                        requester_name = call_tracking.get("requester_name") or ctx.user_name or user_profile.get("name", "Someone")
                        requester_linkedin = call_tracking.get("requester_linkedin") or user_profile.get("linkedin_url") or user_profile.get("linkedin") or ""
                        
                        # Get candidate's WhatsApp ID
                        candidate_profile_data = get_user_profile(candidate_user_id) or {}
                        candidate_wa_id = (
                            candidate_profile_data.get("wa_id")
                            or candidate_profile_data.get("phone")
                            or candidate_profile_data.get("whatsapp")
                            or candidate_user_id
                        )
                        
                        # Format message: "Name, LinkedIn, has requested intro. Do you want to connect?"
                        if requester_linkedin:
                            intro_message = f"{requester_name}, {requester_linkedin}, has requested intro. Do you want to connect?"
                        else:
                            intro_message = f"{requester_name} has requested intro. Do you want to connect?"
                        
                        sender = WhatsAppSender()
                        payload = MsgComponents.text_scaffold(to=candidate_wa_id, text=intro_message)
                        sender.send(data=payload)
                        
                        # Save intro request
                        intro_request = {
                            "requester_uid": ctx.uid,
                            "requester_name": requester_name,
                            "candidate_uid": candidate_user_id,
                            "candidate_name": candidate_name,
                            "status": "pending",
                            "requested_at": time.time(),
                            "source": "profile_page",
                        }
                        fs.collection("intro_requests").add(intro_request)
                        
                        # Update call tracking
                        fs.collection("profile_intro_calls").document(ctx.uid).update({
                            "intro_requested": True,
                            "intro_requested_at": time.time(),
                            "status": "completed",
                        })
                        
                        print(f"✅ [PROFILE_INTRO] Auto-sent intro request from {ctx.uid} to {candidate_user_id}")
            except Exception as e:
                print(f"⚠️ [PROFILE_INTRO] Error sending auto-intro request: {e}")
                # Don't fail the workflow for this

        except Exception as e:
            print(f"⚠️ [STORAGE] Error (non-fatal): {e}")
            import traceback
            traceback.print_exc()
            # Don't stop workflow for storage errors

        return True

    async def _step_send_compensation_insight(self, ctx: PostCallContext) -> bool:
        """
        After a compensation-focused call, send the user a card image showing:
        - Their compensation band
        - Signals helping their profile
        - What's holding it back and how to fix it

        We detect eligibility using:
        - user_type: must be job_seeker / candidate
        - compensation_intent_detected flag set during WhatsApp onboarding
        """
        try:
            if not ctx.user_profile:
                print("ℹ️ [COMP_BAND] No user_profile loaded, skipping")
                return True

            profile = ctx.user_profile or {}
            profile_meta = profile.get("profile", {}) or {}

            user_type = profile_meta.get("user_type") or profile.get("user_type") or "general"
            user_type = str(user_type).lower()

            if user_type not in {"job_seeker", "candidate"}:
                print(f"ℹ️ [COMP_BAND] Skipping non-job-seeker user_type={user_type}")
                return True

            # Only send if this user explicitly came in with compensation intent
            # Check both top-level and profile field (flag can be saved in either location)
            compensation_intent = (
                profile.get("compensation_intent_detected")
                or profile_meta.get("compensation_intent_detected")
            )
            if not compensation_intent:
                print("ℹ️ [COMP_BAND] compensation_intent_detected=False, skipping card")
                return True

            # Resolve WhatsApp id / phone
            wa_id = (
                profile.get("wa_id")
                or profile.get("phone")
                or profile.get("whatsapp")
                or ctx.uid  # fallback: many flows already use wa_id == uid
            )
            if not wa_id:
                print(f"⚠️ [COMP_BAND] No wa_id/phone for {ctx.uid}, cannot send card")
                return True

            # Generate insights via Claude
            print(f"🧠 [COMP_BAND] Generating insights for {ctx.uid}...")
            insights = compensation_insight_service.get_insights(ctx.uid)
            print(f"✅ [COMP_BAND] Generated insights: band={insights.compensation_band[:50]}...")

            # Render the card image
            print(f"🎨 [COMP_BAND] Rendering compensation card image...")
            image_bytes = compensation_insight_service.render_card_png(ctx.uid, insights)
            print(f"✅ [COMP_BAND] Card rendered: {len(image_bytes)} bytes")

            # Upload image to WhatsApp Media API
            phone_number_id = os.getenv("PHONE_NUMBER_ID")
            access_token = os.getenv("META_SYS_USER_TOKEN")
            
            if not phone_number_id or not access_token:
                print(f"⚠️ [COMP_BAND] Missing WhatsApp credentials, cannot upload image")
                return True  # Non-critical, continue workflow
            
            upload_url = f"https://graph.facebook.com/v16.0/{phone_number_id}/media"
            files = {
                'file': ('compensation_card.png', io.BytesIO(image_bytes), 'image/png')
            }
            data = {
                'messaging_product': 'whatsapp',
                'type': 'image'
            }
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            print(f"📤 [COMP_BAND] Uploading image to WhatsApp Media API...")
            upload_response = requests.post(upload_url, headers=headers, files=files, data=data, timeout=60)
            
            if upload_response.status_code != 200:
                error_msg = upload_response.text
                print(f"❌ [COMP_BAND] Failed to upload image: {upload_response.status_code} - {error_msg}")
                return True  # Non-critical, continue workflow
            
            media_id = upload_response.json().get('id')
            print(f"✅ [COMP_BAND] Image uploaded, media_id: {media_id}")

            # Send image using media_id
            payload = {
                "messaging_product": "whatsapp",
                "to": wa_id,
                "type": "image",
                "image": {
                    "id": media_id,
                    "caption": "Here's how founders would price your profile today — and how to level it up.",
                },
            }

            print(f"📤 [COMP_BAND] Sending WhatsApp image message to {wa_id}...")
            result = self.sender.send(data=payload)
            print(f"✅ [COMP_BAND] Sent compensation card to {ctx.uid} at {wa_id}: {result}")
            
            # Note: Profile link is sent separately by _send_profile_link_to_candidate in webhook handler
            # No need to send it here to avoid duplicates

        except Exception as e:
            # Non-critical: this should never block the rest of the workflow
            print(f"⚠️ [COMP_BAND] Error sending compensation insight card: {e}")
            import traceback
            traceback.print_exc()

        return True

    async def _step_send_profile_to_candidate(self, ctx: PostCallContext) -> bool:
        """
        Send the caller (job seeker) their public profile link via WhatsApp template.

        Uses phone number from resume if available, otherwise falls back to existing phone.
        Sends via WhatsApp template message with candidate name and profile URL.
        """
        try:
            # Only for job seekers / candidates, not job providers
            user_type = (
                ctx.user_profile.get("profile", {}).get("user_type", "general")
                if ctx.user_profile
                else "general"
            )
            if user_type not in {"job_seeker", "candidate"}:
                print(f"ℹ️ [PROFILE_LINK] Skipping non-job-seeker user_type={user_type}")
                return True

            # Load user_profiles/{uid} to get slug + whatsapp id
            doc = fs.collection("user_profiles").document(ctx.uid).get()
            if not doc.exists:
                print(f"⚠️ [PROFILE_LINK] No user_profiles doc for {ctx.uid}")
                return True

            profile_doc = doc.to_dict() or {}

            slug = (
                profile_doc.get("slug")
                or profile_doc.get("public_slug")
                or profile_doc.get("username")
                or ctx.uid
            )

            # This is the public profile URL we share with founders
            profile_url = f"https://profiles.vance.so/{slug}"

            # Extract phone number from resume if available
            extraction_data = profile_doc.get("extraction_data", {})
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
                or profile_doc.get("whatsapp")
                or profile_doc.get("phone")
                or profile_doc.get("phone_number")
                or extraction_data.get("phone_number")
                or profile_doc.get("whatsapp_number")
                or ctx.uid  # fallback: many flows already use wa_id == uid
            )

            if not wa_id:
                print(f"⚠️ [PROFILE_LINK] No WhatsApp id/phone for {ctx.uid}")
                return True
            
            # Log which phone source was used
            if resume_phone:
                print(f"📱 [PROFILE_LINK] Using phone from resume: {wa_id}")
            else:
                print(f"📱 [PROFILE_LINK] Using phone from profile: {wa_id}")

            # Check if this is the first call - only send profile link after first call
            # Note: save_call_memory (step 3) runs before this (step 6), so call count is already incremented
            call_summary_doc = fs.collection("user_call_summaries").document(ctx.uid).get()
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
            
            if not is_first_call:
                print(f"ℹ️ [PROFILE_LINK] Not first call (call #{total_calls}), skipping profile link")
                return True
            
            print(f"✅ [PROFILE_LINK] First call detected (call #{total_calls}), will send profile link")
            
            # Idempotency: only send once per user (even if multiple first calls somehow)
            status_doc = fs.collection("post_call_profile_links").document(ctx.uid).get()
            if status_doc.exists:
                print(f"ℹ️ [PROFILE_LINK] Already sent profile link for {ctx.uid} (idempotency)")
                return True

            # Get candidate name for template
            candidate_name = (
                profile_doc.get("name")
                or extraction_data.get("name")
                or ctx.user_name
                or "there"
            )
            
            # Use WhatsApp template message
            # Template name: "profile_ready" (to be registered in WhatsApp Business Manager)
            # Template format: "Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you."
            # Parameters: [candidate_name, profile_url]
            template_name = "profile_ready"
            
            try:
                payload = MsgComponents.template_scaffold(
                    to=wa_id,
                    template_name=template_name,
                    language_code="en",
                    body_parameters=[candidate_name, profile_url],
                )
                result = self.sender.send(data=payload)
                use_template = True
            except Exception as template_error:
                # Fallback to text if template fails (template might not exist yet)
                print(f"⚠️ [PROFILE_LINK] Template '{template_name}' failed, falling back to text: {template_error}")
                text = (
                    f"Hey {candidate_name}, it's Vance. I've just created your profile from our call.\n\n"
                    f"{profile_url}\n\n"
                    "This is what I'll share with founders when I introduce you."
                )
                result = self.sender.send(data=MsgComponents.text_scaffold(to=wa_id, text=text))
                use_template = False
            
            # Store with message ID for tracking
            link_data = {
                "sent_at": time.time(),
                "profile_url": profile_url,
                "wa_id": wa_id,
                "is_first_call": is_first_call,
                "used_template": use_template,
                "phone_source": "resume" if resume_phone else "profile",
            }
            
            # Check if message was actually sent successfully
            if isinstance(result, dict):
                if result.get("status") == "success":
                    message_id = result.get("message_id")
                    if message_id:
                        link_data["message_id"] = message_id
                        link_data["delivery_status"] = "sent"
                        print(f"📱 [PROFILE_LINK] Message ID: {message_id}")
                    else:
                        link_data["delivery_status"] = "sent_no_id"
                        print(f"⚠️ [PROFILE_LINK] Message sent but no message ID returned")
                else:
                    # Message failed to send
                    error = result.get("error", "Unknown error")
                    link_data["delivery_status"] = "failed"
                    link_data["error"] = error
                    print(f"❌ [PROFILE_LINK] Failed to send: {error}")
                    # Don't mark as sent if delivery failed
                    fs.collection("post_call_profile_links").document(ctx.uid).set(link_data)
                    return True  # Continue workflow even if message fails
            else:
                link_data["delivery_status"] = "unknown"
                print(f"⚠️ [PROFILE_LINK] Unexpected send result format")

            fs.collection("post_call_profile_links").document(ctx.uid).set(link_data)

            if link_data.get("delivery_status") == "sent":
                print(f"✅ [PROFILE_LINK] Sent profile link to {ctx.uid} at {wa_id} (first call)")
            else:
                print(f"⚠️ [PROFILE_LINK] Profile link attempt recorded but delivery uncertain")
        except Exception as e:
            print(f"⚠️ [PROFILE_LINK] Error sending profile link for {ctx.uid}: {e}")
            # non-critical: do not stop the rest of the workflow

        # Always continue with later steps
        return True

    async def _step_send_referrals(self, ctx: PostCallContext) -> bool:
        """
        Referral messages removed - no longer sending referral prompts.
        This step is kept for workflow compatibility but does nothing.
        """
        print("ℹ️ [REFERRAL] Referral messages disabled - skipping")
        return True

    async def _step_decide_send_profiles(self, ctx: PostCallContext) -> bool:
        """
        Decide if user should receive candidate profiles.
        """
        assert ctx.extraction_data is not None

        ctx.should_send_profiles, ctx.decision_reason = (
            claude_profile_service.should_send_profiles_to_user(
                extraction_data=ctx.extraction_data
            )
        )

        print(
            f"[POSTCALL] should_send={ctx.should_send_profiles} reason={ctx.decision_reason}"
        )

        if not ctx.should_send_profiles:
            print(f"ℹ️ [PROFILES] Not sending profiles for {ctx.uid}")
            return False

        return True

    async def _step_find_matches(self, ctx: PostCallContext) -> bool:
        """
        Find matching candidates using hybrid search.
        """
        assert ctx.extraction_data is not None
        ctx.matched_profiles = await hybrid_matching_service.find_job_seeker_matches(
            job_provider_data=ctx.extraction_data,
            limit=3,
            job_provider_uid=ctx.uid,
        )

        if not ctx.matched_profiles:
            print(f"⚠️ [PROFILES] No matches for {ctx.uid}")
            return False

        print(f"✅ [PROFILES] Found {len(ctx.matched_profiles)} matches")
        return True

    async def _step_send_profiles(self, ctx: PostCallContext) -> bool:
        """
        Send matched profiles to job provider via WhatsApp.
        """
        assert ctx.matched_profiles is not None

        success = await self._send_matched_profiles(
            uid=ctx.uid,
            matched_profiles=ctx.matched_profiles,
            user_name=ctx.user_name,
            linkedin_url=ctx.linkedin_url,
        )

        if success:
            print(f"[POSTCALL] ✅ Sent matched profiles to job provider {ctx.uid}")
        else:
            print(f"[POSTCALL] ⚠️ Failed to send some profiles to {ctx.uid}")

        return True

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _send_matched_profiles(
        self,
        uid: str,
        matched_profiles: List[MatchedProfile],
        user_name: str,
        linkedin_url: str = "",
    ) -> bool:
        """Send matched job seeker profiles to a job provider via WhatsApp."""
        try:
            profiles_for_storage = []

            for index, profile in enumerate(matched_profiles, 1):
                # Store for later reference
                profiles_for_storage.append(
                    {
                        "uid": profile.uid,
                        "name": profile.name,
                        "email": profile.email,
                        "profile_summary": profile.match_reason,
                        "linkedin_url": profile.linkedin_url,
                        "suggested_at": time.time(),
                    }
                )

                # Send profile photo if available
                self._send_profile_photo(uid, profile)

                # Format and send message
                msg_text = self._format_profile_message(profile, index)
                self.sender.send(
                    data=MsgComponents.text_scaffold(to=uid, text=msg_text)
                )

            # Store suggested profiles for deduplication
            await self._store_suggested_profiles(uid, profiles_for_storage)

            # Notify candidates their profiles were shown
            job_provider_name = (
                user_name if user_name and user_name != "there" else "A company"
            )
            job_provider_data = get_extraction_data(uid) or {}
            await self._notify_candidates(
                uid=uid,
                candidates=profiles_for_storage,
                job_provider_name=job_provider_name,
                job_provider_data=job_provider_data,
                linkedin_url=linkedin_url,
            )

            # Trigger founder referral prompt after sending profiles
            # Only for job providers (founders)
            user_profile = get_user_profile(uid) or {}
            user_type = user_profile.get("profile", {}).get("user_type", "general")
            if user_type in {"job_provider", "hiring"}:
                await founder_referral_service.send_referral_prompt(
                    founder_uid=uid,
                    trigger_reason="profiles_sent"
                )

            return True

        except Exception as e:
            print(f"❌ [SEND_PROFILES] Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _format_profile_message(self, profile: MatchedProfile, index: int) -> str:
        """Format a job seeker profile as a WhatsApp message."""
        lines = [f"*Candidate {index}: {profile.name or 'Unknown'}*"]

        if profile.target_role:
            lines.append(f"🎯 Target Role: {profile.target_role}")

        if profile.core_skills:
            lines.append(f"💻 Skills: {profile.core_skills}")

        experience = profile.work_experience or "1+ years"
        lines.append(f"📊 Experience: {experience}")

        location = profile.current_location or "Sec 24, Gurgaon"
        lines.append(f"📍 Location: {location}")

        salary = profile.salary_expectations or "15k+"
        lines.append(f"💰 Expected: {salary}")

        if profile.linkedin_url:
            lines.append(f"🔗 LinkedIn: {profile.linkedin_url}")

        # Try to attach public profile link if available
        try:
            profile_url = ""

            # Look up public profile by user_id to get slug
            if profile.uid:
                try:
                    public_profiles_ref = fs.collection("public_profiles")
                    # Prefer direct document lookup if uid is used as slug
                    doc = public_profiles_ref.document(profile.uid).get()
                    slug = None
                    data = {}
                    if doc.exists:
                        data = doc.to_dict() or {}
                        # Some profiles use slug == document id, others store user_id
                        slug = doc.id
                    else:
                        # Fallback: query by user_id field
                        try:
                            query = (
                                public_profiles_ref.where("user_id", "==", profile.uid)
                                .limit(1)
                                .stream()
                            )
                            for qdoc in query:
                                data = qdoc.to_dict() or {}
                                slug = qdoc.id
                                break
                        except Exception:
                            slug = None

                    if slug and (data.get("active", True)):
                        profile_url = f"https://profiles.vance.so/{slug}"
                except Exception:
                    profile_url = ""

            if profile_url:
                lines.append(f"🌐 Profile: {profile_url}")
        except Exception as e:
            # Don't break profile sending if profile URL lookup fails
            print(f"⚠️ [POSTCALL] Failed to attach profile URL for {profile.uid}: {e}")

        if profile.match_score:
            lines.append(f"\n_Match Score: {profile.match_score:.0%}_")

        if profile.match_reason:
            reason_display = (
                profile.match_reason[:150] + "..."
                if len(profile.match_reason) > 150
                else profile.match_reason
            )
            lines.append(f"_Why: {reason_display}_")

        return "\n".join(lines)

    def _send_profile_photo(self, recipient_uid: str, profile: MatchedProfile) -> None:
        """Send candidate's profile photo from Firestore to the recipient via WhatsApp."""
        try:
            if not profile.uid:
                return

            # Fetch profile photo from Firestore user_profiles collection
            profile_doc = fs.collection("user_profiles").document(profile.uid).get()
            if not profile_doc.exists:
                print(f"ℹ️ [PROFILE_PHOTO] No user_profiles doc for {profile.uid}")
                return

            profile_data = profile_doc.to_dict() or {}
            photo_data_url = (
                profile_data.get("profilePhoto")
                or profile_data.get("profilePhotoUrl")
                or profile_data.get("avatar_url")
                or ""
            )
            if not photo_data_url or not photo_data_url.startswith("data:"):
                print(f"ℹ️ [PROFILE_PHOTO] No photo for candidate {profile.uid}")
                return

            # Decode base64 data URL: "data:image/jpeg;base64,..."
            header, encoded = photo_data_url.split(",", 1)
            content_type = header.split(";")[0].replace("data:", "")
            image_bytes = base64.b64decode(encoded)

            # Upload to WhatsApp Media API
            phone_number_id = os.getenv("PHONE_NUMBER_ID")
            access_token = os.getenv("META_SYS_USER_TOKEN")
            if not phone_number_id or not access_token:
                print("⚠️ [PROFILE_PHOTO] Missing WhatsApp credentials")
                return

            ext = content_type.split("/")[-1] if "/" in content_type else "jpeg"
            upload_url = f"https://graph.facebook.com/v16.0/{phone_number_id}/media"
            files = {
                "file": (f"profile.{ext}", io.BytesIO(image_bytes), content_type)
            }
            data = {"messaging_product": "whatsapp", "type": "image"}
            headers = {"Authorization": f"Bearer {access_token}"}

            upload_resp = requests.post(
                upload_url, headers=headers, files=files, data=data, timeout=60
            )
            if upload_resp.status_code != 200:
                print(f"❌ [PROFILE_PHOTO] Upload failed: {upload_resp.status_code}")
                return

            media_id = upload_resp.json().get("id")
            if not media_id:
                print("❌ [PROFILE_PHOTO] No media_id in upload response")
                return

            # Send image message
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_uid,
                "type": "image",
                "image": {
                    "id": media_id,
                    "caption": f"📸 {profile.name or 'Candidate'}",
                },
            }
            self.sender.send(data=payload)
            print(f"✅ [PROFILE_PHOTO] Sent photo for {profile.name} to {recipient_uid}")

        except Exception as e:
            print(f"⚠️ [PROFILE_PHOTO] Error sending photo for {profile.uid}: {e}")

    async def _notify_candidates(
        self,
        uid: str,
        candidates: List[dict],
        job_provider_name: str,
        job_provider_data: dict,
        linkedin_url: str = "",
    ) -> None:
        """Notify candidates that their profiles were presented."""
        from utils.db import get_user_profile
        
        for candidate in candidates:
            candidate_uid = candidate.get("uid")
            candidate_name = candidate.get("name", "")
            if not candidate_uid:
                continue
            
            # Get WhatsApp ID from candidate's profile, not from the candidate dict
            candidate_profile = get_user_profile(candidate_uid) or {}
            candidate_wa_id = (
                candidate_profile.get("wa_id")
                or candidate_profile.get("phone")
                or candidate_profile.get("whatsapp")
                or candidate_uid if candidate_uid.isdigit() and len(candidate_uid) >= 10 else ""
            )
            
            if candidate_wa_id:
                try:
                    await notify_candidate_profile_presented(
                        candidate_wa_id=candidate_wa_id,
                        job_provider_uid=uid,
                        job_provider_name=job_provider_name,
                        candidate_name=candidate_name,
                        extraction_data=job_provider_data,
                        linkedin_url=linkedin_url,
                    )
                    print(f"✅ [NOTIFY] Notified candidate {candidate_name} ({candidate_uid}) at {candidate_wa_id}")
                except Exception as e:
                    print(f"⚠️ [NOTIFY] Failed to notify candidate {candidate_name} ({candidate_uid}): {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⚠️ [NOTIFY] No WhatsApp ID found for candidate {candidate_name} ({candidate_uid}), skipping notification")

    async def _store_suggested_profiles(self, uid: str, matches: List[dict]) -> None:
        """Store suggested profiles for later reference and deduplication."""
        try:
            profiles_data = [
                {
                    "uid": m.get("uid", ""),
                    "name": m.get("name", ""),
                    "email": m.get("email", ""),
                    "profile_summary": m.get("profile_summary", ""),
                    "linkedin_url": m.get("linkedin_url", ""),
                    "suggested_at": time.time(),
                }
                for m in matches
            ]

            fs.collection("suggested_profiles").document(uid).set(
                {"profiles": profiles_data, "created_at": time.time()}
            )

            print(f"✅ [STORAGE] Stored {len(matches)} suggested profiles for {uid}")

        except Exception as e:
            print(f"⚠️ [STORAGE] Error storing profiles: {e}")

    async def _get_referral_message_history(self, uid: str) -> dict:
        """Get referral message delivery history for a user."""
        try:
            doc_ref = fs.collection("referral_messages").document(uid)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                assert data is not None
                print(
                    f"📋 [REFERRAL] User {uid} has {data.get('delivery_count', 0)} referrals"
                )
                return {
                    "delivery_count": data.get("delivery_count", 0),
                    "timestamps": data.get("timestamps", []),
                    "last_sent": data.get("last_sent", 0),
                    "exists": True,
                }
            else:
                print(f"📋 [REFERRAL] No referral history for {uid}")
                return {
                    "delivery_count": 0,
                    "timestamps": [],
                    "last_sent": 0,
                    "exists": False,
                }

        except Exception as e:
            print(f"⚠️ [REFERRAL] Error getting history: {e}")
            return {
                "delivery_count": 0,
                "timestamps": [],
                "last_sent": 0,
                "exists": False,
            }

    async def _store_referral_message_delivery(self, uid: str) -> None:
        """Store referral message delivery record."""
        try:
            current_time = time.time()
            doc_ref = fs.collection("referral_messages").document(uid)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                assert data is not None

                delivery_count = data.get("delivery_count", 0) + 1
                timestamps = data.get("timestamps", [])
                timestamps.append(current_time)
                if len(timestamps) > 10:
                    timestamps = timestamps[-10:]

                doc_ref.update(
                    {
                        "delivery_count": delivery_count,
                        "timestamps": timestamps,
                        "last_sent": current_time,
                        "updated_at": current_time,
                    }
                )
            else:
                doc_ref.set(
                    {
                        "delivery_count": 1,
                        "timestamps": [current_time],
                        "last_sent": current_time,
                        "created_at": current_time,
                        "updated_at": current_time,
                    }
                )

            print(f"✅ [REFERRAL] Stored delivery record for {uid}")

        except Exception as e:
            print(f"⚠️ [REFERRAL] Error storing delivery: {e}")

    async def _store_post_call_referral_delivery(self, uid: str) -> None:
        """Store post-call referral delivery record (separate tracking)."""
        try:
            current_time = time.time()
            doc_ref = fs.collection("post_call_referrals").document(uid)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                assert data is not None

                delivery_count = data.get("delivery_count", 0) + 1
                timestamps = data.get("timestamps", [])
                timestamps.append(current_time)
                if len(timestamps) > 10:
                    timestamps = timestamps[-10:]

                doc_ref.update(
                    {
                        "delivery_count": delivery_count,
                        "timestamps": timestamps,
                        "last_sent": current_time,
                        "updated_at": current_time,
                    }
                )
            else:
                doc_ref.set(
                    {
                        "delivery_count": 1,
                        "timestamps": [current_time],
                        "last_sent": current_time,
                        "created_at": current_time,
                        "updated_at": current_time,
                    }
                )

            print(f"✅ [POST_CALL_REFERRAL] Stored delivery for {uid}")

        except Exception as e:
            print(f"⚠️ [POST_CALL_REFERRAL] Error storing delivery: {e}")


# Singleton instance for convenience
post_call_workflow = PostCallWorkflow()
