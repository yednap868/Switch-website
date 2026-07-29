"""
API routes for job application functionality.
Handles AI-powered job applications for candidates.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import time

from utils.db import fs, get_user_profile
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender

# Import job application service
try:
    from services.job_application_service import job_application_service
    JOB_APPLICATION_SERVICE_AVAILABLE = True
except ImportError:
    job_application_service = None
    JOB_APPLICATION_SERVICE_AVAILABLE = False
    print("⚠️ [JOB_APPLICATION] Job application service not available")

router = APIRouter(prefix="/api/job-applications", tags=["Job Applications"])


class JobApplicationRequest(BaseModel):
    """Request model for AI job application."""
    user_id: str  # Candidate's user ID (phone number)
    job_id: str  # Job identifier
    job_title: str
    company: str
    job_url: Optional[str] = None
    application_url: Optional[str] = None


@router.post("/apply")
async def apply_to_job(request: JobApplicationRequest, background_tasks: BackgroundTasks):
    """
    Apply to a job on behalf of a candidate using AI.
    
    This endpoint:
    1. Validates the candidate exists
    2. Stores the application request
    3. Triggers AI application process
    4. Sends confirmation to candidate
    """
    try:
        user_id = request.user_id
        job_id = request.job_id
        
        # Get user profile
        user_profile = get_user_profile(user_id)
        if not user_profile:
            raise HTTPException(
                status_code=404,
                detail=f"User not found: {user_id}"
            )
        
        # Get candidate name
        candidate_name = (
            user_profile.get("name")
            or user_profile.get("profile", {}).get("name")
            or "there"
        )
        
        # Store application request
        application_data = {
            "user_id": user_id,
            "job_id": job_id,
            "job_title": request.job_title,
            "company": request.company,
            "job_url": request.job_url,
            "application_url": request.application_url,
            "status": "pending",
            "applied_at": time.time(),
            "applied_via": "ai",
        }
        
        # Store in Firestore
        application_ref = fs.collection("job_applications").document(f"{user_id}_{job_id}")
        application_ref.set(application_data, merge=True)
        
        print(f"✅ [JOB_APPLICATION] Stored application request for {user_id} to {request.company}")
        
        # Send confirmation message to candidate
        sender = WhatsAppSender()
        confirmation_text = (
            f"Hey {candidate_name}! 👋\n\n"
            f"I've started applying to {request.job_title} at {request.company} on your behalf.\n\n"
            f"I'll handle the application process and keep you updated. You'll hear from me soon!"
        )
        
        try:
            result = sender.send(
                data=MsgComponents.text_scaffold(to=user_id, text=confirmation_text)
            )
            print(f"✅ [JOB_APPLICATION] Sent confirmation to {user_id}")
        except Exception as e:
            print(f"⚠️ [JOB_APPLICATION] Failed to send confirmation: {e}")
        
        # Trigger AI application process (async - don't wait)
        application_url = request.application_url or request.job_url
        if application_url and JOB_APPLICATION_SERVICE_AVAILABLE:
            # Run application process in background
            background_tasks.add_task(
                job_application_service.apply_to_job,
                user_id=user_id,
                job_title=request.job_title,
                company=request.company,
                application_url=application_url,
                job_url=request.job_url,
                job_id=job_id  # Pass job_id to ensure document ID matches
            )
            print(f"🚀 [JOB_APPLICATION] Started AI application process in background")
        elif not application_url:
            print(f"⚠️ [JOB_APPLICATION] No application URL provided - skipping AI form filling")
        
        return {
            "status": "success",
            "message": "Application process started",
            "application_id": f"{user_id}_{job_id}",
            "job_title": request.job_title,
            "company": request.company,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [JOB_APPLICATION] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing job application: {str(e)}"
        )


@router.get("/status/{user_id}")
async def get_application_status(user_id: str):
    """Get all job applications for a user."""
    try:
        applications = []
        apps_ref = fs.collection("job_applications")
        user_apps = apps_ref.where("user_id", "==", user_id).stream()
        
        for app_doc in user_apps:
            app_data = app_doc.to_dict() or {}
            applications.append({
                "application_id": app_doc.id,
                **app_data
            })
        
        return {
            "status": "success",
            "applications": applications,
            "total": len(applications)
        }
    
    except Exception as e:
        print(f"❌ [JOB_APPLICATION] Error getting status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching application status: {str(e)}"
        )


@router.get("/details/{application_id}")
async def get_application_details(application_id: str):
    """Get detailed application information including form fields and answers."""
    try:
        app_ref = fs.collection("job_applications").document(application_id)
        app_doc = app_ref.get()
        
        if not app_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Application not found: {application_id}"
            )
        
        app_data = app_doc.to_dict() or {}
        
        return {
            "status": "success",
            "application": {
                "application_id": application_id,
                **app_data
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [JOB_APPLICATION] Error getting application details: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching application details: {str(e)}"
        )

