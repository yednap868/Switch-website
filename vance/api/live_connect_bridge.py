"""
Multi-mode WebSocket bridge for Live Connect.

Each connection (candidate or business) has 3 modes:
  AI     → relay audio to/from ElevenLabs (same as vobiz_bridge.py)
  HOLD   → play hold audio (silence + periodic beep) via playAudio
  DIRECT → relay audio directly to the other party's Vobiz WebSocket

Candidate lifecycle: AI screening → HOLD → DIRECT
Business lifecycle:  AI intro → DIRECT (per-attempt, winner only)
"""

import asyncio
import audioop
import base64
import json
import math
import os
import struct
import time
import traceback

import httpx
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.webhooks import _call_phone_cache
from api.vobiz_bridge import (
    ELEVENLABS_WS_URL,
    MULAW_CHUNK_SIZE,
    _fetch_caller_context,
    _fetch_open_jobs_text,
    _mulaw_8k_to_pcm_16k,
    _pcm_16k_to_mulaw_8k,
)
from services.live_connect_service import end_session, get_session, update_session_status
from services.vobiz_service import vobiz_service
from models.switch_models import LiveConnectStatus

router = APIRouter(tags=["LiveConnectBridge"])

# Pre-generate hold audio frames at module load time
# Silence: 0xFF repeated (mulaw silence = 0xFF)
_SILENCE_FRAME = b"\xff" * MULAW_CHUNK_SIZE  # 160 bytes = 20ms

# 440Hz beep tone in mulaw 8kHz (generate 200ms = 10 frames)
_BEEP_FRAMES: list[bytes] = []
_BEEP_DURATION_FRAMES = 10  # 10 * 20ms = 200ms


def _generate_beep_frames() -> list[bytes]:
    """Generate 440Hz beep tone as mulaw 8kHz frames."""
    frames = []
    sample_rate = 8000
    frequency = 440
    amplitude = 16000  # ~half of int16 max
    samples_per_frame = MULAW_CHUNK_SIZE  # 160 samples at 8kHz = 20ms

    for frame_idx in range(_BEEP_DURATION_FRAMES):
        pcm_samples = []
        for i in range(samples_per_frame):
            t = (frame_idx * samples_per_frame + i) / sample_rate
            sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
            pcm_samples.append(sample)

        pcm_bytes = struct.pack(f"<{len(pcm_samples)}h", *pcm_samples)
        mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)
        frames.append(mulaw_bytes)
    return frames


_BEEP_FRAMES = _generate_beep_frames()

# Cache for open jobs text (same for all bridges, no need to fetch 20 times)
_open_jobs_cache = {"text": "", "fetched_at": 0.0}
_OPEN_JOBS_CACHE_TTL = 60  # seconds

# Hold pattern: 3 seconds silence (150 frames) + 200ms beep (10 frames)
_SILENCE_FRAMES_BETWEEN_BEEPS = 150  # 150 * 20ms = 3 seconds


async def _play_hold_audio(vobiz_ws: WebSocket, stream_id: str, stop_event: asyncio.Event) -> None:
    """Play hold audio (silence + periodic beep) until stop_event is set."""
    try:
        frame_interval = 0.020  # 20ms per frame

        while not stop_event.is_set():
            # Play silence frames
            for _ in range(_SILENCE_FRAMES_BETWEEN_BEEPS):
                if stop_event.is_set():
                    return
                frame_b64 = base64.b64encode(_SILENCE_FRAME).decode("utf-8")
                msg = {
                    "event": "playAudio",
                    "media": {
                        "contentType": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "payload": frame_b64,
                    },
                    "streamId": stream_id,
                }
                await vobiz_ws.send_text(json.dumps(msg))
                await asyncio.sleep(frame_interval)

            # Play beep
            for beep_frame in _BEEP_FRAMES:
                if stop_event.is_set():
                    return
                frame_b64 = base64.b64encode(beep_frame).decode("utf-8")
                msg = {
                    "event": "playAudio",
                    "media": {
                        "contentType": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "payload": frame_b64,
                    },
                    "streamId": stream_id,
                }
                await vobiz_ws.send_text(json.dumps(msg))
                await asyncio.sleep(frame_interval)

    except (WebSocketDisconnect, Exception) as e:
        print(f"🔗 [LC_BRIDGE] Hold audio stopped: {type(e).__name__}: {e}")


async def _relay_vobiz_to_elevenlabs(vobiz_ws: WebSocket, el_ws, state: dict) -> None:
    """Relay audio from Vobiz (caller) to ElevenLabs agent."""
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
                print(f"🔗 [LC_BRIDGE] Stream started. streamId={stream_id}")

            elif event_type == "stop":
                print(f"🔗 [LC_BRIDGE] Stream stopped")
                break

            elif event_type == "connected":
                pass

    except WebSocketDisconnect:
        print(f"🔗 [LC_BRIDGE] Vobiz disconnected (relay)")
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] Vobiz→EL error: {type(e).__name__}: {e}")


async def _relay_elevenlabs_to_vobiz(el_ws, vobiz_ws: WebSocket, state: dict) -> None:
    """Relay audio from ElevenLabs agent to Vobiz (caller)."""
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
                print(f"🤖 [LC_BRIDGE] Agent: {text[:150]}")

            elif msg_type == "user_transcript":
                text = data.get("user_transcription_event", {}).get("user_transcript", "")
                print(f"👤 [LC_BRIDGE] User: {text[:150]}")

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
        print(f"🔗 [LC_BRIDGE] ElevenLabs disconnected")
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] EL→Vobiz error: {type(e).__name__}: {e}")


async def _run_ai_mode(
    vobiz_ws: WebSocket,
    state: dict,
    call_type: str,
    session: dict,
    disconnect_signal: asyncio.Event = None,
) -> None:
    """
    Run AI mode: connect to ElevenLabs and bridge audio.
    Returns when ElevenLabs conversation ends OR disconnect_signal is set.

    The disconnect_signal allows the tool webhooks (connect_to_business,
    accept_connect) to force-close the ElevenLabs connection, so we don't
    rely on the agent calling end_call.
    """
    agent_id = os.getenv("ELEVENLABS_LIVE_CONNECT_AGENT_ID") or os.getenv("ELEVENLABS_AGENT_ID", "")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    el_url = f"{ELEVENLABS_WS_URL}?agent_id={agent_id}"
    headers = {}
    if api_key:
        headers["xi-api-key"] = api_key

    el_ws = None
    try:
        el_ws = await websockets.connect(el_url, additional_headers=headers)
        print(f"🔗 [LC_BRIDGE] ElevenLabs connected for {call_type}")

        # Wait for init
        init_msg = await asyncio.wait_for(el_ws.recv(), timeout=10)
        init_data = json.loads(init_msg)
        if init_data.get("type") == "conversation_initiation_metadata":
            meta = init_data.get("conversation_initiation_metadata_event", {})
            conv_id = meta.get("conversation_id", "")
            state["conversation_id"] = conv_id
            print(f"🔗 [LC_BRIDGE] EL Conversation ID: {conv_id}")

            # Store conversation ID in session or attempt
            if call_type == "live_connect_candidate":
                session["candidate_conversation_id"] = conv_id
            elif call_type in ("live_connect_business", "live_connect_reverse_candidate"):
                # Store in per-attempt dict if available
                attempt_phone = state.get("attempt_phone", "")
                if attempt_phone:
                    attempt = session.get("_attempts", {}).get(attempt_phone)
                    if attempt:
                        attempt["conversation_id"] = conv_id
                else:
                    session["business_conversation_id"] = conv_id

            # Cache for post-call webhook
            caller_phone = state.get("caller_phone", "")
            if caller_phone and conv_id:
                _call_phone_cache[conv_id] = caller_phone

        # Build dynamic variables for ElevenLabs
        # Use cached open jobs text (same for all bridges — no need to fetch 20 times)
        caller_phone = state.get("caller_phone", "")
        now = time.time()
        if _open_jobs_cache["text"] and (now - _open_jobs_cache["fetched_at"]) < _OPEN_JOBS_CACHE_TTL:
            open_jobs_text = _open_jobs_cache["text"]
        else:
            open_jobs_text = await asyncio.to_thread(_fetch_open_jobs_text)
            _open_jobs_cache["text"] = open_jobs_text
            _open_jobs_cache["fetched_at"] = time.time()

        # For business bridges, skip caller context (it's the business phone, not useful)
        # For candidate bridges, fetch caller context normally
        if call_type == "live_connect_business":
            caller_context = {
                "user_profile": "Business call — no candidate profile needed.",
                "extraction_data": "",
                "conversation_summary": "",
            }
        elif caller_phone:
            caller_context = await asyncio.to_thread(_fetch_caller_context, caller_phone)
        else:
            caller_context = {
                "user_profile": "New caller — no previous data.",
                "extraction_data": "No prior extraction data.",
                "conversation_summary": "No previous conversations.",
            }

        dynamic_vars = {
            "caller_phone": caller_phone,
            "call_type": call_type,
            "open_jobs": open_jobs_text,
            "user_profile": caller_context["user_profile"],
            "extraction_data": caller_context["extraction_data"],
            "conversation_summary": caller_context["conversation_summary"],
            "session_id": session.get("id", ""),
        }

        # Add live connect specific context
        if call_type == "live_connect_candidate":
            dynamic_vars["candidate_name"] = session.get("candidate_name", "")
        elif call_type == "live_connect_business":
            dynamic_vars["screening_summary"] = session.get("screening_summary", "")
            dynamic_vars["candidate_name"] = session.get("candidate_name", "")
            screening_data = session.get("screening_data", {}) or {}
            dynamic_vars["candidate_experience"] = screening_data.get("candidate_experience_level", "")
            dynamic_vars["business_name"] = session.get("business_name", "")
            # Inject current job details from the per-attempt job
            attempt_phone = state.get("attempt_phone", "")
            current_job = {}
            if attempt_phone:
                attempt = session.get("_attempts", {}).get(attempt_phone)
                if attempt:
                    current_job = attempt.get("job") or {}
            if not current_job:
                current_job = session.get("current_job") or {}
            dynamic_vars["job_title"] = current_job.get("title", "")
            dynamic_vars["job_company"] = current_job.get("company", "")
            dynamic_vars["job_location"] = current_job.get("location", "")
            dynamic_vars["job_salary"] = str(current_job.get("salary_max", ""))
            dynamic_vars["job_role"] = current_job.get("title", "")
        elif call_type == "live_connect_reverse_candidate":
            screening_data = session.get("screening_data", {}) or {}
            dynamic_vars["candidate_name"] = session.get("candidate_name", "")
            dynamic_vars["business_name"] = session.get("business_name", "")
            dynamic_vars["job_role"] = screening_data.get("role_needed", "")
            dynamic_vars["job_salary"] = str(screening_data.get("salary_max", ""))
            dynamic_vars["requirement_summary"] = screening_data.get("requirement_summary", "")

        # Build first message as dynamic variable (agent references {{first_message}})
        if call_type == "live_connect_candidate":
            candidate_name = session.get("candidate_name", "")
            if candidate_name:
                dynamic_vars["first_message"] = (
                    f"Hellooo {candidate_name}! Main Jyoti bol rahi hoon, Switch se. Aapko achi job dilwati hoon! "
                    "Bas jaldi se batao — kya kaam karte ho aur kahan rehte ho?"
                )
            else:
                dynamic_vars["first_message"] = (
                    "Hellooo! Main Jyoti bol rahi hoon, Switch se. Aapko achi job dilwati hoon! "
                    "Pehle aapka naam bata dijiye, phir batao — kya kaam karte ho aur kahan rehte ho?"
                )
        elif call_type == "live_connect_business":
            candidate_name = session.get("candidate_name", "candidate")
            screening_summary = session.get("screening_summary", "")
            attempt_phone = state.get("attempt_phone", "")
            current_job = {}
            if attempt_phone:
                attempt = session.get("_attempts", {}).get(attempt_phone)
                if attempt:
                    current_job = attempt.get("job") or {}
            if not current_job:
                current_job = session.get("current_job") or {}
            job_title = current_job.get("title", "")
            summary_text = f" {screening_summary}." if screening_summary else ""
            job_text = f" Aapki {job_title} opening ke liye." if job_title else ""
            dynamic_vars["first_message"] = (
                f"Hello! Jyoti, Switch se. Ek achha candidate screen kiya hai abhi — "
                f"{candidate_name}.{summary_text}{job_text} Wo abhi phone pe hai, seedha connect kar doon?"
            )
        elif call_type == "live_connect_reverse_candidate":
            screening_data = session.get("screening_data", {}) or {}
            business_name = session.get("business_name", "ek business")
            role_needed = screening_data.get("role_needed", "staff")
            salary_max = screening_data.get("salary_max", "")
            salary_text = f" Salary {salary_max} tak." if salary_max else ""
            dynamic_vars["first_message"] = (
                f"Hello! Jyoti Switch se. Ek urgent opening hai — "
                f"{business_name} ko {role_needed} chahiye.{salary_text} "
                f"Abhi owner phone pe hai, directly connect karwa doon. Interested ho?"
            )

        client_data = {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": dynamic_vars,
        }
        await el_ws.send(json.dumps(client_data))
        print(f"🔗 [LC_BRIDGE] Sent client data to EL: call_type={call_type}")

        # Run relay + optional disconnect signal
        vobiz_to_el = asyncio.create_task(_relay_vobiz_to_elevenlabs(vobiz_ws, el_ws, state))
        el_to_vobiz = asyncio.create_task(_relay_elevenlabs_to_vobiz(el_ws, vobiz_ws, state))

        tasks = [vobiz_to_el, el_to_vobiz]

        if disconnect_signal:
            async def _wait_disconnect():
                await disconnect_signal.wait()
                # Give the agent 3 seconds to finish its last sentence
                await asyncio.sleep(3)
                print(f"🔗 [LC_BRIDGE] Disconnect signal received for {call_type}, closing EL")
                await el_ws.close()

            disconnect_task = asyncio.create_task(_wait_disconnect())
            tasks.append(disconnect_task)

        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔗 [LC_BRIDGE] EL connection closed: {e}")
    except asyncio.TimeoutError:
        print("🔗 [LC_BRIDGE] EL init timeout")
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] AI mode error: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        if el_ws:
            try:
                await el_ws.close()
            except Exception:
                pass


async def _drain_vobiz_media(
    vobiz_ws: WebSocket, state: dict, stop_event: asyncio.Event, session: dict = None
) -> None:
    """
    Consume Vobiz media events without relaying (during HOLD mode).
    Also handles start/stop events and keeps session stream_id in sync.
    """
    drained = 0
    while not stop_event.is_set():
        try:
            raw = await asyncio.wait_for(vobiz_ws.receive_text(), timeout=1.0)
            event = json.loads(raw)
            event_type = event.get("event")

            if event_type == "media":
                drained += 1

            elif event_type == "start":
                start_data = event.get("start", {})
                stream_id = (
                    event.get("streamId")
                    or start_data.get("streamId")
                    or ""
                )
                if stream_id:
                    state["stream_id"] = stream_id
                    if session:
                        session["_candidate_stream_id"] = stream_id
                    print(f"🔗 [LC_BRIDGE] Drain: new stream_id={stream_id}")

            elif event_type == "stop":
                print(f"🔗 [LC_BRIDGE] Drain: stream stopped after {drained} media events")
                stop_event.set()
                break

        except asyncio.TimeoutError:
            continue
        except WebSocketDisconnect:
            print(f"🔗 [LC_BRIDGE] Drain: WebSocket disconnected after {drained} media events")
            stop_event.set()
            break
        except Exception:
            continue


async def _send_clear_and_beep(ws: WebSocket, stream_id: str, label: str) -> None:
    """Send clearAudio to flush buffered AI audio, then a brief beep as 'connected' signal."""
    try:
        await ws.send_text(json.dumps({"event": "clearAudio", "streamId": stream_id}))
        print(f"🔗 [LC_BRIDGE] {label}: clearAudio sent (stream_id={stream_id})")

        for beep_frame in _BEEP_FRAMES[:5]:
            frame_b64 = base64.b64encode(beep_frame).decode("utf-8")
            msg = {
                "event": "playAudio",
                "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": frame_b64},
                "streamId": stream_id,
            }
            await ws.send_text(json.dumps(msg))
        print(f"🔗 [LC_BRIDGE] {label}: connected beep sent")
    except Exception as e:
        print(f"⚠️ [LC_BRIDGE] {label}: clearAudio/beep failed: {type(e).__name__}: {e}")


JYOTI_VOICE_ID = "mActWQg9kibLro6Z2ouY"
JYOTI_TTS_MODEL = "eleven_flash_v2_5"


async def _play_tts_intro(
    vobiz_ws: WebSocket,
    stream_id: str,
    text: str,
    label: str = "TTS intro",
) -> None:
    """Generate TTS audio via ElevenLabs and play it to a Vobiz WebSocket."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        print(f"⚠️ [LC_BRIDGE] {label}: skipping TTS (no API key)")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{JYOTI_VOICE_ID}",
                headers={"xi-api-key": api_key},
                json={
                    "text": text,
                    "model_id": JYOTI_TTS_MODEL,
                },
                params={"output_format": "ulaw_8000"},
            )
            resp.raise_for_status()
            mulaw_audio = resp.content

        # Play frame by frame to Vobiz
        for i in range(0, len(mulaw_audio), MULAW_CHUNK_SIZE):
            frame = mulaw_audio[i : i + MULAW_CHUNK_SIZE]
            frame_b64 = base64.b64encode(frame).decode("utf-8")
            msg = {
                "event": "playAudio",
                "media": {
                    "contentType": "audio/x-mulaw",
                    "sampleRate": 8000,
                    "payload": frame_b64,
                },
                "streamId": stream_id,
            }
            await vobiz_ws.send_text(json.dumps(msg))

        # Wait for TTS to finish playing
        play_duration = len(mulaw_audio) / 8000
        print(f"🔗 [LC_BRIDGE] {label}: playing {len(mulaw_audio)} bytes ({play_duration:.1f}s)")
        await asyncio.sleep(play_duration)

    except Exception as e:
        print(f"⚠️ [LC_BRIDGE] {label}: TTS failed: {type(e).__name__}: {e}")


async def _relay_direct(
    source_ws: WebSocket,
    dest_ws: WebSocket,
    stop_event: asyncio.Event,
    direction: str,
    session: dict,
    dest_stream_key: str,
    source_stream_key: str = "",
) -> None:
    """
    Relay mulaw audio directly from one Vobiz WebSocket to another.
    No conversion needed — both are mulaw 8kHz.

    Reads dest_stream_id from session[dest_stream_key] on each send so it
    stays in sync if Vobiz restarts the stream with a new ID. Updates
    session[source_stream_key] when a start event arrives on the source.
    """
    chunks = 0
    other_events = 0
    dest_stream_id = session.get(dest_stream_key, "")
    recording_key = "_recording_candidate_audio" if direction.startswith("candidate") else "_recording_business_audio"
    if recording_key not in session:
        session[recording_key] = bytearray()
    print(f"🔗 [LC_BRIDGE] _relay_direct starting: {direction} (dest_stream_id={dest_stream_id})")
    try:
        while not stop_event.is_set():
            raw = await source_ws.receive_text()
            event = json.loads(raw)
            event_type = event.get("event")

            if event_type == "media":
                payload_b64 = event.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue
                try:
                    recording_buf = session.get(recording_key)
                    if recording_buf is not None:
                        recording_buf.extend(base64.b64decode(payload_b64))
                except Exception:
                    pass

                # Read latest dest stream_id from session (may have been updated)
                current_dest_id = session.get(dest_stream_key, dest_stream_id)

                play_msg = {
                    "event": "playAudio",
                    "media": {
                        "contentType": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "payload": payload_b64,
                    },
                    "streamId": current_dest_id,
                }
                try:
                    await dest_ws.send_text(json.dumps(play_msg))
                except Exception as send_err:
                    print(f"❌ [LC_BRIDGE] Direct relay {direction}: send failed: {type(send_err).__name__}: {send_err}")
                    stop_event.set()
                    break
                chunks += 1
                if chunks == 1:
                    print(f"🔗 [LC_BRIDGE] First direct relay frame: {direction} (payload_len={len(payload_b64)}, dest_stream={current_dest_id})")
                elif chunks % 500 == 0:
                    print(f"🔗 [LC_BRIDGE] Direct relay {direction}: {chunks} chunks")

            elif event_type == "start":
                start_data = event.get("start", {})
                new_stream_id = (
                    event.get("streamId")
                    or start_data.get("streamId")
                    or ""
                )
                print(f"🔗 [LC_BRIDGE] Direct relay {direction}: start event (new_stream_id={new_stream_id})")
                if new_stream_id and source_stream_key:
                    session[source_stream_key] = new_stream_id
                    print(f"🔗 [LC_BRIDGE] Direct relay {direction}: updated session[{source_stream_key}]={new_stream_id}")

            elif event_type == "stop":
                print(f"🔗 [LC_BRIDGE] Direct relay {direction}: stream stopped after {chunks} chunks")
                stop_event.set()
                break

            else:
                other_events += 1
                if other_events <= 5:
                    print(f"🔗 [LC_BRIDGE] Direct relay {direction}: event_type={event_type}")

    except WebSocketDisconnect:
        print(f"🔗 [LC_BRIDGE] Direct relay {direction}: source disconnected after {chunks} chunks")
        stop_event.set()
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] Direct relay {direction} error after {chunks} chunks: {type(e).__name__}: {e}")
        traceback.print_exc()
        stop_event.set()
    print(f"🔗 [LC_BRIDGE] _relay_direct ended: {direction} total_chunks={chunks}")


async def _capture_stream_id(ws: WebSocket, label: str) -> str:
    """Pre-read Vobiz events to capture stream_id before entering AI mode."""
    try:
        for _ in range(10):
            raw = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
            event = json.loads(raw)
            event_type = event.get("event")
            print(f"🔗 [LC_BRIDGE] {label} pre-read event: {event_type}")
            if event_type == "start":
                start_data = event.get("start", {})
                stream_id = (
                    event.get("streamId")
                    or start_data.get("streamId")
                    or event.get("streamSid")
                    or start_data.get("streamSid")
                    or ""
                )
                print(f"🔗 [LC_BRIDGE] {label} stream_id captured: {stream_id}")
                return stream_id
            elif event_type == "connected":
                continue
    except asyncio.TimeoutError:
        print(f"⚠️ [LC_BRIDGE] {label}: timed out waiting for start event")
    return ""


@router.websocket("/ws/live-connect/candidate")
async def live_connect_candidate_bridge(vobiz_ws: WebSocket):
    """
    WebSocket endpoint for the candidate leg of a live connect session.

    Lifecycle: AI screening → HOLD (wait for business) → DIRECT relay
    Handles Vobiz reconnections (keepCallAlive=true) by checking session state.
    """
    await vobiz_ws.accept()

    session_id = vobiz_ws.query_params.get("session_id", "")
    session = get_session(session_id)

    if not session:
        print(f"❌ [LC_BRIDGE] Candidate: no session found for {session_id}")
        await vobiz_ws.close()
        return

    status = session.get("status", "")
    print(f"🔗 [LC_BRIDGE] Candidate WebSocket connected for session {session_id} (status={status})")

    # Update WebSocket reference (may be a reconnection)
    session["_candidate_vobiz_ws"] = vobiz_ws

    # Capture stream_id from Vobiz start event
    stream_id = await _capture_stream_id(vobiz_ws, "Candidate")
    session["_candidate_stream_id"] = stream_id

    # --- 3-WAY CHECK: inbound first connection / true reconnection / outbound first connection ---

    # Case 1: INBOUND FIRST CONNECTION
    # Candidate just arrived at LC bridge from an inbound call (transferred from vobiz_bridge).
    # _candidate_ready is NOT set yet, _candidate_ws_connected is False.
    # Skip AI screening — go straight to HOLD or handle business exhaustion.
    if session.get("inbound") and not session.get("_candidate_ws_connected"):
        print(f"🔗 [LC_BRIDGE] Candidate: INBOUND FIRST CONNECTION (status={status})")
        session["_candidate_ws_connected"] = True
        session["_candidate_ready"] = session.get("_candidate_ready") or asyncio.Event()
        session["_candidate_ready"].set()

        # Check if businesses already exhausted before we arrived
        businesses_exhausted = session.get("_businesses_exhausted")
        if businesses_exhausted:
            print(f"🔗 [LC_BRIDGE] Candidate: businesses already exhausted ({businesses_exhausted}), playing sorry TTS")
            sorry_text = "Abhi koi employer available nahi hai. Hum aapko SMS se job details bhej denge. Thank you!"
            await _play_tts_intro(vobiz_ws, stream_id, sorry_text, "Candidate sorry TTS")
            asyncio.create_task(end_session(session_id, outcome=f"businesses_exhausted_{businesses_exhausted}"))
            # Hang up the Vobiz call (keepCallAlive=true means WS close alone won't end it)
            call_uuid = session.get("candidate_call_uuid", "")
            if call_uuid:
                try:
                    await vobiz_service.hangup_call(call_uuid)
                except Exception as e:
                    print(f"⚠️ [LC_BRIDGE] Failed to hangup after sorry TTS: {e}")
            try:
                await vobiz_ws.close()
            except Exception:
                pass
            return

        # Check if business bridge is already ready (fast path)
        if session.get("_business_bridge_ready") and session["_business_bridge_ready"].is_set():
            if session.get("_conference_active"):
                print(f"🔗 [LC_BRIDGE] Candidate: INBOUND FAST PATH — conference active, waiting for session end")
                try:
                    await session["_session_ended"].wait()
                except Exception:
                    pass
                try:
                    await vobiz_ws.close()
                except Exception:
                    pass
                return
            print(f"🔗 [LC_BRIDGE] Candidate: INBOUND FAST PATH — business already ready")
            winner_phone = session.get("_winner_phone")
            winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
            business_ws = winner_attempt.get("vobiz_ws") or session.get("_business_vobiz_ws")
            business_stream_id = winner_attempt.get("stream_id") or session.get("_business_stream_id")
            candidate_stream_id = session.get("_candidate_stream_id")
            if business_ws and business_stream_id:
                session["bridge_started_at"] = time.time()
                update_session_status(session_id, LiveConnectStatus.BRIDGED)
                await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": candidate_stream_id}))
                business_name = session.get("business_name", "employer")
                intro_text = f"Badhai ho! {business_name} ka HR line pe hai. Himmat se baat karo, all the best!"
                asyncio.create_task(_play_tts_intro(vobiz_ws, candidate_stream_id, intro_text, "Candidate inbound fast-path intro"))
                try:
                    await _relay_direct(
                        source_ws=vobiz_ws,
                        dest_ws=business_ws,
                        stop_event=session["_session_ended"],
                        direction="candidate→business",
                        session=session,
                        dest_stream_key="_business_stream_id",
                        source_stream_key="_candidate_stream_id",
                    )
                except Exception as e:
                    print(f"🔗 [LC_BRIDGE] Candidate inbound fast-path DIRECT error: {e}")
            try:
                await vobiz_ws.close()
            except Exception:
                pass
            return

        # Otherwise enter HOLD — wait for business bridge or session end
        print(f"🔗 [LC_BRIDGE] Candidate: INBOUND entering HOLD mode")
        hold_stop = asyncio.Event()

        async def _wait_inbound_hold_end():
            bridge_ready_task = asyncio.create_task(session["_business_bridge_ready"].wait())
            session_ended_task = asyncio.create_task(session["_session_ended"].wait())
            done, pending = await asyncio.wait(
                [bridge_ready_task, session_ended_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            hold_stop.set()

        hold_waiter = asyncio.create_task(_wait_inbound_hold_end())
        hold_player = asyncio.create_task(_play_hold_audio(vobiz_ws, stream_id, hold_stop))
        drain_task = asyncio.create_task(_drain_vobiz_media(vobiz_ws, {"stream_id": stream_id}, hold_stop, session=session))
        await asyncio.gather(hold_waiter, hold_player, drain_task, return_exceptions=True)

        # HOLD exited — check why
        if session["_session_ended"].is_set() and not session["_business_bridge_ready"].is_set():
            # Session ended while on hold — check if businesses exhausted
            exhausted = session.get("_businesses_exhausted")
            if exhausted:
                print(f"🔗 [LC_BRIDGE] Candidate: HOLD exited due to businesses exhausted ({exhausted}), playing sorry TTS")
                sorry_text = "Abhi koi employer available nahi hai. Hum aapko SMS se job details bhej denge. Thank you!"
                await _play_tts_intro(vobiz_ws, session.get("_candidate_stream_id") or stream_id, sorry_text, "Candidate sorry TTS (hold)")
            else:
                print(f"🔗 [LC_BRIDGE] Candidate: HOLD exited due to session end")
            # Hang up the Vobiz call (keepCallAlive=true means WS close alone won't end it)
            call_uuid = session.get("candidate_call_uuid", "")
            if call_uuid:
                try:
                    await vobiz_service.hangup_call(call_uuid)
                except Exception as e:
                    print(f"⚠️ [LC_BRIDGE] Failed to hangup after hold exit: {e}")
            try:
                await vobiz_ws.close()
            except Exception:
                pass
            return

        # Business bridge ready — enter DIRECT relay (or wait if conference active)
        if session["_business_bridge_ready"].is_set():
            if session.get("_conference_active"):
                print(f"🔗 [LC_BRIDGE] Candidate: INBOUND HOLD exit — conference active, waiting for session end")
                try:
                    await session["_session_ended"].wait()
                except Exception:
                    pass
            else:
                winner_phone = session.get("_winner_phone")
                winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
                business_ws = winner_attempt.get("vobiz_ws") or session.get("_business_vobiz_ws")
                business_stream_id = winner_attempt.get("stream_id") or session.get("_business_stream_id")
                candidate_stream_id = session.get("_candidate_stream_id") or stream_id
                if business_ws and business_stream_id:
                    session["bridge_started_at"] = time.time()
                    update_session_status(session_id, LiveConnectStatus.BRIDGED)
                    await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": candidate_stream_id}))
                    business_name = session.get("business_name", "employer")
                    intro_text = f"Badhai ho! {business_name} ka HR line pe hai. Himmat se baat karo, all the best!"
                    asyncio.create_task(_play_tts_intro(vobiz_ws, candidate_stream_id, intro_text, "Candidate inbound intro"))
                    try:
                        await _relay_direct(
                            source_ws=vobiz_ws,
                            dest_ws=business_ws,
                            stop_event=session["_session_ended"],
                            direction="candidate→business",
                            session=session,
                            dest_stream_key="_business_stream_id",
                            source_stream_key="_candidate_stream_id",
                        )
                    except Exception as e:
                        print(f"🔗 [LC_BRIDGE] Candidate inbound DIRECT error: {e}")

        try:
            await vobiz_ws.close()
        except Exception:
            pass
        return

    # Case 2: TRUE RECONNECTION (Vobiz reconnected after ws close, session already past screening)
    if session.get("_candidate_ws_connected") or (session.get("_candidate_ready") and session["_candidate_ready"].is_set()):
        print(f"🔗 [LC_BRIDGE] Candidate: reconnection detected (status={status}), skipping AI mode")

        # If already bridged or business ready, try to enter DIRECT relay
        if session.get("_business_bridge_ready") and session["_business_bridge_ready"].is_set():
            if session.get("_conference_active"):
                print(f"🔗 [LC_BRIDGE] Candidate: reconnect — conference active, waiting for session end")
                try:
                    await session["_session_ended"].wait()
                except Exception:
                    pass
            else:
                winner_phone = session.get("_winner_phone")
                winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
                business_ws = winner_attempt.get("vobiz_ws") or session.get("_business_vobiz_ws")
                business_stream_id = winner_attempt.get("stream_id") or session.get("_business_stream_id")
                if business_ws and business_stream_id:
                    print(f"🔗 [LC_BRIDGE] Candidate: reconnect → resuming DIRECT relay")
                    try:
                        await _relay_direct(
                            source_ws=vobiz_ws,
                            dest_ws=business_ws,
                            stop_event=session["_session_ended"],
                            direction="candidate→business",
                            session=session,
                            dest_stream_key="_business_stream_id",
                            source_stream_key="_candidate_stream_id",
                        )
                    except Exception as e:
                        print(f"🔗 [LC_BRIDGE] Candidate reconnect DIRECT error: {e}")
                else:
                    print(f"🔗 [LC_BRIDGE] Candidate: reconnect but no business ws, draining until end")
                    await session["_session_ended"].wait()
        else:
            # Still waiting for business — resume HOLD
            print(f"🔗 [LC_BRIDGE] Candidate: reconnect → resuming HOLD")
            hold_stop = asyncio.Event()

            async def _wait_end():
                bridge_task = asyncio.create_task(session["_business_bridge_ready"].wait())
                ended_task = asyncio.create_task(session["_session_ended"].wait())
                await asyncio.wait([bridge_task, ended_task], return_when=asyncio.FIRST_COMPLETED)
                hold_stop.set()

            hold_waiter = asyncio.create_task(_wait_end())
            hold_player = asyncio.create_task(_play_hold_audio(vobiz_ws, stream_id, hold_stop))
            drain_task = asyncio.create_task(_drain_vobiz_media(vobiz_ws, {"stream_id": stream_id}, hold_stop, session=session))
            await asyncio.gather(hold_waiter, hold_player, drain_task, return_exceptions=True)

            if session["_business_bridge_ready"].is_set():
                if session.get("_conference_active"):
                    print(f"🔗 [LC_BRIDGE] Candidate: reconnect HOLD exit — conference active, waiting for session end")
                    try:
                        await session["_session_ended"].wait()
                    except Exception:
                        pass
                else:
                    winner_phone = session.get("_winner_phone")
                    winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
                    business_ws = winner_attempt.get("vobiz_ws") or session.get("_business_vobiz_ws")
                    business_stream_id = winner_attempt.get("stream_id") or session.get("_business_stream_id")
                    if business_ws and business_stream_id:
                        try:
                            session["bridge_started_at"] = time.time()
                            update_session_status(session_id, LiveConnectStatus.BRIDGED)
                            await _relay_direct(
                                source_ws=vobiz_ws,
                                dest_ws=business_ws,
                                stop_event=session["_session_ended"],
                                direction="candidate→business",
                                session=session,
                                dest_stream_key="_business_stream_id",
                                source_stream_key="_candidate_stream_id",
                            )
                        except Exception as e:
                            print(f"🔗 [LC_BRIDGE] Candidate reconnect DIRECT error: {e}")

        try:
            await vobiz_ws.close()
        except Exception:
            pass
        return

    # Case 3: OUTBOUND FIRST CONNECTION (normal flow — AI screening)
    # --- NORMAL FLOW (first connection) ---
    state = {
        "stream_id": stream_id,
        "vobiz_chunks_in": 0,
        "el_chunks_out": 0,
        "conversation_id": None,
        "caller_phone": session.get("candidate_phone", ""),
    }

    try:
        update_session_status(session_id, LiveConnectStatus.SCREENING_CANDIDATE)

        # Phase 1: AI screening
        print(f"🔗 [LC_BRIDGE] Candidate: entering AI mode (stream_id={stream_id})")
        await _run_ai_mode(
            vobiz_ws, state, "live_connect_candidate", session,
            disconnect_signal=session["_candidate_ready"],
        )

        # Update stream_id (relay may have refreshed it)
        if state.get("stream_id"):
            session["_candidate_stream_id"] = state["stream_id"]
        print(f"🔗 [LC_BRIDGE] Candidate: AI mode ended (stream_id={state.get('stream_id')}, candidate_ready={session['_candidate_ready'].is_set()})")

        if not session["_candidate_ready"].is_set():
            print(f"🔗 [LC_BRIDGE] Candidate: AI ended without connect signal")
            return

        # FAST PATH: business bridge is already ready — skip HOLD entirely
        if session["_business_bridge_ready"].is_set():
            print(f"🔗 [LC_BRIDGE] Candidate: FAST PATH — business already ready, skipping HOLD")
            if session.get("_conference_active"):
                print(f"🔗 [LC_BRIDGE] Candidate: conference bridge active (fast path), waiting for session end")
                try:
                    await session["_session_ended"].wait()
                except Exception:
                    pass
            else:
                winner_phone = session.get("_winner_phone")
                winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
                business_ws = winner_attempt.get("vobiz_ws") or session.get("_business_vobiz_ws")
                business_stream_id = winner_attempt.get("stream_id") or session.get("_business_stream_id")
                candidate_stream_id = session.get("_candidate_stream_id")
                if business_ws and business_stream_id:
                    session["bridge_started_at"] = time.time()
                    update_session_status(session_id, LiveConnectStatus.BRIDGED)
                    await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": candidate_stream_id}))
                    business_name = session.get("business_name", "employer")
                    intro_text = f"Badhai ho! {business_name} ka HR line pe hai. Himmat se baat karo, all the best!"
                    asyncio.create_task(_play_tts_intro(vobiz_ws, candidate_stream_id, intro_text, "Candidate fast-path intro"))
                    await _relay_direct(
                        source_ws=vobiz_ws,
                        dest_ws=business_ws,
                        stop_event=session["_session_ended"],
                        direction="candidate→business",
                        session=session,
                        dest_stream_key="_business_stream_id",
                        source_stream_key="_candidate_stream_id",
                    )
                else:
                    print(f"❌ [LC_BRIDGE] Candidate: fast path but no business ws/stream")
            # Skip the HOLD + bridge code below
            return

        # Phase 2: HOLD (slow path)
        print(f"🔗 [LC_BRIDGE] Candidate: entering HOLD mode (stream_id={state.get('stream_id')})")
        hold_stop = asyncio.Event()

        async def _wait_for_hold_end():
            bridge_ready_task = asyncio.create_task(session["_business_bridge_ready"].wait())
            session_ended_task = asyncio.create_task(session["_session_ended"].wait())
            done, pending = await asyncio.wait(
                [bridge_ready_task, session_ended_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            hold_stop.set()

        hold_waiter = asyncio.create_task(_wait_for_hold_end())
        hold_player = asyncio.create_task(_play_hold_audio(vobiz_ws, state["stream_id"], hold_stop))
        drain_task = asyncio.create_task(_drain_vobiz_media(vobiz_ws, state, hold_stop, session=session))

        await asyncio.gather(hold_waiter, hold_player, drain_task, return_exceptions=True)

        if session["_session_ended"].is_set() and not session["_business_bridge_ready"].is_set():
            print(f"🔗 [LC_BRIDGE] Candidate: session ended while on hold (business unreachable)")
            return

        # Phase 3: Bridge
        if session.get("_conference_active"):
            # Conference bridge — Vobiz handles audio directly, no WebSocket relay needed
            print(f"🔗 [LC_BRIDGE] Candidate: conference bridge active, waiting for session end")
            try:
                await session["_session_ended"].wait()
            except Exception:
                pass
        else:
            # Fallback: DIRECT relay via WebSocket
            winner_phone = session.get("_winner_phone")
            winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
            business_ws = winner_attempt.get("vobiz_ws") or session.get("_business_vobiz_ws")
            business_stream_id = winner_attempt.get("stream_id") or session.get("_business_stream_id")
            candidate_stream_id = session.get("_candidate_stream_id")
            print(f"🔗 [LC_BRIDGE] Candidate: entering DIRECT mode (fallback)")
            print(f"  candidate_stream_id={candidate_stream_id} business_stream_id={business_stream_id}")
            print(f"  business_ws={'OPEN' if business_ws else 'NONE'} candidate_ws={'OPEN' if vobiz_ws else 'NONE'}")
            session["bridge_started_at"] = time.time()
            update_session_status(session_id, LiveConnectStatus.BRIDGED)

            if not business_ws or not business_stream_id:
                print(f"❌ [LC_BRIDGE] Candidate: no business WebSocket/stream_id for direct relay")
                return

            await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": candidate_stream_id}))

            business_name = session.get("business_name", "employer")
            current_job = session.get("current_job") or {}
            job_title = current_job.get("title", "")
            intro_parts = [f"Connect ho gaya hai! {business_name} ke HR se baat karo"]
            if job_title:
                intro_parts.append(f"{job_title} ke baare mein")
            intro_parts.append("All the best!")
            intro_text = " ".join(intro_parts)
            asyncio.create_task(_play_tts_intro(vobiz_ws, candidate_stream_id, intro_text, "Candidate intro"))

            await _relay_direct(
                source_ws=vobiz_ws,
                dest_ws=business_ws,
                stop_event=session["_session_ended"],
                direction="candidate→business",
                session=session,
                dest_stream_key="_business_stream_id",
                source_stream_key="_candidate_stream_id",
            )

    except WebSocketDisconnect:
        print(f"🔗 [LC_BRIDGE] Candidate disconnected for session {session_id}")
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] Candidate error: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        if not session.get("_conference_active"):
            session["_session_ended"].set()
        try:
            await vobiz_ws.close()
        except Exception:
            pass
        print(f"🔗 [LC_BRIDGE] Candidate bridge closed for session {session_id}")


@router.websocket("/ws/live-connect/business")
async def live_connect_business_bridge(vobiz_ws: WebSocket):
    """
    WebSocket endpoint for the business leg of a live connect session.

    With parallel calling, each business gets its own bridge instance.
    Uses attempt_phone from query params to isolate per-attempt state.
    Lifecycle: AI intro → conference transfer (if winner)
    """
    await vobiz_ws.accept()

    session_id = vobiz_ws.query_params.get("session_id", "")
    attempt_phone = vobiz_ws.query_params.get("attempt_phone", "")
    session = get_session(session_id)

    if not session:
        print(f"❌ [LC_BRIDGE] Business: no session found for {session_id}")
        await vobiz_ws.close()
        return

    status = session.get("status", "")
    print(f"🔗 [LC_BRIDGE] Business WebSocket connected for session {session_id} attempt_phone={attempt_phone} (status={status})")

    # Look up per-attempt dict
    attempt = session.get("_attempts", {}).get(attempt_phone) if attempt_phone else None

    # Capture stream_id
    stream_id = await _capture_stream_id(vobiz_ws, f"Business({attempt_phone})")

    # Store ws/stream in attempt dict
    if attempt:
        attempt["vobiz_ws"] = vobiz_ws
        attempt["stream_id"] = stream_id
    # Also store globally for backward compat with candidate bridge reads
    session["_business_vobiz_ws"] = vobiz_ws
    session["_business_stream_id"] = stream_id

    # --- REVERSE FLOW: business is the inbound caller, needs HOLD ---
    if session.get("direction") == "business_to_candidate":
        print(f"🔗 [LC_BRIDGE] Business: REVERSE FLOW — entering HOLD mode (waiting for candidate)")
        try:
            hold_stop = asyncio.Event()

            async def _wait_for_candidate_or_end():
                bridge_ready_task = asyncio.create_task(session["_candidate_bridge_ready"].wait())
                session_ended_task = asyncio.create_task(session["_session_ended"].wait())
                done, pending = await asyncio.wait(
                    [bridge_ready_task, session_ended_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
                hold_stop.set()

            hold_waiter = asyncio.create_task(_wait_for_candidate_or_end())
            hold_player = asyncio.create_task(_play_hold_audio(vobiz_ws, stream_id, hold_stop))
            drain_state = {"stream_id": stream_id}
            drain_task = asyncio.create_task(_drain_vobiz_media(vobiz_ws, drain_state, hold_stop))

            await asyncio.gather(hold_waiter, hold_player, drain_task, return_exceptions=True)

            if session["_session_ended"].is_set() and not session["_candidate_bridge_ready"].is_set():
                print(f"🔗 [LC_BRIDGE] Business: session ended while on hold (candidate unreachable)")
                return

            # Candidate agreed — conference transfer both calls
            if session["_candidate_bridge_ready"].is_set():
                # Get winner's call_uuid from attempts
                winner_phone = session.get("_winner_phone", "")
                winner_attempt = session.get("_attempts", {}).get(winner_phone, {}) if winner_phone else {}
                candidate_call_uuid = winner_attempt.get("call_uuid") or session.get("candidate_call_uuid", "")
                business_call_uuid = session.get("business_call_uuid", "")

                if candidate_call_uuid and business_call_uuid:
                    try:
                        session["_conference_active"] = True
                        server_host = os.getenv("SERVER_HOST", "api.relayy.world")
                        conf_url = f"https://{server_host}/api/live-connect/conference/join?session_id={session_id}"

                        print(f"🔗 [LC_BRIDGE] Business reverse: transferring both calls to conference lc_bridge_{session_id}")
                        await vobiz_service.transfer_call(
                            candidate_call_uuid, f"{conf_url}&party=candidate"
                        )
                        await vobiz_service.transfer_call(
                            business_call_uuid, f"{conf_url}&party=business"
                        )

                        session["bridge_started_at"] = time.time()
                        update_session_status(session_id, LiveConnectStatus.BRIDGED)

                        print(f"🔗 [LC_BRIDGE] Business reverse: conference bridge active")
                        await session["_session_ended"].wait()
                    except Exception as conf_err:
                        print(f"❌ [LC_BRIDGE] Business reverse: conference transfer failed: {conf_err}")
                        traceback.print_exc()
                else:
                    print(f"❌ [LC_BRIDGE] Business reverse: missing call UUIDs for conference (candidate={candidate_call_uuid}, business={business_call_uuid})")

        except WebSocketDisconnect:
            print(f"🔗 [LC_BRIDGE] Business disconnected during reverse HOLD for session {session_id}")
        except Exception as e:
            print(f"🔗 [LC_BRIDGE] Business reverse HOLD error: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            if session.get("_conference_active"):
                pass
            else:
                session["_session_ended"].set()
            try:
                await vobiz_ws.close()
            except Exception:
                pass
            print(f"🔗 [LC_BRIDGE] Business reverse bridge closed for session {session_id}")
        return

    # --- RECONNECTION GUARD ---
    # Check if this attempt already won and was accepted
    if attempt and attempt.get("accepted") and session.get("_winner_phone") == attempt_phone:
        print(f"🔗 [LC_BRIDGE] Business: reconnection detected for winner {attempt_phone}, waiting for session end")
        try:
            await session["_session_ended"].wait()
        except Exception:
            pass
        try:
            await vobiz_ws.close()
        except Exception:
            pass
        return

    # Check if race already resolved and this attempt is NOT the winner
    if session.get("_winner_phone") is not None and session.get("_winner_phone") != attempt_phone:
        print(f"🔗 [LC_BRIDGE] Business: race already won by {session.get('_winner_phone')}, closing {attempt_phone}")
        try:
            await vobiz_ws.close()
        except Exception:
            pass
        return

    # --- NORMAL FLOW: AI pitch (per-attempt isolated) ---
    state = {
        "stream_id": stream_id,
        "vobiz_chunks_in": 0,
        "el_chunks_out": 0,
        "conversation_id": None,
        "caller_phone": attempt_phone or session.get("business_phone", ""),
        "attempt_phone": attempt_phone,
    }

    # Use per-attempt disconnect_signal
    disconnect_signal = attempt["disconnect_signal"] if attempt else asyncio.Event()

    try:
        update_session_status(session_id, LiveConnectStatus.PITCHING_BUSINESS)

        print(f"🔗 [LC_BRIDGE] Business: entering AI mode for {attempt_phone} (stream_id={stream_id})")
        await _run_ai_mode(
            vobiz_ws, state, "live_connect_business", session,
            disconnect_signal=disconnect_signal,
        )

        # Update stream_id in attempt
        if state.get("stream_id"):
            if attempt:
                attempt["stream_id"] = state["stream_id"]
            session["_business_stream_id"] = state["stream_id"]
        print(f"🔗 [LC_BRIDGE] Business: AI mode ended for {attempt_phone} (accepted={attempt.get('accepted') if attempt else None})")

        # Check if this attempt won the race
        is_winner = session.get("_winner_phone") == attempt_phone

        if not is_winner:
            # Not the winner (declined, lost race, or AI ended without tool call)
            if attempt and attempt.get("accepted") is None:
                attempt["accepted"] = False
                attempt["declined"].set()
            print(f"🔗 [LC_BRIDGE] Business: {attempt_phone} not winner, closing")
            return

        # This attempt WON — do conference transfer
        candidate_call_uuid = session.get("candidate_call_uuid", "")
        business_call_uuid = attempt.get("call_uuid", "") if attempt else session.get("business_call_uuid", "")

        if candidate_call_uuid and business_call_uuid:
            try:
                session["_conference_active"] = True
                server_host = os.getenv("SERVER_HOST", "api.relayy.world")
                conf_url = f"https://{server_host}/api/live-connect/conference/join?session_id={session_id}"

                print(f"🔗 [LC_BRIDGE] Business: transferring both calls to conference lc_bridge_{session_id}")
                await vobiz_service.transfer_call(
                    candidate_call_uuid, f"{conf_url}&party=candidate"
                )
                await vobiz_service.transfer_call(
                    business_call_uuid, f"{conf_url}&party=business"
                )

                session["bridge_started_at"] = time.time()
                update_session_status(session_id, LiveConnectStatus.BRIDGED)
                session["_business_bridge_ready"].set()

                print(f"🔗 [LC_BRIDGE] Business: conference bridge active (winner={attempt_phone})")
                await session["_session_ended"].wait()

            except Exception as conf_err:
                print(f"❌ [LC_BRIDGE] Conference transfer failed: {conf_err}, falling back to DIRECT relay")
                traceback.print_exc()
                session["_conference_active"] = False

                # Fallback: DIRECT relay via WebSocket
                candidate_ws = session.get("_candidate_vobiz_ws")
                candidate_stream_id = session.get("_candidate_stream_id")
                business_stream_id = attempt.get("stream_id") if attempt else session.get("_business_stream_id")

                if candidate_ws and candidate_stream_id:
                    await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": business_stream_id}))
                    session["_business_bridge_ready"].set()

                    candidate_name = session.get("candidate_name", "candidate")
                    intro_text = f"{candidate_name} connect ho rahe hain. Please baat karo!"
                    asyncio.create_task(_play_tts_intro(vobiz_ws, business_stream_id, intro_text, "Business intro"))

                    await _relay_direct(
                        source_ws=vobiz_ws,
                        dest_ws=candidate_ws,
                        stop_event=session["_session_ended"],
                        direction="business→candidate",
                        session=session,
                        dest_stream_key="_candidate_stream_id",
                        source_stream_key="_business_stream_id",
                    )
        else:
            print(f"❌ [LC_BRIDGE] Business: missing call UUIDs (candidate={candidate_call_uuid}, business={business_call_uuid})")
            # Try direct relay as fallback
            candidate_ws = session.get("_candidate_vobiz_ws")
            candidate_stream_id = session.get("_candidate_stream_id")
            business_stream_id = attempt.get("stream_id") if attempt else session.get("_business_stream_id")

            if candidate_ws and candidate_stream_id and business_stream_id:
                await vobiz_ws.send_text(json.dumps({"event": "clearAudio", "streamId": business_stream_id}))
                session["_business_bridge_ready"].set()
                await _relay_direct(
                    source_ws=vobiz_ws,
                    dest_ws=candidate_ws,
                    stop_event=session["_session_ended"],
                    direction="business→candidate",
                    session=session,
                    dest_stream_key="_candidate_stream_id",
                    source_stream_key="_business_stream_id",
                )

    except WebSocketDisconnect:
        print(f"🔗 [LC_BRIDGE] Business disconnected for session {session_id} attempt={attempt_phone}")
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] Business error: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        if session.get("_conference_active"):
            pass  # Conference handles the call lifecycle via hangup webhooks
        elif session.get("_winner_phone") == attempt_phone and session.get("status") == LiveConnectStatus.BRIDGED.value:
            session["_session_ended"].set()
        elif attempt and attempt.get("accepted") is None:
            attempt["accepted"] = False
            attempt["declined"].set()

        # Hang up non-winner business calls (keepCallAlive=true keeps them alive after WS close)
        is_winner = session.get("_winner_phone") == attempt_phone
        if not is_winner and attempt and attempt.get("call_uuid"):
            try:
                await vobiz_service.hangup_call(attempt["call_uuid"])
                print(f"🔗 [LC_BRIDGE] Hung up non-winner business call {attempt_phone}")
            except Exception as e:
                print(f"⚠️ [LC_BRIDGE] Failed to hangup non-winner {attempt_phone}: {e}")

        try:
            await vobiz_ws.close()
        except Exception:
            pass
        print(f"🔗 [LC_BRIDGE] Business bridge closed for session {session_id} attempt={attempt_phone}")


@router.websocket("/ws/live-connect/reverse-candidate")
async def live_connect_reverse_candidate_bridge(vobiz_ws: WebSocket):
    """
    WebSocket endpoint for the candidate leg in reverse flow (business→candidate).

    With parallel calling, each candidate gets its own bridge instance.
    Uses attempt_phone from query params to isolate per-attempt state.
    Lifecycle: AI pitch to candidate → conference bridge (if winner)
    """
    await vobiz_ws.accept()

    session_id = vobiz_ws.query_params.get("session_id", "")
    attempt_phone = vobiz_ws.query_params.get("attempt_phone", "")
    session = get_session(session_id)

    if not session:
        print(f"❌ [LC_BRIDGE] Reverse candidate: no session found for {session_id}")
        await vobiz_ws.close()
        return

    status = session.get("status", "")
    print(f"🔗 [LC_BRIDGE] Reverse candidate WebSocket connected for session {session_id} attempt_phone={attempt_phone} (status={status})")

    # Look up per-attempt dict
    attempt = session.get("_attempts", {}).get(attempt_phone) if attempt_phone else None

    # Capture stream_id
    stream_id = await _capture_stream_id(vobiz_ws, f"ReverseCandidate({attempt_phone})")

    # Store ws/stream in attempt dict
    if attempt:
        attempt["vobiz_ws"] = vobiz_ws
        attempt["stream_id"] = stream_id
    session["_candidate_vobiz_ws"] = vobiz_ws
    session["_candidate_stream_id"] = stream_id

    # --- RECONNECTION GUARD ---
    if attempt and attempt.get("accepted") and session.get("_winner_phone") == attempt_phone:
        print(f"🔗 [LC_BRIDGE] Reverse candidate: reconnection detected for winner {attempt_phone}, waiting for session end")
        try:
            await session["_session_ended"].wait()
        except Exception:
            pass
        try:
            await vobiz_ws.close()
        except Exception:
            pass
        return

    # Check if race already resolved and this attempt is NOT the winner
    if session.get("_winner_phone") is not None and session.get("_winner_phone") != attempt_phone:
        print(f"🔗 [LC_BRIDGE] Reverse candidate: race already won by {session.get('_winner_phone')}, closing {attempt_phone}")
        try:
            await vobiz_ws.close()
        except Exception:
            pass
        return

    # --- NORMAL FLOW: AI pitch to candidate ---
    state = {
        "stream_id": stream_id,
        "vobiz_chunks_in": 0,
        "el_chunks_out": 0,
        "conversation_id": None,
        "caller_phone": attempt_phone or session.get("candidate_phone", ""),
        "attempt_phone": attempt_phone,
    }

    # Use per-attempt disconnect_signal
    disconnect_signal = attempt["disconnect_signal"] if attempt else asyncio.Event()

    try:
        update_session_status(session_id, LiveConnectStatus.PITCHING_CANDIDATE)

        print(f"🔗 [LC_BRIDGE] Reverse candidate: entering AI mode for {attempt_phone} (stream_id={stream_id})")

        await _run_ai_mode(
            vobiz_ws, state, "live_connect_reverse_candidate", session,
            disconnect_signal=disconnect_signal,
        )

        # Update stream_id in attempt
        if state.get("stream_id"):
            if attempt:
                attempt["stream_id"] = state["stream_id"]
            session["_candidate_stream_id"] = state["stream_id"]
        print(f"🔗 [LC_BRIDGE] Reverse candidate: AI mode ended for {attempt_phone} (accepted={attempt.get('accepted') if attempt else None})")

        # Check if this attempt won the race
        is_winner = session.get("_winner_phone") == attempt_phone

        if not is_winner:
            if attempt and attempt.get("accepted") is None:
                attempt["accepted"] = False
                attempt["declined"].set()
            print(f"🔗 [LC_BRIDGE] Reverse candidate: {attempt_phone} not winner, closing")
            return

        # Candidate agreed and won — _candidate_bridge_ready was already set by accept_candidate_connect tool
        # The business bridge HOLD will pick up _candidate_bridge_ready and do conference transfer
        print(f"🔗 [LC_BRIDGE] Reverse candidate: {attempt_phone} won, waiting for conference/session end")
        try:
            await session["_session_ended"].wait()
        except Exception:
            pass

    except WebSocketDisconnect:
        print(f"🔗 [LC_BRIDGE] Reverse candidate disconnected for session {session_id} attempt={attempt_phone}")
    except Exception as e:
        print(f"🔗 [LC_BRIDGE] Reverse candidate error: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        if session.get("_conference_active"):
            pass
        elif attempt and attempt.get("accepted") is None:
            attempt["accepted"] = False
            attempt["declined"].set()

        # Hang up non-winner candidate calls (keepCallAlive=true keeps them alive after WS close)
        is_winner = session.get("_winner_phone") == attempt_phone
        if not is_winner and attempt and attempt.get("call_uuid"):
            try:
                await vobiz_service.hangup_call(attempt["call_uuid"])
                print(f"🔗 [LC_BRIDGE] Hung up non-winner reverse candidate call {attempt_phone}")
            except Exception as e:
                print(f"⚠️ [LC_BRIDGE] Failed to hangup non-winner reverse candidate {attempt_phone}: {e}")

        try:
            await vobiz_ws.close()
        except Exception:
            pass
        print(f"🔗 [LC_BRIDGE] Reverse candidate bridge closed for session {session_id} attempt={attempt_phone}")
