"""
Service for tracking key metrics in Switch platform.
"""

import time
from typing import Dict, List, Optional
from utils.db import fs
from models.switch_models import JobStatus, ApplicationStatus, CandidateStatus


class SwitchMetricsService:
    """Service for tracking and calculating metrics."""
    
    def get_time_to_first_candidate(self, job_id: str) -> Optional[float]:
        """
        Calculate time from job creation to first candidate match/application.
        Returns time in seconds, or None if no candidates yet.
        """
        job_doc = fs.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            return None
        
        job_data = job_doc.to_dict()
        job_created_at = job_data.get("created_at", 0)
        
        # Get first application
        applications = fs.collection("job_applications").where("job_id", "==", job_id).stream()
        first_application = None
        earliest_time = None
        
        for app_doc in applications:
            app_data = app_doc.to_dict()
            created_at = app_data.get("created_at", 0)
            matched_at = app_data.get("matched_at", 0)
            
            # Use matched_at if available, else created_at
            app_time = matched_at if matched_at else created_at
            
            if not earliest_time or app_time < earliest_time:
                earliest_time = app_time
                first_application = app_data
        
        if earliest_time:
            return earliest_time - job_created_at
        
        return None
    
    def get_call_pickup_rate(self, call_type: str, hours: int = 24) -> Dict:
        """
        Calculate call pickup rate for a given call type.
        Returns: {total_calls, picked_up, pickup_rate}
        """
        cutoff_time = time.time() - (hours * 60 * 60)
        
        calls = fs.collection("calls").where("call_type", "==", call_type).stream()
        
        total_calls = 0
        picked_up = 0
        
        for call_doc in calls:
            call_data = call_doc.to_dict()
            created_at = call_data.get("created_at", 0)
            
            if created_at < cutoff_time:
                continue
            
            total_calls += 1
            status = call_data.get("status", "")
            
            if status in ["COMPLETED", "IN_PROGRESS"]:
                picked_up += 1
        
        pickup_rate = (picked_up / total_calls * 100) if total_calls > 0 else 0
        
        return {
            "total_calls": total_calls,
            "picked_up": picked_up,
            "pickup_rate": round(pickup_rate, 2)
        }
    
    def get_match_rate(self, job_id: str) -> Dict:
        """
        Calculate match rate (candidates matched per job).
        Returns: {job_id, total_applications, matched_count, match_rate}
        """
        applications = fs.collection("job_applications").where("job_id", "==", job_id).stream()
        
        total_applications = 0
        matched_count = 0
        
        for app_doc in applications:
            app_data = app_doc.to_dict()
            total_applications += 1
            
            source = app_data.get("source", "")
            if source == "AI_MATCH":
                matched_count += 1
        
        match_rate = (matched_count / total_applications * 100) if total_applications > 0 else 0
        
        return {
            "job_id": job_id,
            "total_applications": total_applications,
            "matched_count": matched_count,
            "match_rate": round(match_rate, 2)
        }
    
    def get_show_up_rate(self, job_id: str) -> Dict:
        """
        Calculate show-up rate (interviews attended / scheduled).
        Returns: {scheduled, attended, no_show, show_up_rate}
        """
        applications = fs.collection("job_applications").where("job_id", "==", job_id).stream()
        
        scheduled = 0
        attended = 0
        no_show = 0
        
        for app_doc in applications:
            app_data = app_doc.to_dict()
            status = app_data.get("status", "")
            
            if status == ApplicationStatus.INTERVIEW_SCHEDULED.value:
                scheduled += 1
            elif status == ApplicationStatus.INTERVIEWED.value:
                scheduled += 1
                attended += 1
            elif status == ApplicationStatus.NO_SHOW.value:
                scheduled += 1
                no_show += 1
        
        show_up_rate = (attended / scheduled * 100) if scheduled > 0 else 0
        
        return {
            "scheduled": scheduled,
            "attended": attended,
            "no_show": no_show,
            "show_up_rate": round(show_up_rate, 2)
        }
    
    def get_placement_rate(self, job_id: str) -> Dict:
        """
        Calculate placement rate (joined / interviewed).
        Returns: {interviewed, joined, placement_rate}
        """
        applications = fs.collection("job_applications").where("job_id", "==", job_id).stream()
        
        interviewed = 0
        joined = 0
        
        for app_doc in applications:
            app_data = app_doc.to_dict()
            status = app_data.get("status", "")
            
            if status in [ApplicationStatus.INTERVIEWED.value, ApplicationStatus.SELECTED.value, ApplicationStatus.JOINED.value]:
                interviewed += 1
            
            if status == ApplicationStatus.JOINED.value:
                joined += 1
        
        placement_rate = (joined / interviewed * 100) if interviewed > 0 else 0
        
        return {
            "interviewed": interviewed,
            "joined": joined,
            "placement_rate": round(placement_rate, 2)
        }
    
    def get_candidates_in_pool(self) -> Dict:
        """
        Get count of candidates in pool (AVAILABLE status).
        Returns: {total_available, total_in_process, total_placed, total_inactive}
        """
        candidates = fs.collection("candidates").stream()
        
        available = 0
        in_process = 0
        placed = 0
        inactive = 0
        
        for candidate_doc in candidates:
            candidate_data = candidate_doc.to_dict()
            status = candidate_data.get("status", "")
            
            if status == CandidateStatus.AVAILABLE.value:
                available += 1
            elif status == CandidateStatus.IN_PROCESS.value:
                in_process += 1
            elif status == CandidateStatus.PLACED.value:
                placed += 1
            elif status == CandidateStatus.INACTIVE.value:
                inactive += 1
        
        return {
            "total_available": available,
            "total_in_process": in_process,
            "total_placed": placed,
            "total_inactive": inactive
        }
    
    def get_open_jobs_count(self) -> int:
        """Get count of open jobs."""
        jobs = fs.collection("jobs").where("status", "==", JobStatus.OPEN.value).stream()
        return sum(1 for _ in jobs)
    
    def get_all_metrics(self) -> Dict:
        """Get all key metrics."""
        return {
            "candidates_in_pool": self.get_candidates_in_pool(),
            "open_jobs_count": self.get_open_jobs_count(),
            "call_pickup_rate_candidates": self.get_call_pickup_rate("CANDIDATE_PITCH"),
            "call_pickup_rate_screening": self.get_call_pickup_rate("CANDIDATE_SCREENING"),
            "call_pickup_rate_business": self.get_call_pickup_rate("BUSINESS_INTAKE"),
        }


switch_metrics_service = SwitchMetricsService()
