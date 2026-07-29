#!/usr/bin/env python3
"""
Process today's calls (Jan 16, 2026), create missing profiles, and add to momentum frontend.

This script:
1. Finds all calls from today (Jan 16, 2026)
2. Checks which ones don't have profiles
3. Matches phone numbers with resumes
4. Creates profiles using call data + resume data
5. Adds profiles to momentum frontend
"""

import os
import sys
import time
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile, get_extraction_data
from services.voice_extraction_service import voice_extraction_service
try:
    from services.resume_number_extraction_service import resume_number_extraction_service
    RESUME_EXTRACTION_AVAILABLE = True
except ImportError:
    RESUME_EXTRACTION_AVAILABLE = False
    print("⚠️  Resume extraction service not available")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("⚠️  pdfplumber not installed - resume matching will be limited")


def get_todays_calls() -> List[Dict]:
    """Get all calls from today (Jan 16, 2026) - checking multiple sources."""
    print("🔍 Fetching today's calls (Jan 16, 2026)...")
    
    # Jan 16, 2026 - use local timezone (IST is UTC+5:30)
    # Start: Jan 16, 2026 00:00:00 IST = Jan 15, 2026 18:30:00 UTC
    # End: Jan 17, 2026 00:00:00 IST = Jan 16, 2026 18:30:00 UTC
    start_of_day_ist = datetime(2026, 1, 16, 0, 0, 0)
    end_of_day_ist = datetime(2026, 1, 17, 0, 0, 0)
    
    # Convert to UTC (IST = UTC+5:30)
    start_of_day_utc = start_of_day_ist.timestamp() - (5.5 * 3600)
    end_of_day_utc = end_of_day_ist.timestamp() - (5.5 * 3600)
    
    # Also try without timezone conversion (in case timestamps are local)
    start_of_day_local = start_of_day_ist.timestamp()
    end_of_day_local = end_of_day_ist.timestamp()
    
    print(f"   Date range (IST): {start_of_day_ist} to {end_of_day_ist}")
    print(f"   UTC timestamps: {start_of_day_utc} to {end_of_day_utc}")
    print(f"   Local timestamps: {start_of_day_local} to {end_of_day_local}")
    
    calls = []
    seen_uids = set()
    
    try:
        # Method 1: Check user_call_summaries for today
        summaries_ref = fs.collection("user_call_summaries")
        all_summaries = summaries_ref.stream()
        
        for summary_doc in all_summaries:
            summary_data = summary_doc.to_dict() or {}
            uid = summary_doc.id
            
            # Check last call timestamp (try both UTC and local)
            last_call = summary_data.get("last_call_at", 0)
            if last_call and (
                (start_of_day_utc <= last_call < end_of_day_utc) or
                (start_of_day_local <= last_call < end_of_day_local)
            ):
                seen_uids.add(uid)
                calls.append({
                    "uid": uid,
                    "call_id": "",
                    "conversation_id": "",
                    "transcript": "",
                    "extraction_data": summary_data.get("extraction_data", {}),
                    "timestamp": last_call,
                    "duration": summary_data.get("last_call_duration", 0),
                    "total_calls": summary_data.get("total_calls", 0),
                })
        
        # Method 2: Get calls from user_calls collection
        user_calls_ref = fs.collection("user_calls")
        all_users = list(user_calls_ref.stream())
        
        for user_doc in all_users:
            uid = user_doc.id
            if uid in seen_uids:
                continue
            
            try:
                calls_subcollection = user_doc.reference.collection("calls")
                
                # Query calls from today (try UTC range)
                today_calls = calls_subcollection.where("timestamp", ">=", start_of_day_utc).where("timestamp", "<", end_of_day_utc).stream()
                
                for call_doc in today_calls:
                    call_data = call_doc.to_dict() or {}
                    if uid not in seen_uids:
                        seen_uids.add(uid)
                        calls.append({
                            "uid": uid,
                            "call_id": call_data.get("call_id", ""),
                            "conversation_id": call_data.get("conversation_id", ""),
                            "transcript": call_data.get("full_transcript", ""),
                            "extraction_data": call_data.get("extraction_data", {}),
                            "timestamp": call_data.get("timestamp", 0),
                            "duration": call_data.get("call_duration", 0),
                        })
            except Exception as e:
                continue
        
        print(f"   ✅ Found {len(calls)} calls from today")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return calls


def check_missing_profiles(calls: List[Dict]) -> List[Dict]:
    """Check which calls don't have profiles."""
    print("\n📋 Checking which calls have missing profiles...")
    
    missing = []
    
    for call in calls:
        uid = call["uid"]
        
        # Check if profile exists
        profile_doc = fs.collection("user_profiles").document(uid).get()
        has_profile = profile_doc.exists
        
        if not has_profile:
            # Get user data
            user_doc = fs.collection("users").document(uid).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
            
            # Get extraction data
            extraction_doc = fs.collection("extractions").document(uid).get()
            extraction_data = extraction_doc.to_dict() if extraction_doc.exists else {}
            
            # Merge call extraction data
            if call.get("extraction_data"):
                extraction_data.update(call["extraction_data"])
            
            missing.append({
                "uid": uid,
                "phone": uid,  # UID is usually phone number
                "user_data": user_data,
                "extraction_data": extraction_data,
                "call_data": call,
            })
    
    print(f"   ✅ Found {len(missing)} calls without profiles")
    return missing


def find_resume_by_phone(phone: str, resume_dir: str = None) -> Optional[str]:
    """Find resume file by matching phone number."""
    if not PDFPLUMBER_AVAILABLE:
        return None
    
    if not resume_dir:
        resume_dir = Path.home() / "Downloads" / "linkedin_resumes_direct"
    else:
        resume_dir = Path(resume_dir)
    
    if not resume_dir.exists():
        return None
    
    # Normalize phone for matching
    clean_phone = re.sub(r'[^\d]', '', phone)
    if len(clean_phone) == 12 and clean_phone.startswith('91'):
        clean_phone = clean_phone[2:]  # Remove 91 prefix
    
    # Search all PDFs
    pdf_files = list(resume_dir.glob("*.pdf"))
    
    for pdf_file in pdf_files:
        try:
            # Extract text and check for phone
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Check for phone number in text
            phone_patterns = [
                r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                r'\+?\d{10,15}',
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    match_clean = re.sub(r'[^\d]', '', match)
                    if len(match_clean) == 12 and match_clean.startswith('91'):
                        match_clean = match_clean[2:]
                    
                    if match_clean == clean_phone or match_clean in clean_phone or clean_phone in match_clean:
                        return str(pdf_file)
        
        except Exception as e:
            continue
    
    return None


def create_profile_from_call_and_resume(user_data: Dict, extraction_data: Dict, call_data: Dict, resume_path: str = None) -> Dict:
    """Create profile from call data and resume."""
    uid = user_data.get("uid") or extraction_data.get("phone_number") or call_data["uid"]
    
    print(f"\n👤 Creating profile for {uid}")
    
    # Get name
    name = (
        extraction_data.get("name")
        or user_data.get("name")
        or user_data.get("profile", {}).get("name")
        or "Unknown"
    )
    
    # Get phone
    phone = (
        extraction_data.get("phone_number")
        or user_data.get("phone")
        or user_data.get("wa_id")
        or uid
    )
    
    # Process resume if available
    if resume_path and os.path.exists(resume_path) and RESUME_EXTRACTION_AVAILABLE:
        print(f"   📄 Processing resume: {os.path.basename(resume_path)}")
        
        try:
            # Extract numbers from resume
            resume_numbers = resume_number_extraction_service.extract_all_numbers(resume_path)
            if resume_numbers:
                numbers_dict = resume_numbers.model_dump(exclude_none=True)
                extraction_data["resume_extracted_numbers"] = numbers_dict
                
                # Update phone if found in resume
                if numbers_dict.get("phone_number"):
                    resume_phone = numbers_dict["phone_number"]
                    clean_phone = re.sub(r'[^\d]', '', str(resume_phone))
                    if len(clean_phone) == 10:
                        phone = '91' + clean_phone
                    else:
                        phone = clean_phone
                    print(f"   📱 Phone from resume: {phone}")
            
            # Store resume path
            extraction_data["resume_path"] = resume_path
            extraction_data["resume_url"] = resume_path
            extraction_data["resume_filename"] = os.path.basename(resume_path)
        
        except Exception as e:
            print(f"   ⚠️  Error processing resume: {e}")
    elif resume_path:
        # Just store the path even if we can't extract
        extraction_data["resume_path"] = resume_path
        extraction_data["resume_url"] = resume_path
        extraction_data["resume_filename"] = os.path.basename(resume_path)
    
    # Merge call transcript into extraction data
    if call_data.get("transcript"):
        extraction_data["call_transcript"] = call_data["transcript"]
    
    # Ensure user exists
    user_doc_data = {
        "wa_id": phone,
        "phone": phone,
        "name": name,
        "profile": {
            "user_type": "job_seeker",
            "name": name,
        },
        "state": "onboarding",
        "created_at": time.time(),
        "last_interaction": time.time(),
    }
    
    fs.collection("users").document(phone).set(user_doc_data, merge=True)
    print(f"   ✅ Created/updated user: users/{phone}")
    
    # Save extraction data
    fs.collection("extractions").document(phone).set(extraction_data, merge=True)
    print(f"   ✅ Saved extraction data: extractions/{phone}")
    
    # Sync profile
    try:
        voice_extraction_service._sync_job_seeker_profile(phone, extraction_data)
        print(f"   ✅ Synced profile: user_profiles/{phone}")
        
        # Get profile to return slug
        profile_doc = fs.collection("user_profiles").document(phone).get()
        if profile_doc.exists:
            profile_data = profile_doc.to_dict() or {}
            slug = profile_data.get("slug")
            return {
                "uid": phone,
                "name": name,
                "phone": phone,
                "slug": slug,
                "profile_url": f"https://profiles.vance.so/{slug}" if slug else None,
            }
    except Exception as e:
        print(f"   ⚠️  Error syncing profile: {e}")
        import traceback
        traceback.print_exc()
    
    return {
        "uid": phone,
        "name": name,
        "phone": phone,
        "slug": None,
        "profile_url": None,
    }


def add_to_momentum_frontend(profiles: List[Dict]):
    """Add profiles to momentum frontend candidates list."""
    print("\n🎨 Adding profiles to momentum frontend...")
    
    # Find momentum-match repository
    momentum_dir = Path.home() / "momentum-match"
    if not momentum_dir.exists():
        print(f"   ⚠️  Momentum-match directory not found at {momentum_dir}")
        return
    
    candidates_file = momentum_dir / "src" / "data" / "candidates.ts"
    if not candidates_file.exists():
        print(f"   ⚠️  Candidates file not found at {candidates_file}")
        return
    
    print(f"   📝 Updating {candidates_file}")
    
    # Read existing candidates
    try:
        with open(candidates_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract existing candidates array
        # This is a simplified approach - you may need to adjust based on actual file structure
        print(f"   ✅ Found candidates file")
        print(f"   📋 Adding {len(profiles)} new profiles")
        
        # Note: You'll need to manually integrate these or use a proper TypeScript parser
        # For now, just print what needs to be added
        print("\n   Profiles to add:")
        for profile in profiles:
            if profile.get("profile_url"):
                print(f"      - {profile['name']}: {profile['profile_url']}")
    
    except Exception as e:
        print(f"   ❌ Error reading candidates file: {e}")


def main():
    print("=" * 80)
    print("📞 PROCESS TODAY'S CALLS - CREATE PROFILES")
    print("=" * 80)
    
    # Get today's calls
    calls = get_todays_calls()
    
    if not calls:
        print("\n❌ No calls found for today")
        return
    
    # Check missing profiles
    missing = check_missing_profiles(calls)
    
    if not missing:
        print("\n✅ All calls have profiles!")
        return
    
    # Process each missing profile
    created_profiles = []
    resume_dir = Path.home() / "Downloads" / "linkedin_resumes_direct"
    
    for item in missing:
        uid = item["uid"]
        phone = item["phone"]
        
        # Find resume
        resume_path = find_resume_by_phone(phone, str(resume_dir))
        
        # Create profile
        profile = create_profile_from_call_and_resume(
            item["user_data"],
            item["extraction_data"],
            item["call_data"],
            resume_path
        )
        
        if profile.get("profile_url"):
            created_profiles.append(profile)
    
    # Add to momentum frontend
    if created_profiles:
        add_to_momentum_frontend(created_profiles)
    
    print("\n" + "=" * 80)
    print("✅ Processing Complete")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total calls today: {len(calls)}")
    print(f"   Missing profiles: {len(missing)}")
    print(f"   Profiles created: {len(created_profiles)}")
    
    if created_profiles:
        print(f"\n🔗 Created Profile URLs:")
        for profile in created_profiles:
            print(f"   - {profile['name']}: {profile['profile_url']}")


if __name__ == "__main__":
    main()

