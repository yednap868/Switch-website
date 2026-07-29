#!/usr/bin/env python3
"""
Script to send introduction messages to candidates about Rishabh Verma.
Uses the profile_introduction template.
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from utils.db import get_user_profile, fs
from api.whatsapp_modules.conversation_history import conversation_history
from services.interview_scheduling_service import get_job_provider_description


async def send_intro_to_candidate(candidate_uid: str, candidate_name: str, job_provider_uid: str, job_provider_name: str, job_provider_linkedin: str = ""):
    """Send introduction message to a candidate."""
    print(f"\n{'='*70}")
    print(f"Sending intro to {candidate_name} (uid: {candidate_uid})")
    print(f"{'='*70}")
    
    # Get candidate's WhatsApp ID
    candidate_profile = get_user_profile(candidate_uid) or {}
    candidate_wa_id = (
        candidate_profile.get("wa_id")
        or candidate_profile.get("phone")
        or candidate_profile.get("whatsapp")
        or candidate_uid
    )
    
    print(f"Candidate WhatsApp ID: {candidate_wa_id}")
    
    # Get job provider's extraction data
    extraction_doc = fs.collection("extractions").document(job_provider_uid).get()
    extraction_data = extraction_doc.to_dict() if extraction_doc.exists else {}
    
    # Get job provider description
    try:
        job_provider_description = await get_job_provider_description(
            job_provider_uid=job_provider_uid,
            job_provider_name=job_provider_name,
            extraction_data=extraction_data,
            linkedin_url=job_provider_linkedin,
        )
    except Exception as e:
        print(f"⚠️  Could not get job provider description: {e}")
        job_provider_description = "a job provider"
    
    # Build the message text for logging
    if job_provider_linkedin:
        text = f"You have been introduced to {job_provider_name}, LinkedIn - {job_provider_linkedin}"
    else:
        text = f"You have been introduced to {job_provider_name}"
    
    # Build job provider string for template (include LinkedIn if available)
    # Template format: "Hey name, I just introduced you to job_provider_name..."
    job_provider_string = job_provider_name
    if job_provider_linkedin:
        job_provider_string += f", LinkedIn - {job_provider_linkedin}"
    
    # Send template message (24-hour window has passed, must use template)
    try:
        # Template has 2 parameters: [name, job_provider_name]
        template_payload = MsgComponents.template_scaffold(
            to=candidate_wa_id,
            template_name="profile_introduction",
            language_code="en",
            body_parameters=[candidate_name, job_provider_string],
        )
        result = WhatsAppSender.send(template_payload)
        success = result.get("status") == "success"
        
        if success:
            print(f"✅ Template message sent successfully")
            
            # Log to conversation history
            conversation_history.save_message(
                user_id=candidate_wa_id,
                sender="agent",
                content=text,
                message_type="text",
                metadata={
                    "notification_type": "profile_introduction",
                    "job_provider": job_provider_name,
                    "job_provider_uid": job_provider_uid,
                    "used_template": True,
                },
            )
            
            # Update intro count
            intro_count_doc = fs.collection("candidate_intro_count").document(candidate_wa_id).get()
            if intro_count_doc.exists:
                intro_data = intro_count_doc.to_dict() or {}
                fs.collection("candidate_intro_count").document(candidate_wa_id).update({
                    "count": intro_data.get("count", 0) + 1,
                })
            else:
                import time
                fs.collection("candidate_intro_count").document(candidate_wa_id).set({
                    "count": 1,
                    "first_intro_at": time.time(),
                })
            
            return True
        else:
            error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
            print(f"⚠️ Template failed ({error_msg}), falling back to text message...")
            
            # Fallback to text message
            text_message = (
                f"Hey {candidate_name},\n\n"
                f"I just introduced you to {job_provider_name}"
            )
            if job_provider_linkedin:
                text_message += f" ({job_provider_linkedin})"
            text_message += (
                "\nYour profile matches what they're looking for, so this could move fast. "
                "They'll take a look and reply soon. I'll keep track on my side as well 🚀"
            )
            
            text_payload = MsgComponents.text_scaffold(to=candidate_wa_id, text=text_message)
            text_result = WhatsAppSender.send(text_payload)
            text_success = text_result.get("status") == "success"
            
            if text_success:
                print(f"✅ Fallback text message sent successfully")
                conversation_history.save_message(
                    user_id=candidate_wa_id,
                    sender="agent",
                    content=text_message,
                    message_type="text",
                    metadata={
                        "notification_type": "profile_introduction",
                        "job_provider": job_provider_name,
                        "job_provider_uid": job_provider_uid,
                        "used_template": False,
                        "template_fallback": True,
                    },
                )
                return True
            else:
                print(f"❌ Fallback text message also failed: {text_result}")
                return False
            
    except Exception as e:
        print(f"❌ Error sending template message: {e}")
        import traceback
        traceback.print_exc()
        
        # Try fallback text message
        try:
            text_message = (
                f"Hey {candidate_name},\n\n"
                f"I just introduced you to {job_provider_name}"
            )
            if job_provider_linkedin:
                text_message += f" ({job_provider_linkedin})"
            text_message += (
                "\nYour profile matches what they're looking for, so this could move fast. "
                "They'll take a look and reply soon. I'll keep track on my side as well 🚀"
            )
            
            text_payload = MsgComponents.text_scaffold(to=candidate_wa_id, text=text_message)
            text_result = WhatsAppSender.send(text_payload)
            if text_result.get("status") == "success":
                print(f"✅ Fallback text message sent successfully")
                conversation_history.save_message(
                    user_id=candidate_wa_id,
                    sender="agent",
                    content=text_message,
                    message_type="text",
                    metadata={
                        "notification_type": "profile_introduction",
                        "job_provider": job_provider_name,
                        "job_provider_uid": job_provider_uid,
                        "used_template": False,
                        "template_fallback": True,
                    },
                )
                return True
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
        
        return False


async def main():
    import time
    
    # Candidate UIDs
    candidates = {
        "Mahima Kaushik": "917048938186",
        "Irfan": "18624233940",
        "Ayush Gour": "917082024111",  # Found as "Ayush"
        "Mohd Sadiq": "919045508603",
    }
    
    # Job provider details
    job_provider_uid = "918130378953"
    job_provider_name = "Rishabh Verma"
    job_provider_linkedin = "https://www.linkedin.com/in/vrishabh955/"
    
    # Get job provider profile for LinkedIn
    job_provider_profile = get_user_profile(job_provider_uid) or {}
    if not job_provider_linkedin:
        job_provider_linkedin = job_provider_profile.get("linkedin_url", "")
    
    print("=" * 70)
    print("SENDING INTRO NOTIFICATIONS")
    print("=" * 70)
    print(f"\nJob Provider: {job_provider_name}")
    print(f"Job Provider UID: {job_provider_uid}")
    print(f"Job Provider LinkedIn: {job_provider_linkedin}")
    print(f"\nCandidates to notify: {len(candidates)}")
    
    results = []
    for candidate_name, candidate_uid in candidates.items():
        result = await send_intro_to_candidate(
            candidate_uid=candidate_uid,
            candidate_name=candidate_name,
            job_provider_uid=job_provider_uid,
            job_provider_name=job_provider_name,
            job_provider_linkedin=job_provider_linkedin,
        )
        results.append((candidate_name, result))
        
        # Small delay between messages
        await asyncio.sleep(1)
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("=" * 70)
    for candidate_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {candidate_name}: {'Sent' if result else 'Failed'}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

