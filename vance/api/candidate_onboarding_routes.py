"""
API routes for candidate onboarding.
Handles phone signup, OTP verification, and resume upload.
"""

import json
import os
import re
import time
import random
import traceback

import pdfplumber
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional

from models.sql_models import (
    OtpVerification, User, UserProfile, Session as SessionModel,
    Candidate as CandidateModel,
)
from services.switch_screening_service import screening_service
from utils.postgres import get_db

import requests as _requests
import jwt as _pyjwt
from jwt.algorithms import RSAAlgorithm as _RSAAlgorithm

_GOOGLE_JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
_jwks_cache: dict = {}
_jwks_cached_at: float = 0

def _verify_firebase_token_jwks(id_token: str, project_id: str) -> dict:
    global _jwks_cache, _jwks_cached_at
    if not _jwks_cache or (time.time() - _jwks_cached_at) > 3600:
        resp = _requests.get(_GOOGLE_JWKS_URL, timeout=5)
        resp.raise_for_status()
        _jwks_cache = {k["kid"]: k for k in resp.json().get("keys", [])}
        _jwks_cached_at = time.time()
    header = _pyjwt.get_unverified_header(id_token)
    key_data = _jwks_cache.get(header.get("kid"))
    if not key_data:
        raise ValueError("No matching public key for token")
    public_key = _RSAAlgorithm.from_jwk(key_data)
    return _pyjwt.decode(
        id_token,
        public_key,
        algorithms=["RS256"],
        audience=project_id,
        issuer=f"https://securetoken.google.com/{project_id}",
    )

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials as firebase_credentials
    if not firebase_admin._apps:
        _cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "relay-15824-firebase-adminsdk-fbsvc-bc0efb42d8.json")
        firebase_admin.initialize_app(firebase_credentials.Certificate(_cred_path))
    FIREBASE_AVAILABLE = True
except Exception as _e:
    FIREBASE_AVAILABLE = False
    print(f"[ONBOARDING] Firebase Admin not available: {_e}")

try:
    _hearus_cred = None
    _hearus_src = None
    _raw_json = os.getenv("HEARUS_FIREBASE_CREDENTIALS_JSON", "").strip()
    _raw_b64 = os.getenv("HEARUS_FIREBASE_CREDENTIALS_BASE64", "").strip()
    if _raw_json:
        import json as _json
        _hearus_cred = firebase_credentials.Certificate(_json.loads(_raw_json))
        _hearus_src = "HEARUS_FIREBASE_CREDENTIALS_JSON"
    elif _raw_b64:
        import base64 as _b64
        import json as _json
        _hearus_cred = firebase_credentials.Certificate(_json.loads(_b64.b64decode(_raw_b64).decode("utf-8")))
        _hearus_src = "HEARUS_FIREBASE_CREDENTIALS_BASE64"
    else:
        _default_hearus_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hearus-4f2fe-firebase.json")
        _hearus_cred_path = os.getenv("HEARUS_FIREBASE_CREDENTIALS_PATH", _default_hearus_path)
        _hearus_cred = firebase_credentials.Certificate(_hearus_cred_path)
        _hearus_src = _hearus_cred_path
    _hearus_app = firebase_admin.initialize_app(_hearus_cred, name="hearus_phone_auth")
    print(f"[ONBOARDING] Initialized Firebase Admin app 'hearus_phone_auth' (src={_hearus_src}) for phone-auth ID token verification")
except ValueError:
    _hearus_app = firebase_admin.get_app("hearus_phone_auth")
    print("[ONBOARDING] Re-using existing 'hearus_phone_auth' Firebase Admin app")
except Exception as _e:
    _hearus_app = None
    print(f"[ONBOARDING] HearUs Firebase Admin app not available: {_e}")

try:
    from services.resume_number_extraction_service import resume_number_extraction_service
    RESUME_EXTRACTION_AVAILABLE = True
except ImportError:
    resume_number_extraction_service = None
    RESUME_EXTRACTION_AVAILABLE = False
    print("[ONBOARDING] Resume extraction service not available")

router = APIRouter(prefix="/api/candidate-onboarding", tags=["Candidate Onboarding"])




class PhoneSignupRequest(BaseModel):
    """Request model for phone number signup."""
    country_code: str
    phone: str


class OTPVerificationRequest(BaseModel):
    """Request model for OTP verification."""
    country_code: str
    phone: str
    otp: str


class ResumeUploadResponse(BaseModel):
    """Response model for resume upload."""
    status: str
    message: str
    user_id: str
    resume_url: str
    extracted_data: dict


# Fallback in-memory storage (for development)
_otp_storage: dict[str, dict] = {}


def store_otp(phone: str, otp: str, expires_at: float):
    """Store OTP in PostgreSQL."""
    try:
        db = get_db()
        try:
            existing = db.query(OtpVerification).filter_by(phone=phone).first()
            if existing:
                existing.otp = otp
                existing.expires_at = expires_at
                existing.attempts = 0
                existing.created_at = time.time()
            else:
                record = OtpVerification(
                    phone=phone,
                    otp=otp,
                    expires_at=expires_at,
                    attempts=0,
                    created_at=time.time(),
                )
                db.add(record)
            db.commit()
            print(f"[ONBOARDING] OTP stored for {phone}")
        finally:
            db.close()
    except Exception as e:
        print(f"[ONBOARDING] Failed to store OTP in DB: {e}")
        _otp_storage[phone] = {
            "otp": otp,
            "expires_at": expires_at,
            "attempts": 0,
        }


def get_otp(phone: str) -> dict | None:
    """Get OTP from PostgreSQL."""
    try:
        db = get_db()
        try:
            record = db.query(OtpVerification).filter_by(phone=phone).first()
            if record:
                return {
                    "otp": record.otp,
                    "expires_at": record.expires_at,
                    "attempts": record.attempts,
                }
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"[ONBOARDING] Failed to get OTP from DB: {e}")
        return _otp_storage.get(phone)


def update_otp_attempts(phone: str, attempts: int):
    """Update OTP attempts."""
    try:
        db = get_db()
        try:
            record = db.query(OtpVerification).filter_by(phone=phone).first()
            if record:
                record.attempts = attempts
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[ONBOARDING] Failed to update OTP attempts: {e}")


def delete_otp(phone: str):
    """Delete OTP record."""
    try:
        db = get_db()
        try:
            record = db.query(OtpVerification).filter_by(phone=phone).first()
            if record:
                db.delete(record)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[ONBOARDING] Failed to delete OTP: {e}")
        _otp_storage.pop(phone, None)


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))


def normalize_phone(country_code: str, phone: str) -> str:
    """Normalize phone number to standard format with country code."""
    country_code_clean = re.sub(r'[^\d+]', '', country_code)
    if country_code_clean.startswith('+'):
        country_code_clean = country_code_clean[1:]

    phone_clean = re.sub(r'[^\d]', '', phone)

    if country_code_clean:
        return country_code_clean + phone_clean
    elif len(phone_clean) == 10:
        return '91' + phone_clean
    else:
        return phone_clean


@router.post("/signup")
async def signup_with_phone(request: PhoneSignupRequest):
    """Sign up candidate with phone number and send OTP."""
    try:
        phone = normalize_phone(request.country_code, request.phone)

        if not phone or len(phone) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number")

        expires_at = time.time() + (5 * 60)

        e164_phone = f"+{phone}"

        if not e164_phone.startswith('+') or len(e164_phone) < 12:
            raise HTTPException(status_code=400, detail="Invalid phone number format. Please include country code.")

        twofactor_key = os.getenv("TWOFACTOR_API_KEY")
        if not twofactor_key:
            raise HTTPException(status_code=500, detail="SMS service not configured. Contact support.")

        # Phone for 2factor: 10-digit India number (strip country code 91)
        sms_number = phone[-10:] if len(phone) >= 10 else phone

        masked_phone = e164_phone[:4] + "****" + e164_phone[-4:] if len(e164_phone) > 8 else "****"
        print(f"[ONBOARDING] Sending OTP to {masked_phone}")

        try:
            resp = _requests.get(
                f"https://2factor.in/API/V1/{twofactor_key}/SMS/{sms_number}/AUTOGEN",
                timeout=10,
            )
            result = resp.json()
            print(f"[ONBOARDING] 2factor response: {result}")
            if result.get("Status") != "Success":
                raise Exception(result.get("Details", "SMS delivery failed"))
            # Store 2factor session ID as the OTP value for later verification
            session_id = result.get("Details")
            store_otp(phone, session_id, expires_at)
            print(f"[ONBOARDING] OTP sent to {masked_phone} via 2factor, session={session_id}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ONBOARDING] Failed to send SMS OTP: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to send OTP. Please try again. Error: {str(e)}")

        response = JSONResponse({
            "status": "success",
            "message": "OTP sent successfully",
            "phone": phone,
            "otp": None,
        })
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ONBOARDING] Error in signup: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing signup: {str(e)}")


@router.post("/verify-otp")
async def verify_otp(request: OTPVerificationRequest):
    """Verify OTP and create/update user."""
    try:
        phone = normalize_phone(request.country_code, request.phone)
        otp = request.otp.strip()

        otp_data = get_otp(phone)
        if not otp_data:
            raise HTTPException(status_code=400, detail="OTP session not found. Please request a new OTP.")

        if time.time() > otp_data.get("expires_at", 0):
            delete_otp(phone)
            raise HTTPException(status_code=400, detail="OTP expired. Please request a new OTP.")

        attempts = otp_data.get("attempts", 0)
        if attempts >= 3:
            delete_otp(phone)
            raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new OTP.")

        session_id = otp_data.get("otp")
        twofactor_key = os.getenv("TWOFACTOR_API_KEY")
        try:
            verify_resp = _requests.get(
                f"https://2factor.in/API/V1/{twofactor_key}/SMS/VERIFY/{session_id}/{otp}",
                timeout=10,
            )
            verify_result = verify_resp.json()
            print(f"[ONBOARDING] 2factor verify response: {verify_result}")
            if verify_result.get("Status") != "Success" or verify_result.get("Details") != "OTP Matched":
                attempts += 1
                update_otp_attempts(phone, attempts)
                raise HTTPException(status_code=400, detail=f"Invalid OTP. {3 - attempts} attempts remaining.")
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ONBOARDING] 2factor verify error: {e}")
            raise HTTPException(status_code=500, detail="OTP verification failed. Please try again.")

        print(f"[ONBOARDING] OTP verified for {phone}")

        user_id = phone

        db = get_db()
        try:
            # Ensure user exists in users table
            user = db.query(User).filter_by(phone=user_id).first()
            if not user:
                user = User(
                    phone=user_id,
                    name="",
                    verified=True,
                    joined_date=time.strftime("%b %Y"),
                    is_available=True,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(user)
                print(f"[ONBOARDING] Created new user: {user_id}")

            # Ensure user_profiles row exists
            profile = db.query(UserProfile).filter_by(phone=user_id).first()
            if not profile:
                profile = UserProfile(
                    phone=user_id,
                    name="",
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(profile)
                print(f"[ONBOARDING] Created user_profile for: {user_id}")

            # Generate session token
            session_token = f"session_{user_id}_{int(time.time())}"
            session = SessionModel(
                token=session_token,
                user_id=user_id,
                created_at=time.time(),
                expires_at=time.time() + (30 * 24 * 60 * 60),
            )
            db.add(session)
            db.commit()
        finally:
            db.close()

        delete_otp(phone)

        firebase_custom_token = None
        if FIREBASE_AVAILABLE:
            try:
                firebase_custom_token = firebase_auth.create_custom_token(user_id).decode("utf-8")
            except Exception as e:
                print(f"[ONBOARDING] Firebase custom token error: {e}")

        response = JSONResponse({
            "status": "success",
            "message": "OTP verified successfully",
            "user_id": user_id,
            "session_token": session_token,
            "firebase_custom_token": firebase_custom_token,
            "onboarding_stage": "resume_upload",
        })
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ONBOARDING] Error verifying OTP: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error verifying OTP: {str(e)}")


class FirebaseVerifyRequest(BaseModel):
    id_token: str


@router.post("/firebase-verify")
async def firebase_verify(request: FirebaseVerifyRequest):
    """Verify Firebase Phone Auth ID token and return session."""
    try:
        decoded = None
        if _hearus_app is not None:
            try:
                decoded = firebase_auth.verify_id_token(request.id_token, app=_hearus_app)
            except Exception:
                pass
        if decoded is None:
            try:
                decoded = _verify_firebase_token_jwks(request.id_token, "hearus-4f2fe")
            except Exception:
                pass
        if decoded is None and FIREBASE_AVAILABLE:
            decoded = firebase_auth.verify_id_token(request.id_token)
        if decoded is None:
            raise HTTPException(status_code=400, detail="Could not verify token.")
        phone_raw = decoded.get("phone_number", "")
        if not phone_raw:
            raise HTTPException(status_code=400, detail="No phone number in token.")

        phone = phone_raw.lstrip("+").replace(" ", "").replace("-", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone

        db = get_db()
        try:
            user = db.query(User).filter_by(phone=phone).first()
            is_new = user is None
            if not user:
                user = User(
                    phone=phone, name="", verified=True,
                    joined_date=time.strftime("%b %Y"), is_available=True,
                    created_at=time.time(), updated_at=time.time(),
                )
                db.add(user)

            profile = db.query(UserProfile).filter_by(phone=phone).first()
            if not profile:
                profile = UserProfile(phone=phone, name="", created_at=time.time(), updated_at=time.time())
                db.add(profile)

            session_token = f"session_{phone}_{int(time.time())}"
            db.add(SessionModel(
                token=session_token, user_id=phone,
                created_at=time.time(), expires_at=time.time() + (30 * 24 * 60 * 60),
            ))
            db.commit()
        finally:
            db.close()

        print(f"[ONBOARDING] Firebase verify OK: {phone} (new={is_new})")
        response = JSONResponse({
            "status": "success",
            "user_id": phone,
            "session_token": session_token,
            "is_new_user": is_new,
        })
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ONBOARDING] Firebase verify error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/upload-resume")
async def upload_resume(
    user_id: str = Form(...),
    session_token: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload resume and extract information."""
    try:
        # Verify session
        db = get_db()
        try:
            session = db.query(SessionModel).filter_by(token=session_token).first()
            if not session:
                raise HTTPException(status_code=401, detail="Invalid session")
            if session.user_id != user_id:
                raise HTTPException(status_code=401, detail="Session mismatch")
        finally:
            db.close()

        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        file_content = await file.read()

        resume_filename = f"{user_id}_{int(time.time())}_{file.filename}"
        resume_path = f"/tmp/resumes/{resume_filename}"
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)

        with open(resume_path, "wb") as f:
            f.write(file_content)

        print(f"[ONBOARDING] Resume saved: {resume_path}")

        try:
            extracted_numbers = None
            if RESUME_EXTRACTION_AVAILABLE and resume_number_extraction_service:
                try:
                    extracted_numbers = resume_number_extraction_service.extract_all_numbers(resume_path)
                except Exception as e:
                    print(f"[ONBOARDING] Error extracting numbers: {e}")

            resume_text = ""
            try:
                with pdfplumber.open(resume_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            resume_text += page_text + "\n"
            except Exception as e:
                print(f"[ONBOARDING] Error reading PDF: {e}")

            name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', resume_text[:200], re.MULTILINE)
            name = name_match.group(1) if name_match else None

            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text)
            email = email_match.group(0) if email_match else None

            linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', resume_text, re.IGNORECASE)
            linkedin = f"https://www.{linkedin_match.group(0)}" if linkedin_match else None

            extraction_data = {
                "name": name,
                "email": email,
                "linkedin_url": linkedin,
                "resume_path": resume_path,
                "resume_filename": file.filename,
                "resume_text": resume_text,
                "resume_uploaded_at": time.time(),
            }

            if extracted_numbers:
                numbers_dict = extracted_numbers.model_dump(exclude_none=True)
                extraction_data["resume_extracted_numbers"] = numbers_dict
                if numbers_dict.get("phone_number"):
                    extraction_data["phone_number"] = numbers_dict["phone_number"]

            # Update user profile with extraction data
            db = get_db()
            try:
                profile = db.query(UserProfile).filter_by(phone=user_id).first()
                if profile:
                    profile.extraction_data = json.dumps(extraction_data)
                    if name:
                        profile.name = name
                    profile.updated_at = time.time()
                else:
                    profile = UserProfile(
                        phone=user_id,
                        name=name or "",
                        extraction_data=json.dumps(extraction_data),
                        created_at=time.time(),
                        updated_at=time.time(),
                    )
                    db.add(profile)
                db.commit()
            finally:
                db.close()

            print(f"[ONBOARDING] Resume processed for {user_id}")

            response = JSONResponse({
                "status": "success",
                "message": "Resume uploaded and processed successfully",
                "user_id": user_id,
                "resume_url": resume_path,
                "extracted_data": {
                    "name": name,
                    "email": email,
                    "linkedin_url": linkedin,
                    "phone": extraction_data.get("phone_number"),
                    "experience": extracted_numbers.years_of_experience if extracted_numbers else None,
                },
            })
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response

        except Exception as e:
            print(f"[ONBOARDING] Error extracting resume data: {e}")
            traceback.print_exc()
            return {
                "status": "partial_success",
                "message": "Resume uploaded but extraction failed",
                "user_id": user_id,
                "resume_url": resume_path,
                "extracted_data": {},
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ONBOARDING] Error uploading resume: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error uploading resume: {str(e)}")


@router.get("/status/{user_id}")
async def get_onboarding_status(user_id: str):
    """Get onboarding status for a user."""
    try:
        db = get_db()
        try:
            profile = db.query(UserProfile).filter_by(phone=user_id).first()
            if not profile:
                response = JSONResponse({
                    "status": "not_started",
                    "stage": None,
                })
                response.headers["Access-Control-Allow-Origin"] = "*"
                return response

            extraction = json.loads(profile.extraction_data) if profile.extraction_data else {}
            has_resume = bool(extraction.get("resume_path"))
            stage = "complete" if has_resume else "resume_upload"
        finally:
            db.close()

        response = JSONResponse({
            "status": "complete" if stage == "complete" else "in_progress",
            "stage": stage,
            "has_resume": has_resume,
        })
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except Exception as e:
        print(f"[ONBOARDING] Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting onboarding status: {str(e)}")


@router.post("/complete-onboarding")
async def complete_onboarding(user_id: str, form_data: dict, background_tasks: BackgroundTasks):
    """Complete onboarding with full form data. Creates candidate record."""
    try:
        db = get_db()
        try:
            candidate = CandidateModel(
                phone=user_id,
                name=form_data.get("name", ""),
                photo_url=form_data.get("photo_url"),
                aadhaar_number=form_data.get("aadhaar_number"),
                area=form_data.get("area", ""),
                preferred_areas=json.dumps(form_data.get("preferred_areas", [])),
                experience_level=form_data.get("experience_level", ""),
                previous_roles=json.dumps(form_data.get("previous_roles", [])),
                previous_employers=json.dumps(form_data.get("previous_employers", [])),
                expected_salary_min=int(form_data.get("expected_salary_min", 0)),
                expected_salary_max=int(form_data.get("expected_salary_max", 0)),
                languages=json.dumps(form_data.get("languages", [])),
                availability=form_data.get("availability", "Immediate"),
                status="AVAILABLE",
                profile_completeness_score=100,
                created_at=time.time(),
                updated_at=time.time(),
            )

            existing = db.query(CandidateModel).filter_by(phone=user_id).first()
            if existing:
                db.delete(existing)
                db.flush()
            db.add(candidate)

            # Update switch user profile
            user = db.query(User).filter_by(phone=user_id).first()
            if user:
                user.name = form_data.get("name", "") or user.name
                user.photo_url = form_data.get("photo_url") or user.photo_url
                user.location = form_data.get("area", "") or user.location
                user.experience = form_data.get("experience_level", "") or user.experience
                user.preferred_roles = json.dumps(form_data.get("previous_roles", []))
                user.languages = json.dumps(form_data.get("languages", []))
                user.is_available = form_data.get("availability", "Immediate") == "Immediate"
                user.updated_at = time.time()

            db.commit()
        finally:
            db.close()

        background_tasks.add_task(screening_service.initiate_screening_call, user_id)

        return JSONResponse({
            "status": "success",
            "message": "Onboarding complete. We're calling you now for screening. Please pick up!",
            "candidate_id": user_id
        }, headers={"Access-Control-Allow-Origin": "*"})

    except Exception as e:
        print(f"[ONBOARDING] Error completing onboarding: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error completing onboarding: {str(e)}")
