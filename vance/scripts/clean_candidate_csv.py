#!/usr/bin/env python3
"""
Clean and filter the candidate CSV to remove non-resume entries and improve data quality.
"""

import csv
import re
from pathlib import Path


def is_valid_resume(name: str, brief: str, file: str) -> bool:
    """Check if this looks like a valid resume."""
    if not name or name.strip() == "":
        return False
    
    # Filter out obvious non-resume entries
    invalid_names = [
        "the next",
        "employment contract",
        "linkedin",
        "professional summary",
        "adobe scan",
        "vance",
        "deck",
        "offer letter",
        "candidate flow",
    ]
    
    name_lower = name.lower()
    for invalid in invalid_names:
        if invalid in name_lower:
            return False
    
    # Filter out files that are clearly not resumes
    invalid_files = [
        "offer",
        "contract",
        "scan",
        "deck",
        "flow",
        "merged",
    ]
    
    file_lower = file.lower()
    for invalid in invalid_files:
        if invalid in file_lower and "resume" not in file_lower:
            return False
    
    return True


def clean_name(name: str) -> str:
    """Clean up candidate name."""
    if not name:
        return ""
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^(mr|mrs|ms|dr|prof)\.?\s+', '', name, flags=re.IGNORECASE)
    name = name.strip()
    
    # If name has newlines, take first line
    if '\n' in name:
        name = name.split('\n')[0].strip()
    
    return name


def clean_brief(brief: str) -> str:
    """Clean up brief text."""
    if not brief:
        return ""
    
    # Remove newlines and extra spaces
    brief = re.sub(r'\s+', ' ', brief)
    brief = brief.strip()
    
    # Limit length
    if len(brief) > 300:
        brief = brief[:300] + "..."
    
    return brief


def main():
    input_csv = Path(__file__).parent / "candidate_details.csv"
    output_csv = Path(__file__).parent / "candidate_details_cleaned.csv"
    
    if not input_csv.exists():
        print(f"❌ Input file not found: {input_csv}")
        return
    
    candidates = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = clean_name(row.get('name', ''))
            phone = row.get('phone', '').strip()
            linkedin = row.get('linkedin', '').strip()
            brief = clean_brief(row.get('brief', ''))
            file = row.get('file', '')
            
            # Only include valid resumes
            if is_valid_resume(name, brief, file):
                candidates.append({
                    'name': name,
                    'phone': phone,
                    'linkedin': linkedin,
                    'brief': brief,
                    'file': file,
                })
    
    # Write cleaned CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'phone', 'linkedin', 'brief', 'file'])
        writer.writeheader()
        writer.writerows(candidates)
    
    print(f"✅ Cleaned CSV generated")
    print(f"📊 Original entries: {sum(1 for _ in open(input_csv)) - 1}")
    print(f"📊 Valid candidates: {len(candidates)}")
    print(f"💾 Saved to: {output_csv}")
    
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


if __name__ == "__main__":
    main()

