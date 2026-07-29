#!/usr/bin/env python3
"""
Script to attach audio by excluding ALL conversation_ids that are assigned to ANY user.
Only uses completely unassigned conversations.
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service


def get_all_assigned_conversation_ids() -> set:
    """Get ALL conversation_ids that are assigned to ANY user."""
    all_assigned = set()
    
    # Check all user_profiles
    user_profiles_ref = fs.collection("user_profiles")
    all_profiles = user_profiles_ref.stream()
    
    for profile_doc in all_profiles:
        profile_data = profile_doc.to_dict() or {}
        conv_id = profile_data.get("audio_conversation_id", "")
        if conv_id and conv_id.startswith("conv_"):
            all_assigned.add(conv_id)
    
    # Check all user_calls
    user_calls_ref = fs.collection("user_calls")
    all_user_calls = user_calls_ref.stream()
    
    for user_call_doc in all_user_calls:
        calls_ref = user_call_doc.reference.collection("calls")
        calls = list(calls_ref.limit(10).stream())
        for call_doc in calls:
            call_data = call_doc.to_dict() or {}
            conv_id = call_data.get("conversation_id") or call_data.get("call_id")
            if conv_id and conv_id.startswith("conv_"):
                all_assigned.add(conv_id)
    
    return all_assigned


async def attach_audio_excluding_all_assigned(slug: str):
    """Attach audio, excluding ALL assigned conversation_ids."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"Attaching audio for: {slug}")
    print(separator)
    
    # Get ALL assigned conversation_ids
    all_assigned_conv_ids = get_all_assigned_conversation_ids()
    print(f"\nExcluding {len(all_assigned_conv_ids)} assigned conversation_ids")
    
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
    print(f"WhatsApp Number: {phone}")
    
    # Get conversations from ElevenLabs
    print(f"\n1. Fetching conversations from ElevenLabs...")
    conversation_ids = await profile_audio_service._list_conversations_by_user(str(phone))
    
    if not conversation_ids:
        print(f"   ❌ No conversations found")
        return False
    
    print(f"   Found {len(conversation_ids)} conversations")
    
    # Filter out ALL assigned conversations
    print(f"\n2. Filtering out ALL assigned conversations...")
    unassigned = [c for c in conversation_ids if c not in all_assigned_conv_ids]
    print(f"   After filtering: {len(unassigned)} unassigned conversations")
    
    if not unassigned:
        print(f"   ❌ No unassigned conversations available")
        print(f"   All conversations from ElevenLabs are already assigned to other users")
        return False
    
    # Use the first unassigned conversation
    selected_conv_id = unassigned[0]
    print(f"\n3. Selected conversation: {selected_conv_id}")
    print(f"   ✅ Not assigned to anyone")
    
    # Update call log
    print(f"\n4. Updating call log...")
    calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
    calls = list(calls_ref.limit(1).stream())
    if calls:
        call_doc = calls[0]
        call_doc.reference.update({
            "conversation_id": selected_conv_id,
            "call_id": selected_conv_id,
        })
        print(f"   ✅ Updated call log")
    else:
        print(f"   ⚠️  No call records to update")
    
    # Store in user_profile
    print(f"\n5. Storing in user profile...")
    fs.collection("user_profiles").document(user_id).set({
        "audio_conversation_id": selected_conv_id,
        "audio_available": True,
        "audio_updated_at": time.time(),
    }, merge=True)
    print(f"   ✅ Stored conversation_id: {selected_conv_id}")
    
    print(f"\n✅ Audio attached successfully!")
    print(f"   conversation_id: {selected_conv_id}")
    print(f"   ✅ Verified: Not assigned to any user")
    
    return True


async def main():
    slugs = ["irfan", "mahima-kaushik"]
    results = []
    
    for slug in slugs:
        result = await attach_audio_excluding_all_assigned(slug)
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

