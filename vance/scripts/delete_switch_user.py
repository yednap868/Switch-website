#!/usr/bin/env python3
"""
Delete Switch user data for a specific phone number.
This deletes data from switch_users collection and related collections.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def delete_switch_user(phone: str):
    """
    Delete all Switch user data for the given phone number.
    Phone number should be in format: 918368828660 (no + or spaces)
    """
    # Normalize phone (remove + and spaces)
    phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    user_id = phone  # user_id is the phone number
    
    print(f"🗑️  Deleting all data for phone: {phone} (user_id: {user_id})")
    print("=" * 70)
    
    deleted_count = 0
    
    # 1. Delete from switch_users collection
    try:
        switch_user_ref = fs.collection("switch_users").document(user_id)
        if switch_user_ref.get().exists:
            switch_user_ref.delete()
            print(f"✅ Deleted switch_users/{user_id}")
            deleted_count += 1
        else:
            print(f"ℹ️  No switch_users document found")
    except Exception as e:
        print(f"❌ Error deleting switch_users/{user_id}: {e}")
    
    # 2. Delete from users collection (if exists)
    try:
        user_ref = fs.collection("users").document(user_id)
        if user_ref.get().exists:
            user_ref.delete()
            print(f"✅ Deleted users/{user_id}")
            deleted_count += 1
        else:
            print(f"ℹ️  No users document found")
    except Exception as e:
        print(f"❌ Error deleting users/{user_id}: {e}")
    
    # 3. Delete from user_profiles collection
    try:
        profile_ref = fs.collection("user_profiles").document(user_id)
        if profile_ref.get().exists:
            profile_ref.delete()
            print(f"✅ Deleted user_profiles/{user_id}")
            deleted_count += 1
        else:
            print(f"ℹ️  No user_profiles document found")
    except Exception as e:
        print(f"❌ Error deleting user_profiles/{user_id}: {e}")
    
    # 4. Delete from candidates collection
    try:
        candidate_ref = fs.collection("candidates").document(user_id)
        if candidate_ref.get().exists:
            candidate_ref.delete()
            print(f"✅ Deleted candidates/{user_id}")
            deleted_count += 1
        else:
            print(f"ℹ️  No candidates document found")
    except Exception as e:
        print(f"❌ Error deleting candidates/{user_id}: {e}")
    
    # 5. Delete job applications where user is candidate
    try:
        applications = fs.collection("job_applications").where("candidate_id", "==", user_id).stream()
        app_count = 0
        for app_doc in applications:
            fs.collection("job_applications").document(app_doc.id).delete()
            app_count += 1
        if app_count > 0:
            print(f"✅ Deleted {app_count} job applications")
            deleted_count += app_count
        else:
            print(f"ℹ️  No job applications found")
    except Exception as e:
        print(f"❌ Error deleting job applications: {e}")
    
    # 6. Delete calls where user is candidate or business
    try:
        calls_as_candidate = fs.collection("calls").where("candidate_id", "==", user_id).stream()
        calls_as_business = fs.collection("calls").where("business_id", "==", user_id).stream()
        
        call_count = 0
        for call_doc in calls_as_candidate:
            fs.collection("calls").document(call_doc.id).delete()
            call_count += 1
        for call_doc in calls_as_business:
            fs.collection("calls").document(call_doc.id).delete()
            call_count += 1
        
        if call_count > 0:
            print(f"✅ Deleted {call_count} call records")
            deleted_count += call_count
        else:
            print(f"ℹ️  No call records found")
    except Exception as e:
        print(f"❌ Error deleting call records: {e}")
    
    # 7. Delete from businesses (if user is a business)
    try:
        businesses = fs.collection("businesses").where("phone", "==", user_id).stream()
        business_count = 0
        for business_doc in businesses:
            business_id = business_doc.id
            # Delete jobs for this business
            jobs = fs.collection("jobs").where("business_id", "==", business_id).stream()
            job_count = 0
            for job_doc in jobs:
                fs.collection("jobs").document(job_doc.id).delete()
                job_count += 1
            if job_count > 0:
                print(f"✅ Deleted {job_count} jobs for business")
                deleted_count += job_count
            
            # Delete business record
            fs.collection("businesses").document(business_id).delete()
            business_count += 1
        
        if business_count > 0:
            print(f"✅ Deleted {business_count} business records")
            deleted_count += business_count
        else:
            print(f"ℹ️  No business records found")
    except Exception as e:
        print(f"❌ Error deleting business records: {e}")
    
    # 8. Delete from extractions
    try:
        extraction_ref = fs.collection("extractions").document(user_id)
        if extraction_ref.get().exists:
            extraction_ref.delete()
            print(f"✅ Deleted extractions/{user_id}")
            deleted_count += 1
        else:
            print(f"ℹ️  No extractions document found")
    except Exception as e:
        print(f"❌ Error deleting extractions/{user_id}: {e}")
    
    # 9. Delete from otp_verifications
    try:
        otp_ref = fs.collection("otp_verifications").document(user_id)
        if otp_ref.get().exists:
            otp_ref.delete()
            print(f"✅ Deleted otp_verifications/{user_id}")
            deleted_count += 1
        else:
            print(f"ℹ️  No otp_verifications document found")
    except Exception as e:
        print(f"❌ Error deleting otp_verifications/{user_id}: {e}")
    
    # 10. Delete sessions
    try:
        sessions = fs.collection("sessions").where("user_id", "==", user_id).stream()
        session_count = 0
        for session_doc in sessions:
            fs.collection("sessions").document(session_doc.id).delete()
            session_count += 1
        if session_count > 0:
            print(f"✅ Deleted {session_count} sessions")
            deleted_count += session_count
        else:
            print(f"ℹ️  No sessions found")
    except Exception as e:
        print(f"❌ Error deleting sessions: {e}")
    
    print("=" * 70)
    print(f"✅ Deleted {deleted_count} document(s)")
    print(f"🎉 User {phone} is now a fresh user!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/delete_switch_user.py <phone_number>")
        print("Example: python3 scripts/delete_switch_user.py 918368828660")
        sys.exit(1)
    
    phone = sys.argv[1]
    delete_switch_user(phone)
