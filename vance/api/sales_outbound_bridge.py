"""
WebSocket bridge for Sales Outbound calls.

Connects Vobiz (business phone call) ↔ ElevenLabs (Jyoti AI sales agent).
Jyoti pitches Switch to the business and closes for a WhatsApp follow-up.

AI-only bridge: no hold, no transfer, no conference. Just bidirectional relay.
"""

import asyncio
import base64
import json
import os
import traceback

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.sales_outbound_routes import _sales_call_contexts
from api.vobiz_bridge import (
    ELEVENLABS_WS_URL,
    MULAW_CHUNK_SIZE,
    _mulaw_8k_to_pcm_16k,
    _pcm_16k_to_mulaw_8k,
)

router = APIRouter(tags=["SalesOutboundBridge"])


async def _relay_vobiz_to_elevenlabs(vobiz_ws: WebSocket, el_ws, state: dict) -> None:
    """Relay audio from Vobiz (business) to ElevenLabs agent."""
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
                print(f"🔗 [SALES_BRIDGE] Stream started. streamId={stream_id}")

            elif event_type == "stop":
                print("🔗 [SALES_BRIDGE] Stream stopped")
                break

            elif event_type == "connected":
                pass

    except WebSocketDisconnect:
        print("🔗 [SALES_BRIDGE] Vobiz disconnected (relay)")
    except Exception as e:
        print(f"🔗 [SALES_BRIDGE] Vobiz→EL error: {type(e).__name__}: {e}")


async def _relay_elevenlabs_to_vobiz(el_ws, vobiz_ws: WebSocket, state: dict) -> None:
    """Relay audio from ElevenLabs agent to Vobiz (business)."""
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
                print(f"🤖 [SALES_BRIDGE] Agent: {text[:150]}")

            elif msg_type == "user_transcript":
                text = data.get("user_transcription_event", {}).get("user_transcript", "")
                print(f"👤 [SALES_BRIDGE] Business: {text[:150]}")

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
        print("🔗 [SALES_BRIDGE] ElevenLabs disconnected")
    except Exception as e:
        print(f"🔗 [SALES_BRIDGE] EL→Vobiz error: {type(e).__name__}: {e}")


@router.websocket("/ws/sales-outbound")
async def sales_outbound_bridge(vobiz_ws: WebSocket):
    """
    WebSocket endpoint for sales outbound calls.
    Bridges Vobiz ↔ ElevenLabs for Jyoti to pitch Switch to a business.

    CRITICAL: Connect to ElevenLabs IMMEDIATELY. No Firestore calls before
    the relay starts — every second of silence = caller hangs up.
    """
    await vobiz_ws.accept()

    business_phone = vobiz_ws.query_params.get("business_phone", "")
    call_id = vobiz_ws.query_params.get("call_id", "")

    print(f"🔗 [SALES_BRIDGE] WS connected: call_id={call_id} phone={business_phone}", flush=True)

    # Read context from in-memory cache ONLY (set during /initiate, instant)
    sales_context = _sales_call_contexts.get(call_id, {})
    if not sales_context:
        print(f"⚠️ [SALES_BRIDGE] No in-memory context for {call_id}, using empty", flush=True)

    business_name = sales_context.get("business_name", "")
    contact_name = sales_context.get("contact_name", "")
    city = sales_context.get("city", "")
    category = sales_context.get("category", "")

    state = {
        "stream_id": "",
        "vobiz_chunks_in": 0,
        "el_chunks_out": 0,
        "conversation_id": None,
    }

    agent_id = os.getenv("ELEVENLABS_SALES_AGENT_ID") or os.getenv("ELEVENLABS_AGENT_ID", "")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    print(f"🔗 [SALES_BRIDGE] Connecting EL: agent={agent_id[:20]}... key={'set' if api_key else 'MISSING'}", flush=True)

    el_url = f"{ELEVENLABS_WS_URL}?agent_id={agent_id}"
    headers = {}
    if api_key:
        headers["xi-api-key"] = api_key

    el_ws = None
    try:
        # Connect to ElevenLabs IMMEDIATELY — no Firestore before this
        el_ws = await websockets.connect(el_url, additional_headers=headers)
        print(f"🔗 [SALES_BRIDGE] EL connected for {call_id}", flush=True)

        # Wait for init
        init_msg = await asyncio.wait_for(el_ws.recv(), timeout=10)
        init_data = json.loads(init_msg)
        if init_data.get("type") == "conversation_initiation_metadata":
            meta = init_data.get("conversation_initiation_metadata_event", {})
            conv_id = meta.get("conversation_id", "")
            state["conversation_id"] = conv_id
            print(f"🔗 [SALES_BRIDGE] EL conv_id={conv_id}", flush=True)

        # Send dynamic variables to ElevenLabs (agent prompt is configured in EL dashboard)
        client_data = {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": {
                "caller_phone": business_phone,
                "call_type": "sales_outbound",
                "business_name": business_name,
                "contact_name": contact_name,
                "city": city,
                "category": category,
                "call_id": call_id,
                "first_message": "",
            },
        }

        await el_ws.send(json.dumps(client_data))
        print(f"🔗 [SALES_BRIDGE] Client data sent: {business_name} / {city} / {category}", flush=True)

        # Start bidirectional relay IMMEDIATELY
        vobiz_to_el = asyncio.create_task(_relay_vobiz_to_elevenlabs(vobiz_ws, el_ws, state))
        el_to_vobiz = asyncio.create_task(_relay_elevenlabs_to_vobiz(el_ws, vobiz_ws, state))

        done, pending = await asyncio.wait(
            [vobiz_to_el, el_to_vobiz],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔗 [SALES_BRIDGE] EL connection closed: {e}", flush=True)
    except asyncio.TimeoutError:
        print(f"🔗 [SALES_BRIDGE] EL init timeout for {call_id}", flush=True)
    except Exception as e:
        print(f"🔗 [SALES_BRIDGE] Bridge error: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
    finally:
        if el_ws:
            try:
                await el_ws.close()
            except Exception:
                pass
        try:
            await vobiz_ws.close()
        except Exception:
            pass

        print(
            f"🔗 [SALES_BRIDGE] Bridge closed: call_id={call_id} "
            f"vobiz_in={state['vobiz_chunks_in']} el_out={state['el_chunks_out']}"
        )
