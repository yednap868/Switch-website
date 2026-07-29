"""
Candidate Profile API Routes

Endpoints for candidates to:
- Get their profile data
- Update their profile data
"""

import json
import re
import time
import traceback
import base64

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from models.sql_models import UserProfile
from utils.hearus_auth import caller_phone
from utils.postgres import get_db, parse_json_col

router = APIRouter(prefix="/api/candidate-profile", tags=["Candidate Profile"])


class ProfileUpdateRequest(BaseModel):
    """Request model for profile updates."""
    name: Optional[str] = None
    role: Optional[str] = None
    years: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    workArrangement: Optional[str] = None
    salaryRange: Optional[str] = None
    openToRelocate: Optional[str] = None
    noticePeriod: Optional[str] = None
    skills: Optional[List[str]] = None
    availableToChat: Optional[bool] = None
    profilePhoto: Optional[str] = None
    links: Optional[List[Dict[str, Any]]] = None
    prompts: Optional[List[Dict[str, Any]]] = None


@router.get("")
async def get_profile(request: Request):
    """Get the calling candidate's profile (identity from token)."""
    try:
        user_id = caller_phone(request)
        db = get_db()
        try:
            profile = db.query(UserProfile).filter_by(phone=user_id).first()
            if not profile:
                print(f"[PROFILE_API] Profile not found for {user_id}, creating basic profile")
                profile = UserProfile(
                    phone=user_id,
                    name="",
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(profile)
                db.commit()

            extraction_data = json.loads(profile.extraction_data) if profile.extraction_data and profile.extraction_data != "{}" else {}

            name = profile.name or extraction_data.get("name") or ""
            role = extraction_data.get("target_role") or extraction_data.get("current_role") or profile.role or ""

            experience = extraction_data.get("work_experience") or extraction_data.get("years_of_experience") or profile.years or ""
            if isinstance(experience, (int, float)):
                years = f"{int(experience)} years" if experience else ""
            else:
                years = str(experience) if experience else ""

            company = extraction_data.get("current_company") or extraction_data.get("company") or profile.company or ""
            location = extraction_data.get("current_location") or profile.location or ""

            skills = extraction_data.get("skills") or extraction_data.get("technical_skills") or parse_json_col(profile.skills)
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]

            work_arrangement = extraction_data.get("work_arrangement") or profile.work_arrangement or ""
            salary_range = extraction_data.get("salary_range") or extraction_data.get("expected_salary") or profile.salary_range or ""
            open_to_relocate = extraction_data.get("open_to_relocate") or profile.open_to_relocate or ""
            notice_period = extraction_data.get("notice_period") or profile.notice_period or ""
            available_to_chat = profile.available_to_chat if profile.available_to_chat is not None else True

            profile_photo = profile.profile_photo or ""

            links = parse_json_col(profile.links)
            if isinstance(links, dict):
                converted_links = []
                for k, v in links.items():
                    if isinstance(v, dict):
                        converted_links.append({
                            "type": k,
                            "label": v.get("label", k),
                            "url": v.get("url", v.get("value", ""))
                        })
                    else:
                        converted_links.append({"type": k, "label": k, "url": str(v) if v else ""})
                links = converted_links

            prompts = parse_json_col(profile.prompts)
        finally:
            db.close()

        response_data = {
            "status": "success",
            "profile": {
                "name": name,
                "role": role,
                "years": years,
                "company": company,
                "location": location,
                "workArrangement": work_arrangement,
                "salaryRange": salary_range,
                "openToRelocate": open_to_relocate,
                "noticePeriod": notice_period,
                "skills": skills if isinstance(skills, list) else [],
                "availableToChat": available_to_chat,
                "profilePhoto": profile_photo,
                "links": links,
                "prompts": prompts,
            },
        }

        response = JSONResponse(response_data)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[PROFILE_API] Error getting profile: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting profile: {str(e)}")


@router.put("")
async def update_profile(payload: ProfileUpdateRequest, http_request: Request):
    """Update the calling candidate's profile (identity from token)."""
    try:
        user_id = caller_phone(http_request)
        db = get_db()
        try:
            profile = db.query(UserProfile).filter_by(phone=user_id).first()
            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")

            extraction_data = json.loads(profile.extraction_data) if profile.extraction_data and profile.extraction_data != "{}" else {}

            if payload.name is not None:
                extraction_data["name"] = payload.name
                profile.name = payload.name

            if payload.role is not None:
                extraction_data["target_role"] = payload.role
                extraction_data["current_role"] = payload.role
                profile.role = payload.role

            if payload.years is not None:
                years_match = re.search(r'(\d+)', str(payload.years))
                if years_match:
                    extraction_data["years_of_experience"] = int(years_match.group(1))
                extraction_data["work_experience"] = payload.years
                profile.years = payload.years

            if payload.company is not None:
                extraction_data["current_company"] = payload.company
                extraction_data["company"] = payload.company
                profile.company = payload.company

            if payload.location is not None:
                extraction_data["current_location"] = payload.location
                profile.location = payload.location

            if payload.workArrangement is not None:
                extraction_data["work_arrangement"] = payload.workArrangement
                profile.work_arrangement = payload.workArrangement

            if payload.salaryRange is not None:
                extraction_data["salary_range"] = payload.salaryRange
                extraction_data["expected_salary"] = payload.salaryRange
                profile.salary_range = payload.salaryRange

            if payload.openToRelocate is not None:
                extraction_data["open_to_relocate"] = payload.openToRelocate
                profile.open_to_relocate = payload.openToRelocate

            if payload.noticePeriod is not None:
                extraction_data["notice_period"] = payload.noticePeriod
                profile.notice_period = payload.noticePeriod

            if payload.skills is not None:
                extraction_data["skills"] = payload.skills
                extraction_data["technical_skills"] = payload.skills
                profile.skills = json.dumps(payload.skills)

            if payload.availableToChat is not None:
                profile.available_to_chat = payload.availableToChat

            if payload.profilePhoto is not None:
                profile.profile_photo = payload.profilePhoto

            if payload.links is not None:
                profile.links = json.dumps(payload.links)

            if payload.prompts is not None:
                profile.prompts = json.dumps(payload.prompts)

            profile.extraction_data = json.dumps(extraction_data)
            profile.updated_at = time.time()
            db.commit()
        finally:
            db.close()

        print(f"[PROFILE_API] Updated profile for {user_id}")

        response = JSONResponse({"status": "success", "message": "Profile updated successfully"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[PROFILE_API] Error updating profile: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")




@router.post("/upload-photo")
async def upload_profile_photo(request: Request, file: UploadFile = File(...)):
    """Upload profile photo for the calling user (identity from token)."""
    try:
        user_id = caller_phone(request)
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
            profile = db.query(UserProfile).filter_by(phone=user_id).first()

            if not profile:
                profile = UserProfile(
                    phone=user_id,
                    name="",
                    profile_photo=data_url,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
                db.add(profile)
            else:
                profile.profile_photo = data_url
                profile.updated_at = time.time()

            db.commit()
            print(f"[PROFILE_API] Photo saved for {user_id}")
        finally:
            db.close()

        response = JSONResponse({
            "status": "success",
            "message": "Profile photo uploaded successfully",
            "profilePhoto": data_url,
        })
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[PROFILE_API] Error uploading profile photo: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error uploading profile photo: {str(e)}")
