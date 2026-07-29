"""
API routes for Switch app (job swiping app).
Handles Switch-specific user profiles, job applications, and data storage.
All data stored in PostgreSQL.
"""

import json
import base64
import math
import os
import random
import threading
import time
import traceback
import uuid

import asyncio

import anthropic
import httpx
import requests as _otp_requests
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from models.sql_models import User, Job, JobApplication, Candidate, Referral, SwipeEvent, DeliveryDocument, DeliveryApplication, OtpVerification, Session, Notification, EmployerProfile, SmsClick
from services.employer_match_service import notify_candidate_matched, notify_candidate_interview, send_employer_whatsapp, send_blast_to_worker, notify_employer_blast_accepted, send_blast_confirmation_to_worker
from services.switch_post_card_service import trigger_post_card_from_app_hire
from services.notification_service import Content, notify_user
from utils.hearus_auth import caller_phone
from services.switch_edge_cases import edge_case_handler
from services.switch_matching_service import switch_matching_service
from services.vobiz_service import vobiz_service
from utils.db import fs
from utils.geocode import geocode_location
from utils.postgres import get_db, parse_json_col

router = APIRouter(prefix="/api/switch", tags=["Switch App"])

PLACEMENT_SMS_TMPL = """🎉 बधाई हो {first_name}!

आपकी {role} नौकरी पक्की हो गई।
Joining: {date}

App खोलो — सारी details और confirm button वहाँ है:
https://app.switchlocally.com

— Switch Team"""


def _send_placement_sms_bg(phone: str, name: str, role: str, date: str, joining_details: dict):
    def _send():
        try:
            from twilio.rest import Client as TwilioClient
            sid = os.getenv("TWILIO_ACCOUNT_SID")
            token = os.getenv("TWILIO_AUTH_TOKEN")
            from_number = os.getenv("TWILIO_PHONE_NUMBER", "+15625260001")
            if not sid or not token or not phone:
                return
            clean = phone.strip().lstrip("+").replace(" ", "").replace("-", "")
            if not clean.startswith("91"):
                clean = "91" + clean
            first_name = name.split()[0] if name else "भाई"
            role_label = joining_details.get("role") or role.replace("-", " ").title()
            joining_date = joining_details.get("joiningDate") or date
            body = PLACEMENT_SMS_TMPL.format(first_name=first_name, role=role_label, date=joining_date)
            TwilioClient(sid, token).messages.create(body=body, from_=from_number, to=f"+{clean}")
            print(f"[SWITCH] Placement SMS sent to {clean}")
        except Exception as e:
            print(f"[SWITCH] Placement SMS error: {e}")
    threading.Thread(target=_send, daemon=True).start()


class SwitchProfileUpdate(BaseModel):
    """Request model for Switch profile updates."""
    name: Optional[str] = None
    phone: Optional[str] = None
    photoURL: Optional[str] = None
    location: Optional[str] = None
    experience: Optional[str] = None
    preferredRoles: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    education: Optional[str] = None
    referralCode: Optional[str] = None
    isAvailable: Optional[bool] = None
    gender: Optional[str] = None
    dateOfBirth: Optional[str] = None
    expectedSalaryMin: Optional[int] = None
    expectedSalaryMax: Optional[int] = None
    previousCompany: Optional[str] = None
    previousRole: Optional[str] = None
    workDuration: Optional[str] = None
    activeJobKey: Optional[str] = None
    joiningDate: Optional[str] = None
    joiningAbsoluteDate: Optional[str] = None
    joiningDetails: Optional[dict] = None
    checkedIn: Optional[bool] = None
    trainingProgress: Optional[dict] = None
    # Onboarding fields
    lat: Optional[float] = None
    lng: Optional[float] = None
    currentSalary: Optional[int] = None
    village: Optional[str] = None
    switchPriority: Optional[str] = None
    referredBy: Optional[str] = None
    acquisitionSource: Optional[str] = None


class SwitchJobApplication(BaseModel):
    """Request model for job application. Identity derived from bearer token; `user_id` accepted for back-compat but ignored."""
    user_id: Optional[str] = None  # DEPRECATED: candidate for deletion — read from token instead
    job_id: str
    company: str
    role: str
    salary: str
    location: str
    logo: Optional[str] = None
    appliedDate: Optional[str] = None
    status: Optional[str] = "pending"
    callScheduled: Optional[bool] = False
    callTime: Optional[str] = None


class SwipeApplyRequest(BaseModel):
    """Request model for swipe-apply. Identity derived from bearer token."""
    user_id: Optional[str] = None  # DEPRECATED: candidate for deletion
    job_id: str


class SwipeEventRequest(BaseModel):
    user_id: Optional[str] = None  # DEPRECATED: candidate for deletion
    job_id: str
    direction: str  # "left" or "right"


@router.get("/profile")
async def get_switch_profile(request: Request):
    """Get Switch user profile for the caller (identity from bearer token)."""
    user_id = caller_phone(request)
    try:
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()

            if not user:
                return JSONResponse({
                    "status": "success",
                    "profile": {
                        "phone": user_id,
                        "name": "",
                        "photoURL": None,
                        "location": "",
                        "experience": "",
                        "preferredRoles": [],
                        "languages": [],
                        "education": "",
                        "verified": False,
                        "joinedDate": "",
                        "totalApplied": 0,
                        "interviews": 0,
                        "hired": 0,
                        "profileComplete": 0,
                        "referralCode": "",
                    }
                }, headers={"Access-Control-Allow-Origin": "*"})

            # Calculate profile completeness
            fields = ['name', 'phone', 'location', 'experience', 'education', 'photo_url']
            filled_fields = sum(1 for f in fields if getattr(user, f, None))
            preferred_roles = parse_json_col(user.preferred_roles)
            languages = parse_json_col(user.languages)
            array_fields_filled = sum(1 for arr in [preferred_roles, languages] if arr)
            total_fields = len(fields) + 2
            profile_complete = round(((filled_fields + array_fields_filled) / total_fields) * 100) if total_fields > 0 else 0

            # Get stats from applications
            applications = db.query(JobApplication).filter_by(user_id=user_id).all()
            total_applied = len(applications)
            interviews = sum(1 for a in applications if a.status == "interview")
            hired = sum(1 for a in applications if a.status == "hired")

            # Get referrals
            referrals = db.query(Referral).filter_by(referrer_phone=user_id).all()
            referral_list = [
                {
                    "user_id": r.referee_user_id,
                    "name": r.referee_name,
                    "referred_at": r.referred_at,
                    "status": r.status,
                    "earnings": r.earnings,
                }
                for r in referrals
            ]

            response_data = {
                "status": "success",
                "profile": {
                    "phone": user.phone,
                    "name": user.name or "",
                    "photoURL": user.photo_url,
                    "location": user.location or "",
                    "experience": user.experience or "",
                    "preferredRoles": preferred_roles,
                    "languages": languages,
                    "education": user.education or "",
                    "verified": user.verified,
                    "joinedDate": user.joined_date or "",
                    "totalApplied": total_applied,
                    "interviews": interviews,
                    "hired": hired,
                    "profileComplete": profile_complete,
                    "referralCode": user.referral_code or "",
                    "isAvailable": user.is_available,
                    "referrals": referral_list,
                    "totalReferralEarnings": user.total_referral_earnings,
                    "totalReferrals": user.total_referrals,
                    "referredBy": user.referred_by,
                    "activeJobKey": user.active_job_key,
                    "joiningDate": user.joining_date,
                    "joiningDetails": parse_json_col(user.joining_details) if user.joining_details else None,
                    "checkedIn": user.checked_in or False,
                    "trainingProgress": parse_json_col(user.training_progress) if user.training_progress else {},
                    # Fields previously not returned — now included
                    "previousRole": user.previous_role or "",
                    "previousCompany": user.previous_company or "",
                    "workDuration": user.work_duration or "",
                    "gender": user.gender or "",
                    "dateOfBirth": user.date_of_birth or "",
                    "currentSalary": user.expected_salary_min,
                    "expectedSalaryMin": user.expected_salary_min,
                    "expectedSalaryMax": user.expected_salary_max,
                    "lat": user.lat,
                    "lng": user.lng,
                    "village": getattr(user, 'village', '') or "",
                    "switchPriority": getattr(user, 'switch_priority', '') or "",
                    "jobRole": getattr(user, 'job_role', '') or "",
                }
            }

            return JSONResponse(response_data, headers={"Access-Control-Allow-Origin": "*"})
        finally:
            db.close()

    except Exception as e:
        print(f"[SWITCH] Error getting profile: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting profile: {str(e)}")


@router.put("/profile")
async def update_switch_profile(http_request: Request, payload: SwitchProfileUpdate):
    """Update Switch user profile for the caller (identity from bearer token)."""
    user_id = caller_phone(http_request)
    try:
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()

            if not user:
                phone_number = payload.phone if payload.phone else user_id
                full_location = payload.location or ""
                if payload.village and payload.village.strip():
                    full_location = f"{full_location}, {payload.village.strip()}".strip(", ")
                user = User(
                    phone=user_id,
                    name=payload.name or "",
                    photo_url=payload.photoURL,
                    location=full_location,
                    experience=payload.experience or "",
                    preferred_roles=json.dumps(payload.preferredRoles or []),
                    languages=json.dumps(payload.languages or []),
                    education=payload.education or "",
                    referral_code=payload.referralCode or "",
                    verified=True,
                    joined_date=time.strftime("%b %Y"),
                    is_available=payload.isAvailable if payload.isAvailable is not None else True,
                    gender=payload.gender or "",
                    date_of_birth=payload.dateOfBirth or "",
                    expected_salary_min=payload.currentSalary or payload.expectedSalaryMin,
                    expected_salary_max=payload.expectedSalaryMax,
                    previous_company=payload.previousCompany or "",
                    previous_role=payload.previousRole or "",
                    work_duration=payload.workDuration or "",
                    lat=payload.lat,
                    lng=payload.lng,
                    village=payload.village or "",
                    switch_priority=payload.switchPriority or "",
                    referred_by=payload.referredBy or None,
                    acquisition_source=payload.acquisitionSource or "",
                    active_job_key=payload.activeJobKey,
                    joining_date=payload.joiningDate,
                    joining_details=json.dumps(payload.joiningDetails) if payload.joiningDetails else None,
                    checked_in=payload.checkedIn or False,
                    training_progress=json.dumps(payload.trainingProgress) if payload.trainingProgress else "{}",
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(user)

                if payload.referredBy:
                    referrer = db.query(User).filter_by(referral_code=payload.referredBy.upper().strip()).first()
                    if referrer and referrer.phone != user_id:
                        already = db.query(Referral).filter_by(referrer_phone=referrer.phone, referee_user_id=user_id).first()
                        if not already:
                            db.add(Referral(
                                referrer_phone=referrer.phone,
                                referee_user_id=user_id,
                                referee_name=payload.name or "",
                                referred_at=time.time(),
                                status="signed_up",
                                earnings=0,
                            ))
                            referrer.total_referrals = (referrer.total_referrals or 0) + 1
                            referrer.updated_at = time.time()
                            print(f"[SWITCH] Referral recorded: {payload.referredBy} → {user_id}")

                print(f"[SWITCH] Created new user: {user_id}")
            else:
                if payload.name is not None:
                    user.name = payload.name
                if payload.phone is not None:
                    pass  # phone is the PK, don't change it
                if payload.photoURL is not None:
                    user.photo_url = payload.photoURL
                if payload.location is not None:
                    user.location = payload.location
                if payload.experience is not None:
                    user.experience = payload.experience
                if payload.preferredRoles is not None:
                    user.preferred_roles = json.dumps(payload.preferredRoles)
                if payload.languages is not None:
                    user.languages = json.dumps(payload.languages)
                if payload.education is not None:
                    user.education = payload.education
                if payload.referralCode is not None:
                    user.referral_code = payload.referralCode
                if payload.isAvailable is not None:
                    user.is_available = payload.isAvailable
                if payload.gender is not None:
                    user.gender = payload.gender
                if payload.dateOfBirth is not None:
                    user.date_of_birth = payload.dateOfBirth
                if payload.expectedSalaryMin is not None:
                    user.expected_salary_min = payload.expectedSalaryMin
                if payload.expectedSalaryMax is not None:
                    user.expected_salary_max = payload.expectedSalaryMax
                if payload.previousCompany is not None:
                    user.previous_company = payload.previousCompany
                if payload.previousRole is not None:
                    user.previous_role = payload.previousRole
                if payload.workDuration is not None:
                    user.work_duration = payload.workDuration
                newly_placed = payload.activeJobKey and not user.active_job_key
                if payload.activeJobKey is not None:
                    user.active_job_key = payload.activeJobKey
                if payload.joiningDate is not None:
                    user.joining_date = payload.joiningDate
                if payload.joiningDetails is not None:
                    jd = payload.joiningDetails
                    if payload.joiningAbsoluteDate and "joiningAbsoluteDate" not in jd:
                        jd = {**jd, "joiningAbsoluteDate": payload.joiningAbsoluteDate}
                    user.joining_details = json.dumps(jd)
                if payload.checkedIn is not None:
                    user.checked_in = payload.checkedIn
                if payload.trainingProgress is not None:
                    user.training_progress = json.dumps(payload.trainingProgress)
                if payload.lat is not None:
                    user.lat = payload.lat
                if payload.lng is not None:
                    user.lng = payload.lng
                if payload.currentSalary is not None:
                    user.expected_salary_min = payload.currentSalary
                if payload.village is not None and payload.village.strip():
                    user.village = payload.village.strip()
                    # Also merge into location string if not already there
                    base_loc = user.location or ""
                    if payload.village.strip() not in base_loc:
                        user.location = f"{base_loc}, {payload.village.strip()}".strip(", ")
                if payload.switchPriority is not None:
                    user.switch_priority = payload.switchPriority
                if payload.acquisitionSource:
                    user.acquisition_source = payload.acquisitionSource
                if payload.referredBy and not user.referred_by:
                    user.referred_by = payload.referredBy
                    referrer = db.query(User).filter_by(referral_code=payload.referredBy.upper().strip()).first()
                    if referrer and referrer.phone != user_id:
                        already = db.query(Referral).filter_by(referrer_phone=referrer.phone, referee_user_id=user_id).first()
                        if not already:
                            db.add(Referral(
                                referrer_phone=referrer.phone,
                                referee_user_id=user_id,
                                referee_name=user.name or "",
                                referred_at=time.time(),
                                status="signed_up",
                                earnings=0,
                            ))
                            referrer.total_referrals = (referrer.total_referrals or 0) + 1
                            referrer.updated_at = time.time()
                            print(f"[SWITCH] Referral recorded (update path): {payload.referredBy} → {user_id}")
                user.updated_at = time.time()
                print(f"[SWITCH] Updated profile for: {user_id}")

                if newly_placed:
                    _send_placement_sms_bg(
                        phone=user.phone,
                        name=user.name or "",
                        role=payload.activeJobKey,
                        date=payload.joiningDate or "",
                        joining_details=payload.joiningDetails or {},
                    )
                    if payload.joiningDetails:
                        jd = payload.joiningDetails
                        if payload.joiningAbsoluteDate and "joiningAbsoluteDate" not in jd:
                            jd = {**jd, "joiningAbsoluteDate": payload.joiningAbsoluteDate}
                        trigger_post_card_from_app_hire(user_id, jd)

            db.commit()
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": "Profile updated successfully"
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error updating profile: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


@router.put("/users/training-progress")
async def update_training_progress(request: Request):
    """Persist training module progress for the calling user (identity from token)."""
    user_id = caller_phone(request)
    try:
        body = await request.json()
        training_progress = body.get("training_progress", {})
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if user:
                user.training_progress = json.dumps(training_progress)
                user.updated_at = time.time()
                db.commit()
        finally:
            db.close()
        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[SWITCH] Error updating training progress: {e}")
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500, headers={"Access-Control-Allow-Origin": "*"})


@router.post("/profile/status")
async def update_profile_status(request: Request):
    """Persist current user_status to Firestore for the calling user (identity from token)."""
    phone = caller_phone(request)
    try:
        body = await request.json()
        status_key = body.get("status", "")
        status_label = body.get("status_label", "")

        def _write():
            try:
                fs.collection("switch_users").document(phone).set(
                    {"user_status": {"key": status_key, "label": status_label}},
                    merge=True,
                )
            except Exception as e:
                print(f"[SWITCH] profile/status Firestore write error: {e}")
        threading.Thread(target=_write, daemon=True).start()
        return JSONResponse({"success": True}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[SWITCH] profile/status error: {e}")
        return JSONResponse({"success": False}, status_code=500, headers={"Access-Control-Allow-Origin": "*"})


@router.post("/upload-photo")
async def upload_switch_photo(request: Request, file: UploadFile = File(...)):
    """Upload profile photo for the calling user (identity from token)."""
    user_id = caller_phone(request)
    try:
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        file_content = await file.read()
        file_size = len(file_content)

        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 5MB")
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        base64_image = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{file.content_type};base64,{base64_image}"

        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if user:
                user.photo_url = data_url
                user.updated_at = time.time()
            else:
                user = User(
                    phone=user_id,
                    photo_url=data_url,
                    verified=True,
                    joined_date=time.strftime("%b %Y"),
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(user)
            db.commit()
            print(f"[SWITCH] Photo saved for user {user_id}")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": "Photo uploaded successfully",
            "photoURL": data_url
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error uploading photo: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error uploading photo: {str(e)}")


@router.post("/apply")
async def apply_to_job(http_request: Request, payload: SwitchJobApplication):
    """Record job application for the calling user (identity from bearer token)."""
    user_id = caller_phone(http_request)
    try:
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            existing = db.query(JobApplication).filter_by(
                user_id=user_id, job_id=payload.job_id
            ).first()
            if existing:
                app_dict = existing.to_dict()
                return JSONResponse({
                    "status": "success",
                    "message": "Already applied",
                    "application": app_dict
                }, headers={"Access-Control-Allow-Origin": "*"})

            app = JobApplication(
                user_id=user_id,
                job_id=payload.job_id,
                company=payload.company,
                role=payload.role,
                salary=payload.salary,
                location=payload.location,
                logo=payload.logo or "",
                applied_date=payload.appliedDate or time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                status=payload.status or "pending",
                call_scheduled=payload.callScheduled or False,
                call_time=payload.callTime,
                created_at=time.time(),
            )
            db.add(app)
            db.commit()
            app_id = app.id
            app_response = {
                "job_id": payload.job_id,
                "company": payload.company,
                "role": payload.role,
                "salary": payload.salary,
                "location": payload.location,
                "logo": payload.logo,
                "appliedDate": app.applied_date,
                "status": app.status,
                "callScheduled": app.call_scheduled,
                "callTime": app.call_time,
            }
            print(f"[SWITCH] Application recorded for {user_id}: {payload.company}")
        finally:
            db.close()

        _trigger_employer_call(payload.job_id, user_id)
        _trigger_employer_whatsapp(payload.job_id, user_id, app_id)

        return JSONResponse({
            "status": "success",
            "message": "Application recorded",
            "application": app_response
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error recording application: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error recording application: {str(e)}")


@router.post("/swipe")
async def record_swipe(payload: SwipeEventRequest, http_request: Request):
    """Record a swipe event (left or right) for analytics."""
    try:
        user_id = caller_phone(http_request)
        db = get_db()
        try:
            event = SwipeEvent(
                user_id=user_id,
                job_id=payload.job_id,
                direction=payload.direction,
                created_at=time.time(),
            )
            db.add(event)
            db.commit()
        finally:
            db.close()
        return JSONResponse({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[SWITCH] Error recording swipe: {e}")
        return JSONResponse({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


@router.get("/swipe-stats")
async def swipe_stats(minutes: int = 30):
    """Get swipe stats for the last N minutes."""
    try:
        db = get_db()
        try:
            cutoff = time.time() - (minutes * 60)
            events = db.query(SwipeEvent).filter(SwipeEvent.created_at >= cutoff).all()

            total = len(events)
            lefts = sum(1 for e in events if e.direction == "left")
            rights = sum(1 for e in events if e.direction == "right")

            user_stats = {}
            for e in events:
                if e.user_id not in user_stats:
                    user_stats[e.user_id] = {"left": 0, "right": 0}
                user_stats[e.user_id][e.direction] = user_stats[e.user_id].get(e.direction, 0) + 1

            return JSONResponse({
                "minutes": minutes,
                "total_swipes": total,
                "left_swipes": lefts,
                "right_swipes": rights,
                "unique_users": len(user_stats),
                "per_user": user_stats,
            }, headers={"Access-Control-Allow-Origin": "*"})
        finally:
            db.close()
    except Exception as e:
        print(f"[SWITCH] Error fetching swipe stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


DAILY_SWIPE_LIMIT = 5
REFERRAL_BONUS_SWIPES = 10


def _get_swipes_remaining(db, user_id: str) -> dict:
    """Calculate remaining right swipes for a user today.
    Counts actual job_applications (not swipe_events) to prevent race conditions.
    """
    day_start = time.time() - (time.time() % 86400)  # UTC midnight
    today_applied = db.query(JobApplication).filter(
        JobApplication.user_id == user_id,
        JobApplication.created_at >= day_start,
    ).count()
    successful_referrals = db.query(Referral).filter_by(referrer_phone=user_id).count()
    total_allowed = DAILY_SWIPE_LIMIT + (successful_referrals * REFERRAL_BONUS_SWIPES)
    remaining = max(0, total_allowed - today_applied)
    return {
        "total_allowed": total_allowed,
        "used_today": today_applied,
        "remaining": remaining,
        "base_limit": DAILY_SWIPE_LIMIT,
        "referral_bonus": successful_referrals * REFERRAL_BONUS_SWIPES,
        "successful_referrals": successful_referrals,
    }


@router.get("/swipes-remaining")
async def swipes_remaining(request: Request):
    """Get how many right swipes the caller has left today (identity from token)."""
    user_id = caller_phone(request)
    try:
        db = get_db()
        try:
            info = _get_swipes_remaining(db, user_id)
            return JSONResponse(info, headers={"Access-Control-Allow-Origin": "*"})
        finally:
            db.close()
    except Exception as e:
        print(f"[SWITCH] Error fetching swipes remaining: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swipe-apply")
async def swipe_apply(payload: SwipeApplyRequest, http_request: Request):
    """Quick apply from swipe — accepts just job_id, fetches job details from DB."""
    try:
        user_id = caller_phone(http_request)
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Check swipe limit
            swipe_info = _get_swipes_remaining(db, user_id)
            if swipe_info["remaining"] <= 0:
                return JSONResponse({
                    "status": "error",
                    "message": "Daily swipe limit reached. Refer friends to get more swipes!",
                    "swipe_info": swipe_info,
                }, status_code=429, headers={"Access-Control-Allow-Origin": "*"})

            existing = db.query(JobApplication).filter_by(
                user_id=user_id, job_id=payload.job_id
            ).first()
            if existing:
                app_dict = existing.to_dict()
                return JSONResponse({
                    "status": "success",
                    "message": "Already applied",
                    "application": app_dict
                }, headers={"Access-Control-Allow-Origin": "*"})

            job = db.query(Job).filter_by(job_id=payload.job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            app = JobApplication(
                user_id=user_id,
                job_id=payload.job_id,
                company=job.company or "",
                role=job.title or "",
                salary=f"{job.salary_min or ''}-{job.salary_max or ''}",
                location=job.location or "",
                logo=job.logo or "",
                applied_date=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                status="calling_employer",
                call_scheduled=False,
                call_time=None,
                created_at=time.time(),
            )
            db.add(app)
            db.flush()

            # Re-check limit after insert to guard against concurrent requests
            post_info = _get_swipes_remaining(db, user_id)
            if post_info["used_today"] > post_info["total_allowed"]:
                db.rollback()
                return JSONResponse({
                    "status": "error",
                    "message": "Daily swipe limit reached. Refer friends to get more swipes!",
                    "swipe_info": post_info,
                }, status_code=429, headers={"Access-Control-Allow-Origin": "*"})

            db.commit()
            app_id = app.id
            app_dict = app.to_dict()
            print(f"[SWITCH] Swipe-apply recorded for {user_id}: {job.company} - {job.title}")
        finally:
            db.close()

        _trigger_employer_call(payload.job_id, user_id)
        _trigger_employer_whatsapp(payload.job_id, user_id, app_id)

        return JSONResponse({
            "status": "success",
            "message": "Application recorded, calling employer",
            "application": app_dict
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error in swipe-apply: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in swipe-apply: {str(e)}")


DELIVERY_BRANDS = {"zomato", "swiggy", "zepto", "instamart", "blinkit"}


def _detect_delivery_brand(title: str, company: str) -> str:
    """Detect delivery brand from job title/company."""
    text = (title + " " + company).lower()
    for brand in DELIVERY_BRANDS:
        if brand in text:
            return brand
    return ""


@router.post("/delivery-apply")
async def delivery_apply(payload: SwipeApplyRequest, http_request: Request):
    """Apply for a delivery job — creates DeliveryApplication + JobApplication (no employer call)."""
    try:
        user_id = caller_phone(http_request)
        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            swipe_info = _get_swipes_remaining(db, user_id)
            if swipe_info["remaining"] <= 0:
                return JSONResponse({
                    "status": "error",
                    "message": "Daily swipe limit reached. Refer friends to get more swipes!",
                    "swipe_info": swipe_info,
                }, status_code=429, headers={"Access-Control-Allow-Origin": "*"})

            existing = db.query(JobApplication).filter_by(
                user_id=user_id, job_id=payload.job_id
            ).first()
            if existing:
                delivery_app = db.query(DeliveryApplication).filter_by(
                    user_id=user_id, job_id=payload.job_id
                ).first()
                return JSONResponse({
                    "status": "success",
                    "message": "Already applied",
                    "application": existing.to_dict(),
                    "delivery": {
                        "status": delivery_app.status if delivery_app else "documents_pending",
                        "docs_uploaded": delivery_app.docs_uploaded if delivery_app else 0,
                        "total_docs_required": 6,
                    } if delivery_app else None,
                }, headers={"Access-Control-Allow-Origin": "*"})

            job = db.query(Job).filter_by(job_id=payload.job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            brand = _detect_delivery_brand(job.title or "", job.company or "")

            app = JobApplication(
                user_id=user_id,
                job_id=payload.job_id,
                company=job.company or "",
                role=job.title or "",
                salary=f"{job.salary_min or ''}-{job.salary_max or ''}",
                location=job.location or "",
                logo=job.logo or "",
                applied_date=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                status="documents_pending",
                call_scheduled=False,
                call_time=None,
                created_at=time.time(),
            )
            db.add(app)

            delivery_app = DeliveryApplication(
                user_id=user_id,
                job_id=payload.job_id,
                brand=brand,
                company=job.company or "",
                role=job.title or "",
                status="documents_pending",
                docs_uploaded=0,
                total_docs_required=6,
                created_at=time.time(),
            )
            db.add(delivery_app)
            db.flush()

            post_info = _get_swipes_remaining(db, user_id)
            if post_info["used_today"] > post_info["total_allowed"]:
                db.rollback()
                return JSONResponse({
                    "status": "error",
                    "message": "Daily swipe limit reached. Refer friends to get more swipes!",
                    "swipe_info": post_info,
                }, status_code=429, headers={"Access-Control-Allow-Origin": "*"})

            db.commit()
            app_dict = app.to_dict()
            print(f"[SWITCH] Delivery-apply recorded for {user_id}: {job.company} - {job.title} (brand={brand})")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": "Delivery application recorded",
            "application": app_dict,
            "delivery": {
                "status": "documents_pending",
                "docs_uploaded": 0,
                "total_docs_required": 6,
                "brand": brand,
            },
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error in delivery-apply: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error in delivery-apply: {str(e)}")


VALID_DOC_TYPES = {"aadhaar_front", "aadhaar_back", "pan", "driving_license", "vehicle_rc", "bank_details"}


@router.post("/delivery-docs/upload/{job_id}")
async def upload_delivery_doc(job_id: str, request: Request, doc_type: str = "", file: UploadFile = File(...)):
    """Upload a delivery document image."""
    try:
        user_id = caller_phone(request)
        if doc_type not in VALID_DOC_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid doc_type. Must be one of: {', '.join(VALID_DOC_TYPES)}")

        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        file_content = await file.read()
        file_size = len(file_content)

        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 5MB")
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        base64_image = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{file.content_type};base64,{base64_image}"

        db = get_db()
        try:
            existing_doc = db.query(DeliveryDocument).filter_by(
                user_id=user_id, job_id=job_id, doc_type=doc_type
            ).first()

            if existing_doc:
                existing_doc.doc_data = data_url
                existing_doc.file_size = file_size
                existing_doc.status = "uploaded"
                existing_doc.created_at = time.time()
            else:
                doc = DeliveryDocument(
                    user_id=user_id,
                    job_id=job_id,
                    doc_type=doc_type,
                    doc_data=data_url,
                    file_size=file_size,
                    status="uploaded",
                    created_at=time.time(),
                )
                db.add(doc)

            db.flush()

            total_uploaded = db.query(DeliveryDocument).filter_by(
                user_id=user_id, job_id=job_id
            ).count()

            delivery_app = db.query(DeliveryApplication).filter_by(
                user_id=user_id, job_id=job_id
            ).first()
            if delivery_app:
                delivery_app.docs_uploaded = total_uploaded
                if total_uploaded >= delivery_app.total_docs_required:
                    delivery_app.status = "documents_complete"
                    job_app = db.query(JobApplication).filter_by(
                        user_id=user_id, job_id=job_id
                    ).first()
                    if job_app:
                        job_app.status = "documents_complete"

            db.commit()
            print(f"[SWITCH] Delivery doc uploaded: {user_id}/{job_id}/{doc_type} ({file_size} bytes, {total_uploaded}/6)")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "doc_type": doc_type,
            "docs_uploaded": total_uploaded,
            "total_required": 6,
            "all_complete": total_uploaded >= 6,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error uploading delivery doc: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error uploading delivery doc: {str(e)}")


@router.get("/delivery-docs/{job_id}")
async def get_delivery_docs(job_id: str, request: Request):
    """Get delivery document upload status for a user/job."""
    try:
        user_id = caller_phone(request)
        db = get_db()
        try:
            docs = db.query(DeliveryDocument).filter_by(
                user_id=user_id, job_id=job_id
            ).all()
            uploaded_types = {d.doc_type: {"status": d.status, "created_at": d.created_at} for d in docs}

            delivery_app = db.query(DeliveryApplication).filter_by(
                user_id=user_id, job_id=job_id
            ).first()
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "uploaded_docs": uploaded_types,
            "docs_uploaded": len(uploaded_types),
            "total_required": 6,
            "application_status": delivery_app.status if delivery_app else "unknown",
            "brand": delivery_app.brand if delivery_app else "",
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting delivery docs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applications")
async def get_switch_applications(request: Request, since: float = 0):
    """Get all job applications for the calling user (identity from token).

    If ``since`` is provided, only return applications modified after that
    timestamp (delta polling).
    """
    user_id = caller_phone(request)
    try:
        db = get_db()
        try:
            query = db.query(JobApplication).filter_by(user_id=user_id)
            if since:
                query = query.filter(JobApplication.created_at > since)
            applications = query.all()

            app_list = []
            for a in applications:
                d = a.to_dict()
                if a.status == "matched":
                    job = db.query(Job).filter_by(job_id=a.job_id).first()
                    d["employer_phone"] = job.phone if job else None
                app_list.append(d)
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "applications": app_list,
            "total": len(app_list)
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting applications: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting applications: {str(e)}")


@router.post("/applications/{application_id}/no-show")
async def mark_no_show(application_id: str, job_id: str, candidate_id: str, business_id: str):
    """Mark candidate as no-show for interview."""
    try:
        edge_case_handler.handle_candidate_no_show(application_id, job_id, candidate_id, business_id)

        return JSONResponse({
            "status": "success",
            "message": "No-show recorded and replacement candidates sent"
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking no-show: {str(e)}")


@router.get("/worker-photo/{user_id}")
async def get_worker_photo(user_id: str):
    """Get worker profile photo from DB. Returns image bytes."""
    try:
        photo_data_url = None

        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if user:
                photo_data_url = user.photo_url

            if not photo_data_url:
                cand = db.query(Candidate).filter_by(phone=user_id).first()
                if cand:
                    photo_data_url = cand.photo_url
        finally:
            db.close()

        if not photo_data_url or not photo_data_url.startswith("data:"):
            raise HTTPException(status_code=404, detail="No photo")

        header, b64_data = photo_data_url.split(",", 1)
        content_type = "image/jpeg"
        if "png" in header:
            content_type = "image/png"
        elif "gif" in header:
            content_type = "image/gif"
        elif "webp" in header:
            content_type = "image/webp"

        img_bytes = base64.b64decode(b64_data)
        return Response(content=img_bytes, media_type=content_type, headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600",
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photo-stats")
async def get_photo_stats():
    """Return count of users with profile pictures."""
    try:
        db = get_db()
        try:
            all_users = db.query(User).all()
            switch_with_photo = sum(1 for u in all_users if _has_photo(u.photo_url))
            all_candidates = db.query(Candidate).all()
            candidates_with_photo = sum(1 for c in all_candidates if _has_photo(c.photo_url))
        finally:
            db.close()

        return JSONResponse({
            "switchUsersWithPhotos": switch_with_photo,
            "candidatesWithPhotos": candidates_with_photo,
            "totalWithPhotos": switch_with_photo + candidates_with_photo,
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




def _photo_api_path(user_id: str) -> str:
    """Return API path for worker photo."""
    return f"/api/switch/worker-photo/{user_id}"


def _has_photo(url: Optional[str]) -> bool:
    """Check if user has a photo."""
    if not url:
        return False
    return url.startswith("data:") or url.startswith("http")


def _calc_age(dob_str):
    """Calculate age from YYYY-MM-DD date of birth string."""
    if not dob_str:
        return None
    try:
        from datetime import date
        parts = dob_str.split("-")
        birth = date(int(parts[0]), int(parts[1]), int(parts[2]))
        today = date.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except Exception:
        return None


def _format_expected_pay(sal_min, sal_max):
    """Format expected pay from min/max salary integers."""
    if sal_min or sal_max:
        return f"\u20B9{sal_min:,}-\u20B9{sal_max:,}/month"
    return "Negotiable"


@router.get("/available-workers")
async def get_available_workers():
    """Get available workers for employer feed."""
    try:
        workers_map = {}

        db = get_db()
        try:
            all_users = db.query(User).all()
            for u in all_users:
                name = (u.name or "").strip()
                if not name:
                    continue

                apps = db.query(JobApplication).filter_by(user_id=u.phone).all()
                hired_count = sum(1 for a in apps if a.status == "hired")
                roles = parse_json_col(u.preferred_roles)
                exp = u.experience or "Not specified"
                has_photo = _has_photo(u.photo_url)

                expected_pay = _format_expected_pay(u.expected_salary_min or 0, u.expected_salary_max or 0)
                age = _calc_age(u.date_of_birth)

                workers_map[u.phone] = {
                    "userId": u.phone,
                    "id": u.phone,
                    "name": name,
                    "photoURL": _photo_api_path(u.phone) if has_photo else None,
                    "hasPhoto": has_photo,
                    "phone": u.phone,
                    "experience": exp,
                    "preferredRoles": roles,
                    "languages": parse_json_col(u.languages) or ["Hindi"],
                    "location": u.location or "Gurgaon",
                    "lat": u.lat,
                    "lng": u.lng,
                    "isAvailable": u.is_available,
                    "verified": u.verified,
                    "expectedPay": expected_pay,
                    "gender": u.gender or "",
                    "age": age,
                    "education": u.education or "",
                    "previousCompany": u.previous_company or "",
                    "previousRole": u.previous_role or "",
                    "workDuration": u.work_duration or "",
                    "bio": f"{exp} experience. {', '.join(roles[:3])}".strip(". ,") or "Looking for work",
                    "jobsCompleted": hired_count,
                    "rating": 0,
                    "totalApplied": len(apps),
                    "interviews": sum(1 for a in apps if a.status == "interview"),
                    "hired": hired_count,
                }

            all_candidates = db.query(Candidate).all()
            for cand in all_candidates:
                name = (cand.name or "").strip()
                if not name:
                    continue

                expected_min = cand.expected_salary_min or 0
                expected_max = cand.expected_salary_max or 0
                if expected_min or expected_max:
                    expected_pay = f"\u20B9{expected_min:,}-\u20B9{expected_max:,}/month"
                else:
                    expected_pay = "Negotiable"

                prev_roles = parse_json_col(cand.previous_roles)
                area = cand.area or ""
                status = cand.status or "AVAILABLE"
                has_photo = _has_photo(cand.photo_url)

                worker = {
                    "userId": cand.phone,
                    "id": cand.phone,
                    "name": name,
                    "photoURL": _photo_api_path(cand.phone) if has_photo else None,
                    "hasPhoto": has_photo,
                    "phone": cand.phone,
                    "experience": cand.experience_level or "Not specified",
                    "preferredRoles": prev_roles,
                    "languages": parse_json_col(cand.languages) or ["Hindi"],
                    "location": area or "Gurgaon",
                    "lat": cand.lat,
                    "lng": cand.lng,
                    "isAvailable": status == "AVAILABLE",
                    "verified": True,
                    "expectedPay": expected_pay,
                    "bio": f"{cand.experience_level or ''} experience. {', '.join(prev_roles[:3])}".strip(". ,") or "Looking for work",
                    "jobsCompleted": 0,
                    "rating": 0,
                }

                if cand.phone in workers_map:
                    existing = workers_map[cand.phone]
                    workers_map[cand.phone] = {
                        **existing,
                        "photoURL": _photo_api_path(cand.phone) if (worker.get("hasPhoto") or existing.get("hasPhoto")) else None,
                        "hasPhoto": worker.get("hasPhoto", False) or existing.get("hasPhoto", False),
                        "experience": worker["experience"] if worker["experience"] != "Not specified" else existing.get("experience"),
                        "preferredRoles": worker["preferredRoles"] if worker["preferredRoles"] else existing.get("preferredRoles", []),
                        "languages": worker["languages"] if worker["languages"] != ["Hindi"] else existing.get("languages", ["Hindi"]),
                        "location": worker["location"] if worker["location"] != "Gurgaon" else existing.get("location"),
                        "lat": worker.get("lat") or existing.get("lat"),
                        "lng": worker.get("lng") or existing.get("lng"),
                        "expectedPay": worker.get("expectedPay", "Negotiable"),
                        "bio": worker.get("bio", existing.get("bio", "")),
                        "jobsCompleted": existing.get("jobsCompleted", 0),
                    }
                else:
                    workers_map[cand.phone] = worker
        finally:
            db.close()

        workers = list(workers_map.values())
        workers.sort(key=lambda w: (not w.get("isAvailable", True), not w.get("hasPhoto", False), -(w.get("totalApplied", 0) + w.get("hired", 0))))
        workers = workers[:50]
        workers_with_photos = sum(1 for w in workers if w.get("hasPhoto"))

        return JSONResponse({
            "status": "success",
            "workers": workers,
            "total": len(workers),
            "workersWithPhotos": workers_with_photos,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting available workers: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


ROLE_TO_CATEGORIES = {
    "Delivery Partner": ["Delivery"],
    "Delivery Executive": ["Delivery"],
    "Warehouse Worker": ["Warehouse / Logistics"],
    "Picker/Packer": ["Warehouse / Logistics"],
    "Security Guard": ["Security Guard"],
    "Store Assistant": ["Warehouse / Logistics"],
    "Retail Associate": ["Field Sales", "Sales / Business Development"],
    "Waiter/Server": ["Housekeeping"],
    "Receptionist": ["Customer Support / TeleCaller", "Sales / Business Development"],
    "Driver": ["Driver"],
    "Cook/Chef": ["Housekeeping"],
    "Housekeeping": ["Housekeeping"],
    "Sales Executive": ["Field Sales", "Sales / Business Development", "Telesales / Telemarketing"],
    "Customer Service": ["Customer Support / TeleCaller", "Sales / Business Development"],
    "Data Entry": ["Sales / Business Development", "Field Sales"],
    "Packing/Assembly": ["Manufacturing", "Warehouse / Logistics"],
    "Loading/Unloading": ["Labour/Helper", "Warehouse / Logistics"],
    "Cashier": ["Field Sales", "Sales / Business Development"],
    "Supervisor": ["Manufacturing", "Warehouse / Logistics", "Security Guard"],
    "Helper": ["Labour/Helper"],
    "Cleaner": ["Housekeeping", "Labour/Helper"],
    "Watchman": ["Security Guard"],
    "Gardener": ["Housekeeping"],
    "Electrician": ["Manufacturing", "Refrigerator & AC Technician"],
    "Plumber": ["Labour/Helper", "Manufacturing"],
    "Carpenter": ["Labour/Helper", "Manufacturing"],
    "Painter": ["Labour/Helper", "Manufacturing"],
    "Mason": ["Labour/Helper"],
    "Welder": ["Manufacturing", "Labour/Helper"],
    "Mechanic": ["Manufacturing", "Refrigerator & AC Technician"],
    "AC Technician": ["Refrigerator & AC Technician", "Manufacturing"],
    "Factory Worker": ["Manufacturing", "Labour/Helper"],
    "Office Boy": ["Housekeeping", "Labour/Helper", "Field Sales"],
    "Telecaller": ["Telesales / Telemarketing", "Sales / Business Development", "Customer Support / TeleCaller"],
    "Ward Boy": ["Ward Boy"],
}

NCR_CITY_COORDS = {
    "Gurgaon": (28.4595, 77.0266),
    "Delhi": (28.6139, 77.2090),
    "Noida": (28.5355, 77.3910),
    "Faridabad": (28.4089, 77.3178),
    "Ghaziabad": (28.6692, 77.4538),
    "Greater Noida": (28.4744, 77.5040),
}

NCR_PROXIMITY = {
    "Gurgaon": ["Gurgaon", "Delhi", "Faridabad", "Noida", "Ghaziabad", "Greater Noida"],
    "Delhi": ["Delhi", "Gurgaon", "Noida", "Faridabad", "Ghaziabad", "Greater Noida"],
    "Noida": ["Noida", "Greater Noida", "Delhi", "Ghaziabad", "Gurgaon", "Faridabad"],
    "Faridabad": ["Faridabad", "Delhi", "Gurgaon", "Noida", "Ghaziabad", "Greater Noida"],
    "Ghaziabad": ["Ghaziabad", "Delhi", "Noida", "Greater Noida", "Gurgaon", "Faridabad"],
    "Greater Noida": ["Greater Noida", "Noida", "Delhi", "Ghaziabad", "Gurgaon", "Faridabad"],
}


def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two lat/lng points."""
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _format_job_row(job: Job, user_lat=None, user_lng=None) -> dict:
    """Format a Job ORM row into API response format."""
    salary_min = job.salary_min or 0
    salary_max = job.salary_max or 0
    if salary_min and salary_max:
        salary = f"\u20B9{salary_min:,} - \u20B9{salary_max:,}"
    elif salary_min:
        salary = f"\u20B9{salary_min:,}"
    else:
        salary = "Negotiable"

    min_exp = job.min_exp or 0
    max_exp = job.max_exp or 0
    if min_exp or max_exp:
        experience = f"{min_exp}-{max_exp} years"
    else:
        experience = "Freshers welcome"

    perks_raw = job.perks or ""
    perks = [p.strip() for p in perks_raw.split(",") if p.strip()] if perks_raw else []

    distance_km = None
    if user_lat and user_lng and job.lat and job.lng:
        distance_km = round(_haversine_km(user_lat, user_lng, job.lat, job.lng), 1)

    requirements = parse_json_col(job.requirements)
    benefits = parse_json_col(job.benefits)

    result = {
        "id": job.job_id,
        "company": job.company or "",
        "logo": job.logo or "\U0001F4BC",
        "title": job.title or "",
        "salary": salary,
        "location": job.location or "",
        "city": job.city or "",
        "category": job.category or "",
        "openings": job.openings or 0,
        "experience": experience,
        "job_type": job.job_type or "Full Time",
        "shift": job.shift or "",
        "perks": perks,
        "description": job.description or "",
        "requirements": requirements,
        "benefits": benefits,
        "is_delivery": (job.category or "").lower() == "delivery",
    }
    if distance_km is not None:
        result["distance"] = f"{distance_km} km"
        result["_distance_km"] = distance_km
    return result


@router.get("/jobs/jobhai-feed")
async def get_jobhai_feed(user_id: str = "", page: int = 0):
    """Get paginated JobHai job feed sorted by distance from candidate."""
    try:
        page_size = 50

        user_lat = None
        user_lng = None
        user_city = ""
        preferred_categories = set()

        db = get_db()
        try:
            if user_id:
                user = db.query(User).filter_by(phone=user_id).first()
                if user:
                    user_lat = user.lat
                    user_lng = user.lng
                    user_location = (user.location or "").strip()
                    for city_name in NCR_CITY_COORDS:
                        if city_name.lower() in user_location.lower():
                            user_city = city_name
                            break
                    if not user_lat and user_city:
                        user_lat, user_lng = NCR_CITY_COORDS[user_city]
                    for role in parse_json_col(user.preferred_roles):
                        for cat in ROLE_TO_CATEGORIES.get(role, []):
                            preferred_categories.add(cat)

            all_jobs_rows = db.query(Job).all()
        finally:
            db.close()

        all_jobs = [_format_job_row(j, user_lat, user_lng) for j in all_jobs_rows]

        if preferred_categories:
            matched = [j for j in all_jobs if j["category"] in preferred_categories]
            unmatched = [j for j in all_jobs if j["category"] not in preferred_categories]
        else:
            matched = all_jobs
            unmatched = []

        def _sort_by_distance(jobs):
            if not (user_lat and user_lng):
                if user_city:
                    city_order = NCR_PROXIMITY.get(user_city, list(NCR_PROXIMITY["Delhi"]))
                    city_rank = {c: i for i, c in enumerate(city_order)}
                    jobs.sort(key=lambda j: city_rank.get(j["city"], 99))
                return jobs
            nearby = [j for j in jobs if j.get("_distance_km") is not None and j["_distance_km"] <= 10]
            farther = [j for j in jobs if j.get("_distance_km") is not None and j["_distance_km"] > 10]
            no_coords = [j for j in jobs if j.get("_distance_km") is None]
            nearby.sort(key=lambda j: j["_distance_km"])
            farther.sort(key=lambda j: j["_distance_km"])
            return nearby + farther + no_coords

        all_jobs = _sort_by_distance(matched) + _sort_by_distance(unmatched)

        ALLOWED_DELIVERY_BRANDS = {"zomato", "swiggy", "zepto", "instamart", "blinkit"}
        MAX_DELIVERY_PER_BRAND = 5

        def _cap_delivery_brands(jobs):
            """Filter delivery jobs: only allowed brands, max 5 per brand."""
            result = []
            brand_counts = {}
            for j in jobs:
                if j.get("category", "").lower() != "delivery":
                    result.append(j)
                    continue
                text = (j.get("title", "") + " " + j.get("company", "")).lower()
                matched_brand = None
                for brand in ALLOWED_DELIVERY_BRANDS:
                    if brand in text:
                        matched_brand = brand
                        break
                if not matched_brand:
                    continue
                brand_counts[matched_brand] = brand_counts.get(matched_brand, 0) + 1
                if brand_counts[matched_brand] <= MAX_DELIVERY_PER_BRAND:
                    result.append(j)
            return result

        all_jobs = _cap_delivery_brands(all_jobs)

        employer_jobs = [j for j in all_jobs if j.get("id", "").startswith("emp_")]
        other_jobs = [j for j in all_jobs if not j.get("id", "").startswith("emp_")]
        all_jobs = employer_jobs + other_jobs

        for j in all_jobs:
            j.pop("_distance_km", None)

        start = page * page_size
        end = start + page_size
        page_jobs = all_jobs[start:end]
        has_more = end < len(all_jobs)

        return JSONResponse({
            "jobs": page_jobs,
            "has_more": has_more,
            "page": page,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting jobhai feed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/feed/{candidate_id}")
async def get_job_feed(candidate_id: str):
    """Get job feed for candidate (legacy endpoint)."""
    try:
        matching_jobs = switch_matching_service.find_jobs_for_candidate(
            candidate_id=candidate_id,
            exclude_swiped=True,
            limit=20
        )

        jobs_list = []
        for job in matching_jobs:
            business_doc = fs.collection("businesses").document(job.business_id).get()
            business_name = business_doc.to_dict().get("name", "Business") if business_doc.exists else "Business"

            jobs_list.append({
                "id": job.id,
                "company": business_name,
                "role": job.role,
                "salary": f"\u20B9{job.salary_min:,} - \u20B9{job.salary_max:,}",
                "location": job.location,
                "experience": job.experience_required,
                "posted_time": job.created_at,
                "interview_timing": job.interview_timing,
            })

        return JSONResponse({
            "status": "success",
            "jobs": jobs_list,
            "total": len(jobs_list)
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting job feed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting job feed: {str(e)}")


VALID_APPLICATION_STATUSES = {
    "pending", "calling_employer", "connecting", "interview",
    "matched", "employer_declined", "employer_interested",
    "employer_shortlisted", "hired", "cancelled", "expired",
}


class SwitchApplicationUpdate(BaseModel):
    """Request model for updating job application status."""
    status: Optional[str] = None
    callScheduled: Optional[bool] = None
    callTime: Optional[str] = None


class SwitchReferralTrack(BaseModel):
    """Request model for tracking referrals."""
    referrer_code: str
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    referee_user_id: Optional[str] = None
    referee_name: str


@router.put("/applications/{job_id}")
async def update_application_status(
    job_id: str,
    payload: SwitchApplicationUpdate,
    http_request: Request,
):
    """Update application status (e.g., schedule call)."""
    try:
        user_id = caller_phone(http_request)
        if payload.status is not None and payload.status not in VALID_APPLICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{payload.status}'. Must be one of: {', '.join(sorted(VALID_APPLICATION_STATUSES))}",
            )

        db = get_db()
        try:
            app = db.query(JobApplication).filter_by(user_id=user_id, job_id=job_id).first()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")

            if payload.status is not None:
                app.status = payload.status
            if payload.callScheduled is not None:
                app.call_scheduled = payload.callScheduled
            if payload.callTime is not None:
                app.call_time = payload.callTime
            db.commit()
            print(f"[SWITCH] Updated application {job_id} for user {user_id}: status={payload.status}")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": "Application updated"
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error updating application: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating application: {str(e)}")




@router.post("/track-referral")
async def track_referral(payload: SwitchReferralTrack, http_request: Request):
    """Track referral when someone signs up with a referral code."""
    try:
        referrer_code = payload.referrer_code.upper().strip()
        referee_user_id = caller_phone(http_request)
        referee_name = payload.referee_name

        db = get_db()
        try:
            referrer = db.query(User).filter_by(referral_code=referrer_code).first()
            if not referrer:
                print(f"[SWITCH] Referral code {referrer_code} not found")
                return JSONResponse({
                    "status": "error",
                    "message": "Invalid referral code"
                }, headers={"Access-Control-Allow-Origin": "*"})

            if referrer.phone == referee_user_id:
                return JSONResponse({
                    "status": "error",
                    "message": "You cannot use your own referral code"
                }, headers={"Access-Control-Allow-Origin": "*"})

            existing = db.query(Referral).filter_by(
                referrer_phone=referrer.phone, referee_user_id=referee_user_id
            ).first()
            if existing:
                return JSONResponse({
                    "status": "success",
                    "message": "Referral already tracked"
                }, headers={"Access-Control-Allow-Origin": "*"})

            ref = Referral(
                referrer_phone=referrer.phone,
                referee_user_id=referee_user_id,
                referee_name=referee_name,
                referred_at=time.time(),
                status="signed_up",
                earnings=0,
            )
            db.add(ref)

            all_referrals = db.query(Referral).filter_by(referrer_phone=referrer.phone).all()
            total_earnings = sum(r.earnings for r in all_referrals)
            referrer.total_referral_earnings = total_earnings
            referrer.total_referrals = len(all_referrals) + 1
            referrer.updated_at = time.time()

            db.commit()
            referrer_phone = referrer.phone
            print(f"[SWITCH] Tracked referral: {referee_name} referred by {referrer_code} (user: {referrer_phone})")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": "Referral tracked successfully",
            "referrer_user_id": referrer_phone
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error tracking referral: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking referral: {str(e)}")


class ContactsUploadRequest(BaseModel):
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None
    phones: List[str]




@router.post("/contacts")
async def upload_worker_contacts(payload: ContactsUploadRequest, http_request: Request):
    """
    Store phone contacts uploaded by a worker on signup.
    Used to find which of their contacts are already on Switch
    and to surface referral opportunities.
    Contacts are stored as-is; no PII is shared with other users.
    """
    try:
        user_id = caller_phone(http_request)
        phones = [p.strip() for p in payload.phones if p.strip()]

        if not user_id or not phones:
            return JSONResponse({"status": "ok", "matched": 0},
                                headers={"Access-Control-Allow-Origin": "*"})

        # Deduplicate
        phones = list(set(phones))

        db = get_db()
        try:
            user = db.query(User).filter_by(phone=user_id).first()
            if user:
                user.contacts_phones = json.dumps(phones)
                db.commit()
                print(f"[SWITCH] Stored {len(phones)} contacts for user {user_id}")

            # Count how many contacts are existing Switch users
            matched = (
                db.query(User)
                .filter(User.phone.in_(phones))
                .filter(User.phone != user_id)
                .count()
            )
        finally:
            db.close()

        return JSONResponse(
            {"status": "ok", "matched": matched},
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except Exception as e:
        print(f"[SWITCH] Error uploading contacts: {e}")
        return JSONResponse(
            {"status": "ok", "matched": 0},
            headers={"Access-Control-Allow-Origin": "*"},
        )


def _trigger_employer_call(job_id: str, user_id: str):
    """Trigger Vobiz outbound call to employer via the employer-outbound system.
    Runs in a background thread to avoid blocking the apply response.
    """
    def _call():
        try:
            db = get_db()
            try:
                job_row = db.query(Job).filter_by(job_id=job_id).first()
                if not job_row:
                    print(f"[SWITCH] Job {job_id} not found, skipping employer call")
                    return
                job = job_row.to_dict()

                employer_phone = (job.get("phone") or "").strip()
                if not employer_phone:
                    print(f"[SWITCH] No employer phone for job {job_id}, skipping call")
                    return

                user_row = db.query(User).filter_by(phone=user_id).first()
                candidate_name = "Candidate"
                candidate_experience = "Not specified"
                candidate_location = "NCR"
                if user_row:
                    candidate_name = user_row.name or "Candidate"
                    candidate_experience = user_row.experience or "Not specified"
                    candidate_location = user_row.location or "NCR"
            finally:
                db.close()

            server_host = os.getenv("SERVER_HOST", "api.relayy.world")
            initiate_url = f"https://{server_host}/api/employer-outbound/initiate"

            payload = {
                "employer_phone": employer_phone,
                "company": job.get("company", ""),
                "job_id": job_id,
                "job_title": job.get("title", ""),
                "job_category": job.get("category", ""),
                "city": job.get("city", ""),
                "salary_max": job.get("salary_max", 0),
                "candidate_phone": user_id,
                "candidate_name": candidate_name,
                "candidate_experience": candidate_experience,
                "candidate_location": candidate_location,
            }

            print(f"[SWITCH] Triggering employer call: {employer_phone} for {job.get('title')} ({candidate_name})")
            resp = httpx.post(initiate_url, json=payload, timeout=15)
            print(f"[SWITCH] Employer call response: {resp.status_code} {resp.text[:200]}")

        except Exception as e:
            print(f"[SWITCH] Error triggering employer call for job {job_id}: {e}")
            traceback.print_exc()

    threading.Thread(target=_call, daemon=True).start()


def _trigger_employer_whatsapp(job_id: str, user_id: str, application_id: int):
    """Send employer a WhatsApp with candidate details and approval link.
    Runs in a background thread to avoid blocking the apply response.
    """
    def _send():
        try:
            db = get_db()
            try:
                job = db.query(Job).filter_by(job_id=job_id).first()
                if not job:
                    print(f"[SWITCH] Job {job_id} not found, skipping employer WhatsApp")
                    return

                employer_phone = (job.phone or "").strip()
                if not employer_phone:
                    print(f"[SWITCH] No employer phone for job {job_id}, skipping WhatsApp")
                    return

                user = db.query(User).filter_by(phone=user_id).first()
                if not user:
                    print(f"[SWITCH] User {user_id} not found, skipping employer WhatsApp")
                    return

                app = db.query(JobApplication).filter_by(id=application_id).first()
                if not app:
                    print(f"[SWITCH] Application {application_id} not found, skipping employer WhatsApp")
                    return

                token = str(uuid.uuid4())
                app.match_token = token
                db.commit()

                send_employer_whatsapp(token, job, user)
            finally:
                db.close()

        except Exception as e:
            print(f"[SWITCH] Error sending employer WhatsApp for job {job_id}: {e}")
            traceback.print_exc()

    threading.Thread(target=_send, daemon=True).start()


# ==================== EMPLOYER ENDPOINTS ====================


class EmployerPostJobRequest(BaseModel):
    """Request model for employer posting a job."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    employer_phone: Optional[str] = None
    title: str
    category: str
    salary_min: Optional[int] = 0
    salary_max: Optional[int] = 0
    location: Optional[str] = ""
    city: Optional[str] = ""
    requirements: Optional[str] = ""
    openings: Optional[int] = 1
    company: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None




@router.post("/employer/post-job")
async def employer_post_job(payload: EmployerPostJobRequest, http_request: Request):
    """Employer posts a new job listing."""
    try:
        employer_phone = caller_phone(http_request)
        lat = payload.lat
        lng = payload.lng

        db = get_db()
        try:
            job_id = f"emp_{employer_phone}_{uuid.uuid4().hex[:8]}"

            if lat is None or lng is None:
                profile = db.query(EmployerProfile).filter_by(phone=employer_phone).first()
                if profile and profile.lat is not None and profile.lng is not None:
                    lat = profile.lat
                    lng = profile.lng

            req_list = []
            if payload.requirements:
                req_list = [r.strip() for r in payload.requirements.split(",") if r.strip()]

            job = Job(
                job_id=job_id,
                title=payload.title,
                company=payload.company or "",
                category=payload.category,
                location=payload.location or "",
                city=payload.city or "",
                salary_min=payload.salary_min or 0,
                salary_max=payload.salary_max or 0,
                openings=payload.openings or 1,
                requirements=json.dumps(req_list),
                phone=employer_phone,
                company_id=employer_phone,
                job_type="Full Time",
                lat=lat,
                lng=lng,
                created_at=time.time(),
            )
            db.add(job)
            db.commit()
            print(f"[SWITCH] Employer {employer_phone} posted job: {payload.title} ({job_id})")
        finally:
            db.close()

        if lat is None and (payload.location or payload.city):
            async def _geocode_job():
                try:
                    coords = await geocode_location(payload.location or "", payload.city or "")
                    if coords:
                        gdb = get_db()
                        try:
                            j = gdb.query(Job).filter_by(job_id=job_id).first()
                            if j:
                                j.lat = coords[0]
                                j.lng = coords[1]
                                gdb.commit()
                                print(f"[SWITCH] Geocoded job {job_id}: {coords}")
                        finally:
                            gdb.close()
                except Exception as e:
                    print(f"[SWITCH] Geocode error for job {job_id}: {e}")
            asyncio.create_task(_geocode_job())

        return JSONResponse({
            "status": "success",
            "job_id": job_id,
            "message": "Job posted successfully",
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error posting employer job: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error posting job: {str(e)}")


@router.get("/employer/applications")
async def get_employer_applications(request: Request):
    """Get all applications for jobs posted by this employer (identity from token)."""
    try:
        employer_phone = caller_phone(request)
        db = get_db()
        try:
            employer_jobs = db.query(Job).filter_by(company_id=employer_phone).all()
            job_ids = [j.job_id for j in employer_jobs]
            job_map = {j.job_id: j for j in employer_jobs}

            if not job_ids:
                return JSONResponse({
                    "status": "success",
                    "applications": [],
                    "total": 0,
                }, headers={"Access-Control-Allow-Origin": "*"})

            applications = db.query(JobApplication).filter(
                JobApplication.job_id.in_(job_ids)
            ).all()

            app_list = []
            for app in applications:
                user = db.query(User).filter_by(phone=app.user_id).first()
                job = job_map.get(app.job_id)
                has_photo = _has_photo(user.photo_url) if user else False

                app_list.append({
                    "application_id": app.id,
                    "job_id": app.job_id,
                    "job_title": job.title if job else "",
                    "candidate_phone": app.user_id,
                    "candidate_name": user.name if user else "Unknown",
                    "candidate_photo": _photo_api_path(app.user_id) if has_photo else None,
                    "candidate_experience": user.experience if user else "",
                    "candidate_location": user.location if user else "",
                    "candidate_roles": parse_json_col(user.preferred_roles) if user else [],
                    "candidate_languages": parse_json_col(user.languages) if user else [],
                    "status": app.status,
                    "applied_date": app.applied_date,
                    "employer_action": app.employer_action,
                    "kyc_verified_at": app.kyc_verified_at,
                    "kyc_photo_url": app.kyc_photo_url,
                    "kyc_video_url": app.kyc_video_url,
                    "kyc_summary": app.kyc_summary,
                    "kyc_structured": app.kyc_structured,
                    "kyc_agent_name": app.kyc_agent_name,
                })
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "applications": app_list,
            "total": len(app_list),
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting employer applications: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting applications: {str(e)}")


@router.get("/employer/my-jobs")
async def get_employer_jobs(request: Request):
    """Get all jobs posted by this employer (identity from token)."""
    try:
        employer_phone = caller_phone(request)
        db = get_db()
        try:
            jobs = db.query(Job).filter_by(company_id=employer_phone).all()
            job_list = []
            for j in jobs:
                app_count = db.query(JobApplication).filter_by(job_id=j.job_id).count()
                job_list.append({
                    **_format_job_row(j),
                    "job_id": j.job_id,
                    "applications_count": app_count,
                    "created_at": j.created_at,
                })
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "jobs": job_list,
            "total": len(job_list),
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error getting employer jobs: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting jobs: {str(e)}")


# ==================== EMPLOYER SHORTLIST → NOTIFY CANDIDATE ====================


_shortlist_call_contexts: dict = {}


class EmployerShortlistRequest(BaseModel):
    """Request model for employer shortlisting a candidate."""
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    employer_id: Optional[str] = None
    candidate_id: str
    job_id: Optional[str] = ""


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits-only format (no + prefix)."""
    cleaned = phone.replace("+", "").replace("-", "").replace(" ", "")
    if cleaned.startswith("0"):
        cleaned = "91" + cleaned[1:]
    if len(cleaned) == 10:
        cleaned = "91" + cleaned
    return cleaned


@router.post("/employer/shortlist")
async def employer_shortlist_candidate(payload: EmployerShortlistRequest, http_request: Request):
    """Employer shortlists a candidate — notify via WhatsApp + direct call."""
    try:
        employer_phone = caller_phone(http_request)
        candidate_phone = payload.candidate_id
        db = get_db()
        try:
            employer = db.query(User).filter_by(phone=employer_phone).first()
            candidate = db.query(User).filter_by(phone=candidate_phone).first()
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")

            company = employer.name if employer else "Employer"

            job = None
            if payload.job_id:
                job = db.query(Job).filter_by(job_id=payload.job_id).first()
            if not job:
                job = db.query(Job).filter_by(company_id=employer_phone).order_by(Job.created_at.desc()).first()

            job_title = job.title if job else "a position"
            job_company = job.company if job else company

            if job:
                existing = db.query(JobApplication).filter_by(
                    user_id=candidate_phone, job_id=job.job_id
                ).first()
                if not existing:
                    app = JobApplication(
                        user_id=candidate_phone,
                        job_id=job.job_id,
                        company=job_company,
                        role=job_title,
                        salary=f"{job.salary_min or ''}-{job.salary_max or ''}",
                        location=job.location or "",
                        logo=job.logo or "",
                        applied_date=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        status="employer_shortlisted",
                        call_scheduled=False,
                        created_at=time.time(),
                    )
                    db.add(app)
                    db.commit()
        finally:
            db.close()

        job_id_for_wa = job.job_id if job else None
        call_id = uuid.uuid4().hex[:12]

        _shortlist_call_contexts[call_id] = {
            "employer_phone": _normalize_phone(employer_phone),
            "company": job_company,
            "job_title": job_title,
        }

        def _send_whatsapp():
            try:
                if not job_id_for_wa:
                    print(f"[SHORTLIST] No job found, skipping WhatsApp for {candidate_phone}")
                    return
                wa_db = get_db()
                try:
                    wa_job = wa_db.query(Job).filter_by(job_id=job_id_for_wa).first()
                    if wa_job:
                        notify_candidate_matched(candidate_phone, wa_job)
                        print(f"[SHORTLIST] WhatsApp sent to candidate {candidate_phone}")
                    else:
                        print(f"[SHORTLIST] Job {job_id_for_wa} not found in DB, skipping WhatsApp")
                finally:
                    wa_db.close()
            except Exception as e:
                print(f"[SHORTLIST] WhatsApp error for {candidate_phone}: {e}")
                traceback.print_exc()

        threading.Thread(target=_send_whatsapp, daemon=True).start()

        async def _make_call():
            try:
                server_host = os.getenv("SERVER_HOST", "api.relayy.world")
                answer_url = f"https://{server_host}/api/switch/employer/shortlist-answer?call_id={call_id}"
                to_digits = _normalize_phone(candidate_phone)
                result = await vobiz_service.make_call(
                    to_number=to_digits,
                    answer_url=answer_url,
                )
                print(f"[SHORTLIST] Call initiated to {to_digits}: {result}")
            except Exception as e:
                print(f"[SHORTLIST] Call error for {candidate_phone}: {e}")
                traceback.print_exc()

        asyncio.ensure_future(_make_call())

        print(f"[SHORTLIST] Employer {employer_phone} shortlisted {candidate_phone} for {job_title} @ {job_company}")
        return JSONResponse({
            "status": "success",
            "message": "Candidate notified",
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SHORTLIST] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/employer/shortlist-answer")
async def shortlist_answer_webhook(request: Request):
    """Vobiz answer webhook — candidate picks up, hears intro, gets connected to employer.
    CRITICAL CALL PATH: must return XML instantly, no DB calls."""
    call_id = request.query_params.get("call_id", "")
    ctx = _shortlist_call_contexts.pop(call_id, None)

    if not ctx:
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Response>\n'
            '  <Speak voice="WOMAN" language="hi-IN">Kuch gadbad ho gayi. Kripya baad mein koshish karein.</Speak>\n'
            '</Response>'
        )
        return Response(content=xml, media_type="application/xml")

    employer_phone = ctx["employer_phone"]
    company = ctx["company"]
    job_title = ctx["job_title"]

    intro = f"Namaste! {company} ko aapki profile pasand aayi hai {job_title} ke liye. Hum aapko unse connect kar rahe hain."

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        f'  <Speak voice="WOMAN" language="hi-IN">{intro}</Speak>\n'
        '  <Dial>\n'
        f'    <Number>{employer_phone}</Number>\n'
        '  </Dial>\n'
        '</Response>'
    )
    return Response(content=xml, media_type="application/xml")


# ==================== ADMIN: NOTIFY EMPLOYERS (one-time) ====================


@router.post("/admin/notify-employers")
async def admin_notify_employers(dry_run: bool = False):
    """One-time: send WhatsApp to employers about candidates who applied to their jobs."""
    from services.employer_match_service import (
        EMPLOYER_TEMPLATE_NAME,
        _normalize_wa_phone,
        _send_via_switch,
    )
    from utils.whatsapp.components import MsgComponents

    results = []
    db = get_db()
    try:
        apps = db.query(JobApplication).all()

        job_apps = {}
        for a in apps:
            if a.job_id not in job_apps:
                job_apps[a.job_id] = []
            job_apps[a.job_id].append(a)

        for job_id, applications in sorted(job_apps.items(), key=lambda x: -len(x[1])):
            job = db.query(Job).filter_by(job_id=job_id).first()
            if not job:
                results.append({"job_id": job_id, "status": "skipped", "reason": "job deleted"})
                continue

            employer_phone = (job.phone or "").strip()
            if not employer_phone:
                results.append({"job_id": job_id, "status": "skipped", "reason": "no phone"})
                continue

            wa_phone = _normalize_wa_phone(employer_phone)

            candidate_names = []
            for app in applications:
                candidate = db.query(User).filter_by(phone=app.user_id).first()
                name = candidate.name if candidate else "Candidate"
                exp = (candidate.experience if candidate else "") or "Not specified"
                loc = (candidate.location if candidate else "") or "NCR"
                candidate_names.append(f"{name} | {exp} | {loc}")

            n = len(candidate_names)
            summary = candidate_names[0] if n == 1 else f"{candidate_names[0]} (+{n - 1} more)"

            entry = {
                "job_id": job_id,
                "company": job.company,
                "title": job.title,
                "employer_phone": wa_phone,
                "candidates": n,
                "summary": summary,
            }

            if dry_run:
                entry["status"] = "dry_run"
                results.append(entry)
                continue

            payload = MsgComponents.template_scaffold(
                to=wa_phone,
                template_name=EMPLOYER_TEMPLATE_NAME,
                language_code="en",
                body_parameters=[
                    job.title or "Open Position",
                    summary,
                    "https://app.switchlocally.com/hire",
                ],
            )
            result = _send_via_switch(payload)
            entry["status"] = result.get("status", "unknown")
            if result.get("error"):
                entry["error"] = result["error"]
            results.append(entry)
    finally:
        db.close()

    sent = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")

    return JSONResponse({
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "total_jobs": len(results),
        "results": results,
    }, headers={"Access-Control-Allow-Origin": "*"})


# ==================== ADMIN: DELETE USER ====================


@router.delete("/admin/delete-user/{user_id}")
async def admin_delete_user(user_id: str):
    """Delete a user and all their data from the system."""
    try:
        db = get_db()
        try:
            deleted = {}
            deleted["delivery_documents"] = db.query(DeliveryDocument).filter_by(user_id=user_id).delete()
            deleted["delivery_applications"] = db.query(DeliveryApplication).filter_by(user_id=user_id).delete()
            deleted["job_applications"] = db.query(JobApplication).filter_by(user_id=user_id).delete()
            deleted["swipe_events"] = db.query(SwipeEvent).filter_by(user_id=user_id).delete()
            deleted["referrals_as_referrer"] = db.query(Referral).filter_by(referrer_phone=user_id).delete()
            deleted["referrals_as_referee"] = db.query(Referral).filter_by(referee_user_id=user_id).delete()
            deleted["otp"] = db.query(OtpVerification).filter_by(phone=user_id).delete()
            deleted["sessions"] = db.query(Session).filter_by(user_id=user_id).delete()
            deleted["candidate"] = db.query(Candidate).filter_by(phone=user_id).delete()
            deleted["user"] = db.query(User).filter_by(phone=user_id).delete()
            db.commit()
            print(f"[SWITCH] Deleted user {user_id}: {deleted}")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": f"User {user_id} deleted",
            "deleted": deleted,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error deleting user: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


@router.delete("/admin/delete-job/{job_id}")
async def admin_delete_job(job_id: str):
    """Delete a job and all related applications."""
    try:
        db = get_db()
        try:
            deleted = {}
            deleted["delivery_documents"] = db.query(DeliveryDocument).filter_by(job_id=job_id).delete()
            deleted["delivery_applications"] = db.query(DeliveryApplication).filter_by(job_id=job_id).delete()
            deleted["job_applications"] = db.query(JobApplication).filter_by(job_id=job_id).delete()
            deleted["swipe_events"] = db.query(SwipeEvent).filter_by(job_id=job_id).delete()
            deleted["job"] = db.query(Job).filter_by(job_id=job_id).delete()
            db.commit()
            print(f"[SWITCH] Deleted job {job_id}: {deleted}")
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "message": f"Job {job_id} deleted",
            "deleted": deleted,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error deleting job: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")


# ==================== EMPLOYER INBOX ====================



@router.get("/employer/inbox")
async def employer_inbox(request: Request):
    """Applications grouped by job for the employer inbox (identity from token)."""
    try:
        employer_phone = caller_phone(request)
        db = get_db()
        try:
            employer_jobs = db.query(Job).filter_by(company_id=employer_phone).order_by(Job.created_at.desc()).all()
            job_ids = [j.job_id for j in employer_jobs]
            if not job_ids:
                return JSONResponse({"status": "success", "jobs": []}, headers={"Access-Control-Allow-Origin": "*"})

            applications = db.query(JobApplication).filter(JobApplication.job_id.in_(job_ids)).all()
            apps_by_job = {}
            for app in applications:
                apps_by_job.setdefault(app.job_id, []).append(app)

            jobs_list = []
            for job in employer_jobs:
                job_apps = apps_by_job.get(job.job_id, [])
                candidates = []
                for app in job_apps:
                    user = db.query(User).filter_by(phone=app.user_id).first()
                    has_photo = _has_photo(user.photo_url) if user else False
                    candidates.append({
                        "application_id": app.id,
                        "phone": app.user_id,
                        "name": user.name if user else "Unknown",
                        "photo": _photo_api_path(app.user_id) if has_photo else None,
                        "experience": user.experience if user else "",
                        "location": user.location if user else "",
                        "status": app.status,
                        "employer_action": app.employer_action,
                        "applied_date": app.applied_date,
                        "applied_at": app.created_at,
                        "interview_datetime": app.interview_datetime,
                        "interview_confirmed": app.interview_confirmed,
                        "interview_outcome": app.interview_outcome,
                        "kyc_verified_at": app.kyc_verified_at,
                        "kyc_photo_url": app.kyc_photo_url,
                        "kyc_video_url": app.kyc_video_url,
                        "kyc_summary": app.kyc_summary,
                        "kyc_structured": app.kyc_structured,
                        "kyc_agent_name": app.kyc_agent_name,
                    })

                new_count = sum(1 for c in candidates if not c.get("employer_action"))
                jobs_list.append({
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "new_candidates": new_count,
                    "total_candidates": len(candidates),
                    "posted_at": job.created_at,
                    "candidates": candidates,
                })
        finally:
            db.close()

        return JSONResponse({"status": "success", "jobs": jobs_list}, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error employer inbox: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class BatchActionItem(BaseModel):
    application_id: int
    action: str  # "approve" or "decline"


class BatchActionRequest(BaseModel):
    actions: List[BatchActionItem]


@router.post("/employer/batch-action")
async def employer_batch_action(request: BatchActionRequest):
    """Bulk approve or decline applications."""
    try:
        db = get_db()
        results = []
        try:
            for item in request.actions:
                app = db.query(JobApplication).filter_by(id=item.application_id).first()
                if not app or app.employer_action:
                    results.append({"id": item.application_id, "status": "skipped"})
                    continue

                app.employer_action = "approved" if item.action == "approve" else "declined"
                app.employer_action_at = time.time()
                if item.action == "approve":
                    app.status = "matched"
                    app.matched_at = time.time()
                    _append_status_history(app, "matched")
                else:
                    app.status = "employer_declined"
                    _append_status_history(app, "employer_declined")
                results.append({"id": item.application_id, "status": app.status})

                if item.action == "approve":
                    user_id = app.user_id
                    job_id = app.job_id

                    def _notify(uid=user_id, jid=job_id):
                        try:
                            ndb = get_db()
                            try:
                                job = ndb.query(Job).filter_by(job_id=jid).first()
                                if job:
                                    notify_candidate_matched(uid, job)
                            finally:
                                ndb.close()
                        except Exception as exc:
                            print(f"[SWITCH] Error batch notify: {exc}")

                    threading.Thread(target=_notify, daemon=True).start()

            db.commit()
        finally:
            db.close()

        return JSONResponse({"status": "success", "results": results}, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error batch action: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EMPLOYER CANDIDATE DISCOVERY ====================

@router.get("/employer/matched-candidates")
async def employer_matched_candidates(request: Request, job_id: str = ""):
    """Get AI-matched candidates for an employer's job (identity from token)."""
    try:
        employer_phone = caller_phone(request)
        db = get_db()
        try:
            if job_id:
                job = db.query(Job).filter_by(job_id=job_id, company_id=employer_phone).first()
            else:
                job = db.query(Job).filter_by(company_id=employer_phone).order_by(Job.created_at.desc()).first()

            if not job:
                return JSONResponse({"status": "success", "candidates": []}, headers={"Access-Control-Allow-Origin": "*"})

            already_applied_users = {
                a.user_id for a in
                db.query(JobApplication.user_id).filter_by(job_id=job.job_id).all()
            }

            candidates = switch_matching_service.find_matching_candidates(job, limit=20)
            result = []
            for c in candidates:
                if c.phone in already_applied_users:
                    continue
                result.append({
                    "phone": c.phone,
                    "name": c.name,
                    "photo": _photo_api_path(c.phone) if c.photo_url else None,
                    "experience": c.experience_level,
                    "location": c.area,
                    "roles": c.preferred_roles,
                    "languages": c.languages,
                })
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "job_id": job.job_id,
            "job_title": job.title,
            "candidates": result,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[SWITCH] Error matched candidates: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class EmployerInterestRequest(BaseModel):
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    employer_phone: Optional[str] = None
    job_id: str
    candidate_phone: str


@router.post("/employer/express-interest")
async def employer_express_interest(payload: EmployerInterestRequest, http_request: Request):
    """Employer swipes right on a candidate — creates reverse-match application."""
    try:
        # Employer identity is attested by the bearer token; we still write
        # nothing about the employer onto the JobApplication row because ownership
        # is derived from the Job's company_id. The token is the authorization.
        _ = caller_phone(http_request)
        db = get_db()
        try:
            existing = db.query(JobApplication).filter_by(
                user_id=payload.candidate_phone,
                job_id=payload.job_id,
            ).first()
            if existing:
                return JSONResponse({"status": "already_exists", "application_id": existing.id},
                                    headers={"Access-Control-Allow-Origin": "*"})

            job = db.query(Job).filter_by(job_id=payload.job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            salary_str = ""
            if job.salary_min and job.salary_max:
                salary_str = f"₹{job.salary_min} - ₹{job.salary_max}"
            elif job.salary_min:
                salary_str = f"₹{job.salary_min}"

            app = JobApplication(
                user_id=payload.candidate_phone,
                job_id=payload.job_id,
                company=job.company,
                role=job.title,
                salary=salary_str,
                location=job.location,
                logo=job.logo or "",
                applied_date=time.strftime("%Y-%m-%d"),
                status="employer_interested",
                initiated_by="employer",
                created_at=time.time(),
                expires_at=time.time() + 86400,
                status_history=json.dumps([{"status": "employer_interested", "at": time.time()}]),
            )
            db.add(app)
            db.commit()

            app_id = app.id
            candidate_phone = payload.candidate_phone

            def _notify_candidate(phone=candidate_phone, j=job):
                try:
                    from services.employer_match_service import _normalize_wa_phone, _send_via_switch
                    from utils.whatsapp.components import MsgComponents
                    wa_phone = _normalize_wa_phone(phone)
                    message = (
                        f"एक कंपनी को आपकी profile पसंद आई!\n\n"
                        f"पद: {j.title}\n"
                        f"कंपनी: {j.company}\n"
                        f"वेतन: {salary_str or 'बातचीत से तय'}\n\n"
                        f"ऐप खोलो और Accept करो: https://app.switchlocally.com/?employer_interest={app_id}"
                    )
                    payload = MsgComponents.text_scaffold(to=wa_phone, text=message)
                    _send_via_switch(payload)
                except Exception as exc:
                    print(f"[SWITCH] Error notifying candidate of interest: {exc}")

            threading.Thread(target=_notify_candidate, daemon=True).start()

        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "application_id": app_id,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error express interest: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class AcceptInterestRequest(BaseModel):
    application_id: int
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    user_id: Optional[str] = None


@router.post("/employer/accept-interest")
async def accept_employer_interest(payload: AcceptInterestRequest, http_request: Request):
    """Candidate accepts employer interest — becomes a match."""
    try:
        user_id = caller_phone(http_request)
        db = get_db()
        try:
            app = db.query(JobApplication).filter_by(id=payload.application_id, user_id=user_id).first()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")
            if app.status == "matched":
                return JSONResponse({"status": "already_matched"}, headers={"Access-Control-Allow-Origin": "*"})

            app.status = "matched"
            app.matched_at = time.time()
            _append_status_history(app, "matched")
            db.commit()

            job_id = app.job_id

            def _notify_employer(jid=job_id, uid=user_id):
                try:
                    ndb = get_db()
                    try:
                        job = ndb.query(Job).filter_by(job_id=jid).first()
                        user = ndb.query(User).filter_by(phone=uid).first()
                        if job and user:
                            send_employer_whatsapp(app.match_token or "", job, user)
                    finally:
                        ndb.close()
                except Exception as exc:
                    print(f"[SWITCH] Error notifying employer of acceptance: {exc}")

            threading.Thread(target=_notify_employer, daemon=True).start()

        finally:
            db.close()

        return JSONResponse({"status": "success", "new_status": "matched"}, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error accept interest: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INTERVIEW FLOW ====================

class InterviewScheduleRequest(BaseModel):
    application_id: int
    datetime: str
    location: str


@router.post("/interview/schedule")
async def schedule_interview(request: InterviewScheduleRequest):
    """Employer sets interview time + location."""
    try:
        db = get_db()
        try:
            app = db.query(JobApplication).filter_by(id=request.application_id).first()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")

            app.interview_datetime = request.datetime
            app.interview_location = request.location
            app.status = "interview"
            _append_status_history(app, "interview")
            db.commit()

            user_id = app.user_id
            job_id = app.job_id
            dt = request.datetime
            loc = request.location

            app_id = app.id

            def _notify(uid=user_id, jid=job_id, when=dt, where=loc, aid=app_id):
                try:
                    ndb = get_db()
                    try:
                        job = ndb.query(Job).filter_by(job_id=jid).first()
                    finally:
                        ndb.close()
                    job_title = job.title if job else "Job"
                    company = job.company if job else "Company"
                    notify_user(
                        uid,
                        Content(
                            type="interview",
                            title="Interview scheduled: {role} at {company}",
                            body="{when} • {location}",
                            url="/app/interviews/{application_id}",
                        ),
                        params={
                            "role": job_title,
                            "company": company,
                            "when": when,
                            "location": where,
                            "application_id": aid,
                        },
                        extra_data={"application_id": aid},
                        idempotency_key=f"interview:{aid}",
                    )
                    if job:
                        notify_candidate_interview(uid, job, when, where)
                except Exception as exc:
                    print(f"[SWITCH] Error scheduling interview notification: {exc}")

            threading.Thread(target=_notify, daemon=True).start()

        finally:
            db.close()

        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SWITCH] Error schedule interview: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class InterviewConfirmRequest(BaseModel):
    application_id: int


@router.post("/interview/confirm")
async def confirm_interview(request: InterviewConfirmRequest):
    """Candidate confirms they will attend the interview."""
    try:
        db = get_db()
        try:
            app = db.query(JobApplication).filter_by(id=request.application_id).first()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")
            app.interview_confirmed = True
            _append_status_history(app, "interview_confirmed")
            db.commit()
        finally:
            db.close()
        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class InterviewOutcomeRequest(BaseModel):
    application_id: int
    outcome: str  # 'hired', 'rejected', 'no_show'


@router.post("/interview/outcome")
async def interview_outcome(request: InterviewOutcomeRequest):
    """Record the outcome of the interview."""
    try:
        db = get_db()
        try:
            app = db.query(JobApplication).filter_by(id=request.application_id).first()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")

            app.interview_outcome = request.outcome
            if request.outcome == "hired":
                app.status = "hired"
            _append_status_history(app, request.outcome)
            db.commit()

            if request.outcome == "hired":
                user_id = app.user_id
                job_id = app.job_id
                app_id = app.id
                created_at = app.created_at

                def _celebrate(uid=user_id, jid=job_id, aid=app_id, created=created_at):
                    try:
                        ndb = get_db()
                        try:
                            job = ndb.query(Job).filter_by(job_id=jid).first()
                        finally:
                            ndb.close()
                        hours = int((time.time() - created) / 3600) if created else 0
                        company = job.company if job else "Company"
                        notify_user(
                            uid,
                            Content(
                                type="hired",
                                title="You're hired!",
                                body="{company} hired you{duration}",
                                url="/app/applications/{application_id}",
                            ),
                            params={
                                "company": company,
                                "duration": f" in {hours}h" if hours else "",
                                "application_id": aid,
                            },
                            extra_data={"application_id": aid},
                            idempotency_key=f"hired:{aid}",
                        )
                    except Exception as exc:
                        print(f"[SWITCH] Error hired notification: {exc}")

                threading.Thread(target=_celebrate, daemon=True).start()

        finally:
            db.close()

        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== NOTIFICATIONS ====================

@router.get("/notifications")
async def get_notifications(request: Request):
    """Get all notifications for the calling user (identity from token), newest first."""
    user_id = caller_phone(request)
    try:
        db = get_db()
        try:
            notifs = db.query(Notification).filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(50).all()
            result = [{
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "read": n.read,
                "created_at": n.created_at,
            } for n in notifs]
            unread = sum(1 for n in notifs if not n.read)
        finally:
            db.close()

        return JSONResponse({
            "status": "success",
            "notifications": result,
            "unread": unread,
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int):
    """Mark a single notification as read."""
    try:
        db = get_db()
        try:
            n = db.query(Notification).filter_by(id=notification_id).first()
            if n:
                n.read = True
                db.commit()
        finally:
            db.close()
        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HELPERS ====================

def _append_status_history(app: JobApplication, new_status: str):
    """Append a status entry to the application's status_history JSON."""
    try:
        history = json.loads(app.status_history or "[]")
    except (json.JSONDecodeError, TypeError):
        history = []
    history.append({"status": new_status, "at": time.time()})
    app.status_history = json.dumps(history)


def _create_notification(db, user_id: str, ntype: str, title: str, body: str, data: str = "{}"):
    """Insert a notification row."""
    n = Notification(
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        data=data,
        created_at=time.time(),
    )
    db.add(n)
    db.commit()


# ==================== EMPLOYER PROFILE PERSISTENCE ====================


@router.get("/employer/profile")
async def get_employer_profile(request: Request):
    """Retrieve the calling employer's profile (identity from token)."""
    try:
        phone = caller_phone(request)
        db = get_db()
        try:
            profile = db.query(EmployerProfile).filter_by(phone=phone).first()
            if not profile:
                return JSONResponse({"found": False}, headers={"Access-Control-Allow-Origin": "*"})
            return JSONResponse({
                "found": True,
                "profile": {
                    "phone": profile.phone,
                    "company": profile.company,
                    "business_type": profile.business_type,
                    "location": profile.location,
                    "interview_location": profile.interview_location,
                    "lat": profile.lat,
                    "lng": profile.lng,
                },
            }, headers={"Access-Control-Allow-Origin": "*"})
        finally:
            db.close()
    except Exception as e:
        print(f"[SWITCH] Error get employer profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class EmployerProfileUpdate(BaseModel):
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    phone: Optional[str] = None
    company: str = ""
    business_type: str = ""
    location: str = ""
    interview_location: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None


@router.put("/employer/profile")
async def upsert_employer_profile(body: EmployerProfileUpdate, request: Request):
    """Create or update the calling employer's profile (identity from token)."""
    try:
        phone = caller_phone(request)
        lat = body.lat
        lng = body.lng
        location_changed = False

        db = get_db()
        try:
            profile = db.query(EmployerProfile).filter_by(phone=phone).first()
            if profile:
                if body.company:
                    profile.company = body.company
                if body.business_type:
                    profile.business_type = body.business_type
                if body.location and body.location != profile.location:
                    profile.location = body.location
                    location_changed = True
                elif body.location:
                    profile.location = body.location
                if body.interview_location is not None:
                    profile.interview_location = body.interview_location
                if lat is not None and lng is not None:
                    profile.lat = lat
                    profile.lng = lng
                elif location_changed:
                    profile.lat = None
                    profile.lng = None
                profile.updated_at = time.time()
            else:
                profile = EmployerProfile(
                    phone=phone,
                    company=body.company,
                    business_type=body.business_type,
                    location=body.location,
                    interview_location=body.interview_location,
                    lat=lat,
                    lng=lng,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(profile)
                if not lat and body.location:
                    location_changed = True
            db.commit()
        finally:
            db.close()

        if location_changed and lat is None:
            async def _geocode_profile():
                try:
                    coords = await geocode_location(body.location)
                    if coords:
                        gdb = get_db()
                        try:
                            p = gdb.query(EmployerProfile).filter_by(phone=phone).first()
                            if p:
                                p.lat = coords[0]
                                p.lng = coords[1]
                                p.updated_at = time.time()
                                gdb.commit()
                                print(f"[SWITCH] Geocoded employer {phone}: {coords}")
                        finally:
                            gdb.close()
                except Exception as e:
                    print(f"[SWITCH] Geocode error for employer {phone}: {e}")
            asyncio.create_task(_geocode_profile())

        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"[SWITCH] Error upsert employer profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/coach")
async def switch_coach(request: Request):
    """AI Coach for Switch workers - streams Claude responses"""
    try:
        body = await request.json()
        message = body.get("message", "")
        job_context = body.get("job_context", "")

        if not message:
            return JSONResponse({"error": "Message required"}, headers={"Access-Control-Allow-Origin": "*"})

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return JSONResponse({"error": "API key not configured"}, headers={"Access-Control-Allow-Origin": "*"})

        client = anthropic.AsyncAnthropic(api_key=api_key)

        system_prompt = """You are Switch Coach, a friendly AI assistant for blue-collar workers in India.

Your role:
- Help workers learn their jobs (warehouses, restaurants, security, delivery, retail)
- Give interview preparation tips
- Explain SOPs and daily tasks
- Motivate workers to improve their skills and reputation score
- Guide career growth

Communication style:
- Use simple Hinglish (Hindi + English mix) - easy to understand
- Keep responses SHORT (2-4 sentences max unless explaining something complex)
- Be encouraging and practical
- Use emojis occasionally
- Never use complex English words

Examples of good responses:
"Bilkul! Warehouse mein picking ke liye barcode scan karna bahut zaroori hai. Har item scan karo - skip mat karo. Isse accuracy 100% rahegi aur aapki rating badhegi! 📦"

"Interview mein: time par aao, saaf kapde pehno, haath milate waqt smile karo. Bolo - 'Main mehnat karne ke liye ready hoon aur sikhne mein interested hoon.' Simple aur honest raho! 💪"
"""

        if job_context:
            system_prompt += f"\n\nWorker's current job context: {job_context}"

        async def generate():
            try:
                async with client.messages.stream(
                    model="claude-sonnet-4-6",
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": message}]
                ) as stream:
                    async for text in stream.text_stream:
                        yield f"data: {json.dumps({'text': text})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"[SWITCH] Coach stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        print(f"[SWITCH] Coach error: {e}")
        return JSONResponse({"error": str(e)}, headers={"Access-Control-Allow-Origin": "*"})




@router.post("/jyoti-call")
async def jyoti_interview_call(request: Request):
    """Trigger Jyoti AI call to worker for interview prep (identity from token)."""
    try:
        user_id = caller_phone(request)
        body = await request.json()
        job_role = body.get("job_role", "General")
        training_completed = body.get("training_completed", False)

        # Call goes to the caller's own phone (12-digit 91-prefixed form from token).
        phone_digits = user_id
        phone_number = phone_digits

        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        elevenlabs_phone_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")

        if not elevenlabs_api_key or not elevenlabs_agent_id or not elevenlabs_phone_id:
            return JSONResponse({"error": "Call service not configured"}, headers={"Access-Control-Allow-Origin": "*"})

        from elevenlabs import ConversationInitiationClientDataRequestInput, ElevenLabs
        elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

        # Get user data
        user_data = {}
        try:
            user_doc = fs.collection("switch_users").document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
        except:
            pass

        elevenlabs_client.conversational_ai.twilio.outbound_call(
            agent_id=elevenlabs_agent_id,
            agent_phone_number_id=elevenlabs_phone_id,
            to_number=phone_digits,
            conversation_initiation_client_data=ConversationInitiationClientDataRequestInput(
                user_id=user_id,
                dynamic_variables={
                    "name": user_data.get("name", ""),
                    "uid": user_id,
                    "user_type": "job_seeker",
                    "connection_type": "jyoti_interview_prep",
                    "job_role": job_role,
                    "training_completed": str(training_completed),
                    "primary_goal": f"Interview preparation for {job_role}",
                },
            ),
        )

        # Notify admin on WhatsApp
        admin_phone = "918368828660"
        user_name = user_data.get("name", "Unknown")
        user_location = user_data.get("location", "Unknown")
        try:
            from utils.whatsapp.components import MsgComponents
            from services.employer_match_service import _send_via_switch
            admin_msg = (
                f"🎯 *New Jyoti Interview Call*\n\n"
                f"Worker: {user_name}\nPhone: {phone_number}\n"
                f"Location: {user_location}\nJob Role: {job_role}\n"
                f"Training Done: {'✅' if training_completed else '❌'}\n\n"
                f"_Book Rapido for interview when confirmed_"
            )
            payload = MsgComponents.text_scaffold(to=admin_phone, text=admin_msg)
            _send_via_switch(payload)
        except Exception as wa_err:
            print(f"[JYOTI] WhatsApp notify error: {wa_err}")

        # Save call record
        try:
            fs.collection("jyoti_calls").document(f"{user_id}_{int(time.time())}").set({
                "user_id": user_id,
                "phone": phone_number,
                "job_role": job_role,
                "training_completed": training_completed,
                "status": "initiated",
                "created_at": time.time(),
            })
        except:
            pass

        return JSONResponse(
            {"status": "success", "message": "Jyoti will call you shortly!"},
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500, headers={"Access-Control-Allow-Origin": "*"})




from fastapi.responses import RedirectResponse

@router.get("/r/{campaign}")
async def sms_click_redirect(campaign: str, p: str = ""):
    """Log SMS link click then redirect to destination."""
    dest = "https://app.switchlocally.com?iti=1"
    try:
        with get_db() as db:
            row = db.query(SmsClick).filter(SmsClick.phone == p, SmsClick.campaign == campaign).first()
            if row and row.clicked_at is None:
                row.clicked_at = time.time()
                db.commit()
    except Exception as e:
        print(f"[SMS_CLICK] log error: {e}")
    return RedirectResponse(url=dest, status_code=302)


# ── JOB BLAST ────────────────────────────────────────────────────────────────

_active_blasts: dict = {}  # blast_id -> blast dict

_ROLE_KEYWORDS = {
    "cook": ["cook", "chef"],
    "cook/chef": ["cook", "chef"],
    "cook / chef": ["cook", "chef"],
    "housekeeping": ["housekeeping", "housekeeper"],
    "cleaner / office boy": ["cleaner", "office", "sweeper"],
    "security guard": ["security", "guard"],
    "helper": ["helper", "labour", "labor"],
    "warden": ["warden"],
    "receptionist": ["receptionist", "front desk"],
    "supervisor": ["supervisor"],
    "waiter / server": ["waiter", "server", "steward"],
    "delivery rider": ["delivery", "rider"],
}


def _role_keywords_for(role: str) -> list:
    return _ROLE_KEYWORDS.get(role.lower(), [role.lower().split()[0]])


def _worker_matches_role(preferred_roles_json: str, role: str) -> bool:
    try:
        roles = json.loads(preferred_roles_json) if preferred_roles_json else []
    except Exception:
        roles = []
    roles_str = " ".join(r.lower() for r in roles)
    return any(kw in roles_str for kw in _role_keywords_for(role))


class BlastCreateRequest(BaseModel):
    role: str
    location: str
    time: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    openings: Optional[int] = 1
    # DEPRECATED: candidate for deletion — caller identity is sourced from the bearer token.
    employer_phone: Optional[str] = None


@router.post("/blast")
async def create_blast(payload: BlastCreateRequest, http_request: Request):
    employer_phone = caller_phone(http_request)
    blast_id = str(uuid.uuid4())
    blast = {
        "id": blast_id,
        "role": payload.role,
        "location": payload.location,
        "time": payload.time,
        "salary_min": payload.salary_min,
        "salary_max": payload.salary_max,
        "openings": payload.openings,
        "employer_phone": employer_phone,
        "created_at": time.time(),
        "expires_at": time.time() + 300,
        "responses": {},
        "notified": [],
    }
    _active_blasts[blast_id] = blast

    def _notify():
        try:
            with get_db() as db:
                workers = db.query(User).filter(
                    User.phone.isnot(None),
                    User.phone != "",
                    User.is_available.is_(True),
                ).all()
                targets = [
                    w for w in workers
                    if _worker_matches_role(w.preferred_roles or "[]", payload.role)
                ]
                print(f"[BLAST] Notifying {len(targets)} workers for '{payload.role}'")
                for w in targets[:300]:
                    try:
                        send_blast_to_worker(w.phone, payload.role, payload.location, payload.time or "9:00 AM")
                        blast["notified"].append(w.phone)
                    except Exception as e:
                        print(f"[BLAST] WA failed {w.phone}: {e}")
        except Exception as e:
            print(f"[BLAST] notify error: {e}")
            traceback.print_exc()

    threading.Thread(target=_notify, daemon=True).start()
    return JSONResponse({"blast_id": blast_id, "status": "sent"})


@router.get("/blast/active")
async def get_active_blast(request: Request):
    worker_phone = caller_phone(request)
    now = time.time()
    expired = [bid for bid, b in _active_blasts.items() if b["expires_at"] < now]
    for bid in expired:
        del _active_blasts[bid]
    for blast in _active_blasts.values():
        if worker_phone in blast["responses"]:
            continue
        return JSONResponse({k: v for k, v in blast.items() if k != "notified"})
    return JSONResponse(None)


@router.post("/blast/{blast_id}/respond")
async def respond_to_blast(blast_id: str, request: Request):
    if blast_id not in _active_blasts:
        raise HTTPException(404, "Blast not found")
    worker_phone = caller_phone(request)
    body = await request.json()
    response = body.get("response")
    blast = _active_blasts[blast_id]
    blast["responses"][worker_phone] = response

    if response == "accepted":
        def _notify_accept():
            try:
                worker_name = "Worker"
                try:
                    with get_db() as db:
                        u = db.query(User).filter_by(phone=worker_phone).first()
                        if u:
                            worker_name = u.name or "Worker"
                except Exception:
                    pass
                if blast.get("employer_phone"):
                    notify_employer_blast_accepted(
                        blast["employer_phone"], worker_name, worker_phone,
                        blast["role"], blast["location"]
                    )
                send_blast_confirmation_to_worker(
                    worker_phone, blast["role"], blast["location"], blast.get("time", "9:00 AM")
                )
            except Exception as e:
                print(f"[BLAST] accept notify error: {e}")
        threading.Thread(target=_notify_accept, daemon=True).start()

    return JSONResponse({"status": "ok"})


@router.get("/blast/{blast_id}/stats")
async def blast_stats(blast_id: str):
    if blast_id not in _active_blasts:
        raise HTTPException(404, "Blast not found")
    responses = _active_blasts[blast_id]["responses"]
    accepted = sum(1 for v in responses.values() if v == "accepted")
    rejected = sum(1 for v in responses.values() if v == "rejected")
    notified = len(_active_blasts[blast_id].get("notified", []))
    return JSONResponse({"accepted": accepted, "rejected": rejected, "total": len(responses), "notified": notified})


@router.get("/sms-stats/{campaign}")
async def sms_stats(campaign: str):
    """Return sent/clicked counts for an SMS campaign."""
    try:
        with get_db() as db:
            rows = db.query(SmsClick).filter(SmsClick.campaign == campaign).all()
            total_sent = len(rows)
            total_clicked = sum(1 for r in rows if r.clicked_at is not None)
            return JSONResponse({
                "campaign": campaign,
                "sent": total_sent,
                "clicked": total_clicked,
                "click_rate": f"{round(total_clicked / total_sent * 100, 1)}%" if total_sent else "0%",
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── OTP (WhatsApp + Voice Call) ───────────────────────────────────────────────
_wa_otps: dict = {}  # phone → {otp, expires_at, attempts, speak_token}

SWITCH_WA_PHONE_ID = os.getenv("SWITCH_PHONE_NUMBER_ID", "937143829489912")
SWITCH_WA_TOKEN    = os.getenv("META_SYS_USER_TOKEN", "")


def _send_otp_via_template(to: str, otp: str) -> bool:
    """Send OTP using AUTHENTICATION template — bypasses 24-hour messaging window.
    Falls back to free text if the template is not yet registered."""
    url = f"https://graph.facebook.com/v21.0/{SWITCH_WA_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {SWITCH_WA_TOKEN}"}

    template_payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "switch_otp",
            "language": {"code": "en"},
            "components": [
                {"type": "BODY", "parameters": [{"type": "text", "text": otp}]},
                {
                    "type": "BUTTON",
                    "sub_type": "COPY_CODE",
                    "index": "0",
                    "parameters": [{"type": "COUPON_CODE", "coupon_code": otp}],
                },
            ],
        },
    }
    r = _otp_requests.post(url, json=template_payload, headers=headers, timeout=10)
    print(f"[WA_OTP] template send to {to}: {r.status_code} {r.text[:300]}")
    if r.status_code == 200:
        return True

    # Template not registered yet — fall back to free text (works within 24-hr window)
    if r.status_code in (400, 404) and "132001" in r.text:
        print(f"[WA_OTP] template 'switch_otp' not registered, falling back to text")
        fallback = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": f"*{otp}* is your Switch OTP. Valid for 5 minutes. Do not share."},
        }
        r2 = _otp_requests.post(url, json=fallback, headers=headers, timeout=10)
        print(f"[WA_OTP] fallback text send to {to}: {r2.status_code} {r2.text[:200]}")
        return r2.status_code == 200

    return False




@router.post("/send-whatsapp-otp")
async def send_whatsapp_otp(request: Request):
    try:
        body = await request.json()
        phone = str(body.get("phone", "")).strip().replace("+", "").replace(" ", "")
        if len(phone) == 10:
            phone = "91" + phone
        if not phone or len(phone) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number")

        otp = str(random.randint(100000, 999999))
        _wa_otps[phone] = {"otp": otp, "expires_at": time.time() + 300, "attempts": 0}

        ok = _send_otp_via_template(phone, otp)
        if not ok:
            raise HTTPException(status_code=500, detail="WhatsApp delivery failed")

        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-whatsapp-otp")
async def verify_whatsapp_otp(request: Request):
    try:
        body = await request.json()
        phone = str(body.get("phone", "")).strip().replace("+", "").replace(" ", "")
        if len(phone) == 10:
            phone = "91" + phone
        otp_input = str(body.get("otp", "")).strip()

        record = _wa_otps.get(phone)
        if not record:
            raise HTTPException(status_code=400, detail="OTP not found. Please request again.")
        if time.time() > record["expires_at"]:
            _wa_otps.pop(phone, None)
            raise HTTPException(status_code=400, detail="OTP expired. Please request again.")
        if record["attempts"] >= 5:
            _wa_otps.pop(phone, None)
            raise HTTPException(status_code=400, detail="Too many attempts. Please request a new OTP.")

        # 2factor.in voice/SMS OTP — verify via their API using the session_id
        if record.get("via") in ("2factor_voice", "2factor_sms"):
            twofactor_key = os.getenv("TWOFACTOR_API_KEY", "")
            session_id = record["otp"]
            verify_resp = _otp_requests.get(
                f"https://2factor.in/API/V1/{twofactor_key}/SMS/VERIFY/{session_id}/{otp_input}",
                timeout=10,
            )
            verify_result = verify_resp.json()
            print(f"[VERIFY_OTP] 2factor verify: {verify_result}")
            if verify_result.get("Status") != "Success" or verify_result.get("Details") != "OTP Matched":
                record["attempts"] += 1
                remaining = 5 - record["attempts"]
                raise HTTPException(status_code=400, detail=f"Wrong OTP. {remaining} attempts left.")
        else:
            if otp_input != record["otp"]:
                _wa_otps[phone]["attempts"] += 1
                remaining = 5 - _wa_otps[phone]["attempts"]
                raise HTTPException(status_code=400, detail=f"Wrong OTP. {remaining} attempts left.")

        _wa_otps.pop(phone, None)

        # Ensure user exists in DB
        with get_db() as db:
            user = db.query(User).filter_by(phone=phone).first()
            if not user:
                user = User(phone=phone, name="", verified=True, joined_date=time.strftime("%b %Y"), is_available=True, created_at=time.time(), updated_at=time.time())
                db.add(user)
                db.commit()

        return JSONResponse({"status": "success", "user_id": phone}, headers={"Access-Control-Allow-Origin": "*"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/call-otp")
async def send_call_otp(request: Request):
    """Send OTP via 2factor.in voice call."""
    try:
        body = await request.json()
        phone = str(body.get("phone", "")).strip().replace("+", "").replace(" ", "")
        if len(phone) == 10:
            phone = "91" + phone
        if not phone or len(phone) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number")

        twofactor_key = os.getenv("TWOFACTOR_API_KEY", "")
        if not twofactor_key:
            raise HTTPException(status_code=500, detail="OTP service not configured")

        # 2factor.in expects 10-digit number (strip country code)
        number_10 = phone[-10:]

        resp = _otp_requests.get(
            f"https://2factor.in/API/V1/{twofactor_key}/VOICE/{number_10}/AUTOGEN",
            timeout=10,
        )
        result = resp.json()
        print(f"[CALL_OTP] 2factor VOICE response for {number_10}: {result}")

        if result.get("Status") != "Success":
            raise HTTPException(status_code=500, detail="Call delivery failed")

        session_id = result.get("Details")
        _wa_otps[phone] = {"otp": session_id, "expires_at": time.time() + 300, "attempts": 0, "via": "2factor_voice"}

        return JSONResponse({"status": "success"}, headers={"Access-Control-Allow-Origin": "*"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CALL_OTP] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
