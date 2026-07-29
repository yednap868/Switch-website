"""
Service for handling business requirement intake via AI calls.
Collects structured job requirements from businesses.
"""

import os
import time
from typing import Dict, Optional
from elevenlabs import ElevenLabs, ConversationInitiationClientDataRequestInput
from utils.db import fs
from models.switch_models import Business, Call, CallType, CallStatus


class BusinessIntakeService:
    """Service for initiating and handling business intake calls."""
    
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_agent_id = os.getenv("ELEVENLABS_AGENT_ID")
        self.elevenlabs_phone_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
        
        if self.elevenlabs_api_key and self.elevenlabs_agent_id:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        else:
            self.elevenlabs_client = None
            print("⚠️ [BUSINESS_INTAKE] ElevenLabs not configured")
    
    async def initiate_business_call(
        self,
        business_phone: str,
        initial_message: str,
        business_id: Optional[str] = None
    ) -> str:
        """
        Initiate AI call to business to collect job requirements.
        
        Args:
            business_phone: Business phone number (E.164 format)
            initial_message: Initial requirement message from WhatsApp
            business_id: Optional business ID if already exists
        
        Returns:
            Call ID
        """
        if not self.elevenlabs_client:
            raise Exception("ElevenLabs not configured")
        
        # Format phone number
        if not business_phone.startswith('+'):
            if business_phone.startswith('91'):
                business_phone = '+' + business_phone
            else:
                business_phone = '+91' + business_phone
        
        # Create call record
        call_id = f"business_intake_{business_phone}_{int(time.time())}"
        call_record = Call(
            id=call_id,
            call_type=CallType.BUSINESS_INTAKE,
            from_number=os.getenv("ELEVENLABS_PHONE_NUMBER_ID", ""),
            to_number=business_phone,
            business_id=business_id,
            status=CallStatus.INITIATED,
            ai_extracted_data={"initial_message": initial_message}
        )
        
        fs.collection("calls").document(call_id).set(call_record.model_dump())
        
        # Initiate call via ElevenLabs
        try:
            self.elevenlabs_client.conversational_ai.twilio.outbound_call(
                agent_id=self.elevenlabs_agent_id,
                agent_phone_number_id=self.elevenlabs_phone_id,
                to_number=business_phone,
                conversation_initiation_client_data=ConversationInitiationClientDataRequestInput(
                    user_id=business_id or business_phone,
                    dynamic_variables={
                        "call_type": "business_inbound",
                        "initial_message": initial_message,
                    },
                ),
            )
            
            print(f"✅ [BUSINESS_INTAKE] Initiated call to {business_phone} (call_id: {call_id})")
            return call_id
            
        except Exception as e:
            print(f"❌ [BUSINESS_INTAKE] Error initiating call: {e}")
            # Update call status
            fs.collection("calls").document(call_id).update({
                "status": CallStatus.FAILED.value
            })
            raise
    
    async def extract_requirements_from_call(self, call_id: str, transcript: str) -> Dict:
        """
        Extract structured requirements from call transcript using AI.
        
        Args:
            call_id: Call ID
            transcript: Call transcript
        
        Returns:
            Structured requirements dictionary
        """
        # Use Claude to extract structured data from transcript
        try:
            from anthropic import Anthropic
            
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            prompt = f"""Extract job requirements from this business intake call transcript:

{transcript}

Extract and return a JSON object with:
- role: Job role type (WAITER, HELPER, SALES, KITCHEN, DELIVERY, SECURITY, etc.)
- positions_count: Number of positions needed (integer)
- salary_min: Minimum salary (integer, in rupees)
- salary_max: Maximum salary (integer, in rupees)
- experience_required: Required experience (e.g., "Fresher", "1-2 years", "3-5 years")
- location: Job location/area
- shift_timing: Shift timing if mentioned
- requirements_notes: Any specific requirements mentioned
- interview_address: Interview address if mentioned
- interview_timing: Interview timing/availability

Return only valid JSON, no markdown formatting."""

            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            requirements_text = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if requirements_text.startswith("```"):
                requirements_text = requirements_text.split("```")[1]
                if requirements_text.startswith("json"):
                    requirements_text = requirements_text[4:]
            requirements = json.loads(requirements_text)
            
            # Update call record with extracted data
            fs.collection("calls").document(call_id).update({
                "transcript": transcript,
                "ai_extracted_data": requirements,
                "status": CallStatus.COMPLETED.value
            })
            
            print(f"✅ [BUSINESS_INTAKE] Extracted requirements from call {call_id}")
            return requirements
            
        except Exception as e:
            print(f"❌ [BUSINESS_INTAKE] Error extracting requirements: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def create_or_update_business(self, phone: str, name: str = "", contact_person: str = "") -> str:
        """
        Create or update business record.
        
        Args:
            phone: Business phone number
            name: Business name
            contact_person: Contact person name
        
        Returns:
            Business ID
        """
        # Normalize phone
        phone_clean = phone.replace("+", "").replace("-", "").replace(" ", "")
        business_id = f"business_{phone_clean}"
        
        business_doc = fs.collection("businesses").document(business_id).get()
        
        if business_doc.exists:
            # Update existing
            fs.collection("businesses").document(business_id).update({
                "name": name or business_doc.to_dict().get("name", ""),
                "contact_person": contact_person or business_doc.to_dict().get("contact_person", ""),
            })
            print(f"✅ [BUSINESS_INTAKE] Updated business: {business_id}")
        else:
            # Create new
            business_data = Business(
                id=business_id,
                phone=phone_clean,
                name=name,
                contact_person=contact_person,
                business_type="OTHER",
                area="",
                address=""
            )
            fs.collection("businesses").document(business_id).set(business_data.model_dump())
            print(f"✅ [BUSINESS_INTAKE] Created business: {business_id}")
        
        return business_id


business_intake_service = BusinessIntakeService()
