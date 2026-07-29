"""
Script to delete all data for a specific user ID.
Deletes from all collections where user data might exist.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def delete_user_data(user_id: str):
    """
    Delete all data for a user ID from all collections.
    
    Args:
        user_id: User ID (phone number) to delete
    """
    print(f"🗑️  Starting deletion for user: {user_id}")
    print("=" * 70)
    
    deleted_count = 0
    
    # 1. Delete from switch_users
    try:
        switch_user_doc = fs.collection("switch_users").document(user_id).get()
        if switch_user_doc.exists:
            fs.collection("switch_users").document(user_id).delete()
            print(f"✅ Deleted from switch_users")
            deleted_count += 1
        else:
            print(f"ℹ️  No data in switch_users")
    except Exception as e:
        print(f"❌ Error deleting from switch_users: {e}")
    
    # 2. Delete from candidates
    try:
        candidate_doc = fs.collection("candidates").document(user_id).get()
        if candidate_doc.exists:
            fs.collection("candidates").document(user_id).delete()
            print(f"✅ Deleted from candidates")
            deleted_count += 1
        else:
            print(f"ℹ️  No data in candidates")
    except Exception as e:
        print(f"❌ Error deleting from candidates: {e}")
    
    # 3. Delete from users
    try:
        user_doc = fs.collection("users").document(user_id).get()
        if user_doc.exists:
            fs.collection("users").document(user_id).delete()
            print(f"✅ Deleted from users")
            deleted_count += 1
        else:
            print(f"ℹ️  No data in users")
    except Exception as e:
        print(f"❌ Error deleting from users: {e}")
    
    # 4. Delete from user_profiles
    try:
        profile_doc = fs.collection("user_profiles").document(user_id).get()
        if profile_doc.exists:
            fs.collection("user_profiles").document(user_id).delete()
            print(f"✅ Deleted from user_profiles")
            deleted_count += 1
        else:
            print(f"ℹ️  No data in user_profiles")
    except Exception as e:
        print(f"❌ Error deleting from user_profiles: {e}")
    
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
    
    # 7. Delete sessions
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
    
    # 8. Delete extractions
    try:
        extraction_doc = fs.collection("extractions").document(user_id).get()
        if extraction_doc.exists:
            fs.collection("extractions").document(user_id).delete()
            print(f"✅ Deleted from extractions")
            deleted_count += 1
        else:
            print(f"ℹ️  No data in extractions")
    except Exception as e:
        print(f"❌ Error deleting from extractions: {e}")
    
    # 9. Delete OTP verifications
    try:
        otp_doc = fs.collection("otp_verifications").document(user_id).get()
        if otp_doc.exists:
            fs.collection("otp_verifications").document(user_id).delete()
            print(f"✅ Deleted from otp_verifications")
            deleted_count += 1
        else:
            print(f"ℹ️  No data in otp_verifications")
    except Exception as e:
        print(f"❌ Error deleting from otp_verifications: {e}")
    
    # 10. Delete from businesses (if user is a business)
    try:
        # Check if phone matches any business
        businesses = fs.collection("businesses").where("phone", "==", user_id).stream()
        business_count = 0
        for business_doc in businesses:
            fs.collection("businesses").document(business_doc.id).delete()
            business_count += 1
        if business_count > 0:
            print(f"✅ Deleted {business_count} business records")
            deleted_count += business_count
        else:
            print(f"ℹ️  No business records found")
    except Exception as e:
        print(f"❌ Error deleting business records: {e}")
    
    # 11. Delete jobs created by this business (if applicable)
    try:
        # First find business_id if exists
        businesses = fs.collection("businesses").where("phone", "==", user_id).stream()
        business_ids = [doc.id for doc in businesses]
        
        for business_id in business_ids:
            jobs = fs.collection("jobs").where("business_id", "==", business_id).stream()
            job_count = 0
            for job_doc in jobs:
                fs.collection("jobs").document(job_doc.id).delete()
                job_count += 1
            if job_count > 0:
                print(f"✅ Deleted {job_count} jobs for business {business_id}")
                deleted_count += job_count
    except Exception as e:
        print(f"❌ Error deleting jobs: {e}")
    
    print("=" * 70)
    print(f"✅ Deletion complete!")
    print(f"   Total records deleted: {deleted_count}")
    print(f"   User ID: {user_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_user_data.py <user_id>")
        print("Example: python scripts/delete_user_data.py 918368828660")
        sys.exit(1)
    
    user_id = sys.argv[1]
    
    # Confirm deletion
    print(f"⚠️  WARNING: This will delete ALL data for user: {user_id}")
    print("This includes:")
    print("  - User profiles")
    print("  - Switch candidate/business data")
    print("  - Job applications")
    print("  - Call records")
    print("  - Sessions")
    print("  - Extractions")
    print()
    
    confirm = input("Type 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("❌ Deletion cancelled")
        sys.exit(0)
    
    delete_user_data(user_id)
