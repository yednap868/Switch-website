"""
HTTP routes for Live Connect — Vobiz answer/hangup webhooks and session initiation.

Vobiz hits these when the outbound call is answered or hung up:
  - answer/candidate → returns <Stream> XML pointing to /ws/live-connect/candidate
  - answer/business  → returns <Stream> XML pointing to /ws/live-connect/business
  - hangup           → handles call end for either party
  - initiate         → API to start a live connect session
"""

import os
import threading
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response
from google.cloud import firestore
from google.cloud import storage as gcs

from services.live_connect_service import (
    analyze_conference_recording,
    end_session,
    get_session,
    initiate_session,
)
from services.vobiz_service import vobiz_service
from utils.db import fs

router = APIRouter(prefix="/api/live-connect", tags=["LiveConnect"])


@router.post("/answer/candidate")
async def live_connect_answer_candidate(request: Request):
    """
    Vobiz answer_url for the candidate leg.
    Returns <Stream> XML pointing to our live connect candidate bridge.
    """
    session_id = request.query_params.get("session_id", "")
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    caller = data.get("From") or data.get("from") or ""
    call_uuid = data.get("CallUUID") or data.get("call_uuid") or ""

    print(f"📞 [LC_ROUTES] Candidate answered: session={session_id} from={caller} uuid={call_uuid}")

    # Update in-memory session immediately (no Firestore blocking)
    session = get_session(session_id)
    if session and call_uuid:
        session["candidate_call_uuid"] = call_uuid

    # Return XML immediately — Firestore logging in background
    xml = vobiz_service.build_custom_stream_xml(
        ws_path="/ws/live-connect/candidate",
        query_params=f"session_id={session_id}",
    )
    print(f"📞 [LC_ROUTES] Returning Stream XML for candidate:\n{xml}")

    def _log():
        try:
            fs.collection("debug_webhooks").document("last_lc_answer_candidate").set(
                {"payload": data, "session_id": session_id, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [LC_ROUTES] Background logging failed: {e}")

    threading.Thread(target=_log, daemon=True).start()

    return Response(content=xml, media_type="application/xml")


@router.post("/answer/business")
async def live_connect_answer_business(request: Request):
    """
    Vobiz answer_url for the business leg (parallel calling).
    Extracts attempt_phone from query params, stores call_uuid in per-attempt dict,
    signals attempt["answered"]. Returns <Stream> XML with attempt_phone in query params.
    """
    session_id = request.query_params.get("session_id", "")
    attempt_phone = request.query_params.get("attempt_phone", "")
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    caller = data.get("From") or data.get("from") or ""
    call_uuid = data.get("CallUUID") or data.get("call_uuid") or ""

    print(f"📞 [LC_ROUTES] Business answered: session={session_id} attempt_phone={attempt_phone} from={caller} uuid={call_uuid}")

    # Update in-memory session immediately (no Firestore blocking)
    session = get_session(session_id)
    if session and attempt_phone:
        attempt = session.get("_attempts", {}).get(attempt_phone)
        if attempt:
            if call_uuid:
                attempt["call_uuid"] = call_uuid
            attempt["answered"].set()
            print(f"📞 [LC_ROUTES] Signaled attempt[{attempt_phone}].answered")
        else:
            print(f"⚠️ [LC_ROUTES] No attempt found for phone {attempt_phone}")

    # Return XML immediately — Firestore logging in background
    xml = vobiz_service.build_custom_stream_xml(
        ws_path="/ws/live-connect/business",
        query_params=f"session_id={session_id}&attempt_phone={attempt_phone}",
    )
    print(f"📞 [LC_ROUTES] Returning Stream XML for business (attempt_phone={attempt_phone}):\n{xml}")

    def _log():
        try:
            fs.collection("debug_webhooks").document("last_lc_answer_business").set(
                {"payload": data, "session_id": session_id, "attempt_phone": attempt_phone, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [LC_ROUTES] Background logging failed: {e}")

    threading.Thread(target=_log, daemon=True).start()

    return Response(content=xml, media_type="application/xml")


@router.post("/answer/reverse-candidate")
async def live_connect_answer_reverse_candidate(request: Request):
    """
    Vobiz answer_url for the candidate leg in reverse flow (business→candidate).
    Extracts attempt_phone from query params, stores call_uuid in per-attempt dict,
    signals attempt["answered"]. Returns <Stream> XML with attempt_phone in query params.
    """
    session_id = request.query_params.get("session_id", "")
    attempt_phone = request.query_params.get("attempt_phone", "")
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    caller = data.get("From") or data.get("from") or ""
    call_uuid = data.get("CallUUID") or data.get("call_uuid") or ""

    print(f"📞 [LC_ROUTES] Reverse candidate answered: session={session_id} attempt_phone={attempt_phone} from={caller} uuid={call_uuid}")

    # Update in-memory session immediately (no Firestore blocking)
    session = get_session(session_id)
    if session and attempt_phone:
        attempt = session.get("_attempts", {}).get(attempt_phone)
        if attempt:
            if call_uuid:
                attempt["call_uuid"] = call_uuid
            attempt["answered"].set()
            print(f"📞 [LC_ROUTES] Signaled attempt[{attempt_phone}].answered")
        else:
            print(f"⚠️ [LC_ROUTES] No attempt found for phone {attempt_phone}")

    # Return XML immediately — Firestore logging in background
    xml = vobiz_service.build_custom_stream_xml(
        ws_path="/ws/live-connect/reverse-candidate",
        query_params=f"session_id={session_id}&attempt_phone={attempt_phone}",
    )
    print(f"📞 [LC_ROUTES] Returning Stream XML for reverse candidate (attempt_phone={attempt_phone}):\n{xml}")

    def _log():
        try:
            fs.collection("debug_webhooks").document("last_lc_answer_reverse_candidate").set(
                {"payload": data, "session_id": session_id, "attempt_phone": attempt_phone, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [LC_ROUTES] Background logging failed: {e}")

    threading.Thread(target=_log, daemon=True).start()

    return Response(content=xml, media_type="application/xml")


@router.post("/hangup")
async def live_connect_hangup(request: Request):
    """
    Vobiz hangup_url for either party in a live connect session.

    With parallel calling, individual attempt hangups should NOT end the session.
    Only end session when:
    - The WINNER's hangup during BRIDGED status
    - The candidate/business party (hold side) hangs up
    """
    session_id = request.query_params.get("session_id", "")
    party = request.query_params.get("party", "")
    attempt_phone = request.query_params.get("attempt_phone", "")
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    duration = data.get("Duration") or data.get("duration")
    hangup_cause = data.get("HangupCause") or data.get("hangup_cause", "")

    print(f"📞 [LC_ROUTES] Hangup: session={session_id} party={party} attempt_phone={attempt_phone} duration={duration} cause={hangup_cause}")

    def _log_hangup():
        try:
            fs.collection("debug_webhooks").document(f"last_lc_hangup_{party}").set(
                {"payload": data, "session_id": session_id, "party": party, "attempt_phone": attempt_phone, "created_at": time.time()}
            )
        except Exception as e:
            print(f"⚠️ [LC_ROUTES] Background hangup logging failed: {e}")

    threading.Thread(target=_log_hangup, daemon=True).start()

    session = get_session(session_id)
    if not session:
        return {"status": "ok", "message": f"Hangup processed (no session) for {party}"}

    status = session.get("status", "")

    # If attempt_phone is provided, this is a parallel attempt hangup
    if attempt_phone:
        attempt = session.get("_attempts", {}).get(attempt_phone)
        if attempt:
            # Record outcome if not already set
            if not attempt.get("outcome"):
                attempt["outcome"] = "hangup"
            attempt["pitch_ended_at"] = attempt.get("pitch_ended_at") or time.time()
            # Signal declined so the coordinator knows this attempt is done
            attempt["declined"].set()

        # Check if this is the WINNER hanging up during bridge
        winner_phone = session.get("_winner_phone")
        if attempt_phone == winner_phone and status == "BRIDGED":
            duration_str = f"{duration}s" if duration else "unknown"
            outcome = f"{party}_hangup (winner, duration={duration_str}, cause={hangup_cause})"
            await end_session(session_id, outcome=outcome)
        else:
            print(f"📞 [LC_ROUTES] Attempt {attempt_phone} hung up (not winner or not bridged), not ending session")
    else:
        # No attempt_phone — this is the hold-side party (candidate in normal flow, business in reverse)
        if party == "business" and status != "BRIDGED":
            print(f"📞 [LC_ROUTES] Business hung up before bridge (status={status}), not ending session")
        elif party == "candidate" and session.get("direction") == "business_to_candidate" and status != "BRIDGED":
            print(f"📞 [LC_ROUTES] Candidate hung up before bridge in reverse flow (status={status}), not ending session")
        else:
            duration_str = f"{duration}s" if duration else "unknown"
            outcome = f"{party}_hangup (duration={duration_str}, cause={hangup_cause})"
            await end_session(session_id, outcome=outcome)

    return {"status": "ok", "message": f"Hangup processed for {party}"}


@router.post("/conference/join")
async def live_connect_conference_join(request: Request):
    """
    Vobiz answer URL for conference bridge.
    Both parties are transferred here — they join the same Vobiz conference room
    so audio is handled natively by Vobiz with zero extra latency.
    """
    session_id = request.query_params.get("session_id", "")
    party = request.query_params.get("party", "")

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    print(f"📞 [LC_ROUTES] Conference join: session={session_id} party={party}")

    session = get_session(session_id)
    room_name = f"lc_bridge_{session_id}"

    if party == "candidate":
        business_name = session.get("business_name", "employer") if session else "employer"
        intro = f"Badhai ho! {business_name} ka HR line pe hai. Himmat se baat karo, all the best!"
    elif party == "business":
        candidate_name = session.get("candidate_name", "candidate") if session else "candidate"
        intro = f"{candidate_name} line pe aa rahe hain. Please baat shuru karo!"
    else:
        intro = ""

    server_host = os.getenv("SERVER_HOST", "api.relayy.world")
    callback_url = f"https://{server_host}/api/live-connect/recording-callback?session_id={session_id}"

    xml = vobiz_service.build_conference_xml(room_name, intro, callback_url=callback_url)

    print(f"📞 [LC_ROUTES] Conference XML for {party}:\n{xml}")
    return Response(content=xml, media_type="application/xml")


@router.post("/recording-callback")
async def live_connect_recording_callback(request: Request):
    """
    Vobiz action callback when conference ends and recording is ready.
    Downloads recording from Vobiz (requires auth), re-uploads to GCS,
    and saves the public URL to both Firestore collections.
    """
    session_id = request.query_params.get("session_id", "")
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    record_url = data.get("RecordUrl") or data.get("record_url") or ""
    record_duration = data.get("RecordingDuration") or data.get("recording_duration") or ""
    conference_name = data.get("ConferenceName") or data.get("conference_name") or ""

    print(f"🎙️ [LC_ROUTES] Recording callback: session={session_id} url={record_url} duration={record_duration}")

    if session_id and record_url:
        threading.Thread(
            target=_download_and_save_recording,
            args=(session_id, record_url, record_duration, conference_name),
            daemon=True,
        ).start()

    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?>\n<Response/>',
        media_type="application/xml",
    )


def _download_and_save_recording(
    session_id: str, vobiz_url: str, duration: str, conference_name: str
) -> None:
    """Download recording from Vobiz, upload to GCS, save URLs to Firestore, then transcribe + analyze."""
    auth_id = os.getenv("VOBIZ_AUTH_ID", "")
    auth_token = os.getenv("VOBIZ_AUTH_TOKEN", "")
    bucket_name = os.getenv("GCS_RECORDING_BUCKET", "relay-15824-recordings")

    public_url = ""
    mp3_bytes = b""
    try:
        resp = httpx.get(
            vobiz_url,
            headers={"X-Auth-ID": auth_id, "X-Auth-Token": auth_token},
            timeout=60,
        )
        resp.raise_for_status()
        mp3_bytes = resp.content
        print(f"🎙️ [LC_ROUTES] Downloaded recording: {len(mp3_bytes)} bytes")

        client = gcs.Client()
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            print(f"🎙️ [LC_ROUTES] Creating GCS bucket: {bucket_name}")
            bucket = client.create_bucket(bucket_name, location="asia-south1")

        blob_path = f"recordings/live_connect/{session_id}.mp3"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(mp3_bytes, content_type="audio/mpeg")
        blob.make_public()
        public_url = blob.public_url
        print(f"🎙️ [LC_ROUTES] Uploaded to GCS: {public_url}")
    except Exception as e:
        print(f"⚠️ [LC_ROUTES] Failed to download/upload recording: {e}")

    recording_url = public_url or vobiz_url
    try:
        fs.collection("live_connect_sessions").document(session_id).update({
            "recording_url": recording_url,
            "recording_duration": duration,
            "conference_name": conference_name,
        })
        print(f"✅ [LC_ROUTES] Saved recording URL to live_connect_sessions for {session_id}")
    except Exception as e:
        print(f"⚠️ [LC_ROUTES] Failed to save recording to sessions: {e}")
    try:
        fs.collection("telephonic_interviews").document(session_id).set({
            "recording_url": recording_url,
            "recording_duration": duration,
            "recorded_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        print(f"✅ [LC_ROUTES] Saved recording URL to telephonic_interviews for {session_id}")
    except Exception as e:
        print(f"⚠️ [LC_ROUTES] Failed to save recording to interviews: {e}")

    if mp3_bytes:
        analyze_conference_recording(session_id, mp3_bytes, recording_url)


@router.post("/initiate")
async def live_connect_initiate(request: Request):
    """
    API to start a live connect V2 session (screen-first, multi-call).

    Body:
        candidate_phone: str - Candidate phone number (required)
        candidate_name: str (optional) - Candidate name if known
        candidate_id: str (optional) - Candidate ID
    """
    data = await request.json()

    candidate_phone = data.get("candidate_phone", "")
    if not candidate_phone:
        return {
            "status": "error",
            "message": "candidate_phone is required",
        }

    session = await initiate_session(
        candidate_phone=candidate_phone,
        candidate_name=data.get("candidate_name", ""),
        candidate_id=data.get("candidate_id", ""),
        test_business_phone=data.get("test_business_phone", ""),
    )

    # Return only serializable fields
    result = {k: v for k, v in session.items() if not k.startswith("_")}
    return {"status": "success", "session": result}


@router.get("/debug")
async def live_connect_debug():
    """Debug endpoint to verify env vars and Vobiz account numbers."""
    lc_agent = os.getenv("ELEVENLABS_LIVE_CONNECT_AGENT_ID", "")
    main_agent = os.getenv("ELEVENLABS_AGENT_ID", "")
    vobiz_phone_env = os.getenv("VOBIZ_PHONE_NUMBER", "")
    vobiz_auth = os.getenv("VOBIZ_AUTH_ID", "")

    result = {
        "live_connect_agent_id": lc_agent[:20] + "..." if lc_agent else "(NOT SET)",
        "main_agent_id": main_agent[:20] + "..." if main_agent else "(NOT SET)",
        "vobiz_phone_env": vobiz_phone_env or "(NOT SET)",
        "vobiz_phone_service": vobiz_service.phone_number or "(NOT SET)",
        "vobiz_auth_id": vobiz_auth[:10] + "..." if vobiz_auth else "(NOT SET)",
        "using_agent": (lc_agent or main_agent)[:20] + "..." if (lc_agent or main_agent) else "(NONE)",
    }

    # List numbers on the Vobiz account
    try:
        account_numbers = await vobiz_service.list_phone_numbers()
        result["vobiz_account_numbers"] = account_numbers
    except Exception as e:
        result["vobiz_account_numbers_error"] = str(e)

    return result
