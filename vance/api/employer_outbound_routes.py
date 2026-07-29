"""
HTTP routes for Employer Outbound Calling — answer/hangup webhooks and API endpoints.

Flow:
  POST /api/employer-outbound/initiate → triggers single call to employer
  Vobiz answers → POST /api/employer-outbound/answer → returns <Stream> XML
  WebSocket bridge at /ws/employer-outbound relays audio to ElevenLabs
  Call ends → POST /api/employer-outbound/hangup → cleanup
  Post-call webhook fires → extracts interview slot data → stores in interview_slots

  POST /api/employer-outbound/batch → triggers batch calls to employers
  GET  /api/employer-outbound/slots → list all interview slots
  POST /api/employer-outbound/slots/{slot_id}/match → match candidates + notify
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

router = APIRouter(prefix="/api/employer-outbound", tags=["EmployerOutbound"])

# In-memory cache: maps call_id → job context (set during initiate, read by bridge)
_employer_call_contexts: dict[str, dict] = {}


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


@router.post("/answer")
async def employer_outbound_answer(request: Request):
    """
    Vobiz answer webhook for employer outbound calls.
    Returns <Stream> XML pointing to /ws/employer-outbound.
    Must return XML instantly — all logging in background thread.
    """
    employer_phone = request.query_params.get("employer_phone", "")
    call_id = request.query_params.get("call_id", "")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    call_uuid = data.get("CallUUID") or data.get("call_uuid") or ""
    caller = data.get("From") or data.get("from") or ""

    print(f"📞 [EMP_OUT] Answer: call_id={call_id} employer_phone={employer_phone} from={caller} uuid={call_uuid}")

    # Store CallUUID in context for hangup
    ctx = _employer_call_contexts.get(call_id)
    if ctx:
        ctx["call_uuid"] = call_uuid

    xml = vobiz_service.build_custom_stream_xml(
        ws_path="/ws/employer-outbound",
        query_params=f"employer_phone={employer_phone}&call_id={call_id}",
    )

    def _log():
        try:
            fs.collection("debug_webhooks").document("last_emp_outbound_answer").set(
                {"payload": data, "call_id": call_id, "employer_phone": employer_phone, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [EMP_OUT] Background logging failed: {e}")

    threading.Thread(target=_log, daemon=True).start()

    return Response(content=xml, media_type="application/xml")


@router.post("/hangup")
async def employer_outbound_hangup(request: Request):
    """
    Vobiz hangup webhook for employer outbound calls.
    Logs call outcome and cleans up in-memory context.
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

    print(f"📞 [EMP_OUT] Hangup: call_id={call_id} duration={duration} cause={hangup_cause}")

    def _log():
        try:
            # Update Firestore call record
            doc_ref = fs.collection("employer_outbound_calls").document(call_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.update({
                    "duration": int(duration) if duration else 0,
                    "hangup_cause": hangup_cause,
                    "status": "completed",
                    "completed_at": time.time(),
                })
            fs.collection("debug_webhooks").document("last_emp_outbound_hangup").set(
                {"payload": data, "call_id": call_id, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [EMP_OUT] Hangup logging failed: {e}")

    threading.Thread(target=_log, daemon=True).start()

    # Cleanup in-memory context
    _employer_call_contexts.pop(call_id, None)

    return {"status": "ok", "message": f"Hangup processed for call_id={call_id}"}


@router.post("/initiate")
async def employer_outbound_initiate(request: Request):
    """
    Trigger a single outbound call to an employer.

    Body:
        employer_phone: str - Employer phone number (required)
        company: str - Company name
        job_id: str - Job document ID
        job_title: str - Job title/position
        job_category: str - Job category
        city: str - City
        salary_max: int - Maximum salary offered
        candidate_phone: str - Candidate phone number (for live connect transfer)
        candidate_name: str - Candidate name
        candidate_experience: str - Candidate experience
        candidate_location: str - Candidate location
    """
    data = await request.json()
    employer_phone = data.get("employer_phone", "").strip()

    if not employer_phone:
        return {"status": "error", "message": "employer_phone is required"}

    normalized = _normalize_phone(employer_phone)
    company = data.get("company", "").strip()
    job_id = data.get("job_id", "")
    job_title = data.get("job_title", "").strip()
    job_category = data.get("job_category", "").strip()
    city = data.get("city", "").strip()
    salary_max = data.get("salary_max", 0)
    candidate_phone = data.get("candidate_phone", "").strip()
    candidate_name = data.get("candidate_name", "").strip()
    candidate_experience = data.get("candidate_experience", "").strip()
    candidate_location = data.get("candidate_location", "").strip()

    call_id = f"emp_{uuid4().hex[:12]}"

    # Store context in memory for bridge to read (fast, no Firestore blocking)
    job_context = {
        "call_id": call_id,
        "employer_phone": normalized,
        "company": company,
        "job_id": job_id,
        "job_title": job_title,
        "job_category": job_category,
        "city": city,
        "salary_max": salary_max,
        "candidate_phone": _normalize_phone(candidate_phone) if candidate_phone else "",
        "candidate_name": candidate_name,
        "candidate_experience": candidate_experience,
        "candidate_location": candidate_location,
        "initiated_at": time.time(),
    }
    _employer_call_contexts[call_id] = job_context

    # Build Vobiz URLs
    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    answer_url = f"https://{server_host}/api/employer-outbound/answer?employer_phone={normalized}&call_id={call_id}"
    hangup_url = f"https://{server_host}/api/employer-outbound/hangup?call_id={call_id}"

    print(f"📞 [EMP_OUT] Initiating call: call_id={call_id} to={normalized} company={company} title={job_title}")

    try:
        result = await vobiz_service.make_call(
            to_number=normalized,
            answer_url=answer_url,
            hangup_url=hangup_url,
        )
        print(f"✅ [EMP_OUT] Call initiated: {result}")
    except Exception as e:
        print(f"❌ [EMP_OUT] Call initiation failed: {e}")
        _employer_call_contexts.pop(call_id, None)
        return {"status": "error", "message": f"Call failed: {e}"}

    # Save to Firestore in background
    def _save():
        try:
            fs.collection("employer_outbound_calls").document(call_id).set({
                **job_context,
                "status": "initiated",
                "vobiz_response": str(result),
            })
        except Exception as e:
            print(f"⚠️ [EMP_OUT] Firestore save failed: {e}")

    threading.Thread(target=_save, daemon=True).start()

    return {"status": "success", "call_id": call_id, "employer_phone": normalized}


@router.post("/batch")
async def employer_outbound_batch(request: Request, background_tasks: BackgroundTasks):
    """
    Trigger batch outbound calls to employers.

    Body:
        city: str - Filter by city (optional)
        category: str - Filter by job category (optional)
        limit: int - Max employers to call (default 20)
        delay_between: int - Seconds between calls (default 45)
    """
    data = await request.json()
    city = data.get("city", "").strip()
    category = data.get("category", "").strip()
    limit = data.get("limit", 20)
    delay_between = data.get("delay_between", 45)

    background_tasks.add_task(_run_batch_calls, city, category, limit, delay_between)

    return {"status": "started", "city": city, "category": category, "limit": limit}


async def _run_batch_calls(city: str, category: str, limit: int, delay_between: int):
    """Background task to run batch employer calls."""
    print(f"📞 [EMP_BATCH] Starting batch: city={city} category={category} limit={limit} delay={delay_between}s")

    try:
        # Query jobhai_jobs with filters
        query = fs.collection("jobhai_jobs")
        if city:
            query = query.where("city", "==", city)
        if category:
            query = query.where("category", "==", category)

        docs = list(query.stream())
        print(f"📞 [EMP_BATCH] Found {len(docs)} jobs matching filters")

        # Deduplicate by phone and collect unique employers
        seen_phones = set()
        employers = []
        for doc in docs:
            job = doc.to_dict()
            phone = job.get("phone", "")
            if not phone:
                continue
            normalized = _normalize_phone(phone)
            if normalized in seen_phones:
                continue
            seen_phones.add(normalized)
            employers.append({
                "employer_phone": normalized,
                "company": job.get("company", ""),
                "job_id": doc.id,
                "job_title": job.get("title", ""),
                "job_category": job.get("category", ""),
                "city": job.get("city", ""),
                "salary_max": job.get("salary_max", 0),
            })

        # Skip phones already called today
        today_start = time.time() - 86400
        already_called = set()
        try:
            recent_calls = fs.collection("employer_outbound_calls").where("initiated_at", ">=", today_start).stream()
            for call_doc in recent_calls:
                call_data = call_doc.to_dict()
                already_called.add(call_data.get("employer_phone", ""))
        except Exception as e:
            print(f"⚠️ [EMP_BATCH] Error checking recent calls: {e}")

        employers = [e for e in employers if e["employer_phone"] not in already_called]
        employers = employers[:limit]

        print(f"📞 [EMP_BATCH] Calling {len(employers)} employers (skipped {len(already_called)} already called today)")

        server_host = os.getenv("SERVER_HOST", "api.relayy.world")
        call_ids = []

        for i, emp in enumerate(employers):
            call_id = f"emp_{uuid4().hex[:12]}"
            normalized = emp["employer_phone"]

            job_context = {
                "call_id": call_id,
                **emp,
                "initiated_at": time.time(),
            }
            _employer_call_contexts[call_id] = job_context

            answer_url = f"https://{server_host}/api/employer-outbound/answer?employer_phone={normalized}&call_id={call_id}"
            hangup_url = f"https://{server_host}/api/employer-outbound/hangup?call_id={call_id}"

            try:
                result = await vobiz_service.make_call(
                    to_number=normalized,
                    answer_url=answer_url,
                    hangup_url=hangup_url,
                )
                call_ids.append(call_id)

                # Save to Firestore
                fs.collection("employer_outbound_calls").document(call_id).set({
                    **job_context,
                    "status": "initiated",
                    "batch": True,
                    "vobiz_response": str(result),
                })
                print(f"✅ [EMP_BATCH] [{i+1}/{len(employers)}] Called {normalized} ({emp['company']})")
            except Exception as e:
                print(f"❌ [EMP_BATCH] [{i+1}/{len(employers)}] Failed {normalized}: {e}")
                _employer_call_contexts.pop(call_id, None)

            if i < len(employers) - 1:
                await asyncio.sleep(delay_between)

        print(f"📞 [EMP_BATCH] Batch complete: {len(call_ids)}/{len(employers)} calls initiated")

    except Exception as e:
        print(f"❌ [EMP_BATCH] Batch failed: {e}")


@router.get("/slots")
async def list_interview_slots():
    """List all interview slots, ordered by creation time."""
    try:
        slots = []
        docs = fs.collection("interview_slots").order_by("created_at", direction="DESCENDING").stream()
        for doc in docs:
            slot = doc.to_dict()
            slot["id"] = doc.id
            slots.append(slot)
        return {"status": "success", "slots": slots, "total": len(slots)}
    except Exception as e:
        print(f"❌ [EMP_OUT] Error listing slots: {e}")
        return {"status": "error", "message": str(e), "slots": []}


@router.post("/slots/{slot_id}/match")
async def match_slot_candidates(slot_id: str):
    """Match candidates to an interview slot and send notifications."""
    from services.employer_slot_matching_service import match_and_notify

    try:
        result = await asyncio.to_thread(match_and_notify, slot_id)
        return {"status": "success", **result}
    except Exception as e:
        print(f"❌ [EMP_OUT] Matching failed for slot {slot_id}: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/calls")
async def list_employer_calls():
    """List recent employer outbound calls."""
    try:
        calls = []
        docs = fs.collection("employer_outbound_calls").order_by("initiated_at", direction="DESCENDING").limit(100).stream()
        for doc in docs:
            call = doc.to_dict()
            call["id"] = doc.id
            calls.append(call)
        return {"status": "success", "calls": calls, "total": len(calls)}
    except Exception as e:
        print(f"❌ [EMP_OUT] Error listing calls: {e}")
        return {"status": "error", "message": str(e), "calls": []}


@router.get("/debug-el")
async def debug_elevenlabs():
    """Test ElevenLabs WebSocket connectivity — returns agent_id, connection status, init metadata."""
    import websockets as _ws

    agent_id = os.getenv("ELEVENLABS_EMPLOYER_AGENT_ID") or os.getenv("ELEVENLABS_AGENT_ID", "")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    result = {
        "agent_id": agent_id[:20] + "..." if agent_id else "MISSING",
        "api_key_set": bool(api_key),
        "api_key_prefix": api_key[:8] + "..." if api_key else "MISSING",
    }

    if not agent_id or not api_key:
        result["status"] = "error"
        result["message"] = "Missing ELEVENLABS_EMPLOYER_AGENT_ID or ELEVENLABS_API_KEY"
        return result

    el_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
    try:
        el_ws = await _ws.connect(el_url, additional_headers={"xi-api-key": api_key})
        result["ws_connected"] = True

        init_msg = await asyncio.wait_for(el_ws.recv(), timeout=10)
        import json as _json
        init_data = _json.loads(init_msg)
        result["init_type"] = init_data.get("type", "unknown")
        if init_data.get("type") == "conversation_initiation_metadata":
            meta = init_data.get("conversation_initiation_metadata_event", {})
            result["conversation_id"] = meta.get("conversation_id", "")
            result["audio_format"] = meta.get("agent_output_audio_format", "")
        else:
            result["init_raw"] = str(init_data)[:500]

        await el_ws.close()
        result["status"] = "success"
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {e}"

    return result


@router.api_route("/conference", methods=["GET", "POST"])
async def employer_outbound_conference(request: Request):
    """Vobiz answer URL for conference bridge.
    Both employer (transferred) and candidate (new call) join the same conference room.
    """
    call_id = request.query_params.get("call_id", "")
    party = request.query_params.get("party", "")
    candidate_name = request.query_params.get("name", "Candidate")
    job_company = request.query_params.get("company", "")
    job_role = request.query_params.get("role", "")
    room_name = f"emp_bridge_{call_id[:16]}"

    if party == "candidate":
        if job_company:
            intro = f"Namaste! {job_company} ke HR line pe hain, aapki call connect kar rahi hoon. Ek second ruko."
        else:
            intro = "Namaste! Employer line pe hain, aapki call connect kar rahi hoon. Ek second ruko."
    else:
        intro = "Candidate ko connect kar rahe hain, ek second."

    xml = vobiz_service.build_conference_xml(room_name=room_name, intro_text=intro, wait_sound=(party == "employer"))
    print(f"📞 [EMP_OUT] Conference join: party={party} room={room_name} call_id={call_id}")
    return Response(content=xml, media_type="application/xml")
