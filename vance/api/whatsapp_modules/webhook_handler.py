"""
Webhook handler module.
Handles incoming WhatsApp webhooks with deduplication and validation.
"""

import os
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, Query, Request, Response

# Redis-based deduplication
try:
    # Import the cache wrapper and access the underlying raw client
    from utils.redis_client import redis_cache

    _raw_client = getattr(redis_cache, "redis_client", None)
    if _raw_client is not None:
        redis_client = _raw_client
        REDIS_AVAILABLE = True
        print("✅ [REDIS] Deduplication will use Redis")
    else:
        REDIS_AVAILABLE = False
        print("⚠️ [REDIS] redis_cache has no active client; using in-memory dedupe")
except Exception as e:
    print(f"⚠️ [REDIS] Redis not available, falling back to in-memory: {e}")
    REDIS_AVAILABLE = False

# Fallback: Message deduplication with TTL (in-memory)
_processed_messages: Dict[str, float] = {}
_deduplication_ttl = 3600  # 1 hour TTL
_max_deduplication_size = 10000  # Maximum 10k messages


# Persistent deduplication using Firebase (survives server restarts)
def _is_duplicate_message_persistent(message_id: str) -> bool:
    """Check if message has already been processed using Firebase persistence."""
    try:
        from utils.db import fs

        doc_ref = fs.collection("processed_messages").document(message_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            timestamp = data.get("timestamp", 0)
            current_time = time.time()

            if current_time - timestamp <= _deduplication_ttl:
                print(
                    f"⏭️ [WEBHOOK] Message {message_id} already processed (persistent check)"
                )
                return True
            else:
                # Remove expired message
                doc_ref.delete()
                print(f"🧹 [DEDUP] Removed expired message {message_id}")

        return False
    except Exception as e:
        print(f"⚠️ [DEDUP] Error in persistent deduplication: {e}")
        return False


def _mark_message_processed_persistent(message_id: str):
    """Mark message as processed using Firebase persistence."""
    try:
        from utils.db import fs

        fs.collection("processed_messages").document(message_id).set(
            {"timestamp": time.time(), "processed_at": time.time()}
        )
        print(f"🔄 [WEBHOOK] Marked message {message_id} as processed (persistent)")
    except Exception as e:
        print(f"⚠️ [DEDUP] Error marking message as processed: {e}")


def extract_message_data(webhook_data: dict) -> Tuple[str, str, str, str, str]:
    """
    Extract message ID, user ID, phone number, message text, and message type from webhook data.
    Returns (message_id, user_id, phone_number, message_text, message_type) tuple.

    Handles:
    - Regular text messages
    - Quick reply button responses (type: "button")
    - Interactive messages (type: "interactive")
    - Media messages (image, video, audio, document)
    """
    try:
        for entry in webhook_data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Skip status updates
                if "statuses" in value:
                    print(f"⏭️ [WEBHOOK] Skipping status update webhook")
                    return "", "", "", "", ""

                # Extract user ID and phone number
                contacts = value.get("contacts", [])
                user_id = contacts[0].get("wa_id", "") if contacts else ""
                phone_number = (
                    contacts[0].get("profile", {}).get("name", "") if contacts else ""
                )

                # Extract phone number from contacts
                if contacts and len(contacts) > 0:
                    contact = contacts[0]
                    # Try different phone number fields - wa_id is often the phone number
                    phone_number = (
                        contact.get("phone")
                        or contact.get("wa_id")
                        or contact.get("profile", {}).get("phone", "")
                    )

                    # If we got the wa_id as phone, that's actually correct for WhatsApp
                    if phone_number == user_id:
                        print(
                            f"📱 [WEBHOOK] Using wa_id as phone: {phone_number} for user: {user_id}"
                        )
                    else:
                        print(
                            f"📱 [WEBHOOK] Extracted phone: {phone_number} for user: {user_id}"
                        )

                # Extract message
                messages = value.get("messages", [])
                if messages:
                    message = messages[0]
                    message_id = message.get("id", "")
                    message_type = message.get("type", "unknown")
                    message_text = ""

                    # Handle regular text messages
                    if message_type == "text":
                        message_text = message.get("text", {}).get("body", "")
                        print(f"📝 [WEBHOOK] Text message: '{message_text}'")

                    # Handle quick reply button responses (type: "button")
                    elif message_type == "button":
                        button = message.get("button", {})
                        button_text = button.get("text", "")
                        button_payload = button.get("payload", "")

                        # Use payload if available, otherwise use text
                        message_text = button_payload if button_payload else button_text
                        print(
                            f"🔘 [WEBHOOK] Button clicked: text='{button_text}', payload='{button_payload}'"
                        )

                    # Unknown message type
                    else:
                        print(f"⚠️ [WEBHOOK] Unknown message type: {message_type}")

                    return message_id, user_id, phone_number, message_text, message_type

    except Exception as e:
        print(f"❌ [WEBHOOK] Error extracting message data: {e}")
        import traceback

        traceback.print_exc()

    return "", "", "", "", "error"


def _cleanup_old_messages():
    """Clean up old message IDs from deduplication cache."""
    current_time = time.time()
    expired_messages = [
        msg_id
        for msg_id, timestamp in _processed_messages.items()
        if current_time - timestamp > _deduplication_ttl
    ]
    for msg_id in expired_messages:
        del _processed_messages[msg_id]
    if expired_messages:
        print(f"🧹 [DEDUP] Cleaned up {len(expired_messages)} expired message IDs")


def _enforce_size_limit():
    """Enforce maximum size limit for deduplication cache."""
    if len(_processed_messages) > _max_deduplication_size:
        # Remove oldest 20% of messages
        sorted_messages = sorted(_processed_messages.items(), key=lambda x: x[1])
        to_remove = int(_max_deduplication_size * 0.2)
        for msg_id, _ in sorted_messages[:to_remove]:
            del _processed_messages[msg_id]
        print(f"🧹 [DEDUP] Removed {to_remove} old messages to enforce size limit")


def try_claim_message(message_id: str) -> bool:
    """
    Atomically claim a message for processing.
    Returns True if we successfully claimed it (first to process).
    Returns False if it was already claimed (duplicate).

    This uses Redis SETNX for atomic check-and-set in production.
    """
    # Try Redis first (atomic SETNX)
    if REDIS_AVAILABLE:
        try:
            redis_key = f"whatsapp:msg:{message_id}"
            # SETNX with NX=True: returns True if key was set, False if already exists
            # This is ATOMIC - no race condition possible
            was_set = redis_client.set(redis_key, "1", ex=_deduplication_ttl, nx=True)

            if was_set:
                print(f"✅ [REDIS] Claimed message {message_id} (atomic)")
                return True
            else:
                print(
                    f"⏭️ [REDIS] Message {message_id} already claimed by another request (duplicate blocked)"
                )
                return False
        except Exception as e:
            print(f"⚠️ [REDIS] Error claiming message, falling back to in-memory: {e}")

    # Fallback: in-memory (not perfectly atomic, but single-worker safe)
    current_time = time.time()

    # Check if already processed and not expired
    if message_id in _processed_messages:
        timestamp = _processed_messages[message_id]
        if current_time - timestamp <= _deduplication_ttl:
            print(f"⏭️ [MEMORY] Message {message_id} already claimed (in-memory)")
            return False
        else:
            # Expired, can reclaim
            del _processed_messages[message_id]

    # Claim it
    _cleanup_old_messages()
    _enforce_size_limit()
    _processed_messages[message_id] = current_time
    print(f"✅ [MEMORY] Claimed message {message_id} (in-memory)")
    return True


def handle_webhook(
    data: Dict[Any, Any],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], str]:
    """
    Handle incoming webhook and return extracted data.
    Returns (message_id, user_id, phone_number, message_text, message_type) if valid, (None, None, None, None, type) if should skip.

    Handles both regular text messages and quick reply button responses.
    Uses atomic claim to prevent duplicate processing.
    """
    print(f"🔍 [WEBHOOK] Received webhook data")

    # Extract message data (now includes message_type)
    message_id, user_id, phone_number, message_text, message_type = (
        extract_message_data(data)
    )

    # Validate basic fields
    if not message_id or not user_id:
        print(f"⏭️ [WEBHOOK] Skipping - no valid message_id or user_id")
        return None, None, None, None, message_type

    # ATOMIC CLAIM: Try to claim this message (check-and-set in one operation)
    # If another request already claimed it, this returns False
    if not try_claim_message(message_id):
        print(f"⏭️ [WEBHOOK] Skipping duplicate message {message_id}")
        return None, None, None, None, message_type

    # We successfully claimed it! Now validate content
    if not message_text:
        print(f"⏭️ [WEBHOOK] No text message found")
        return None, None, None, None, message_type

    print(
        f"📱 [WEBHOOK] Processing claimed {message_type} message {message_id}: '{message_text[:50]}...' (phone: {phone_number})"
    )
    return message_id, user_id, phone_number, message_text, message_type


def verify_webhook(
    hub_challenge: Optional[str] = None, hub_verify_token: Optional[str] = None
) -> str:
    """
    Verify WhatsApp webhook.
    Returns challenge string if valid, raises HTTPException if not.
    """
    if not hub_challenge or not hub_verify_token:
        raise HTTPException(status_code=400, detail="Missing challenge parameters")

    if hub_verify_token != os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN"):
        raise HTTPException(status_code=403, detail="Invalid verify token")

    return hub_challenge
