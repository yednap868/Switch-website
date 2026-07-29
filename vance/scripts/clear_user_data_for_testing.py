#!/usr/bin/env python3
"""
Clear all user data for a specific user ID to test onboarding as a fresh user.
This deletes data from all relevant Firestore collections.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def clear_user_data(uid: str):
    """
    Clear all user data for testing onboarding broadcast feature.
    """
    print(f"🧹 Clearing all data for user {uid}...")
    print("=" * 70)
    
    deleted_count = 0
    
    # 1. Main user document
    try:
        user_ref = fs.collection("users").document(uid)
        if user_ref.get().exists:
            user_ref.delete()
            print(f"✅ Deleted users/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No user document found")
    except Exception as e:
        print(f"❌ Error deleting users/{uid}: {e}")
    
    # 2. Extraction data
    try:
        extraction_ref = fs.collection("extractions").document(uid)
        if extraction_ref.get().exists:
            extraction_ref.delete()
            print(f"✅ Deleted extractions/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No extraction data found")
    except Exception as e:
        print(f"❌ Error deleting extractions/{uid}: {e}")
    
    # 3. Onboarding broadcast record (idempotency)
    try:
        broadcast_ref = fs.collection("onboarding_broadcasts").document(uid)
        if broadcast_ref.get().exists:
            broadcast_ref.delete()
            print(f"✅ Deleted onboarding_broadcasts/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No broadcast record found")
    except Exception as e:
        print(f"❌ Error deleting onboarding_broadcasts/{uid}: {e}")
    
    # 4. Conversation history (main doc + messages subcollection)
    try:
        conv_ref = fs.collection("conversations").document(uid)
        
        # Delete all messages in subcollection
        messages_ref = conv_ref.collection("messages")
        message_count = 0
        for msg_doc in messages_ref.stream():
            msg_doc.reference.delete()
            message_count += 1
        
        if message_count > 0:
            print(f"✅ Deleted {message_count} messages from conversations/{uid}/messages")
            deleted_count += 1
        
        # Delete main conversation document
        if conv_ref.get().exists:
            conv_ref.delete()
            print(f"✅ Deleted conversations/{uid}")
            deleted_count += 1
        else:
            if message_count == 0:
                print(f"ℹ️  No conversation history found")
    except Exception as e:
        print(f"❌ Error deleting conversations/{uid}: {e}")
    
    # 5. User profiles
    try:
        profile_ref = fs.collection("user_profiles").document(uid)
        if profile_ref.get().exists:
            profile_ref.delete()
            print(f"✅ Deleted user_profiles/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No user profile found")
    except Exception as e:
        print(f"❌ Error deleting user_profiles/{uid}: {e}")
    
    # 6. User call summaries
    try:
        summary_ref = fs.collection("user_call_summaries").document(uid)
        if summary_ref.get().exists:
            summary_ref.delete()
            print(f"✅ Deleted user_call_summaries/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No call summary found")
    except Exception as e:
        print(f"❌ Error deleting user_call_summaries/{uid}: {e}")
    
    # 7. Post-call profile links
    try:
        link_ref = fs.collection("post_call_profile_links").document(uid)
        if link_ref.get().exists:
            link_ref.delete()
            print(f"✅ Deleted post_call_profile_links/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No profile link record found")
    except Exception as e:
        print(f"❌ Error deleting post_call_profile_links/{uid}: {e}")
    
    # 8. User calls (main doc + calls subcollection)
    try:
        calls_ref = fs.collection("user_calls").document(uid)
        
        # Delete all calls in subcollection
        calls_subcollection = calls_ref.collection("calls")
        call_count = 0
        for call_doc in calls_subcollection.stream():
            call_doc.reference.delete()
            call_count += 1
        
        if call_count > 0:
            print(f"✅ Deleted {call_count} call records from user_calls/{uid}/calls")
            deleted_count += 1
        
        # Delete main user_calls document
        if calls_ref.get().exists:
            calls_ref.delete()
            print(f"✅ Deleted user_calls/{uid}")
            deleted_count += 1
        else:
            if call_count == 0:
                print(f"ℹ️  No call history found")
    except Exception as e:
        print(f"❌ Error deleting user_calls/{uid}: {e}")
    
    # 9. Agent memory
    try:
        agent_memory_ref = fs.collection("agent_memory").document(uid)
        if agent_memory_ref.get().exists:
            agent_memory_ref.delete()
            print(f"✅ Deleted agent_memory/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No agent memory found")
    except Exception as e:
        print(f"❌ Error deleting agent_memory/{uid}: {e}")
    
    # 10. User memory
    try:
        user_memory_ref = fs.collection("user_memory").document(uid)
        if user_memory_ref.get().exists:
            user_memory_ref.delete()
            print(f"✅ Deleted user_memory/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No user memory found")
    except Exception as e:
        print(f"❌ Error deleting user_memory/{uid}: {e}")
    
    # 11. Post-call referrals
    try:
        referral_ref = fs.collection("post_call_referrals").document(uid)
        if referral_ref.get().exists:
            referral_ref.delete()
            print(f"✅ Deleted post_call_referrals/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No referral record found")
    except Exception as e:
        print(f"❌ Error deleting post_call_referrals/{uid}: {e}")
    
    # 12. Referral messages
    try:
        referral_msg_ref = fs.collection("referral_messages").document(uid)
        if referral_msg_ref.get().exists:
            referral_msg_ref.delete()
            print(f"✅ Deleted referral_messages/{uid}")
            deleted_count += 1
        else:
            print(f"ℹ️  No referral message record found")
    except Exception as e:
        print(f"❌ Error deleting referral_messages/{uid}: {e}")
    
    print("=" * 70)
    print(f"✅ User data cleared! Deleted {deleted_count} document(s)")
    print(f"\n📝 User {uid} is now ready for fresh onboarding testing")
    print(f"   The next onboarding will trigger the broadcast feature")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/clear_user_data_for_testing.py <uid>")
        print("Example: python3 scripts/clear_user_data_for_testing.py 918368828660")
        sys.exit(1)
    
    uid = sys.argv[1]
    clear_user_data(uid)

