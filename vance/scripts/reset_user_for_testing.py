#!/usr/bin/env python3
"""
Reset specific user data to test profile link sending as a "first call".
This deletes:
- user_call_summaries (resets call count)
- post_call_profile_links (resets idempotency)
- user_calls subcollection (call history)

Keeps:
- user_profiles (profile data)
- users (user document)
- extractions (extraction data)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def reset_user_for_testing(uid: str):
    """
    Reset user data to simulate first call scenario.
    """
    print(f"🔄 Resetting user {uid} for first-call testing...")
    
    try:
        # 1. Delete call summary (resets call count)
        summary_ref = fs.collection("user_call_summaries").document(uid)
        if summary_ref.get().exists:
            summary_ref.delete()
            print(f"✅ Deleted user_call_summaries/{uid}")
        else:
            print(f"ℹ️  No call summary found")
        
        # 2. Delete profile link idempotency record
        link_ref = fs.collection("post_call_profile_links").document(uid)
        if link_ref.get().exists:
            link_ref.delete()
            print(f"✅ Deleted post_call_profile_links/{uid}")
        else:
            print(f"ℹ️  No profile link record found")
        
        # 3. Delete call history (user_calls/{uid}/calls)
        calls_ref = fs.collection("user_calls").document(uid).collection("calls")
        call_count = 0
        for call_doc in calls_ref.stream():
            call_doc.reference.delete()
            call_count += 1
        if call_count > 0:
            print(f"✅ Deleted {call_count} call records from user_calls/{uid}/calls")
        else:
            print(f"ℹ️  No call history found")
        
        # 4. Delete user_calls document itself
        user_calls_ref = fs.collection("user_calls").document(uid)
        if user_calls_ref.get().exists:
            user_calls_ref.delete()
            print(f"✅ Deleted user_calls/{uid}")
        
        print(f"\n✅ User {uid} reset complete!")
        print(f"   Next call will be treated as first call")
        print(f"   Profile link will be sent automatically")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting user: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/reset_user_for_testing.py <uid>")
        print("Example: python3 scripts/reset_user_for_testing.py 918368828660")
        sys.exit(1)
    
    uid = sys.argv[1]
    reset_user_for_testing(uid)
