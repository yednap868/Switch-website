"""
Test script to verify user recognition logic for compensation intent users.
"""


def _get_fresh_user_questions(missing_fields: list, user_data: dict = None) -> list:
    """Get specific questions agent should ask fresh users in order."""
    questions = []

    # Check if user was auto-classified from compensation intent (skip connection_type question)
    compensation_intent = (
        user_data.get("compensation_intent_detected", False)
        if user_data
        else False
    )
    
    # FIRST: Ask what kind of people they want to connect with (applies to both candidates and hiring founders)
    # SKIP if user was auto-classified from compensation intent
    if "connection_type" in missing_fields and not compensation_intent:
        questions.append("What kind of people are you looking to connect with?")
        questions.append("(e.g., founders hiring engineers, candidates looking for opportunities, referrers, etc.)")

    if "name" in missing_fields:
        questions.append("What should I call you?")

    if "email" in missing_fields:
        questions.append("What's your email? I'll send you some connections.")

    if "linkedin_url" in missing_fields:
        questions.append(
            "Send me your LinkedIn - I want to see your background before we talk."
        )

    return questions


def _get_fresh_user_context_missing_fields(user_data: dict = None) -> list:
    """Simulate the missing_fields logic from _get_fresh_user_context."""
    profile = user_data.get("profile", {}) if user_data else {}
    
    missing_fields = []
    # Check if user was auto-classified from compensation intent (skip connection_type question)
    compensation_intent = (
        user_data.get("compensation_intent_detected", False)
        if user_data
        else False
    )
    # FIRST: Check if they've answered "what kind of people you want to connect with"
    # SKIP if compensation intent detected
    if not compensation_intent:
        if not profile.get("goal") and not profile.get("connection_type"):
            missing_fields.append("connection_type")
    if not profile.get("name"):
        missing_fields.append("name")
    if not profile.get("email"):
        missing_fields.append("email")
    if not profile.get("linkedin_url"):
        missing_fields.append("linkedin_url")
    
    return missing_fields


def test_user_recognition_compensation():
    """Test that compensation intent users skip connection_type question."""
    
    print("🧪 Testing User Recognition for Compensation Intent Users\n")
    print("=" * 80)
    
    # Test Case 1: Regular user (no compensation intent)
    print("\n📋 Test Case 1: Regular user (no compensation intent)")
    user_data_regular = {
        "profile": {},
        "compensation_intent_detected": False,
    }
    missing_fields_regular = _get_fresh_user_context_missing_fields(user_data_regular)
    questions_regular = _get_fresh_user_questions(missing_fields_regular, user_data_regular)
    
    print(f"Missing fields: {missing_fields_regular}")
    print(f"Questions to ask: {questions_regular}")
    
    assert "connection_type" in missing_fields_regular, "Regular user should have connection_type in missing fields"
    assert any("What kind of people" in q for q in questions_regular), "Regular user should be asked about connection type"
    print("✅ PASS: Regular user will be asked about connection type")
    
    # Test Case 2: Compensation intent user
    print("\n📋 Test Case 2: Compensation intent user")
    user_data_compensation = {
        "profile": {},
        "user_type": "job_seeker",
        "compensation_intent_detected": True,
    }
    missing_fields_compensation = _get_fresh_user_context_missing_fields(user_data_compensation)
    questions_compensation = _get_fresh_user_questions(missing_fields_compensation, user_data_compensation)
    
    print(f"Missing fields: {missing_fields_compensation}")
    print(f"Questions to ask: {questions_compensation}")
    
    assert "connection_type" not in missing_fields_compensation, "Compensation intent user should NOT have connection_type in missing fields"
    assert not any("What kind of people" in q for q in questions_compensation), "Compensation intent user should NOT be asked about connection type"
    assert any("What should I call you" in q for q in questions_compensation), "Compensation intent user should be asked for name"
    print("✅ PASS: Compensation intent user skips connection type question")
    
    # Test Case 3: Compensation intent user with partial data
    print("\n📋 Test Case 3: Compensation intent user with name already provided")
    user_data_partial = {
        "profile": {
            "name": "John Doe",
        },
        "user_type": "job_seeker",
        "compensation_intent_detected": True,
    }
    missing_fields_partial = _get_fresh_user_context_missing_fields(user_data_partial)
    questions_partial = _get_fresh_user_questions(missing_fields_partial, user_data_partial)
    
    print(f"Missing fields: {missing_fields_partial}")
    print(f"Questions to ask: {questions_partial}")
    
    assert "connection_type" not in missing_fields_partial, "Should not ask for connection_type"
    assert "name" not in missing_fields_partial, "Name should not be in missing fields"
    assert "email" in missing_fields_partial, "Email should be in missing fields"
    assert not any("What should I call you" in q for q in questions_partial), "Should not ask for name"
    assert any("email" in q.lower() for q in questions_partial), "Should ask for email"
    print("✅ PASS: Compensation intent user with partial data works correctly")
    
    print("\n" + "=" * 80)
    print("✅ All user recognition tests passed!")
    return True


if __name__ == "__main__":
    import sys
    try:
        success = test_user_recognition_compensation()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

