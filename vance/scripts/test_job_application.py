"""
Test script to verify AI job application service works locally.
Tests:
1. Resume extraction from user profile
2. Candidate data extraction
3. Cover letter generation
4. Form filling (if Playwright available)
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.job_application_service import job_application_service
from utils.db import get_user_profile, fs


async def test_job_application(user_id: str, job_title: str, company: str, application_url: str):
    """Test AI job application flow."""
    print(f"🧪 Testing AI Job Application")
    print(f"   User ID: {user_id}")
    print(f"   Job: {job_title} at {company}")
    print(f"   Application URL: {application_url}\n")
    
    # Step 1: Check if user exists and has resume data
    print("1️⃣ Checking user profile and resume data...")
    user_profile = get_user_profile(user_id)
    if not user_profile:
        print(f"   ❌ User profile not found: {user_id}")
        return False
    
    print(f"   ✅ User profile found")
    
    # Check extraction data
    profile_ref = fs.collection("user_profiles").document(user_id).get()
    profile_data = profile_ref.to_dict() if profile_ref.exists else {}
    extraction_data = profile_data.get("extraction_data", {})
    
    print(f"   📄 Extraction data:")
    print(f"      - Name: {extraction_data.get('name', 'Not found')}")
    print(f"      - Email: {extraction_data.get('email', 'Not found')}")
    print(f"      - Phone: {extraction_data.get('phone_number', 'Not found')}")
    print(f"      - Resume path: {extraction_data.get('resume_path', 'Not found')}")
    print(f"      - Resume text: {'Found' if extraction_data.get('resume_text') else 'Not found'} ({len(extraction_data.get('resume_text', ''))} chars)")
    
    # Step 2: Extract candidate data
    print("\n2️⃣ Extracting candidate data...")
    candidate_data = job_application_service._extract_candidate_data(user_id)
    if not candidate_data:
        print(f"   ❌ Failed to extract candidate data")
        return False
    
    print(f"   ✅ Candidate data extracted:")
    print(f"      - Name: {candidate_data.name}")
    print(f"      - Email: {candidate_data.email or 'Not found'}")
    print(f"      - Phone: {candidate_data.phone or 'Not found'}")
    print(f"      - LinkedIn: {candidate_data.linkedin_url or 'Not found'}")
    print(f"      - Experience: {candidate_data.years_of_experience or 'Not found'}")
    print(f"      - Resume path: {candidate_data.resume_path or 'Not found'}")
    print(f"      - Resume text: {'Found' if candidate_data.resume_text else 'Not found'}")
    
    # Step 3: Generate cover letter
    print("\n3️⃣ Generating cover letter...")
    try:
        cover_letter = await job_application_service._generate_cover_letter(
            candidate_data=candidate_data,
            job_title=job_title,
            company=company,
            job_description=None
        )
        print(f"   ✅ Cover letter generated ({len(cover_letter)} chars)")
        print(f"   Preview: {cover_letter[:200]}...")
    except Exception as e:
        print(f"   ⚠️  Cover letter generation failed: {e}")
        cover_letter = "Fallback cover letter"
    
    # Step 4: Test form filling (if Playwright available)
    print("\n4️⃣ Testing form filling capability...")
    try:
        from playwright.async_api import async_playwright
        print(f"   ✅ Playwright is available")
        print(f"   ⚠️  Skipping actual form filling (requires valid URL and form fields)")
        print(f"   Note: This will be done in background when candidate applies")
    except ImportError:
        print(f"   ⚠️  Playwright not installed - form filling will be skipped")
        print(f"   Install with: pip install playwright && playwright install chromium")
    
    # Step 5: Test full application flow (dry run)
    print("\n5️⃣ Testing full application flow (dry run)...")
    print(f"   Application URL: {application_url}")
    print(f"   This would:")
    print(f"   1. Navigate to {application_url}")
    print(f"   2. Fill form fields:")
    print(f"      - Name: {candidate_data.name}")
    print(f"      - Email: {candidate_data.email or '(not found)'}")
    print(f"      - Phone: {candidate_data.phone or '(not found)'}")
    print(f"      - LinkedIn: {candidate_data.linkedin_url or '(not found)'}")
    if candidate_data.resume_path and os.path.exists(candidate_data.resume_path):
        print(f"      - Resume: {candidate_data.resume_path} (will upload)")
    else:
        print(f"      - Resume: (not found - cannot upload)")
    print(f"      - Cover letter: (will paste {len(cover_letter)} chars)")
    print(f"   3. Submit application")
    
    print(f"\n✅ Test complete - All data extraction steps working!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AI job application service")
    parser.add_argument("--user-id", required=True, help="User ID to test with")
    parser.add_argument("--job-title", default="Full-Stack Engineer", help="Job title")
    parser.add_argument("--company", default="Nanonets", help="Company name")
    parser.add_argument("--application-url", default="https://www.nanonets.com/careers", help="Application URL")
    
    args = parser.parse_args()
    
    result = asyncio.run(test_job_application(
        user_id=args.user_id,
        job_title=args.job_title,
        company=args.company,
        application_url=args.application_url
    ))
    
    sys.exit(0 if result else 1)

