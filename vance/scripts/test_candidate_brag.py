"""
Test script for candidate brag service.
Tests brag prompt generation and share templates.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.candidate_brag_service import candidate_brag_service


async def test_brag_service():
    """Test the candidate brag service."""
    print("=" * 60)
    print("Testing Candidate Brag Service")
    print("=" * 60)
    
    # Test with a sample candidate UID
    test_candidate_uid = "918368828660"  # Using your UID for testing
    
    print(f"\n1. Testing with candidate UID: {test_candidate_uid}")
    
    # Test 1: Generate share templates
    print("\n2. Testing share template generation...")
    milestones = ["intro", "interview", "offer", "hired"]
    
    for milestone in milestones:
        templates = candidate_brag_service._generate_share_templates(milestone)
        print(f"\n   Milestone: {milestone}")
        print(f"   LinkedIn ({len(templates['linkedin'])} chars):")
        print(f"   {templates['linkedin'][:100]}...")
        print(f"   Twitter ({len(templates['twitter'])} chars):")
        print(f"   {templates['twitter'][:100]}...")
        print(f"   WhatsApp ({len(templates['whatsapp'])} chars):")
        print(f"   {templates['whatsapp'][:100]}...")
    
    # Test 2: Check idempotency
    print("\n3. Testing idempotency check...")
    should_send_1 = candidate_brag_service.should_send_brag_prompt(test_candidate_uid, "intro")
    print(f"   Should send 'intro' (first check): {should_send_1}")
    
    # Test 3: Send brag prompt (skip actual sending in automated test)
    if should_send_1:
        print("\n4. Testing send_brag_prompt logic...")
        print("   ✅ Idempotency check passed - would send message")
        print("   (Skipping actual WhatsApp send in automated test)")
        
        # Uncomment below to actually send:
        # result = await candidate_brag_service.send_brag_prompt(
        #     candidate_uid=test_candidate_uid,
        #     milestone="intro",
        #     founder_name="Test Founder",
        # )
        # print(f"   Result: {result}")
    
    # Test 4: Check different milestones
    print("\n5. Testing different milestones...")
    for milestone in milestones:
        should_send = candidate_brag_service.should_send_brag_prompt(test_candidate_uid, milestone)
        print(f"   {milestone}: {'Would send' if should_send else 'Already sent'}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nShare Templates Preview:")
    print("-" * 60)
    templates = candidate_brag_service._generate_share_templates("interview")
    print("LinkedIn:")
    print(templates['linkedin'])
    print("\nTwitter/X:")
    print(templates['twitter'])
    print("\nWhatsApp:")
    print(templates['whatsapp'])


if __name__ == "__main__":
    asyncio.run(test_brag_service())

