#!/usr/bin/env python3
"""
Check job seekers created through outbound calls.

This script:
1. Finds all job seekers/candidates
2. Checks if profiles were created
3. Gets their profile links
4. Verifies Firestore storage
5. Shows statistics
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile


def get_all_job_seekers() -> List[Dict]:
    """Get all job seekers from Firestore."""
    print("🔍 Fetching all job seekers from Firestore...")
    
    job_seekers = []
    
    try:
        # Get from users collection
        users_ref = fs.collection("users")
        users = users_ref.stream()
        
        for user_doc in users:
            user_data = user_doc.to_dict() or {}
            user_id = user_doc.id
            
            # Check user type
            profile = user_data.get("profile", {})
            user_type = profile.get("user_type", "")
            
            # Also check extraction data for intent
            extraction_data = user_data.get("extraction_data", {})
            intent = extraction_data.get("intent", "")
            
            # Check if job seeker or candidate
            if user_type in {"job_seeker", "candidate"} or intent in {"job_seeker_need", "candidate"}:
                job_seekers.append({
                    "uid": user_id,
                    "user_data": user_data,
                    "user_type": user_type,
                    "intent": intent,
                })
        
        print(f"   ✅ Found {len(job_seekers)} job seekers in users collection")
        
    except Exception as e:
        print(f"   ❌ Error fetching from users: {e}")
    
    return job_seekers


def check_profiles(job_seekers: List[Dict]) -> List[Dict]:
    """Check if profiles exist for job seekers."""
    print("\n📋 Checking profiles for each job seeker...")
    
    results = []
    
    for js in job_seekers:
        uid = js["uid"]
        
        # Check user_profiles collection
        profile_doc = fs.collection("user_profiles").document(uid).get()
        has_profile = profile_doc.exists
        
        profile_data = {}
        slug = None
        profile_url = None
        
        if has_profile:
            profile_data = profile_doc.to_dict() or {}
            slug = (
                profile_data.get("slug")
                or profile_data.get("public_slug")
                or profile_data.get("username")
            )
            if slug:
                profile_url = f"https://profiles.vance.so/{slug}"
        
        # Check extraction data
        extraction_doc = fs.collection("extractions").document(uid).get()
        has_extraction = extraction_doc.exists
        extraction_data = extraction_doc.to_dict() if has_extraction else {}
        
        # Check call history
        call_summary_doc = fs.collection("user_call_summaries").document(uid).get()
        has_calls = call_summary_doc.exists
        call_summary = call_summary_doc.to_dict() if has_calls else {}
        total_calls = call_summary.get("total_calls", 0)
        
        # Check if profile link was sent
        profile_link_doc = fs.collection("post_call_profile_links").document(uid).get()
        profile_link_sent = profile_link_doc.exists
        profile_link_data = profile_link_doc.to_dict() if profile_link_sent else {}
        
        # Get name
        name = (
            profile_data.get("name")
            or js["user_data"].get("name")
            or extraction_data.get("name")
            or js["user_data"].get("profile", {}).get("name")
            or "Unknown"
        )
        
        # Get phone
        phone = (
            profile_data.get("phone")
            or profile_data.get("whatsapp")
            or js["user_data"].get("phone")
            or js["user_data"].get("wa_id")
            or extraction_data.get("phone_number")
            or uid
        )
        
        # Check resume data
        resume_phone = None
        if profile_data.get("extraction_data", {}).get("resume_extracted_numbers", {}):
            resume_numbers = profile_data.get("extraction_data", {}).get("resume_extracted_numbers", {})
            resume_phone = resume_numbers.get("phone_number") if isinstance(resume_numbers, dict) else None
        
        result = {
            "uid": uid,
            "name": name,
            "phone": phone,
            "resume_phone": resume_phone,
            "has_profile": has_profile,
            "slug": slug,
            "profile_url": profile_url,
            "has_extraction": has_extraction,
            "has_calls": has_calls,
            "total_calls": total_calls,
            "profile_link_sent": profile_link_sent,
            "profile_link_data": profile_link_data,
            "created_at": profile_data.get("created_at") or js["user_data"].get("created_at"),
            "updated_at": profile_data.get("updated_at"),
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
    with_slugs = sum(1 for r in results if r["slug"])
    with_calls = sum(1 for r in results if r["has_calls"])
    with_extractions = sum(1 for r in results if r["has_extraction"])
    profile_links_sent = sum(1 for r in results if r["profile_link_sent"])
    with_resume_phone = sum(1 for r in results if r["resume_phone"])
    
    print(f"\n📈 Total Job Seekers: {total}")
    print(f"   ✅ With Profiles: {with_profiles} ({with_profiles/total*100:.1f}%)")
    print(f"   🔗 With Profile URLs: {with_slugs} ({with_slugs/total*100:.1f}%)")
    print(f"   📞 With Call History: {with_calls} ({with_calls/total*100:.1f}%)")
    print(f"   📝 With Extraction Data: {with_extractions} ({with_extractions/total*100:.1f}%)")
    print(f"   📱 Profile Links Sent: {profile_links_sent} ({profile_links_sent/total*100:.1f}%)")
    print(f"   📄 With Resume Phone: {with_resume_phone} ({with_resume_phone/total*100:.1f}%)")
    
    # Average calls
    calls_list = [r["total_calls"] for r in results if r["has_calls"]]
    if calls_list:
        avg_calls = sum(calls_list) / len(calls_list)
        print(f"   📊 Average Calls per User: {avg_calls:.1f}")
    
    return {
        "total": total,
        "with_profiles": with_profiles,
        "with_slugs": with_slugs,
        "with_calls": with_calls,
        "profile_links_sent": profile_links_sent,
    }


def print_detailed_list(results: List[Dict]):
    """Print detailed list of all job seekers."""
    print("\n" + "=" * 80)
    print("📋 DETAILED LIST")
    print("=" * 80)
    
    # Sort by created_at (newest first)
    sorted_results = sorted(
        results,
        key=lambda x: x["created_at"] or 0,
        reverse=True
    )
    
    for i, result in enumerate(sorted_results, 1):
        print(f"\n{i}. {result['name']} (UID: {result['uid'][:12]}...)")
        print(f"   Phone: {result['phone']}")
        if result['resume_phone']:
            print(f"   📄 Resume Phone: {result['resume_phone']}")
        
        if result['has_profile']:
            print(f"   ✅ Profile: Created")
            if result['profile_url']:
                print(f"   🔗 URL: {result['profile_url']}")
            else:
                print(f"   ⚠️  No slug/URL")
        else:
            print(f"   ❌ Profile: NOT CREATED")
        
        if result['has_calls']:
            print(f"   📞 Calls: {result['total_calls']} call(s)")
        else:
            print(f"   ⚠️  No call history")
        
        if result['profile_link_sent']:
            link_data = result['profile_link_data']
            sent_at = link_data.get('sent_at', 0)
            if sent_at:
                sent_date = datetime.fromtimestamp(sent_at).strftime("%Y-%m-%d %H:%M:%S")
                print(f"   📱 Profile Link Sent: {sent_date}")
                if link_data.get('used_template'):
                    print(f"   ✅ Sent via template")
                else:
                    print(f"   📝 Sent via text")
        else:
            print(f"   ⚠️  Profile link NOT sent")
        
        if result['created_at']:
            created_date = datetime.fromtimestamp(result['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            print(f"   📅 Created: {created_date}")


def export_profile_links(results: List[Dict], output_file: str = "job_seeker_profiles.csv"):
    """Export profile links to CSV."""
    import csv
    
    print(f"\n💾 Exporting profile links to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name', 'uid', 'phone', 'resume_phone', 'profile_url', 
            'has_profile', 'total_calls', 'profile_link_sent', 'created_at'
        ])
        writer.writeheader()
        
        for result in results:
            created_str = ""
            if result['created_at']:
                created_str = datetime.fromtimestamp(result['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            
            writer.writerow({
                'name': result['name'],
                'uid': result['uid'],
                'phone': result['phone'],
                'resume_phone': result['resume_phone'] or '',
                'profile_url': result['profile_url'] or '',
                'has_profile': 'Yes' if result['has_profile'] else 'No',
                'total_calls': result['total_calls'],
                'profile_link_sent': 'Yes' if result['profile_link_sent'] else 'No',
                'created_at': created_str,
            })
    
    print(f"   ✅ Exported {len(results)} records")


def main():
    print("=" * 80)
    print("🔍 JOB SEEKER ANALYSIS - OUTBOUND CALLS")
    print("=" * 80)
    
    # Get all job seekers
    job_seekers = get_all_job_seekers()
    
    if not job_seekers:
        print("\n❌ No job seekers found")
        return
    
    # Check profiles
    results = check_profiles(job_seekers)
    
    # Print summary
    stats = print_summary(results)
    
    # Print detailed list
    print_detailed_list(results)
    
    # Export to CSV
    export_profile_links(results)
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete")
    print("=" * 80)
    
    # Print profile URLs only
    print("\n🔗 PROFILE LINKS:")
    print("-" * 80)
    profile_urls = [r['profile_url'] for r in results if r['profile_url']]
    for url in profile_urls:
        print(url)
    
    if not profile_urls:
        print("No profile URLs found")


if __name__ == "__main__":
    main()

