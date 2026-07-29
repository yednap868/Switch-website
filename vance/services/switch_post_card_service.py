"""
Automated post-card placement pipeline (Steps 1–8).

Triggered by KYC completion; subsequent steps run via WhatsApp replies and cron jobs.
All 8 steps run without human intervention.
"""

import json
import math
import random
import re
import threading
import time
import traceback
from datetime import datetime, timedelta
from typing import Optional

from models.sql_models import Placement, Job, User, JobApplication
from services.employer_match_service import _send_via_switch, _normalize_wa_phone
from services.notification_service import notify_user, Content
from utils.whatsapp.components import MsgComponents
from utils.postgres import get_db
from utils.upi import generate_upi_link

FRONTEND_HOST = "app.switchlocally.com"
ADMIN_PHONE = "918368828660"
DEFAULT_JOINING_TIME = "09:00 AM"

_ACTIVE_STATUSES = {
    "confirmed", "evening_confirmed", "en_route", "en_route_delayed",
    "at_risk", "checked_in", "employer_verified", "payment_pending",
    "payment_complete", "joined", "active",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now_ist() -> datetime:
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def _today_ist() -> str:
    return _now_ist().strftime("%Y-%m-%d")


def _tomorrow_ist() -> str:
    return (_now_ist() + timedelta(days=1)).strftime("%Y-%m-%d")


def _haversine_km(lat1, lng1, lat2, lng2) -> Optional[float]:
    if any(v is None for v in [lat1, lng1, lat2, lng2]):
        return None
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _maps_url(lat, lng) -> str:
    if lat and lng:
        return f"https://maps.google.com/?q={lat},{lng}"
    return "https://maps.google.com"


def _first_name(user: Optional[User]) -> str:
    if not user:
        return "दोस्त"
    return (user.name or "दोस्त").split()[0]


def _notify_admin(text: str):
    try:
        _send_via_switch(MsgComponents.text_scaffold(
            to=_normalize_wa_phone(ADMIN_PHONE), text=text
        ))
    except Exception as e:
        print(f"[POST_CARD] Admin notify error: {e}")


def _push(user_id: str, title: str, body: str, url: str = "/", idempotency_key: str = ""):
    try:
        notify_user(
            user_id,
            Content(type="placement", title=title, body=body, url=url),
            idempotency_key=idempotency_key or None,
        )
    except Exception as e:
        print(f"[POST_CARD] Push notify error for {user_id}: {e}")


# ── Step 1: Match + joining details ──────────────────────────────────────────

def _find_best_job(db, user: User) -> Optional[Job]:
    user_role = (user.job_role or "").lower().strip()
    if not user_role:
        roles = json.loads(user.preferred_roles or "[]")
        user_role = roles[0].lower() if roles else ""

    jobs = db.query(Job).filter(Job.openings > 0).all()
    scored = []
    for job in jobs:
        job_cat = (job.category or "").lower()
        if not (job_cat == user_role or user_role in job_cat or job_cat in user_role):
            continue
        dist = _haversine_km(user.lat, user.lng, job.lat, job.lng)
        if dist is None or dist > 5:
            continue
        score = (5 - dist) * 10
        salary_mid = (job.salary_min + job.salary_max) / 2 if job.salary_max else job.salary_min
        if user.expected_salary_min and salary_mid >= user.expected_salary_min:
            score += 20
        scored.append((score, job))

    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def trigger_post_card_from_app_hire(user_id: str, joining_details: dict):
    """Step 1 variant: triggered when app sets activeJobKey for the first time.

    Uses pre-filled joining_details from the app (no job matching needed).
    joining_details must have: company, role, joiningAbsoluteDate (YYYY-MM-DD),
    and optionally joiningDate (Hindi label for time slot).
    """
    def _run():
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if not user:
                return

            iso_date = joining_details.get("joiningAbsoluteDate", "")
            if not iso_date:
                # Parse Hindi label: "आज" = today, anything with "कल" = tomorrow
                label = joining_details.get("joiningDate", "")
                if "कल" in label or "kal" in label.lower():
                    iso_date = _tomorrow_ist()
                else:
                    iso_date = _today_ist()

            # Pick joining time from Hindi time slot
            label = joining_details.get("joiningDate", "")
            if "दोपहर" in label:
                joining_time = "12:00 PM"
            elif "शाम" in label:
                joining_time = "05:00 PM"
            else:
                joining_time = DEFAULT_JOINING_TIME  # 09:00 AM

            # Avoid duplicates for the same date
            existing = db.query(Placement).filter(
                Placement.user_id == user_id,
                Placement.joining_date == iso_date,
                Placement.status.in_(list(_ACTIVE_STATUSES)),
            ).first()
            if existing:
                print(f"[POST_CARD] Placement already exists for {user_id} on {iso_date}")
                return

            company = joining_details.get("company", "")
            role = joining_details.get("roleEn") or joining_details.get("role", "")

            # Try to find matching job in DB for employer phone + coordinates
            emp_phone = ""
            job_lat, job_lng = None, None
            job_id = "app_hire"
            if company:
                from sqlalchemy import func
                job = db.query(Job).filter(
                    func.lower(Job.company).contains(company.lower()[:15])
                ).first()
                if job:
                    emp_phone = job.phone or ""
                    job_lat = job.lat
                    job_lng = job.lng
                    job_id = job.job_id

            otp = str(random.randint(1000, 9999))
            placement = Placement(
                application_id=0,
                user_id=user_id,
                job_id=job_id,
                employer_phone=emp_phone,
                company=company,
                role=role,
                status="confirmed",
                job_lat=job_lat,
                job_lng=job_lng,
                joining_date=iso_date,
                joining_time=joining_time,
                joining_otp=otp,
            )
            db.add(placement)
            db.commit()
            db.refresh(placement)

            _send_step1_joining_details(user, _make_job_stub(joining_details, job_lat, job_lng), placement)
            _push(
                user_id,
                title="🎉 नौकरी पक्की हो गई!",
                body=f"{company} — {role} · {iso_date}",
                url="/card",
                idempotency_key=f"step1_{placement.id}",
            )
            print(f"[POST_CARD] App-hire Step 1 done — placement #{placement.id} for {user_id} → {company}")
        except Exception as e:
            print(f"[POST_CARD] App-hire Step 1 error for {user_id}: {e}")
            traceback.print_exc()
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()


def _make_job_stub(joining_details: dict, lat=None, lng=None):
    """Build a minimal Job-like object from joining_details for _send_step1_joining_details."""
    class _JobStub:
        pass
    j = _JobStub()
    j.company = joining_details.get("company", "")
    j.title = joining_details.get("roleEn") or joining_details.get("role", "")
    j.salary_min = 12000
    j.salary_max = 15000
    j.location = joining_details.get("address", "")
    j.lat = lat
    j.lng = lng
    pay = joining_details.get("pay", "")
    if pay:
        import re
        nums = re.findall(r"\d+", pay.replace(",", ""))
        if nums:
            j.salary_min = int(nums[0]) * (1000 if int(nums[0]) < 1000 else 1)
            j.salary_max = int(nums[-1]) * (1000 if int(nums[-1]) < 1000 else 1)
    return j


def trigger_post_card_flow(user_id: str, job_id: str = ""):
    """Step 1: find best job, create placement, send joining details via WhatsApp."""
    def _run():
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if not user:
                return

            # Avoid duplicate confirmed placements for tomorrow
            tomorrow = _tomorrow_ist()
            existing = db.query(Placement).filter(
                Placement.user_id == user_id,
                Placement.joining_date == tomorrow,
                Placement.status.in_(list(_ACTIVE_STATUSES)),
            ).first()
            if existing:
                print(f"[POST_CARD] Placement already exists for {user_id} on {tomorrow}")
                return

            job = None
            if job_id:
                job = db.query(Job).filter_by(job_id=job_id).first()
            if not job:
                job = _find_best_job(db, user)
            if not job:
                print(f"[POST_CARD] No matching job for {user_id}")
                return

            app = None
            if job_id:
                app = (
                    db.query(JobApplication)
                    .filter_by(user_id=user_id, job_id=job_id)
                    .order_by(JobApplication.created_at.desc())
                    .first()
                )

            otp = str(random.randint(1000, 9999))
            placement = Placement(
                application_id=app.id if app else 0,
                user_id=user_id,
                job_id=job.job_id,
                employer_phone=job.phone or "",
                company=job.company or "",
                role=job.title or "",
                status="confirmed",
                job_lat=job.lat,
                job_lng=job.lng,
                joining_date=tomorrow,
                joining_time=DEFAULT_JOINING_TIME,
                joining_otp=otp,
            )
            db.add(placement)
            db.commit()
            db.refresh(placement)

            _send_step1_joining_details(user, job, placement)
            _push(
                user_id,
                title="🎉 नौकरी पक्की हो गई!",
                body=f"{job.company} — {job.title} · कल {placement.joining_time}",
                url="/card",
                idempotency_key=f"step1_{placement.id}",
            )
            print(f"[POST_CARD] Step 1 done — placement #{placement.id} for {user_id} → {job.company}")
        except Exception as e:
            print(f"[POST_CARD] Step 1 error for {user_id}: {e}")
            traceback.print_exc()
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()


def _send_step1_joining_details(user: User, job: Job, placement: Placement):
    to = _normalize_wa_phone(user.phone)
    name = _first_name(user)
    salary = job.salary_max or job.salary_min or 0
    location_line = f"\n📍 {job.location}" if job.location else ""
    text = (
        f"✅ Joining confirm: {name} ji!\n\n"
        f"🏢 Company: {job.company or ''}\n"
        f"💼 Role: {job.title or ''}\n"
        f"💰 Salary: Rs.{salary}/month\n"
        f"⏰ Report time: {placement.joining_time}{location_line}\n\n"
        f"📋 Documents: Aadhaar card (original + copy), 2 passport photos\n\n"
        f"🔑 Check-in OTP: *{placement.joining_otp}*\n"
        f"Employer ko yeh OTP dikhayein jab pahunchein."
    )
    _send_via_switch(MsgComponents.text_scaffold(to=to, text=text))
    if job.lat and job.lng:
        _send_via_switch(MsgComponents.text_scaffold(to=to, text=_maps_url(job.lat, job.lng)))


# ── Step 2: Evening confirmation (cron at 8 PM IST) ──────────────────────────

def run_evening_confirmation_cron() -> dict:
    db = get_db()
    sent = 0
    try:
        tomorrow = _tomorrow_ist()
        placements = db.query(Placement).filter(
            Placement.joining_date == tomorrow,
            Placement.status == "confirmed",
            Placement.evening_confirm_sent_at.is_(None),
        ).all()

        for p in placements:
            try:
                _send_evening_confirmation(p)
                p.evening_confirm_sent_at = time.time()
                p.updated_at = time.time()
                db.commit()
                sent += 1
            except Exception as e:
                print(f"[POST_CARD] Evening confirm error #{p.id}: {e}")

        return {"sent": sent, "date": tomorrow}
    finally:
        db.close()


def _send_evening_confirmation(p: Placement):
    db = get_db()
    try:
        user = db.query(User).filter_by(phone=p.user_id).first()
        name = _first_name(user)
    finally:
        db.close()

    to = _normalize_wa_phone(p.user_id)
    _send_via_switch(MsgComponents.template_scaffold(
        to=to,
        template_name="switch_evening_confirm",
        language_code="hi",
        body_parameters=[name, p.joining_time, p.company],
        button_payloads=[f"confirm_arrival_{p.id}", f"cancel_arrival_{p.id}"],
    ))
    if p.job_lat and p.job_lng:
        _send_via_switch(MsgComponents.text_scaffold(to=to, text=_maps_url(p.job_lat, p.job_lng)))


def run_evening_followup_cron() -> dict:
    """10 PM: follow-up for non-responders. 10:30 PM: mark AT_RISK."""
    db = get_db()
    now = time.time()
    followup_sent = at_risk_marked = 0
    try:
        tomorrow = _tomorrow_ist()
        placements = db.query(Placement).filter(
            Placement.joining_date == tomorrow,
            Placement.status == "confirmed",
            Placement.evening_confirm_sent_at.isnot(None),
        ).all()

        for p in placements:
            try:
                elapsed = now - p.evening_confirm_sent_at
                to = _normalize_wa_phone(p.user_id)
                # ~2.5 hours after 8 PM send = ~10:30 PM → AT_RISK
                if elapsed >= 9000:
                    p.status = "at_risk"
                    p.updated_at = time.time()
                    db.commit()
                    at_risk_marked += 1
                # ~2 hours after send = ~10 PM → follow-up nudge
                elif elapsed >= 7200:
                    _send_via_switch(MsgComponents.text_scaffold(
                        to=to,
                        text="Kal aa rahe ho? Haan ya nahi batao — seat kisi aur ko mil jayegi 🙏"
                    ))
                    followup_sent += 1
            except Exception as e:
                print(f"[POST_CARD] Evening followup error #{p.id}: {e}")

        return {"followup_sent": followup_sent, "at_risk_marked": at_risk_marked}
    finally:
        db.close()


# ── Step 2 reply handlers ─────────────────────────────────────────────────────

def confirm_worker_arrival(placement_id: int):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        p.status = "evening_confirmed"
        p.updated_at = time.time()
        db.commit()

        to = _normalize_wa_phone(p.user_id)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text=f"✅ Perfect! Kal {p.joining_time} baje {p.company} pahunchna. All the best! 🙏\n\nOTP yaad rakhna: *{p.joining_otp}*"
        ))
        print(f"[POST_CARD] Arrival confirmed for placement #{placement_id}")
    finally:
        db.close()


def cancel_worker_arrival(placement_id: int):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        p.status = "cancelled_by_worker"
        p.updated_at = time.time()
        db.commit()

        to = _normalize_wa_phone(p.user_id)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text="Koi baat nahi! Jab bhi taiyaar ho, Switch pe aur jobs milenge. 💪"
        ))
        print(f"[POST_CARD] Arrival cancelled for placement #{placement_id}")
    finally:
        db.close()
    trigger_auto_replacement(placement_id, "cancelled_by_worker")


# ── Step 2 button: morning reply helpers ─────────────────────────────────────

def handle_morning_confirm(placement_id: int):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        to = _normalize_wa_phone(p.user_id)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text=f"✅ Accha! Aaj {p.joining_time} baje {p.company} pahunchna. All the best! 🙏\n\nOTP: *{p.joining_otp}*",
        ))
    finally:
        db.close()


def handle_employer_ready(placement_id: int, employer_phone: str):
    print(f"[POST_CARD] Employer ready for placement #{placement_id}")


def handle_employer_needs_help(placement_id: int, employer_phone: str):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        to = _normalize_wa_phone(employer_phone)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text="Please describe the issue and our team will assist you shortly.",
        ))
        _notify_admin(f"Employer {employer_phone} needs help with placement #{placement_id}")
    finally:
        db.close()


# ── Step 3: Morning wake-up (cron at 6:30 AM IST) ────────────────────────────

def run_morning_nudge_cron() -> dict:
    db = get_db()
    sent = 0
    try:
        today = _today_ist()
        placements = db.query(Placement).filter(
            Placement.joining_date == today,
            Placement.status.in_(["confirmed", "evening_confirmed", "at_risk"]),
            Placement.morning_nudge_sent_at.is_(None),
        ).all()

        for p in placements:
            try:
                user = db.query(User).filter_by(phone=p.user_id).first()
                name = _first_name(user)
                to = _normalize_wa_phone(p.user_id)
                _send_via_switch(MsgComponents.template_scaffold(
                    to=to,
                    template_name="sw_report_today",
                    language_code="hi",
                    body_parameters=[name, p.joining_time, p.company],
                    button_payloads=[f"morning_go_{p.id}", f"morning_delay_{p.id}", f"morning_no_{p.id}"],
                ))
                _send_via_switch(MsgComponents.text_scaffold(
                    to=to,
                    text=f"🔑 Aaj ka OTP: *{p.joining_otp}*\nEmployer ko yeh OTP dikhayein jab pahunchein.",
                ))
                if p.job_lat and p.job_lng:
                    _send_via_switch(MsgComponents.text_scaffold(to=to, text=_maps_url(p.job_lat, p.job_lng)))
                _push(
                    p.user_id,
                    title="🌅 आज joining का दिन!",
                    body=f"{p.company} · {p.joining_time} बजे पहुँचें",
                    url="/card",
                    idempotency_key=f"morning_{p.id}",
                )
                p.morning_nudge_sent_at = time.time()
                p.updated_at = time.time()
                db.commit()
                sent += 1
            except Exception as e:
                print(f"[POST_CARD] Morning nudge error #{p.id}: {e}")

        return {"sent": sent, "date": today}
    finally:
        db.close()


# ── Step 4: En-route check (cron 30 min before joining_time) ─────────────────

def run_enroute_check_cron() -> dict:
    db = get_db()
    sent = 0
    try:
        today = _today_ist()
        now_ist = _now_ist()
        placements = db.query(Placement).filter(
            Placement.joining_date == today,
            Placement.status.in_(["confirmed", "evening_confirmed", "at_risk"]),
            Placement.enroute_check_sent_at.is_(None),
        ).all()

        for p in placements:
            if not p.joining_time:
                continue
            try:
                jt = datetime.strptime(f"{today} {p.joining_time}", "%Y-%m-%d %I:%M %p")
                minutes_until = (jt - now_ist).total_seconds() / 60
                if not (25 <= minutes_until <= 45):
                    continue

                user = db.query(User).filter_by(phone=p.user_id).first()
                name = _first_name(user)
                to = _normalize_wa_phone(p.user_id)
                _send_via_switch(MsgComponents.template_scaffold(
                    to=to,
                    template_name="switch_enroute_check",
                    language_code="hi",
                    body_parameters=[name, p.joining_time, p.company],
                    button_payloads=[f"enroute_{p.id}", f"enroute_delayed_{p.id}", f"noshow_{p.id}"],
                ))
                _push(
                    p.user_id,
                    title="⏰ निकलने का समय!",
                    body=f"{p.company} पहुँचने में 30 मिनट बाकी",
                    url="/card",
                    idempotency_key=f"enroute_{p.id}",
                )
                p.enroute_check_sent_at = time.time()
                p.updated_at = time.time()
                db.commit()
                sent += 1
            except Exception as e:
                print(f"[POST_CARD] En-route check error #{p.id}: {e}")

        return {"sent": sent}
    finally:
        db.close()


def run_enroute_timeout_cron() -> dict:
    """15 min after en-route check: no response → LIKELY_NO_SHOW + trigger replacement."""
    db = get_db()
    now = time.time()
    marked = 0
    try:
        today = _today_ist()
        placements = db.query(Placement).filter(
            Placement.joining_date == today,
            Placement.status.in_(["confirmed", "evening_confirmed", "at_risk"]),
            Placement.enroute_check_sent_at.isnot(None),
        ).all()

        for p in placements:
            if p.enroute_check_sent_at and (now - p.enroute_check_sent_at) > 900:
                p.status = "likely_no_show"
                p.updated_at = time.time()
                db.commit()
                marked += 1
                trigger_auto_replacement(p.id, "likely_no_show")

        return {"marked": marked}
    finally:
        db.close()


# ── Step 4 reply handlers ─────────────────────────────────────────────────────

def worker_enroute(placement_id: int, delayed: bool = False):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        p.status = "en_route_delayed" if delayed else "en_route"
        p.updated_at = time.time()
        db.commit()
    finally:
        db.close()
    notify_employer_worker_enroute(placement_id, delayed)


def worker_noshow(placement_id: int):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        p.status = "no_show"
        p.updated_at = time.time()
        db.commit()

        to = _normalize_wa_phone(p.user_id)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text="Koi baat nahi. Jab bhi ready ho, Switch pe aur mauke milenge. 💪"
        ))
    finally:
        db.close()
    trigger_auto_replacement(placement_id, "no_show")


# ── Step 5: Employer notification ────────────────────────────────────────────

def notify_employer_worker_enroute(placement_id: int, delayed: bool = False):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p or not p.employer_phone:
            return
        user = db.query(User).filter_by(phone=p.user_id).first()
        worker_name = (user.name if user else "") or p.user_id

        to = _normalize_wa_phone(p.employer_phone)
        eta = p.joining_time + (" (thoda late)" if delayed else "")
        _send_via_switch(MsgComponents.template_scaffold(
            to=to,
            template_name="sw_employer_eta",
            language_code="en",
            body_parameters=[worker_name, eta],
            button_payloads=[f"emp_ready_{p.id}", f"emp_help_{p.id}"],
        ))
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text=f"Worker's check-in OTP: *{p.joining_otp}*\nAsk for this OTP when {worker_name} arrives and reply back to verify.",
        ))
        p.employer_notified_enroute_at = time.time()
        p.updated_at = time.time()
        db.commit()
        print(f"[POST_CARD] Employer notified for placement #{placement_id}")
    except Exception as e:
        print(f"[POST_CARD] Employer notify error #{placement_id}: {e}")
    finally:
        db.close()


# ── Step 6: OTP check-in + payment ───────────────────────────────────────────

def handle_employer_otp(employer_phone: str, otp: str) -> bool:
    """Employer sends 4-digit OTP via WhatsApp. Returns True if verified."""
    if len(otp) != 4 or not otp.isdigit():
        return False

    emp_last10 = re.sub(r"\D", "", employer_phone)[-10:]
    db = get_db()
    try:
        today = _today_ist()
        placement = (
            db.query(Placement)
            .filter(
                Placement.employer_phone.like(f"%{emp_last10}"),
                Placement.joining_otp == otp,
                Placement.joining_date == today,
                Placement.status.in_(["confirmed", "evening_confirmed", "en_route", "en_route_delayed", "at_risk", "likely_no_show"]),
            )
            .order_by(Placement.created_at.desc())
            .first()
        )
        if not placement:
            return False

        placement.status = "checked_in"
        placement.checkin_at = time.time()
        placement.employer_verified_at = time.time()
        placement.updated_at = time.time()
        db.commit()

        _on_checkin_complete(placement)
        return True
    except Exception as e:
        print(f"[POST_CARD] OTP verify error for {employer_phone}: {e}")
        return False
    finally:
        db.close()


def _on_checkin_complete(placement: Placement):
    db = get_db()
    try:
        user = db.query(User).filter_by(phone=placement.user_id).first()
        worker_name = (user.name if user else "") or placement.user_id
        ref_code = (user.referral_code if user else "") or f"SW{placement.user_id[-6:]}"

        to_worker = _normalize_wa_phone(placement.user_id)
        _send_via_switch(MsgComponents.template_scaffold(
            to=to_worker,
            template_name="sw_checkin_done",
            language_code="hi",
            body_parameters=[_first_name(user)],
        ))
        _send_via_switch(MsgComponents.text_scaffold(
            to=to_worker,
            text=f"Refer karo aur ₹200 kamao:\nhttps://{FRONTEND_HOST}/r/{ref_code}",
        ))
        _push(
            placement.user_id,
            title="✅ Check-in हो गया!",
            body="Kaam shuru — ₹200 travel money milega",
            url="/card",
            idempotency_key=f"checkin_{placement.id}",
        )

        if placement.employer_phone:
            to_employer = _normalize_wa_phone(placement.employer_phone)
            pay_url = f"https://{FRONTEND_HOST}/pay/{placement.id}"
            try:
                pay_ref = f"P{placement.id}T{int(time.time())}"[:35]
                pay_url = generate_upi_link(2000.00, pay_ref)
            except Exception:
                pass
            _send_via_switch(MsgComponents.template_scaffold(
                to=to_employer,
                template_name="switch_placement_fee",
                language_code="en",
                body_parameters=[worker_name, placement.company, pay_url],
            ))

        if user:
            user.chowk_streak = (user.chowk_streak or 0) + 1
            user.yogdaan_score = (user.yogdaan_score or 0) + 10
            user.updated_at = time.time()
            db.commit()
    except Exception as e:
        print(f"[POST_CARD] Check-in complete error #{placement.id}: {e}")
    finally:
        db.close()


def handle_employer_cash_confirmed(employer_phone: str) -> bool:
    emp_last10 = re.sub(r"\D", "", employer_phone)[-10:]
    db = get_db()
    try:
        today = _today_ist()
        placement = (
            db.query(Placement)
            .filter(
                Placement.employer_phone.like(f"%{emp_last10}"),
                Placement.status == "checked_in",
                Placement.joining_date == today,
            )
            .order_by(Placement.created_at.desc())
            .first()
        )
        if not placement:
            return False

        placement.payment_status = "cash_collected"
        placement.payment_at = time.time()
        placement.status = "payment_complete"
        placement.updated_at = time.time()
        db.commit()

        to_employer = _normalize_wa_phone(employer_phone)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to_employer,
            text="✅ Cash payment noted! Placement complete. Worker ka kaam shuru ho gaya. 🎉"
        ))
        return True
    except Exception as e:
        print(f"[POST_CARD] Cash confirm error for {employer_phone}: {e}")
        return False
    finally:
        db.close()


# ── Step 7: Auto-replacement engine ──────────────────────────────────────────

def trigger_auto_replacement(placement_id: int, reason: str):
    def _run():
        db = get_db()
        try:
            original = db.query(Placement).filter_by(id=placement_id).first()
            if not original:
                return
            # Already spawned a replacement
            if original.replacement_batch == -1:
                return

            job = db.query(Job).filter_by(job_id=original.job_id).first()
            if not job:
                return

            all_candidates = _find_replacement_candidates(db, original, job)
            if not all_candidates:
                _notify_employer_no_replacement(original)
                return

            # Store all backup phones; send first batch of 3
            backup_phones = [c.phone for c in all_candidates[:9]]
            original.backup_workers = json.dumps(backup_phones)
            original.replacement_batch = 0
            db.commit()

            _send_replacement_offers(original, job, all_candidates[:3])
            print(f"[POST_CARD] Replacement batch 0 sent for #{placement_id}, reason={reason}")
        except Exception as e:
            print(f"[POST_CARD] Auto-replacement error #{placement_id}: {e}")
            traceback.print_exc()
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()


def _find_replacement_candidates(db, original: Placement, job: Job):
    busy_phones = {
        p.user_id for p in db.query(Placement).filter(
            Placement.status.in_(list(_ACTIVE_STATUSES))
        ).all()
    }
    busy_phones.discard(original.user_id)

    job_cat = (job.category or "").lower()
    workers = (
        db.query(User)
        .filter(
            User.photo_url.isnot(None),
            User.phone.notin_(busy_phones),
        )
        .order_by(User.created_at.desc())
        .all()
    )

    matched = []
    for w in workers:
        role = (w.job_role or "").lower()
        if not (role == job_cat or role in job_cat or job_cat in role):
            continue
        dist = _haversine_km(w.lat, w.lng, job.lat, job.lng)
        if dist is None or dist > 5:
            continue
        matched.append((dist, w))

    matched.sort(key=lambda x: x[0])
    return [w for _, w in matched]


def _send_replacement_offers(original: Placement, job: Job, candidates):
    salary = str(job.salary_max or job.salary_min or 0)
    arrive_time = _now_ist().strftime("%I:%M %p").lstrip("0")

    for c in candidates:
        dist = _haversine_km(c.lat, c.lng, job.lat, job.lng)
        dist_str = str(round(dist, 1)) if dist else "2"
        to = _normalize_wa_phone(c.phone)
        _send_via_switch(MsgComponents.template_scaffold(
            to=to,
            template_name="switch_replacement_urgent_u",
            language_code="hi",
            body_parameters=[
                job.company or "", job.title or "", salary,
                job.location or "", dist_str, arrive_time,
            ],
            button_payloads=[f"replacement_yes_{original.id}", f"replacement_no_{original.id}"],
        ))


def handle_replacement_accepted(original_placement_id: int, new_worker_phone: str):
    db = get_db()
    try:
        original = db.query(Placement).filter_by(id=original_placement_id).first()
        if not original:
            return
        # Idempotency: only one replacement per original placement
        if original.replacement_batch == -1:
            to = _normalize_wa_phone(new_worker_phone)
            _send_via_switch(MsgComponents.text_scaffold(
                to=to,
                text="Seat fill ho gayi, agli baar jaldi reply karna! 🙏"
            ))
            return

        job = db.query(Job).filter_by(job_id=original.job_id).first()
        if not job:
            return

        new_user = db.query(User).filter_by(phone=new_worker_phone).first()
        otp = str(random.randint(1000, 9999))
        new_placement = Placement(
            application_id=0,
            user_id=new_worker_phone,
            job_id=original.job_id,
            employer_phone=original.employer_phone,
            company=original.company,
            role=original.role,
            status="confirmed",
            job_lat=original.job_lat,
            job_lng=original.job_lng,
            joining_date=original.joining_date,
            joining_time=original.joining_time,
            joining_otp=otp,
        )
        db.add(new_placement)

        # Mark original as replaced so no further offers go out
        original.replacement_batch = -1
        db.commit()
        db.refresh(new_placement)

        if new_user:
            _send_step1_joining_details(new_user, job, new_placement)

        if original.employer_phone:
            to_employer = _normalize_wa_phone(original.employer_phone)
            arrive_time = _now_ist().strftime("%I:%M %p").lstrip("0")
            _send_via_switch(MsgComponents.text_scaffold(
                to=to_employer,
                text=(
                    f"✅ Replacement worker assign ho gaya!\n\n"
                    f"Worker: {new_user.name if new_user else new_worker_phone}\n"
                    f"⏰ Arriving by {arrive_time}\n"
                    f"🔑 OTP: *{otp}*"
                )
            ))

        backup = json.loads(original.backup_workers or "[]")
        for phone in backup:
            if phone == new_worker_phone:
                continue
            to = _normalize_wa_phone(phone)
            _send_via_switch(MsgComponents.text_scaffold(
                to=to,
                text="Seat fill ho gayi, agli baar jaldi reply karna! 🙏 Aur jobs ke liye Switch open rakho."
            ))

        print(f"[POST_CARD] Replacement placement #{new_placement.id} for original #{original_placement_id}")
    except Exception as e:
        print(f"[POST_CARD] Replacement accept error: {e}")
        traceback.print_exc()
    finally:
        db.close()


def handle_replacement_declined(original_placement_id: int, worker_phone: str):
    db = get_db()
    try:
        original = db.query(Placement).filter_by(id=original_placement_id).first()
        if not original or original.replacement_batch == -1:
            return

        backup = json.loads(original.backup_workers or "[]")
        backup = [p for p in backup if p != worker_phone]
        original.backup_workers = json.dumps(backup)
        db.commit()

        # If all 3 in current batch declined, try next batch
        batch = original.replacement_batch
        batch_responded = batch * 3
        if len(backup) <= max(0, 9 - batch_responded - 3):
            job = db.query(Job).filter_by(job_id=original.job_id).first()
            if job:
                next_batch_start = (batch + 1) * 3
                next_candidates = _find_replacement_candidates(db, original, job)
                if next_batch_start < len(next_candidates):
                    original.replacement_batch = batch + 1
                    db.commit()
                    _send_replacement_offers(original, job, next_candidates[next_batch_start:next_batch_start + 3])
                else:
                    _notify_employer_no_replacement(original)
    except Exception as e:
        print(f"[POST_CARD] Replacement decline error: {e}")
    finally:
        db.close()


def _notify_employer_no_replacement(placement: Placement):
    if not placement.employer_phone:
        return
    to = _normalize_wa_phone(placement.employer_phone)
    _send_via_switch(MsgComponents.text_scaffold(
        to=to,
        text="Aaj ke liye worker available nahi hai. Kal subah bhej denge. Inconvenience ke liye maafi chahte hain. 🙏"
    ))


# ── Step 8: Post-placement retention ─────────────────────────────────────────

def run_retention_day1_cron() -> dict:
    """8 PM on joining day: how was the first day?"""
    db = get_db()
    sent = 0
    try:
        today = _today_ist()
        placements = db.query(Placement).filter(
            Placement.joining_date == today,
            Placement.status.in_(["checked_in", "payment_complete", "joined", "active"]),
        ).all()

        for p in placements:
            try:
                user = db.query(User).filter_by(phone=p.user_id).first()
                name = _first_name(user)
                to = _normalize_wa_phone(p.user_id)
                _send_via_switch(MsgComponents.template_scaffold(
                    to=to,
                    template_name="switch_retention_day1",
                    language_code="hi",
                    body_parameters=[name, p.company],
                    button_payloads=[f"day_good_{p.id}", f"day_ok_{p.id}", f"day_bad_{p.id}"],
                ))

                if p.employer_phone:
                    to_emp = _normalize_wa_phone(p.employer_phone)
                    _send_via_switch(MsgComponents.template_scaffold(
                        to=to_emp,
                        template_name="switch_employer_day1",
                        language_code="en",
                        body_parameters=[name, p.company],
                        button_payloads=[f"emp_day_good_{p.id}", f"emp_day_bad_{p.id}"],
                    ))
                sent += 1
            except Exception as e:
                print(f"[POST_CARD] Day-1 retention error #{p.id}: {e}")

        return {"sent": sent}
    finally:
        db.close()


def run_retention_day3_cron() -> dict:
    db = get_db()
    sent = 0
    try:
        day3_date = (_now_ist() - timedelta(days=3)).strftime("%Y-%m-%d")
        placements = db.query(Placement).filter(
            Placement.joining_date == day3_date,
            Placement.status.in_(["payment_complete", "joined", "active"]),
        ).all()

        for p in placements:
            try:
                user = db.query(User).filter_by(phone=p.user_id).first()
                name = _first_name(user)
                to = _normalize_wa_phone(p.user_id)
                _send_via_switch(MsgComponents.template_scaffold(
                    to=to,
                    template_name="sw_attendance_day3",
                    language_code="hi",
                    body_parameters=[name, p.company or ""],
                ))
                sent += 1
            except Exception as e:
                print(f"[POST_CARD] Day-3 retention error #{p.id}: {e}")

        return {"sent": sent}
    finally:
        db.close()


def run_retention_day7_cron() -> dict:
    db = get_db()
    sent = 0
    try:
        day7_date = (_now_ist() - timedelta(days=7)).strftime("%Y-%m-%d")
        placements = db.query(Placement).filter(
            Placement.joining_date == day7_date,
            Placement.status.in_(["payment_complete", "joined", "active"]),
        ).all()

        for p in placements:
            try:
                user = db.query(User).filter_by(phone=p.user_id).first()
                name = _first_name(user)
                ref_code = (user.referral_code if user else "") or f"SW{p.user_id[-6:]}"
                to = _normalize_wa_phone(p.user_id)

                _send_via_switch(MsgComponents.template_scaffold(
                    to=to,
                    template_name="sw_attendance_week1",
                    language_code="hi",
                    body_parameters=[name, p.company or ""],
                    button_payloads=[f"week_good_{p.id}", f"week_ok_{p.id}", f"week_quit_{p.id}"],
                ))
                sent += 1
            except Exception as e:
                print(f"[POST_CARD] Day-7 retention error #{p.id}: {e}")

        return {"sent": sent}
    finally:
        db.close()


def handle_worker_wants_quit(placement_id: int):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        to = _normalize_wa_phone(p.user_id)
        _send_via_switch(MsgComponents.text_scaffold(
            to=to,
            text=(
                f"Kya problem hui? Batao, hum solve karenge. 🙏\n\n"
                f"Agar doosri naukri chahiye toh Switch pe aur jobs hain:\n"
                f"👉 https://{FRONTEND_HOST}"
            )
        ))
    finally:
        db.close()


def handle_day_bad_feedback(placement_id: int, is_worker: bool = True):
    db = get_db()
    try:
        p = db.query(Placement).filter_by(id=placement_id).first()
        if not p:
            return
        if is_worker:
            # Route to Jyoti for AI-driven resolution — no human needed
            to = _normalize_wa_phone(p.user_id)
            _send_via_switch(MsgComponents.text_scaffold(
                to=to,
                text=(
                    f"Kya problem hui {p.company} mein? Batao — main resolve karne ki koshish karunga. 🙏\n\n"
                    f"(Ya agar doosri naukri chahiye toh bhi batao)"
                )
            ))
        else:
            to = _normalize_wa_phone(p.employer_phone)
            _send_via_switch(MsgComponents.text_scaffold(
                to=to,
                text="Kya problem hui worker ke saath? Batao — hum replace karne ki koshish karenge."
            ))
    finally:
        db.close()
