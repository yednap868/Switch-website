#!/usr/bin/env python3
"""
Script to extract numbers from locally stored resume PDFs.

Usage:
    # Extract from a single PDF
    python3 scripts/extract_numbers_from_local_pdfs.py /path/to/resume.pdf

    # Extract from all PDFs in a directory
    python3 scripts/extract_numbers_from_local_pdfs.py /path/to/resumes/

    # Extract from a directory and save results to JSON
    python3 scripts/extract_numbers_from_local_pdfs.py /path/to/resumes/ --output results.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.resume_number_extraction_service import (
    resume_number_extraction_service,
)


def extract_from_file(pdf_path: str) -> dict:
    """Extract numbers from a single PDF file."""
    print(f"\n📄 Processing: {pdf_path}")
    print("-" * 70)

    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return None

    if not pdf_path.lower().endswith('.pdf'):
        print(f"⚠️  Not a PDF file: {pdf_path}")
        return None

    extracted = resume_number_extraction_service.extract_all_numbers(pdf_path)

    if not extracted:
        print("❌ Failed to extract numbers")
        return None

    result = {
        "file": pdf_path,
        "extracted": extracted.model_dump(exclude_none=True),
    }

    print("✅ Extracted Numbers:")
    print(f"   Phone Number: {extracted.phone_number or 'Not found'}")
    print(f"   Years of Experience: {extracted.years_of_experience or 'Not found'}")
    print(f"   Salary Expectation: {extracted.salary_expectation or 'Not found'}")
    print(f"   Years at Companies: {extracted.years_at_companies or 'Not found'}")
    print(f"   Number of Companies: {extracted.number_of_companies or 'Not found'}")
    print(f"   Number of Projects: {extracted.number_of_projects or 'Not found'}")
    print(f"   Graduation Year: {extracted.graduation_year or 'Not found'}")

    return result


def extract_from_directory(directory: str) -> list:
    """Extract numbers from all PDFs in a directory."""
    pdf_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"❌ No PDF files found in {directory}")
        return []

    print(f"📁 Found {len(pdf_files)} PDF file(s)")
    print("=" * 70)

    results = []
    for pdf_file in pdf_files:
        result = extract_from_file(pdf_file)
        if result:
            results.append(result)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Extract numbers from local resume PDFs"
    )
    parser.add_argument(
        "path",
        help="Path to a PDF file or directory containing PDFs",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file to save results",
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"❌ Path does not exist: {args.path}")
        sys.exit(1)

    results = []

    if path.is_file():
        # Single file
        result = extract_from_file(str(path))
        if result:
            results.append(result)
    elif path.is_dir():
        # Directory
        results = extract_from_directory(str(path))
    else:
        print(f"❌ Invalid path: {args.path}")
        sys.exit(1)

    # Print summary
    print("\n" + "=" * 70)
    print(f"✅ Processed {len(results)} resume(s) successfully")
    print("=" * 70)

    # Save to JSON if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to: {args.output}")

    # Print summary statistics
    if results:
        print("\n📊 Summary Statistics:")
        print("-" * 70)
        phones_found = sum(1 for r in results if r['extracted'].get('phone_number'))
        experience_found = sum(1 for r in results if r['extracted'].get('years_of_experience'))
        salary_found = sum(1 for r in results if r['extracted'].get('salary_expectation'))
        
        print(f"   Resumes with phone numbers: {phones_found}/{len(results)}")
        print(f"   Resumes with experience: {experience_found}/{len(results)}")
        print(f"   Resumes with salary: {salary_found}/{len(results)}")


if __name__ == "__main__":
    main()

