"""
Service for managing jobs - creation, status updates, and lifecycle.
"""

import time
from typing import List, Optional
from utils.db import fs
from models.switch_models import Job, JobStatus, JobApplication, ApplicationStatus, ApplicationSource, CandidateStatus


class SwitchJobService:
    """Service for job management."""
    
    def create_job_from_requirements(
        self,
        business_id: str,
        requirements: dict
    ) -> Job:
        """
        Create job from AI-extracted requirements.
        
        Args:
            business_id: Business ID
            requirements: Extracted requirements dictionary
        
        Returns:
            Created Job object
        """
        job_id = f"job_{business_id}_{int(time.time())}"
        
        job_data = Job(
            id=job_id,
            business_id=business_id,
            role=requirements.get("role", "OTHER"),
            positions_count=int(requirements.get("positions_count", 1)),
            positions_filled=0,
            salary_min=int(requirements.get("salary_min", 0)),
            salary_max=int(requirements.get("salary_max", 0)),
            experience_required=requirements.get("experience_required", ""),
            location=requirements.get("location", ""),
            shift_timing=requirements.get("shift_timing"),
            requirements_notes=requirements.get("requirements_notes"),
            interview_address=requirements.get("interview_address", ""),
            interview_timing=requirements.get("interview_timing"),
            status=JobStatus.OPEN,
            ai_call_recording_url=requirements.get("call_recording_url")
        )
        
        fs.collection("jobs").document(job_id).set(job_data.model_dump())
        print(f"✅ [JOB_SERVICE] Created job: {job_id} for business {business_id}")
        
        return job_data
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        job_doc = fs.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            return None
        
        return Job(**job_doc.to_dict())
    
    def update_job_status(self, job_id: str, status: JobStatus):
        """Update job status."""
        fs.collection("jobs").document(job_id).update({
            "status": status.value,
            "updated_at": time.time()
        })
        print(f"✅ [JOB_SERVICE] Updated job {job_id} status to {status.value}")
    
    def increment_positions_filled(self, job_id: str):
        """Increment positions_filled and update status if needed."""
        job = self.get_job(job_id)
        if not job:
            return
        
        new_filled = job.positions_filled + 1
        
        if new_filled >= job.positions_count:
            # Job is fully filled
            self.update_job_status(job_id, JobStatus.FILLED)
        elif new_filled > 0:
            # Partially filled
            self.update_job_status(job_id, JobStatus.PARTIALLY_FILLED)
        
        fs.collection("jobs").document(job_id).update({
            "positions_filled": new_filled,
            "updated_at": time.time()
        })
    
    def create_application(
        self,
        job_id: str,
        candidate_id: str,
        source: ApplicationSource
    ) -> JobApplication:
        """Create job application."""
        application_id = f"app_{job_id}_{candidate_id}"
        
        application_data = JobApplication(
            id=application_id,
            job_id=job_id,
            candidate_id=candidate_id,
            source=source,
            status=ApplicationStatus.APPLIED if source == ApplicationSource.SWIPE else ApplicationStatus.MATCHED,
            matched_at=time.time() if source != ApplicationSource.SWIPE else None
        )
        
        fs.collection("job_applications").document(application_id).set(application_data.model_dump())
        print(f"✅ [JOB_SERVICE] Created application: {application_id}")
        
        return application_data
    
    def update_application_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        notes: Optional[str] = None
    ):
        """Update application status."""
        updates = {
            "status": status.value,
            "updated_at": time.time()
        }
        
        if status == ApplicationStatus.INTERVIEW_SCHEDULED:
            updates["interview_scheduled_at"] = time.time()
        elif status == ApplicationStatus.JOINED:
            updates["joined_at"] = time.time()
        
        if notes:
            updates["notes"] = notes
        
        fs.collection("job_applications").document(application_id).update(updates)
        print(f"✅ [JOB_SERVICE] Updated application {application_id} to {status.value}")
    
    def get_applications_for_job(self, job_id: str) -> List[JobApplication]:
        """Get all applications for a job."""
        applications = fs.collection("job_applications").where("job_id", "==", job_id).stream()
        return [JobApplication(**app.to_dict()) for app in applications]
    
    def get_applications_for_candidate(self, candidate_id: str) -> List[JobApplication]:
        """Get all applications for a candidate."""
        applications = fs.collection("job_applications").where("candidate_id", "==", candidate_id).stream()
        return [JobApplication(**app.to_dict()) for app in applications]
    
    def handle_candidate_joined(self, candidate_id: str, job_id: str):
        """
        Handle when candidate joins a job:
        - Update candidate status to PLACED
        - Withdraw from all other applications
        - Update job positions_filled
        """
        # Update candidate status
        from services.switch_availability_tracker import availability_tracker
        availability_tracker.update_candidate_status(candidate_id, CandidateStatus.PLACED)
        
        # Get all applications for this candidate
        applications = self.get_applications_for_candidate(candidate_id)
        
        # Update the joined application
        for app in applications:
            if app.job_id == job_id:
                self.update_application_status(app.id, ApplicationStatus.JOINED)
            else:
                # Withdraw other applications
                self.update_application_status(app.id, ApplicationStatus.REJECTED, "Candidate joined another job")
        
        # Update job positions_filled
        self.increment_positions_filled(job_id)
        
        print(f"✅ [JOB_SERVICE] Candidate {candidate_id} joined job {job_id}")


switch_job_service = SwitchJobService()
