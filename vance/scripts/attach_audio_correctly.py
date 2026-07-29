#!/usr/bin/env python3
"""
Script to attach audio by fetching conversation details and matching user_id (phone number).
Excludes Saurabh's conversation_ids.
"""
import sys
import os
import asyncio
import time
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile


def get_saurabh_conversation_ids() -> set:
    """Get all conversation_ids that belong to Saurabh."""
    saurabh_uid = "918368828660"
    saurabh_conv_ids = set()
    
    # From user_profile
    saurabh_profile = get_user_profile(saurabh_uid) or {}
    conv_id = saurabh_profile.get("audio_conversation_id", "")
    if conv_id:
        saurabh_conv_ids.add(conv_id)
    
    # From user_calls
    calls_ref = fs.collection("user_calls").document(saurabh_uid).collection("calls")
    calls = list(calls_ref.stream())
    for call_doc in calls:
        call_data = call_doc.to_dict() or {}
        conv_id = call_data.get("conversation_id") or call_data.get("call_id")
        if conv_id:
            saurabh_conv_ids.add(conv_id)
    
    return saurabh_conv_ids


async def get_conversations_by_user_id(phone: str, exclude_conv_ids: set) -> list[dict]:
    """Get conversations from ElevenLabs by fetching details to match user_id."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not set")
        return []
    
    url = "https://api.elevenlabs.io/v1/convai/conversations"
    headers = {"xi-api-key": api_key}
    
    # Normalize phone number for matching
    phone_normalized = str(phone).replace("+", "").replace("-", "").replace(" ", "")
    
    matching_conversations = []
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Get all conversations
            print(f"   Fetching conversation list...")
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            conversations = response.json()
            
            # Handle both list and dict responses
            if isinstance(conversations, dict):
                conversations = conversations.get("conversations", []) or conversations.get("data", []) or []
            
            print(f"   Found {len(conversations)} total conversations")
            print(f"   Checking each conversation's user_id...")
            
            # Fetch details for each conversation to get user_id
            for i, conv in enumerate(conversations, 1):
                if isinstance(conv, dict):
                    conv_id = conv.get("conversation_id") or conv.get("id") or conv.get("_id")
                    if not conv_id:
                        continue
                    
                    # Skip if it's Saurabh's conversation
                    if conv_id in exclude_conv_ids:
                        if i <= 5 or i % 10 == 0:
                            print(f"   [{i}/{len(conversations)}] Skipping Saurabh's conversation: {conv_id}")
                        continue
                    
                    # Fetch conversation details to get user_id
                    try:
                        detail_url = f"https://api.elevenlabs.io/v1/convai/conversations/{conv_id}"
                        detail_response = await client.get(detail_url, headers=headers, timeout=30.0)
                        detail_response.raise_for_status()
                        detail_data = detail_response.json()
                        
                        # Get user_id from details
                        user_id = str(detail_data.get("user_id", "")).replace("+", "").replace("-", "").replace(" ", "")
                        
                        if user_id == phone_normalized:
                            matching_conversations.append({
                                "conversation_id": str(conv_id),
                                "user_id": user_id,
                                "metadata": detail_data
                            })
                            print(f"   ✅ [{i}/{len(conversations)}] Matched: {conv_id} (User ID: {user_id})")
                        elif i <= 5 or i % 10 == 0:
                            print(f"   [{i}/{len(conversations)}] Checking {conv_id}... (user_id: {user_id})")
                    except Exception as e:
                        if i <= 5:
                            print(f"   ⚠️  Error fetching details for {conv_id}: {e}")
                        continue
            
            return matching_conversations
            
    except Exception as e:
        print(f"⚠️ Error fetching conversations: {e}")
        return []


async def attach_audio_correctly(slug: str):
    """Attach audio by matching ElevenLabs User ID to WhatsApp number."""
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
    
    # Get conversations from ElevenLabs where User ID matches phone
    print(f"\n1. Fetching conversations from ElevenLabs where User ID = {phone}...")
    matching_conversations = await get_conversations_by_user_id(phone, saurabh_conv_ids)
    
    if not matching_conversations:
        print(f"   ❌ No conversations found with User ID = {phone}")
        return False
    
    print(f"   Found {len(matching_conversations)} matching conversations")
    
    # Check which ones are already assigned
    print(f"\n2. Checking which conversations are already assigned...")
    available = []
    for conv in matching_conversations:
        conv_id = conv["conversation_id"]
        profiles_with_conv = fs.collection("user_profiles").where("audio_conversation_id", "==", conv_id).limit(1).stream()
        assigned = list(profiles_with_conv)
        
        if not assigned:
            available.append(conv)
            print(f"   ✅ {conv_id} - AVAILABLE")
        else:
            assigned_user = assigned[0].id
            assigned_name = get_user_profile(assigned_user).get("name", assigned_user)
            print(f"   ❌ {conv_id} - Already assigned to {assigned_name}")
    
    if not available:
        print(f"\n   ❌ No available conversations")
        return False
    
    # Use the first available conversation (most recent)
    selected_conv = available[0]
    conv_id = selected_conv["conversation_id"]
    
    print(f"\n3. Selected conversation: {conv_id}")
    print(f"   ✅ User ID matches: {selected_conv['user_id']} == {phone}")
    print(f"   ✅ Not Saurabh's conversation")
    
    # Update call log
    print(f"\n4. Updating call log...")
    calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
    calls = list(calls_ref.limit(1).stream())
    if calls:
        call_doc = calls[0]
        call_doc.reference.update({
            "conversation_id": conv_id,
            "call_id": conv_id,
        })
        print(f"   ✅ Updated call log")
    else:
        print(f"   ⚠️  No call records to update")
    
    # Store in user_profile
    print(f"\n5. Storing in user profile...")
    fs.collection("user_profiles").document(user_id).set({
        "audio_conversation_id": conv_id,
        "audio_available": True,
        "audio_updated_at": time.time(),
    }, merge=True)
    print(f"   ✅ Stored conversation_id: {conv_id}")
    
    print(f"\n✅ Audio attached successfully!")
    print(f"   conversation_id: {conv_id}")
    print(f"   ✅ Verified: User ID matches WhatsApp number")
    print(f"   ✅ Verified: Not Saurabh's conversation")
    
    return True


async def main():
    slugs = ["irfan", "mahima-kaushik"]
    results = []
    
    for slug in slugs:
        result = await attach_audio_correctly(slug)
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

