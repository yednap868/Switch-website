"""
Agent-based WhatsApp router.
Replaces the complex state-based router with a simple agent-based approach.
"""

import asyncio
import traceback
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response

from agent.runner import runner
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender

from .conversation_history import conversation_history
from .user_recognition import user_recognition
from .webhook_handler import handle_webhook, verify_webhook

# Optional Redis lock support
try:
    from utils.redis_client import redis_cache

    _redis_client = getattr(redis_cache, "redis_client", None)
    if _redis_client:
        print("[ROUTER] Redis proactive lock enabled")
except Exception as _e:
    _redis_client = None
    print(f"[ROUTER] Redis unavailable: {_e}")

# Create router
router = APIRouter(tags=["whatsapp"])


def send_whatsapp_message(user_id: str, message: str, message_id: str = None) -> bool:
    """Send WhatsApp message."""
    try:
        message_data = MsgComponents.text_scaffold(to=user_id, text=message)
        result = WhatsAppSender.send(message_data)

        if isinstance(result, dict) and result.get("status") == "success":
            print(f"[WHATSAPP] Sent message to {user_id}")
            return True
        else:
            print(f"[WHATSAPP] Failed to send to {user_id}: {result}")
            return False
    except Exception as e:
        print(f"[WHATSAPP] Error sending message: {e}")
        return False


def send_typing_indicator(message_id: str):
    """Send typing indicator."""
    try:
        WhatsAppSender.send_typing_indicator_with_message_id(message_id, 1)
    except Exception as e:
        print(f"[TYPING] Failed: {e}")


def _is_privacy_breach(message_text: str) -> bool:
    """Check if user is asking about system internals."""
    message_lower = message_text.lower()
    privacy_keywords = [
        "system prompt",
        "codebase",
        "source code",
        "api key",
        "credentials",
        "firebase",
        "qdrant",
        "how do you work",
        "are you an ai",
        "are you a bot",
    ]
    return sum(1 for kw in privacy_keywords if kw in message_lower) >= 2


def _parse_user_type_response(message_text: str) -> str | None:
    """Parse button response for user type classification."""
    mappings = {
        "job_seeker": "job_seeker",
        "job seeker": "job_seeker",
        "looking for a job": "job_seeker",
        "i'm looking for a job": "job_seeker",
        "job_provider": "job_provider",
        "job provider": "job_provider",
        "hiring": "job_provider",
        "i'm hiring": "job_provider",
        "looking to hire": "job_provider",
    }
    return mappings.get(message_text.lower().strip())


def _is_compensation_intent(message_text: str) -> bool:
    """
    Detect if user message indicates compensation/compensation band intent.
    This automatically classifies them as a job seeker.
    """
    message_lower = message_text.lower()
    compensation_keywords = [
        "compensation band",
        "compensation",
        "salary",
        "pay",
        "what founders would pay",
        "what would founders pay",
        "founders would place me",
        "compensation founders",
        "salary band",
        "pay band",
        "what am i worth",
        "my worth",
        "market rate",
        "market salary",
    ]
    return any(keyword in message_lower for keyword in compensation_keywords)


async def _handle_send_candidates_directly(user_id: str, message_text: str) -> str | None:
    """
    Directly handle 'bhejo' type messages by sending Switch candidate profile cards.
    Returns response string if handled, None if message should go to agent.
    """
    message_lower = message_text.lower().strip()

    # Keywords that trigger direct candidate sending
    send_keywords = ["bhejo", "send", "dikhao", "batao candidate", "candidates bhejo", "profile bhejo"]

    if not any(kw in message_lower for kw in send_keywords):
        return None

    print(f"📤 [DIRECT_SEND] Detected candidate request: '{message_text}'")

    try:
        from models.switch_models import Job
        from services.switch_matching_service import switch_matching_service
        from services.switch_profile_card_service import switch_profile_card_service
        from services.switch_interview_service import switch_interview_service

        # Detect role from message
        role = "Staff"
        if "waiter" in message_lower:
            role = "Waiter"
        elif "helper" in message_lower:
            role = "Helper"
        elif "sales" in message_lower:
            role = "Sales"
        elif "kitchen" in message_lower:
            role = "Kitchen"
        elif "delivery" in message_lower:
            role = "Delivery"

        print(f"📤 [DIRECT_SEND] Role detected: {role}")

        # Create job for matching
        import time
        job = Job(
            id=f"job_{user_id}_{int(time.time())}",
            business_id=user_id,
            role=role,
            positions_count=1,
            salary_min=8000,
            salary_max=15000,
            experience_required="Fresher",
            location="Delhi NCR",
            interview_address="To be shared",
        )

        # Find candidates
        candidates = switch_matching_service.find_matching_candidates(job, limit=3)
        if not candidates:
            print(f"📤 [DIRECT_SEND] No matches, trying fallback...")
            candidates = switch_matching_service.find_any_candidates_fallback(limit=3)

        if not candidates:
            return f"Abhi {role} ke liye koi candidate nahi mila. Jaise hi milega, bhej dungi! 👍"

        print(f"📤 [DIRECT_SEND] Found {len(candidates)} candidates, sending cards...")

        # Store pending candidates for interview selection
        switch_interview_service.store_pending_candidates(user_id, candidates)

        sender = WhatsAppSender()
        sent_count = 0

        for i, candidate in enumerate(candidates[:3], 1):
            try:
                print(f"🎨 [DIRECT_SEND] Generating card for {candidate.name}...")
                card_bytes = switch_profile_card_service.generate_profile_card(candidate)
                print(f"🎨 [DIRECT_SEND] Card size: {len(card_bytes)} bytes")

                caption = f"*Candidate {i}: {candidate.name}*\n"
                if candidate.area:
                    caption += f"📍 {candidate.area}\n"
                if candidate.experience_level:
                    caption += f"💼 {candidate.experience_level}\n"
                caption += f"💰 ₹{candidate.expected_salary_min:,}-{candidate.expected_salary_max:,}/month"

                print(f"📤 [DIRECT_SEND] Uploading image...")
                result = sender.send_image(to=user_id, image_bytes=card_bytes, caption=caption)
                print(f"📤 [DIRECT_SEND] Result: {result}")

                if result.get("status") == "success":
                    sent_count += 1
                else:
                    # Fallback to text
                    text_msg = MsgComponents.text_scaffold(to=user_id, text=caption)
                    sender.send(text_msg)
                    sent_count += 1

                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"❌ [DIRECT_SEND] Error for {candidate.name}: {e}")
                traceback.print_exc()
                # Send text fallback
                text_msg = MsgComponents.text_scaffold(
                    to=user_id,
                    text=f"*Candidate {i}: {candidate.name}*\n📍 {candidate.area}\n💼 {candidate.experience_level}"
                )
                sender.send(text_msg)
                sent_count += 1

        if sent_count > 0:
            return f"Yeh lo {sent_count} candidates! 👆\n\nKoi pasand aaya? 'YES 1' ya 'YES 2' likh kar batao, interview fix kar dungi! 😊"
        else:
            return "Candidates bhejne mein problem hui. Thodi der baad try karo."

    except Exception as e:
        print(f"❌ [DIRECT_SEND] Error: {e}")
        traceback.print_exc()
        return None  # Let agent handle it


async def process_message_with_agent(user_id: str, message_text: str) -> str:
    """
    Process user message through the agent.
    This is the core message handling function.
    """
    try:
        print(f"[AGENT] Processing message from {user_id}: {message_text[:50]}...")

        # INTERVIEW FLOW: Check if this is part of interview scheduling
        try:
            from services.switch_interview_service import switch_interview_service
            interview_response = switch_interview_service.handle_message(user_id, message_text)
            if interview_response:
                print(f"[AGENT] Handled by interview service")
                return interview_response
        except Exception as e:
            print(f"[AGENT] Interview service error: {e}")

        # DIRECT HANDLER: Check if this is a "bhejo" type message
        direct_response = await _handle_send_candidates_directly(user_id, message_text)
        if direct_response:
            print(f"[AGENT] Handled directly (bypassed agent)")
            return direct_response

        # Run the agent
        response = await runner(
            uid=user_id,
            input=message_text,
            mode="text",
            model="anthropic:claude-sonnet-4-20250514",
        )

        print(f"[AGENT] Response generated: {response[:100]}...")

        # Save to conversation history
        try:
            conversation_history.save_message(
                user_id=user_id,
                sender="user",
                content=message_text,
                message_type="text",
            )
            conversation_history.save_message(
                user_id=user_id,
                sender="agent",
                content=response,
                message_type="text",
            )
        except Exception as e:
            print(f"[HISTORY] Failed to save: {e}")

        return response

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[AGENT] Error ({error_type}): {error_msg}")
        traceback.print_exc()
        
        # Log more details about the error
        if "tool_use_id" in error_msg.lower() or "tool_result" in error_msg.lower():
            print(f"[AGENT] ⚠️ Tool-related error detected - this might be a conversation history issue")
        elif "validation" in error_msg.lower() or "validate" in error_msg.lower():
            print(f"[AGENT] ⚠️ Validation error detected - check message format")
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            print(f"[AGENT] ⚠️ Rate limit error - too many requests")
        
        return "Hit a glitch. Give it another shot."


def process_webhook_in_background(
    message_id: str,
    user_id: str,
    phone_number: str,
    message_text: str,
    message_type: str,
):
    """
    Background task to process webhook message.
    Returns 200 immediately to Meta, processes async.
    """
    try:
        print(f"[BACKGROUND] Processing message {message_id}")

        # Check if user was deleted
        if _redis_client:
            deletion_marker = f"user:deleted:{user_id}"
            if _redis_client.get(deletion_marker):
                print(f"[DELETED] User {user_id} was deleted, ignoring")
                return

            lock_key = f"proactive_lock:{user_id}"
            if _redis_client.get(lock_key):
                print(f"[LOCK] User {user_id} is locked, ignoring")
                return

        # Check if this is a Switch business requirement message
        # Look for job-related keywords
        job_keywords = ["need", "want", "looking for", "hire", "require", "vacancy", "job", "worker", "staff", "employee"]
        message_lower = message_text.lower()
        is_business_message = any(keyword in message_lower for keyword in job_keywords)
        
        # Check if user is a business (exists in businesses collection)
        if is_business_message:
            try:
                from utils.db import fs
                from services.switch_business_intake_service import business_intake_service
                
                # Check if business exists or create
                phone_clean = phone_number.replace("+", "").replace("-", "").replace(" ", "")
                business_doc = fs.collection("businesses").where("phone", "==", phone_clean).limit(1).stream()
                business_exists = any(True for _ in business_doc)
                
                if business_exists or is_business_message:
                    print(f"[SWITCH] Detected business requirement message from {user_id}")
                    # Route to Switch business intake
                    asyncio.create_task(
                        business_intake_service.initiate_business_call(
                            business_phone=phone_number,
                            initial_message=message_text,
                            business_id=None
                        )
                    )
                    # Send acknowledgment
                    send_whatsapp_message(
                        user_id,
                        "Thanks! We're calling you now to collect job requirements. Please pick up! 📞"
                    )
                    return
            except Exception as e:
                print(f"[SWITCH] Error routing business message: {e}")

        # Store phone number if available
        if phone_number:
            try:
                user_recognition.create_or_update_user(
                    wa_id=user_id, phone=phone_number, initial_data={}
                )
            except Exception as e:
                print(f"[USER] Failed to store phone: {e}")

        # Mark message as read
        WhatsAppSender.mark_message_as_read(message_id)

        # Send typing indicator
        send_typing_indicator(message_id)

        # Get user profile to check for fresh user or awaiting classification
        user_data = user_recognition.get_user_identity(user_id)
        profile = user_data.get("profile", {}) if user_data else {}

        # Check if awaiting button response for user type classification
        if profile.get("awaiting_type_classification"):
            user_type = _parse_user_type_response(message_text)
            if user_type:
                # Store user type and clear awaiting flag
                user_recognition.create_or_update_user(
                    wa_id=user_id,
                    phone=phone_number,
                    initial_data={
                        "user_type": user_type,
                        "awaiting_type_classification": False,
                    },
                )

                # Log user's selection to conversation history
                conversation_history.save_message(
                    user_id=user_id,
                    sender="user",
                    content=f"[Selected: {user_type}]",
                    message_type="button_response",
                    metadata={
                        "template_name": "define_user_type",
                        "selected_option": user_type,
                    },
                )

                # Send acknowledgment
                ack = (
                    "Got it!"
                    if user_type == "job_seeker"
                    else "Perfect - I'll find you great candidates!"
                )
                send_whatsapp_message(user_id, ack)

                # Log acknowledgment to conversation history
                conversation_history.save_message(
                    user_id=user_id,
                    sender="agent",
                    content=ack,
                    message_type="text",
                )

                print(f"[CLASSIFICATION] User {user_id} classified as {user_type}")
                # Continue to agent processing below
            else:
                # Didn't recognize button response, continue to agent processing
                print(
                    f"[CLASSIFICATION] Unrecognized response from {user_id}: {message_text}"
                )

        # Check if fresh user needs type classification (no user_type and not awaiting)
        # For Switch: Skip the Vance template - let Jyoti handle classification naturally
        has_user_type = profile.get("user_type") or profile.get(
            "awaiting_type_classification"
        )
        if not has_user_type:
            # Check if message indicates compensation intent (auto-classify as job_seeker)
            if _is_compensation_intent(message_text):
                print(f"[COMPENSATION_INTENT] Detected compensation intent from {user_id}, auto-classifying as job_seeker")
                # Automatically set user_type to job_seeker and skip template
                user_recognition.create_or_update_user(
                    wa_id=user_id,
                    phone=phone_number,
                    initial_data={
                        "user_type": "job_seeker",
                        "profile": {"user_type": "job_seeker"},
                        "compensation_intent_detected": True,  # Flag to skip connection_type question
                    },
                )
                # Log to conversation history
                conversation_history.save_message(
                    user_id=user_id,
                    sender="agent",
                    content="[Auto-classified as job_seeker based on compensation intent]",
                    message_type="system",
                    metadata={
                        "auto_classified": True,
                        "user_type": "job_seeker",
                        "reason": "compensation_intent",
                    },
                )
                # Continue to agent processing (skip template)
            # Skip Vance template - let Switch/Jyoti agent handle naturally
            # The agent will detect business vs candidate from conversation

        # Check for privacy breach
        if _is_privacy_breach(message_text):
            print(f"[PRIVACY] Breach detected from {user_id}")
            send_whatsapp_message(
                user_id,
                "That's confidential. Let's focus on you - what are you working on?",
            )
            return

        # Process through agent (run async in sync context)
        response = asyncio.run(process_message_with_agent(user_id, message_text))

        # Send response
        if response:
            success = send_whatsapp_message(user_id, response)
            if success:
                print(f"[BACKGROUND] Successfully processed {message_id}")
            else:
                print(f"[BACKGROUND] Failed to send response")
        else:
            print(f"[BACKGROUND] No response for {message_id}")

    except Exception as e:
        print(f"[BACKGROUND] Error processing {message_id}: {e}")
        traceback.print_exc()


@router.post("/api/whatsapp/webhooks", tags=["Bot"])
async def whatsapp_webhook(data: dict[Any, Any], background_tasks: BackgroundTasks):
    """
    Agent-based WhatsApp webhook handler.

    Returns 200 immediately to Meta (within 100ms).
    Processes the message in the background through the agent.
    """
    # Handle webhook and extract data
    message_id, user_id, phone_number, message_text, message_type = handle_webhook(data)

    # Skip if invalid or duplicate
    if not message_id or not user_id or not message_text:
        return Response(status_code=200)

    # Skip empty or system messages
    if not message_text.strip() or message_text.strip().lower() in [
        "system",
        "webhook",
        "test",
        "ping",
    ]:
        return Response(status_code=200)

    # Queue processing in background
    background_tasks.add_task(
        process_webhook_in_background,
        message_id=message_id,
        user_id=user_id,
        phone_number=phone_number,
        message_text=message_text,
        message_type=message_type,
    )

    print(f"[WEBHOOK] Queued {message_type} message {message_id} for agent processing")
    return Response(status_code=200)


@router.get("/api/whatsapp/webhooks", tags=["Challenge"])
def whatsapp_webhook_verification(
    request: Request,
    hub_challenge: str = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str = Query(default=None, alias="hub.verify_token"),
):
    """WhatsApp webhook verification endpoint."""
    challenge = verify_webhook(hub_challenge, hub_verify_token)
    return Response(content=challenge)
