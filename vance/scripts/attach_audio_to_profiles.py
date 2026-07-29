#!/usr/bin/env python3
"""
Attach intro and thinking audio to all job seeker profiles.
Fetches audio from ElevenLabs using conversation_id from call history.
"""

import sys
import os
import asyncio
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_extraction_data, get_user_profile
from services.profile_audio_service import profile_audio_service


def get_all_job_seekers():
    """Get all job seekers from extractions collection."""
    extractions_ref = fs.collection("extractions")
    all_extractions = extractions_ref.stream()
    
    job_seekers = []
    for ext_doc in all_extractions:
        ext_data = ext_doc.to_dict() or {}
        uid = ext_doc.id
        
        # Check if it's a job seeker (has target_role or core_skills)
        if ext_data.get("target_role") or ext_data.get("core_skills"):
            user_profile = get_user_profile(uid) or {}
            name = user_profile.get("name") or ext_data.get("name") or uid
            
            job_seekers.append({
                "uid": uid,
                "name": name,
            })
    
    return job_seekers


def find_conversation_id(uid: str) -> str:
    """Find conversation_id from multiple sources."""
    try:
        # 1. Check user_calls collection (most reliable source)
        calls_ref = fs.collection("user_calls").document(uid).collection("calls")
        # Try with timestamp ordering first
        try:
            calls = calls_ref.order_by("timestamp", direction="DESCENDING").limit(10).stream()
        except:
            # If timestamp ordering fails, just get all calls
            calls = calls_ref.limit(10).stream()
        
        for call_doc in calls:
            call_data = call_doc.to_dict() or {}
            conversation_id = call_data.get("conversation_id")
            # Check if it's a valid conversation_id (starts with conv_)
            if conversation_id and conversation_id.strip() and conversation_id.startswith("conv_"):
                return conversation_id.strip()
            # Also check call_id as fallback
            call_id = call_data.get("call_id")
            if call_id and call_id.strip() and call_id.startswith("conv_"):
                return call_id.strip()
        
        # 2. Check user_profiles for stored conversation_id
        profile_doc = fs.collection("user_profiles").document(uid).get()
        if profile_doc.exists:
            profile_data = profile_doc.to_dict() or {}
            conversation_id = profile_data.get("audio_conversation_id")
            if conversation_id and conversation_id != "missing" and conversation_id.startswith("conv_"):
                return conversation_id
        
        # 3. Search all calls collection group (comprehensive search)
        try:
            from firebase_admin import firestore
            all_calls_query = (
                fs.collection_group("calls")
                .where("user_id", "==", uid)
                .limit(10)
            )
            for call_doc in all_calls_query.stream():
                call_data = call_doc.to_dict() or {}
                conversation_id = call_data.get("conversation_id")
                if conversation_id and conversation_id.strip() and conversation_id.startswith("conv_"):
                    return conversation_id.strip()
                call_id = call_data.get("call_id")
                if call_id and call_id.strip() and call_id.startswith("conv_"):
                    return call_id.strip()
        except Exception as e:
            # Collection group queries might fail, that's okay
            pass
        
        return ""
    except Exception as e:
        print(f"  ⚠️  Error finding conversation_id: {e}")
        return ""


async def attach_audio_to_profile(uid: str, name: str) -> bool:
    """Attach audio to a profile using conversation_id."""
    print(f"\n{'='*70}")
    print(f"Processing: {name} ({uid})")
    print(f"{'='*70}")
    
    # Check if audio already exists
    profile_doc = fs.collection("user_profiles").document(uid).get()
    if profile_doc.exists:
        profile_data = profile_doc.to_dict() or {}
        intro_audio = profile_data.get("intro_audio_url", "")
        thinking_audio = profile_data.get("thinking_audio_url", "")
        
        if intro_audio and thinking_audio:
            print(f"✅ Audio already attached (intro: {len(intro_audio)} chars, thinking: {len(thinking_audio)} chars)")
            return True
    
    # Find conversation_id from stored records first
    print(f"🔍 Finding conversation_id from call history...")
    conversation_id = find_conversation_id(uid)
    
    # Create payload
    payload = {}
    if conversation_id:
        print(f"✅ Found conversation_id in call history: {conversation_id}")
        payload = {
            "conversation_id": conversation_id,
            "data": {
                "conversation_id": conversation_id,
            }
        }
    else:
        print(f"ℹ️  No conversation_id in call history, will search ElevenLabs by user ID...")
        # Empty payload - service will try to find by user ID/phone
        payload = {}
    
    # Attach audio using the service (it will search by user ID if conversation_id not in payload)
    print(f"🎧 Fetching audio from ElevenLabs...")
    try:
        await profile_audio_service.attach_call_recording_to_profile(
            user_id=uid,
            payload=payload,
        )
        
        # Verify it was attached
        profile_doc = fs.collection("user_profiles").document(uid).get()
        if profile_doc.exists:
            profile_data = profile_doc.to_dict() or {}
            intro_audio = profile_data.get("intro_audio_url", "")
            thinking_audio = profile_data.get("thinking_audio_url", "")
            
            if intro_audio and thinking_audio:
                print(f"✅ Audio attached successfully!")
                print(f"   Intro audio: {len(intro_audio)} chars")
                print(f"   Thinking audio: {len(thinking_audio)} chars")
                return True
            else:
                print(f"⚠️  Audio fetch attempted but URLs not found in profile")
                return False
        else:
            print(f"⚠️  Profile document not found after audio attachment")
            return False
            
    except Exception as e:
        print(f"❌ Error attaching audio: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 70)
    print("ATTACHING AUDIO TO ALL JOB SEEKER PROFILES")
    print("=" * 70)
    print("\nThis will:")
    print("  - Find conversation_id from call history")
    print("  - Fetch audio from ElevenLabs API")
    print("  - Attach intro_audio_url and thinking_audio_url to profiles")
    print("\n" + "=" * 70)
    
    job_seekers = get_all_job_seekers()
    print(f"\nFound {len(job_seekers)} job seekers to process\n")
    
    success_count = 0
    already_attached = 0
    failed_count = 0
    
    for i, js in enumerate(job_seekers, 1):
        print(f"\n[{i}/{len(job_seekers)}]")
        try:
            # Check if already has audio
            profile_doc = fs.collection("user_profiles").document(js["uid"]).get()
            if profile_doc.exists:
                profile_data = profile_doc.to_dict() or {}
                if profile_data.get("intro_audio_url") and profile_data.get("thinking_audio_url"):
                    print(f"✅ {js['name']}: Audio already attached")
                    already_attached += 1
                    continue
            
            result = await attach_audio_to_profile(js["uid"], js["name"])
            if result:
                success_count += 1
            else:
                failed_count += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Error processing {js['name']}: {e}")
            failed_count += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"✅ COMPLETE:")
    print(f"  Successfully attached: {success_count}")
    print(f"  Already had audio: {already_attached}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(job_seekers)}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

