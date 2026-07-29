"""
WebSocket bridge between Vobiz audio stream and ElevenLabs Conversation API.

When a caller dials the Vobiz number:
1. Vobiz hits our answer_url → we return <Stream> XML pointing here
2. Vobiz opens a bidirectional WebSocket, streaming caller audio (mulaw 8kHz)
3. This bridge opens a WebSocket to ElevenLabs Conversation API
4. Audio is relayed bidirectionally with format conversion:
   - Caller → ElevenLabs: mulaw 8kHz → PCM 16-bit 16kHz
   - ElevenLabs → Caller: PCM 16kHz → mulaw 8kHz (chunked into 160-byte frames)
"""

import asyncio
import audioop
import base64
import concurrent.futures
import json
import math
import os
import struct
import threading
import time
import traceback

import httpx
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.webhooks import _call_phone_cache, _fetch_jobhai_jobs_summary, _inbound_lc_business_sessions, _inbound_lc_sessions
from api.vobiz_routes import _inbound_call_uuids
from models.switch_models import LiveConnectStatus
from services.live_connect_service import get_session, update_session_status
from services.vobiz_service import vobiz_service
from models.sql_models import CallerMemory
from utils.postgres import get_db

router = APIRouter(tags=["VobizBridge"])

ELEVENLABS_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation"

# Bridge stop events: normalized_phone → asyncio.Event
# When set, the bridge relay loop exits so the stream ends and <Redirect> fires.
_bridge_stop_events: dict[str, asyncio.Event] = {}

# Vobiz sends/expects 160-byte mulaw chunks (20ms at 8kHz)
MULAW_CHUNK_SIZE = 160

# Cache for open jobs text — avoids slow Firestore queries on every call
_open_jobs_cache = {"text": "", "fetched_at": 0.0}
_OPEN_JOBS_CACHE_TTL = 60  # seconds

# Dedicated thread pool for Firestore calls. When Firestore hits 429 quota,
# the SDK retries internally for up to 300s, holding the thread hostage.
# Using a separate pool prevents stuck workers from blocking the default
# asyncio thread pool (which would kill ALL bridge connections).
_FIRESTORE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=30, thread_name_prefix="firestore"
)


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


def _fetch_caller_context(phone: str) -> dict:
    """
    Fetch caller context from PostgreSQL caller_memory table for returning caller awareness.
    Returns dict with keys: user_profile, extraction_data, conversation_summary.
    """
    import json as _json
    normalized = _normalize_phone(phone)
    user_profile_text = ""
    conversation_summary_text = ""

    try:
        db = get_db()
        try:
            row = db.query(CallerMemory).filter(CallerMemory.phone == normalized).first()
        finally:
            db.close()

        if row:
            parts = []
            if row.name:
                parts.append(f"Name: {row.name}")
            if row.total_calls:
                parts.append(f"Previous calls: {row.total_calls}")
            if row.last_outcome and row.last_outcome != "unknown":
                parts.append(f"Last outcome: {row.last_outcome}")

            profile = _json.loads(row.profile) if row.profile else {}
            known = _json.loads(row.known_details) if row.known_details else {}
            last_jobs = _json.loads(row.last_jobs_pitched) if row.last_jobs_pitched else []

            if last_jobs:
                parts.append(f"Last jobs pitched: {', '.join(last_jobs)}")

            if profile:
                for field, label in [
                    ("experience_years", "Experience"), ("desired_role", "Wants"),
                    ("city", "City"), ("employment_status", "Status"),
                ]:
                    val = profile.get(field, "")
                    if val:
                        parts.append(f"{label}: {val}")
                sal_min = profile.get("salary_min", 0)
                sal_max = profile.get("salary_max", 0)
                if sal_min or sal_max:
                    parts.append(f"Salary: Rs {sal_min or '?'}-{sal_max or '?'}/month")
            elif known:
                for k, v in known.items():
                    if v:
                        parts.append(f"{k}: {v}")

            if parts:
                user_profile_text = "RETURNING CALLER — " + "; ".join(parts)
            if row.last_conversation_summary:
                conversation_summary_text = f"Last call summary: {row.last_conversation_summary}"

        print(
            f"🔍 [BRIDGE] Caller context for {normalized}: "
            f"profile={len(user_profile_text)}c, summary={len(conversation_summary_text)}c"
        )
    except Exception as e:
        print(f"⚠️ [BRIDGE] Error fetching caller context: {e}")

    return {
        "user_profile": user_profile_text or "New caller — no previous data.",
        "extraction_data": "No prior extraction data.",
        "conversation_summary": conversation_summary_text or "No previous conversations.",
    }


def _fetch_open_jobs_text() -> str:
    """Return PG staffing job listings for Jyoti's {{open_jobs}} dynamic variable."""
    try:
        from services.pg_jobs_service import get_pg_jobs_text
        return get_pg_jobs_text()
    except Exception as e:
        print(f"❌ [BRIDGE] Error fetching PG jobs: {e}")
        return "No open positions right now."


def _mulaw_8k_to_pcm_16k(mulaw_bytes: bytes) -> bytes:
    """Convert mulaw 8kHz audio to PCM 16-bit 16kHz."""
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return pcm_16k


def _pcm_16k_to_mulaw_8k(pcm_bytes: bytes) -> bytes:
    """Convert PCM 16-bit 16kHz audio to mulaw 8kHz."""
    pcm_8k, _ = audioop.ratecv(pcm_bytes, 2, 1, 16000, 8000, None)
    mulaw_8k = audioop.lin2ulaw(pcm_8k, 2)
    return mulaw_8k


JYOTI_VOICE_ID = "mActWQg9kibLro6Z2ouY"
JYOTI_TTS_MODEL = "eleven_flash_v2_5"


async def _lc_tts_intro(vobiz_ws: WebSocket, stream_id: str, text: str) -> None:
    """Generate TTS audio via ElevenLabs and play it to a Vobiz WebSocket."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        print("⚠️ [BRIDGE] LC TTS: no API key, skipping")
        return
    try:
        print(f"🔗 [BRIDGE] LC TTS: generating audio for stream_id={stream_id}, text={text[:60]}...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{JYOTI_VOICE_ID}",
                headers={"xi-api-key": api_key},
                json={"text": text, "model_id": JYOTI_TTS_MODEL},
                params={"output_format": "ulaw_8000"},
            )
            resp.raise_for_status()
            mulaw_audio = resp.content
        play_duration = len(mulaw_audio) / 8000
        print(f"🔗 [BRIDGE] LC TTS: got {len(mulaw_audio)} bytes ({play_duration:.1f}s), sending frames...")
        for i in range(0, len(mulaw_audio), MULAW_CHUNK_SIZE):
            frame = mulaw_audio[i : i + MULAW_CHUNK_SIZE]
            msg = {
                "event": "playAudio",
                "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000,
                          "payload": base64.b64encode(frame).decode()},
                "streamId": stream_id,
            }
            await vobiz_ws.send_text(json.dumps(msg))
        # Wait for audio to finish playing before returning
        print(f"🔗 [BRIDGE] LC TTS: frames sent, waiting {play_duration:.1f}s for playback")
        await asyncio.sleep(play_duration)
        print(f"🔗 [BRIDGE] LC TTS: playback done")
    except Exception as e:
        print(f"⚠️ [BRIDGE] LC TTS intro failed: {e}")
        traceback.print_exc()


async def _lc_direct_relay(
    source_ws: WebSocket, dest_ws: WebSocket,
    stop_event: asyncio.Event, session: dict,
    dest_stream_key: str,
) -> None:
    """Relay mulaw audio from candidate to business Vobiz WebSocket."""
    chunks = 0
    if "_recording_candidate_audio" not in session:
        session["_recording_candidate_audio"] = bytearray()
    try:
        while not stop_event.is_set():
            raw = await source_ws.receive_text()
            event = json.loads(raw)
            if event.get("event") == "media":
                payload_b64 = event.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue
                try:
                    recording_buf = session.get("_recording_candidate_audio")
                    if recording_buf is not None:
                        recording_buf.extend(base64.b64decode(payload_b64))
                except Exception:
                    pass
                dest_stream_id = session.get(dest_stream_key, "")
                if not dest_stream_id:
                    continue
                msg = {
                    "event": "playAudio",
                    "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000,
                              "payload": payload_b64},
                    "streamId": dest_stream_id,
                }
                await dest_ws.send_text(json.dumps(msg))
                chunks += 1
            elif event.get("event") == "stop":
                break
    except (WebSocketDisconnect, Exception) as e:
        print(f"🔗 [BRIDGE] LC direct relay ended after {chunks} chunks: {type(e).__name__}: {e}")


@router.websocket("/ws/vobiz-bridge")
async def vobiz_elevenlabs_bridge(vobiz_ws: WebSocket):
    """
    WebSocket endpoint that Vobiz connects to via <Stream>.
    Bridges audio between the caller and ElevenLabs agent.
    """
    await vobiz_ws.accept()
    print("=" * 60)
    print("🔗 [BRIDGE] Vobiz WebSocket connected")

    # Read caller phone from query params (passed by answer webhook via Stream URL)
    caller_phone = vobiz_ws.query_params.get("caller_phone", "")
    print(f"🔗 [BRIDGE] Caller phone: {caller_phone or '(not provided)'}")

    agent_id = os.getenv("ELEVENLABS_AGENT_ID", "agent_1101kfxtskyve0csns9bh7bedq9h")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    el_url = f"{ELEVENLABS_WS_URL}?agent_id={agent_id}"
    headers = {}
    if api_key:
        headers["xi-api-key"] = api_key

    # Bridge debug log — written to Firestore so we can check without SSH
    bridge_debug = {
        "caller_phone": caller_phone,
        "started_at": time.time(),
        "agent_id": agent_id,
        "steps": ["WS_ACCEPTED"],
    }

    def _bridge_log(step: str, extra: dict = None):
        bridge_debug["steps"].append(step)
        bridge_debug["last_step"] = step
        bridge_debug["last_step_at"] = time.time()
        if extra:
            bridge_debug.update(extra)
        print(f"🔗 [BRIDGE_LOG] {step}" + (f" {extra}" if extra else ""))

    # Shared state between relay tasks
    state = {
        "stream_id": None,
        "vobiz_chunks_in": 0,
        "el_chunks_out": 0,
        "el_frames_out": 0,
        "conversation_id": None,
        "el_audio_format": "unknown",
        "caller_phone": caller_phone,
    }

    el_ws = None
    try:
        _bridge_log("CONNECTING_EL")
        el_ws = await websockets.connect(
            el_url,
            additional_headers=headers,
        )
        _bridge_log("EL_CONNECTED")
        print("🔗 [BRIDGE] ElevenLabs WebSocket connected")

        # Wait for ElevenLabs conversation initiation
        init_msg = await asyncio.wait_for(el_ws.recv(), timeout=10)
        init_data = json.loads(init_msg)
        init_type = init_data.get("type")
        print(f"🔗 [BRIDGE] ElevenLabs init: type={init_type}")

        if init_type == "conversation_initiation_metadata":
            meta = init_data.get("conversation_initiation_metadata_event", {})
            state["conversation_id"] = meta.get("conversation_id", "")
            state["el_audio_format"] = meta.get("agent_output_audio_format", "unknown")
            print(f"🔗 [BRIDGE] Conversation ID: {state['conversation_id']}")
            print(f"🔗 [BRIDGE] Agent output format: {state['el_audio_format']}")
            print(f"🔗 [BRIDGE] User input format: {meta.get('user_input_audio_format', 'unknown')}")

            # Cache caller phone for post-call webhook SMS
            if caller_phone and state["conversation_id"]:
                _call_phone_cache[state["conversation_id"]] = caller_phone
                print(f"🔗 [BRIDGE] Cached caller phone {caller_phone} for conversation {state['conversation_id']}")

        _bridge_log("EL_INIT_OK", {"conversation_id": state["conversation_id"]})

        # Fetch caller context and jobs with caching + strict timeout.
        # The relay MUST start quickly or the caller hears silence and hangs up.
        default_context = {
            "user_profile": "New caller — no previous data.",
            "extraction_data": "No prior extraction data.",
            "conversation_summary": "No previous conversations.",
        }

        # Use cached open jobs if fresh (avoids slow Firestore query)
        # IMPORTANT: all Firestore fetches use _FIRESTORE_EXECUTOR (not default
        # asyncio thread pool) so stuck 429-retry workers don't kill the bridge.
        loop = asyncio.get_running_loop()
        now = time.time()
        if _open_jobs_cache["text"] and (now - _open_jobs_cache["fetched_at"]) < _OPEN_JOBS_CACHE_TTL:
            open_jobs_text = _open_jobs_cache["text"]
            # Only need to fetch caller context (single doc read, fast)
            try:
                if caller_phone:
                    caller_context = await asyncio.wait_for(
                        loop.run_in_executor(_FIRESTORE_EXECUTOR, _fetch_caller_context, caller_phone),
                        timeout=3.0,
                    )
                else:
                    caller_context = default_context
            except (asyncio.TimeoutError, Exception):
                print("⚠️ [BRIDGE] Caller context fetch timed out or failed")
                caller_context = default_context
        else:
            # Cache cold — fetch both in parallel with 3s timeout
            try:
                jobs_future = loop.run_in_executor(_FIRESTORE_EXECUTOR, _fetch_open_jobs_text)
                if caller_phone:
                    ctx_future = loop.run_in_executor(_FIRESTORE_EXECUTOR, _fetch_caller_context, caller_phone)
                    results = await asyncio.wait_for(asyncio.gather(jobs_future, ctx_future), timeout=3.0)
                    open_jobs_text = results[0]
                    caller_context = results[1]
                else:
                    open_jobs_text = await asyncio.wait_for(jobs_future, timeout=3.0)
                    caller_context = default_context
                _open_jobs_cache["text"] = open_jobs_text
                _open_jobs_cache["fetched_at"] = time.time()
            except (asyncio.TimeoutError, Exception):
                print("⚠️ [BRIDGE] Context fetch timed out or failed, proceeding with defaults")
                open_jobs_text = _fetch_jobhai_jobs_summary() or "No open positions right now."
                caller_context = default_context
                # Warm cache in background for next call (daemon thread, won't block pool)
                threading.Thread(target=lambda: _open_jobs_cache.update({"text": _fetch_open_jobs_text(), "fetched_at": time.time()}), daemon=True).start()
        client_data = {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": {
                "caller_phone": caller_phone,
                "open_jobs": open_jobs_text,
                "user_profile": caller_context["user_profile"],
                "extraction_data": caller_context["extraction_data"],
                "conversation_summary": caller_context["conversation_summary"],
            },
        }
        await el_ws.send(json.dumps(client_data))
        _bridge_log("CLIENT_DATA_SENT", {"jobs_chars": len(open_jobs_text)})
        print(f"🔗 [BRIDGE] Sent client data to EL: caller_phone={caller_phone}, jobs={len(open_jobs_text)} chars, context={len(caller_context['user_profile'])}c")

        # Run both relay directions concurrently
        _bridge_log("RELAY_STARTED")
        vobiz_to_el = asyncio.create_task(
            _relay_vobiz_to_elevenlabs(vobiz_ws, el_ws, state)
        )
        el_to_vobiz = asyncio.create_task(
            _relay_elevenlabs_to_vobiz(el_ws, vobiz_ws, state)
        )

        # Register stop event so live connect can force-end the bridge
        stop_event = asyncio.Event()
        normalized_for_stop = _normalize_phone(caller_phone) if caller_phone else ""
        if normalized_for_stop:
            _bridge_stop_events[normalized_for_stop] = stop_event

        async def _wait_for_stop():
            await stop_event.wait()

        stop_task = asyncio.create_task(_wait_for_stop())

        done, pending = await asyncio.wait(
            [vobiz_to_el, el_to_vobiz, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        _bridge_log("RELAY_ENDED", {
            "vobiz_chunks": state["vobiz_chunks_in"],
            "el_chunks": state["el_chunks_out"],
        })
        for task in pending:
            task.cancel()

    except websockets.exceptions.ConnectionClosed as e:
        _bridge_log("ERROR_EL_CLOSED", {"error": str(e)})
        print(f"🔗 [BRIDGE] ElevenLabs connection closed: {e}")
    except asyncio.TimeoutError:
        _bridge_log("ERROR_EL_TIMEOUT")
        print("🔗 [BRIDGE] ElevenLabs init timeout")
    except WebSocketDisconnect:
        _bridge_log("ERROR_VOBIZ_DISCONNECT")
        print("🔗 [BRIDGE] Vobiz disconnected")
    except Exception as e:
        _bridge_log("ERROR", {"error": f"{type(e).__name__}: {e}"})
        print(f"🔗 [BRIDGE] Error: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        if el_ws:
            await el_ws.close()

        # Clean up stop event
        if normalized_for_stop:
            _bridge_stop_events.pop(normalized_for_stop, None)

        # Check for pending inbound live connect transfer.
        # Instead of closing the stream and redirecting, we keep the SAME Vobiz
        # WebSocket open and switch to hold mode (play hold audio + wait for
        # business bridge). This avoids XML redirect complexity.
        lc_session = None
        pending_session_id = ""
        normalized_phone = _normalize_phone(caller_phone) if caller_phone else ""
        if normalized_phone:
            pending_session_id = _inbound_lc_sessions.pop(normalized_phone, "")
            if pending_session_id and pending_session_id != "__transferred__":
                lc_session = get_session(pending_session_id)

        if lc_session:
            # === INLINE LC HOLD MODE ===
            # Keep the same Vobiz WS open, play hold audio, wait for business
            print(f"🔗 [BRIDGE] Entering LC HOLD mode for session {pending_session_id}")
            stream_id = state.get("stream_id", "")

            # Clear any buffered ElevenLabs audio
            if stream_id:
                try:
                    await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": stream_id}))
                except Exception:
                    pass

            # Update session with candidate WS info
            lc_session["_candidate_vobiz_ws"] = vobiz_ws
            lc_session["_candidate_stream_id"] = stream_id
            lc_session["_candidate_ws_connected"] = True
            if not lc_session.get("_candidate_ready"):
                lc_session["_candidate_ready"] = asyncio.Event()
            lc_session["_candidate_ready"].set()

            # Play hold audio until business bridge ready or session ends
            hold_stop = asyncio.Event()
            business_ready = lc_session.get("_business_bridge_ready") or asyncio.Event()
            session_ended = lc_session.get("_session_ended") or asyncio.Event()

            async def _wait_hold_end():
                br_task = asyncio.create_task(business_ready.wait())
                se_task = asyncio.create_task(session_ended.wait())
                done_set, pend_set = await asyncio.wait(
                    [br_task, se_task], return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pend_set:
                    t.cancel()
                hold_stop.set()

            async def _play_hold(ws, sid, stop_ev):
                """Play silence + periodic beep on the Vobiz WS."""
                try:
                    silence_frame = b"\xff" * 160
                    beep_frames = []
                    for fi in range(10):
                        pcm = []
                        for i in range(160):
                            t = (fi * 160 + i) / 8000
                            pcm.append(int(16000 * math.sin(2 * 3.14159 * 440 * t)))
                        pcm_bytes = struct.pack(f"<{len(pcm)}h", *pcm)
                        beep_frames.append(audioop.lin2ulaw(pcm_bytes, 2))

                    while not stop_ev.is_set():
                        for _ in range(150):  # 3s silence
                            if stop_ev.is_set():
                                return
                            msg = {
                                "event": "playAudio",
                                "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000,
                                          "payload": base64.b64encode(silence_frame).decode()},
                                "streamId": sid,
                            }
                            await ws.send_text(json.dumps(msg))
                            await asyncio.sleep(0.020)
                        for bf in beep_frames:
                            if stop_ev.is_set():
                                return
                            msg = {
                                "event": "playAudio",
                                "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000,
                                          "payload": base64.b64encode(bf).decode()},
                                "streamId": sid,
                            }
                            await ws.send_text(json.dumps(msg))
                            await asyncio.sleep(0.020)
                except Exception as e:
                    print(f"🔗 [BRIDGE] Hold audio error: {e}")

            async def _drain_hold(ws, stop_ev):
                """Consume incoming Vobiz media during hold (don't relay anywhere)."""
                try:
                    while not stop_ev.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.receive_text(), timeout=1.0)
                            event = json.loads(raw)
                            if event.get("event") == "start":
                                new_sid = event.get("streamId") or event.get("start", {}).get("streamId", "")
                                if new_sid:
                                    state["stream_id"] = new_sid
                                    lc_session["_candidate_stream_id"] = new_sid
                            elif event.get("event") == "stop":
                                stop_ev.set()
                                break
                        except asyncio.TimeoutError:
                            continue
                except (WebSocketDisconnect, Exception):
                    stop_ev.set()

            hold_waiter = asyncio.create_task(_wait_hold_end())
            hold_player = asyncio.create_task(_play_hold(vobiz_ws, stream_id, hold_stop))
            drain_task = asyncio.create_task(_drain_hold(vobiz_ws, hold_stop))
            await asyncio.gather(hold_waiter, hold_player, drain_task, return_exceptions=True)

            # HOLD exited — check if business bridge is ready or session ended
            if business_ready.is_set() and not session_ended.is_set():
                print(f"🔗 [BRIDGE] LC HOLD: business ready — entering DIRECT relay")
                winner_phone = lc_session.get("_winner_phone")
                winner_attempt = lc_session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
                business_ws = winner_attempt.get("vobiz_ws") or lc_session.get("_business_vobiz_ws")
                business_stream_id = winner_attempt.get("stream_id") or lc_session.get("_business_stream_id")
                candidate_stream_id = lc_session.get("_candidate_stream_id") or stream_id

                if business_ws and business_stream_id:
                    lc_session["bridge_started_at"] = time.time()
                    update_session_status(pending_session_id, LiveConnectStatus.BRIDGED)
                    await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": candidate_stream_id}))

                    # Play TTS intro to candidate (await so it plays before relay starts)
                    business_name = lc_session.get("business_name", "employer")
                    await _lc_tts_intro(
                        vobiz_ws, candidate_stream_id,
                        f"Badhai ho! {business_name} ka HR line pe hai. Himmat se baat karo, all the best!",
                    )

                    # Direct relay: candidate audio → business WS
                    try:
                        await _lc_direct_relay(
                            source_ws=vobiz_ws,
                            dest_ws=business_ws,
                            stop_event=session_ended,
                            session=lc_session,
                            dest_stream_key="_business_stream_id",
                        )
                    except Exception as e:
                        print(f"🔗 [BRIDGE] LC DIRECT relay error: {e}")
                else:
                    print(f"⚠️ [BRIDGE] LC HOLD: business ready but no WS/stream_id")
            else:
                exhausted = lc_session.get("_businesses_exhausted")
                if exhausted:
                    print(f"🔗 [BRIDGE] LC HOLD: businesses exhausted ({exhausted})")
                else:
                    print(f"🔗 [BRIDGE] LC HOLD: session ended without business")

            # Clean up — hang up the Vobiz call
            call_uuid = lc_session.get("candidate_call_uuid") or _inbound_call_uuids.get(normalized_phone, "")
            if call_uuid:
                try:
                    await vobiz_service.hangup_call(call_uuid)
                except Exception:
                    pass
            try:
                await vobiz_ws.close()
            except Exception:
                pass

        else:
            # No pending LC session — normal bridge close
            if normalized_phone:
                # Check for pending BUSINESS live connect session (reverse flow)
                pending_biz_session_id = _inbound_lc_business_sessions.pop(normalized_phone, "")
                if pending_biz_session_id:
                    print(f"🔗 [BRIDGE] Pending biz LC session {pending_biz_session_id} — not handled here yet")

                call_uuid = _inbound_call_uuids.get(normalized_phone, "")
                if call_uuid:
                    try:
                        print(f"🔗 [BRIDGE] Hanging up Vobiz call {call_uuid}")
                        await vobiz_service.hangup_call(call_uuid)
                    except Exception as e:
                        print(f"⚠️ [BRIDGE] Failed to hangup Vobiz call: {e}")
            try:
                await vobiz_ws.close()
            except Exception:
                pass

        print("=" * 60)
        print(f"🔗 [BRIDGE] === BRIDGE CLOSED ===")
        print(f"🔗 [BRIDGE] Caller: {state.get('caller_phone', 'N/A')}")
        print(f"🔗 [BRIDGE] Conversation: {state.get('conversation_id', 'N/A')}")
        print(f"🔗 [BRIDGE] Stream ID: {state.get('stream_id', 'N/A')}")
        print(f"🔗 [BRIDGE] Audio: Vobiz→EL={state['vobiz_chunks_in']} chunks, EL→Vobiz={state['el_chunks_out']} chunks ({state['el_frames_out']} frames)")
        print(f"🔗 [BRIDGE] EL audio format: {state.get('el_audio_format', 'unknown')}")
        if lc_session:
            print(f"🔗 [BRIDGE] >>> LC session {pending_session_id} handled inline")
        print("=" * 60)


async def _relay_vobiz_to_elevenlabs(vobiz_ws: WebSocket, el_ws, state: dict):
    """Relay audio from Vobiz (caller) to ElevenLabs agent."""
    first_msg_logged = False
    try:
        while True:
            raw = await vobiz_ws.receive_text()
            event = json.loads(raw)
            event_type = event.get("event")

            if not first_msg_logged:
                print(f"🔗 [BRIDGE] First Vobiz raw msg: {raw[:300]}")
                first_msg_logged = True

            if event_type == "media":
                payload_b64 = event.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue

                mulaw_bytes = base64.b64decode(payload_b64)
                pcm_16k = _mulaw_8k_to_pcm_16k(mulaw_bytes)
                pcm_b64 = base64.b64encode(pcm_16k).decode("utf-8")

                await el_ws.send(json.dumps({
                    "user_audio_chunk": pcm_b64,
                }))

                state["vobiz_chunks_in"] += 1
                if state["vobiz_chunks_in"] == 1:
                    print(f"🔗 [BRIDGE] First Vobiz→EL chunk ({len(mulaw_bytes)}B mulaw → {len(pcm_16k)}B pcm)")
                elif state["vobiz_chunks_in"] % 200 == 0:
                    print(f"🔗 [BRIDGE] Vobiz→EL: {state['vobiz_chunks_in']} chunks")

            elif event_type == "start":
                # Vobiz uses "streamId" (not "streamSid")
                start_data = event.get("start", {})
                stream_id = (
                    event.get("streamId")
                    or start_data.get("streamId")
                    or event.get("streamSid")
                    or start_data.get("streamSid")
                    or ""
                )
                state["stream_id"] = stream_id
                print(f"🔗 [BRIDGE] Vobiz stream started. streamId={stream_id}")
                print(f"🔗 [BRIDGE] Start event: {json.dumps(event)[:400]}")

            elif event_type == "stop":
                print(f"🔗 [BRIDGE] Vobiz stream stopped after {state['vobiz_chunks_in']} chunks")
                break

            elif event_type == "connected":
                print(f"🔗 [BRIDGE] Vobiz connected event: {json.dumps(event)[:200]}")

            elif event_type == "incorrectPayload":
                print(f"⚠️ [BRIDGE] Vobiz incorrectPayload: {json.dumps(event)[:300]}")

            else:
                print(f"🔗 [BRIDGE] Vobiz event: {event_type} → {json.dumps(event)[:200]}")

    except WebSocketDisconnect:
        print(f"🔗 [BRIDGE] Vobiz disconnected (relay) after {state['vobiz_chunks_in']} chunks")
    except Exception as e:
        print(f"🔗 [BRIDGE] Vobiz→EL error: {type(e).__name__}: {e}")
        traceback.print_exc()


async def _relay_elevenlabs_to_vobiz(el_ws, vobiz_ws: WebSocket, state: dict):
    """
    Relay audio from ElevenLabs agent to Vobiz (caller).

    ElevenLabs sends large audio chunks (~1-2 seconds each).
    Vobiz expects small 160-byte mulaw frames (20ms each).
    We split each ElevenLabs chunk into multiple Vobiz-sized frames
    and send them using the playAudio event with streamId.
    """
    try:
        async for message in el_ws:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "audio":
                audio_event = data.get("audio_event", {})
                audio_b64 = audio_event.get("audio_base_64", "")
                if not audio_b64:
                    if state["el_chunks_out"] == 0:
                        print(f"🔗 [BRIDGE] EL audio msg empty. Keys={list(data.keys())}")
                        print(f"🔗 [BRIDGE] Full msg: {json.dumps(data)[:400]}")
                    continue

                pcm_bytes = base64.b64decode(audio_b64)
                mulaw_bytes = _pcm_16k_to_mulaw_8k(pcm_bytes)

                state["el_chunks_out"] += 1

                # Split into 160-byte frames (20ms at 8kHz mulaw)
                # and send each as a separate playAudio message
                frames_sent = 0
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
                    frames_sent += 1
                    state["el_frames_out"] += 1

                if state["el_chunks_out"] == 1:
                    print(f"🔗 [BRIDGE] First EL→Vobiz: {len(pcm_bytes)}B pcm → {len(mulaw_bytes)}B mulaw → {frames_sent} frames")
                    first_frame_b64 = base64.b64encode(mulaw_bytes[:MULAW_CHUNK_SIZE]).decode("utf-8")
                    sample_msg = {
                        "event": "playAudio",
                        "media": {
                            "contentType": "audio/x-mulaw",
                            "sampleRate": 8000,
                            "payload": first_frame_b64[:40] + "...",
                        },
                        "streamId": state["stream_id"],
                    }
                    print(f"🔗 [BRIDGE] Sample playAudio: {json.dumps(sample_msg)}")
                elif state["el_chunks_out"] % 10 == 0:
                    print(f"🔗 [BRIDGE] EL→Vobiz: {state['el_chunks_out']} chunks, {state['el_frames_out']} total frames")

            elif msg_type == "agent_response":
                text = data.get("agent_response_event", {}).get("agent_response", "")
                print(f"🤖 [BRIDGE] Agent: {text[:150]}")

            elif msg_type == "user_transcript":
                text = data.get("user_transcription_event", {}).get("user_transcript", "")
                print(f"👤 [BRIDGE] User: {text[:150]}")

            elif msg_type == "conversation_initiation_metadata":
                print(f"🔗 [BRIDGE] Late init metadata: {json.dumps(data)[:300]}")

            elif msg_type == "ping":
                ping_event = data.get("ping_event", {})
                await el_ws.send(json.dumps({
                    "type": "pong",
                    "event_id": ping_event.get("event_id"),
                }))

            elif msg_type == "interruption":
                print("🔗 [BRIDGE] Agent interrupted by user")
                if state.get("stream_id"):
                    await vobiz_ws.send_text(json.dumps({
                        "event": "clearAudio",
                        "streamId": state["stream_id"],
                    }))

            elif msg_type == "agent_response_correction":
                print(f"🔗 [BRIDGE] EL msg type={msg_type}: {json.dumps(data)[:200]}")

            else:
                print(f"🔗 [BRIDGE] EL msg type={msg_type}: {json.dumps(data)[:200]}")

    except websockets.exceptions.ConnectionClosed:
        print(f"🔗 [BRIDGE] ElevenLabs disconnected after {state['el_chunks_out']} chunks ({state['el_frames_out']} frames)")
    except Exception as e:
        print(f"🔗 [BRIDGE] EL→Vobiz error: {type(e).__name__}: {e}")
        traceback.print_exc()
