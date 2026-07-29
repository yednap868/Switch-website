#!/usr/bin/env python3
"""
Script to extract numbers from a candidate's resume PDF.

Usage:
    python3 scripts/extract_resume_numbers.py <user_id>
    python3 scripts/extract_resume_numbers.py <user_id> <resume_url>
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.resume_number_extraction_service import (
    resume_number_extraction_service,
)
from utils.db import get_user_profile


def extract_numbers_for_user(user_id: str, resume_path_or_url: str = None):
    """Extract numbers from resume for a given user (local path or URL)."""
    print(f"🔍 Extracting numbers from resume for user: {user_id}")
    print("=" * 70)

    # Get resume URL if not provided
    if not resume_path_or_url:
        profile = get_user_profile(user_id)
        if not profile:
            print(f"❌ User profile not found for {user_id}")
            return

        resume_path_or_url = (
            profile.get("resume_url")
            or profile.get("extraction_data", {}).get("resume_url")
        )

        if not resume_path_or_url:
            print(f"❌ No resume URL found for user {user_id}")
            print("   Please provide resume_path_or_url as second argument")
            return

    # Check if it's a local file or URL
    if os.path.exists(resume_path_or_url):
        print(f"📄 Resume file: {resume_path_or_url}")
    else:
        print(f"📄 Resume URL: {resume_path_or_url}")

    # Extract numbers
    extracted = resume_number_extraction_service.extract_all_numbers(resume_path_or_url)

    if not extracted:
        print("❌ Failed to extract numbers from resume")
        return

    print("\n✅ Extracted Numbers:")
    print("-" * 70)
    print(f"Phone Number: {extracted.phone_number or 'Not found'}")
    print(f"Years of Experience: {extracted.years_of_experience or 'Not found'}")
    print(f"Salary Expectation: {extracted.salary_expectation or 'Not found'}")
    print(f"Years at Companies: {extracted.years_at_companies or 'Not found'}")
    print(f"Number of Companies: {extracted.number_of_companies or 'Not found'}")
    print(f"Number of Projects: {extracted.number_of_projects or 'Not found'}")
    print(f"Graduation Year: {extracted.graduation_year or 'Not found'}")
    print("-" * 70)

    # Update profile (only if it's a URL, not a local file)
    if not os.path.exists(resume_path_or_url):
        print("\n💾 Updating user profile...")
        updated = resume_number_extraction_service.update_candidate_profile_with_numbers(
            user_id=user_id, resume_path_or_url=resume_path_or_url
        )
    else:
        print("\n💡 Local file detected - skipping profile update")
        print("   (Profile updates only work with URLs stored in Firestore)")
        updated = None

    if updated:
        print("✅ Profile updated successfully!")
    else:
        print("⚠️ Profile update failed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/extract_resume_numbers.py <user_id> [resume_path_or_url]")
        print("Example: python3 scripts/extract_resume_numbers.py 918368828660")
        print("Example: python3 scripts/extract_resume_numbers.py 918368828660 https://example.com/resume.pdf")
        print("Example: python3 scripts/extract_resume_numbers.py 918368828660 /path/to/resume.pdf")
        sys.exit(1)

    user_id = sys.argv[1]
    resume_path_or_url = sys.argv[2] if len(sys.argv) > 2 else None

    extract_numbers_for_user(user_id, resume_path_or_url)

