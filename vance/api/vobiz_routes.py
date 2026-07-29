"""
Vobiz.ai webhook routes for incoming call handling.

Vobiz hits these endpoints when phone events occur:
  - answer_url: Called when an incoming call is received on our Vobiz number
  - hangup_url: Called when a call ends

The answer_url returns <Stream> XML that opens a bidirectional WebSocket
to our bridge, which relays audio to/from ElevenLabs Conversation API.
"""

import os
import threading

from fastapi import APIRouter, Request
from fastapi.responses import Response

from services.incoming_call_service import (
    build_answer_response,
    create_incoming_call_record,
    handle_hangup,
)
from services.vobiz_service import vobiz_service

router = APIRouter(prefix="/api/webhooks/vobiz", tags=["Vobiz"])

# In-memory cache: normalized_phone → Vobiz CallUUID for active inbound calls.
# Used by live connect to transfer the inbound call after screening.
_inbound_call_uuids: dict[str, str] = {}


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


@router.post("/answer")
async def vobiz_answer_url(request: Request):
    """
    Vobiz answer_url webhook — called when someone dials our Vobiz number.

    Vobiz sends caller info (From, To, CallUUID, etc.) as form data or JSON.
    We log the call, then return XML that forwards to ElevenLabs via SIP.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    caller_number = data.get("From") or data.get("from") or data.get("caller_id", "")
    called_number = data.get("To") or data.get("to") or ""
    vobiz_call_id = data.get("CallUUID") or data.get("call_uuid") or data.get("call_id", "")

    # Cache CallUUID for live connect transfer
    if vobiz_call_id and caller_number:
        normalized = _normalize_phone(caller_number)
        _inbound_call_uuids[normalized] = vobiz_call_id

    print(
        f"📞 [VOBIZ] Incoming call: from={caller_number} to={called_number} "
        f"call_id={vobiz_call_id}"
    )
    print(f"📞 [VOBIZ] Full payload: {data}")

    # Build <Stream> XML FIRST — return immediately so Vobiz doesn't timeout
    xml_response = build_answer_response(caller_number)
    print(f"📞 [VOBIZ] Returning Stream XML immediately")
    print(f"📞 [VOBIZ] XML response:\n{xml_response}")

    # Log call record in background thread (don't block the response)
    def _log_call():
        try:
            create_incoming_call_record(
                caller_number=caller_number,
                vobiz_call_id=vobiz_call_id,
            )
        except Exception as e:
            print(f"⚠️ [VOBIZ] Background call logging failed: {e}")

    threading.Thread(target=_log_call, daemon=True).start()

    return Response(content=xml_response, media_type="application/xml")


@router.post("/hangup")
async def vobiz_hangup_url(request: Request):
    """
    Vobiz hangup_url webhook — called when a call ends.

    Updates the call record with duration and hangup cause.
    The main transcript/extraction processing is done by the
    ElevenLabs post-call webhook separately.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    caller_number = data.get("From") or data.get("from") or data.get("caller_id", "")
    vobiz_call_id = data.get("CallUUID") or data.get("call_uuid") or data.get("call_id", "")
    duration = data.get("Duration") or data.get("duration")
    hangup_cause = data.get("HangupCause") or data.get("hangup_cause", "")

    # Clean up CallUUID cache
    if caller_number:
        normalized = _normalize_phone(caller_number)
        _inbound_call_uuids.pop(normalized, None)

    print(
        f"📞 [VOBIZ] Hangup: from={caller_number} call_id={vobiz_call_id} "
        f"duration={duration} cause={hangup_cause}"
    )

    # Return immediately, do Firestore operations in background
    duration_int = None
    if duration is not None:
        try:
            duration_int = int(duration)
        except (ValueError, TypeError):
            pass

    def _log_hangup():
        try:
            handle_hangup(
                caller_number=caller_number,
                vobiz_call_id=vobiz_call_id,
                duration=duration_int,
                hangup_cause=hangup_cause,
            )
        except Exception as e:
            print(f"⚠️ [VOBIZ] Background hangup logging failed: {e}")

    threading.Thread(target=_log_hangup, daemon=True).start()

    return {"status": "ok", "message": "Hangup processed"}


@router.post("/stream-ended")
async def vobiz_stream_ended(request: Request):
    """
    Vobiz <Redirect> endpoint — hit after the <Stream> ends.

    When the ElevenLabs bridge closes (stream ends), Vobiz processes the
    <Redirect> element and POSTs here. If there's a pending live connect
    session, we return <Stream> XML to connect the candidate to the LC bridge.
    Otherwise we hang up.
    """
    caller_phone = request.query_params.get("caller_phone", "")
    normalized = _normalize_phone(caller_phone) if caller_phone else ""

    print(f"📞 [VOBIZ] stream-ended redirect: caller_phone={caller_phone} normalized={normalized}")

    # Lazy import to avoid circular dependency
    from api.webhooks import _inbound_lc_sessions, _inbound_lc_business_sessions

    # Check for pending inbound live connect session
    if normalized:
        pending_session_id = _inbound_lc_sessions.pop(normalized, "")
        if pending_session_id and pending_session_id != "__transferred__":
            print(f"📞 [VOBIZ] stream-ended: Found pending LC session {pending_session_id} — returning LC candidate stream XML")
            server_host = os.getenv("SERVER_HOST", "api.relayy.world")
            xml = vobiz_service.build_custom_stream_xml(
                ws_path="/ws/live-connect/candidate",
                query_params=f"session_id={pending_session_id}",
                speak_first="Ek minute hold kijiye, hum aapko employer se connect kar rahe hain.",
            )
            return Response(content=xml, media_type="application/xml")

        # Check for pending business live connect session (reverse flow)
        pending_biz_session_id = _inbound_lc_business_sessions.pop(normalized, "")
        if pending_biz_session_id:
            print(f"📞 [VOBIZ] stream-ended: Found pending biz LC session {pending_biz_session_id} — returning LC business stream XML")
            server_host = os.getenv("SERVER_HOST", "api.relayy.world")
            xml = vobiz_service.build_custom_stream_xml(
                ws_path="/ws/live-connect/business",
                query_params=f"session_id={pending_biz_session_id}&attempt_phone={normalized}",
            )
            return Response(content=xml, media_type="application/xml")

    # No pending session — hang up
    print(f"📞 [VOBIZ] stream-ended: No pending LC session for {normalized} — hanging up")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        "  <Hangup/>\n"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/status")
async def vobiz_status():
    """Health check for Vobiz webhook endpoints."""
    return {
        "status": "active",
        "configured": vobiz_service.is_configured,
        "phone_number": vobiz_service.phone_number or "(not set)",
        "endpoints": {
            "answer_url": "/api/webhooks/vobiz/answer",
            "hangup_url": "/api/webhooks/vobiz/hangup",
            "stream_ended": "/api/webhooks/vobiz/stream-ended",
        },
    }
