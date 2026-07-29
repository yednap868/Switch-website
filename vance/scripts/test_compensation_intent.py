"""
Test script to verify compensation intent detection logic.
"""


def _is_compensation_intent(message_text: str) -> bool:
    """
    Detect if user message indicates compensation/compensation band intent.
    This automatically classifies them as a job seeker.
    """
    message_lower = message_text.lower()
    compensation_keywords = [
        "compensation band",
        "compensation",
        "salary",
        "pay",
        "what founders would pay",
        "what would founders pay",
        "founders would place me",
        "compensation founders",
        "salary band",
        "pay band",
        "what am i worth",
        "my worth",
        "market rate",
        "market salary",
    ]
    return any(keyword in message_lower for keyword in compensation_keywords)


def test_compensation_intent_detection():
    """Test various messages to see if compensation intent is detected."""
    
    test_cases = [
        # Should be detected
        ("Hi Vance, I want to know what compensation band founders would place me in today.", True),
        ("What compensation band would founders place me in?", True),
        ("I want to know my compensation", True),
        ("What salary would founders pay me?", True),
        ("What's my market rate?", True),
        ("What am I worth?", True),
        ("compensation band", True),
        ("salary band", True),
        ("what founders would pay", True),
        ("market salary", True),
        ("I want to know what compensation band founders would place me in today", True),
        
        # Should NOT be detected
        ("Hi, I'm looking for a job", False),
        ("I'm hiring engineers", False),
        ("I want to connect with founders", False),
        ("What's your name?", False),
        ("Hello", False),
        ("I need a job", False),
    ]
    
    print("🧪 Testing Compensation Intent Detection\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for message, expected in test_cases:
        result = _is_compensation_intent(message)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | Expected: {expected}, Got: {result}")
        print(f"   Message: {message[:70]}")
        print()
    
    print("=" * 80)
    print(f"\n📊 Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    import sys
    success = test_compensation_intent_detection()
    sys.exit(0 if success else 1)
