"""
SQLAlchemy ORM models for Switch app PostgreSQL database.
Replaces Firestore collections with relational tables.
"""

import json
import time

from sqlalchemy import Column, Text, Float, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(Text, primary_key=True)
    title = Column(Text, default="")
    company = Column(Text, default="")
    category = Column(Text, default="")
    location = Column(Text, default="")
    city = Column(Text, default="")
    salary_min = Column(Integer, default=0)
    salary_max = Column(Integer, default=0)
    openings = Column(Integer, default=0)
    job_type = Column(Text, default="Full Time")
    shift = Column(Text, default="")
    min_exp = Column(Integer, default=0)
    max_exp = Column(Integer, default=0)
    perks = Column(Text, default="")
    description = Column(Text, default="")
    requirements = Column(Text, default="[]")  # JSON list
    benefits = Column(Text, default="[]")  # JSON list
    logo = Column(Text, default="")
    phone = Column(Text, default="")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    job_url = Column(Text, default="")
    company_id = Column(Text, default="")
    created_at = Column(Float, default=time.time)

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "category": self.category,
            "location": self.location,
            "city": self.city,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "openings": self.openings,
            "job_type": self.job_type,
            "shift": self.shift,
            "min_exp": self.min_exp,
            "max_exp": self.max_exp,
            "perks": self.perks or "",
            "description": self.description or "",
            "requirements": json.loads(self.requirements) if self.requirements else [],
            "benefits": json.loads(self.benefits) if self.benefits else [],
            "logo": self.logo or "",
            "phone": self.phone or "",
            "lat": self.lat,
            "lng": self.lng,
        }


class User(Base):
    """Flattened switch_users document — profile fields are top-level columns."""
    __tablename__ = "users"

    phone = Column(Text, primary_key=True)
    name = Column(Text, default="")
    photo_url = Column(Text, nullable=True)
    location = Column(Text, default="")
    experience = Column(Text, default="")
    preferred_roles = Column(Text, default="[]")  # JSON list
    languages = Column(Text, default="[]")  # JSON list
    education = Column(Text, default="")
    referral_code = Column(Text, default="")
    is_available = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)
    joined_date = Column(Text, default="")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    referred_by = Column(Text, nullable=True)
    total_referral_earnings = Column(Integer, default=0)
    total_referrals = Column(Integer, default=0)
    gender = Column(Text, server_default="", default="")
    date_of_birth = Column(Text, server_default="", default="")
    expected_salary_min = Column(Integer, nullable=True)
    expected_salary_max = Column(Integer, nullable=True)
    previous_company = Column(Text, server_default="", default="")
    previous_role = Column(Text, server_default="", default="")
    work_duration = Column(Text, server_default="", default="")
    contacts_phones = Column(Text, server_default="[]", default="[]")  # JSON list of phone numbers from device contacts
    switch_priority = Column(Text, server_default="", default="")   # 'salary' | 'stay' | 'both'
    village = Column(Text, server_default="", default="")            # hometown / village name
    job_role = Column(Text, server_default="", default="")           # role key from PG onboarding
    acquisition_source = Column(Text, server_default="", default="")  # how user heard about Switch
    chowk_streak = Column(Integer, server_default="0", default=0)
    yogdaan_score = Column(Integer, server_default="0", default=0)
    # Switch placement & training state
    active_job_key = Column(Text, nullable=True)
    joining_date = Column(Text, nullable=True)
    joining_details = Column(Text, nullable=True)  # JSON dict
    checked_in = Column(Boolean, server_default="false", default=False)
    training_progress = Column(Text, server_default="'{}'", default="{}")  # JSON dict of completed module keys
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    job_id = Column(Text, nullable=False)
    company = Column(Text, default="")
    role = Column(Text, default="")
    salary = Column(Text, default="")
    location = Column(Text, default="")
    logo = Column(Text, default="")
    applied_date = Column(Text, default="")
    status = Column(Text, default="pending")
    call_scheduled = Column(Boolean, default=False)
    call_time = Column(Text, nullable=True)
    match_token = Column(Text, nullable=True, unique=True)
    employer_action = Column(Text, nullable=True)
    employer_action_at = Column(Float, nullable=True)
    created_at = Column(Float, default=time.time)
    # Phase 1: Match moment
    matched_at = Column(Float, nullable=True)
    employer_viewed_at = Column(Float, nullable=True)
    status_history = Column(Text, default="[]")
    expires_at = Column(Float, nullable=True)
    # Phase 4: Two-sided matching
    initiated_by = Column(Text, default="worker")
    # Phase 5: Interview flow
    interview_datetime = Column(Text, nullable=True)
    interview_location = Column(Text, nullable=True)
    interview_confirmed = Column(Boolean, default=False)
    interview_outcome = Column(Text, nullable=True)
    # Phase 6: Video KYC verification
    kyc_verified_at = Column(Float, nullable=True)
    kyc_photo_url = Column(Text, nullable=True)
    kyc_conversation_id = Column(Text, nullable=True)
    kyc_answers = Column(Text, nullable=True)
    kyc_video_url = Column(Text, nullable=True)
    kyc_transcript = Column(Text, nullable=True)
    kyc_structured = Column(Text, nullable=True)
    kyc_summary = Column(Text, nullable=True)
    kyc_agent_name = Column(Text, nullable=True)
    kyc_is_first = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "company": self.company,
            "role": self.role,
            "salary": self.salary,
            "location": self.location,
            "logo": self.logo,
            "appliedDate": self.applied_date,
            "status": self.status,
            "callScheduled": self.call_scheduled,
            "callTime": self.call_time,
            "matchToken": self.match_token,
            "matched_at": self.matched_at,
            "employer_viewed_at": self.employer_viewed_at,
            "status_history": self.status_history,
            "expires_at": self.expires_at,
            "initiated_by": self.initiated_by,
            "interview_datetime": self.interview_datetime,
            "interview_location": self.interview_location,
            "interview_confirmed": self.interview_confirmed,
            "interview_outcome": self.interview_outcome,
            "kyc_verified_at": self.kyc_verified_at,
            "kyc_photo_url": self.kyc_photo_url,
            "kyc_conversation_id": self.kyc_conversation_id,
            "kyc_video_url": self.kyc_video_url,
            "kyc_summary": self.kyc_summary,
            "kyc_structured": self.kyc_structured,
            "kyc_agent_name": self.kyc_agent_name,
            "application_id": self.id,
            "created_at": self.created_at,
        }


class OtpVerification(Base):
    __tablename__ = "otp_verifications"

    phone = Column(Text, primary_key=True)
    otp = Column(Text, nullable=False)
    expires_at = Column(Float, nullable=False)
    attempts = Column(Integer, default=0)
    created_at = Column(Float, default=time.time)


class Session(Base):
    __tablename__ = "sessions"

    token = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    created_at = Column(Float, default=time.time)
    expires_at = Column(Float, nullable=False)


class CommunityPost(Base):
    __tablename__ = "community_posts"

    post_id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    text = Column(Text, default="")
    author_name = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=True)
    is_ai_generated = Column(Boolean, default=False)
    needs_ai_comments = Column(Boolean, default=True)
    theme = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)


class CommunityLike(Base):
    __tablename__ = "community_likes"

    like_id = Column(Text, primary_key=True)
    post_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),
    )


class CommunityComment(Base):
    __tablename__ = "community_comments"

    comment_id = Column(Text, primary_key=True)
    post_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    text = Column(Text, default="")
    author_name = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=True)
    is_ai_generated = Column(Boolean, default=False)
    created_at = Column(Float, default=time.time)


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_phone = Column(Text, nullable=False)
    referee_user_id = Column(Text, nullable=False)
    referee_name = Column(Text, default="")
    referred_at = Column(Float, default=time.time)
    status = Column(Text, default="signed_up")
    earnings = Column(Integer, default=0)


class UserProfile(Base):
    """user_profiles collection — for candidate profile management."""
    __tablename__ = "user_profiles"

    phone = Column(Text, primary_key=True)
    name = Column(Text, default="")
    extraction_data = Column(Text, default="{}")  # JSON dict
    role = Column(Text, default="")
    years = Column(Text, default="")
    company = Column(Text, default="")
    location = Column(Text, default="")
    work_arrangement = Column(Text, default="")
    salary_range = Column(Text, default="")
    open_to_relocate = Column(Text, default="")
    notice_period = Column(Text, default="")
    skills = Column(Text, default="[]")  # JSON list
    available_to_chat = Column(Boolean, default=True)
    profile_photo = Column(Text, nullable=True)
    links = Column(Text, default="[]")  # JSON list
    prompts = Column(Text, default="[]")  # JSON list
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class Candidate(Base):
    __tablename__ = "candidates"

    phone = Column(Text, primary_key=True)
    name = Column(Text, default="")
    photo_url = Column(Text, nullable=True)
    aadhaar_number = Column(Text, nullable=True)
    area = Column(Text, default="")
    preferred_areas = Column(Text, default="[]")  # JSON list
    experience_level = Column(Text, default="")
    previous_roles = Column(Text, default="[]")  # JSON list
    previous_employers = Column(Text, default="[]")  # JSON list
    expected_salary_min = Column(Integer, default=0)
    expected_salary_max = Column(Integer, default=0)
    languages = Column(Text, default="[]")  # JSON list
    availability = Column(Text, default="Immediate")
    status = Column(Text, default="AVAILABLE")
    profile_completeness_score = Column(Integer, default=0)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class SwipeEvent(Base):
    __tablename__ = "swipe_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    job_id = Column(Text, nullable=False)
    direction = Column(Text, nullable=False)  # "left" or "right"
    created_at = Column(Float, default=time.time)


class EmployerCall(Base):
    __tablename__ = "employer_calls"

    execution_id = Column(Text, primary_key=True)
    job_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False)
    employer_phone = Column(Text, default="")
    status = Column(Text, default="queued")
    created_at = Column(Float, default=time.time)


class DeliveryDocument(Base):
    __tablename__ = "delivery_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    job_id = Column(Text, nullable=False)
    doc_type = Column(Text, nullable=False)  # aadhaar_front, aadhaar_back, pan, driving_license, vehicle_rc, bank_details
    doc_data = Column(Text, nullable=False)  # base64 data URL
    file_size = Column(Integer, default=0)
    status = Column(Text, default="uploaded")
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "doc_type", name="uq_user_job_doctype"),
    )


class DeliveryApplication(Base):
    __tablename__ = "delivery_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    job_id = Column(Text, nullable=False)
    brand = Column(Text, default="")
    company = Column(Text, default="")
    role = Column(Text, default="")
    status = Column(Text, default="documents_pending")  # documents_pending → documents_complete
    docs_uploaded = Column(Integer, default=0)
    total_docs_required = Column(Integer, default=6)
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_delivery_user_job"),
    )


class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    phone = Column(Text, primary_key=True)
    company = Column(Text, default="")
    business_type = Column(Text, default="")
    location = Column(Text, default="")
    interview_location = Column(Text, default="")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    data = Column(Text, default="{}")
    read = Column(Boolean, default=False)
    created_at = Column(Float, default=time.time)


class FcmToken(Base):
    __tablename__ = "fcm_tokens"

    token = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False, index=True)
    phone = Column(Text, nullable=True, index=True)
    role = Column(Text, default="worker")
    platform = Column(Text, default="web")
    created_at = Column(Float, default=time.time)
    last_seen_at = Column(Float, default=time.time)
    disabled_at = Column(Float, nullable=True)


class Placement(Base):
    """Full placement pipeline tracker: match → interview → check-in → payment → attendance."""
    __tablename__ = "placements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, nullable=False)
    user_id = Column(Text, nullable=False)
    job_id = Column(Text, nullable=False)
    employer_phone = Column(Text, default="")
    company = Column(Text, default="")
    role = Column(Text, default="")
    status = Column(Text, default="matched")
    interview_invite_sent_at = Column(Float, nullable=True)
    candidate_confirmed_at = Column(Float, nullable=True)
    admin_notified_at = Column(Float, nullable=True)
    checkin_token = Column(Text, nullable=True, unique=True)
    checkin_selfie = Column(Text, nullable=True)
    checkin_lat = Column(Float, nullable=True)
    checkin_lng = Column(Float, nullable=True)
    checkin_otp = Column(Text, nullable=True)
    checkin_at = Column(Float, nullable=True)
    checkin_location_verified = Column(Boolean, nullable=True)
    verify_token = Column(Text, nullable=True, unique=True)
    employer_verified_at = Column(Float, nullable=True)
    razorpay_order_id = Column(Text, nullable=True)
    razorpay_payment_id = Column(Text, nullable=True)
    payment_amount = Column(Integer, default=200000)
    payment_status = Column(Text, nullable=True)
    payment_at = Column(Float, nullable=True)
    first_day_checkin_token = Column(Text, nullable=True, unique=True)
    first_day_checkin_at = Column(Float, nullable=True)
    first_day_selfie = Column(Text, nullable=True)
    first_day_location_verified = Column(Boolean, nullable=True)
    joining_date = Column(Text, nullable=True)
    joining_time = Column(Text, nullable=True)          # "09:00 AM"
    joining_otp = Column(Text, nullable=True)           # 4-digit OTP for post-card flow
    backup_workers = Column(Text, default="[]")         # JSON list of backup worker phones
    replacement_batch = Column(Integer, default=0)      # -1 = replacement found
    evening_confirm_sent_at = Column(Float, nullable=True)
    morning_nudge_sent_at = Column(Float, nullable=True)
    enroute_check_sent_at = Column(Float, nullable=True)
    employer_notified_enroute_at = Column(Float, nullable=True)
    attendance_day_count = Column(Integer, default=0)
    candidate_bonus_status = Column(Text, default="pending")
    job_lat = Column(Float, nullable=True)
    job_lng = Column(Float, nullable=True)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "employer_phone": self.employer_phone,
            "company": self.company,
            "role": self.role,
            "status": self.status,
            "checkin_token": self.checkin_token,
            "checkin_otp": self.checkin_otp,
            "checkin_at": self.checkin_at,
            "checkin_location_verified": self.checkin_location_verified,
            "verify_token": self.verify_token,
            "employer_verified_at": self.employer_verified_at,
            "payment_status": self.payment_status,
            "payment_at": self.payment_at,
            "joining_date": self.joining_date,
            "attendance_day_count": self.attendance_day_count,
            "candidate_bonus_status": self.candidate_bonus_status,
            "created_at": self.created_at,
        }


class AttendanceCheckin(Base):
    """Daily attendance record for 30-day tracking."""
    __tablename__ = "attendance_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    placement_id = Column(Integer, nullable=False)
    user_id = Column(Text, nullable=False)
    day_number = Column(Integer, nullable=False)
    date = Column(Text, nullable=False)
    checkin_token = Column(Text, nullable=True, unique=True)
    selfie = Column(Text, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    location_verified = Column(Boolean, nullable=True)
    otp = Column(Text, nullable=True)
    employer_verified = Column(Boolean, default=False)
    status = Column(Text, default="pending")
    created_at = Column(Float, default=time.time)

    __table_args__ = (
        UniqueConstraint("placement_id", "date", name="uq_placement_date"),
    )


class PlacementPayment(Base):
    """Payment records for placement fees."""
    __tablename__ = "placement_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    placement_id = Column(Integer, nullable=False)
    employer_phone = Column(Text, default="")
    razorpay_order_id = Column(Text, nullable=True)
    razorpay_payment_id = Column(Text, nullable=True)
    amount = Column(Integer, default=200000)
    status = Column(Text, default="created")
    created_at = Column(Float, default=time.time)


class UPIPayment(Base):
    """UPI payment records for employer hiring-request fees (₹2,000 per hire)."""
    __tablename__ = "upi_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hiring_request_id = Column(Text, nullable=False, index=True)
    employer_phone = Column(Text, nullable=False)
    amount = Column(Integer, nullable=False)
    upi_link = Column(Text, nullable=False)
    payment_ref = Column(Text, nullable=False)
    status = Column(Text, default="pending")  # pending | awaiting_verification | verified | failed | duplicate
    employer_submitted_utr = Column(Text, nullable=True, unique=True)
    verified_at = Column(Float, nullable=True)
    verified_by = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time)


class CallerMemory(Base):
    """Per-caller memory built up across inbound calls — replaces Firestore switch_caller_memory."""
    __tablename__ = "caller_memory"

    phone = Column(Text, primary_key=True)   # 12-digit: 91XXXXXXXXXX
    name = Column(Text, default="")
    caller_type = Column(Text, default="candidate")
    total_calls = Column(Integer, default=0)
    first_call_at = Column(Float, nullable=True)
    last_call_at = Column(Float, nullable=True)
    last_conversation_summary = Column(Text, default="")
    known_details = Column(Text, default="{}")   # JSON dict
    profile = Column(Text, default="{}")         # JSON dict (structured candidate profile)
    last_jobs_pitched = Column(Text, default="[]")  # JSON list
    last_outcome = Column(Text, default="unknown")
    last_conversation_id = Column(Text, default="")
    updated_at = Column(Float, default=time.time)


class InboundCall(Base):
    """Inbound call record for every call to Jyoti's number — replaces Firestore calls collection."""
    __tablename__ = "inbound_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Text, default="", index=True)
    caller_number = Column(Text, default="", index=True)
    called_number = Column(Text, default="")
    vobiz_call_id = Column(Text, default="")
    caller_type = Column(Text, default="unknown")  # "candidate" | "unknown"
    status = Column(Text, default="initiated")     # "initiated" | "completed"
    duration_seconds = Column(Integer, nullable=True)
    hangup_cause = Column(Text, default="")
    created_at = Column(Float, default=time.time)


class PgCandidate(Base):
    """PG staffing inbound call — screened candidate record."""
    __tablename__ = "pg_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(Text, nullable=False, index=True)
    conversation_id = Column(Text, default="")
    call_id = Column(Text, default="")
    name = Column(Text, default="")
    city = Column(Text, default="")
    current_location = Column(Text, default="")
    currently_employed = Column(Boolean, nullable=True)
    current_employer = Column(Text, default="")
    experience_years = Column(Text, default="")
    interested_role = Column(Text, default="")
    salary_expectation = Column(Text, default="")
    joining_confirmed = Column(Boolean, default=False)
    joining_date = Column(Text, default="")       # "today" | "tomorrow" | "this_week"
    matched_pg_name = Column(Text, default="")
    matched_pg_location = Column(Text, default="")
    matched_salary = Column(Text, default="")
    sms_sent = Column(Boolean, default=False)
    created_at = Column(Float, default=time.time)


class SmsClick(Base):
    """Tracks SMS broadcast sends and link clicks for worker signup campaign."""
    __tablename__ = "sms_clicks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(Text, unique=True, nullable=False)
    phone = Column(Text, nullable=False)
    campaign = Column(Text, default="worker_signup")
    sent_at = Column(Float, nullable=True)
    clicked_at = Column(Float, nullable=True)
    signed_up = Column(Boolean, default=False)


class WaConversation(Base):
    """Per-user WhatsApp conversation history with Jyoti."""
    __tablename__ = "wa_conversations"

    phone = Column(Text, primary_key=True)
    messages = Column(Text, default="[]")  # JSON array of {role, content, ts}
    summary = Column(Text, default="")     # rolling summary after every 20 msgs
    updated_at = Column(Float, default=time.time)
    created_at = Column(Float, default=time.time)


class WaBlastLog(Base):
    """Tracks WhatsApp blast sends, delivery, reads and link clicks per user."""
    __tablename__ = "wa_blast_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign = Column(Text, nullable=False, index=True)
    phone = Column(Text, nullable=False, index=True)
    name = Column(Text, default="")
    wamid = Column(Text, nullable=True, unique=True)
    job_label = Column(Text, default="")
    click_token = Column(Text, nullable=True, unique=True, index=True)
    sent_at = Column(Float, nullable=True)
    delivered_at = Column(Float, nullable=True)
    read_at = Column(Float, nullable=True)
    clicked_at = Column(Float, nullable=True)
    failed = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    created_at = Column(Float, default=time.time)
