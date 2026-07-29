#!/usr/bin/env python3
"""
Script to find and attach audio for profiles that are missing it.
Attempts to find conversation_id from ElevenLabs and attach it.
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service


async def try_to_find_and_attach_audio(slug: str):
    """Try to find conversation_id from ElevenLabs and attach audio."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"Attempting to find audio for: {slug}")
    print(separator)
    
    # Get user_id from public profile
    public_doc = fs.collection("public_profiles").document(slug).get()
    if not public_doc.exists:
        print(f"❌ Public profile not found")
        return False
    
    public_data = public_doc.to_dict() or {}
    user_id = public_data.get("user_id")
    if not user_id:
        print(f"❌ No user_id in public profile")
        return False
    
    user_profile = get_user_profile(user_id) or {}
    name = user_profile.get("name", slug)
    phone = user_profile.get("wa_id") or user_profile.get("phone") or user_id
    
    print(f"User: {name}")
    print(f"User ID: {user_id}")
    print(f"Phone: {phone}")
    
    # Get conversations from ElevenLabs
    print(f"\n1. Fetching conversations from ElevenLabs...")
    conversation_ids = await profile_audio_service._list_conversations_by_user(str(phone))
    
    if not conversation_ids:
        print(f"   ❌ No conversations found in ElevenLabs for {phone}")
        return False
    
    print(f"   Found {len(conversation_ids)} conversations")
    
    # Check call timestamps
    print(f"\n2. Checking call timestamps...")
    calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
    try:
        calls = calls_ref.order_by("timestamp", direction="DESCENDING").limit(5).stream()
    except:
        calls = calls_ref.limit(5).stream()
    
    call_timestamps = []
    for call_doc in calls:
        call_data = call_doc.to_dict() or {}
        timestamp = call_data.get("timestamp", 0)
        if timestamp:
            call_timestamps.append(timestamp)
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)) if timestamp else "N/A"
            print(f"   Call timestamp: {timestamp} ({time_str})")
    
    if not call_timestamps:
        print(f"   ⚠️  No call timestamps found")
    
    print(f"\n3. Attempting to use most recent conversation...")
    # Use the most recent conversation as a best guess
    most_recent_conv_id = conversation_ids[0]
    print(f"   Selected: {most_recent_conv_id}")
    
    # Check if this conversation_id is already assigned to another user
    print(f"\n4. Checking if conversation_id is already assigned...")
    profiles_with_conv = fs.collection("user_profiles").where("audio_conversation_id", "==", most_recent_conv_id).limit(1).stream()
    already_assigned = list(profiles_with_conv)
    
    if already_assigned:
        assigned_user = already_assigned[0].id
        print(f"   ⚠️  conversation_id {most_recent_conv_id} is already assigned to user {assigned_user}")
        if assigned_user != user_id:
            print(f"   ❌ Cannot use this conversation_id - it belongs to another user")
            # Try the next conversation
            if len(conversation_ids) > 1:
                print(f"\n   Trying next conversation...")
                most_recent_conv_id = conversation_ids[1]
                print(f"   Selected: {most_recent_conv_id}")
                # Check again
                profiles_with_conv = fs.collection("user_profiles").where("audio_conversation_id", "==", most_recent_conv_id).limit(1).stream()
                already_assigned = list(profiles_with_conv)
                if already_assigned:
                    assigned_user = already_assigned[0].id
                    if assigned_user != user_id:
                        print(f"   ❌ This one is also assigned to another user")
                        return False
            else:
                return False
    
    print(f"   ✅ conversation_id appears to be available")
    
    # Update call log
    print(f"\n5. Updating call log...")
    calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
    calls = list(calls_ref.limit(1).stream())
    if calls:
        call_doc = calls[0]
        call_doc.reference.update({
            "conversation_id": most_recent_conv_id,
            "call_id": most_recent_conv_id,
        })
        print(f"   ✅ Updated call log")
    else:
        print(f"   ⚠️  No call records to update")
    
    # Store conversation_id in user_profile for on-demand fetching
    print(f"\n6. Storing conversation_id in user profile...")
    fs.collection("user_profiles").document(user_id).set({
        "audio_conversation_id": most_recent_conv_id,
        "audio_available": True,
        "audio_updated_at": time.time(),
    }, merge=True)
    print(f"   ✅ Stored conversation_id")
    
    print(f"\n✅ Audio setup complete!")
    print(f"   conversation_id: {most_recent_conv_id}")
    print(f"   Audio will be fetched on-demand from ElevenLabs")
    return True


async def main():
    slugs = ["irfan", "mahima-kaushik"]
    results = []
    
    for slug in slugs:
        result = await try_to_find_and_attach_audio(slug)
        results.append((slug, result))
    
    separator = "=" * 70
    print(f"\n{separator}")
    print("SUMMARY")
    print(separator)
    for slug, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {slug}: {'Audio attached' if result else 'Could not attach audio'}")
    print(separator)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

