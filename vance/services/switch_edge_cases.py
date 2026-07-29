"""
Service for handling edge cases in Switch platform.
"""

import time
from typing import Optional
from utils.db import fs
from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from models.switch_models import CandidateStatus, ApplicationStatus, JobStatus
from services.switch_job_service import switch_job_service
from services.switch_matching_service import switch_matching_service
from services.switch_whatsapp_service import switch_whatsapp_service
from services.switch_screening_service import screening_service
from services.switch_availability_tracker import availability_tracker


class SwitchEdgeCaseHandler:
    """Service for handling edge cases."""
    
    def handle_no_matching_candidates(self, job_id: str, business_id: str):
        """
        Handle case when no matching candidates found.
        Notify business and trigger sourcing alert.
        """
        print(f"⚠️ [EDGE_CASE] No matching candidates for job {job_id}")
        
        # Get business phone
        business_doc = fs.collection("businesses").document(business_id).get()
        if not business_doc.exists:
            return
        
        business_data = business_doc.to_dict()
        business_phone = business_data.get("phone", "")
        
        # Format phone
        if not business_phone.startswith('+'):
            if business_phone.startswith('91'):
                business_phone = '+' + business_phone
            else:
                business_phone = '+91' + business_phone
        
        # Send WhatsApp message
        message = (
            "We're finding candidates for your requirement. "
            "We'll send you candidate profiles within 4 hours. "
            "Thank you for your patience! 🙏"
        )
        
        try:
            message_data = MsgComponents.text_scaffold(to=business_phone, text=message)
            result = WhatsAppSender.send(message_data)
            if result.get("status") == "success":
                print(f"✅ [EDGE_CASE] Notified business {business_id} about no matches")
            else:
                print(f"❌ [EDGE_CASE] Error sending message: {result.get('error')}")
        except Exception as e:
            print(f"❌ [EDGE_CASE] Error sending message: {e}")
        
        # Trigger sourcing alert (log for now, can be extended to alert system)
        fs.collection("sourcing_alerts").document(f"{job_id}_{int(time.time())}").set({
            "job_id": job_id,
            "business_id": business_id,
            "alert_type": "no_candidates",
            "created_at": time.time(),
            "status": "pending"
        })
        print(f"✅ [EDGE_CASE] Created sourcing alert for job {job_id}")
    
    async def handle_screening_call_no_pickup(
        self,
        candidate_id: str,
        attempt: int = 1
    ):
        """
        Handle when candidate doesn't pick screening call.
        Retry 2x at 30-min intervals, then send WhatsApp callback request.
        """
        if attempt > 2:
            # Max retries reached, send WhatsApp callback request
            candidate_doc = fs.collection("candidates").document(candidate_id).get()
            if not candidate_doc.exists:
                return
            
            candidate = candidate_doc.to_dict()
            candidate_phone = candidate.get("phone", "")
            
            # Format phone
            if not candidate_phone.startswith('+'):
                if candidate_phone.startswith('91'):
                    candidate_phone = '+' + candidate_phone
                else:
                    candidate_phone = '+91' + candidate_phone
            
            message = (
                "Hi! We tried calling you for your screening call but couldn't reach you. "
                "Please call us back or reply 'CALLBACK' to schedule a time that works for you. "
                "This is important to complete your profile setup! 📞"
            )
            
            try:
                message_data = MsgComponents.text_scaffold(to=candidate_phone, text=message)
                result = WhatsAppSender.send(message_data)
                if result.get("status") == "success":
                    print(f"✅ [EDGE_CASE] Sent callback request to candidate {candidate_id}")
                else:
                    print(f"❌ [EDGE_CASE] Error sending callback request: {result.get('error')}")
            except Exception as e:
                print(f"❌ [EDGE_CASE] Error sending callback request: {e}")
        else:
            # Retry after 30 minutes
            print(f"⏰ [EDGE_CASE] Scheduling retry {attempt + 1} for candidate {candidate_id} in 30 minutes")
            # In production, use a task queue (Celery, etc.) for delayed retries
            # For now, log it
            fs.collection("call_retries").document(f"{candidate_id}_{attempt}").set({
                "candidate_id": candidate_id,
                "attempt": attempt + 1,
                "scheduled_at": time.time() + (30 * 60),  # 30 minutes
                "call_type": "screening"
            })
    
    def handle_candidate_no_show(
        self,
        application_id: str,
        job_id: str,
        candidate_id: str,
        business_id: str
    ):
        """
        Handle candidate no-show at interview.
        Mark as NO_SHOW, notify business, offer replacement candidate.
        """
        print(f"⚠️ [EDGE_CASE] Candidate {candidate_id} no-show for job {job_id}")
        
        # Update application status
        switch_job_service.update_application_status(
            application_id,
            ApplicationStatus.NO_SHOW,
            notes="Candidate did not show up for interview"
        )
        
        # Update candidate status back to AVAILABLE
        availability_tracker.update_candidate_status(candidate_id, CandidateStatus.AVAILABLE)
        
        # Notify business
        job = switch_job_service.get_job(job_id)
        if job:
            business_doc = fs.collection("businesses").document(business_id).get()
            if business_doc.exists:
                business_data = business_doc.to_dict()
                business_phone = business_data.get("phone", "")
                
                # Format phone
                if not business_phone.startswith('+'):
                    if business_phone.startswith('91'):
                        business_phone = '+' + business_phone
                    else:
                        business_phone = '+91' + business_phone
                
                candidate_doc = fs.collection("candidates").document(candidate_id).get()
                candidate_name = candidate_doc.to_dict().get("name", "Candidate") if candidate_doc.exists else "Candidate"
                
                message = (
                    f"⚠️ {candidate_name} did not show up for the interview. "
                    f"We're finding a replacement candidate for you. "
                    f"You'll receive new candidate profiles shortly."
                )
                
                try:
                    message_data = MsgComponents.text_scaffold(to=business_phone, text=message)
                    result = WhatsAppSender.send(message_data)
                    if result.get("status") == "success":
                        print(f"✅ [EDGE_CASE] Notified business about no-show")
                    else:
                        print(f"❌ [EDGE_CASE] Error notifying business: {result.get('error')}")
                except Exception as e:
                    print(f"❌ [EDGE_CASE] Error notifying business: {e}")
        
        # Find replacement candidate
        replacement_candidates = switch_matching_service.find_matching_candidates(job, limit=5)
        
        if replacement_candidates:
            # Send replacement candidates to business
            import asyncio
            asyncio.create_task(
                switch_whatsapp_service.send_candidate_profiles(
                    business_id,
                    replacement_candidates,
                    job_id
                )
            )
            print(f"✅ [EDGE_CASE] Sent {len(replacement_candidates)} replacement candidates")
        else:
            # No replacement candidates, trigger sourcing
            self.handle_no_matching_candidates(job_id, business_id)
    
    def handle_job_filled_externally(self, job_id: str, business_id: str):
        """
        Handle when business marks job as filled externally.
        Close job and notify any pending candidates.
        """
        print(f"ℹ️ [EDGE_CASE] Job {job_id} filled externally")
        
        # Close job
        switch_job_service.update_job_status(job_id, JobStatus.CLOSED)
        
        # Get pending applications
        applications = switch_job_service.get_applications_for_job(job_id)
        
        # Notify pending candidates
        for app in applications:
            if app.status in [ApplicationStatus.APPLIED, ApplicationStatus.MATCHED, ApplicationStatus.INTERVIEW_SCHEDULED]:
                candidate_doc = fs.collection("candidates").document(app.candidate_id).get()
                if candidate_doc.exists:
                    candidate = candidate_doc.to_dict()
                    candidate_phone = candidate.get("phone", "")
                    
                    # Format phone
                    if not candidate_phone.startswith('+'):
                        if candidate_phone.startswith('91'):
                            candidate_phone = '+' + candidate_phone
                        else:
                            candidate_phone = '+91' + candidate_phone
                    
                    message = (
                        "The job you applied for has been filled. "
                        "We'll notify you when we have similar opportunities! "
                        "Keep your profile updated. 🙏"
                    )
                    
                    try:
                        message_data = MsgComponents.text_scaffold(to=candidate_phone, text=message)
                        result = WhatsAppSender.send(message_data)
                        if result.get("status") != "success":
                            print(f"❌ [EDGE_CASE] Error notifying candidate: {result.get('error')}")
                    except Exception as e:
                        print(f"❌ [EDGE_CASE] Error notifying candidate: {e}")
                    
                    # Update candidate status back to AVAILABLE
                    availability_tracker.update_candidate_status(app.candidate_id, CandidateStatus.AVAILABLE)
                    
                    # Update application status
                    switch_job_service.update_application_status(
                        app.id,
                        ApplicationStatus.REJECTED,
                        notes="Job filled externally"
                    )
        
        print(f"✅ [EDGE_CASE] Closed job {job_id} and notified {len(applications)} candidates")


edge_case_handler = SwitchEdgeCaseHandler()
