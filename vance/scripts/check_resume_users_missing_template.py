#!/usr/bin/env python3
"""
Check users created from resumes who haven't received profile link template messages.

This script:
1. Finds users with resume data
2. Checks if they have profiles
3. Checks if profile link was sent
4. Lists users missing template messages
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile


def get_users_with_resumes() -> List[Dict]:
    """Get all users who have resume data."""
    print("🔍 Fetching users with resume data...")
    
    users_with_resumes = []
    
    try:
        # Method 1: Check user_profiles collection for resume data
        profiles_ref = fs.collection("user_profiles")
        profiles = profiles_ref.stream()
        
        for profile_doc in profiles:
            profile_data = profile_doc.to_dict() or {}
            uid = profile_doc.id
            
            # Check for resume data in multiple places
            extraction_data = profile_data.get("extraction_data", {})
            resume_url = profile_data.get("resume_url") or extraction_data.get("resume_url")
            resume_path = extraction_data.get("resume_path")
            resume_extracted_numbers = extraction_data.get("resume_extracted_numbers", {})
            resume_filename = extraction_data.get("resume_filename")
            
            # Also check if source is resume_import
            source = profile_data.get("source", "")
            
            # Check if user has resume data
            has_resume = bool(
                resume_url 
                or resume_path 
                or resume_filename
                or (resume_extracted_numbers and isinstance(resume_extracted_numbers, dict) and resume_extracted_numbers.get("phone_number"))
                or source == "resume_import"
            )
            
            if has_resume:
                # Get user data
                user_doc = fs.collection("users").document(uid).get()
                user_data = user_doc.to_dict() if user_doc.exists else {}
                
                # Also check user source
                user_source = user_data.get("source", "")
                
                users_with_resumes.append({
                    "uid": uid,
                    "profile_data": profile_data,
                    "user_data": user_data,
                    "resume_url": resume_url,
                    "resume_path": resume_path,
                    "resume_filename": resume_filename,
                    "resume_extracted_numbers": resume_extracted_numbers,
                    "source": source or user_source,
                })
        
        # Method 2: Also check users collection for resume_import source
        users_ref = fs.collection("users")
        users = users_ref.stream()
        
        seen_uids = {u["uid"] for u in users_with_resumes}
        
        for user_doc in users:
            user_data = user_doc.to_dict() or {}
            uid = user_doc.id
            
            if uid in seen_uids:
                continue
            
            # Check if source is resume_import
            source = user_data.get("source", "")
            if source == "resume_import":
                # Get profile data
                profile_doc = fs.collection("user_profiles").document(uid).get()
                profile_data = profile_doc.to_dict() if profile_doc.exists else {}
                extraction_data = profile_data.get("extraction_data", {})
                
                users_with_resumes.append({
                    "uid": uid,
                    "profile_data": profile_data,
                    "user_data": user_data,
                    "resume_url": profile_data.get("resume_url") or extraction_data.get("resume_url"),
                    "resume_path": extraction_data.get("resume_path"),
                    "resume_filename": extraction_data.get("resume_filename"),
                    "resume_extracted_numbers": extraction_data.get("resume_extracted_numbers", {}),
                    "source": source,
                })
        
        print(f"   ✅ Found {len(users_with_resumes)} users with resume data")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return users_with_resumes


def check_profile_links(users: List[Dict]) -> List[Dict]:
    """Check which users have received profile link messages."""
    print("\n📋 Checking profile link status...")
    
    results = []
    
    for user in users:
        uid = user["uid"]
        profile_data = user["profile_data"]
        
        # Check if profile exists
        slug = (
            profile_data.get("slug")
            or profile_data.get("public_slug")
            or profile_data.get("username")
        )
        profile_url = f"https://profiles.vance.so/{slug}" if slug else None
        
        # Check if profile link was sent
        profile_link_doc = fs.collection("post_call_profile_links").document(uid).get()
        profile_link_sent = profile_link_doc.exists
        profile_link_data = profile_link_doc.to_dict() if profile_link_sent else {}
        
        # Get name
        name = (
            profile_data.get("name")
            or user["user_data"].get("name")
            or user["user_data"].get("profile", {}).get("name")
            or "Unknown"
        )
        
        # Get phone
        phone = (
            profile_data.get("phone")
            or profile_data.get("whatsapp")
            or user["user_data"].get("phone")
            or user["user_data"].get("wa_id")
            or uid
        )
        
        # Get resume phone
        resume_phone = None
        if user["resume_extracted_numbers"] and isinstance(user["resume_extracted_numbers"], dict):
            resume_phone = user["resume_extracted_numbers"].get("phone_number")
        
        # Check call history
        call_summary_doc = fs.collection("user_call_summaries").document(uid).get()
        has_calls = call_summary_doc.exists
        call_summary = call_summary_doc.to_dict() if has_calls else {}
        total_calls = call_summary.get("total_calls", 0)
        
        result = {
            "uid": uid,
            "name": name,
            "phone": phone,
            "resume_phone": resume_phone,
            "has_profile": bool(slug),
            "profile_url": profile_url,
            "profile_link_sent": profile_link_sent,
            "profile_link_data": profile_link_data,
            "has_calls": has_calls,
            "total_calls": total_calls,
            "resume_url": user["resume_url"],
            "resume_path": user["resume_path"],
            "created_at": profile_data.get("created_at") or user["user_data"].get("created_at"),
        }
        
        results.append(result)
    
    return results


def print_summary(results: List[Dict]):
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("📊 SUMMARY STATISTICS")
    print("=" * 80)
    
    total = len(results)
    with_profiles = sum(1 for r in results if r["has_profile"])
    with_calls = sum(1 for r in results if r["has_calls"])
    profile_links_sent = sum(1 for r in results if r["profile_link_sent"])
    missing_template = sum(1 for r in results if r["has_profile"] and not r["profile_link_sent"])
    with_resume_phone = sum(1 for r in results if r["resume_phone"])
    
    print(f"\n📈 Total Users with Resumes: {total}")
    print(f"   ✅ With Profiles: {with_profiles} ({with_profiles/total*100:.1f}%)")
    print(f"   📞 With Call History: {with_calls} ({with_calls/total*100:.1f}%)")
    print(f"   📱 Profile Links Sent: {profile_links_sent} ({profile_links_sent/total*100:.1f}%)")
    print(f"   ⚠️  Missing Template (have profile, no link sent): {missing_template}")
    print(f"   📄 With Resume Phone: {with_resume_phone} ({with_resume_phone/total*100:.1f}%)")
    
    return {
        "total": total,
        "with_profiles": with_profiles,
        "missing_template": missing_template,
    }


def print_missing_template_users(results: List[Dict]):
    """Print users who have profiles but haven't received template messages."""
    print("\n" + "=" * 80)
    print("⚠️  USERS WITH PROFILES BUT NO TEMPLATE MESSAGE SENT")
    print("=" * 80)
    
    missing = [r for r in results if r["has_profile"] and not r["profile_link_sent"]]
    
    if not missing:
        print("\n✅ All users with profiles have received template messages!")
        return
    
    print(f"\nFound {len(missing)} users missing template messages:\n")
    
    for i, user in enumerate(missing, 1):
        print(f"{i}. {user['name']} (UID: {user['uid'][:12]}...)")
        print(f"   Phone: {user['phone']}")
        if user['resume_phone']:
            print(f"   📄 Resume Phone: {user['resume_phone']}")
        print(f"   🔗 Profile: {user['profile_url']}")
        if user['has_calls']:
            print(f"   📞 Calls: {user['total_calls']} call(s)")
        else:
            print(f"   ⚠️  No call history")
        if user['created_at']:
            created_date = datetime.fromtimestamp(user['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            print(f"   📅 Created: {created_date}")
        print()


def export_missing_users(results: List[Dict], output_file: str = "missing_template_users.csv"):
    """Export users missing template messages to CSV."""
    import csv
    
    missing = [r for r in results if r["has_profile"] and not r["profile_link_sent"]]
    
    if not missing:
        print(f"\n✅ No users missing template messages to export")
        return
    
    print(f"\n💾 Exporting {len(missing)} users to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'uid', 'phone', 'resume_phone', 'profile_url', 
            'total_calls', 'has_calls', 'resume_url', 'created_at'
        ])
        writer.writeheader()
        
        for user in missing:
            created_str = ""
            if user['created_at']:
                created_str = datetime.fromtimestamp(user['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            
            writer.writerow({
                'name': user['name'],
                'uid': user['uid'],
                'phone': user['phone'],
                'resume_phone': user['resume_phone'] or '',
                'profile_url': user['profile_url'] or '',
                'total_calls': user['total_calls'],
                'has_calls': 'Yes' if user['has_calls'] else 'No',
                'resume_url': user['resume_url'] or user['resume_path'] or '',
                'created_at': created_str,
            })
    
    print(f"   ✅ Exported {len(missing)} records")


def main():
    print("=" * 80)
    print("🔍 RESUME USERS - MISSING TEMPLATE MESSAGES ANALYSIS")
    print("=" * 80)
    
    # Get users with resumes
    users = get_users_with_resumes()
    
    if not users:
        print("\n❌ No users with resume data found")
        return
    
    # Check profile links
    results = check_profile_links(users)
    
    # Print summary
    stats = print_summary(results)
    
    # Print missing template users
    print_missing_template_users(results)
    
    # Export to CSV
    export_missing_users(results)
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete")
    print("=" * 80)
    
    # Print profile URLs for missing users
    missing = [r for r in results if r["has_profile"] and not r["profile_link_sent"]]
    if missing:
        print("\n🔗 PROFILE LINKS (Missing Template Messages):")
        print("-" * 80)
        for user in missing:
            print(user['profile_url'])


if __name__ == "__main__":
    main()

