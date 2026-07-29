"""
Service for tracking and managing call records.
"""

import time
from typing import Optional, Dict
from utils.db import fs
from models.switch_models import Call, CallStatus, CallType


class CallTrackingService:
    """Service for call tracking and management."""
    
    def create_call_record(
        self,
        call_type: CallType,
        from_number: str,
        to_number: str,
        business_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        job_id: Optional[str] = None,
        initial_data: Optional[Dict] = None
    ) -> str:
        """
        Create a new call record.
        
        Returns:
            Call ID
        """
        call_id = f"{call_type.value}_{int(time.time())}_{to_number[-4:]}"
        
        call_record = Call(
            id=call_id,
            call_type=call_type,
            from_number=from_number,
            to_number=to_number,
            business_id=business_id,
            candidate_id=candidate_id,
            job_id=job_id,
            status=CallStatus.INITIATED,
            ai_extracted_data=initial_data or {}
        )
        
        fs.collection("calls").document(call_id).set(call_record.model_dump())
        print(f"✅ [CALL_TRACKING] Created call record: {call_id}")
        
        return call_id
    
    def update_call_status(
        self,
        call_id: str,
        status: CallStatus,
        recording_url: Optional[str] = None,
        transcript: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        extracted_data: Optional[Dict] = None
    ):
        """Update call status and store additional data."""
        updates = {
            "status": status.value,
            "updated_at": time.time()
        }
        
        if recording_url:
            updates["recording_url"] = recording_url
        
        if transcript:
            updates["transcript"] = transcript
        
        if duration_seconds:
            updates["duration_seconds"] = duration_seconds
        
        if extracted_data:
            # Merge with existing extracted data
            call_doc = fs.collection("calls").document(call_id).get()
            if call_doc.exists:
                existing_data = call_doc.to_dict().get("ai_extracted_data", {})
                existing_data.update(extracted_data)
                updates["ai_extracted_data"] = existing_data
            else:
                updates["ai_extracted_data"] = extracted_data
        
        fs.collection("calls").document(call_id).update(updates)
        print(f"✅ [CALL_TRACKING] Updated call {call_id} status to {status.value}")
    
    def get_call(self, call_id: str) -> Optional[Call]:
        """Get call record by ID."""
        call_doc = fs.collection("calls").document(call_id).get()
        if not call_doc.exists:
            return None
        
        return Call(**call_doc.to_dict())
    
    async def extract_call_data(self, call_id: str, transcript: str) -> Dict:
        """
        Use AI to extract structured data from call transcript.
        """
        try:
            import os
            from anthropic import Anthropic
            
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            call_doc = fs.collection("calls").document(call_id).get()
            if not call_doc.exists:
                return {}
            
            call_data = call_doc.to_dict()
            call_type = call_data.get("call_type", "")
            
            # Create extraction prompt based on call type
            if call_type == CallType.BUSINESS_INTAKE.value:
                prompt = """Extract job requirements from this business intake call transcript. Return JSON with: role, positions_count, salary_min, salary_max, experience_required, location, shift_timing, requirements_notes, interview_address, interview_timing."""
            elif call_type == CallType.CANDIDATE_SCREENING.value:
                prompt = """Extract candidate insights from this screening call transcript. Return JSON with: experience_level, previous_roles, availability, preferences, any additional insights."""
            else:
                prompt = """Extract key information from this call transcript. Return JSON with relevant fields."""
            
            full_prompt = f"{prompt}\n\nTranscript:\n{transcript}\n\nReturn only valid JSON, no markdown formatting."
            
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            import json
            extracted_text = response.content[0].text.strip()
            if extracted_text.startswith("```"):
                extracted_text = extracted_text.split("```")[1]
                if extracted_text.startswith("json"):
                    extracted_text = extracted_text[4:]
            
            extracted_data = json.loads(extracted_text)
            
            # Update call record
            self.update_call_status(call_id, CallStatus.COMPLETED, extracted_data=extracted_data)
            
            return extracted_data
            
        except Exception as e:
            print(f"❌ [CALL_TRACKING] Error extracting call data: {e}")
            import traceback
            traceback.print_exc()
            return {}


call_tracking_service = CallTrackingService()
