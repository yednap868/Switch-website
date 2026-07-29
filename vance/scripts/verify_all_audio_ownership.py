#!/usr/bin/env python3
"""
Script to verify all profiles have correct audio ownership.
Checks all public profiles and verifies their audio_conversation_id belongs to them.
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile
from services.profile_audio_service import profile_audio_service


def verify_all_audio_ownership():
    """Verify all profiles have correct audio ownership."""
    print("=" * 70)
    print("VERIFYING ALL PROFILE AUDIO OWNERSHIP")
    print("=" * 70)
    
    # Get all public profiles
    print("\n1. Fetching all public profiles...")
    public_profiles_ref = fs.collection("public_profiles")
    public_profiles = list(public_profiles_ref.stream())
    
    print(f"   Found {len(public_profiles)} public profiles")
    
    profiles_with_audio = []
    profiles_without_audio = []
    profiles_with_incorrect_audio = []
    
    print("\n2. Checking each profile...")
    print()
    
    for i, pub_doc in enumerate(public_profiles, 1):
        slug = pub_doc.id
        pub_data = pub_doc.to_dict() or {}
        user_id = pub_data.get("user_id")
        active = pub_data.get("active", True)
        
        if not user_id or not active:
            continue
        
        profile_doc = fs.collection("user_profiles").document(user_id).get()
        if not profile_doc.exists:
            continue
        
        profile_data = profile_doc.to_dict() or {}
        name = profile_data.get("name", user_id)
        conv_id = profile_data.get("audio_conversation_id", "")
        audio_available = profile_data.get("audio_available", False)
        
        if not conv_id or conv_id == "missing" or not audio_available:
            profiles_without_audio.append({"name": name, "user_id": user_id, "slug": slug})
            continue
        
        if not conv_id.startswith("conv_"):
            continue
        
        profiles_with_audio.append({
            "name": name,
            "user_id": user_id,
            "slug": slug,
            "conversation_id": conv_id,
        })
        
        # Verify ownership
        is_owner = profile_audio_service._verify_conversation_ownership(conv_id, user_id)
        
        status = "✅" if is_owner else "❌"
        print(f"{status} [{i}/{len(public_profiles)}] {name} ({slug}): {conv_id[:40]}...")
        
        if not is_owner:
            profiles_with_incorrect_audio.append({
                "name": name,
                "user_id": user_id,
                "slug": slug,
                "conversation_id": conv_id,
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total public profiles: {len(public_profiles)}")
    print(f"Profiles with audio: {len(profiles_with_audio)}")
    print(f"Profiles without audio: {len(profiles_without_audio)}")
    print(f"Profiles with INCORRECT audio: {len(profiles_with_incorrect_audio)}")
    
    if profiles_with_incorrect_audio:
        print("\n" + "=" * 70)
        print("❌ PROFILES WITH INCORRECT AUDIO")
        print("=" * 70)
        for issue in profiles_with_incorrect_audio:
            print(f"  - {issue['name']} ({issue['slug']})")
            print(f"    User ID: {issue['user_id']}")
            print(f"    Conversation ID: {issue['conversation_id']}")
            print()
    
    if profiles_without_audio and len(profiles_without_audio) <= 10:
        print("\n" + "=" * 70)
        print("PROFILES WITHOUT AUDIO")
        print("=" * 70)
        for profile in profiles_without_audio[:10]:
            print(f"  - {profile['name']} ({profile['slug']})")
    
    print("\n" + "=" * 70)
    if len(profiles_with_incorrect_audio) == 0:
        print("✅ ALL PROFILES WITH AUDIO HAVE CORRECT OWNERSHIP")
    else:
        print(f"⚠️  FOUND {len(profiles_with_incorrect_audio)} PROFILES WITH INCORRECT AUDIO")
    print("=" * 70)
    
    return len(profiles_with_incorrect_audio)


if __name__ == "__main__":
    try:
        issues_count = verify_all_audio_ownership()
        sys.exit(0 if issues_count == 0 else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

