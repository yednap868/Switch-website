#!/usr/bin/env python3
"""
Script to send intro notification and update user profile.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from utils.db import get_user_profile, save_data_merge

def send_intro_notification():
    """Send intro notification to candidate and mark Rishabh as job provider."""
    # Candidate who will receive the intro
    candidate_uid = "917486949525"
    
    # Job provider details
    job_provider_phone = "+918130378953"  # Normalize: remove +, spaces
    job_provider_uid = job_provider_phone.replace("+", "").replace(" ", "").replace("-", "")
    
    job_provider_name = "Rishabh Verma"
    job_provider_linkedin = "https://www.linkedin.com/in/vrishabh955/"
    
    print(f"=" * 70)
    print(f"SENDING INTRO NOTIFICATION")
    print(f"=" * 70)
    print(f"Candidate UID: {candidate_uid}")
    print(f"Job Provider UID: {job_provider_uid}")
    print(f"Job Provider Name: {job_provider_name}")
    print(f"Job Provider LinkedIn: {job_provider_linkedin}")
    print()
    
    # 1. Send intro notification to candidate
    message = f"You have been introduced to {job_provider_name}, LinkedIn - {job_provider_linkedin}"
    
    print(f"📤 Sending message to candidate {candidate_uid}...")
    try:
        message_data = MsgComponents.text_scaffold(to=candidate_uid, text=message)
        result = WhatsAppSender.send(message_data)
        
        if isinstance(result, dict) and result.get("status") == "success":
            message_id = result.get("message_id")
            print(f"✅ Message sent successfully! Message ID: {message_id}")
        else:
            error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else str(result)
            print(f"❌ Failed to send message: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # 2. Mark Rishabh as job provider
    print(f"👤 Updating user profile for {job_provider_uid}...")
    try:
        # Get existing profile
        existing_profile = get_user_profile(job_provider_uid) or {}
        
        # Update profile with job provider info
        update_data = {
            "user_type": "job_provider",
            "connection_type": "hiring engineers",
            "name": job_provider_name,
            "linkedin_url": job_provider_linkedin,
        }
        
        # If profile exists, merge the update
        if existing_profile:
            print(f"   Existing profile found, updating...")
            save_data_merge(job_provider_uid, "users", update_data)
        else:
            print(f"   No existing profile, creating new one...")
            # Create new profile
            from utils.db import fs
            fs.collection("users").document(job_provider_uid).set(update_data, merge=True)
        
        print(f"✅ User profile updated successfully!")
        print(f"   User type: job_provider")
        print(f"   Connection type: hiring engineers")
        print(f"   Name: {job_provider_name}")
        print(f"   LinkedIn: {job_provider_linkedin}")
        
    except Exception as e:
        print(f"❌ Error updating user profile: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print(f"=" * 70)
    print(f"✅ COMPLETED SUCCESSFULLY")
    print(f"=" * 70)
    return True

if __name__ == "__main__":
    success = send_intro_notification()
    sys.exit(0 if success else 1)

