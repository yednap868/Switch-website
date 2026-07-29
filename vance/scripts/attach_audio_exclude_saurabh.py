#!/usr/bin/env python3
"""
Script to attach audio by WhatsApp number, but EXCLUDE any conversations
that belong to Saurabh (uid: 918368828660).
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service

SAURABH_UID = "918368828660"


def get_saurabh_conversation_ids() -> set:
    """Get all conversation_ids that belong to Saurabh."""
    saurabh_conv_ids = set()
    
    # Check user_profile
    saurabh_profile = get_user_profile(SAURABH_UID) or {}
    conv_id = saurabh_profile.get("audio_conversation_id", "")
    if conv_id:
        saurabh_conv_ids.add(conv_id)
    
    # Check user_calls
    calls_ref = fs.collection("user_calls").document(SAURABH_UID).collection("calls")
    calls = list(calls_ref.stream())
    for call_doc in calls:
        call_data = call_doc.to_dict() or {}
        conv_id = call_data.get("conversation_id") or call_data.get("call_id")
        if conv_id:
            saurabh_conv_ids.add(conv_id)
    
    return saurabh_conv_ids


async def attach_audio_excluding_saurabh(slug: str):
    """Attach audio, but exclude Saurabh's conversations."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"Attaching audio for: {slug}")
    print(separator)
    
    # Get Saurabh's conversation_ids to exclude
    saurabh_conv_ids = get_saurabh_conversation_ids()
    print(f"\nExcluding Saurabh's conversation_ids: {list(saurabh_conv_ids)}")
    
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
    
    # Filter out Saurabh's conversations
    print(f"\n2. Filtering out Saurabh's conversations...")
    filtered_conversations = [c for c in conversation_ids if c not in saurabh_conv_ids]
    print(f"   After filtering: {len(filtered_conversations)} conversations")
    
    if not filtered_conversations:
        print(f"   ❌ No conversations available after excluding Saurabh's")
        return False
    
    # Check which ones are already assigned to other users
    print(f"\n3. Checking which conversations are already assigned...")
    available = []
    for conv_id in filtered_conversations:
        profiles_with_conv = fs.collection("user_profiles").where("audio_conversation_id", "==", conv_id).limit(1).stream()
        assigned = list(profiles_with_conv)
        
        if not assigned:
            available.append(conv_id)
            print(f"   ✅ {conv_id} - AVAILABLE")
        else:
            assigned_user = assigned[0].id
            assigned_name = get_user_profile(assigned_user).get("name", assigned_user)
            print(f"   ❌ {conv_id} - Already assigned to {assigned_name}")
    
    if not available:
        print(f"\n   ❌ No available conversations")
        return False
    
    # Use the first available conversation
    selected_conv_id = available[0]
    print(f"\n4. Selected conversation: {selected_conv_id}")
    print(f"   ✅ Not Saurabh's")
    print(f"   ✅ Not assigned to anyone else")
    
    # Update call log
    print(f"\n5. Updating call log...")
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
    print(f"\n6. Storing in user profile...")
    fs.collection("user_profiles").document(user_id).set({
        "audio_conversation_id": selected_conv_id,
        "audio_available": True,
        "audio_updated_at": time.time(),
    }, merge=True)
    print(f"   ✅ Stored conversation_id: {selected_conv_id}")
    
    print(f"\n✅ Audio attached successfully!")
    print(f"   conversation_id: {selected_conv_id}")
    print(f"   ✅ Verified: Not Saurabh's audio")
    
    return True


async def main():
    slugs = ["irfan", "mahima-kaushik"]
    results = []
    
    for slug in slugs:
        result = await attach_audio_excluding_saurabh(slug)
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

