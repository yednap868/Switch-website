"""
Test script for the hybrid matching service.

Run with environment variables:
    source env_vars.sh && python mock.py

Or just run to test syntax/imports:
    python mock.py
"""

import asyncio
import os
import sys

from services.interview_scheduling_service import notify_candidate_profile_presented
from utils.db import get_extraction_data, get_user_profile
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_env_vars():
    """Check if required environment variables are set."""
    required_vars = ["QDRANT_BASE_URL", "QDRANT_API_KEY", "ANTHROPIC_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    return missing


def test_hybrid_matching_service():
    """Test the hybrid matching service with mock job provider data."""
    print("=" * 60)
    print("Testing Hybrid Matching Service")
    print("=" * 60)

    # Test 1: With structured data (should skip LLM extraction)
    print("\n--- Test 1: Structured job provider data ---")
    job_provider_data_structured = {
        "job_title": "Senior Python Developer",
        "required_skills": "Python, AWS, Docker, FastAPI",
        "experience_level": "4-6 years",
        "office_location": "Bangalore",
        "work_model": "Hybrid",
        "role_description": "Build scalable backend services and APIs for our AI platform",
        "salary_budget": "25-35 LPA",
        "hiring_urgency": "Immediate",
    }

    # Test 2: With raw voice call extraction data (should trigger LLM extraction)
    print("\n--- Test 2: Raw voice call data (needs LLM extraction) ---")
    job_provider_data_raw = {
        "the_story": "I'm the CTO at a Series A fintech startup in Bangalore. We've raised $5M and are scaling our engineering team.",
        "current_focus": "Building out our payments infrastructure. We use Python and FastAPI for our backend, everything runs on AWS.",
        "top_priorities": "Need to hire 2 senior backend engineers in the next month. Must know Python well, experience with AWS is critical.",
        "future_vision": "Want to expand to 10 engineers by end of year. Looking for people who can grow into tech leads.",
        "urgent_needs": "Immediate hire for a Senior Python Developer. Budget is 25-35 LPA. Hybrid work model, office in Bangalore. Need someone with 4-6 years experience.",
    }

    # Use raw data to test the LLM extraction
    job_provider_data = job_provider_data_raw

    print("\n📋 Job Provider Requirements:")
    for key, value in job_provider_data.items():
        print(f"   {key}: {value}")

    print("\n" + "-" * 60)
    print("🔍 Starting hybrid matching...")
    print("-" * 60)

    try:
        from services.hybrid_matching_service import hybrid_matching_service

        # Test the matching
        matches = hybrid_matching_service.find_job_seeker_matches(
            job_provider_data=job_provider_data,
            limit=3,
            min_score=0.5,  # Lower threshold for testing
        )

        print("\n" + "=" * 60)
        print(f"✅ RESULTS: Found {len(matches)} matches")
        print("=" * 60)

        if matches:
            for i, match in enumerate(matches, 1):
                print(f"\n--- Candidate {i} ---")
                print(f"   Name: {match.name}")
                print(f"   Target Role: {match.target_role}")
                print(f"   Skills: {match.core_skills}")
                print(f"   Experience: {match.work_experience}")
                print(f"   Location: {match.current_location}")
                print(f"   Match Score: {match.match_score:.2%}")
                print(
                    f"   Match Reason: {match.match_reason[:100]}..."
                    if len(match.match_reason) > 100
                    else f"   Match Reason: {match.match_reason}"
                )
        else:
            print("\n⚠️ No matches found. This could mean:")
            print("   - No job seekers in the database with 'job_seeker_need' intent")
            print("   - The Qdrant collections are empty")
            print("   - Check the logs above for errors")

        return len(matches) >= 0  # Test passes even with 0 matches (no errors)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_search_class():
    """Test that the Search class from utils/qdrant.py works."""
    print("\n" + "=" * 60)
    print("Testing Search Class (utils/qdrant.py)")
    print("=" * 60)

    try:
        from utils.qdrant import Search

        # Test UserProfiles collection
        print("\n🔍 Testing UserProfiles collection...")
        profiles_search = Search("UserProfiles")
        results = profiles_search.query("software developer python", limit=5)
        print(f"   Found {len(results)} results in UserProfiles")

        if results:
            print(
                "   Sample result keys:", list(results[0].keys()) if results else "N/A"
            )
            # Check if intent field exists in metadata
            if results[0].get("metadata", {}).get("intent"):
                print(f"   Sample intent: {results[0]['metadata']['intent']}")
            # Check extraction_data structure
            extraction_data = results[0].get("metadata", {}).get("extraction_data", {})
            print(
                f"   extraction_data keys: {list(extraction_data.keys()) if extraction_data else 'EMPTY'}"
            )
            if extraction_data:
                print(
                    f"   Sample extraction_data: {dict(list(extraction_data.items())[:3])}"
                )

        # Test UserUrgentNeeds collection
        print("\n🔍 Testing UserUrgentNeeds collection...")
        needs_search = Search("UserUrgentNeeds")
        results = needs_search.query("hiring engineer", limit=5)
        print(f"   Found {len(results)} results in UserUrgentNeeds")

        print("\n✅ Search class is working!")
        return True

    except Exception as e:
        print(f"\n❌ Search class error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_uuid_generation():
    """Test that UUID generation works for Qdrant point IDs."""
    print("\n" + "=" * 60)
    print("Testing UUID Generation")
    print("=" * 60)

    import uuid

    test_id = uuid.uuid4().hex
    print(f"   Generated UUID: {test_id}")
    print(f"   Length: {len(test_id)}")
    print(f"   Is valid hex: {all(c in '0123456789abcdef' for c in test_id)}")

    # This is what Qdrant expects
    assert len(test_id) == 32, "UUID hex should be 32 characters"
    assert all(c in "0123456789abcdef" for c in test_id), "Should be valid hex"

    print("\n✅ UUID generation is working!")
    return True


async def test_notify_candidate_profile_presented(
    job_seeker_uid: str, job_provider_uid: str
):
    """
    Test the notify_candidate_profile_presented function.

    Args:
        job_seeker_uid: WhatsApp ID of the job seeker (candidate)
        job_provider_uid: WhatsApp ID of the job provider
    """
    print("\n" + "=" * 60)
    print("Testing notify_candidate_profile_presented")
    print("=" * 60)

    # Fetch job seeker data
    job_seeker_profile = get_user_profile(job_seeker_uid) or {}
    job_seeker_name = job_seeker_profile.get("name", "Unknown Candidate")
    print(f"\n📋 Job Seeker: {job_seeker_name} ({job_seeker_uid})")

    # Fetch job provider data
    job_provider_profile = get_user_profile(job_provider_uid) or {}
    job_provider_extraction = get_extraction_data(job_provider_uid) or {}
    job_provider_name = job_provider_profile.get("name", "A company")
    job_provider_linkedin = job_provider_profile.get("linkedin_url", "")

    print(f"📋 Job Provider: {job_provider_name} ({job_provider_uid})")
    print(f"   Job Title: {job_provider_extraction.get('job_title', '(not set)')}")
    print(
        f"   Company Stage: {job_provider_extraction.get('company_stage', '(not set)')}"
    )
    print(
        f"   Company Culture: {job_provider_extraction.get('company_culture', '(not set)')}"
    )
    print(f"   LinkedIn: {job_provider_linkedin or '(not set)'}")

    print("\n" + "-" * 60)
    print("🔔 Generating description and sending notification...")
    print("-" * 60)

    try:
        result = await notify_candidate_profile_presented(
            candidate_wa_id=job_seeker_uid,
            job_provider_uid=job_provider_uid,
            job_provider_name=job_provider_name,
            candidate_name=job_seeker_name,
            extraction_data=job_provider_extraction,
            linkedin_url=job_provider_linkedin,
        )
        if result:
            print("\n✅ Notification sent successfully!")
        else:
            print("\n❌ Notification failed to send")
        return result
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(
        test_notify_candidate_profile_presented(
            job_seeker_uid="918368828660",
            job_provider_uid="918766335252",
        )
    )
