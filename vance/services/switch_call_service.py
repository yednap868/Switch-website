"""
Service for managing calls - batch calling, warm transfer, call merging.
"""

import os
import time
from typing import List, Optional
from elevenlabs import ElevenLabs, ConversationInitiationClientDataRequestInput
from utils.db import fs
from models.switch_models import Call, CallType, CallStatus, Job, Candidate
from models.switch_models import CandidateStatus, ApplicationStatus


class SwitchCallService:
    """Service for managing candidate calls and warm transfers."""
    
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        self.elevenlabs_phone_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if self.elevenlabs_api_key and self.elevenlabs_agent_id:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        else:
            self.elevenlabs_client = None
    
    async def batch_call_candidates(
        self,
        job: Job,
        candidates: List[Candidate],
        business_phone: str
    ) -> dict:
        """
        Batch call top candidates for a job.
        First one to pick up gets connected to business.
        
        Args:
            job: Job object
            candidates: List of candidate objects
            business_phone: Business phone number for warm transfer
        
        Returns:
            Result dictionary with call status
        """
        if not self.elevenlabs_client:
            raise Exception("ElevenLabs not configured")
        
        print(f"📞 [CALL_SERVICE] Batch calling {len(candidates)} candidates for job {job.id}")
        
        active_calls = []
        first_pickup = None
        
        # Initiate calls to all candidates
        for candidate in candidates:
            try:
                call_id = await self._initiate_candidate_pitch_call(candidate, job)
                active_calls.append({
                    "call_id": call_id,
                    "candidate_id": candidate.id,
                    "candidate": candidate
                })
                
                # Small delay between calls
                import asyncio
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"❌ [CALL_SERVICE] Error calling candidate {candidate.id}: {e}")
                continue
        
        # Wait for first pickup (in real implementation, this would be via webhook)
        # For now, we'll return the call IDs and handle pickup via webhook
        
        return {
            "status": "calling",
            "active_calls": len(active_calls),
            "call_ids": [c["call_id"] for c in active_calls]
        }
    
    async def _initiate_candidate_pitch_call(self, candidate: Candidate, job: Job) -> str:
        """Initiate AI call to candidate with job pitch."""
        call_id = f"candidate_pitch_{candidate.id}_{job.id}_{int(time.time())}"
        
        # Format candidate phone
        candidate_phone = candidate.phone
        if not candidate_phone.startswith('+'):
            if candidate_phone.startswith('91'):
                candidate_phone = '+' + candidate_phone
            else:
                candidate_phone = '+91' + candidate_phone
        
        # Create call record
        call_record = Call(
            id=call_id,
            call_type=CallType.CANDIDATE_PITCH,
            from_number=self.elevenlabs_phone_id,
            to_number=candidate_phone,
            candidate_id=candidate.id,
            job_id=job.id,
            status=CallStatus.INITIATED,
            ai_extracted_data={
                "job_role": job.role,
                "job_company": job.business_id,
                "job_salary": f"{job.salary_min}-{job.salary_max}",
                "job_location": job.location
            }
        )
        
        fs.collection("calls").document(call_id).set(call_record.model_dump())
        
        # Initiate call
        self.elevenlabs_client.conversational_ai.twilio.outbound_call(
            agent_id=self.elevenlabs_agent_id,
            agent_phone_number_id=self.elevenlabs_phone_id,
            to_number=candidate_phone,
            conversation_initiation_client_data=ConversationInitiationClientDataRequestInput(
                user_id=candidate.id,
                dynamic_variables={
                    "call_type": "candidate_pitch",
                    "candidate_name": candidate.name,
                    "job_role": job.role,
                    "job_location": job.location,
                    "job_salary": f"₹{job.salary_min:,} - ₹{job.salary_max:,}",
                    "job_timing": job.interview_timing or "",
                },
            ),
        )
        
        print(f"✅ [CALL_SERVICE] Initiated pitch call to {candidate.name} ({candidate_phone})")
        return call_id
    
    async def handle_candidate_pickup(
        self,
        call_id: str,
        candidate_id: str,
        job_id: str,
        interested: bool
    ):
        """
        Handle when candidate picks up and responds.
        
        Args:
            call_id: Call ID
            candidate_id: Candidate ID
            job_id: Job ID
            interested: Whether candidate is interested
        """
        if not interested:
            # Mark candidate as not interested for this job
            print(f"ℹ️ [CALL_SERVICE] Candidate {candidate_id} not interested in job {job_id}")
            return
        
        # Candidate is interested - attempt warm transfer
        job = switch_job_service.get_job(job_id)
        if not job:
            return
        
        # Get business phone
        business_doc = fs.collection("businesses").document(job.business_id).get()
        if not business_doc.exists:
            return
        
        business_data = business_doc.to_dict()
        business_phone = business_data.get("phone", "")
        
        if not business_phone.startswith('+'):
            if business_phone.startswith('91'):
                business_phone = '+' + business_phone
            else:
                business_phone = '+91' + business_phone
        
        # Attempt to call business and merge calls
        try:
            await self._attempt_warm_transfer(call_id, candidate_id, job_id, business_phone)
        except Exception as e:
            print(f"⚠️ [CALL_SERVICE] Warm transfer failed: {e}")
            # Fallback: Send WhatsApp profiles to business
            from services.switch_whatsapp_service import switch_whatsapp_service
            candidate = fs.collection("candidates").document(candidate_id).get()
            if candidate.exists:
                candidate_data = Candidate(**candidate.to_dict())
                await switch_whatsapp_service.send_candidate_profiles(
                    job.business_id,
                    [candidate_data],
                    job_id
                )
    
    async def _attempt_warm_transfer(
        self,
        candidate_call_id: str,
        candidate_id: str,
        job_id: str,
        business_phone: str
    ):
        """Attempt warm transfer: call business and merge with candidate call."""
        # This would use Twilio's call merging/conference features
        # For now, we'll create a new call to business
        
        print(f"🔄 [CALL_SERVICE] Attempting warm transfer for job {job_id}")
        
        # Call business
        business_call_id = f"business_connect_{job_id}_{int(time.time())}"
        
        # In production, this would use Twilio's <Dial> and <Conference> verbs
        # to merge the calls
        
        # For now, create a call record
        call_record = Call(
            id=business_call_id,
            call_type=CallType.CONNECTED_CALL,
            from_number=self.elevenlabs_phone_id,
            to_number=business_phone,
            candidate_id=candidate_id,
            job_id=job_id,
            status=CallStatus.INITIATED
        )
        
        fs.collection("calls").document(business_call_id).set(call_record.model_dump())
        
        # Update candidate status
        from services.switch_availability_tracker import availability_tracker
        availability_tracker.update_candidate_status(candidate_id, CandidateStatus.IN_PROCESS)
        
        # Create application
        from models.switch_models import ApplicationSource
        from services.switch_job_service import switch_job_service
        switch_job_service.create_application(
            job_id,
            candidate_id,
            ApplicationSource.AI_MATCH
        )
        
        print(f"✅ [CALL_SERVICE] Warm transfer initiated for job {job_id}")


switch_call_service = SwitchCallService()
