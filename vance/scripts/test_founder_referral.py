"""
Test script for founder referral service.
Tests referral code generation, link creation, and prompt sending.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.founder_referral_service import founder_referral_service
from utils.db import fs, get_user_profile


async def test_referral_service():
    """Test the founder referral service."""
    print("=" * 60)
    print("Testing Founder Referral Service")
    print("=" * 60)
    
    # Test with a sample founder UID (you can change this)
    test_founder_uid = "918368828660"  # Using your UID for testing
    
    print(f"\n1. Testing with founder UID: {test_founder_uid}")
    
    # Check if user exists
    user_profile = get_user_profile(test_founder_uid) or {}
    if not user_profile:
        print(f"⚠️  User {test_founder_uid} not found. Using test UID anyway.")
    else:
        print(f"✅ User found: {user_profile.get('name', 'Unknown')}")
    
    # Test 1: Generate referral code
    print("\n2. Testing referral code generation...")
    code1 = founder_referral_service.generate_referral_code(test_founder_uid)
    code2 = founder_referral_service.generate_referral_code(test_founder_uid)
    print(f"   Code 1: {code1}")
    print(f"   Code 2: {code2}")
    print(f"   Codes are same (expected for same day): {code1 == code2}")
    
    # Test 2: Get or create referral link
    print("\n3. Testing get_or_create_referral_link...")
    link1 = founder_referral_service.get_or_create_referral_link(test_founder_uid)
    print(f"   Referral link: {link1}")
    
    # Get again (should return same)
    link2 = founder_referral_service.get_or_create_referral_link(test_founder_uid)
    print(f"   Second call (should be same): {link2}")
    print(f"   Links match: {link1 == link2}")
    
    # Check Firestore
    referral_doc = fs.collection("founder_referrals").document(test_founder_uid).get()
    if referral_doc.exists:
        referral_data = referral_doc.to_dict() or {}
        print(f"   ✅ Stored in Firestore:")
        print(f"      - Referral code: {referral_data.get('referral_code')}")
        print(f"      - Referral count: {referral_data.get('referral_count', 0)}")
    
    # Test 3: Check idempotency
    print("\n4. Testing idempotency check...")
    should_send_1 = founder_referral_service.should_send_referral_prompt(test_founder_uid)
    print(f"   Should send (first check): {should_send_1}")
    
    # Test 4: Send referral prompt (if should_send is True)
    # Skip actual sending in automated test - just verify the logic
    if should_send_1:
        print("\n5. Testing send_referral_prompt logic...")
        print("   ✅ Idempotency check passed - would send message")
        print("   (Skipping actual WhatsApp send in automated test)")
        
        # Verify we can call the function (but it won't send if we don't want to)
        # Uncomment below to actually send:
        # result = await founder_referral_service.send_referral_prompt(
        #     founder_uid=test_founder_uid,
        #     trigger_reason="test"
        # )
        # print(f"   Result: {result}")
    else:
        print("\n5. Skipping send test (prompt already sent recently)")
        prompt_doc = fs.collection("founder_referral_prompts").document(test_founder_uid).get()
        if prompt_doc.exists:
            prompt_data = prompt_doc.to_dict() or {}
            sent_at = prompt_data.get("sent_at", 0)
            import time
            days_ago = (time.time() - sent_at) / 86400
            print(f"   Last sent: {days_ago:.1f} days ago")
    
    # Test 5: Test referral tracking
    print("\n6. Testing referral tracking...")
    test_referred_uid = "test_referred_123"
    test_code = code1
    referrer_uid = founder_referral_service.track_referral(
        referred_uid=test_referred_uid,
        referral_code=test_code
    )
    if referrer_uid:
        print(f"   ✅ Referral tracked: {test_referred_uid} referred by {referrer_uid}")
        
        # Check referral relationship
        rel_doc = fs.collection("referral_relationships").document(test_referred_uid).get()
        if rel_doc.exists:
            rel_data = rel_doc.to_dict() or {}
            print(f"   ✅ Relationship stored:")
            print(f"      - Referrer: {rel_data.get('referrer_uid')}")
            print(f"      - Code: {rel_data.get('referral_code')}")
    else:
        print(f"   ⚠️  Could not track referral (code might not match)")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_referral_service())

