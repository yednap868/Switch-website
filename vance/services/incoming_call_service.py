"""
Service for handling incoming phone calls via Vobiz.

When a user calls the Vobiz phone number:
1. Vobiz sends a POST to our answer_url with caller info
2. We log the call to PostgreSQL inbound_calls table
3. We return <Stream> XML that opens a bidirectional WebSocket to our bridge
4. Our bridge relays audio to/from ElevenLabs Conversation API
5. ElevenLabs agent Jyoti answers and handles the conversation
6. After the call, the post-call webhook processes the transcript
"""

import time
from typing import Optional

from models.sql_models import InboundCall
from services.vobiz_service import vobiz_service
from utils.postgres import get_db


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to 12-digit digits-only (91XXXXXXXXXX)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


def create_incoming_call_record(
    caller_number: str,
    vobiz_call_id: Optional[str] = None,
) -> str:
    """
    Create an inbound call record in PostgreSQL.

    Returns the internal call_id string.
    """
    normalized = _normalize_phone(caller_number)
    call_id = f"incoming_{normalized}_{int(time.time())}"

    db = get_db()
    try:
        row = InboundCall(
            call_id=call_id,
            caller_number=normalized,
            called_number=vobiz_service.phone_number or "",
            vobiz_call_id=vobiz_call_id or "",
            caller_type="candidate",
            status="initiated",
        )
        db.add(row)
        db.commit()
        print(f"📞 [INCOMING] Logged inbound call {call_id} from {normalized}")
    except Exception as e:
        print(f"⚠️ [INCOMING] Failed to log call: {e}")
        db.rollback()
    finally:
        db.close()

    return call_id


def build_answer_response(caller_number: str) -> str:
    """
    Build the <Stream> XML response for Vobiz answer_url.
    """
    normalized = _normalize_phone(caller_number)
    return vobiz_service.build_bridge_stream_xml(caller_phone=normalized)


def handle_hangup(
    caller_number: str,
    vobiz_call_id: Optional[str] = None,
    duration: Optional[int] = None,
    hangup_cause: Optional[str] = None,
) -> None:
    """
    Update the inbound call record on hangup.
    """
    normalized = _normalize_phone(caller_number)

    db = get_db()
    try:
        row = (
            db.query(InboundCall)
            .filter(InboundCall.caller_number == normalized)
            .order_by(InboundCall.id.desc())
            .first()
        )
        if not row:
            print(f"⚠️ [INCOMING] No call record found for hangup from {normalized}")
            return

        row.status = "completed"
        if duration is not None:
            row.duration_seconds = duration
        if hangup_cause:
            row.hangup_cause = hangup_cause
        if vobiz_call_id:
            row.vobiz_call_id = vobiz_call_id

        db.commit()
        print(
            f"✅ [INCOMING] Updated call #{row.id} — duration={duration}s, cause={hangup_cause}"
        )
    except Exception as e:
        print(f"⚠️ [INCOMING] Hangup update failed: {e}")
        db.rollback()
    finally:
        db.close()
