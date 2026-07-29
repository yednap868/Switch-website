"""
User recognition and smart lookup module.
Handles multi-key user identification and conversation resumption.
"""

import re
import time
from typing import Any, Dict, List, Optional

try:
    from utils.db import fs

    FIREBASE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ [FIREBASE] Firebase not available: {e}")
    fs = None
    FIREBASE_AVAILABLE = False


class UserRecognitionManager:
    """Manages user recognition with multiple lookup keys."""

    def __init__(self):
        self.lookup_keys = ["wa_id", "phone", "email"]

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for consistent lookup."""
        if not phone:
            return phone

        # For WhatsApp IDs (wa_id), don't normalize - keep as is
        if phone.startswith("user_") or phone.startswith("wa_") or len(phone) > 15:
            return phone

        # Remove all non-digit characters
        digits = re.sub(r"\D", "", phone)

        # Handle different formats
        if digits.startswith("1") and len(digits) == 11:
            # US number with country code
            return digits[1:]  # Remove leading 1
        elif len(digits) == 10:
            # US number without country code
            return digits
        elif len(digits) == 12 and digits.startswith("91"):
            # Indian number with country code (91)
            return digits
        else:
            # International number - keep as is
            return digits

    def _normalize_email(self, email: str) -> str:
        """Normalize email for consistent lookup."""
        return email.lower().strip()

    def _search_user_by_key(self, key: str, value: str) -> Optional[Dict]:
        """Search for user by specific key-value pair."""
        if not FIREBASE_AVAILABLE:
            return None
        try:
            # Normalize value based on key type
            if key == "phone":
                value = self._normalize_phone(value)
            elif key == "email":
                value = self._normalize_email(value)

            # Search in users collection
            users_ref = fs.collection("users")
            query = users_ref.where(key, "==", value).limit(1)

            for doc in query.stream():
                user_data = doc.to_dict()
                user_data["wa_id"] = doc.id  # Ensure wa_id is set
                return user_data

            return None

        except Exception as e:
            print(f"❌ [RECOGNITION] Error searching by {key}: {e}")
            return None

    def find_user(
        self, wa_id: str = None, phone: str = None, email: str = None
    ) -> Optional[Dict]:
        """Find user using multiple lookup keys."""
        search_params = []

        if wa_id:
            search_params.append(("wa_id", wa_id))
        if phone:
            search_params.append(("phone", self._normalize_phone(phone)))
        if email:
            search_params.append(("email", self._normalize_email(email)))

        # Try each lookup key
        for key, value in search_params:
            user_data = self._search_user_by_key(key, value)
            if user_data:
                print(f"🔍 [RECOGNITION] Found user by {key}: {value}")
                return user_data

        print(f"🔍 [RECOGNITION] User not found with params: {search_params}")
        return None

    def create_or_update_user(
        self,
        wa_id: str,
        phone: str = None,
        email: str = None,
        initial_data: dict = None,
    ) -> Dict:
        """Create new user or update existing user with additional identifiers."""
        if not FIREBASE_AVAILABLE:
            print(f"👤 [USER] Firebase not available - creating in-memory user {wa_id}")
            return {
                "wa_id": wa_id,
                "phone": self._normalize_phone(phone) if phone else None,
                "email": self._normalize_email(email) if email else None,
                "profile": initial_data or {},
                "state": "greeting",
                "created_at": time.time(),
                "last_interaction": time.time(),
            }
        try:
            # Check if user already exists
            existing_user = self.find_user(wa_id=wa_id, phone=phone, email=email)

            if existing_user:
                # Update existing user with new identifiers
                update_data = {}

                if phone and not existing_user.get("phone"):
                    update_data["phone"] = self._normalize_phone(phone)

                if email and not existing_user.get("email"):
                    update_data["email"] = self._normalize_email(email)

                if initial_data:
                    if "profile" not in existing_user:
                        existing_user["profile"] = {}
                    existing_user["profile"].update(initial_data)
                    update_data["profile"] = existing_user["profile"]
                    
                    # Also save compensation_intent_detected at top level for easier access
                    if "compensation_intent_detected" in initial_data:
                        update_data["compensation_intent_detected"] = initial_data["compensation_intent_detected"]

                if update_data:
                    update_data["last_updated"] = time.time()
                    fs.collection("users").document(wa_id).set(update_data, merge=True)
                    print(f"👤 [USER] Updated user {wa_id} with new identifiers")

                return existing_user
            else:
                # Create new user
                user_data = {
                    "wa_id": wa_id,
                    "phone": self._normalize_phone(phone) if phone else None,
                    "email": self._normalize_email(email) if email else None,
                    "profile": initial_data or {},
                    "state": "greeting",
                    "created_at": time.time(),
                    "last_interaction": time.time(),
                }
                
                # Also save compensation_intent_detected at top level for easier access
                if initial_data and "compensation_intent_detected" in initial_data:
                    user_data["compensation_intent_detected"] = initial_data["compensation_intent_detected"]

                fs.collection("users").document(wa_id).set(user_data)
                print(f"👤 [USER] Created new user {wa_id}")

                return user_data

        except Exception as e:
            print(f"❌ [USER] Error creating/updating user: {e}")
            return {}

    def get_user_identity(self, wa_id: str) -> Dict[str, Any]:
        """Get complete user identity information."""
        try:
            user_data = self.find_user(wa_id=wa_id)
            if user_data:
                return {
                    "wa_id": user_data.get("wa_id", wa_id),
                    "phone": user_data.get("phone"),
                    "email": user_data.get("email"),
                    "profile": user_data.get("profile", {}),
                    "state": user_data.get("state", "greeting"),
                    "created_at": user_data.get("created_at", time.time()),
                    "last_interaction": user_data.get("last_interaction", time.time()),
                }
            return {}

        except Exception as e:
            print(f"❌ [IDENTITY] Error getting user identity: {e}")
            return {}

    def is_returning_user(self, wa_id: str) -> bool:
        """Check if user is returning (has previous conversation history)."""
        try:
            user_data = self.find_user(wa_id=wa_id)
            if user_data:
                # Check if user has conversation history
                messages_ref = (
                    fs.collection("conversations")
                    .document(wa_id)
                    .collection("messages")
                )
                message_count = len(list(messages_ref.limit(1).stream()))

                is_returning = message_count > 0
                print(
                    f"🔄 [RETURNING] User {wa_id} is {'returning' if is_returning else 'new'}"
                )
                return is_returning

            return False

        except Exception as e:
            print(f"❌ [RETURNING] Error checking returning user: {e}")
            return False

    def validate_user_context(self, wa_id: str) -> bool:
        """Validate user context to prevent contamination."""
        try:
            # This is a user validation method to ensure proper context isolation
            user_data = self.find_user(wa_id=wa_id)
            return user_data is not None

        except Exception as e:
            print(f"❌ [VALIDATION] Error validating user context: {e}")
            return False

    def get_intelligent_user_context(self, wa_id: str) -> Dict[str, Any]:
        """Get intelligent context for how the agent should interact with this user."""
        try:
            user_data = self.find_user(wa_id=wa_id)
            is_returning = self.is_returning_user(wa_id)

            if not user_data:
                # Completely new user
                return self._get_fresh_user_context(wa_id)

            if not is_returning:
                # User exists but no conversation history - treat as fresh
                return self._get_fresh_user_context(wa_id, user_data)

            # Returning user with history
            return self._get_returning_user_context(wa_id, user_data)

        except Exception as e:
            print(f"❌ [INTELLIGENT_CONTEXT] Error getting user context: {e}")
            return self._get_fresh_user_context(wa_id)

    def _get_fresh_user_context(
        self, wa_id: str, user_data: Dict = None
    ) -> Dict[str, Any]:
        """Get context for fresh users - what agent should ask and how to behave."""
        profile = user_data.get("profile", {}) if user_data else {}

        # Check both top-level user_data AND profile field since log_user_profile saves at top level
        # Helper to check if field exists in either location
        def has_field(field_name: str) -> bool:
            # Check top level first (where log_user_profile saves)
            if user_data and user_data.get(field_name):
                return True
            # Check profile field (legacy location)
            if profile.get(field_name):
                return True
            return False
        
        def has_goal_or_connection_type() -> bool:
            # Check top level
            if user_data:
                if user_data.get("goal") or user_data.get("connection_type") or user_data.get("primary_goal"):
                    return True
            # Check profile field
            if profile.get("goal") or profile.get("connection_type") or profile.get("primary_goal"):
                return True
            return False

        # Determine what information is missing
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
            if not has_goal_or_connection_type():
                missing_fields.append("connection_type")
        if not has_field("name"):
            missing_fields.append("name")
        if not has_field("email"):
            missing_fields.append("email")
        # Check linkedin_url (can be at top level or in profile)
        has_linkedin = has_field("linkedin_url")
        # Also check for "linkedin" field (alternative name)
        if not has_linkedin:
            if user_data and (user_data.get("linkedin") or isinstance(user_data.get("linkedin"), dict)):
                has_linkedin = True
            if profile.get("linkedin") or isinstance(profile.get("linkedin"), dict):
                has_linkedin = True
        if not has_linkedin:
            missing_fields.append("linkedin_url")

        return {
            "user_type": "fresh_user",
            "is_returning": False,
            "behavior_mode": "discovery",
            "conversation_approach": "full_onboarding",
            "missing_fields": missing_fields,
            "agent_instructions": {
                "greeting_style": "welcoming_introduction",
                "information_gathering": "systematic_collection",
                "conversation_flow": "guided_discovery",
                "questions_to_ask": self._get_fresh_user_questions(missing_fields, user_data),
                "what_to_avoid": [
                    "Referencing previous conversations",
                    "Assuming any context about their business",
                    "Mentioning previous data or extraction",
                    "Using follow-up language",
                ],
                "conversation_goals": [
                    "Collect basic profile information",
                    "Understand their primary goal",
                    "Build rapport and trust",
                    "Set expectations for the service",
                ],
            },
            "data_handling": {
                "use_previous_data": False,
                "start_fresh": True,
                "extraction_approach": "comprehensive",
                "validation_needed": True,
            },
            "context_summary": f"Fresh user - needs full onboarding. Missing: {', '.join(missing_fields)}",
        }

    def _get_returning_user_context(
        self, wa_id: str, user_data: Dict
    ) -> Dict[str, Any]:
        """Get context for returning users - what agent should reference and how to continue."""
        try:
            # Get conversation history and extraction data
            from .conversation_history import conversation_history

            conv_context = conversation_history.get_conversation_context(wa_id)

            # Get extraction data
            extraction_data = {}
            if FIREBASE_AVAILABLE:
                try:
                    extraction_doc = fs.collection("extractions").document(wa_id).get()
                    if extraction_doc.exists:
                        extraction_data = extraction_doc.to_dict()
                except:
                    pass

            # Analyze conversation recency
            last_interaction = user_data.get("last_interaction", 0)
            days_since_last = (time.time() - last_interaction) / (24 * 60 * 60)

            # Determine conversation approach based on recency
            if days_since_last > 7:
                approach = "gentle_reconnection"
                greeting_style = "warm_welcome_back"
            elif days_since_last > 1:
                approach = "contextual_resume"
                greeting_style = "brief_welcome_back"
            else:
                approach = "immediate_continuation"
                greeting_style = "natural_continuation"

            return {
                "user_type": "returning_user",
                "is_returning": True,
                "behavior_mode": "continuation",
                "conversation_approach": approach,
                "days_since_last_interaction": days_since_last,
                "agent_instructions": {
                    "greeting_style": greeting_style,
                    "information_gathering": "update_focused",
                    "conversation_flow": "contextual_continuation",
                    "questions_to_ask": self._get_returning_user_questions(
                        extraction_data, days_since_last
                    ),
                    "what_to_reference": [
                        "Previous conversations naturally",
                        "Their stated goals and priorities",
                        "Previous extraction data",
                        "Conversation history and topics",
                    ],
                    "conversation_goals": [
                        "Check for updates since last conversation",
                        "Reference previous context appropriately",
                        "Build on existing relationship",
                        "Focus on progress and changes",
                    ],
                },
                "data_handling": {
                    "use_previous_data": True,
                    "start_fresh": False,
                    "extraction_approach": "incremental_update",
                    "validation_needed": False,
                },
                "previous_context": {
                    "extraction_data": extraction_data,
                    "conversation_topics": conv_context.get("key_topics", []),
                    "last_goals": extraction_data.get("urgent_needs", ""),
                    "user_story": extraction_data.get("the_story", ""),
                    "current_focus": extraction_data.get("current_focus", ""),
                },
                "context_summary": f"Returning user - {approach} approach. Last seen {days_since_last:.1f} days ago",
            }

        except Exception as e:
            print(f"❌ [RETURNING_CONTEXT] Error: {e}")
            # Fallback to fresh user approach if error
            return self._get_fresh_user_context(wa_id, user_data)

    def _get_fresh_user_questions(self, missing_fields: List[str], user_data: Dict = None) -> List[str]:
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

        # Note: Detailed questions about goals/story happen on the voice call, not text
        # These are only asked if onboarding is complete and user agrees to call

        return questions

    def _get_returning_user_questions(
        self, extraction_data: Dict, days_since_last: float
    ) -> List[str]:
        """Get specific questions agent should ask returning users."""
        questions = []

        if days_since_last > 7:
            questions.extend(
                [
                    "What's changed since we last talked?",
                    "How are things going with [previous goal]?",
                    "Any updates on what you were working on?",
                ]
            )
        elif days_since_last > 1:
            questions.extend(
                [
                    "What's your priority now?",
                    "How's [previous focus] going?",
                    "What's evolved since our last conversation?",
                ]
            )
        else:
            questions.extend(
                [
                    "What's the update?",
                    "How did [previous topic] go?",
                    "What's next on your list?",
                ]
            )

        # Add context-specific questions based on previous data
        if extraction_data.get("urgent_needs"):
            questions.append(
                f"How's the progress on {extraction_data['urgent_needs']}?"
            )

        if extraction_data.get("top_priority"):
            questions.append(f"Still focused on {extraction_data['top_priority']}?")

        return questions

    def get_conversation_resume_context(self, wa_id: str) -> Dict[str, Any]:
        """Legacy method - redirects to intelligent context."""
        return self.get_intelligent_user_context(wa_id)


# Global user recognition manager instance
user_recognition = UserRecognitionManager()
