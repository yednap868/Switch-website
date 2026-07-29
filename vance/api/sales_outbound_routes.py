"""
HTTP routes for Sales Outbound Calling — Jyoti cold-calls businesses to get them
hiring on Switch. AI-only (no human transfer); ends with a WhatsApp follow-up.

Flow:
  POST /api/sales-outbound/initiate → triggers single call to a business
  Vobiz answers → POST /api/sales-outbound/answer → returns <Stream> XML
  WebSocket bridge at /ws/sales-outbound relays audio to ElevenLabs (Jyoti)
  Call ends → POST /api/sales-outbound/hangup → cleanup + send WhatsApp link

  POST /api/sales-outbound/batch → triggers batch calls to a list of businesses
  GET  /api/sales-outbound/calls → list recent sales outbound calls
"""

import asyncio
import os
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import Response

from services.vobiz_service import vobiz_service
from utils.db import fs
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender

router = APIRouter(prefix="/api/sales-outbound", tags=["SalesOutbound"])

# In-memory cache: maps call_id → business context (set during initiate, read by bridge)
_sales_call_contexts: dict[str, dict] = {}

# Default WhatsApp follow-up message sent after the call.
_DEFAULT_FOLLOWUP = (
    "Namaste! Main Jyoti, Switch app se. 😊\n\n"
    "Apni hiring requirement yahan free mein daal do — "
    "verified workers seedha aapko call karenge:\n"
    "https://switch.jobs/post\n\n"
    "Koi sawaal ho toh yahin reply kar dena!"
)


def _send_whatsapp_followup(to_number: str, message: str) -> bool:
    """Send the post-call WhatsApp follow-up. Best-effort; returns success flag."""
    try:
        message_data = MsgComponents.text_scaffold(to=to_number, text=message)
        result = WhatsAppSender.send(message_data)
        return isinstance(result, dict) and result.get("status") == "success"
    except Exception as e:
        print(f"⚠️ [SALES_OUT] WhatsApp follow-up error: {e}")
        return False


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


@router.post("/answer")
async def sales_outbound_answer(request: Request):
    """
    Vobiz answer webhook for sales outbound calls.
    Returns <Stream> XML pointing to /ws/sales-outbound.
    Must return XML instantly — all logging in background thread.
    """
    business_phone = request.query_params.get("business_phone", "")
    call_id = request.query_params.get("call_id", "")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    call_uuid = data.get("CallUUID") or data.get("call_uuid") or ""
    caller = data.get("From") or data.get("from") or ""

    print(f"📞 [SALES_OUT] Answer: call_id={call_id} business_phone={business_phone} from={caller} uuid={call_uuid}")

    ctx = _sales_call_contexts.get(call_id)
    if ctx:
        ctx["call_uuid"] = call_uuid

    xml = vobiz_service.build_custom_stream_xml(
        ws_path="/ws/sales-outbound",
        query_params=f"business_phone={business_phone}&call_id={call_id}",
    )

    def _log():
        try:
            fs.collection("debug_webhooks").document("last_sales_outbound_answer").set(
                {"payload": data, "call_id": call_id, "business_phone": business_phone, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [SALES_OUT] Background logging failed: {e}")

    threading.Thread(target=_log, daemon=True).start()

    return Response(content=xml, media_type="application/xml")


@router.post("/hangup")
async def sales_outbound_hangup(request: Request):
    """
    Vobiz hangup webhook for sales outbound calls.
    Logs call outcome, sends the WhatsApp follow-up, and cleans up context.
    """
    call_id = request.query_params.get("call_id", "")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    duration = data.get("Duration") or data.get("duration") or 0
    hangup_cause = data.get("HangupCause") or data.get("hangup_cause", "")

    print(f"📞 [SALES_OUT] Hangup: call_id={call_id} duration={duration} cause={hangup_cause}")

    ctx = _sales_call_contexts.get(call_id, {})
    business_phone = ctx.get("business_phone", "")
    followup_message = ctx.get("followup_message") or _DEFAULT_FOLLOWUP
    send_followup = ctx.get("send_followup", True)

    def _log_and_followup():
        try:
            duration_int = int(duration) if duration else 0
            doc_ref = fs.collection("sales_outbound_calls").document(call_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.update({
                    "duration": duration_int,
                    "hangup_cause": hangup_cause,
                    "status": "completed",
                    "completed_at": time.time(),
                })

            # Only follow up if the call actually connected (someone picked up).
            if send_followup and business_phone and duration_int > 0:
                sent = _send_whatsapp_followup(business_phone, followup_message)
                if doc.exists:
                    doc_ref.update({"followup_sent": bool(sent), "followup_at": time.time()})
                print(f"📲 [SALES_OUT] Follow-up to {business_phone}: {'sent' if sent else 'failed'}")

            fs.collection("debug_webhooks").document("last_sales_outbound_hangup").set(
                {"payload": data, "call_id": call_id, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [SALES_OUT] Hangup logging failed: {e}")

    threading.Thread(target=_log_and_followup, daemon=True).start()

    _sales_call_contexts.pop(call_id, None)

    return {"status": "ok", "message": f"Hangup processed for call_id={call_id}"}


@router.post("/initiate")
async def sales_outbound_initiate(request: Request):
    """
    Trigger a single outbound sales call to a business.

    Body:
        business_phone: str - Business phone number (required)
        business_name: str - Business / shop name
        contact_name: str - Name of the person to address
        city: str - City
        category: str - What they typically hire for (helper, delivery, cook...)
        followup_message: str - Override the default WhatsApp follow-up text
        send_followup: bool - Send WhatsApp follow-up after the call (default true)
    """
    data = await request.json()
    business_phone = data.get("business_phone", "").strip()

    if not business_phone:
        return {"status": "error", "message": "business_phone is required"}

    normalized = _normalize_phone(business_phone)
    call_id = f"sales_{uuid4().hex[:12]}"

    sales_context = {
        "call_id": call_id,
        "business_phone": normalized,
        "business_name": data.get("business_name", "").strip(),
        "contact_name": data.get("contact_name", "").strip(),
        "city": data.get("city", "").strip(),
        "category": data.get("category", "").strip(),
        "followup_message": (data.get("followup_message") or "").strip() or _DEFAULT_FOLLOWUP,
        "send_followup": bool(data.get("send_followup", True)),
        "initiated_at": time.time(),
    }
    _sales_call_contexts[call_id] = sales_context

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    answer_url = f"https://{server_host}/api/sales-outbound/answer?business_phone={normalized}&call_id={call_id}"
    hangup_url = f"https://{server_host}/api/sales-outbound/hangup?call_id={call_id}"

    print(f"📞 [SALES_OUT] Initiating call: call_id={call_id} to={normalized} business={sales_context['business_name']}")

    try:
        result = await vobiz_service.make_call(
            to_number=normalized,
            answer_url=answer_url,
            hangup_url=hangup_url,
        )
        print(f"✅ [SALES_OUT] Call initiated: {result}")
    except Exception as e:
        print(f"❌ [SALES_OUT] Call initiation failed: {e}")
        _sales_call_contexts.pop(call_id, None)
        return {"status": "error", "message": f"Call failed: {e}"}

    def _save():
        try:
            fs.collection("sales_outbound_calls").document(call_id).set({
                **sales_context,
                "status": "initiated",
                "vobiz_response": str(result),
            })
        except Exception as e:
            print(f"⚠️ [SALES_OUT] Firestore save failed: {e}")

    threading.Thread(target=_save, daemon=True).start()

    return {"status": "success", "call_id": call_id, "business_phone": normalized}


@router.post("/batch")
async def sales_outbound_batch(request: Request, background_tasks: BackgroundTasks):
    """
    Trigger batch outbound sales calls to a list of businesses.

    Body:
        leads: list[dict] - Each: {business_phone, business_name, contact_name, city, category}
        delay_between: int - Seconds between calls (default 45)
        send_followup: bool - Send WhatsApp follow-up after each call (default true)
    """
    data = await request.json()
    leads = data.get("leads", [])
    delay_between = data.get("delay_between", 45)
    send_followup = bool(data.get("send_followup", True))

    if not isinstance(leads, list) or not leads:
        return {"status": "error", "message": "leads (non-empty list) is required"}

    background_tasks.add_task(_run_batch_calls, leads, delay_between, send_followup)

    return {"status": "started", "count": len(leads), "delay_between": delay_between}


async def _run_batch_calls(leads: list, delay_between: int, send_followup: bool):
    """Background task to run batch sales calls, deduped by phone."""
    print(f"📞 [SALES_BATCH] Starting batch: {len(leads)} leads delay={delay_between}s")

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    seen_phones = set()
    call_ids = []

    for i, lead in enumerate(leads):
        raw_phone = (lead.get("business_phone") or "").strip()
        if not raw_phone:
            continue
        normalized = _normalize_phone(raw_phone)
        if normalized in seen_phones:
            continue
        seen_phones.add(normalized)

        call_id = f"sales_{uuid4().hex[:12]}"
        sales_context = {
            "call_id": call_id,
            "business_phone": normalized,
            "business_name": (lead.get("business_name") or "").strip(),
            "contact_name": (lead.get("contact_name") or "").strip(),
            "city": (lead.get("city") or "").strip(),
            "category": (lead.get("category") or "").strip(),
            "followup_message": (lead.get("followup_message") or "").strip() or _DEFAULT_FOLLOWUP,
            "send_followup": send_followup,
            "initiated_at": time.time(),
        }
        _sales_call_contexts[call_id] = sales_context

        answer_url = f"https://{server_host}/api/sales-outbound/answer?business_phone={normalized}&call_id={call_id}"
        hangup_url = f"https://{server_host}/api/sales-outbound/hangup?call_id={call_id}"

        try:
            result = await vobiz_service.make_call(
                to_number=normalized,
                answer_url=answer_url,
                hangup_url=hangup_url,
            )
            call_ids.append(call_id)
            fs.collection("sales_outbound_calls").document(call_id).set({
                **sales_context,
                "status": "initiated",
                "batch": True,
                "vobiz_response": str(result),
            })
            print(f"✅ [SALES_BATCH] [{i+1}/{len(leads)}] Called {normalized} ({sales_context['business_name']})")
        except Exception as e:
            print(f"❌ [SALES_BATCH] [{i+1}/{len(leads)}] Failed {normalized}: {e}")
            _sales_call_contexts.pop(call_id, None)

        if i < len(leads) - 1:
            await asyncio.sleep(delay_between)

    print(f"📞 [SALES_BATCH] Batch complete: {len(call_ids)}/{len(leads)} calls initiated")


@router.get("/calls")
async def list_sales_calls():
    """List recent sales outbound calls."""
    try:
        calls = []
        docs = fs.collection("sales_outbound_calls").order_by("initiated_at", direction="DESCENDING").limit(100).stream()
        for doc in docs:
            call = doc.to_dict()
            call["id"] = doc.id
            calls.append(call)
        return {"status": "success", "calls": calls, "total": len(calls)}
    except Exception as e:
        print(f"❌ [SALES_OUT] Error listing calls: {e}")
        return {"status": "error", "message": str(e), "calls": []}
