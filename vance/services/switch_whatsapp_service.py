"""
Service for sending WhatsApp messages with templates.
"""

import base64
import io
import os
import time
from typing import List

import requests

from utils.db import fs
from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from models.switch_models import Candidate, Job, Business


class SwitchWhatsAppService:
    """Service for WhatsApp messaging with templates."""
    
    
    async def send_candidate_profiles(
        self,
        business_id: str,
        candidates: List[Candidate],
        job_id: str
    ):
        """
        Send formatted candidate profile cards to business.
        
        Format:
        🎯 Candidates for [Role] position:
        
        1️⃣ [Name]
        📍 [Area] | 💼 [Experience]
        💰 Expected: [Salary]
        🏢 Previous: [Last employer]
        
        [Select button]
        """
        business_doc = fs.collection("businesses").document(business_id).get()
        if not business_doc.exists:
            return
        
        business_data = business_doc.to_dict()
        business_phone = business_data.get("phone", "")
        
        job_doc = fs.collection("jobs").document(job_id).get()
        if not job_doc.exists:
            return
        
        job = Job(**job_doc.to_dict())

        # Format phone for WhatsApp
        if not business_phone.startswith('+'):
            if business_phone.startswith('91'):
                business_phone = '+' + business_phone
            else:
                business_phone = '+91' + business_phone
        wa_phone = business_phone.lstrip("+")

        message = f"🎯 Candidates for {job.role} position:\n\n"

        for i, candidate in enumerate(candidates, 1):
            # Send candidate photo before the text card
            self._send_candidate_photo(wa_phone, candidate)

            emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i-1] if i <= 5 else f"{i}."
            message += f"{emoji} {candidate.name}\n"
            message += f"📍 {candidate.area or 'Sec 24, Gurgaon'} | 💼 {candidate.experience_level or '1+ years'}\n"
            salary_min = candidate.expected_salary_min or 15000
            salary_max = candidate.expected_salary_max or 15000
            message += f"💰 Expected: ₹{salary_min:,} - ₹{salary_max:,}\n"

            if candidate.previous_employers:
                message += f"🏢 Previous: {', '.join(candidate.previous_employers[:2])}\n"

            message += "\n"

        message += "---\n"
        message += "Reply with candidate number to schedule interview."

        try:
            message_data = MsgComponents.text_scaffold(to=wa_phone, text=message)
            result = WhatsAppSender.send(message_data)
            if result.get("status") == "success":
                print(f"✅ [WHATSAPP] Sent candidate profiles to business {business_id}")
            else:
                print(f"❌ [WHATSAPP] Error sending profiles: {result.get('error')}")
        except Exception as e:
            print(f"❌ [WHATSAPP] Error sending profiles: {e}")

    def _send_candidate_photo(self, recipient_phone: str, candidate: Candidate) -> None:
        """Send Switch candidate's profile photo to the recipient via WhatsApp.

        Photo lookup order:
        1. candidate.photo_url from the candidates collection (new system)
        2. switch_users/{candidate.id} → profile.photoURL (old system)
        """
        try:
            photo_data = self._get_candidate_photo(candidate)
            if not photo_data:
                print(f"ℹ️ [SWITCH_PHOTO] No photo for candidate {candidate.id}")
                return

            image_bytes, content_type = photo_data

            phone_number_id = os.getenv("PHONE_NUMBER_ID")
            access_token = os.getenv("META_SYS_USER_TOKEN")
            if not phone_number_id or not access_token:
                print("⚠️ [SWITCH_PHOTO] Missing WhatsApp credentials")
                return

            ext = content_type.split("/")[-1] if "/" in content_type else "jpeg"
            upload_url = f"https://graph.facebook.com/v16.0/{phone_number_id}/media"
            files = {
                "file": (f"profile.{ext}", io.BytesIO(image_bytes), content_type)
            }
            data = {"messaging_product": "whatsapp", "type": "image"}
            headers = {"Authorization": f"Bearer {access_token}"}

            upload_resp = requests.post(
                upload_url, headers=headers, files=files, data=data, timeout=60
            )
            if upload_resp.status_code != 200:
                print(f"❌ [SWITCH_PHOTO] Upload failed: {upload_resp.status_code}")
                return

            media_id = upload_resp.json().get("id")
            if not media_id:
                print("❌ [SWITCH_PHOTO] No media_id in upload response")
                return

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "image",
                "image": {
                    "id": media_id,
                    "caption": f"📸 {candidate.name}",
                },
            }
            WhatsAppSender.send(payload)
            print(f"✅ [SWITCH_PHOTO] Sent photo for {candidate.name} to {recipient_phone}")

        except Exception as e:
            print(f"⚠️ [SWITCH_PHOTO] Error sending photo for {candidate.id}: {e}")

    def _get_candidate_photo(self, candidate: Candidate) -> tuple | None:
        """Fetch candidate photo bytes and content type.

        Returns (image_bytes, content_type) or None.
        Checks candidates collection (photo_url) then switch_users (profile.photoURL).
        """
        # 1. Check photo_url from Candidate model (new candidates collection)
        if candidate.photo_url:
            photo_url = candidate.photo_url
            if photo_url.startswith("data:"):
                return self._decode_base64_data_url(photo_url)
            # Regular URL - download it
            try:
                resp = requests.get(photo_url, timeout=30)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "image/jpeg")
                    return resp.content, content_type
            except Exception as e:
                print(f"⚠️ [SWITCH_PHOTO] Failed to download {photo_url}: {e}")

        # 2. Fallback: switch_users collection (old system)
        try:
            sw_doc = fs.collection("switch_users").document(candidate.id).get()
            if sw_doc.exists:
                sw_data = sw_doc.to_dict() or {}
                photo_data_url = sw_data.get("profile", {}).get("photoURL", "")
                if photo_data_url and photo_data_url.startswith("data:"):
                    return self._decode_base64_data_url(photo_data_url)
        except Exception as e:
            print(f"⚠️ [SWITCH_PHOTO] switch_users lookup failed for {candidate.id}: {e}")

        return None

    @staticmethod
    def _decode_base64_data_url(data_url: str) -> tuple | None:
        """Decode a base64 data URL into (bytes, content_type)."""
        try:
            header, encoded = data_url.split(",", 1)
            content_type = header.split(";")[0].replace("data:", "")
            image_bytes = base64.b64decode(encoded)
            return image_bytes, content_type
        except Exception as e:
            print(f"⚠️ [SWITCH_PHOTO] Failed to decode data URL: {e}")
            return None

    async def send_interview_confirmation(
        self,
        candidate_id: str,
        job: Job
    ):
        """
        Send interview confirmation message to candidate via WhatsApp template.
        Falls back to text message if template fails.
        """
        candidate_doc = fs.collection("candidates").document(candidate_id).get()
        if not candidate_doc.exists:
            return

        candidate = Candidate(**candidate_doc.to_dict())
        candidate_phone = candidate.phone

        business_doc = fs.collection("businesses").document(job.business_id).get()
        business_name = business_doc.to_dict().get("name", "Business") if business_doc.exists else "Business"

        # Format phone
        if not candidate_phone.startswith('+'):
            if candidate_phone.startswith('91'):
                candidate_phone = '+' + candidate_phone
            else:
                candidate_phone = '+91' + candidate_phone

        # Clean phone for WhatsApp API (remove +)
        wa_phone = candidate_phone.lstrip("+")

        interview_timing = job.interview_timing or "TBD"
        interview_address = job.interview_address or "TBD"
        role = job.role or "Open Position"
        salary = f"₹{job.salary_min:,} - ₹{job.salary_max:,}"

        # Try sending via WhatsApp template first
        try:
            template_payload = MsgComponents.template_scaffold(
                to=wa_phone,
                template_name="interview_confirmation",
                language_code="en",
                body_parameters=[
                    business_name,
                    role,
                    interview_timing,
                    interview_address,
                    salary,
                ],
            )
            result = WhatsAppSender.send(template_payload)
            if result.get("status") == "success":
                print(f"✅ [WHATSAPP] Sent interview template to candidate {candidate_id}")
                return
            print(f"⚠️ [WHATSAPP] Template failed, falling back to text: {result.get('error')}")
        except Exception as e:
            print(f"⚠️ [WHATSAPP] Template error, falling back to text: {e}")

        # Fallback to text message
        message = "✅ Interview Confirmed!\n\n"
        message += f"🏢 {business_name}\n"
        message += f"📍 {interview_address}\n"
        message += f"🗓️ {interview_timing}\n"
        message += f"💼 Role: {role}\n"
        message += f"💰 Salary: {salary}\n\n"
        message += "Reply YES to confirm attendance."

        try:
            message_data = MsgComponents.text_scaffold(to=wa_phone, text=message)
            result = WhatsAppSender.send(message_data)
            if result.get("status") == "success":
                print(f"✅ [WHATSAPP] Sent interview text confirmation to candidate {candidate_id}")
            else:
                print(f"❌ [WHATSAPP] Error sending confirmation: {result.get('error')}")
        except Exception as e:
            print(f"❌ [WHATSAPP] Error sending confirmation: {e}")
    
    async def send_business_confirmation(
        self,
        business_id: str,
        candidate: Candidate,
        job: Job
    ):
        """
        Send confirmation to business when candidate confirms interview.
        
        Format:
        ✅ [Candidate Name] confirmed for interview
        
        🗓️ [Date & Time]
        📱 Candidate contact: [Number]
        
        They'll arrive at your location. Payment of ₹2,000 after successful joining.
        """
        business_doc = fs.collection("businesses").document(business_id).get()
        if not business_doc.exists:
            return
        
        business_data = business_doc.to_dict()
        business_phone = business_data.get("phone", "")
        
        message = f"✅ {candidate.name} confirmed for interview\n\n"
        message += f"🗓️ {job.interview_timing or 'TBD'}\n"
        message += f"📱 Candidate contact: {candidate.phone}\n\n"
        message += "They'll arrive at your location. Payment of ₹2,000 after successful joining."
        
        # Format phone
        if not business_phone.startswith('+'):
            if business_phone.startswith('91'):
                business_phone = '+' + business_phone
            else:
                business_phone = '+91' + business_phone
        
        try:
            message_data = MsgComponents.text_scaffold(to=business_phone, text=message)
            result = WhatsAppSender.send(message_data)
            if result.get("status") == "success":
                print(f"✅ [WHATSAPP] Sent confirmation to business {business_id}")
            else:
                print(f"❌ [WHATSAPP] Error sending business confirmation: {result.get('error')}")
        except Exception as e:
            print(f"❌ [WHATSAPP] Error sending business confirmation: {e}")


switch_whatsapp_service = SwitchWhatsAppService()
