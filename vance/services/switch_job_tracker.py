"""
Service for tracking and updating job status based on positions filled.
"""

import time
from utils.db import fs
from models.switch_models import Job, JobStatus


class JobStatusTracker:
    """Service for tracking job status."""
    
    def update_job_status(self, job_id: str):
        """
        Update job status based on positions_filled:
        - If filled >= count: status = FILLED, remove from feeds
        - Else if filled > 0: status = PARTIALLY_FILLED
        - Else: status = OPEN
        """
        job_doc = fs.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            return
        
        job = Job(**job_doc.to_dict())
        
        if job.positions_filled >= job.positions_count:
            # Job is fully filled
            new_status = JobStatus.FILLED
            print(f"✅ [JOB_TRACKER] Job {job_id} is FILLED ({job.positions_filled}/{job.positions_count})")
        elif job.positions_filled > 0:
            # Partially filled
            new_status = JobStatus.PARTIALLY_FILLED
            print(f"ℹ️ [JOB_TRACKER] Job {job_id} is PARTIALLY_FILLED ({job.positions_filled}/{job.positions_count})")
        else:
            # Still open
            new_status = JobStatus.OPEN
        
        if job.status != new_status:
            fs.collection("jobs").document(job_id).update({
                "status": new_status.value,
                "updated_at": time.time()
            })
            print(f"✅ [JOB_TRACKER] Updated job {job_id} status: {job.status.value} → {new_status.value}")
    
    def remove_job_from_feeds(self, job_id: str):
        """Remove job from all candidate feeds (when FILLED or CLOSED)."""
        # In production, this would update a feed cache or trigger feed refresh
        # For now, jobs are filtered by status in the feed endpoint
        print(f"🗑️ [JOB_TRACKER] Removed job {job_id} from feeds")


job_status_tracker = JobStatusTracker()
