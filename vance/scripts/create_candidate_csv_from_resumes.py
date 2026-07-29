#!/usr/bin/env python3
"""
Create CSV from downloaded resumes with phone, name, and brief.

Phone numbers: If 10 digits, adds 91 prefix.

Usage:
    python3 scripts/create_candidate_csv_from_resumes.py ~/Downloads/linkedin_resumes_direct
    python3 scripts/create_candidate_csv_from_resumes.py ~/Downloads/linkedin_resumes_direct --output candidates.csv
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path

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
            # If 10 digits, add 91 prefix
            if len(phone) == 10 and phone.isdigit():
                phone = '91' + phone
            elif 10 <= len(phone) <= 15:
                return phone
    return None


def extract_brief(text: str) -> str:
    """Extract brief/about section from resume."""
    # Look for common section headers
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
    
    # Fallback: take first few sentences
    sentences = re.split(r'[.!?]\s+', text[:500])
    if len(sentences) >= 2:
        brief = '. '.join(sentences[:2]) + '.'
        if len(brief) > 200:
            brief = brief[:200] + "..."
        return brief
    
    return None


def process_resume(pdf_path: Path) -> dict:
    """Process a single resume PDF."""
    text = extract_text_from_pdf(str(pdf_path))
    if not text:
        return None
    
    return {
        "name": extract_name(text),
        "phone": extract_phone_number(text),
        "brief": extract_brief(text),
        "file": pdf_path.name,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create CSV from resume PDFs"
    )
    parser.add_argument(
        "resume_dir",
        help="Directory containing resume PDFs",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="candidates.csv",
        help="Output CSV file (default: candidates.csv)",
    )
    
    args = parser.parse_args()
    
    resume_dir = Path(args.resume_dir)
    if not resume_dir.exists() or not resume_dir.is_dir():
        print(f"❌ Directory not found: {resume_dir}")
        sys.exit(1)
    
    # Find all PDF files
    pdf_files = list(resume_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {resume_dir}")
        sys.exit(1)
    
    print(f"📁 Found {len(pdf_files)} PDF file(s)")
    print("=" * 70)
    
    candidates = []
    
    for pdf_file in pdf_files:
        print(f"📄 Processing: {pdf_file.name}")
        result = process_resume(pdf_file)
        
        if result:
            candidates.append(result)
            print(f"   ✅ Name: {result['name'] or 'Not found'}")
            print(f"   ✅ Phone: {result['phone'] or 'Not found'}")
        else:
            print(f"   ⚠️  Could not extract data")
    
    # Write CSV
    output_path = Path(args.output)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'phone', 'brief', 'file'])
        writer.writeheader()
        writer.writerows(candidates)
    
    print("\n" + "=" * 70)
    print(f"✅ Generated CSV with {len(candidates)} candidates")
    print(f"💾 Saved to: {output_path}")
    
    # Summary
    with_names = sum(1 for c in candidates if c['name'])
    with_phones = sum(1 for c in candidates if c['phone'])
    with_brief = sum(1 for c in candidates if c['brief'])
    
    print(f"\n📊 Summary:")
    print(f"   Candidates with names: {with_names}/{len(candidates)}")
    print(f"   Candidates with phones: {with_phones}/{len(candidates)}")
    print(f"   Candidates with brief: {with_brief}/{len(candidates)}")


if __name__ == "__main__":
    main()

