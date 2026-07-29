"""
Service for candidate screening calls after onboarding.
"""

import os
import time
from typing import Dict, Optional
from elevenlabs import ElevenLabs, ConversationInitiationClientDataRequestInput
from utils.db import fs
from models.switch_models import Call, CallType, CallStatus, Candidate, CandidateStatus
from services.switch_matching_service import switch_matching_service
from services.switch_call_service import switch_call_service
from services.switch_job_service import switch_job_service
from models.switch_models import ApplicationSource


class ScreeningService:
    """Service for candidate screening calls."""
    
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        self.elevenlabs_phone_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
        
        if self.elevenlabs_api_key and self.elevenlabs_agent_id:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        else:
            self.elevenlabs_client = None
    
    async def initiate_screening_call(self, candidate_id: str, attempt: int = 1) -> str:
        """
        Initiate screening call to candidate after onboarding.
        
        Args:
            candidate_id: Candidate ID
        
        Returns:
            Call ID
        """
        if not self.elevenlabs_client:
            raise Exception("ElevenLabs not configured")
        
        candidate_doc = fs.collection("candidates").document(candidate_id).get()
        if not candidate_doc.exists:
            raise Exception(f"Candidate {candidate_id} not found")
        
        candidate = Candidate(**candidate_doc.to_dict())
        
        # Format phone
        candidate_phone = candidate.phone
        if not candidate_phone.startswith('+'):
            if candidate_phone.startswith('91'):
                candidate_phone = '+' + candidate_phone
            else:
                candidate_phone = '+91' + candidate_phone
        
        call_id = f"screening_{candidate_id}_{int(time.time())}"
        
        # Create call record
        call_record = Call(
            id=call_id,
            call_type=CallType.CANDIDATE_SCREENING,
            from_number=self.elevenlabs_phone_id,
            to_number=candidate_phone,
            candidate_id=candidate_id,
            status=CallStatus.INITIATED
        )
        
        fs.collection("calls").document(call_id).set(call_record.model_dump())
        
        # Initiate call
        self.elevenlabs_client.conversational_ai.twilio.outbound_call(
            agent_id=self.elevenlabs_agent_id,
            agent_phone_number_id=self.elevenlabs_phone_id,
            to_number=candidate_phone,
            conversation_initiation_client_data=ConversationInitiationClientDataRequestInput(
                user_id=candidate_id,
                dynamic_variables={
                    "call_type": "candidate_inbound",
                    "candidate_name": candidate.name,
                    "registered_via": "app",
                },
            ),
        )
        
        print(f"✅ [SCREENING] Initiated screening call to {candidate.name} ({candidate_phone}) - Attempt {attempt}")
        return call_id
    
    async def process_screening_call_complete(
        self,
        call_id: str,
        transcript: str,
        extracted_data: Dict
    ):
        """
        Process completed screening call.
        Extract insights, update candidate profile, check for job matches.
        """
        call_doc = fs.collection("calls").document(call_id).get()
        if not call_doc.exists:
            return
        
        call_data = call_doc.to_dict()
        candidate_id = call_data.get("candidate_id")
        
        if not candidate_id:
            return
        
        # Update call record
        fs.collection("calls").document(call_id).update({
            "transcript": transcript,
            "ai_extracted_data": extracted_data,
            "status": CallStatus.COMPLETED.value,
            "recording_url": extracted_data.get("recording_url")
        })
        
        # Update candidate profile with insights
        candidate_doc = fs.collection("candidates").document(candidate_id).get()
        if candidate_doc.exists:
            candidate_data = candidate_doc.to_dict()
            
            # Update with extracted insights
            updates = {
                "screening_call_recording_url": extracted_data.get("recording_url"),
                "last_active_at": time.time()
            }
            
            # Merge extracted data into profile
            if "experience_level" in extracted_data:
                updates["experience_level"] = extracted_data["experience_level"]
            if "previous_roles" in extracted_data:
                updates["previous_roles"] = extracted_data.get("previous_roles", [])
            if "availability" in extracted_data:
                updates["availability"] = extracted_data["availability"]
            
            fs.collection("candidates").document(candidate_id).update(updates)
        
        # Check for real-time job matches
        await self._check_realtime_job_matches(candidate_id)
        
        print(f"✅ [SCREENING] Processed screening call {call_id} for candidate {candidate_id}")
    
    async def _check_realtime_job_matches(self, candidate_id: str):
        """Check for matching jobs and offer connection if found."""
        matching_jobs = switch_matching_service.find_jobs_for_candidate(
            candidate_id,
            exclude_swiped=True,
            limit=1
        )
        
        if matching_jobs:
            job = matching_jobs[0]
            print(f"🎯 [SCREENING] Found real-time match for candidate {candidate_id}: job {job.id}")
            
            # In production, this would trigger another AI call or WhatsApp message
            # For now, we'll create an application
            switch_job_service.create_application(
                job.id,
                candidate_id,
                ApplicationSource.AI_MATCH
            )
            
            # Update candidate status
            from services.switch_availability_tracker import availability_tracker
            availability_tracker.update_candidate_status(candidate_id, CandidateStatus.IN_PROCESS)


screening_service = ScreeningService()
