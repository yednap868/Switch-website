#!/usr/bin/env python3
"""
Create CSV from resumes in Downloads, removing duplicates and excluding previous candidates.

This script:
1. Reads previous CSV to get existing phone numbers
2. Processes resumes from Downloads
3. Extracts name, phone, brief
4. Removes duplicates by phone number
5. Excludes candidates from previous CSV
6. Generates fresh CSV

Usage:
    python3 scripts/create_fresh_candidate_csv.py --previous-csv candidate_details_cleaned.csv --output fresh_candidates.csv
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, Set

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
    
    # Common non-name patterns to exclude
    exclude_patterns = [
        'resume', 'cv', 'curriculum', 'vitae', 'phone', 'email', 'linkedin', 'github', 
        'portfolio', 'objective', 'summary', 'experience', 'education', 'skills',
        'software', 'engineer', 'developer', 'manager', 'analyst', 'designer',
        'programming', 'languages', 'degree', 'certificate', 'institute', 'board',
        'cgpa', 'percentage', 'year', 'university', 'college', 'delhi', 'india',
        'gurgaon', 'bangalore', 'mumbai', 'pune', 'hyderabad', 'chennai', 'kolkata',
        'address', 'location', 'contact', 'mobile', 'whatsapp'
    ]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        line_lower = line.lower()
        
        # Skip if contains excluded patterns
        if any(pattern in line_lower for pattern in exclude_patterns):
            continue
        
        # Skip if looks like an address or location
        if any(word in line_lower for word in ['street', 'road', 'avenue', 'lane', 'pin', 'pincode', 'state', 'country']):
            continue
        
        # Skip if contains numbers (likely not a name)
        if re.search(r'\d', line):
            continue
        
        # Skip if contains special characters (except spaces and hyphens)
        if re.search(r'[^\w\s-]', line):
            continue
        
        words = line.split()
        if 2 <= len(words) <= 4:
            # Check if all words start with capital letters
            if all(word[0].isupper() if word else False for word in words):
                # Skip if all caps (likely a header)
                if line.isupper() and len(line) > 15:
                    continue
                # Skip if contains common job-related words
                if any(word.lower() in ['full', 'stack', 'frontend', 'backend', 'data', 'science', 'machine', 'learning'] for word in words):
                    continue
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
    """Extract phone number from text and normalize."""
    patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+?\d{10,15}',
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            phone = re.sub(r'[-.\s()]', '', matches[0])
            # Remove country code if present
            if phone.startswith('91') and len(phone) == 12:
                phone = phone[2:]
            elif phone.startswith('+91') and len(phone) == 13:
                phone = phone[3:]
            # If 10 digits, add 91 prefix for normalization
            if len(phone) == 10 and phone.isdigit():
                normalized = '91' + phone
            elif 10 <= len(phone) <= 15:
                normalized = phone
            else:
                continue
            
            # Return both formats for comparison
            return normalized
    
    return None


def normalize_phone(phone: str) -> str:
    """Normalize phone number for comparison."""
    if not phone:
        return ""
    
    # Remove all non-digits
    clean = re.sub(r'[^\d]', '', str(phone))
    
    # Remove 91 prefix if present (for comparison)
    if clean.startswith('91') and len(clean) == 12:
        return clean[2:]  # Return 10 digits
    elif len(clean) == 10:
        return clean
    else:
        return clean


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
            if len(brief) > 200:
                brief = brief[:200] + "..."
            return brief
    
    sentences = re.split(r'[.!?]\s+', text[:500])
    if len(sentences) >= 2:
        brief = '. '.join(sentences[:2]) + '.'
        if len(brief) > 200:
            brief = brief[:200] + "..."
        return brief
    
    return None


def load_existing_phones(csv_path: str) -> Set[str]:
    """Load phone numbers from previous CSV to exclude."""
    existing_phones = set()
    
    if not csv_path or not os.path.exists(csv_path):
        print(f"ℹ️  No previous CSV provided or file not found")
        return existing_phones
    
    print(f"📋 Loading existing phone numbers from: {csv_path}")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                phone = row.get('phone', '').strip()
                if phone:
                    # Normalize for comparison
                    normalized = normalize_phone(phone)
                    if normalized:
                        existing_phones.add(normalized)
        
        print(f"   ✅ Found {len(existing_phones)} existing phone numbers to exclude")
    except Exception as e:
        print(f"   ⚠️  Error reading previous CSV: {e}")
    
    return existing_phones


def process_resume(pdf_path: Path, existing_phones: Set[str]) -> Dict:
    """Process a single resume and return candidate data."""
    text = extract_text_from_pdf(str(pdf_path))
    if not text:
        return None
    
    name = extract_name(text)
    phone = extract_phone_number(text)
    brief = extract_brief(text)
    
    if not name or not phone:
        return None
    
    # Normalize phone for duplicate checking
    normalized_phone = normalize_phone(phone)
    
    # Check if phone exists in previous CSV
    if normalized_phone in existing_phones:
        return None  # Skip this candidate
    
    # Format phone: if 10 digits, add 91 prefix
    if len(normalized_phone) == 10:
        formatted_phone = '91' + normalized_phone
    else:
        formatted_phone = phone
    
    return {
        "name": name,
        "phone": formatted_phone,
        "brief": brief or "",
        "file": pdf_path.name,
        "_normalized_phone": normalized_phone,  # For duplicate detection
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create fresh CSV from resumes, excluding previous candidates"
    )
    parser.add_argument(
        "--previous-csv",
        default="scripts/candidate_details_cleaned.csv",
        help="Previous CSV file to exclude candidates from (default: scripts/candidate_details_cleaned.csv)",
    )
    parser.add_argument(
        "--resume-dir",
        default=None,
        help="Directory containing resumes (default: ~/Downloads)",
    )
    parser.add_argument(
        "--output",
        default="fresh_candidates.csv",
        help="Output CSV file (default: fresh_candidates.csv)",
    )
    
    args = parser.parse_args()
    
    # Load existing phone numbers
    existing_phones = load_existing_phones(args.previous_csv)
    
    # Determine resume directory
    if args.resume_dir:
        resume_dir = Path(args.resume_dir)
    else:
        resume_dir = Path.home() / "Downloads"
    
    if not resume_dir.exists():
        print(f"❌ Directory not found: {resume_dir}")
        sys.exit(1)
    
    # Find all PDF files
    pdf_files = list(resume_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {resume_dir}")
        sys.exit(1)
    
    print(f"\n📁 Found {len(pdf_files)} PDF file(s) in {resume_dir}")
    print("=" * 70)
    
    # Process resumes
    candidates = []
    seen_phones = set()  # Track duplicates within this batch
    skipped_existing = 0
    skipped_duplicate = 0
    skipped_no_data = 0
    
    for pdf_file in pdf_files:
        print(f"📄 Processing: {pdf_file.name}")
        
        result = process_resume(pdf_file, existing_phones)
        
        if result is None:
            # Check why it was skipped
            text = extract_text_from_pdf(str(pdf_file))
            if text:
                name = extract_name(text)
                phone = extract_phone_number(text)
                if name and phone:
                    normalized = normalize_phone(phone)
                    if normalized in existing_phones:
                        skipped_existing += 1
                        print(f"   ⏭️  Skipped - exists in previous CSV")
                    else:
                        skipped_no_data += 1
                        print(f"   ⚠️  Skipped - missing name or phone")
                else:
                    skipped_no_data += 1
                    print(f"   ⚠️  Skipped - missing name or phone")
            else:
                skipped_no_data += 1
                print(f"   ⚠️  Skipped - could not extract text")
            continue
        
        # Check for duplicates within this batch
        normalized = result["_normalized_phone"]
        if normalized in seen_phones:
            skipped_duplicate += 1
            print(f"   ⏭️  Skipped - duplicate phone number")
            continue
        
        seen_phones.add(normalized)
        
        # Remove internal field
        del result["_normalized_phone"]
        
        candidates.append(result)
        print(f"   ✅ Name: {result['name']}, Phone: {result['phone']}")
    
    # Write CSV
    if candidates:
        output_path = Path(args.output)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'phone', 'brief', 'file'])
            writer.writeheader()
            writer.writerows(candidates)
        
        print("\n" + "=" * 70)
        print(f"✅ Generated fresh CSV with {len(candidates)} unique candidates")
        print(f"💾 Saved to: {output_path}")
        print("=" * 70)
        
        print(f"\n📊 Summary:")
        print(f"   ✅ New candidates: {len(candidates)}")
        print(f"   ⏭️  Skipped (existing): {skipped_existing}")
        print(f"   ⏭️  Skipped (duplicates): {skipped_duplicate}")
        print(f"   ⚠️  Skipped (no data): {skipped_no_data}")
        print(f"   📁 Total PDFs processed: {len(pdf_files)}")
    else:
        print("\n❌ No new candidates found (all were duplicates or in previous CSV)")


if __name__ == "__main__":
    main()

