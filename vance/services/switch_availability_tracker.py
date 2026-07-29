"""
Service for tracking candidate availability status.
"""

import time
from typing import Optional
from utils.db import fs
from models.switch_models import Candidate, CandidateStatus


class AvailabilityTracker:
    """Service for tracking candidate availability."""
    
    def update_candidate_status(self, candidate_id: str, status: CandidateStatus):
        """
        Update candidate status.
        
        Status transitions:
        - On apply: IN_PROCESS (temp lock)
        - On join: PLACED (remove from pool)
        - On reject: AVAILABLE (back to pool)
        - On inactive 7+ days: INACTIVE
        """
        candidate_doc = fs.collection("candidates").document(candidate_id).get()
        if not candidate_doc.exists:
            print(f"⚠️ [AVAILABILITY] Candidate {candidate_id} not found")
            return
        
        current_status = candidate_doc.to_dict().get("status", CandidateStatus.AVAILABLE.value)
        
        if current_status == status.value:
            return  # No change needed
        
        fs.collection("candidates").document(candidate_id).update({
            "status": status.value,
            "last_active_at": time.time()
        })
        
        print(f"✅ [AVAILABILITY] Updated candidate {candidate_id} status: {current_status} → {status.value}")
    
    def check_inactive_candidates(self, days: int = 7):
        """
        Mark candidates as INACTIVE if they haven't been active for N days.
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        candidates = fs.collection("candidates").where("status", "==", CandidateStatus.AVAILABLE.value).stream()
        
        inactive_count = 0
        for candidate_doc in candidates:
            candidate_data = candidate_doc.to_dict()
            last_active = candidate_data.get("last_active_at", 0)
            
            if last_active < cutoff_time:
                fs.collection("candidates").document(candidate_doc.id).update({
                    "status": CandidateStatus.INACTIVE.value
                })
                inactive_count += 1
        
        if inactive_count > 0:
            print(f"✅ [AVAILABILITY] Marked {inactive_count} candidates as INACTIVE")
    
    def handle_candidate_joined(self, candidate_id: str):
        """Handle when candidate joins a job - mark as PLACED."""
        self.update_candidate_status(candidate_id, CandidateStatus.PLACED)
    
    def handle_candidate_rejected(self, candidate_id: str):
        """Handle when candidate is rejected - mark as AVAILABLE."""
        self.update_candidate_status(candidate_id, CandidateStatus.AVAILABLE)
    
    def handle_candidate_applied(self, candidate_id: str):
        """Handle when candidate applies - mark as IN_PROCESS (temp lock)."""
        self.update_candidate_status(candidate_id, CandidateStatus.IN_PROCESS)


availability_tracker = AvailabilityTracker()
