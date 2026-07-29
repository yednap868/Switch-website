#!/usr/bin/env python3
"""
Script to attach audio to profiles by matching conversations to WhatsApp numbers only.
Fetches conversations from ElevenLabs and matches them by phone number.
"""
import sys
import os
import asyncio
import time
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile


async def get_conversations_by_phone(phone: str) -> list[dict]:
    """Get conversations from ElevenLabs API filtered by phone number."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not set")
        return []
    
    url = "https://api.elevenlabs.io/v1/convai/conversations"
    headers = {"xi-api-key": api_key}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get conversations
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            conversations = response.json()
            
            # Handle both list and dict responses
            if isinstance(conversations, dict):
                conversations = conversations.get("conversations", []) or conversations.get("data", []) or []
            
            # Filter by phone number - normalize phone for matching
            phone_normalized = str(phone).replace("+", "").replace("-", "").replace(" ", "")
            phone_last_10 = phone_normalized[-10:] if len(phone_normalized) >= 10 else phone_normalized
            
            matching = []
            for conv in conversations:
                if isinstance(conv, dict):
                    conv_id = conv.get("conversation_id") or conv.get("id") or conv.get("_id")
                    if not conv_id:
                        continue
                    
                    # Check various phone number fields
                    conv_phone = (
                        str(conv.get("user_phone", ""))
                        or str(conv.get("phone_number", ""))
                        or str(conv.get("phone", ""))
                        or str(conv.get("participant_phone", ""))
                        or str(conv.get("to", ""))
                        or str(conv.get("from", ""))
                    )
                    
                    if conv_phone:
                        conv_phone_normalized = conv_phone.replace("+", "").replace("-", "").replace(" ", "")
                        conv_phone_last_10 = conv_phone_normalized[-10:] if len(conv_phone_normalized) >= 10 else conv_phone_normalized
                        
                        # Match by last 10 digits
                        if phone_last_10 == conv_phone_last_10:
                            matching.append({
                                "conversation_id": str(conv_id),
                                "phone": conv_phone,
                                "metadata": conv
                            })
                            print(f"   ✅ Matched: {conv_id} (phone: {conv_phone})")
                    else:
                        # If no phone in metadata, we can't verify - skip it
                        print(f"   ⚠️  Skipping {conv_id} - no phone number in metadata")
            
            return matching
            
    except Exception as e:
        print(f"⚠️ Error fetching conversations: {e}")
        return []


async def attach_audio_by_phone(slug: str):
    """Attach audio by matching conversations to WhatsApp number."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"Attaching audio for: {slug}")
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
    print(f"WhatsApp Number: {phone}")
    
    # Get conversations from ElevenLabs filtered by phone
    print(f"\n1. Fetching conversations from ElevenLabs for phone {phone}...")
    matching_conversations = await get_conversations_by_phone(phone)
    
    if not matching_conversations:
        print(f"   ❌ No conversations found for phone {phone}")
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
        print(f"\n   ❌ No available conversations for {name}")
        return False
    
    # Use the first available conversation (most recent)
    selected_conv = available[0]
    conv_id = selected_conv["conversation_id"]
    
    print(f"\n3. Selected conversation: {conv_id}")
    print(f"   Phone match: {selected_conv.get('phone', 'N/A')}")
    
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
    print(f"   Verified by phone number: {phone}")
    
    return True


async def main():
    slugs = ["irfan", "mahima-kaushik"]
    results = []
    
    for slug in slugs:
        result = await attach_audio_by_phone(slug)
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

