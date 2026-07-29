#!/usr/bin/env python3
"""
List all job seeker profile links.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_extraction_data, get_user_profile


def get_all_job_seeker_profiles():
    """Get all job seekers with their profile links."""
    # First, build a map of user_id -> slug from public_profiles collection
    public_profiles_ref = fs.collection("public_profiles")
    all_public_profiles = public_profiles_ref.stream()
    
    slug_map = {}  # user_id -> slug
    for profile_doc in all_public_profiles:
        profile_data = profile_doc.to_dict() or {}
        if profile_data.get("active", True):  # Only active profiles
            user_id = profile_data.get("user_id")
            slug = profile_doc.id  # Document ID is the slug
            if user_id:
                slug_map[user_id] = slug
    
    # Now get all job seekers from extractions
    extractions_ref = fs.collection("extractions")
    all_extractions = extractions_ref.stream()
    
    profiles = []
    for ext_doc in all_extractions:
        ext_data = ext_doc.to_dict() or {}
        uid = ext_doc.id
        
        # Check if it's a job seeker (has target_role or core_skills)
        if ext_data.get("target_role") or ext_data.get("core_skills"):
            user_profile = get_user_profile(uid) or {}
            name = user_profile.get("name") or ext_data.get("name") or uid
            
            # Get profile slug from multiple sources
            slug = (
                user_profile.get("slug")
                or user_profile.get("public_slug")
                or user_profile.get("username")
                or slug_map.get(uid)  # Check public_profiles collection
            )
            
            if slug:
                profile_url = f"https://profiles.vance.so/{slug}"
            else:
                profile_url = None
            
            profiles.append({
                "uid": uid,
                "name": name,
                "slug": slug,
                "url": profile_url,
            })
    
    # Sort by name for easier reading
    profiles.sort(key=lambda x: x["name"].lower() if x["name"] else "")
    
    return profiles


def main():
    print("=" * 70)
    print("ALL JOB SEEKER PROFILE LINKS")
    print("=" * 70)
    print()
    
    profiles = get_all_job_seeker_profiles()
    
    print(f"Total job seekers: {len(profiles)}\n")
    
    for i, profile in enumerate(profiles, 1):
        if profile["url"]:
            print(f"{i}. {profile['name']} ({profile['uid']})")
            print(f"   {profile['url']}")
        else:
            print(f"{i}. {profile['name']} ({profile['uid']})")
            print(f"   ⚠️  No profile link (missing slug)")
        print()
    
    print("=" * 70)
    
    # Also print just URLs for easy copying
    print("\nURLs only (for easy copying):")
    print("-" * 70)
    for profile in profiles:
        if profile["url"]:
            print(profile["url"])


if __name__ == "__main__":
    main()

