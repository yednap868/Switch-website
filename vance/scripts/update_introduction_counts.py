#!/usr/bin/env python3
"""
Script to update each candidate profile with the number of introductions to founders.
Counts intro_requests where candidate_uid matches and requester is a job provider.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile, save_data_merge

def is_job_provider(uid: str) -> bool:
    """Check if a user is a job provider (founder)."""
    profile = get_user_profile(uid) or {}
    
    # Check explicit user_type
    user_type = profile.get("user_type", "").lower()
    if user_type == "job_provider":
        return True
    elif user_type == "job_seeker" or user_type == "candidate":
        return False
    
    # Check connection_type for hiring indicators
    connection_type = (profile.get("connection_type") or "").lower()
    if any(keyword in connection_type for keyword in ["hiring", "hire", "recruit", "looking to hire"]):
        return True
    
    return False

def get_all_candidates():
    """Get all job seekers/candidates from the database."""
    candidates = []
    
    # Get all users from user_profiles collection
    user_profiles_ref = fs.collection("user_profiles")
    user_profiles = user_profiles_ref.stream()
    
    for doc in user_profiles:
        user_data = doc.to_dict() or {}
        user_id = doc.id
        
        # Check if this is a candidate/job seeker
        user_type = user_data.get("user_type", "").lower()
        extraction_data = user_data.get("extraction_data", {}) or {}
        
        # Check multiple indicators
        is_candidate = (
            user_type in ("job_seeker", "candidate") or
            "looking for" in (user_data.get("connection_type") or "").lower() or
            "seeking" in (user_data.get("primary_goal") or "").lower()
        )
        
        if is_candidate:
            name = user_data.get("name") or extraction_data.get("name") or user_id
            candidates.append({
                "uid": user_id,
                "name": name,
            })
    
    # Also check public_profiles collection for candidates with slugs
    public_profiles_ref = fs.collection("public_profiles")
    public_profiles = public_profiles_ref.stream()
    
    for doc in public_profiles:
        profile_data = doc.to_dict() or {}
        user_id = profile_data.get("user_id")
        
        if user_id and profile_data.get("active", True):
            # Check if we already have this candidate
            if not any(c["uid"] == user_id for c in candidates):
                user_profile = get_user_profile(user_id) or {}
                name = user_profile.get("name") or profile_data.get("name") or user_id
                
                # Only add if it's a candidate
                user_type = user_profile.get("user_type", "").lower()
                if user_type in ("job_seeker", "candidate"):
                    candidates.append({
                        "uid": user_id,
                        "name": name,
                    })
    
    return candidates

def count_introductions_to_founders(candidate_uid: str) -> int:
    """Count how many introductions have been made to founders for this candidate."""
    try:
        # Query intro_requests where candidate_uid matches
        intro_requests = fs.collection("intro_requests").where("candidate_uid", "==", candidate_uid).stream()
        
        founder_intro_count = 0
        for intro_doc in intro_requests:
            intro_data = intro_doc.to_dict() or {}
            requester_uid = intro_data.get("requester_uid")
            
            # Check if requester is a job provider (founder)
            if requester_uid and is_job_provider(requester_uid):
                founder_intro_count += 1
        
        return founder_intro_count
    except Exception as e:
        print(f"   ⚠️  Error counting introductions: {e}")
        return 0

def update_introduction_counts():
    """Update all candidate profiles with introduction counts."""
    print("=" * 70)
    print("UPDATING INTRODUCTION COUNTS FOR ALL CANDIDATES")
    print("=" * 70)
    print()
    
    # Get all candidates
    print("📋 Fetching all candidates...")
    candidates = get_all_candidates()
    print(f"✅ Found {len(candidates)} candidates")
    print()
    
    updated_count = 0
    error_count = 0
    
    for idx, candidate in enumerate(candidates, 1):
        candidate_uid = candidate["uid"]
        candidate_name = candidate["name"]
        
        print(f"[{idx}/{len(candidates)}] Processing {candidate_name} ({candidate_uid})...")
        
        try:
            # Count introductions to founders
            founder_intro_count = count_introductions_to_founders(candidate_uid)
            
            # Update profile with count
            update_data = {
                "introductions_count": founder_intro_count,
                "founder_introductions_count": founder_intro_count,  # Also store as founder_introductions_count
            }
            
            # Update in user_profiles
            save_data_merge(candidate_uid, "users", update_data)
            
            # Also update in user_profiles collection if it exists
            user_profile_ref = fs.collection("user_profiles").document(candidate_uid)
            user_profile_doc = user_profile_ref.get()
            if user_profile_doc.exists:
                user_profile_ref.update(update_data)
            
            print(f"   ✅ Updated: {founder_intro_count} introductions to founders")
            updated_count += 1
            
        except Exception as e:
            print(f"   ❌ Error updating {candidate_name}: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
    
    print()
    print("=" * 70)
    print("✅ COMPLETED")
    print("=" * 70)
    print(f"Total candidates processed: {len(candidates)}")
    print(f"Successfully updated: {updated_count}")
    print(f"Errors: {error_count}")
    print()
    
    return updated_count, error_count

if __name__ == "__main__":
    updated, errors = update_introduction_counts()
    sys.exit(0 if errors == 0 else 1)

