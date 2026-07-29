"""
Employer match routes — serves /hire/{token} page and JSON API for approve/decline.
"""

import json
import threading
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from models.sql_models import Job, User, JobApplication
from services.employer_match_service import notify_candidate_matched
from services.placement_service import create_placement, send_interview_invite
from utils.postgres import get_db

router = APIRouter(prefix="/api/employer-match", tags=["Employer Match"])
hire_router = APIRouter(tags=["Employer Hire Page"])
templates = Jinja2Templates(directory="templates")


def _load_match_context(token: str) -> dict:
    """Load candidate + job data for a match token. Returns template context dict."""
    db = get_db()
    try:
        app = db.query(JobApplication).filter_by(match_token=token).first()
        if not app:
            return {"error": True}

        if app.employer_action:
            return {
                "already_actioned": True,
                "employer_action": app.employer_action,
            }

        candidate = db.query(User).filter_by(phone=app.user_id).first()
        job = db.query(Job).filter_by(job_id=app.job_id).first()

        if not candidate or not job:
            return {"error": True}

        preferred_roles = ""
        if candidate.preferred_roles:
            roles = json.loads(candidate.preferred_roles)
            preferred_roles = ", ".join(roles[:3]) if roles else ""

        languages = ""
        if candidate.languages:
            langs = json.loads(candidate.languages)
            languages = ", ".join(langs[:4]) if langs else ""

        has_photo = bool(candidate.photo_url and candidate.photo_url.startswith("data:"))

        kyc_app = db.query(JobApplication).filter_by(
            match_token=token
        ).first()

        return {
            "candidate": {
                "phone": candidate.phone,
                "name": candidate.name or "",
                "experience": candidate.experience or "",
                "location": candidate.location or "",
                "education": candidate.education or "",
            },
            "job": {
                "job_id": job.job_id,
                "title": job.title or "",
                "company": job.company or "",
                "location": job.location or "",
                "salary_min": job.salary_min or 0,
                "salary_max": job.salary_max or 0,
            },
            "preferred_roles": preferred_roles,
            "languages": languages,
            "has_photo": has_photo,
            "token": token,
            "kyc_verified_at": kyc_app.kyc_verified_at if kyc_app else None,
            "kyc_photo_url": kyc_app.kyc_photo_url if kyc_app else None,
            "kyc_video_url": kyc_app.kyc_video_url if kyc_app else None,
            "kyc_summary": kyc_app.kyc_summary if kyc_app else None,
            "kyc_agent_name": kyc_app.kyc_agent_name if kyc_app else None,
        }
    finally:
        db.close()


@hire_router.get("/hire/{token}")
async def hire_page(token: str, request: Request):
    """Serve the employer candidate approval page."""
    ctx = _load_match_context(token)
    ctx["request"] = request
    return templates.TemplateResponse("employer_match.html", ctx)


@router.get("/{token}")
async def employer_match_data(token: str):
    """Return candidate + job data as JSON for the frontend approval page.
    Also records employer_viewed_at on first view.
    """
    db = get_db()
    try:
        app = db.query(JobApplication).filter_by(match_token=token).first()
        if app and not app.employer_viewed_at:
            app.employer_viewed_at = time.time()
            db.commit()
    except Exception:
        pass
    finally:
        db.close()

    ctx = _load_match_context(token)
    if ctx.get("error"):
        return JSONResponse({"error": True}, status_code=404)
    ctx.pop("token", None)
    return JSONResponse(ctx)


@router.post("/{token}/approve")
async def approve_candidate(token: str):
    """Employer approves candidate — set status to matched, notify candidate."""
    db = get_db()
    try:
        app = db.query(JobApplication).filter_by(match_token=token).first()
        if not app:
            return JSONResponse({"status": "error", "message": "Invalid token"}, status_code=404)

        if app.employer_action:
            return JSONResponse({"status": "already_actioned", "action": app.employer_action})

        app.employer_action = "approved"
        app.employer_action_at = time.time()
        app.status = "matched"
        app.matched_at = time.time()
        try:
            history = json.loads(app.status_history or "[]")
        except (json.JSONDecodeError, TypeError):
            history = []
        history.append({"status": "matched", "at": time.time()})
        app.status_history = json.dumps(history)
        db.commit()

        user_id = app.user_id
        job_id = app.job_id
        app_id = app.id
    finally:
        db.close()

    def _notify():
        try:
            ndb = get_db()
            try:
                job = ndb.query(Job).filter_by(job_id=job_id).first()
                if job:
                    notify_candidate_matched(user_id, job, application_id=app_id)
                    app_obj = ndb.query(JobApplication).filter_by(id=app_id).first()
                    if app_obj:
                        placement = create_placement(ndb, app_obj, job, job.phone or "")
                        send_interview_invite(placement)
            finally:
                ndb.close()
        except Exception as e:
            print(f"[EMPLOYER_MATCH] Error notifying candidate: {e}")

    threading.Thread(target=_notify, daemon=True).start()

    return JSONResponse({"status": "success", "action": "approved"})


@router.post("/{token}/decline")
async def decline_candidate(token: str):
    """Employer passes on candidate."""
    db = get_db()
    try:
        app = db.query(JobApplication).filter_by(match_token=token).first()
        if not app:
            return JSONResponse({"status": "error", "message": "Invalid token"}, status_code=404)

        if app.employer_action:
            return JSONResponse({"status": "already_actioned", "action": app.employer_action})

        app.employer_action = "declined"
        app.employer_action_at = time.time()
        db.commit()
    finally:
        db.close()

    return JSONResponse({"status": "success", "action": "declined"})
