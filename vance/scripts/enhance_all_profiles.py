#!/usr/bin/env python3
"""
Enhance all job seeker profiles:
1. Attach LinkedIn URLs
2. Fill missing fields (story, strengths, proofOfWork, thoughts)
3. Set 100% verification status
4. Ensure all fields are populated
"""

import sys
import os
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_extraction_data, get_user_profile
from services.voice_extraction_service import voice_extraction_service


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
                "extraction_data": ext_data,
                "user_profile": user_profile,
            })
    
    return job_seekers


def enhance_profile(uid: str, name: str, extraction_data: dict, user_profile: dict):
    """Enhance a single profile with all missing data."""
    print(f"\n{'='*70}")
    print(f"Enhancing profile for: {name} ({uid})")
    print(f"{'='*70}")
    
    updates = {}
    
    # 1. Get LinkedIn URL from multiple sources
    linkedin_url = (
        user_profile.get("linkedin_url")
        or extraction_data.get("linkedin_url")
        or ""
    )
    
    if linkedin_url:
        updates["linkedin_url"] = linkedin_url
        print(f"✅ LinkedIn URL: {linkedin_url}")
    else:
        print(f"⚠️  No LinkedIn URL found")
    
    # 2. Get or generate high-signal fields (story, strengths, proofOfWork, thoughts)
    profile_doc = fs.collection("user_profiles").document(uid).get()
    profile_data = profile_doc.to_dict() if profile_doc.exists else {}
    
    has_story = bool(profile_data.get("story"))
    has_strengths = bool(profile_data.get("strengths"))
    has_proof = bool(profile_data.get("proofOfWork") or profile_data.get("proof_of_work"))
    has_thoughts = bool(profile_data.get("thoughts"))
    
    if not (has_story and has_strengths and has_proof and has_thoughts):
        print(f"📝 Generating high-signal fields...")
        high_signal = voice_extraction_service._generate_high_signal_profile(
            user_id=uid,
            name=name,
            extraction_data=extraction_data,
        )
        if high_signal:
            updates.update(high_signal)
            print(f"✅ Generated: story={bool(high_signal.get('story'))}, "
                  f"strengths={len(high_signal.get('strengths', []))}, "
                  f"proofOfWork={len(high_signal.get('proofOfWork', []))}, "
                  f"thoughts={len(high_signal.get('thoughts', []))}")
    else:
        print(f"✅ High-signal fields already exist")
    
    # 3. Set verification status (100% verified)
    verification_score = profile_data.get("verification_score", 0)
    verification_percentile = profile_data.get("verification_percentile", 0)
    verified_at_display = profile_data.get("verified_at_display", "")
    
    if verification_score != 100 or verification_percentile != 6 or not verified_at_display:
        updates["verification_score"] = 100
        updates["verification_percentile"] = 6
        updates["verified_at_display"] = datetime.now().strftime("%B %d, %Y")
        print(f"✅ Set verification: 100% verified (Top 6%)")
    else:
        print(f"✅ Verification already set")
    
    # 4. Ensure avatar URL exists (try to fetch from LinkedIn if missing)
    avatar_url = (
        profile_data.get("avatar_url")
        or user_profile.get("avatar_url")
        or extraction_data.get("avatar_url")
    )
    
    if not avatar_url and linkedin_url:
        print(f"🖼️  Fetching avatar from LinkedIn...")
        avatar_url = voice_extraction_service._fetch_avatar_from_linkedin(linkedin_url)
        if avatar_url:
            updates["avatar_url"] = avatar_url
            print(f"✅ Avatar URL: {avatar_url}")
    
    if avatar_url and not profile_data.get("avatar_url"):
        updates["avatar_url"] = avatar_url
    
    # 5. Ensure email is present
    email = (
        profile_data.get("email")
        or user_profile.get("email")
        or extraction_data.get("email")
        or ""
    )
    if email and not profile_data.get("email"):
        updates["email"] = email
    
    # 6. Ensure name is present
    if name and not profile_data.get("name"):
        updates["name"] = name
    
    # 7. Ensure slug exists
    slug = (
        profile_data.get("slug")
        or profile_data.get("public_slug")
        or profile_data.get("username")
    )
    if not slug:
        print(f"🔗 Generating slug...")
        slug = voice_extraction_service._ensure_public_slug(user_id=uid, name=name)
        updates["slug"] = slug
        print(f"✅ Slug: {slug}")
    
    # 8. Ensure extraction_data is stored
    if extraction_data and not profile_data.get("extraction_data"):
        updates["extraction_data"] = extraction_data
    
    # 9. Set updated timestamp
    updates["updated_at"] = time.time()
    
    # Apply updates
    if updates:
        fs.collection("user_profiles").document(uid).set(updates, merge=True)
        print(f"✅ Updated profile with {len(updates)} fields")
        return True
    else:
        print(f"ℹ️  No updates needed")
        return False


def main():
    print("=" * 70)
    print("ENHANCING ALL JOB SEEKER PROFILES")
    print("=" * 70)
    print("\nThis will:")
    print("  - Attach LinkedIn URLs to profiles")
    print("  - Generate missing high-signal fields (story, strengths, proof, thoughts)")
    print("  - Set 100% verification status (Top 6%)")
    print("  - Fill in all missing fields")
    print("\n" + "=" * 70)
    
    job_seekers = get_all_job_seekers()
    print(f"\nFound {len(job_seekers)} job seekers to process\n")
    
    updated_count = 0
    for i, js in enumerate(job_seekers, 1):
        print(f"\n[{i}/{len(job_seekers)}] Processing...")
        try:
            updated = enhance_profile(
                uid=js["uid"],
                name=js["name"],
                extraction_data=js["extraction_data"],
                user_profile=js["user_profile"],
            )
            if updated:
                updated_count += 1
        except Exception as e:
            print(f"❌ Error processing {js['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"✅ COMPLETE: Updated {updated_count} out of {len(job_seekers)} profiles")
    print("=" * 70)


if __name__ == "__main__":
    main()

