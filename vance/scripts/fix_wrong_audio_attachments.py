#!/usr/bin/env python3
"""
Script to fix profiles with incorrect conversation_id attachments.
Checks each user's stored conversation_id and verifies ownership.
If conversation_id doesn't belong to the user, it's cleared.
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service


def verify_conversation_ownership(conversation_id: str, user_id: str) -> bool:
    """Verify that a conversation_id belongs to a specific user_id."""
    if not conversation_id or not user_id:
        return False
    
    try:
        # Check user_calls/{user_id}/calls for this conversation_id
        calls_ref = fs.collection("user_calls").document(user_id).collection("calls")
        calls_query = calls_ref.where("conversation_id", "==", conversation_id).limit(1)
        matching_calls = list(calls_query.stream())
        
        if matching_calls:
            return True
        
        # Check if conversation_id is already stored for this user in user_profiles
        profile_doc = fs.collection("user_profiles").document(user_id).get()
        if profile_doc.exists:
            profile_data = profile_doc.to_dict() or {}
            stored_conv_id = profile_data.get("audio_conversation_id")
            if stored_conv_id == conversation_id:
                # This is a circular check - need to verify via call history
                # If call history doesn't have it, it's likely wrong
                return False
        
        return False
        
    except Exception as e:
        print(f"   ⚠️  Error verifying ownership: {e}")
        return False


async def fix_user_audio(user_id: str, name: str) -> bool:
    """Fix audio attachment for a single user."""
    print(f"\n{'='*70}")
    print(f"Checking: {name} ({user_id})")
    print(f"{'='*70}")
    
    try:
        # Check user_profiles for stored conversation_id
        profile_doc = fs.collection("user_profiles").document(user_id).get()
        if not profile_doc.exists:
            print(f"   ℹ️  No user_profiles document found")
            return False
        
        profile_data = profile_doc.to_dict() or {}
        stored_conv_id = profile_data.get("audio_conversation_id")
        
        if not stored_conv_id or stored_conv_id == "missing":
            print(f"   ℹ️  No conversation_id stored (or marked as missing)")
            return False
        
        if not stored_conv_id.startswith("conv_"):
            print(f"   ⚠️  Invalid conversation_id format: {stored_conv_id}")
            return False
        
        print(f"   Found conversation_id: {stored_conv_id}")
        
        # Verify ownership
        is_valid = verify_conversation_ownership(stored_conv_id, user_id)
        
        if not is_valid:
            print(f"   ❌ conversation_id does NOT belong to this user!")
            print(f"   🔧 Clearing incorrect conversation_id and audio URLs...")
            
            # Clear the incorrect conversation_id and audio URLs
            fs.collection("user_profiles").document(user_id).update({
                "audio_conversation_id": "missing",
                "intro_audio_url": "",
                "thinking_audio_url": "",
                "audio_available": False,
            })
            
            print(f"   ✅ Cleared incorrect audio attachment")
            return True
        else:
            print(f"   ✅ conversation_id is valid - belongs to this user")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def fix_all_wrong_attachments():
    """Fix all profiles with incorrect conversation_id attachments."""
    print("=" * 70)
    print("FIXING INCORRECT AUDIO ATTACHMENTS")
    print("=" * 70)
    print()
    
    # Get all job seekers
    print("📋 Fetching all job seekers...")
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
    
    print(f"✅ Found {len(job_seekers)} job seekers")
    print()
    
    fixed_count = 0
    
    for idx, candidate in enumerate(job_seekers, 1):
        print(f"[{idx}/{len(job_seekers)}]")
        was_fixed = await fix_user_audio(candidate["uid"], candidate["name"])
        if was_fixed:
            fixed_count += 1
    
    print()
    print("=" * 70)
    print("✅ COMPLETED")
    print("=" * 70)
    print(f"Total candidates checked: {len(job_seekers)}")
    print(f"Fixed incorrect attachments: {fixed_count}")
    print()
    
    return fixed_count


if __name__ == "__main__":
    fixed = asyncio.run(fix_all_wrong_attachments())
    sys.exit(0 if fixed >= 0 else 1)

