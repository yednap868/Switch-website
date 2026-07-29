#!/usr/bin/env python3
"""
Script to fix Kuldeep's audio by finding conversation_id from ElevenLabs and storing it.
"""
import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service


async def fix_kuldeep_audio():
    uid = "919206906847"
    print("=" * 70)
    print("FIXING KULDEEP AUDIO")
    print("=" * 70)
    
    # Get user profile to find phone number
    user_profile = get_user_profile(uid) or {}
    user_phone = user_profile.get("wa_id") or user_profile.get("phone") or uid
    
    print(f"User ID: {uid}")
    print(f"User Phone: {user_phone}")
    print()
    
    # Try to find conversation_id from ElevenLabs
    print("🔍 Searching for conversations in ElevenLabs...")
    conversation_ids = await profile_audio_service._list_conversations_by_user(str(user_phone))
    
    if conversation_ids:
        print(f"✅ Found {len(conversation_ids)} conversation(s)")
        
        # Try the first conversation_id (most recent)
        conv_id = conversation_ids[0]
        print(f"\n🎧 Using conversation_id: {conv_id}")
        
        # Verify it belongs to Kuldeep by trying to fetch audio
        print(f"🔍 Verifying conversation_id belongs to Kuldeep...")
        intro_url, thinking_url = await profile_audio_service._fetch_audio_from_elevenlabs_api(
            conv_id, user_id=uid, trim_intro=False, trim_thinking=False
        )
        
        if intro_url or thinking_url:
            print(f"✅ Successfully verified and fetched audio!")
            print(f"   Intro URL length: {len(intro_url) if intro_url else 0} chars")
            print(f"   Thinking URL length: {len(thinking_url) if thinking_url else 0} chars")
            
            # Store conversation_id for on-demand fetching
            # Audio is too large to store directly in Firestore, so we'll use on-demand fetching
            update = {
                "audio_conversation_id": conv_id,
                "audio_available": True,
                "audio_updated_at": time.time(),
                "audio_fetch_attempted_at": time.time(),
            }
            
            fs.collection("user_profiles").document(uid).set(update, merge=True)
            print(f"✅ Conversation ID stored for on-demand audio fetch!")
            print(f"   Conversation ID: {conv_id}")
            print(f"   Audio will be fetched on-demand via API endpoint")
            return True
        else:
            print(f"⚠️  No audio found for this conversation_id")
            return False
    else:
        print("⚠️  No conversations found in ElevenLabs")
        print("   This might mean the call was not recorded or conversation_id is not accessible")
        return False


if __name__ == "__main__":
    success = asyncio.run(fix_kuldeep_audio())
    print()
    print("=" * 70)
    if success:
        print("✅ COMPLETED SUCCESSFULLY")
    else:
        print("⚠️  COMPLETED WITH WARNINGS")
    print("=" * 70)
    sys.exit(0 if success else 1)

