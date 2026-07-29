#!/usr/bin/env python3
"""
Simple script to extract numbers from local PDF resumes.
Doesn't require full service dependencies.
"""

import argparse
import json
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
        print(f"❌ Error reading PDF: {e}")
    return text


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


def extract_years_of_experience(text: str) -> float:
    """Extract total years of experience."""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)\s*(?:of\s*)?(?:experience|exp)',
        r'(?:experience|exp)[:\s]+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:in|of)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                years = float(matches[0])
                if 0 <= years <= 50:
                    return years
            except ValueError:
                continue
    return None


def extract_salary_expectation(text: str) -> str:
    """Extract salary expectation from text."""
    patterns = [
        r'(?:salary|compensation|expected|expecting|CTC|LPA)[:\s]*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand|lakh|lakhs|L|cr|crore)?',
        r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K|thousand|lakh|lakhs|L|cr|crore)?\s*(?:salary|compensation|expected|expecting|CTC|LPA)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
    return None


def extract_all_numbers(pdf_path: str) -> dict:
    """Extract all numbers from a PDF."""
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None

    return {
        "phone_number": extract_phone_number(text),
        "years_of_experience": extract_years_of_experience(text),
        "salary_expectation": extract_salary_expectation(text),
        "text_preview": text[:500] + "..." if len(text) > 500 else text,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract numbers from local resume PDFs")
    parser.add_argument("path", help="Path to PDF file or directory")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"❌ Path does not exist: {args.path}")
        sys.exit(1)

    results = []

    if path.is_file():
        print(f"📄 Processing: {path}")
        result = extract_all_numbers(str(path))
        if result:
            result["file"] = str(path)
            results.append(result)
            print(f"✅ Phone: {result['phone_number'] or 'Not found'}")
            print(f"✅ Experience: {result['years_of_experience'] or 'Not found'} years")
            print(f"✅ Salary: {result['salary_expectation'] or 'Not found'}")
    elif path.is_dir():
        pdf_files = list(path.glob("*.pdf"))
        print(f"📁 Found {len(pdf_files)} PDF file(s)")
        for pdf_file in pdf_files:
            print(f"\n📄 Processing: {pdf_file.name}")
            result = extract_all_numbers(str(pdf_file))
            if result:
                result["file"] = str(pdf_file)
                results.append(result)
                print(f"   Phone: {result['phone_number'] or 'Not found'}")
                print(f"   Experience: {result['years_of_experience'] or 'Not found'} years")
                print(f"   Salary: {result['salary_expectation'] or 'Not found'}")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {args.output}")

    print(f"\n✅ Processed {len(results)} resume(s)")


if __name__ == "__main__":
    main()

