#!/usr/bin/env python3
"""
Create Firestore users from resume data and store all information including resume.

This script:
1. Reads CSV or processes resume PDFs
2. Creates user documents in Firestore
3. Stores resume data (file path or uploads to storage)
4. Creates extraction_data with resume information
5. Creates user_profiles document
6. Links everything together

Usage:
    # From CSV
    python3 scripts/create_users_from_resumes.py --csv candidate_details.csv

    # From resume directory
    python3 scripts/create_users_from_resumes.py --resume-dir ~/Downloads/linkedin_resumes_direct

    # From single resume
    python3 scripts/create_users_from_resumes.py --resume /path/to/resume.pdf --name "John Doe" --phone "919876543210"
"""

import argparse
import csv
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, save_data_merge
from services.resume_number_extraction_service import resume_number_extraction_service

try:
    import pdfplumber
except ImportError:
    print("❌ pdfplumber not installed. Install with: pip install pdfplumber")
    sys.exit(1)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"⚠️  Error reading {os.path.basename(pdf_path)}: {e}")
    return text


def extract_name(text: str) -> str:
    """Extract candidate name from resume text."""
    lines = text.split('\n')[:20]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        if any(skip in line.lower() for skip in ['resume', 'cv', 'curriculum', 'vitae', 'phone', 'email', 'linkedin', 'github', 'portfolio', 'objective', 'summary', 'experience', 'education', 'skills']):
            continue
        
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(word[0].isupper() if word else False for word in words):
                if not line.isupper() or len(line) < 15:
                    if not any(word.lower() in ['software', 'engineer', 'developer', 'manager', 'analyst', 'designer'] for word in words):
                        return line
    
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
    patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+?\d{10,15}',
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            phone = re.sub(r'[-.\s()]', '', matches[0])
            if phone.startswith('91') and len(phone) == 12:
                phone = phone[2:]
            elif phone.startswith('+91') and len(phone) == 13:
                phone = phone[3:]
            if len(phone) == 10 and phone.isdigit():
                phone = '91' + phone
            elif 10 <= len(phone) <= 15:
                return phone
    return None


def extract_email(text: str) -> str:
    """Extract email from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    if matches:
        return matches[0].lower()
    return None


def extract_linkedin(text: str) -> str:
    """Extract LinkedIn URL from text."""
    patterns = [
        r'linkedin\.com/in/[\w-]+',
        r'linkedin\.com/pub/[\w-]+',
        r'www\.linkedin\.com/in/[\w-]+',
        r'https?://(?:www\.)?linkedin\.com/in/[\w-]+',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            url = matches[0]
            if not url.startswith('http'):
                url = 'https://www.' + url
            return url
    
    return None


def extract_brief(text: str) -> str:
    """Extract brief/about section from resume."""
    brief_patterns = [
        r'(?:summary|about|profile|objective|overview)[:\s]*\n?(.{100,500})',
        r'(?:professional\s+summary|executive\s+summary)[:\s]*\n?(.{100,500})',
    ]
    
    for pattern in brief_patterns:
        match = re.search(pattern, text[:2000], re.IGNORECASE | re.DOTALL)
        if match:
            brief = match.group(1).strip()
            brief = re.sub(r'\s+', ' ', brief)
            brief = re.sub(r'\n+', ' ', brief)
            if len(brief) > 300:
                brief = brief[:300] + "..."
            return brief
    
    sentences = re.split(r'[.!?]\s+', text[:500])
    if len(sentences) >= 2:
        brief = '. '.join(sentences[:2]) + '.'
        if len(brief) > 300:
            brief = brief[:300] + "..."
        return brief
    
    return None


def generate_user_id(phone: str, email: str = None, name: str = None) -> str:
    """Generate a unique user ID from phone/email/name."""
    # Use phone as primary ID (WhatsApp format)
    if phone:
        # Clean phone: remove non-digits, ensure 91 prefix for 10 digits
        clean_phone = re.sub(r'[^\d]', '', phone)
        if len(clean_phone) == 10:
            clean_phone = '91' + clean_phone
        return clean_phone
    
    # Fallback to email hash
    if email:
        email_hash = hashlib.md5(email.encode()).hexdigest()[:12]
        return f"email_{email_hash}"
    
    # Fallback to name hash
    if name:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:12]
        return f"name_{name_hash}"
    
    # Last resort: timestamp
    return f"user_{int(time.time())}"


def store_resume_file(resume_path: str, user_id: str) -> Optional[str]:
    """Store resume file and return storage path or URL."""
    # For now, store the file path
    # In production, you might want to upload to Firebase Storage or S3
    # and return the public URL
    
    if not os.path.exists(resume_path):
        return None
    
    # Store relative path or full path
    # Option 1: Store full path (simple, but not portable)
    resume_storage_path = resume_path
    
    # Option 2: Copy to a resumes directory (better for production)
    # resumes_dir = Path.home() / "Vance-1" / "storage" / "resumes"
    # resumes_dir.mkdir(parents=True, exist_ok=True)
    # resume_filename = f"{user_id}_{os.path.basename(resume_path)}"
    # resume_dest = resumes_dir / resume_filename
    # shutil.copy2(resume_path, resume_dest)
    # resume_storage_path = str(resume_dest)
    
    return resume_storage_path


def create_user_from_resume_data(
    name: str,
    phone: str,
    email: str = None,
    linkedin: str = None,
    brief: str = None,
    resume_path: str = None,
    resume_text: str = None,
) -> Dict:
    """Create a complete user in Firestore from resume data."""
    
    # Generate user ID
    user_id = generate_user_id(phone, email, name)
    
    print(f"\n👤 Creating user: {user_id}")
    print(f"   Name: {name}")
    print(f"   Phone: {phone}")
    if email:
        print(f"   Email: {email}")
    if linkedin:
        print(f"   LinkedIn: {linkedin}")
    
    # Extract additional data from resume if available
    extraction_data = {}
    resume_numbers = None
    
    if resume_path and os.path.exists(resume_path):
        # Extract numbers from resume
        try:
            resume_numbers = resume_number_extraction_service.extract_all_numbers(resume_path)
            if resume_numbers:
                numbers_dict = resume_numbers.model_dump(exclude_none=True)
                extraction_data["resume_extracted_numbers"] = numbers_dict
                
                # Add phone if not provided
                if not phone and numbers_dict.get("phone_number"):
                    phone = numbers_dict["phone_number"]
                    # Format phone
                    clean_phone = re.sub(r'[^\d]', '', phone)
                    if len(clean_phone) == 10:
                        phone = '91' + clean_phone
                    else:
                        phone = clean_phone
                    user_id = generate_user_id(phone, email, name)
                    print(f"   📱 Phone extracted from resume: {phone}")
                    print(f"   🔄 Updated user_id: {user_id}")
        except Exception as e:
            print(f"   ⚠️  Error extracting resume numbers: {e}")
        
        # Store resume file path
        resume_storage_path = store_resume_file(resume_path, user_id)
        if resume_storage_path:
            extraction_data["resume_path"] = resume_storage_path
            extraction_data["resume_url"] = resume_storage_path  # For compatibility
            extraction_data["resume_filename"] = os.path.basename(resume_path)
    
    # Build extraction data
    if name:
        extraction_data["name"] = name
    if email:
        extraction_data["email"] = email
    if linkedin:
        extraction_data["linkedin_url"] = linkedin
    if brief:
        extraction_data["the_story"] = brief
        extraction_data["summary"] = brief
    
    # Add resume numbers to extraction_data
    if resume_numbers:
        numbers_dict = resume_numbers.model_dump(exclude_none=True)
        for key, value in numbers_dict.items():
            if key == "phone_number" and not extraction_data.get("phone_number"):
                extraction_data["phone_number"] = value
            elif key == "years_of_experience" and not extraction_data.get("work_experience"):
                extraction_data["work_experience"] = f"{value} years"
            elif key == "salary_expectation" and not extraction_data.get("salary_expectations"):
                extraction_data["salary_expectations"] = value
    
    # Create user document in Firestore
    user_data = {
        "wa_id": user_id,  # WhatsApp ID (phone number)
        "phone": phone,
        "email": email,
        "name": name,
        "profile": {
            "user_type": "job_seeker",  # Default to job seeker
            "name": name,
            "email": email,
            "linkedin_url": linkedin,
        },
        "state": "onboarding",
        "created_at": time.time(),
        "last_interaction": time.time(),
        "source": "resume_import",  # Track that this came from resume import
    }
    
    # Save to users collection
    fs.collection("users").document(user_id).set(user_data, merge=True)
    print(f"   ✅ Created user document: users/{user_id}")
    
    # Save extraction data
    fs.collection("extractions").document(user_id).set(extraction_data, merge=True)
    print(f"   ✅ Saved extraction data: extractions/{user_id}")
    
    # Create user_profiles document (for profile page)
    profile_data = {
        "name": name,
        "email": email,
        "linkedin_url": linkedin,
        "extraction_data": extraction_data,
        "intent": "job_seeker_need",
        "created_at": time.time(),
        "updated_at": time.time(),
        "source": "resume_import",
    }
    
    # Try to generate slug (will be done properly when profile is synced)
    if name:
        slug_base = re.sub(r'[^\w\s-]', '', name.lower()).strip().replace(' ', '-')
        profile_data["slug"] = slug_base
    
    fs.collection("user_profiles").document(user_id).set(profile_data, merge=True)
    print(f"   ✅ Created profile document: user_profiles/{user_id}")
    
    # Sync profile to ensure slug and complete profile structure
    try:
        from services.voice_extraction_service import voice_extraction_service
        voice_extraction_service._sync_job_seeker_profile(user_id, extraction_data)
        print(f"   ✅ Synced complete profile with slug")
    except Exception as e:
        print(f"   ⚠️  Profile sync failed (non-critical): {e}")
    
    return {
        "user_id": user_id,
        "user_data": user_data,
        "extraction_data": extraction_data,
        "profile_data": profile_data,
    }


def process_csv(csv_path: str, resume_dir: str = None):
    """Process CSV file and create users."""
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    print(f"📁 Reading CSV: {csv_path}")
    
    created_count = 0
    skipped_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '').strip()
            phone = row.get('phone', '').strip()
            brief = row.get('brief', '').strip()
            resume_file = row.get('file', '').strip()
            
            if not name or not phone:
                print(f"⚠️  Skipping row - missing name or phone")
                skipped_count += 1
                continue
            
            # Find resume file if directory provided
            resume_path = None
            if resume_dir and resume_file:
                resume_path = os.path.join(resume_dir, resume_file)
                if not os.path.exists(resume_path):
                    # Try to find by name
                    resume_path = None
                    for ext in ['.pdf', '.PDF']:
                        potential_path = os.path.join(resume_dir, resume_file.replace('%20', ' '))
                        if os.path.exists(potential_path):
                            resume_path = potential_path
                            break
            
            try:
                result = create_user_from_resume_data(
                    name=name,
                    phone=phone,
                    brief=brief,
                    resume_path=resume_path,
                )
                created_count += 1
                print(f"   ✅ User created: {result['user_id']}")
            except Exception as e:
                print(f"   ❌ Error creating user: {e}")
                import traceback
                traceback.print_exc()
                skipped_count += 1
    
    print(f"\n{'='*70}")
    print(f"✅ Created {created_count} users")
    print(f"⚠️  Skipped {skipped_count} rows")
    print(f"{'='*70}")


def process_resume_directory(resume_dir: str):
    """Process all resumes in a directory and create users."""
    resume_dir_path = Path(resume_dir)
    if not resume_dir_path.exists():
        print(f"❌ Directory not found: {resume_dir}")
        return
    
    pdf_files = list(resume_dir_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {resume_dir}")
        return
    
    print(f"📁 Found {len(pdf_files)} PDF file(s)")
    print("=" * 70)
    
    created_count = 0
    skipped_count = 0
    
    for pdf_file in pdf_files:
        print(f"\n📄 Processing: {pdf_file.name}")
        
        # Extract data from PDF
        text = extract_text_from_pdf(str(pdf_file))
        if not text:
            print(f"   ⚠️  Could not extract text")
            skipped_count += 1
            continue
        
        name = extract_name(text)
        phone = extract_phone_number(text)
        email = extract_email(text)
        linkedin = extract_linkedin(text)
        brief = extract_brief(text)
        
        if not name or not phone:
            print(f"   ⚠️  Missing name or phone - skipping")
            skipped_count += 1
            continue
        
        try:
            result = create_user_from_resume_data(
                name=name,
                phone=phone,
                email=email,
                linkedin=linkedin,
                brief=brief,
                resume_path=str(pdf_file),
                resume_text=text,
            )
            created_count += 1
            print(f"   ✅ User created: {result['user_id']}")
        except Exception as e:
            print(f"   ❌ Error creating user: {e}")
            import traceback
            traceback.print_exc()
            skipped_count += 1
    
    print(f"\n{'='*70}")
    print(f"✅ Created {created_count} users")
    print(f"⚠️  Skipped {skipped_count} resumes")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="Create Firestore users from resume data"
    )
    parser.add_argument(
        "--csv",
        help="CSV file with candidate data (name, phone, brief, file)",
    )
    parser.add_argument(
        "--resume-dir",
        help="Directory containing resume PDFs",
    )
    parser.add_argument(
        "--resume",
        help="Single resume PDF file",
    )
    parser.add_argument(
        "--name",
        help="Candidate name (required with --resume)",
    )
    parser.add_argument(
        "--phone",
        help="Phone number (required with --resume)",
    )
    parser.add_argument(
        "--email",
        help="Email address (optional)",
    )
    parser.add_argument(
        "--linkedin",
        help="LinkedIn URL (optional)",
    )
    
    args = parser.parse_args()
    
    if args.csv:
        # Process CSV
        resume_dir = args.resume_dir if args.resume_dir else None
        process_csv(args.csv, resume_dir)
    elif args.resume_dir:
        # Process directory
        process_resume_directory(args.resume_dir)
    elif args.resume:
        # Process single resume
        if not args.name or not args.phone:
            print("❌ --name and --phone are required with --resume")
            sys.exit(1)
        
        if not os.path.exists(args.resume):
            print(f"❌ Resume file not found: {args.resume}")
            sys.exit(1)
        
        result = create_user_from_resume_data(
            name=args.name,
            phone=args.phone,
            email=args.email,
            linkedin=args.linkedin,
            resume_path=args.resume,
        )
        print(f"\n✅ User created: {result['user_id']}")
    else:
        parser.print_help()
        print("\n⚠️  Please provide --csv, --resume-dir, or --resume")
        sys.exit(1)


if __name__ == "__main__":
    main()

