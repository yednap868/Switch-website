#!/usr/bin/env python3
"""
Script to attach audio to profiles by fetching from ElevenLabs using WhatsApp number
and verifying ownership more carefully.
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service


async def find_and_attach_audio_with_verification(slug: str):
    """Find and attach audio with better verification."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"Finding audio for: {slug}")
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
    
    # Check which ones are already assigned
    print(f"\n2. Checking which conversations are already assigned...")
    unassigned = []
    for i, conv_id in enumerate(conversation_ids[:20], 1):  # Check first 20
        profiles_with_conv = fs.collection("user_profiles").where("audio_conversation_id", "==", conv_id).limit(1).stream()
        assigned = list(profiles_with_conv)
        
        if not assigned:
            unassigned.append(conv_id)
            print(f"   ✅ [{i}] {conv_id} - UNASSIGNED")
        else:
            assigned_user = assigned[0].id
            assigned_name = get_user_profile(assigned_user).get("name", assigned_user)
            print(f"   ❌ [{i}] {conv_id} - Assigned to {assigned_name} ({assigned_user})")
    
    if not unassigned:
        print(f"\n   ❌ No unassigned conversations found")
        return False
    
    print(f"\n   Found {len(unassigned)} unassigned conversations")
    
    # Try to verify ownership by checking if conversation_id appears in user's data
    print(f"\n3. Attempting to verify ownership...")
    verified_conv_id = None
    
    for conv_id in unassigned:
        # Method 1: Check if it's in user_calls (even if empty, we can check the structure)
        # This won't work for these users since they don't have conversation_id in calls
        
        # Method 2: Check if conversation_id appears in any extraction data
        # (sometimes extraction data might have conversation_id)
        extraction_doc = fs.collection("extractions").document(user_id).get()
        if extraction_doc.exists:
            extraction_data = extraction_doc.to_dict() or {}
            # Check if conversation_id is mentioned anywhere in extraction
            extraction_str = str(extraction_data).lower()
            if conv_id.lower() in extraction_str:
                print(f"   ✅ Found {conv_id} in extraction data - VERIFIED")
                verified_conv_id = conv_id
                break
        
        # Method 3: Check if this conversation_id is in any call logs for this user
        # (even if conversation_id field is empty, check other fields)
        calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
        calls = list(calls_ref.limit(10).stream())
        for call_doc in calls:
            call_data = call_doc.to_dict() or {}
            # Check all fields in call_data for the conversation_id
            call_str = str(call_data).lower()
            if conv_id.lower() in call_str:
                print(f"   ✅ Found {conv_id} in call data - VERIFIED")
                verified_conv_id = conv_id
                break
        
        if verified_conv_id:
            break
    
    # If we couldn't verify, use the most recent unassigned one
    # (this is a best guess - the user can verify manually)
    if not verified_conv_id:
        print(f"\n   ⚠️  Could not verify ownership automatically")
        print(f"   Using most recent unassigned conversation as best guess")
        verified_conv_id = unassigned[0]
        print(f"   Selected: {verified_conv_id}")
        print(f"   ⚠️  WARNING: This is not verified - please check manually!")
    
    # Update call log
    print(f"\n4. Updating call log...")
    calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
    calls = list(calls_ref.limit(1).stream())
    if calls:
        call_doc = calls[0]
        call_doc.reference.update({
            "conversation_id": verified_conv_id,
            "call_id": verified_conv_id,
        })
        print(f"   ✅ Updated call log with conversation_id: {verified_conv_id}")
    else:
        print(f"   ⚠️  No call records to update")
    
    # Store conversation_id in user_profile
    print(f"\n5. Storing conversation_id in user profile...")
    fs.collection("user_profiles").document(user_id).set({
        "audio_conversation_id": verified_conv_id,
        "audio_available": True,
        "audio_updated_at": time.time(),
    }, merge=True)
    print(f"   ✅ Stored conversation_id: {verified_conv_id}")
    
    print(f"\n✅ Audio setup complete!")
    print(f"   conversation_id: {verified_conv_id}")
    print(f"   Audio will be fetched on-demand from ElevenLabs")
    
    if not verified_conv_id in [c for c in unassigned if c == verified_conv_id]:
        print(f"\n   ⚠️  REMINDER: Please verify this is the correct audio!")
    
    return True


async def main():
    slugs = ["irfan", "mahima-kaushik"]
    results = []
    
    for slug in slugs:
        result = await find_and_attach_audio_with_verification(slug)
        results.append((slug, result))
    
    separator = "=" * 70
    print(f"\n{separator}")
    print("SUMMARY")
    print(separator)
    for slug, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {slug}: {'Audio attached' if result else 'Could not attach audio'}")
    print(separator)
    print("\n⚠️  IMPORTANT: Please verify the audio is correct by checking the profiles!")
    print("   If the audio is wrong, we can clear it and try again.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

