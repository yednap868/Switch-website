#!/usr/bin/env python3
"""
Create profiles.vance.so profiles for all job seekers, one at a time.
Shows each profile link and waits for confirmation before proceeding.
"""

import sys
import os

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
            })
    
    return job_seekers


def create_profile_for_job_seeker(uid: str, name: str, extraction_data: dict):
    """Create/update profile for a job seeker."""
    try:
        # Use the same service that creates profiles during voice onboarding
        voice_extraction_service._sync_job_seeker_profile(
            user_id=uid,
            extraction_data=extraction_data,
        )
        
        # Get the created profile to find the slug
        profile_doc = fs.collection("user_profiles").document(uid).get()
        if not profile_doc.exists:
            return None, "Profile document not created"
        
        profile_data = profile_doc.to_dict() or {}
        slug = (
            profile_data.get("slug")
            or profile_data.get("public_slug")
            or profile_data.get("username")
            or uid
        )
        
        profile_url = f"https://profiles.vance.so/{slug}"
        return profile_url, "success"
        
    except Exception as e:
        return None, f"Error: {str(e)}"


def get_next_job_seeker_to_process():
    """Get the next job seeker that needs a profile created."""
    import json
    import os
    
    job_seekers = get_all_job_seekers()
    
    if not job_seekers:
        return None, None, None
    
    # Load processed list from file (if exists)
    processed_file = "/tmp/processed_job_seekers.json"
    processed_uids = set()
    if os.path.exists(processed_file):
        try:
            with open(processed_file, 'r') as f:
                processed_uids = set(json.load(f))
        except:
            pass
    
    # Find the first one that hasn't been processed yet
    for js in job_seekers:
        if js["uid"] in processed_uids:
            continue
            
        profile_doc = fs.collection("user_profiles").document(js["uid"]).get()
        if not profile_doc.exists:
            # Mark as processed before returning (so we don't show it again)
            processed_uids.add(js["uid"])
            with open(processed_file, 'w') as f:
                json.dump(list(processed_uids), f)
            return js, "new", len(job_seekers)
        
        profile_data = profile_doc.to_dict() or {}
        slug = profile_data.get("slug") or profile_data.get("public_slug")
        if not slug:
            # Mark as processed before returning
            processed_uids.add(js["uid"])
            with open(processed_file, 'w') as f:
                json.dump(list(processed_uids), f)
            return js, "needs_slug", len(job_seekers)
        
        # Has profile with slug - return it (will be marked as processed in process_one_job_seeker)
        return {
            **js,
            "slug": slug,
            "url": f"https://profiles.vance.so/{slug}" if slug else None,
        }, "existing", len(job_seekers)
    
    # All have been processed
    return None, "all_processed", len(job_seekers)


def process_one_job_seeker():
    """Process one job seeker - create profile if needed, return the link."""
    import json
    import os
    
    job_seeker, status, total = get_next_job_seeker_to_process()
    
    if not job_seeker:
        if status == "all_processed":
            return None, "All job seekers have been processed", total, 0
        return None, "No job seekers found", 0, 0
    
    if status == "existing":
        # Mark as processed
        processed_file = "/tmp/processed_job_seekers.json"
        processed_uids = set()
        if os.path.exists(processed_file):
            try:
                with open(processed_file, 'r') as f:
                    processed_uids = set(json.load(f))
            except:
                pass
        processed_uids.add(job_seeker["uid"])
        with open(processed_file, 'w') as f:
            json.dump(list(processed_uids), f)
        return job_seeker["url"], "existing", total, 0
    
    # Need to create profile
    profile_url, result_status = create_profile_for_job_seeker(
        uid=job_seeker["uid"],
        name=job_seeker["name"],
        extraction_data=job_seeker["extraction_data"],
    )
    
    # Mark as processed
    if profile_url:
        processed_file = "/tmp/processed_job_seekers.json"
        processed_uids = set()
        if os.path.exists(processed_file):
            try:
                with open(processed_file, 'r') as f:
                    processed_uids = set(json.load(f))
            except:
                pass
        processed_uids.add(job_seeker["uid"])
        with open(processed_file, 'w') as f:
            json.dump(list(processed_uids), f)
    
    return profile_url, result_status, total, 1


def main():
    print("=" * 70)
    print("JOB SEEKER PROFILE CREATION")
    print("=" * 70)
    
    # Process one at a time
    profile_url, status, total, created = process_one_job_seeker()
    
    if profile_url:
        print(f"\n✅ Profile ready!")
        print(f"   Profile URL: {profile_url}")
        print(f"   Status: {status}")
        if created:
            print(f"   ✅ Profile was just created")
        else:
            print(f"   ℹ️  Profile already existed")
    else:
        print(f"\n❌ {status}")
    
    print(f"\n📊 Progress: {total} total job seekers")
    print("\n" + "=" * 70)
    print("Run this script again to process the next job seeker")
    print("=" * 70)


if __name__ == "__main__":
    main()

