"""
Switch placement routes — check-in pages, employer verification, payment, and attendance cron.

Two routers:
- `router` (prefix /api/switch) for JSON APIs
- `pages_router` (no prefix) for HTML pages served at /checkin/{token} and /verify/{token}
"""

import asyncio
import os
import random
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta

import requests as _requests

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from models.sql_models import Placement, AttendanceCheckin, PlacementPayment, Job, JobApplication, User
from services.employer_match_service import notify_employer_kyc_complete
from services.placement_service import (
    generate_otp, haversine_km,
    send_employer_verify_link, send_joining_details,
    send_daily_attendance_link,
)
from services.switch_post_card_service import (
    trigger_post_card_flow,
    run_evening_confirmation_cron,
    run_evening_followup_cron,
    run_morning_nudge_cron,
    run_enroute_check_cron,
    run_enroute_timeout_cron,
    run_retention_day1_cron,
    run_retention_day3_cron,
    run_retention_day7_cron,
)
from utils.postgres import get_db
import json as _json

try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    razorpay = None
    RAZORPAY_AVAILABLE = False

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if RAZORPAY_AVAILABLE and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "switch-admin-key")

router = APIRouter(prefix="/api/switch", tags=["Switch Placement"])
pages_router = APIRouter(tags=["Switch Placement Pages"])
templates = Jinja2Templates(directory="templates")


# ── Check-in page ──────────────────────────────────────────────────────────

@pages_router.get("/checkin/{token}")
async def checkin_page(token: str, request: Request):
    """Serve the check-in HTML page for candidate selfie + location."""
    ctx = _load_checkin_context(token)
    ctx["request"] = request
    return templates.TemplateResponse("placement_checkin.html", ctx)


def _load_checkin_context(token: str) -> dict:
    """Look up token across Placement.checkin_token, first_day_checkin_token, AttendanceCheckin.checkin_token."""
    db = get_db()
    try:
        placement = db.query(Placement).filter_by(checkin_token=token).first()
        checkin_type = "interview"

        if not placement:
            placement = db.query(Placement).filter_by(first_day_checkin_token=token).first()
            checkin_type = "first_day"

        if not placement:
            attendance = db.query(AttendanceCheckin).filter_by(checkin_token=token).first()
            if attendance:
                placement = db.query(Placement).filter_by(id=attendance.placement_id).first()
                checkin_type = "attendance"

        if not placement:
            return {"error": True, "message": "Invalid or expired link"}

        already_done = False
        if checkin_type == "interview" and placement.checkin_at:
            already_done = True
        elif checkin_type == "first_day" and placement.first_day_checkin_at:
            already_done = True
        elif checkin_type == "attendance" and attendance and attendance.status != "pending":
            already_done = True

        return {
            "error": False,
            "already_done": already_done,
            "token": token,
            "checkin_type": checkin_type,
            "company": placement.company or "",
            "role": placement.role or "",
        }
    finally:
        db.close()


@router.get("/checkin-context/{token}")
async def checkin_context(token: str):
    """JSON endpoint for React check-in page — returns placement context."""
    ctx = _load_checkin_context(token)
    return JSONResponse(ctx, headers={"Access-Control-Allow-Origin": "*"})


class CheckinSubmitRequest(BaseModel):
    selfie: str
    lat: float
    lng: float


@router.post("/checkin/{token}/submit")
async def checkin_submit(token: str, req: CheckinSubmitRequest):
    """Process check-in: save selfie + location, verify distance, generate OTP."""
    db = get_db()
    try:
        placement, checkin_type, attendance = _find_placement_by_token(db, token)
        if not placement:
            return JSONResponse({"error": "Invalid token"}, status_code=404)

        distance = haversine_km(req.lat, req.lng, placement.job_lat, placement.job_lng)
        location_verified = distance is not None and distance <= 0.2

        otp = generate_otp()

        if checkin_type == "interview":
            placement.checkin_selfie = req.selfie
            placement.checkin_lat = req.lat
            placement.checkin_lng = req.lng
            placement.checkin_otp = otp
            placement.checkin_at = time.time()
            placement.checkin_location_verified = location_verified
            placement.status = "checked_in"
            placement.updated_at = time.time()
        elif checkin_type == "first_day":
            placement.first_day_selfie = req.selfie
            placement.first_day_checkin_at = time.time()
            placement.first_day_location_verified = location_verified
            placement.status = "joined"
            placement.joining_date = datetime.utcnow().strftime("%Y-%m-%d")
            placement.updated_at = time.time()
        elif checkin_type == "attendance" and attendance:
            attendance.selfie = req.selfie
            attendance.lat = req.lat
            attendance.lng = req.lng
            attendance.otp = otp
            attendance.location_verified = location_verified
            attendance.status = "checked_in"

        db.commit()

        if checkin_type == "interview":
            _bg_send_employer_verify(placement.id)

        return JSONResponse({
            "success": True,
            "otp": otp,
            "location_verified": location_verified,
            "distance_m": round(distance * 1000) if distance is not None else None,
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[PLACEMENT] Check-in submit error: {e}")
        traceback.print_exc()
        db.rollback()
        return JSONResponse({
            "error": f"Server error: {str(e)}",
        }, status_code=500, headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()


# DEPRECATED 2026-04-21: replaced by POST /verify/scan (QR-scan flow).
# Kept alive for in-flight WhatsApp links minted before the switchover.
# Remove once no verify links remain in the wild (check Placement rows where
# verify_token is set and employer_verified_at is null).
@router.get("/verify-context/{token}")
async def verify_context(token: str):
    """JSON endpoint for React verify page — returns placement context."""
    ctx = _load_verify_context(token)
    return JSONResponse(ctx, headers={"Access-Control-Allow-Origin": "*"})




def _find_placement_by_token(db, token):
    """Find placement and type by checkin token. Returns (placement, type, attendance_or_None)."""
    placement = db.query(Placement).filter_by(checkin_token=token).first()
    if placement:
        return placement, "interview", None

    placement = db.query(Placement).filter_by(first_day_checkin_token=token).first()
    if placement:
        return placement, "first_day", None

    attendance = db.query(AttendanceCheckin).filter_by(checkin_token=token).first()
    if attendance:
        placement = db.query(Placement).filter_by(id=attendance.placement_id).first()
        return placement, "attendance", attendance

    return None, None, None


def _bg_send_employer_verify(placement_id):
    """Background: send employer verify link after candidate checks in."""
    def _send():
        ndb = get_db()
        try:
            p = ndb.query(Placement).filter_by(id=placement_id).first()
            if p:
                send_employer_verify_link(p)
        except Exception as e:
            print(f"[PLACEMENT] Error sending verify link: {e}")
        finally:
            ndb.close()
    threading.Thread(target=_send, daemon=True).start()


# ── Employer Verification ──────────────────────────────────────────────────

# DEPRECATED 2026-04-21: replaced by in-app QR scan in the employer app.
@pages_router.get("/verify/{token}")
async def verify_page(token: str, request: Request):
    """Serve the employer verification HTML page."""
    ctx = _load_verify_context(token)
    ctx["request"] = request
    return templates.TemplateResponse("placement_verify.html", ctx)


def _load_verify_context(token: str) -> dict:
    db = get_db()
    try:
        placement = db.query(Placement).filter_by(verify_token=token).first()
        if not placement:
            return {"error": True, "message": "Invalid or expired link"}

        if placement.employer_verified_at:
            return {
                "error": False,
                "already_verified": True,
                "token": token,
                "company": placement.company,
            }

        return {
            "error": False,
            "already_verified": False,
            "token": token,
            "company": placement.company,
            "role": placement.role,
            "selfie": placement.checkin_selfie or "",
            "location_verified": placement.checkin_location_verified,
            "razorpay_key": RAZORPAY_KEY_ID or "",
        }
    finally:
        db.close()


class VerifySubmitRequest(BaseModel):
    otp: str


# DEPRECATED 2026-04-21: replaced by POST /verify/scan/confirm (QR-scan flow).
# Logic is preserved so in-flight OTP links keep working during the transition.
@router.post("/verify/{token}/submit")
async def verify_submit(token: str, req: VerifySubmitRequest):
    """Employer enters OTP to verify candidate arrival."""
    db = get_db()
    try:
        placement = db.query(Placement).filter_by(verify_token=token).first()
        if not placement:
            return JSONResponse({"error": "Invalid token"}, status_code=404)

        if placement.employer_verified_at:
            return JSONResponse({"error": "Already verified"}, status_code=400)

        if req.otp != placement.checkin_otp:
            return JSONResponse({"error": "Incorrect OTP"}, status_code=400)

        placement.employer_verified_at = time.time()
        placement.status = "employer_verified"
        placement.updated_at = time.time()
        db.commit()

        order_id = None
        amount = placement.payment_amount or 200000

        if razorpay_client:
            order_data = {
                "amount": amount,
                "currency": "INR",
                "receipt": f"placement_{placement.id}_{int(time.time())}",
                "notes": {
                    "placement_id": str(placement.id),
                    "employer_phone": placement.employer_phone,
                },
            }
            order = razorpay_client.order.create(data=order_data)
            order_id = order["id"]

            placement.razorpay_order_id = order_id
            placement.status = "payment_pending"
            placement.updated_at = time.time()
            db.commit()

            payment_record = PlacementPayment(
                placement_id=placement.id,
                employer_phone=placement.employer_phone,
                razorpay_order_id=order_id,
                amount=amount,
                status="created",
            )
            db.add(payment_record)
            db.commit()

        return JSONResponse({
            "verified": True,
            "order_id": order_id,
            "razorpay_key": RAZORPAY_KEY_ID or "",
            "amount": amount,
        }, headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()




# ── QR Scan Verification (replaces OTP flow) ───────────────────────────────

# Set of placement statuses that count as "active — worker is committed to this
# employer." Used by the scan flow to decide whether a walk-in hire is possible.
_ACTIVE_PLACEMENT_STATUSES = {
    "matched",
    "checked_in",
    "employer_verified",
    "payment_pending",
    "payment_complete",
    "joined",
    "active",
}

# Statuses where the placement is past the employer-verify step — scanning
# again is a no-op.
_POST_VERIFY_STATUSES = {
    "employer_verified",
    "payment_pending",
    "payment_complete",
    "joined",
    "active",
}


import hashlib as _hashlib

_CHECKIN_OTP_SALT = os.getenv("CHECKIN_OTP_SALT", "switch-checkin-2026")


def _normalize_phone(raw: str) -> str:
    clean = (raw or "").strip().lstrip("+").replace(" ", "").replace("-", "")
    if len(clean) == 10 and not clean.startswith("91"):
        clean = "91" + clean
    return clean


def _worker_fixed_otp(phone: str) -> str:
    h = _hashlib.sha256(f"{_CHECKIN_OTP_SALT}:{_normalize_phone(phone)}".encode()).hexdigest()
    return str(int(h[:4], 16) % 9000 + 1000)


@router.get("/worker-info/{phone}")
async def worker_info(phone: str):
    """Return basic worker info for employer QR scan — name, photo, role."""
    db = get_db()
    try:
        clean = _normalize_phone(phone)
        worker = db.query(User).filter_by(phone=clean).first()
        if not worker:
            return JSONResponse({"error": "Worker not found"}, status_code=404,
                                headers={"Access-Control-Allow-Origin": "*"})
        role = ""
        if worker.joining_details:
            try:
                jd = _json.loads(worker.joining_details) if isinstance(worker.joining_details, str) else (worker.joining_details or {})
                role = jd.get("role") or jd.get("roleEn") or ""
            except Exception:
                pass
        return JSONResponse({
            "name": worker.name or "",
            "photo": worker.photo_url or "",
            "role": role,
        }, headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()


@router.options("/worker-info/{phone}")
async def worker_info_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


@router.get("/worker-checkin-otp/{phone}")
async def worker_checkin_otp(phone: str):
    """Return fixed 4-digit OTP for the worker — deterministic, no expiry."""
    clean = _normalize_phone(phone)
    if not clean:
        return JSONResponse({"error": "Invalid phone"}, status_code=400,
                            headers={"Access-Control-Allow-Origin": "*"})
    return JSONResponse({"otp": _worker_fixed_otp(clean)},
                        headers={"Access-Control-Allow-Origin": "*"})


@router.options("/worker-checkin-otp/{phone}")
async def worker_checkin_otp_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


class OtpConfirmRequest(BaseModel):
    employer_phone: str
    worker_phone: str
    otp: str


@router.post("/verify/otp-confirm")
async def verify_otp_confirm(req: OtpConfirmRequest):
    """Employer submits worker OTP to confirm joining.

    Verifies the fixed OTP, marks the worker as checked-in, and creates or
    updates a Placement record so the UPI payment flow can proceed.
    """
    worker_phone = _normalize_phone(req.worker_phone)
    employer_phone = _normalize_phone(req.employer_phone)

    expected = _worker_fixed_otp(worker_phone)
    if req.otp.strip() != expected:
        return JSONResponse({"error": "OTP galat hai. Worker ke phone pe dekho."}, status_code=400,
                            headers={"Access-Control-Allow-Origin": "*"})

    db = get_db()
    try:
        worker = db.query(User).filter_by(phone=worker_phone).first()
        if not worker:
            return JSONResponse({"error": "Worker not found"}, status_code=404,
                                headers={"Access-Control-Allow-Origin": "*"})

        role, company = "", ""
        if worker.joining_details:
            try:
                jd = _json.loads(worker.joining_details) if isinstance(worker.joining_details, str) else (worker.joining_details or {})
                role = jd.get("role") or jd.get("roleEn") or ""
                company = jd.get("company") or ""
            except Exception:
                pass

        # Mark worker as checked in
        worker.checked_in = True
        worker.updated_at = time.time()

        # Find or create a placement record
        placement = (
            db.query(Placement)
            .filter(
                Placement.user_id == worker_phone,
                Placement.status.in_(_ACTIVE_PLACEMENT_STATUSES),
            )
            .order_by(Placement.created_at.desc())
            .first()
        )
        if not placement:
            placement = Placement(
                user_id=worker_phone,
                employer_phone=employer_phone,
                role=role,
                company=company,
                status="employer_verified",
                employer_verified_at=time.time(),
                updated_at=time.time(),
            )
            db.add(placement)
        else:
            placement.employer_phone = employer_phone
            placement.employer_verified_at = time.time()
            placement.status = "employer_verified"
            placement.updated_at = time.time()

        db.commit()
        db.refresh(placement)

        return JSONResponse({
            "verified": True,
            "placement_id": placement.id,
            "worker_name": worker.name or "",
            "role": role,
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500,
                            headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()


@router.options("/verify/otp-confirm")
async def verify_otp_confirm_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


class VerifyScanRequest(BaseModel):
    employer_phone: str
    worker_phone: str


@router.post("/verify/scan")
async def verify_scan(req: VerifyScanRequest):
    """Employer scans worker QR.

    Decision tree (happy path only — walk-in hire is a future extension):
      * worker not found                                → 404
      * active placement with THIS employer, pending   → {mode:"confirm", ...}
      * active placement already past employer-verify  → {mode:"already_done"}
      * active placement with DIFFERENT employer       → 403 not-your-worker
      * no active placement anywhere                   → {mode:"walk_in_pending"}
        (walk-in hire UI deferred; see project memory `walkin_hire_flow`)
    """
    employer_phone = _normalize_phone(req.employer_phone)
    if not employer_phone:
        return JSONResponse({"error": "employer_phone required"}, status_code=400)

    worker_phone = _normalize_phone(req.worker_phone)
    if not worker_phone:
        return JSONResponse({"error": "worker_phone required"}, status_code=400)

    db = get_db()
    try:
        worker = db.query(User).filter_by(phone=worker_phone).first()
        if not worker:
            return JSONResponse(
                {"error": "Worker not found"}, status_code=404,
            )

        active = (
            db.query(Placement)
            .filter(
                Placement.user_id == worker_phone,
                Placement.status.in_(_ACTIVE_PLACEMENT_STATUSES),
            )
            .order_by(Placement.created_at.desc())
            .first()
        )

        if active and _normalize_phone(active.employer_phone) != employer_phone:
            return JSONResponse(
                {
                    "error": "not_your_worker",
                    "message": "This worker is placed with another employer — you cannot confirm this placement.",
                },
                status_code=403,
            )

        if active and active.status in _POST_VERIFY_STATUSES:
            return JSONResponse({
                "mode": "already_done",
                "placement_id": active.id,
                "status": active.status,
            })

        if active:
            photo = worker.photo_url or active.checkin_selfie or ""
            return JSONResponse({
                "mode": "confirm",
                "placement_id": active.id,
                "name": worker.name or "",
                "photo": photo,
                "role": active.role or "",
                "company": active.company or "",
            })

        # No active placement anywhere. Walk-in hire flow lives here — not yet
        # implemented; the client shows a stub "not yet supported" message.
        return JSONResponse({
            "mode": "walk_in_pending",
            "name": worker.name or "",
            "photo": worker.photo_url or "",
        })
    finally:
        db.close()


class VerifyScanConfirmRequest(BaseModel):
    employer_phone: str
    placement_id: int


@router.post("/verify/scan/confirm")
async def verify_scan_confirm(req: VerifyScanConfirmRequest):
    """Employer has confirmed the photo matches. Flip placement to
    employer_verified and create a Razorpay order for the placement fee.
    Ownership is re-checked server-side.
    """
    employer_phone = _normalize_phone(req.employer_phone)
    if not employer_phone:
        return JSONResponse({"error": "employer_phone required"}, status_code=400)

    db = get_db()
    try:
        placement = db.query(Placement).filter_by(id=req.placement_id).first()
        if not placement:
            return JSONResponse({"error": "Placement not found"}, status_code=404)

        if _normalize_phone(placement.employer_phone) != employer_phone:
            return JSONResponse(
                {
                    "error": "not_your_worker",
                    "message": "This placement belongs to another employer.",
                },
                status_code=403,
            )

        if placement.status in _POST_VERIFY_STATUSES:
            return JSONResponse(
                {"error": "already_verified", "status": placement.status},
                status_code=400,
            )

        placement.employer_verified_at = time.time()
        placement.status = "employer_verified"
        placement.updated_at = time.time()
        db.commit()

        order_id = None
        amount = placement.payment_amount or 200000

        if razorpay_client:
            order = razorpay_client.order.create(data={
                "amount": amount,
                "currency": "INR",
                "receipt": f"placement_{placement.id}_{int(time.time())}",
                "notes": {
                    "placement_id": str(placement.id),
                    "employer_phone": placement.employer_phone,
                },
            })
            order_id = order["id"]

            placement.razorpay_order_id = order_id
            placement.status = "payment_pending"
            placement.updated_at = time.time()

            db.add(PlacementPayment(
                placement_id=placement.id,
                employer_phone=placement.employer_phone,
                razorpay_order_id=order_id,
                amount=amount,
                status="created",
            ))
            db.commit()

        return JSONResponse({
            "verified": True,
            "placement_id": placement.id,
            "order_id": order_id,
            "razorpay_key": RAZORPAY_KEY_ID or "",
            "amount": amount,
        })
    finally:
        db.close()


# ── Payment Verification ──────────────────────────────────────────────────

class PaymentVerifyRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


@router.post("/placement-payment/verify")
async def placement_payment_verify(req: PaymentVerifyRequest):
    """Verify Razorpay payment signature and complete placement."""
    if not razorpay_client:
        return JSONResponse({"error": "Payment not configured"}, status_code=500)

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": req.order_id,
            "razorpay_payment_id": req.payment_id,
            "razorpay_signature": req.signature,
        })
    except Exception as e:
        print(f"[PLACEMENT] Payment verification failed: {e}")
        return JSONResponse({"error": "Payment verification failed"}, status_code=400)

    db = get_db()
    try:
        payment = db.query(PlacementPayment).filter_by(razorpay_order_id=req.order_id).first()
        if payment:
            payment.razorpay_payment_id = req.payment_id
            payment.status = "paid"

        placement = db.query(Placement).filter_by(razorpay_order_id=req.order_id).first()
        if placement:
            placement.razorpay_payment_id = req.payment_id
            placement.payment_status = "paid"
            placement.payment_at = time.time()
            placement.status = "payment_complete"
            placement.first_day_checkin_token = uuid.uuid4().hex
            placement.updated_at = time.time()
            db.commit()

            _bg_send_joining_details(placement.id)

        return JSONResponse({"success": True}, headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()




def _bg_send_joining_details(placement_id):
    """Background: send joining details to candidate after payment."""
    def _send():
        ndb = get_db()
        try:
            p = ndb.query(Placement).filter_by(id=placement_id).first()
            if p:
                send_joining_details(p)
        except Exception as e:
            print(f"[PLACEMENT] Error sending joining details: {e}")
        finally:
            ndb.close()
    threading.Thread(target=_send, daemon=True).start()


# ── Daily Attendance Cron ──────────────────────────────────────────────────

@router.post("/placement/cron/daily-attendance")
async def daily_attendance_cron(request: Request):
    """Cron endpoint: create daily attendance records and send check-in links.

    Protected by admin API key in query param or header.
    """
    api_key = request.query_params.get("key") or request.headers.get("x-api-key", "")
    if api_key != ADMIN_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    sent_count = 0

    db = get_db()
    try:
        active_placements = db.query(Placement).filter(
            Placement.status.in_(["active", "joined"]),
            Placement.attendance_day_count < 30,
        ).all()

        for placement in active_placements:
            existing = db.query(AttendanceCheckin).filter_by(
                placement_id=placement.id, date=today
            ).first()
            if existing:
                continue

            day_number = placement.attendance_day_count + 1
            token = uuid.uuid4().hex

            checkin = AttendanceCheckin(
                placement_id=placement.id,
                user_id=placement.user_id,
                day_number=day_number,
                date=today,
                checkin_token=token,
                status="pending",
            )
            db.add(checkin)

            placement.attendance_day_count = day_number
            if placement.status == "joined":
                placement.status = "active"
            placement.updated_at = time.time()

            db.commit()

            try:
                send_daily_attendance_link(placement, day_number, token)
                sent_count += 1
            except Exception as e:
                print(f"[CRON] Error sending day {day_number} link for placement #{placement.id}: {e}")

            if day_number >= 30:
                placement.status = "completed"
                placement.updated_at = time.time()
                db.commit()

        return JSONResponse({
            "success": True,
            "date": today,
            "placements_processed": len(active_placements),
            "links_sent": sent_count,
        })
    finally:
        db.close()


# ── Worker ID Card verification ───────────────────────────────────────────────

@router.get("/worker-card/{phone}/{job_key}")
async def worker_card_verify(phone: str, job_key: str):
    """Public endpoint: employer scans QR on worker ID card.
    Returns worker details + placement status without exposing sensitive data.
    """
    db = get_db()
    try:
        clean_phone = phone.strip().lstrip("+").replace(" ", "")
        if not clean_phone.startswith("91") and len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        user = db.query(User).filter_by(phone=clean_phone).first()
        if not user:
            return JSONResponse(
                {"error": True, "message": "Worker not found"},
                status_code=404,
                headers={"Access-Control-Allow-Origin": "*"},
            )

        placement = (
            db.query(Placement)
            .filter_by(user_id=clean_phone, job_id=job_key)
            .order_by(Placement.created_at.desc())
            .first()
        )

        if not placement:
            placement = (
                db.query(Placement)
                .filter(Placement.user_id == clean_phone)
                .order_by(Placement.created_at.desc())
                .first()
            )

        import json as _json
        joining_details = {}
        if user.joining_details:
            try:
                joining_details = _json.loads(user.joining_details) if isinstance(user.joining_details, str) else (user.joining_details or {})
            except Exception:
                joining_details = {}

        joining_date = (
            joining_details.get("joiningDate")
            or (placement.joining_date if placement else None)
            or user.joining_date
            or ""
        )
        role = (
            joining_details.get("role")
            or (placement.role if placement else "")
            or ""
        )
        company = (
            joining_details.get("company")
            or (placement.company if placement else "")
            or ""
        )
        address = joining_details.get("address") or ""
        status = (placement.status if placement else "confirmed")

        return JSONResponse({
            "error": False,
            "name": user.name or "",
            "photo": user.photo_url or (placement.checkin_selfie if placement else None) or "",
            "role": role,
            "company": company,
            "joining_date": joining_date,
            "location": address or user.location or "Delhi NCR",
            "status": status,
            "phone_last4": clean_phone[-4:],
        }, headers={"Access-Control-Allow-Origin": "*"})
    finally:
        db.close()


@router.options("/worker-card/{phone}/{job_key}")
async def worker_card_verify_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


# ── KYC agent pool ────────────────────────────────────────────────────────────

KYC_AGENTS = [
    {"id": "priya",  "name": "Priya",  "gender": "female", "voice_id": "EXAVITQu4vr4xnSDxMaL"},
    {"id": "neha",   "name": "Neha",   "gender": "female", "voice_id": "Xb7hH8MSUJpSbSDYk0k2"},
    {"id": "kavya",  "name": "Kavya",  "gender": "female", "voice_id": "XB0fDUnXU5powFXDhCwa"},
    {"id": "arjun",  "name": "Arjun",  "gender": "male",   "voice_id": "onwK4e9ZLuTAKqWW03F9"},
    {"id": "rahul",  "name": "Rahul",  "gender": "male",   "voice_id": "N2lVS1w4EtoT3dr4eOWO"},
    {"id": "vikram", "name": "Vikram", "gender": "male",   "voice_id": "IKne3meq5aSn9XLyUdCD"},
]


# ── Video KYC session (ElevenLabs tokens) ────────────────────────────────────

@router.get("/kyc-session")
async def get_kyc_session(user_id: str = "", job_company: str = "", job_address: str = "", job_role: str = ""):
    api_key  = os.getenv("ELEVENLABS_API_KEY", "")
    agent_id = os.getenv("ELEVENLABS_KYC_AGENT_ID", "agent_2701kpppe4p7e29abz1hw0pvn3ej")
    if not api_key:
        return JSONResponse(
            {"error": "ELEVENLABS_API_KEY not configured"},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    def _gather_context_and_fetch_tokens():
        is_first = True
        candidate_name = ""
        known_location = ""
        known_experience = ""
        if user_id:
            db = get_db()
            try:
                prior = db.query(JobApplication).filter(
                    JobApplication.user_id == user_id,
                    JobApplication.kyc_verified_at.isnot(None),
                ).first()
                is_first = prior is None

                user = db.query(User).filter_by(phone=user_id).first()
                if user:
                    candidate_name = user.name or ""
                    known_location = user.location or ""
                    known_experience = user.experience or ""
            finally:
                db.close()

        headers = {"xi-api-key": api_key}
        webrtc = _requests.get(
            f"https://api.elevenlabs.io/v1/convai/conversation/token?agent_id={agent_id}",
            headers=headers, timeout=8,
        )
        signed = _requests.get(
            f"https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id={agent_id}",
            headers=headers, timeout=8,
        )
        return (
            is_first, candidate_name, known_location, known_experience,
            webrtc.status_code, webrtc.json(), signed.status_code, signed.json(),
        )

    try:
        (is_first, cand_name, known_loc, known_exp,
         wrtc_status, wrtc_data, signed_status, signed_data) = await asyncio.to_thread(_gather_context_and_fetch_tokens)
        conversation_token = wrtc_data.get("token", "") if wrtc_status == 200 else ""
        signed_url = signed_data.get("signed_url", "") if signed_status == 200 else ""
        if not conversation_token and not signed_url:
            return JSONResponse(
                {"error": f"ElevenLabs token endpoints returned {wrtc_status}/{signed_status}"},
                status_code=502,
                headers={"Access-Control-Allow-Origin": "*"},
            )
        agent = random.choice(KYC_AGENTS)
        dynamic_variables = {
            "agent_name": agent["name"],
            "agent_gender": agent["gender"],
            "candidate_name": cand_name or "dost",
            "job_role": job_role or "",
            "job_company": job_company or "",
            "is_first_kyc": "true" if is_first else "false",
            "known_location": known_loc or "",
            "known_experience": known_exp or "",
        }
        return JSONResponse(
            {
                "conversation_token": conversation_token,
                "signed_url": signed_url,
                "agent_id": agent_id,
                "voice_id": agent["voice_id"],
                "agent_name": agent["name"],
                "agent_id_pool": agent["id"],
                "agent_gender": agent["gender"],
                "is_first_kyc": is_first,
                "dynamic_variables": dynamic_variables,
            },
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )


@router.options("/kyc-session")
async def kyc_session_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


# ── Video KYC completion (persist + notify employer) ──────────────────────────

class KYCCompleteRequest(BaseModel):
    user_id: str
    job_id: str = ""
    conversation_id: str = ""
    photo_base64: str = ""
    answers: dict = {}
    structured: dict = {}
    transcript: list = []
    agent_name: str = ""
    is_first_kyc: bool = True


def _build_kyc_summary(structured: dict, transcript: list, job_role: str = "") -> str:
    """Call Claude Haiku to produce a 2-3 sentence employer-facing summary of the KYC."""
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    name = structured.get("full_name") or structured.get("name") or "the candidate"
    exp  = structured.get("total_experience_years") or structured.get("experience") or "unknown"
    loc  = structured.get("current_location") or structured.get("location") or ""
    avail = structured.get("availability") or ""
    edu  = structured.get("education") or ""
    lang = ", ".join(structured.get("languages_spoken") or []) or ""
    vehicle = "has a two-wheeler" if structured.get("has_vehicle") else "no vehicle"
    last_role = structured.get("last_role") or ""
    last_co   = structured.get("last_employer") or ""
    expected  = structured.get("expected_salary") or ""

    context_lines = [
        f"Name: {name}",
        f"Experience: {exp} years" if exp else "",
        f"Location: {loc}" if loc else "",
        f"Education: {edu}" if edu else "",
        f"Last role: {last_role} at {last_co}" if last_role else "",
        f"Expected salary: {expected}" if expected else "",
        f"Languages: {lang}" if lang else "",
        f"Vehicle: {vehicle}",
        f"Availability: {avail}" if avail else "",
        f"Applying for: {job_role}" if job_role else "",
    ]
    context_str = "\n".join(l for l in context_lines if l)

    prompt = (
        f"You are summarizing a Video KYC interview for an employer to quickly evaluate a candidate.\n"
        f"Write 2-3 concise English sentences covering: who they are, relevant experience, and key highlights.\n"
        f"Be factual and neutral. No filler phrases.\n\n"
        f"Candidate details:\n{context_str}"
    )
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[KYC_SUMMARY] Claude error: {e}")
        return ""


def _persist_and_notify_kyc(payload: KYCCompleteRequest) -> dict:
    """Write KYC fields onto the matching application row and ping employer."""
    db = get_db()
    try:
        query = db.query(JobApplication).filter_by(user_id=payload.user_id)
        if payload.job_id:
            query = query.filter_by(job_id=payload.job_id)
        app = query.order_by(JobApplication.created_at.desc()).first()

        if not app:
            return {"status": "no_application", "notified": False}

        app.kyc_verified_at = time.time()
        app.kyc_conversation_id = payload.conversation_id or ""
        app.kyc_answers = _json.dumps(payload.answers or {})
        app.kyc_structured = _json.dumps(payload.structured or {})
        app.kyc_transcript = _json.dumps(payload.transcript or [])
        app.kyc_agent_name = payload.agent_name or ""
        app.kyc_is_first = payload.is_first_kyc
        if payload.photo_base64:
            if payload.photo_base64.startswith("data:"):
                app.kyc_photo_url = payload.photo_base64
            else:
                app.kyc_photo_url = f"data:image/jpeg;base64,{payload.photo_base64}"

        job = db.query(Job).filter_by(job_id=app.job_id).first()
        user = db.query(User).filter_by(phone=payload.user_id).first()

        summary = _build_kyc_summary(
            payload.structured or {},
            payload.transcript or [],
            job.title if job else "",
        )
        if summary:
            app.kyc_summary = summary

        db.commit()
        app_id = app.id

        employer_phone = (job.phone or "").strip() if job else ""
        trigger_post_card_flow(payload.user_id, payload.job_id or "")

        if employer_phone:
            joining_date = user.joining_date if user else ""
            try:
                notify_employer_kyc_complete(
                    employer_phone=employer_phone,
                    worker_name=user.name if user else "",
                    job_title=job.title if job else "",
                    company=job.company if job else "",
                    joining_date=joining_date,
                    application_id=app_id,
                )
                return {"status": "ok", "notified": True, "application_id": app_id}
            except Exception as notify_err:
                print(f"[KYC_COMPLETE] notify error: {notify_err}")
                return {"status": "ok", "notified": False, "application_id": app_id}

        return {"status": "ok", "notified": False, "application_id": app_id}
    finally:
        db.close()


@router.post("/kyc/complete")
async def kyc_complete(payload: KYCCompleteRequest):
    """Mark a job application as KYC-verified and ping the employer on WhatsApp.

    Idempotent: re-posting for the same (user_id, job_id) overwrites the KYC fields.
    If no matching JobApplication exists (e.g. worker completed KYC without applying),
    returns status=no_application; the frontend should still continue the flow.
    """
    if not payload.user_id:
        return JSONResponse(
            {"error": "user_id required"},
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )
    try:
        result = await asyncio.to_thread(_persist_and_notify_kyc, payload)
        return JSONResponse(result, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )


# ── Video KYC video upload ────────────────────────────────────────────────────

@router.post("/kyc/upload-video")
async def kyc_upload_video(request: Request):
    """Accept a webm video blob and store it, returning the URL."""
    form = await request.form()
    user_id = form.get("user_id", "")
    job_id  = form.get("job_id", "")
    video_file = form.get("video")

    if not user_id or not video_file:
        return JSONResponse(
            {"error": "user_id and video required"},
            status_code=400,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    try:
        video_bytes = await video_file.read()
        ext = "webm"
        filename = f"kyc_{user_id}_{int(time.time())}.{ext}"

        upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads", "kyc_videos")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(video_bytes)

        video_url = f"https://api.relayy.world/uploads/kyc_videos/{filename}"

        if user_id and job_id:
            def _update_video_url():
                db = get_db()
                try:
                    query = db.query(JobApplication).filter_by(user_id=user_id)
                    if job_id:
                        query = query.filter_by(job_id=job_id)
                    app = query.order_by(JobApplication.created_at.desc()).first()
                    if app:
                        app.kyc_video_url = video_url
                        db.commit()
                finally:
                    db.close()
            threading.Thread(target=_update_video_url, daemon=True).start()

        return JSONResponse(
            {"status": "ok", "video_url": video_url},
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {"error": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"},
        )


@router.options("/kyc/upload-video")
async def kyc_upload_video_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


@router.options("/kyc/complete")
async def kyc_complete_options():
    return JSONResponse({}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })


# ── Joining reminder cron ──────────────────────────────────────────────────────

NIGHT_BEFORE_SMS = """🌙 कल joining है!

नमस्ते {name}, कल आपकी joining है:
🏢 {company}
💼 {role}
📅 {slot}
📍 {address}

ज़रूरी सामान तैयार रखें:
• आधार कार्ड (original + copy)
• पासपोर्ट साइज़ फ़ोटो (2)
• Switch देगा ₹200 travel

App खोलो: https://app.switchlocally.com
— Switch Team"""

MORNING_OF_SMS = """🌅 आज आपकी joining है!

{name} जी, आज joining का दिन है!
🏢 {company} · {role}
📅 {slot}

👉 अभी निकलो — https://app.switchlocally.com

— Switch Team"""

REFERRAL_SMS = """🎉 {name} जी, बधाई हो!

आपकी {company} में joining हो गई।
अब दोस्तों को भी दिलाओ job — हर referral पर मिलेंगे ₹200!

आपका referral link:
https://app.switchlocally.com/r/{referral_code}

— Switch Team"""


def _send_reminder_sms(phone: str, body: str):
    def _do():
        try:
            from twilio.rest import Client
            sid   = os.getenv("TWILIO_ACCOUNT_SID")
            token = os.getenv("TWILIO_AUTH_TOKEN")
            frm   = os.getenv("TWILIO_PHONE_NUMBER", "+15625260001")
            if not sid or not token:
                return
            clean = phone.strip().lstrip("+").replace(" ", "").replace("-", "")
            if not clean.startswith("91"):
                clean = "91" + clean
            Client(sid, token).messages.create(body=body, from_=frm, to=f"+{clean}")
            print(f"[REMINDER] SMS sent to {clean}")
        except Exception as e:
            print(f"[REMINDER] SMS error to {phone}: {e}")
    threading.Thread(target=_do, daemon=True).start()


def _run_joining_reminders() -> dict:
    """Core logic for joining reminder SMS. Returns stats dict. Safe to call from any thread."""
    import json as _json
    db = get_db()
    night_sent = morning_sent = referral_sent = 0
    try:
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        today_iso    = now_ist.strftime("%Y-%m-%d")
        tomorrow_iso = (now_ist + timedelta(days=1)).strftime("%Y-%m-%d")

        placed_users = db.query(User).filter(
            User.active_job_key.isnot(None),
            User.checked_in == False,
        ).all()

        for u in placed_users:
            if not u.phone:
                continue
            details = {}
            if u.joining_details:
                try:
                    details = _json.loads(u.joining_details) if isinstance(u.joining_details, str) else (u.joining_details or {})
                except Exception:
                    details = {}

            abs_date = details.get("joiningAbsoluteDate") or ""
            name     = (u.name or "भाई").split()[0]
            company  = details.get("company") or u.active_job_key or "आपकी company"
            role     = details.get("role") or ""
            slot     = details.get("joiningDate") or u.joining_date or ""
            address  = details.get("address") or "Delhi NCR"

            if abs_date == tomorrow_iso:
                body = NIGHT_BEFORE_SMS.format(name=name, company=company, role=role, slot=slot, address=address)
                _send_reminder_sms(u.phone, body)
                night_sent += 1
            elif abs_date == today_iso:
                body = MORNING_OF_SMS.format(name=name, company=company, role=role, slot=slot)
                _send_reminder_sms(u.phone, body)
                morning_sent += 1

        three_days_ago = (now_ist - timedelta(days=3)).timestamp()
        placed_old = db.query(User).filter(
            User.active_job_key.isnot(None),
            User.updated_at <= three_days_ago,
            User.total_referrals == 0,
        ).all()
        for u in placed_old:
            if not u.phone:
                continue
            details = {}
            if u.joining_details:
                try:
                    details = _json.loads(u.joining_details) if isinstance(u.joining_details, str) else (u.joining_details or {})
                except Exception:
                    details = {}
            name     = (u.name or "भाई").split()[0]
            company  = details.get("company") or u.active_job_key or "आपकी company"
            ref_code = u.referral_code or f"SW{u.phone[-6:]}"
            body = REFERRAL_SMS.format(name=name, company=company, referral_code=ref_code)
            _send_reminder_sms(u.phone, body)
            referral_sent += 1

        print(f"[REMINDERS] night={night_sent} morning={morning_sent} referral={referral_sent} date={today_iso}")
        return {"success": True, "date_ist": today_iso, "night_before_sent": night_sent, "morning_of_sent": morning_sent, "referral_nudge_sent": referral_sent}
    finally:
        db.close()


@router.post("/placement/cron/joining-reminders")
async def joining_reminders_cron(request: Request):
    """Cron: send night-before and morning-of joining reminders.
    Call at 8 PM IST for night-before, 7 AM IST for morning-of.
    """
    api_key = request.query_params.get("key") or request.headers.get("x-api-key", "")
    if api_key != ADMIN_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    result = _run_joining_reminders()
    return JSONResponse(result)


def _check_api_key(request: Request) -> bool:
    key = request.query_params.get("key") or request.headers.get("x-api-key", "")
    return key == ADMIN_API_KEY


# ── Post-card automated pipeline cron endpoints ───────────────────────────────

@router.post("/placement/cron/evening-confirm")
async def cron_evening_confirm(request: Request):
    """8 PM IST: send evening confirmation to tomorrow's joiners."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_evening_confirmation_cron)
    return JSONResponse(result)


@router.post("/placement/cron/evening-followup")
async def cron_evening_followup(request: Request):
    """10 PM IST: follow-up for non-responders; 10:30 PM mark AT_RISK."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_evening_followup_cron)
    return JSONResponse(result)


@router.post("/placement/cron/morning-nudge")
async def cron_morning_nudge(request: Request):
    """6:30 AM IST: wake-up message for today's joiners."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_morning_nudge_cron)
    return JSONResponse(result)


@router.post("/placement/cron/enroute-check")
async def cron_enroute_check(request: Request):
    """8:30 AM IST: en-route check 30 min before joining_time."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_enroute_check_cron)
    return JSONResponse(result)


@router.post("/placement/cron/enroute-timeout")
async def cron_enroute_timeout(request: Request):
    """8:45 AM IST: mark LIKELY_NO_SHOW for workers who ignored en-route check."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_enroute_timeout_cron)
    return JSONResponse(result)


@router.post("/placement/cron/retention-day1")
async def cron_retention_day1(request: Request):
    """8 PM IST on joining day: how was the first day?"""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_retention_day1_cron)
    return JSONResponse(result)


@router.post("/placement/cron/retention-day3")
async def cron_retention_day3(request: Request):
    """Day 3 check-in message."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_retention_day3_cron)
    return JSONResponse(result)


@router.post("/placement/cron/retention-day7")
async def cron_retention_day7(request: Request):
    """Day 7 celebration + referral nudge."""
    if not _check_api_key(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    result = await asyncio.to_thread(run_retention_day7_cron)
    return JSONResponse(result)
