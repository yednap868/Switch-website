"""
Switch WABA webhook — handles incoming WhatsApp messages and button replies
for the Switch phone number (separate from Vance's main number).

Routes interactive button replies (interview_yes/no) to the placement pipeline.
Text replies like "Haan" trigger admin notification with candidate details.
"""

import json
import os
import threading
import time

import requests

from fastapi import APIRouter, BackgroundTasks, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from models.sql_models import Placement, JobApplication, Job, User, WaBlastLog
from services.employer_match_service import _send_via_switch, _normalize_wa_phone
from services.jyoti_wa_service import handle_message as jyoti_handle
from services.placement_service import handle_candidate_confirmed, handle_candidate_declined
from services.switch_post_card_service import (
    confirm_worker_arrival,
    cancel_worker_arrival,
    worker_enroute,
    worker_noshow,
    handle_replacement_accepted,
    handle_replacement_declined,
    handle_day_bad_feedback,
    handle_worker_wants_quit,
    handle_employer_otp,
    handle_employer_cash_confirmed,
    handle_morning_confirm,
    handle_employer_ready,
    handle_employer_needs_help,
)
from utils.postgres import get_db
from utils.whatsapp.components import MsgComponents

router = APIRouter(prefix="/api/switch-wa", tags=["Switch WhatsApp Webhook"])

SWITCH_WEBHOOK_VERIFY_TOKEN = os.getenv(
    "SWITCH_WEBHOOK_VERIFY_TOKEN",
    os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", ""),
)

_SWITCH_PHONE_ID = os.getenv("SWITCH_PHONE_NUMBER_ID", "990475317490297")
_WA_MESSAGES_URL = f"https://graph.facebook.com/v21.0/{_SWITCH_PHONE_ID}/messages"


def _wa_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('META_SYS_USER_TOKEN', '')}",
        "Content-Type": "application/json",
    }


@router.get("/webhook")
async def switch_wa_verify(
    request: Request,
    hub_mode: str = Query(default=None, alias="hub.mode"),
    hub_verify_token: str = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str = Query(default=None, alias="hub.challenge"),
):
    """Meta webhook verification (GET)."""
    if hub_mode == "subscribe" and hub_verify_token == SWITCH_WEBHOOK_VERIFY_TOKEN:
        print(f"[SWITCH_WA] Webhook verified")
        return PlainTextResponse(hub_challenge or "")
    return PlainTextResponse("Forbidden", status_code=403)


@router.get("/debug")
async def switch_wa_debug(phone: str = "918368828660", text: str = "test"):
    """Debug endpoint — runs full Jyoti pipeline and returns result without sending WA."""
    results = {}
    try:
        from services.jyoti_wa_service import handle_message as jyoti_handle_test
        results["jyoti_reply"] = jyoti_handle_test(phone, text)
    except Exception as e:
        results["jyoti_error"] = str(e)
    try:
        payload = MsgComponents.text_scaffold(to=_normalize_wa_phone(phone), text="debug test")
        results["send_result"] = _send_via_switch(payload)
    except Exception as e:
        results["send_error"] = str(e)
    results["meta_token_set"] = bool(os.getenv("META_SYS_USER_TOKEN"))
    results["anthropic_key_set"] = bool(os.getenv("ANTHROPIC_API_KEY"))
    results["switch_phone_id"] = os.getenv("SWITCH_PHONE_NUMBER_ID", "990475317490297")
    return JSONResponse(results)


@router.post("/webhook")
async def switch_wa_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming messages from Switch WABA — button replies, text, etc."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "ok"})

    entries = body.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for message in messages:
                msg_type = message.get("type")
                sender = message.get("from", "")
                wamid = message.get("id", "")
                print(f"[SWITCH_WA] Received {msg_type} from {sender} wamid={wamid}")
                if msg_type == "text":
                    text = message.get("text", {}).get("body", "")
                    cleaned = text.strip().lower().rstrip(".")
                    if cleaned in AFFIRMATIVE_WORDS:
                        background_tasks.add_task(_handle_text_reply, sender, text)
                    elif cleaned.isdigit() and len(cleaned) == 4:
                        background_tasks.add_task(_handle_otp_text, sender, cleaned, wamid)
                    elif "cash" in cleaned and "paid" in cleaned:
                        background_tasks.add_task(_handle_cash_paid_text, sender)
                    else:
                        background_tasks.add_task(_jyoti_reply, sender, text, wamid)
                elif msg_type == "audio":
                    media_id = message.get("audio", {}).get("id", "")
                    background_tasks.add_task(_jyoti_voice_message, sender, media_id, wamid)
                elif msg_type == "interactive":
                    background_tasks.add_task(_process_interactive, message)
                else:
                    print(f"[SWITCH_WA] Skipping {msg_type} from {sender}")
            statuses = value.get("statuses", [])
            for status in statuses:
                background_tasks.add_task(_process_status, status)

    return JSONResponse({"status": "ok"})


def _mark_read_and_typing(wamid: str):
    """Mark as read (blue ticks) + show typing indicator in one API call."""
    if not wamid:
        return
    try:
        requests.post(
            _WA_MESSAGES_URL,
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": wamid,
                "typing_indicator": {"type": "text"},
            },
            headers=_wa_headers(),
            timeout=5,
        )
        print(f"[SWITCH_WA] Read + typing sent for {wamid}")
    except Exception as e:
        print(f"[SWITCH_WA] Mark-read error: {e}")


def _send_reaction(to: str, wamid: str, emoji: str):
    """React to a message with an emoji."""
    if not wamid or not to:
        return
    try:
        requests.post(
            _WA_MESSAGES_URL,
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "reaction",
                "reaction": {"message_id": wamid, "emoji": emoji},
            },
            headers=_wa_headers(),
            timeout=5,
        )
    except Exception as e:
        print(f"[SWITCH_WA] Reaction error: {e}")


def _transcribe_audio(media_id: str) -> str:
    """Download WhatsApp audio and transcribe via ElevenLabs Scribe STT."""
    el_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not el_key or not media_id:
        print(f"[VOICE] Skipping transcription — el_key={'set' if el_key else 'missing'} media_id={media_id!r}")
        return ""
    try:
        import io
        token = os.getenv("META_SYS_USER_TOKEN", "")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Step 1: Get media download URL from Meta
        meta_resp = requests.get(
            f"https://graph.facebook.com/v21.0/{media_id}",
            headers=auth_headers,
            timeout=10,
        )
        print(f"[VOICE] Meta media lookup: {meta_resp.status_code} — {meta_resp.text[:120]}")
        audio_url = meta_resp.json().get("url", "")
        if not audio_url:
            return ""

        # Step 2: Download audio (Meta requires auth on the CDN URL too)
        audio_resp = requests.get(audio_url, headers=auth_headers, timeout=30)
        print(f"[VOICE] Audio download: {audio_resp.status_code} bytes={len(audio_resp.content)}")
        audio_bytes = audio_resp.content
        if not audio_bytes:
            return ""

        # Step 3: Transcribe with ElevenLabs Scribe
        stt_resp = requests.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": el_key},
            files={"file": ("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg")},
            data={"model_id": "scribe_v1"},
            timeout=30,
        )
        print(f"[VOICE] ElevenLabs STT: {stt_resp.status_code} — {stt_resp.text[:150]}")
        if stt_resp.status_code != 200:
            return ""
        transcript = stt_resp.json().get("text", "").strip()
        print(f"[VOICE] Transcript: {transcript[:100]}")
        return transcript
    except Exception as e:
        print(f"[VOICE] Transcription error: {e}")
        return ""


def _tts_elevenlabs(text: str) -> bytes:
    """Convert text to speech via ElevenLabs. Returns audio bytes or empty."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("JYOTI_VOICE_ID", "")
    if not api_key or not voice_id:
        return b""
    try:
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.content
        print(f"[TTS] ElevenLabs error {resp.status_code}: {resp.text[:100]}")
        return b""
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return b""


def _upload_and_send_audio(to: str, audio_bytes: bytes):
    """Upload audio to Meta media API and send as WhatsApp voice note."""
    if not audio_bytes:
        return
    token = os.getenv("META_SYS_USER_TOKEN", "")
    phone_id = os.getenv("SWITCH_PHONE_NUMBER_ID", "990475317490297")
    try:
        import io
        # Upload media
        upload_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{phone_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("voice.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
            timeout=30,
        )
        media_id = upload_resp.json().get("id", "")
        if not media_id:
            print(f"[TTS] Media upload failed: {upload_resp.text[:100]}")
            return
        # Send audio message
        requests.post(
            _WA_MESSAGES_URL,
            headers=_wa_headers(),
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "audio",
                "audio": {"id": media_id},
            },
            timeout=15,
        )
        print(f"[TTS] Voice note sent to {to}")
    except Exception as e:
        print(f"[TTS] Send error: {e}")


def _jyoti_voice_message(sender: str, media_id: str, wamid: str):
    """Handle incoming voice note: transcribe → Jyoti → reply (text + optional voice)."""
    _mark_read_and_typing(wamid)
    transcript = _transcribe_audio(media_id)
    if not transcript:
        # No Whisper key or transcription failed — ask them to type
        payload = MsgComponents.text_scaffold(
            to=_normalize_wa_phone(sender),
            text="Aapki voice note sun li! Abhi text mein likhkar bhejein please, zyada achha help kar sakenge. 🙏",
        )
        _send_via_switch(payload)
        return
    # Process transcription through Jyoti
    _jyoti_reply(sender, transcript, wamid)


def _process_status(status: dict):
    """Update wa_blast_logs when Meta sends delivered/read status for a blast message."""
    wamid = status.get("id", "")
    status_val = status.get("status", "")
    ts = float(status.get("timestamp", time.time()))

    if status_val not in ("delivered", "read"):
        return

    db = get_db()
    try:
        log = db.query(WaBlastLog).filter(WaBlastLog.wamid == wamid).first()
        if not log:
            return
        if status_val == "delivered" and not log.delivered_at:
            log.delivered_at = ts
        elif status_val == "read" and not log.read_at:
            log.read_at = ts
            if not log.delivered_at:
                log.delivered_at = ts
        db.commit()
        print(f"[BLAST] {status_val} — {log.phone} ({log.campaign})")
    except Exception as e:
        print(f"[BLAST] Status update error: {e}")
    finally:
        db.close()


def _process_interactive(message: dict):
    """Handle interactive button/list replies."""
    sender = message.get("from", "")
    interactive = message.get("interactive", {})
    if interactive.get("type") == "button_reply":
        button_id = interactive.get("button_reply", {}).get("id", "")
        button_title = interactive.get("button_reply", {}).get("title", "")
        print(f"[SWITCH_WA] Button reply from {sender}: id={button_id!r} title={button_title!r}")
        _handle_button_reply(button_id, button_title, sender)
    elif interactive.get("type") == "list_reply":
        row_id = interactive.get("list_reply", {}).get("id", "")
        print(f"[SWITCH_WA] List reply from {sender}: {row_id}")


def _handle_button_reply(button_id: str, button_title: str, sender: str):
    """Parse button ID/title and route to placement pipeline.

    Handles two sources:
    1. Dynamic interactive messages: button IDs like interview_yes_{placement_id}
    2. interview_invite_urgent template: fixed buttons matched by title text
    """
    # --- Dynamic interactive message buttons (placement-specific) ---
    if button_id.startswith("interview_yes_"):
        placement_id_str = button_id.replace("interview_yes_", "")
        try:
            placement_id = int(placement_id_str)
        except ValueError:
            print(f"[SWITCH_WA] Invalid placement ID: {placement_id_str}")
            return
        threading.Thread(
            target=handle_candidate_confirmed,
            args=(placement_id,),
            daemon=True,
        ).start()

    elif button_id.startswith("interview_no_"):
        placement_id_str = button_id.replace("interview_no_", "")
        try:
            placement_id = int(placement_id_str)
        except ValueError:
            print(f"[SWITCH_WA] Invalid placement ID: {placement_id_str}")
            return
        threading.Thread(
            target=handle_candidate_declined,
            args=(placement_id,),
            daemon=True,
        ).start()

    # --- Post-card pipeline buttons ---
    elif button_id.startswith("confirm_arrival_"):
        pid = _parse_placement_id(button_id, "confirm_arrival_")
        if pid:
            threading.Thread(target=confirm_worker_arrival, args=(pid,), daemon=True).start()

    elif button_id.startswith("cancel_arrival_"):
        pid = _parse_placement_id(button_id, "cancel_arrival_")
        if pid:
            threading.Thread(target=cancel_worker_arrival, args=(pid,), daemon=True).start()

    elif button_id.startswith("enroute_delayed_"):
        pid = _parse_placement_id(button_id, "enroute_delayed_")
        if pid:
            threading.Thread(target=worker_enroute, args=(pid, True), daemon=True).start()

    elif button_id.startswith("enroute_"):
        pid = _parse_placement_id(button_id, "enroute_")
        if pid:
            threading.Thread(target=worker_enroute, args=(pid, False), daemon=True).start()

    elif button_id.startswith("noshow_"):
        pid = _parse_placement_id(button_id, "noshow_")
        if pid:
            threading.Thread(target=worker_noshow, args=(pid,), daemon=True).start()

    elif button_id.startswith("replacement_yes_"):
        pid = _parse_placement_id(button_id, "replacement_yes_")
        if pid:
            threading.Thread(target=handle_replacement_accepted, args=(pid, sender), daemon=True).start()

    elif button_id.startswith("replacement_no_"):
        pid = _parse_placement_id(button_id, "replacement_no_")
        if pid:
            threading.Thread(target=handle_replacement_declined, args=(pid, sender), daemon=True).start()

    elif button_id.startswith("day_bad_"):
        pid = _parse_placement_id(button_id, "day_bad_")
        if pid:
            threading.Thread(target=handle_day_bad_feedback, args=(pid, True), daemon=True).start()

    elif button_id.startswith("emp_day_bad_"):
        pid = _parse_placement_id(button_id, "emp_day_bad_")
        if pid:
            threading.Thread(target=handle_day_bad_feedback, args=(pid, False), daemon=True).start()

    elif button_id.startswith("week_quit_"):
        pid = _parse_placement_id(button_id, "week_quit_")
        if pid:
            threading.Thread(target=handle_worker_wants_quit, args=(pid,), daemon=True).start()

    elif button_id.startswith("morning_go_"):
        pid = _parse_placement_id(button_id, "morning_go_")
        if pid:
            threading.Thread(target=handle_morning_confirm, args=(pid,), daemon=True).start()

    elif button_id.startswith("morning_no_"):
        pid = _parse_placement_id(button_id, "morning_no_")
        if pid:
            threading.Thread(target=worker_noshow, args=(pid,), daemon=True).start()

    elif button_id.startswith("emp_ready_"):
        pid = _parse_placement_id(button_id, "emp_ready_")
        if pid:
            threading.Thread(target=handle_employer_ready, args=(pid, sender), daemon=True).start()

    elif button_id.startswith("emp_help_"):
        pid = _parse_placement_id(button_id, "emp_help_")
        if pid:
            threading.Thread(target=handle_employer_needs_help, args=(pid, sender), daemon=True).start()

    elif button_id.startswith(("day_good_", "day_ok_", "emp_day_good_", "week_good_", "week_ok_", "morning_delay_")):
        print(f"[SWITCH_WA] Positive feedback button {button_id!r} from {sender}")

    # --- interview_invite_urgent template buttons (matched by title) ---
    elif "हाँ" in button_title or "aa raha" in button_title.lower():
        print(f"[SWITCH_WA] Template YES from {sender}")
        threading.Thread(target=_handle_template_yes, args=(sender,), daemon=True).start()

    elif "नहीं" in button_title or "nahi" in button_title.lower():
        print(f"[SWITCH_WA] Template NO from {sender}")
        threading.Thread(target=_handle_template_no, args=(sender,), daemon=True).start()

    else:
        print(f"[SWITCH_WA] Unknown button id={button_id!r} title={button_title!r} from {sender}")


def _parse_placement_id(button_id: str, prefix: str):
    """Extract integer placement ID from button_id like 'prefix{id}'. Returns None on error."""
    try:
        return int(button_id[len(prefix):])
    except (ValueError, IndexError):
        print(f"[SWITCH_WA] Bad placement ID in button {button_id!r}")
        return None


def _handle_template_yes(sender: str):
    """Candidate tapped 'Haan aa raha hoon' on the interview_invite_urgent template.

    Looks up the most recent active placement for this phone and confirms it.
    If no placement exists, falls back to admin notification.
    """
    db = get_db()
    try:
        placement = (
            db.query(Placement)
            .filter(
                Placement.user_id == sender,
                Placement.status.in_(["matched", "interview_invited"]),
            )
            .order_by(Placement.id.desc())
            .first()
        )
        if placement:
            print(f"[SWITCH_WA] Confirming placement #{placement.id} for {sender}")
            handle_candidate_confirmed(placement.id)
        else:
            print(f"[SWITCH_WA] No active post-card placement for {sender}")
    except Exception as e:
        print(f"[SWITCH_WA] Error handling template YES for {sender}: {e}")
    finally:
        db.close()


def _handle_template_no(sender: str):
    """Candidate tapped 'Nahi aaj nahi ho payega' on the interview_invite_urgent template."""
    db = get_db()
    try:
        placement = (
            db.query(Placement)
            .filter(
                Placement.user_id == sender,
                Placement.status.in_(["matched", "interview_invited"]),
            )
            .order_by(Placement.id.desc())
            .first()
        )
        if placement:
            print(f"[SWITCH_WA] Declining placement #{placement.id} for {sender}")
            handle_candidate_declined(placement.id)
        else:
            print(f"[SWITCH_WA] No active placement for {sender} on template NO")
    except Exception as e:
        print(f"[SWITCH_WA] Error handling template NO for {sender}: {e}")
    finally:
        db.close()


AFFIRMATIVE_WORDS = {"haan", "ha", "haa", "han", "yes", "yeah", "ok", "okay", "chalega", "theek", "thik", "ji"}
ADMIN_PHONE = "918368828660"


def _jyoti_reply(sender: str, text: str, wamid: str = ""):
    """Call Jyoti AI and send reply back to sender."""
    try:
        _mark_read_and_typing(wamid)
        reply = jyoti_handle(sender, text)
        if not reply:
            return
        to = _normalize_wa_phone(sender)
        # Send voice note if configured, otherwise send text
        if os.getenv("JYOTI_VOICE_ID"):
            audio_bytes = _tts_elevenlabs(reply)
            if audio_bytes:
                _upload_and_send_audio(to, audio_bytes)
            else:
                _send_via_switch(MsgComponents.text_scaffold(to=to, text=reply))
        else:
            _send_via_switch(MsgComponents.text_scaffold(to=to, text=reply))
        if wamid:
            _send_reaction(to, wamid, "🙏")
        print(f"[JYOTI] Replied to {sender}: {reply[:80]}")
    except Exception as e:
        print(f"[JYOTI] Error replying to {sender}: {e}")


def _handle_text_reply(sender: str, text: str):
    """If candidate replies affirmatively, notify admin with details for Rapido booking."""
    cleaned = text.strip().lower().rstrip(".")
    if cleaned not in AFFIRMATIVE_WORDS:
        return

    threading.Thread(
        target=_notify_admin_candidate_ready,
        args=(sender,),
        daemon=True,
    ).start()


def _handle_otp_text(sender: str, otp: str, wamid: str):
    """Employer sends 4-digit OTP for worker check-in."""
    verified = handle_employer_otp(sender, otp)
    if not verified:
        # Not an employer OTP — route to Jyoti
        _jyoti_reply(sender, otp, wamid)


def _handle_cash_paid_text(sender: str):
    """Employer confirms cash payment."""
    handled = handle_employer_cash_confirmed(sender)
    if not handled:
        _jyoti_reply(sender, "cash paid", "")


def _notify_admin_candidate_ready(candidate_phone: str):
    """Look up candidate's active applications and send details to admin."""
    db = get_db()
    try:
        user = db.query(User).filter_by(phone=candidate_phone).first()
        name = user.name if user else candidate_phone
        location = user.location if user else "Unknown"

        apps = db.query(JobApplication).filter(
            JobApplication.user_id == candidate_phone,
            JobApplication.status.in_(["calling_employer", "matched", "employer_shortlisted"]),
        ).all()

        if not apps:
            print(f"[SWITCH_WA] {candidate_phone} said yes but no active applications found")
            return

        job_lines = []
        for a in apps[:5]:
            job = db.query(Job).filter_by(job_id=a.job_id).first()
            if job:
                job_lines.append(
                    f"• {job.title} — {job.company} ({job.location})\n"
                    f"  Employer: {job.phone or 'N/A'}"
                )

        jobs_text = "\n".join(job_lines)

        admin_msg = (
            f"🚗 RAPIDO BOOK KARO!\n\n"
            f"Candidate: {name}\n"
            f"Phone: {candidate_phone}\n"
            f"Location: {location}\n\n"
            f"Jobs applied:\n{jobs_text}\n\n"
            f"Candidate ne Haan bola hai. Rapido book karo!"
        )

        wa_admin = _normalize_wa_phone(ADMIN_PHONE)
        payload = MsgComponents.text_scaffold(to=wa_admin, text=admin_msg)
        result = _send_via_switch(payload)
        print(f"[SWITCH_WA] Admin notified about {candidate_phone}: {result}")
    except Exception as e:
        print(f"[SWITCH_WA] Error notifying admin about {candidate_phone}: {e}")
    finally:
        db.close()
