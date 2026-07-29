"""
WebSocket bridge for Employer Outbound calls.

Connects Vobiz (employer phone call) ↔ ElevenLabs (Jyoti AI agent).
Jyoti asks employer about interview availability, date/time/address.

Simple one-mode bridge: AI mode only (no hold, no direct relay).
"""

import asyncio
import base64
import json
import os
import threading
import time
import traceback

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.employer_outbound_routes import _employer_call_contexts
from api.webhooks import _call_phone_cache, _employer_conversation_cache
from api.vobiz_bridge import (
    ELEVENLABS_WS_URL,
    MULAW_CHUNK_SIZE,
    _mulaw_8k_to_pcm_16k,
    _pcm_16k_to_mulaw_8k,
)
from models.sql_models import JobApplication
from services.vobiz_service import vobiz_service
from urllib.parse import quote as url_quote
from utils.db import fs
from utils.postgres import get_db

router = APIRouter(tags=["EmployerOutboundBridge"])



async def _relay_vobiz_to_elevenlabs(vobiz_ws: WebSocket, el_ws, state: dict) -> None:
    """Relay audio from Vobiz (employer) to ElevenLabs agent."""
    try:
        while True:
            raw = await vobiz_ws.receive_text()
            event = json.loads(raw)
            event_type = event.get("event")

            if event_type == "media":
                payload_b64 = event.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue
                mulaw_bytes = base64.b64decode(payload_b64)
                pcm_16k = _mulaw_8k_to_pcm_16k(mulaw_bytes)
                pcm_b64 = base64.b64encode(pcm_16k).decode("utf-8")
                await el_ws.send(json.dumps({"user_audio_chunk": pcm_b64}))
                state["vobiz_chunks_in"] += 1

            elif event_type == "start":
                start_data = event.get("start", {})
                stream_id = (
                    event.get("streamId")
                    or start_data.get("streamId")
                    or event.get("streamSid")
                    or start_data.get("streamSid")
                    or ""
                )
                state["stream_id"] = stream_id
                print(f"🔗 [EMP_BRIDGE] Stream started. streamId={stream_id}")

            elif event_type == "stop":
                print("🔗 [EMP_BRIDGE] Stream stopped")
                break

            elif event_type == "connected":
                pass

    except WebSocketDisconnect:
        print("🔗 [EMP_BRIDGE] Vobiz disconnected (relay)")
    except Exception as e:
        print(f"🔗 [EMP_BRIDGE] Vobiz→EL error: {type(e).__name__}: {e}")


TRANSFER_TRIGGER_PHRASES = [
    "connect karti",
    "connect kar deti",
    "connect kar rahi",
    "transfer karti",
    "transfer kar",
    "abhi connect",
    "ruko connect",
]


async def _relay_elevenlabs_to_vobiz(el_ws, vobiz_ws: WebSocket, state: dict) -> None:
    """Relay audio from ElevenLabs agent to Vobiz (employer).
    Also monitors agent responses for transfer trigger phrases.
    """
    try:
        async for message in el_ws:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "audio":
                audio_event = data.get("audio_event", {})
                audio_b64 = audio_event.get("audio_base_64", "")
                if not audio_b64:
                    continue
                pcm_bytes = base64.b64decode(audio_b64)
                mulaw_bytes = _pcm_16k_to_mulaw_8k(pcm_bytes)
                state["el_chunks_out"] += 1

                for i in range(0, len(mulaw_bytes), MULAW_CHUNK_SIZE):
                    frame = mulaw_bytes[i:i + MULAW_CHUNK_SIZE]
                    frame_b64 = base64.b64encode(frame).decode("utf-8")
                    play_msg = {
                        "event": "playAudio",
                        "media": {
                            "contentType": "audio/x-mulaw",
                            "sampleRate": 8000,
                            "payload": frame_b64,
                        },
                        "streamId": state["stream_id"],
                    }
                    await vobiz_ws.send_text(json.dumps(play_msg))

            elif msg_type == "agent_response":
                text = data.get("agent_response_event", {}).get("agent_response", "")
                print(f"🤖 [EMP_BRIDGE] Agent: {text[:150]}")
                text_lower = text.lower()
                transfer_event = state.get("transfer_event")
                if transfer_event and not transfer_event.is_set():
                    for phrase in TRANSFER_TRIGGER_PHRASES:
                        if phrase in text_lower:
                            print(f"🔗 [EMP_BRIDGE] Transfer trigger detected: '{phrase}' in '{text[:80]}'")
                            transfer_event.set()
                            break

            elif msg_type == "user_transcript":
                text = data.get("user_transcription_event", {}).get("user_transcript", "")
                print(f"👤 [EMP_BRIDGE] Employer: {text[:150]}")

            elif msg_type == "ping":
                ping_event = data.get("ping_event", {})
                await el_ws.send(json.dumps({
                    "type": "pong",
                    "event_id": ping_event.get("event_id"),
                }))

            elif msg_type == "interruption":
                if state.get("stream_id"):
                    await vobiz_ws.send_text(json.dumps({
                        "event": "clearAudio",
                        "streamId": state["stream_id"],
                    }))

    except websockets.exceptions.ConnectionClosed:
        print("🔗 [EMP_BRIDGE] ElevenLabs disconnected")
    except Exception as e:
        print(f"🔗 [EMP_BRIDGE] EL→Vobiz error: {type(e).__name__}: {e}")


def _build_candidate_pitch_prompt(job_context: dict) -> str:
    """Build the Jyoti employer pitch system prompt with candidate details filled in."""
    candidate_name = job_context.get("candidate_name", "Candidate")
    candidate_experience = job_context.get("candidate_experience", "Not specified")
    candidate_location = job_context.get("candidate_location", "NCR")
    job_role = job_context.get("job_title", "")
    job_company = job_context.get("company", "")
    job_salary = str(job_context.get("salary_max", "")) if job_context.get("salary_max") else "Negotiable"
    city = job_context.get("city", "")

    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "system_prompt_bolna_jyoti_employer.md")
    try:
        with open(prompt_path, "r") as f:
            prompt_template = f.read()
        prompt = prompt_template.replace("{candidate_name}", candidate_name)
        prompt = prompt.replace("{candidate_experience}", candidate_experience)
        prompt = prompt.replace("{candidate_location}", candidate_location)
        prompt = prompt.replace("{candidate_phone}", "HIDDEN")
        prompt = prompt.replace("{job_role}", job_role)
        prompt = prompt.replace("{job_company}", job_company)
        prompt = prompt.replace("{job_salary}", job_salary)
        prompt = prompt.replace("{job_location}", city)
    except Exception as e:
        print(f"⚠️ [EMP_BRIDGE] Error reading prompt template: {e}")
        prompt = (
            f"You are Jyoti from Switch app. You're calling an employer about a candidate. "
            f"Candidate: {candidate_name}, {candidate_experience} experience, from {candidate_location}. "
            f"Job: {job_role} at {job_company}. "
            f"Pitch the candidate briefly. If employer says yes, say 'connect karti hoon' and transfer."
        )
    return prompt


async def _do_conference_bridge(call_id: str, job_context: dict, el_ws) -> None:
    """Transfer employer to conference and call candidate to join.
    Called when Jyoti's transfer trigger phrase is detected.
    """
    candidate_phone = job_context.get("candidate_phone", "")
    candidate_name = job_context.get("candidate_name", "Candidate")
    job_company = job_context.get("company", "")
    job_role = job_context.get("job_title", "")
    call_uuid = job_context.get("call_uuid", "")

    if not candidate_phone:
        print(f"❌ [EMP_BRIDGE] No candidate_phone in context, cannot bridge call_id={call_id}")
        return

    if not call_uuid:
        print(f"❌ [EMP_BRIDGE] No call_uuid for employer, cannot transfer call_id={call_id}")
        return

    print(f"🔗 [EMP_BRIDGE] Starting conference bridge: call_id={call_id} employer_uuid={call_uuid} candidate={candidate_phone}")

    job_id = job_context.get("job_id", "")

    # Update application status to "connecting" so candidate sees it in the app
    def _set_connecting():
        if not candidate_phone or not job_id:
            return
        try:
            db = get_db()
            try:
                app = db.query(JobApplication).filter_by(
                    user_id=candidate_phone, job_id=job_id
                ).first()
                if app:
                    app.status = "connecting"
                    db.commit()
                    print(f"✅ [EMP_BRIDGE] Application status → connecting: user={candidate_phone} job={job_id}")
            finally:
                db.close()
        except Exception as e:
            print(f"⚠️ [EMP_BRIDGE] Failed to set connecting status: {e}")

    threading.Thread(target=_set_connecting, daemon=True).start()

    # Wait for Jyoti's audio to finish playing to employer
    await asyncio.sleep(3)

    # Close ElevenLabs connection (Jyoti is done)
    try:
        await el_ws.close()
    except Exception:
        pass

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    conf_base = f"https://{server_host}/api/employer-outbound/conference"
    name_param = url_quote(candidate_name)
    company_param = url_quote(job_company)
    role_param = url_quote(job_role)

    employer_conf_url = f"{conf_base}?call_id={call_id}&party=employer&name={name_param}&company={company_param}&role={role_param}"
    candidate_conf_url = f"{conf_base}?call_id={call_id}&party=candidate&name={name_param}&company={company_param}&role={role_param}"
    hangup_url = f"https://{server_host}/api/employer-outbound/hangup?call_id={call_id}"

    try:
        transfer_result = await vobiz_service.transfer_call(call_uuid, employer_conf_url)
        print(f"✅ [EMP_BRIDGE] Employer transferred to conference: {transfer_result}")
    except Exception as e:
        print(f"❌ [EMP_BRIDGE] Employer transfer failed: {e}")
        return

    try:
        call_result = await vobiz_service.make_call(
            to_number=candidate_phone,
            answer_url=candidate_conf_url,
            hangup_url=hangup_url,
        )
        print(f"✅ [EMP_BRIDGE] Candidate called to conference: {call_result}")
    except Exception as e:
        print(f"❌ [EMP_BRIDGE] Candidate call failed: {e}")
        return

    def _log_bridge_and_update_app():
        try:
            fs.collection("employer_outbound_calls").document(call_id).update({
                "status": "conference_bridging",
                "candidate_phone": candidate_phone,
                "conference_initiated_at": time.time(),
            })
        except Exception as e:
            print(f"⚠️ [EMP_BRIDGE] Firestore bridge log failed: {e}")

        if candidate_phone and job_id:
            try:
                db = get_db()
                try:
                    app = db.query(JobApplication).filter_by(
                        user_id=candidate_phone, job_id=job_id
                    ).first()
                    if app:
                        app.status = "interview"
                        app.call_scheduled = True
                        app.call_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        db.commit()
                        print(f"✅ [EMP_BRIDGE] Application updated to 'interview': user={candidate_phone} job={job_id}")
                    else:
                        print(f"⚠️ [EMP_BRIDGE] No application found for user={candidate_phone} job={job_id}")
                finally:
                    db.close()
            except Exception as e:
                print(f"⚠️ [EMP_BRIDGE] Application status update failed: {e}")

    threading.Thread(target=_log_bridge_and_update_app, daemon=True).start()


@router.websocket("/ws/employer-outbound")
async def employer_outbound_bridge(vobiz_ws: WebSocket):
    """
    WebSocket endpoint for employer outbound calls.
    Bridges Vobiz ↔ ElevenLabs for Jyoti to talk to the employer.

    CRITICAL: Connect to ElevenLabs IMMEDIATELY. No Firestore calls before
    the relay starts — every second of silence = caller hangs up.
    """
    await vobiz_ws.accept()

    employer_phone = vobiz_ws.query_params.get("employer_phone", "")
    call_id = vobiz_ws.query_params.get("call_id", "")

    print(f"🔗 [EMP_BRIDGE] WS connected: call_id={call_id} phone={employer_phone}", flush=True)

    # Read job context from in-memory cache ONLY (set during /initiate, instant)
    job_context = _employer_call_contexts.get(call_id, {})
    if not job_context:
        print(f"⚠️ [EMP_BRIDGE] No in-memory context for {call_id}, using empty", flush=True)

    company = job_context.get("company", "")
    job_title = job_context.get("job_title", "")
    city = job_context.get("city", "")
    salary_max = job_context.get("salary_max", 0)
    candidate_phone = job_context.get("candidate_phone", "")
    candidate_name = job_context.get("candidate_name", "")
    candidate_location = job_context.get("candidate_location", "NCR")
    has_candidate = bool(candidate_phone)

    # Transfer event — set when Jyoti says "connect karti hoon"
    transfer_event = asyncio.Event() if has_candidate else None

    state = {
        "stream_id": "",
        "vobiz_chunks_in": 0,
        "el_chunks_out": 0,
        "conversation_id": None,
        "transfer_event": transfer_event,
    }

    agent_id = os.getenv("ELEVENLABS_EMPLOYER_AGENT_ID") or os.getenv("ELEVENLABS_AGENT_ID", "")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    print(f"🔗 [EMP_BRIDGE] Connecting EL: agent={agent_id[:20]}... key={'set' if api_key else 'MISSING'}", flush=True)

    el_url = f"{ELEVENLABS_WS_URL}?agent_id={agent_id}"
    headers = {}
    if api_key:
        headers["xi-api-key"] = api_key

    el_ws = None
    try:
        # Connect to ElevenLabs IMMEDIATELY — no Firestore before this
        el_ws = await websockets.connect(el_url, additional_headers=headers)
        print(f"🔗 [EMP_BRIDGE] EL connected for {call_id}", flush=True)

        # Wait for init
        init_msg = await asyncio.wait_for(el_ws.recv(), timeout=10)
        init_data = json.loads(init_msg)
        if init_data.get("type") == "conversation_initiation_metadata":
            meta = init_data.get("conversation_initiation_metadata_event", {})
            conv_id = meta.get("conversation_id", "")
            state["conversation_id"] = conv_id
            print(f"🔗 [EMP_BRIDGE] EL conv_id={conv_id}", flush=True)

            if conv_id:
                _employer_conversation_cache[conv_id] = call_id
                _call_phone_cache[conv_id] = employer_phone

        # Send dynamic variables to ElevenLabs (agent prompt is configured in EL dashboard)
        client_data = {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": {
                "caller_phone": employer_phone,
                "call_type": "employer_outbound",
                "company_name": company,
                "job_title": job_title,
                "job_city": city,
                "job_salary": str(salary_max) if salary_max else "",
                "call_id": call_id,
                "candidate_name": candidate_name,
                "candidate_phone": candidate_phone,
                "candidate_location": candidate_location,
                "employer_history": "",
                "first_message": "",
            },
        }

        await el_ws.send(json.dumps(client_data))
        print(f"🔗 [EMP_BRIDGE] Client data sent: {company} / {job_title} / {candidate_name}", flush=True)

        # Start bidirectional relay IMMEDIATELY
        vobiz_to_el = asyncio.create_task(_relay_vobiz_to_elevenlabs(vobiz_ws, el_ws, state))
        el_to_vobiz = asyncio.create_task(_relay_elevenlabs_to_vobiz(el_ws, vobiz_ws, state))

        if transfer_event:
            async def _wait_for_transfer():
                await transfer_event.wait()

            transfer_waiter = asyncio.create_task(_wait_for_transfer())
            done, pending = await asyncio.wait(
                [vobiz_to_el, el_to_vobiz, transfer_waiter],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if transfer_event.is_set():
                print(f"🔗 [EMP_BRIDGE] Transfer triggered, starting conference bridge", flush=True)
                for task in pending:
                    task.cancel()
                await _do_conference_bridge(call_id, job_context, el_ws)
                el_ws = None
            else:
                for task in pending:
                    task.cancel()
        else:
            done, pending = await asyncio.wait(
                [vobiz_to_el, el_to_vobiz],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔗 [EMP_BRIDGE] EL connection closed: {e}", flush=True)
    except asyncio.TimeoutError:
        print(f"🔗 [EMP_BRIDGE] EL init timeout for {call_id}", flush=True)
    except Exception as e:
        print(f"🔗 [EMP_BRIDGE] Bridge error: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
    finally:
        if el_ws:
            try:
                await el_ws.close()
            except Exception:
                pass
        conv_id = state.get("conversation_id")
        if conv_id:
            async def _cleanup():
                await asyncio.sleep(300)
                _employer_conversation_cache.pop(conv_id, None)
            asyncio.create_task(_cleanup())

        try:
            await vobiz_ws.close()
        except Exception:
            pass

        print(
            f"🔗 [EMP_BRIDGE] Bridge closed: call_id={call_id} "
            f"vobiz_in={state['vobiz_chunks_in']} el_out={state['el_chunks_out']}"
        )
