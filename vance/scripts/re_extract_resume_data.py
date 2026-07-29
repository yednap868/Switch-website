#!/usr/bin/env python3
"""
Re-extract resume data for a user if extraction was incomplete.

Usage:
    python3 scripts/re_extract_resume_data.py 918368828660 [resume_path]
"""

import sys
import os
import re
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except ImportError:
        print("❌ pdfplumber not installed. Install with: pip install pdfplumber")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️  Error reading PDF: {e}")
        return ""


def extract_name(text: str) -> str:
    """Extract candidate name from resume text."""
    # Try first 20 lines
    lines = text.split('\n')[:20]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # Skip common headers
        if any(skip in line.lower() for skip in ['resume', 'cv', 'curriculum', 'vitae', 'phone', 'email', 'linkedin', 'github', 'portfolio', 'objective', 'summary', 'experience', 'education', 'skills']):
            continue
        
        # Check if line looks like a name (2-4 words, capitalized)
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(word[0].isupper() if word else False for word in words):
                if not line.isupper() or len(line) < 15:
                    if not any(word.lower() in ['software', 'engineer', 'developer', 'manager', 'analyst', 'designer'] for word in words):
                        return line
    
    # Fallback: try to find name patterns
    name_patterns = [
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*$',
        r'Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text[:500], re.MULTILINE)
        if match:
            return match.group(1).strip()
    
    return None


def extract_phone_number(text: str) -> str:
    """Extract phone number from text."""
    # Indian phone patterns: +91, 91, or 10-digit numbers
    patterns = [
        r'\+?91[\s-]?[6-9]\d{9}',  # +91 or 91 prefix
        r'[6-9]\d{9}',  # 10-digit starting with 6-9
        r'\(\d{3}\)\s?\d{3}[\s-]?\d{4}',  # US format
        r'\d{3}[\s.-]?\d{3}[\s.-]?\d{4}',  # Generic 10-digit
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Clean and format
            phone = re.sub(r'[^\d]', '', matches[0])
            if len(phone) == 10:
                return '91' + phone
            elif len(phone) == 12 and phone.startswith('91'):
                return phone
            return phone
    
    return None


def extract_email(text: str) -> str:
    """Extract email from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    if matches:
        return matches[0]
    return None


def extract_linkedin(text: str) -> str:
    """Extract LinkedIn URL from text."""
    linkedin_pattern = r'linkedin\.com/in/[\w-]+'
    matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
    if matches:
        return f"https://www.{matches[0]}"
    return None


def re_extract_resume_data(user_id: str, resume_path: str = None):
    """
    Re-extract resume data for a user.
    
    Args:
        user_id: User ID to extract data for
        resume_path: Optional path to resume file. If not provided, tries to find from Firestore.
    """
    print(f"\n{'='*80}")
    print(f"Re-extracting Resume Data for UID: {user_id}")
    print(f"{'='*80}\n")
    
    # If resume_path not provided, try to get from Firestore
    if not resume_path:
        extraction_ref = fs.collection("extractions").document(user_id).get()
        if extraction_ref.exists:
            extraction_data = extraction_ref.to_dict() or {}
            resume_path = extraction_data.get("resume_path") or extraction_data.get("resume_url")
            print(f"📋 Found resume path in Firestore: {resume_path}")
        else:
            print("❌ No extraction data found. Please provide resume_path.")
            return
    
    # Check if file exists
    if not os.path.exists(resume_path):
        print(f"❌ Resume file not found: {resume_path}")
        print(f"   Trying to find resume file...")
        
        # Try to find by filename
        filename = os.path.basename(resume_path)
        possible_paths = [
            os.path.join(os.path.expanduser("~"), "Vance-1", "storage", "resumes", filename),
            os.path.join(os.path.expanduser("~"), "Vance-1", "uploads", filename),
            os.path.join("/tmp", filename),
            os.path.join("/tmp/resumes", filename),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                resume_path = path
                print(f"✅ Found resume at: {resume_path}")
                break
        else:
            print(f"❌ Could not find resume file. Please provide the correct path.")
            return
    
    print(f"📄 Processing resume: {resume_path}")
    print(f"   File size: {os.path.getsize(resume_path) / 1024:.1f} KB\n")
    
    # Extract text
    print("📖 Extracting text from PDF...")
    resume_text = extract_text_from_pdf(resume_path)
    
    if not resume_text:
        print("❌ Could not extract text from PDF")
        return
    
    print(f"✅ Extracted {len(resume_text)} characters of text\n")
    
    # Extract fields
    print("🔍 Extracting candidate information...")
    name = extract_name(resume_text)
    email = extract_email(resume_text)
    phone = extract_phone_number(resume_text)
    linkedin_url = extract_linkedin(resume_text)
    
    print(f"   Name: {name or 'Not found'}")
    print(f"   Email: {email or 'Not found'}")
    print(f"   Phone: {phone or 'Not found'}")
    print(f"   LinkedIn: {linkedin_url or 'Not found'}\n")
    
    # Build extraction data
    extraction_data = {
        "name": name,
        "email": email,
        "phone_number": phone,
        "linkedin_url": linkedin_url,
        "resume_path": resume_path,
        "resume_filename": os.path.basename(resume_path),
        "resume_text": resume_text,
        "resume_uploaded_at": time.time(),
        "re_extracted_at": time.time(),
    }
    
    # Try to extract numbers using resume_number_extraction_service if available
    try:
        from services.resume_number_extraction_service import resume_number_extraction_service
        extracted_numbers = resume_number_extraction_service.extract_all_numbers(resume_path)
        if extracted_numbers:
            numbers_dict = extracted_numbers.model_dump(exclude_none=True)
            extraction_data["resume_extracted_numbers"] = numbers_dict
            if numbers_dict.get("phone_number") and not phone:
                extraction_data["phone_number"] = numbers_dict["phone_number"]
                print(f"   Phone (from numbers service): {extraction_data['phone_number']}")
    except ImportError:
        print("   ⚠️  resume_number_extraction_service not available - skipping number extraction")
    except Exception as e:
        print(f"   ⚠️  Error extracting numbers: {e}")
    
    # Update Firestore
    print(f"\n💾 Updating Firestore...")
    fs.collection("extractions").document(user_id).set(extraction_data, merge=True)
    print(f"   ✅ Updated extractions/{user_id}")
    
    # Update user profile
    try:
        from services.voice_extraction_service import voice_extraction_service
        voice_extraction_service._sync_job_seeker_profile(user_id, extraction_data)
        print(f"   ✅ Synced user_profiles/{user_id}")
    except ImportError:
        print("   ⚠️  voice_extraction_service not available - profile sync skipped")
    except Exception as e:
        print(f"   ⚠️  Error syncing profile: {e}")
    
    # Update users collection
    if name:
        fs.collection("users").document(user_id).update({
            "name": name,
            "profile.name": name,
            "updated_at": time.time(),
        })
        print(f"   ✅ Updated users/{user_id}")
    
    print(f"\n{'='*80}")
    print(f"✅ Resume data extraction complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/re_extract_resume_data.py <user_id> [resume_path]")
        sys.exit(1)
    
    user_id = sys.argv[1]
    resume_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    re_extract_resume_data(user_id, resume_path)

