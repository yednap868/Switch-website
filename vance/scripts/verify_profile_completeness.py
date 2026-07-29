"""
Script to verify profile completeness and check for missing fields.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db import fs, get_user_profile, get_extraction_data


def check_profile_completeness(uid: str):
    """Check if a profile is complete with all required fields."""
    print(f"\n{'='*60}")
    print(f"Checking Profile Completeness for UID: {uid}")
    print(f"{'='*60}\n")
    
    # 1. Check user profile
    user_profile = get_user_profile(uid) or {}
    print("1. User Profile (users/{uid}):")
    print(f"   - Name: {user_profile.get('name', 'MISSING')}")
    print(f"   - Email: {user_profile.get('email', 'MISSING')}")
    print(f"   - LinkedIn: {user_profile.get('linkedin_url', 'MISSING')}")
    print(f"   - User Type: {user_profile.get('profile', {}).get('user_type', 'MISSING')}")
    
    # 2. Check extraction data
    extraction = get_extraction_data(uid) or {}
    print(f"\n2. Extraction Data (extractions/{uid}):")
    print(f"   - Has extraction: {bool(extraction)}")
    if extraction:
        print(f"   - Fields: {len(extraction)} fields")
        key_fields = ['target_role', 'core_skills', 'work_experience', 'current_location']
        for field in key_fields:
            value = extraction.get(field, '')
            print(f"   - {field}: {'✅' if value else '❌ MISSING'}")
    
    # 3. Check user_profiles document
    profile_doc = fs.collection("user_profiles").document(uid).get()
    print(f"\n3. Public Profile (user_profiles/{uid}):")
    if profile_doc.exists:
        profile_data = profile_doc.to_dict() or {}
        print(f"   - Exists: ✅")
        print(f"   - Slug: {profile_data.get('slug', '❌ MISSING')}")
        print(f"   - Name: {profile_data.get('name', '❌ MISSING')}")
        print(f"   - Email: {profile_data.get('email', '❌ MISSING')}")
        print(f"   - LinkedIn: {profile_data.get('linkedin_url', '❌ MISSING')}")
        print(f"   - Avatar: {profile_data.get('avatar_url', '❌ MISSING')}")
        print(f"   - Intro Audio: {'✅' if profile_data.get('intro_audio_url') else '❌ MISSING'}")
        print(f"   - Thinking Audio: {'✅' if profile_data.get('thinking_audio_url') else '❌ MISSING'}")
        print(f"   - Story: {'✅' if profile_data.get('story') else '❌ MISSING'}")
        print(f"   - Strengths: {'✅' if profile_data.get('strengths') else '❌ MISSING'}")
        print(f"   - Proof of Work: {'✅' if profile_data.get('proofOfWork') or profile_data.get('proof_of_work') else '❌ MISSING'}")
        print(f"   - Thoughts: {'✅' if profile_data.get('thoughts') else '❌ MISSING'}")
    else:
        print(f"   - Exists: ❌ MISSING")
    
    # 4. Check call summary
    call_summary = fs.collection("user_call_summaries").document(uid).get()
    print(f"\n4. Call Summary (user_call_summaries/{uid}):")
    if call_summary.exists:
        summary_data = call_summary.to_dict() or {}
        print(f"   - Total Calls: {summary_data.get('total_calls', 0)}")
        print(f"   - First Call: {summary_data.get('first_call_timestamp', 'N/A')}")
    else:
        print(f"   - Exists: ❌ MISSING")
    
    # 5. Check profile link status
    link_doc = fs.collection("post_call_profile_links").document(uid).get()
    print(f"\n5. Profile Link Status (post_call_profile_links/{uid}):")
    if link_doc.exists:
        link_data = link_doc.to_dict() or {}
        print(f"   - Sent: ✅")
        print(f"   - Sent At: {link_data.get('sent_at', 'N/A')}")
        print(f"   - Delivery Status: {link_data.get('delivery_status', 'unknown')}")
    else:
        print(f"   - Sent: ❌ NOT SENT")
    
    # 6. Check latest call for conversation_id
    from firebase_admin import firestore
    calls_ref = fs.collection("user_calls").document(uid).collection("calls")
    calls = list(calls_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream())
    print(f"\n6. Latest Call:")
    if calls:
        latest_call = calls[0].to_dict() or {}
        print(f"   - Conversation ID: {latest_call.get('conversation_id', '❌ MISSING')}")
        print(f"   - Call ID: {latest_call.get('call_id', 'N/A')}")
        print(f"   - Duration: {latest_call.get('duration', 0)}s")
    else:
        print(f"   - No calls found")
    
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_profile_completeness.py <uid>")
        sys.exit(1)
    
    uid = sys.argv[1]
    check_profile_completeness(uid)

