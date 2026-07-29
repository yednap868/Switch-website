"""
API routes for Switch business side - requirement intake, job management.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional
import time

from utils.db import fs
from services.switch_business_intake_service import business_intake_service
from services.switch_job_service import switch_job_service
from services.switch_matching_service import switch_matching_service
from services.switch_call_service import switch_call_service
from services.switch_whatsapp_service import switch_whatsapp_service
from models.switch_models import BusinessRequirementRequest, JobCreationRequest


router = APIRouter(prefix="/api/switch/business", tags=["Switch Business"])


class WhatsAppMessageRequest(BaseModel):
    """Request model for WhatsApp business message."""
    from_number: str
    message: str
    message_id: Optional[str] = None




@router.post("/whatsapp/requirement")
async def handle_business_requirement(
    request: WhatsAppMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Handle WhatsApp message from business with job requirement.
    Triggers AI call to business to collect structured requirements.
    """
    try:
        print(f"📱 [BUSINESS_ROUTES] Received requirement from {request.from_number}: {request.message[:50]}...")
        
        # Create or update business record
        business_id = business_intake_service.create_or_update_business(
            phone=request.from_number,
            name="",  # Will be collected in call
            contact_person=""
        )
        
        # Trigger AI call to business in background
        background_tasks.add_task(
            business_intake_service.initiate_business_call,
            business_phone=request.from_number,
            initial_message=request.message,
            business_id=business_id
        )
        
        return JSONResponse({
            "status": "success",
            "message": "We're calling you now to collect job requirements. Please pick up!",
            "business_id": business_id
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        print(f"❌ [BUSINESS_ROUTES] Error handling requirement: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing requirement: {str(e)}")


@router.post("/jobs/create")
async def create_job_from_requirements(request: JobCreationRequest):
    """
    Create job from AI-extracted requirements.
    Called after business intake call completes.
    """
    try:
        job = switch_job_service.create_job_from_requirements(
            business_id=request.business_id,
            requirements=request.model_dump()
        )
        
        # Trigger real-time candidate matching
        matching_candidates = switch_matching_service.find_matching_candidates(job)
        
        if matching_candidates:
            # Batch call candidates
            business_doc = fs.collection("businesses").document(request.business_id).get()
            business_phone = business_doc.to_dict().get("phone", "") if business_doc.exists else ""
            
            await switch_call_service.batch_call_candidates(
                job=job,
                candidates=matching_candidates,
                business_phone=business_phone
            )
        else:
            # No matching candidates - handle edge case
            from services.switch_edge_cases import edge_case_handler
            edge_case_handler.handle_no_matching_candidates(job.id, request.business_id)
        
        return JSONResponse({
            "status": "success",
            "job_id": job.id,
            "candidates_matched": len(matching_candidates) if matching_candidates else 0
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        print(f"❌ [BUSINESS_ROUTES] Error creating job: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details."""
    try:
        job = switch_job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JSONResponse({
            "status": "success",
            "job": job.model_dump()
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting job: {str(e)}")


@router.put("/jobs/{job_id}/close")
async def close_job(job_id: str):
    """Close job (mark as CLOSED). Handles job filled externally edge case."""
    try:
        from models.switch_models import JobStatus
        from services.switch_edge_cases import edge_case_handler
        
        job = switch_job_service.get_job(job_id)
        if job:
            edge_case_handler.handle_job_filled_externally(job_id, job.business_id)
        else:
            switch_job_service.update_job_status(job_id, JobStatus.CLOSED)
        
        return JSONResponse({
            "status": "success",
            "message": "Job closed"
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error closing job: {str(e)}")


@router.post("/jobs/{job_id}/select-candidate")
async def select_candidate(job_id: str, candidate_id: str):
    """
    Business selects a candidate from WhatsApp profiles.
    Triggers interview confirmation flow.
    """
    try:
        from models.switch_models import ApplicationSource, ApplicationStatus
        
        # Create application
        application = switch_job_service.create_application(
            job_id=job_id,
            candidate_id=candidate_id,
            source=ApplicationSource.BUSINESS_SELECT
        )
        
        # Update status to INTERVIEW_SCHEDULED
        switch_job_service.update_application_status(
            application.id,
            ApplicationStatus.INTERVIEW_SCHEDULED
        )
        
        # Get job and candidate
        job = switch_job_service.get_job(job_id)
        candidate_doc = fs.collection("candidates").document(candidate_id).get()
        
        if job and candidate_doc.exists:
            from models.switch_models import Candidate
            candidate = Candidate(**candidate_doc.to_dict())
            
            # Send interview confirmation to candidate
            await switch_whatsapp_service.send_interview_confirmation(candidate_id, job)
        
        return JSONResponse({
            "status": "success",
            "message": "Interview scheduled"
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error selecting candidate: {str(e)}")
