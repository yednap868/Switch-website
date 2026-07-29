"""
Placement pipeline service: match → interview invite → check-in → verify → payment → attendance.

Handles the full lifecycle after a candidate-employer match.
"""

import math
import random
import time
import uuid

from models.sql_models import (
    Placement, AttendanceCheckin, PlacementPayment,
    Job, User, JobApplication, EmployerProfile,
)
from services.employer_match_service import _send_via_switch, _normalize_wa_phone
from utils.whatsapp.components import MsgComponents
from utils.postgres import get_db

ADMIN_PHONE = "918368828660"
FRONTEND_HOST = "app.switchlocally.com"
CHECKIN_BASE_URL = f"https://{FRONTEND_HOST}/checkin"
VERIFY_BASE_URL = f"https://{FRONTEND_HOST}/verify"


def create_placement(db, application, job, employer_phone):
    """Create a Placement record from a matched application."""
    placement = Placement(
        application_id=application.id,
        user_id=application.user_id,
        job_id=application.job_id,
        employer_phone=employer_phone or job.phone or "",
        company=job.company or application.company or "",
        role=job.title or application.role or "",
        status="matched",
        job_lat=job.lat,
        job_lng=job.lng,
    )
    db.add(placement)
    db.commit()
    db.refresh(placement)
    print(f"[PLACEMENT] Created placement #{placement.id} for application #{application.id}")
    return placement


def send_interview_invite(placement):
    """Send interactive WhatsApp buttons to candidate asking if they can come for interview."""
    wa_phone = _normalize_wa_phone(placement.user_id)

    body_text = (
        f"🎉 Badhaai ho! {placement.company} ko aapki profile pasand aayi!\n\n"
        f"{placement.role} ke liye interview kar sakte hain.\n"
        f"Kya aap 2 ghante mein aa sakte hain?\n\n"
        f"Aane jaane ka paisa Switch company degi. "
        f"Abhi jaaoge toh naukri aaj hi lag sakti hai!"
    )

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": wa_phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"interview_yes_{placement.id}",
                            "title": "Haan chalega",
                        },
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"interview_no_{placement.id}",
                            "title": "Aaj nahi",
                        },
                    },
                ],
            },
        },
    }

    result = _send_via_switch(payload)
    print(f"[PLACEMENT] Interview invite to {wa_phone}: {result}")

    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement.id).first()
        if p:
            p.status = "interview_invited"
            p.interview_invite_sent_at = time.time()
            p.updated_at = time.time()
            db.commit()
    finally:
        db.close()

    return result


def handle_candidate_confirmed(placement_id):
    """Candidate said yes — update status, notify admin, send check-in link."""
    db = get_db()
    try:
        placement = db.query(Placement).filter_by(id=placement_id).first()
        if not placement:
            print(f"[PLACEMENT] Placement #{placement_id} not found")
            return

        placement.status = "candidate_confirmed"
        placement.candidate_confirmed_at = time.time()
        placement.updated_at = time.time()

        checkin_token = uuid.uuid4().hex
        placement.checkin_token = checkin_token

        db.commit()

        _send_candidate_confirmation(placement)
        _send_checkin_link(placement)

        db.commit()
    finally:
        db.close()


def handle_candidate_declined(placement_id):
    """Candidate said no — update status and acknowledge."""
    db = get_db()
    try:
        placement = db.query(Placement).filter_by(id=placement_id).first()
        if not placement:
            return

        placement.status = "candidate_declined"
        placement.updated_at = time.time()
        db.commit()

        wa_phone = _normalize_wa_phone(placement.user_id)
        msg = MsgComponents.text_scaffold(
            to=wa_phone,
            text="Koi baat nahi! Jab bhi taiyaar ho, Switch pe aur jobs milenge. 💪",
        )
        _send_via_switch(msg)
    finally:
        db.close()


def _send_candidate_confirmation(placement):
    """Tell candidate their ride is being booked."""
    wa_phone = _normalize_wa_phone(placement.user_id)
    msg = MsgComponents.text_scaffold(
        to=wa_phone,
        text="Bahut badhiya! 🚀 Ride book ho rahi hai. Aapko jaldi update milega.",
    )
    _send_via_switch(msg)


def _notify_admin_confirmed(placement, candidate_name):
    """WhatsApp admin that candidate confirmed — arrange Rapido."""
    admin_wa = _normalize_wa_phone(ADMIN_PHONE)

    job_location = ""
    db = get_db()
    try:
        job = db.query(Job).filter_by(job_id=placement.job_id).first()
        if job:
            job_location = job.location or ""
        employer = db.query(EmployerProfile).filter_by(phone=placement.employer_phone).first()
        interview_loc = employer.interview_location if employer else ""
    finally:
        db.close()

    location_str = interview_loc or job_location or "Not set"

    text = (
        f"✅ {candidate_name} ({placement.user_id}) confirmed for "
        f"{placement.role} at {placement.company}.\n\n"
        f"📍 Location: {location_str}\n"
        f"📱 Employer: {placement.employer_phone}\n\n"
        f"Arrange Rapido for the candidate."
    )
    msg = MsgComponents.text_scaffold(to=admin_wa, text=text)
    result = _send_via_switch(msg)
    print(f"[PLACEMENT] Admin notified: {result}")


def _send_checkin_link(placement):
    """Send check-in link to candidate."""
    wa_phone = _normalize_wa_phone(placement.user_id)
    checkin_url = f"{CHECKIN_BASE_URL}/{placement.checkin_token}"

    text = (
        f"Jab aap {placement.company} pahunch jaayein, "
        f"yeh link kholein aur check-in karein:\n\n"
        f"{checkin_url}\n\n"
        f"Selfie lein aur location share karein. "
        f"Ek OTP milega jo employer ko dikhana hai."
    )
    msg = MsgComponents.text_scaffold(to=wa_phone, text=text)
    result = _send_via_switch(msg)
    print(f"[PLACEMENT] Check-in link sent to {wa_phone}: {result}")


def send_employer_verify_link(placement):
    """Send verification link to employer after candidate checks in."""
    if not placement.verify_token:
        db = get_db()
        try:
            p = db.query(Placement).filter_by(id=placement.id).first()
            p.verify_token = uuid.uuid4().hex
            db.commit()
            placement.verify_token = p.verify_token
        finally:
            db.close()

    wa_phone = _normalize_wa_phone(placement.employer_phone)
    verify_url = f"{VERIFY_BASE_URL}/{placement.verify_token}"

    text = (
        f"Candidate {placement.company} ke liye pahunch gaya hai!\n\n"
        f"Candidate se OTP lein aur verify karein:\n"
        f"{verify_url}"
    )
    msg = MsgComponents.text_scaffold(to=wa_phone, text=text)
    result = _send_via_switch(msg)
    print(f"[PLACEMENT] Verify link sent to employer {wa_phone}: {result}")


def send_joining_details(placement):
    """Send joining details and bonus info to candidate after payment."""
    wa_phone = _normalize_wa_phone(placement.user_id)

    text = (
        f"🎉 Badhaai ho! Aapki naukri {placement.company} mein {placement.role} ke liye pakki ho gayi!\n\n"
        f"📅 Kal se kaam pe aayein.\n"
        f"💰 30 din kaam karne pe ₹500 bonus milega Switch ki taraf se!\n\n"
        f"Har din check-in ka link aayega WhatsApp pe. "
        f"Roz check-in karna zaroori hai."
    )
    msg = MsgComponents.text_scaffold(to=wa_phone, text=text)
    result = _send_via_switch(msg)
    print(f"[PLACEMENT] Joining details sent to {wa_phone}: {result}")


def send_daily_attendance_link(placement, day_number, checkin_token):
    """Send daily attendance check-in link."""
    wa_phone = _normalize_wa_phone(placement.user_id)
    checkin_url = f"{CHECKIN_BASE_URL}/{checkin_token}"

    text = (
        f"Day {day_number}/30 at {placement.company} 📋\n\n"
        f"Aaj ka check-in karein:\n{checkin_url}"
    )
    msg = MsgComponents.text_scaffold(to=wa_phone, text=text)
    result = _send_via_switch(msg)
    print(f"[PLACEMENT] Day {day_number} attendance link sent to {wa_phone}: {result}")
    return result


def generate_otp():
    """Generate a random 4-digit OTP."""
    return str(random.randint(1000, 9999))


def haversine_km(lat1, lng1, lat2, lng2):
    """Calculate distance in km between two coordinates using Haversine formula."""
    if any(v is None for v in [lat1, lng1, lat2, lng2]):
        return None

    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
