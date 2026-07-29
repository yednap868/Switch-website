#!/usr/bin/env python3
"""
Extract candidate details (name, phone, brief, LinkedIn) from PDFs and generate CSV.
"""

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
    # Common patterns for names at the start of resumes
    lines = text.split('\n')[:20]  # Check first 20 lines
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        # Skip common headers
        if any(skip in line.lower() for skip in ['resume', 'cv', 'curriculum', 'vitae', 'phone', 'email', 'linkedin', 'github', 'portfolio', 'objective', 'summary', 'experience', 'education', 'skills']):
            continue
        
        # Check if line looks like a name (2-4 words, capitalized, no special chars except spaces/hyphens)
        words = line.split()
        if 2 <= len(words) <= 4:
            # Check if all words start with capital letters
            if all(word[0].isupper() if word else False for word in words):
                # Check if it's not all caps (which might be a header)
                if not line.isupper() or len(line) < 15:
                    # Exclude lines that are clearly not names
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
            if 10 <= len(phone) <= 15:
                return phone
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
    # Look for common section headers
    brief_patterns = [
        r'(?:summary|about|profile|objective|overview)[:\s]*\n?(.{100,500})',
        r'(?:professional\s+summary|executive\s+summary)[:\s]*\n?(.{100,500})',
    ]
    
    for pattern in brief_patterns:
        match = re.search(pattern, text[:2000], re.IGNORECASE | re.DOTALL)
        if match:
            brief = match.group(1).strip()
            # Clean up the brief
            brief = re.sub(r'\s+', ' ', brief)  # Replace multiple spaces with single space
            brief = re.sub(r'\n+', ' ', brief)  # Replace newlines with space
            # Take first 200 characters
            if len(brief) > 200:
                brief = brief[:200] + "..."
            return brief
    
    # Fallback: take first few sentences from the beginning
    sentences = re.split(r'[.!?]\s+', text[:500])
    if len(sentences) >= 2:
        brief = '. '.join(sentences[:2]) + '.'
        if len(brief) > 200:
            brief = brief[:200] + "..."
        return brief
    
    return None


def extract_candidate_details(pdf_path: str) -> dict:
    """Extract all candidate details from a PDF."""
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None
    
    return {
        "name": extract_name(text),
        "phone": extract_phone_number(text),
        "linkedin": extract_linkedin(text),
        "brief": extract_brief(text),
        "file": os.path.basename(pdf_path),
    }


def main():
    downloads_path = Path.home() / "Downloads"
    output_csv = Path(__file__).parent / "candidate_details.csv"
    
    print(f"📁 Scanning PDFs in: {downloads_path}")
    print("=" * 70)
    
    pdf_files = list(downloads_path.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in Downloads")
        return
    
    print(f"📄 Found {len(pdf_files)} PDF file(s)")
    print("=" * 70)
    
    candidates = []
    
    for pdf_file in pdf_files:
        print(f"📄 Processing: {pdf_file.name}")
        details = extract_candidate_details(str(pdf_file))
        
        if details:
            candidates.append(details)
            print(f"   ✅ Name: {details['name'] or 'Not found'}")
            print(f"   ✅ Phone: {details['phone'] or 'Not found'}")
            print(f"   ✅ LinkedIn: {details['linkedin'] or 'Not found'}")
        else:
            print(f"   ⚠️  Could not extract details")
    
    # Write to CSV
    if candidates:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'phone', 'linkedin', 'brief', 'file'])
            writer.writeheader()
            writer.writerows(candidates)
        
        print("\n" + "=" * 70)
        print(f"✅ Generated CSV with {len(candidates)} candidates")
        print(f"💾 Saved to: {output_csv}")
        print("=" * 70)
        
        # Print summary
        with_names = sum(1 for c in candidates if c['name'])
        with_phones = sum(1 for c in candidates if c['phone'])
        with_linkedin = sum(1 for c in candidates if c['linkedin'])
        with_brief = sum(1 for c in candidates if c['brief'])
        
        print(f"\n📊 Summary:")
        print(f"   Candidates with names: {with_names}/{len(candidates)}")
        print(f"   Candidates with phones: {with_phones}/{len(candidates)}")
        print(f"   Candidates with LinkedIn: {with_linkedin}/{len(candidates)}")
        print(f"   Candidates with brief: {with_brief}/{len(candidates)}")
    else:
        print("❌ No candidate details extracted")


if __name__ == "__main__":
    main()

