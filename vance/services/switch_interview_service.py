"""
Switch Interview Scheduling Service.
Handles the flow when a business selects a candidate for interview.
"""

import re
import time
from typing import Optional, Tuple
from dataclasses import dataclass

from utils.db import fs
from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from services.switch_matching_service import SwitchCandidate


@dataclass
class InterviewState:
    """Tracks the interview scheduling state for a business."""
    business_phone: str
    selected_candidate_id: str
    selected_candidate_name: str
    selected_candidate_phone: str
    candidate_area: str
    candidate_experience: str
    job_role: str
    job_salary_min: int
    job_salary_max: int
    business_name: str
    step: str  # "awaiting_datetime", "awaiting_location", "completed"
    interview_datetime: Optional[str] = None
    interview_location: Optional[str] = None
    created_at: float = 0


class SwitchInterviewService:
    """Service for handling interview scheduling flow."""

    def parse_candidate_selection(self, message_text: str) -> Optional[int]:
        """
        Parse candidate selection from message.
        Returns candidate number (1, 2, 3, etc.) or None if not a selection.

        Examples:
        - "YES 1" -> 1
        - "yes 2" -> 2
        - "1" -> 1
        - "1st theek hai" -> 1
        - "2nd wala" -> 2
        - "select 3" -> 3
        - "pehla wala" -> 1
        - "dusra" -> 2
        - "teesra" -> 3
        """
        message_lower = message_text.lower().strip()
        print(f"🔍 [INTERVIEW] Parsing selection from: '{message_lower}'")

        # English ordinals (1st, 2nd, 3rd)
        ordinal_patterns = [
            (r"1st|first", 1),
            (r"2nd|second", 2),
            (r"3rd|third", 3),
            (r"4th|fourth", 4),
            (r"5th|fifth", 5),
        ]

        for pattern, num in ordinal_patterns:
            if re.search(pattern, message_lower):
                print(f"🔍 [INTERVIEW] Matched ordinal pattern '{pattern}' -> {num}")
                return num

        # Hindi ordinals
        hindi_ordinals = {
            "pehla": 1, "pehli": 1, "pahla": 1, "pahli": 1, "pehle": 1,
            "dusra": 2, "dusri": 2, "doosra": 2, "dusre": 2,
            "teesra": 3, "teesri": 3, "tisra": 3, "teesre": 3,
            "chautha": 4, "chauthi": 4,
            "panchwa": 5, "panchvi": 5,
        }

        for word, num in hindi_ordinals.items():
            if word in message_lower:
                print(f"🔍 [INTERVIEW] Matched Hindi ordinal '{word}' -> {num}")
                return num

        # Common confirmation patterns with numbers
        # "1 theek hai", "2 ok", "3 chalega", etc.
        confirmation_pattern = r"^(\d+)\s*(theek|thik|ok|okay|chalega|done|select|wala|number|no\.?|num)?"
        match = re.search(confirmation_pattern, message_lower)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                print(f"🔍 [INTERVIEW] Matched confirmation pattern -> {num}")
                return num

        # Pattern: "YES 1", "yes 2", "select 1", etc.
        patterns = [
            r"yes\s*(\d+)",
            r"(\d+)\s*yes",
            r"select\s*(\d+)",
            r"(\d+)\s*select",
            r"choose\s*(\d+)",
            r"(\d+)\s*choose",
            r"candidate\s*(\d+)",
            r"number\s*(\d+)",
            r"no\.?\s*(\d+)",
            r"#\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                num = int(match.group(1))
                print(f"🔍 [INTERVIEW] Matched pattern '{pattern}' -> {num}")
                return num

        # Last resort: any single digit at start or end of message
        start_num = re.match(r"^(\d)\b", message_lower)
        if start_num:
            num = int(start_num.group(1))
            if 1 <= num <= 5:
                print(f"🔍 [INTERVIEW] Matched start number -> {num}")
                return num

        print(f"🔍 [INTERVIEW] No selection pattern matched")
        return None

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for consistent storage/lookup."""
        return phone.replace("+", "").replace("-", "").replace(" ", "")

    def get_pending_candidates(self, business_phone: str) -> list:
        """
        Get the list of candidates that were sent to this business.
        Stored in Firestore under business_pending_candidates collection.
        """
        phone_normalized = self._normalize_phone(business_phone)
        print(f"🔍 [INTERVIEW] Getting pending candidates for: {phone_normalized}")
        try:
            doc = fs.collection("business_pending_candidates").document(phone_normalized).get()
            if doc.exists:
                data = doc.to_dict()
                candidates = data.get("candidates", [])
                print(f"🔍 [INTERVIEW] Found {len(candidates)} pending candidates")
                return candidates
            else:
                print(f"🔍 [INTERVIEW] No pending candidates document found")
        except Exception as e:
            print(f"❌ [INTERVIEW] Error getting pending candidates: {e}")
        return []

    def store_pending_candidates(self, business_phone: str, candidates: list):
        """
        Store the list of candidates sent to a business.
        Called after sending profile cards.
        """
        phone_normalized = self._normalize_phone(business_phone)
        print(f"📝 [INTERVIEW] Storing candidates for: {phone_normalized}")
        try:
            candidate_data = []
            for c in candidates:
                if isinstance(c, SwitchCandidate):
                    candidate_data.append({
                        "id": c.id,
                        "phone": c.phone,
                        "name": c.name,
                        "area": c.area,
                        "experience_level": c.experience_level,
                        "expected_salary_min": c.expected_salary_min,
                        "expected_salary_max": c.expected_salary_max,
                    })
                elif isinstance(c, dict):
                    candidate_data.append(c)

            fs.collection("business_pending_candidates").document(phone_normalized).set({
                "candidates": candidate_data,
                "sent_at": time.time(),
            })
            print(f"✅ [INTERVIEW] Stored {len(candidate_data)} pending candidates for {phone_normalized}")
        except Exception as e:
            print(f"❌ [INTERVIEW] Error storing pending candidates: {e}")
            import traceback
            traceback.print_exc()

    def get_interview_state(self, business_phone: str) -> Optional[InterviewState]:
        """Get current interview scheduling state for a business."""
        phone_normalized = self._normalize_phone(business_phone)
        try:
            doc = fs.collection("interview_scheduling").document(phone_normalized).get()
            if doc.exists:
                data = doc.to_dict()
                return InterviewState(
                    business_phone=data.get("business_phone", business_phone),
                    selected_candidate_id=data.get("selected_candidate_id", ""),
                    selected_candidate_name=data.get("selected_candidate_name", ""),
                    selected_candidate_phone=data.get("selected_candidate_phone", ""),
                    candidate_area=data.get("candidate_area", ""),
                    candidate_experience=data.get("candidate_experience", ""),
                    job_role=data.get("job_role", "Staff"),
                    job_salary_min=data.get("job_salary_min", 8000),
                    job_salary_max=data.get("job_salary_max", 15000),
                    business_name=data.get("business_name", ""),
                    step=data.get("step", "awaiting_datetime"),
                    interview_datetime=data.get("interview_datetime"),
                    interview_location=data.get("interview_location"),
                    created_at=data.get("created_at", 0),
                )
        except Exception as e:
            print(f"❌ [INTERVIEW] Error getting interview state: {e}")
        return None

    def set_interview_state(self, state: InterviewState):
        """Save interview scheduling state."""
        phone_normalized = self._normalize_phone(state.business_phone)
        try:
            fs.collection("interview_scheduling").document(phone_normalized).set({
                "business_phone": state.business_phone,
                "selected_candidate_id": state.selected_candidate_id,
                "selected_candidate_name": state.selected_candidate_name,
                "selected_candidate_phone": state.selected_candidate_phone,
                "candidate_area": state.candidate_area,
                "candidate_experience": state.candidate_experience,
                "job_role": state.job_role,
                "job_salary_min": state.job_salary_min,
                "job_salary_max": state.job_salary_max,
                "business_name": state.business_name,
                "step": state.step,
                "interview_datetime": state.interview_datetime,
                "interview_location": state.interview_location,
                "created_at": state.created_at or time.time(),
            })
            print(f"✅ [INTERVIEW] Saved interview state for {state.business_phone}, step: {state.step}")
        except Exception as e:
            print(f"❌ [INTERVIEW] Error saving interview state: {e}")

    def clear_interview_state(self, business_phone: str):
        """Clear interview scheduling state after completion."""
        phone_normalized = self._normalize_phone(business_phone)
        try:
            fs.collection("interview_scheduling").document(phone_normalized).delete()
            print(f"✅ [INTERVIEW] Cleared interview state for {business_phone}")
        except Exception as e:
            print(f"❌ [INTERVIEW] Error clearing interview state: {e}")

    def start_interview_scheduling(
        self,
        business_phone: str,
        candidate_index: int,
        business_name: str = "",
        job_role: str = "Staff",
        salary_min: int = 8000,
        salary_max: int = 15000,
    ) -> Tuple[bool, str]:
        """
        Start the interview scheduling flow for a selected candidate.
        Returns (success, response_message).
        """
        # Get pending candidates
        candidates = self.get_pending_candidates(business_phone)

        if not candidates:
            return False, "Abhi koi candidates pending nahi hai. Pehle 'bhejo' likh ke candidates mangao! 😊"

        if candidate_index < 1 or candidate_index > len(candidates):
            return False, f"Candidate {candidate_index} nahi mila. {len(candidates)} candidates bheje the - 1 se {len(candidates)} mein se choose karo."

        candidate = candidates[candidate_index - 1]

        # Get business name from Firestore if not provided
        if not business_name:
            try:
                phone_clean = business_phone.replace("+", "").replace("-", "").replace(" ", "")
                business_docs = fs.collection("businesses").where("phone", "==", phone_clean).limit(1).stream()
                for doc in business_docs:
                    business_data = doc.to_dict()
                    business_name = business_data.get("name", "") or business_data.get("contact_person", "")
                    break
            except Exception as e:
                print(f"⚠️ [INTERVIEW] Could not get business name: {e}")

        if not business_name:
            business_name = "Your Business"

        # Create interview state
        state = InterviewState(
            business_phone=business_phone,
            selected_candidate_id=candidate.get("id", ""),
            selected_candidate_name=candidate.get("name", "Candidate"),
            selected_candidate_phone=candidate.get("phone", ""),
            candidate_area=candidate.get("area", ""),
            candidate_experience=candidate.get("experience_level", ""),
            job_role=job_role,
            job_salary_min=salary_min,
            job_salary_max=salary_max,
            business_name=business_name,
            step="awaiting_datetime",
            created_at=time.time(),
        )

        self.set_interview_state(state)

        # Ask for interview date/time
        response = f"*{candidate.get('name', 'Candidate')}* ko select kar liya! 👍\n\n"
        response += "Ab interview ka date aur time batao.\n"
        response += "Example: *Kal 11 baje* ya *Monday 3 PM*"

        return True, response

    def handle_interview_datetime(self, business_phone: str, datetime_text: str) -> Tuple[bool, str]:
        """
        Handle when business provides interview date/time.
        Returns (success, response_message).
        """
        state = self.get_interview_state(business_phone)

        if not state or state.step != "awaiting_datetime":
            return False, ""

        # Store the datetime
        state.interview_datetime = datetime_text
        state.step = "awaiting_location"
        self.set_interview_state(state)

        # Ask for location
        response = f"Date/Time: *{datetime_text}* ✅\n\n"
        response += "Ab interview ki location/address batao.\n"
        response += "Example: *CP Metro ke paas, ABC Restaurant*"

        return True, response

    def handle_interview_location(self, business_phone: str, location_text: str) -> Tuple[bool, str]:
        """
        Handle when business provides interview location.
        Sends confirmation to candidate and completes the flow.
        Returns (success, response_message).
        """
        state = self.get_interview_state(business_phone)

        if not state or state.step != "awaiting_location":
            return False, ""

        # Store the location
        state.interview_location = location_text
        state.step = "completed"
        self.set_interview_state(state)

        # Send message to candidate
        candidate_message_sent = self.send_interview_to_candidate(state)

        # Create job application record
        self.create_interview_application(state)

        # Clear interview state
        self.clear_interview_state(business_phone)

        # Clear pending candidates
        try:
            phone_normalized = self._normalize_phone(business_phone)
            fs.collection("business_pending_candidates").document(phone_normalized).delete()
        except Exception:
            pass

        # Response to business
        if candidate_message_sent:
            response = "Interview fix ho gaya! ✅\n\n"
            response += f"*{state.selected_candidate_name}* ko message bhej diya:\n"
            response += f"📍 {location_text}\n"
            response += f"🗓️ {state.interview_datetime}\n\n"
            response += "Woh aa jayega. Joining ke baad ₹2000 payment kar dena.\n\n"
            response += "Kuch aur chahiye toh batao! 😊"
        else:
            response = "Interview schedule ho gaya! ✅\n\n"
            response += f"Candidate ko message bhejne mein issue hua, par details yeh hai:\n"
            response += f"📍 {location_text}\n"
            response += f"🗓️ {state.interview_datetime}\n\n"
            response += f"Candidate: {state.selected_candidate_name}\n"
            response += f"Phone: {state.selected_candidate_phone}"

        return True, response

    def send_interview_to_candidate(self, state: InterviewState) -> bool:
        """
        Send interview confirmation message to candidate.
        Returns True if sent successfully.
        """
        candidate_phone = state.selected_candidate_phone

        if not candidate_phone:
            print(f"❌ [INTERVIEW] No candidate phone number")
            return False

        # Format phone for WhatsApp
        if not candidate_phone.startswith('+'):
            if candidate_phone.startswith('91'):
                candidate_phone = '+' + candidate_phone
            else:
                candidate_phone = '+91' + candidate_phone

        # Create congratulations message
        message = "🎉 *Badhai ho! Interview fix ho gaya!*\n\n"
        message += f"🏢 *{state.business_name}*\n"
        message += f"💼 Role: {state.job_role}\n"
        message += f"💰 Salary: ₹{state.job_salary_min:,} - ₹{state.job_salary_max:,}/month\n"
        message += f"📍 Location: {state.interview_location}\n"
        message += f"🗓️ Date/Time: {state.interview_datetime}\n\n"
        message += "⚠️ *Important:* Interview pe zaroor jaana. Nahi aane pe fine lagega!\n\n"
        message += "Koi sawaal ho toh yahan reply karo. Good luck! 💪"

        try:
            sender = WhatsAppSender()
            message_data = MsgComponents.text_scaffold(to=candidate_phone, text=message)
            result = sender.send(message_data)

            if result.get("status") == "success":
                print(f"✅ [INTERVIEW] Sent interview confirmation to {candidate_phone}")
                return True
            else:
                print(f"❌ [INTERVIEW] Failed to send to candidate: {result.get('error')}")
                return False

        except Exception as e:
            print(f"❌ [INTERVIEW] Error sending to candidate: {e}")
            return False

    def create_interview_application(self, state: InterviewState):
        """Create a job application record for tracking."""
        try:
            application_id = f"app_{state.selected_candidate_id}_{int(time.time())}"

            fs.collection("job_applications").document(application_id).set({
                "id": application_id,
                "business_phone": state.business_phone,
                "business_name": state.business_name,
                "candidate_id": state.selected_candidate_id,
                "candidate_name": state.selected_candidate_name,
                "candidate_phone": state.selected_candidate_phone,
                "job_role": state.job_role,
                "salary_min": state.job_salary_min,
                "salary_max": state.job_salary_max,
                "interview_datetime": state.interview_datetime,
                "interview_location": state.interview_location,
                "status": "INTERVIEW_SCHEDULED",
                "source": "BUSINESS_SELECT",
                "created_at": time.time(),
            })
            print(f"✅ [INTERVIEW] Created application record: {application_id}")

        except Exception as e:
            print(f"❌ [INTERVIEW] Error creating application: {e}")

    def handle_message(self, business_phone: str, message_text: str) -> Optional[str]:
        """
        Main handler for interview scheduling messages.
        Returns response string if this message is part of interview flow, None otherwise.
        """
        print(f"🔍 [INTERVIEW] handle_message called: phone={business_phone}, msg='{message_text[:50]}'")

        # Normalize phone number - remove + prefix for consistent lookup
        phone_normalized = business_phone.replace("+", "").replace("-", "").replace(" ", "")
        print(f"🔍 [INTERVIEW] Normalized phone: {phone_normalized}")

        # Check if there's an active interview scheduling session
        state = self.get_interview_state(phone_normalized)
        print(f"🔍 [INTERVIEW] Interview state: {state.step if state else 'None'}")

        if state:
            # We're in an active interview scheduling flow
            if state.step == "awaiting_datetime":
                success, response = self.handle_interview_datetime(phone_normalized, message_text)
                if success:
                    return response

            elif state.step == "awaiting_location":
                success, response = self.handle_interview_location(phone_normalized, message_text)
                if success:
                    return response

        # Check if this is a candidate selection
        candidate_num = self.parse_candidate_selection(message_text)
        print(f"🔍 [INTERVIEW] Parsed candidate number: {candidate_num}")

        if candidate_num:
            # Check pending candidates
            pending = self.get_pending_candidates(phone_normalized)
            print(f"🔍 [INTERVIEW] Pending candidates for {phone_normalized}: {len(pending)}")

            success, response = self.start_interview_scheduling(phone_normalized, candidate_num)
            print(f"🔍 [INTERVIEW] start_interview_scheduling result: success={success}")
            if success:
                return response
            else:
                return response  # Return error message too

        print(f"🔍 [INTERVIEW] No interview action taken, returning None")
        return None


# Singleton instance
switch_interview_service = SwitchInterviewService()
