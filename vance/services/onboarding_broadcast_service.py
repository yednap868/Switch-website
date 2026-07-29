"""
Onboarding broadcast service.

Whenever a new user completes onboarding, we broadcast a short, human-style
WhatsApp message about them to a small, relevant audience inside Vance.

High-level behaviour:
    - Detect whether the user is a job seeker (candidate) or job provider (hiring).
    - For job seekers: find relevant job providers / founders who are hiring.
    - For job providers: find relevant candidates who match their needs.
    - Send each recipient a short message:
        "I just spoke with {Name} — they're looking for {Role/Need} in {Location/Domain}.
         Profile: {profile_link}
         Need an intro?"

Implementation notes:
    - This service is intentionally conservative:
        - Limit audience size to avoid spam.
        - Uses simple heuristics over Firestore `extractions` +
          `user_profiles` instead of heavy LLM matching.
    - Idempotency:
        - Firestore collection `onboarding_broadcasts/{uid}` ensures that
          we only broadcast once per user (per onboarding completion).
"""

import time
from typing import Dict, List, Optional, Tuple

from firebase_admin import firestore

from utils.db import fs, get_extraction_data, get_user_profile
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


class OnboardingBroadcastService:
    """Service responsible for broadcasting new users on onboarding completion."""

    # Heuristic field groups to detect user type from extraction data
    JOB_SEEKER_INDICATORS = [
        "target_role",
        "core_skills",
        "work_experience",
        "job_search_urgency",
        "current_location",
    ]

    JOB_PROVIDER_INDICATORS = [
        "job_title",
        "required_skills",
        "hiring_urgency",
        "company_stage",
        "company_culture",
    ]

    def __init__(self):
        self.sender = WhatsAppSender()

    # -------------------------------------------------------------------------
    # Public entrypoints
    # -------------------------------------------------------------------------

    def broadcast_on_text_onboarding_complete(self, user_id: str) -> None:
        """
        Broadcast a user who just completed text onboarding (connection_type + name + email + linkedin).
        
        This is called after text onboarding completes, before the voice call.
        Uses the connection_type/goal to determine who to message.
        """
        try:
            if self._already_broadcast(user_id, user_type="text_onboarding"):
                print(f"ℹ️ [ONBOARD_BROADCAST] User {user_id} already broadcast after text onboarding – skipping")
                return

            user_profile = get_user_profile(user_id) or {}
            name = user_profile.get("name") or ""
            goal = (
                user_profile.get("connection_type")
                or user_profile.get("goal")
                or user_profile.get("primary_goal")
                or user_profile.get("arbitrary", {}).get("connection_type")
                or ""
            )
            
            if not name or not goal:
                print(f"⚠️ [ONBOARD_BROADCAST] Missing name or connection_type/goal for {user_id}, skipping broadcast")
                return

            # Determine user type from user_profile (most reliable)
            from agent.models import detect_user_type
            detected_user_type = detect_user_type(user_profile)
            user_type_str = detected_user_type.value if hasattr(detected_user_type, 'value') else str(detected_user_type)
            
            # If user_type is still general, try to infer from goal/connection_type
            if user_type_str == "general":
                connection_type_lower = goal.lower()
                # If they mention "hiring", "recruit", "looking to hire", "engineers", "developers" → likely job provider
                # If they mention "looking for roles", "founders hiring", "job opportunities" → likely job seeker
                if any(kw in connection_type_lower for kw in ["hiring", "recruit", "looking to hire", "need engineers", "want engineers"]):
                    user_type_str = "job_provider"
                elif any(kw in connection_type_lower for kw in ["looking for roles", "founders hiring", "job opportunities", "looking for job"]):
                    user_type_str = "job_seeker"
                elif any(kw in connection_type_lower for kw in ["engineer", "developer", "full stack", "backend", "frontend"]):
                    # Technical roles mentioned - likely job provider looking to hire
                    user_type_str = "job_provider"

            # Build simple message for template
            # Template format: "I just spoke with {{1}} — they're looking to connect with {{2}}. Need an intro?"
            message = f"I just spoke with {name} — they're looking to connect with {goal}.\nNeed an intro?"

            # Find audience based on user type
            # Job providers → find candidates/job seekers (20 candidates)
            # Job seekers → find job providers/founders (10 job providers)
            audience = []
            if user_type_str == "job_provider":
                # User is a job provider → find 20 candidates/job seekers
                audience = self._find_candidates_by_connection_type(goal, limit=20)
                print(f"🔍 [ONBOARD_BROADCAST] Job provider detected, finding 20 candidates for {user_id}")
            elif user_type_str == "job_seeker":
                # User is a job seeker → find 10 job providers/founders
                audience = self._find_job_providers_by_connection_type(goal, limit=10)
                print(f"🔍 [ONBOARD_BROADCAST] Job seeker detected, finding 10 job providers for {user_id}")
            else:
                # Ambiguous - default to treating as job provider if it mentions technical roles
                # (most common case: "full stack engineers" = hiring)
                connection_type_lower = goal.lower()
                if any(kw in connection_type_lower for kw in ["engineer", "developer", "full stack", "backend", "frontend"]):
                    audience = self._find_candidates_by_connection_type(goal, limit=20)
                    print(f"🔍 [ONBOARD_BROADCAST] Ambiguous type but technical roles mentioned, treating as job provider, finding 20 candidates")
                else:
                    # Try job providers first (for job seekers)
                    audience = self._find_job_providers_by_connection_type(goal, limit=10)
                    print(f"🔍 [ONBOARD_BROADCAST] Ambiguous type, trying job providers first, found {len(audience)}")
                    if len(audience) < 5:
                        # Fallback to candidates if not enough job providers
                        candidates = self._find_candidates_by_connection_type(goal, limit=20)
                        audience.extend(candidates)
                        print(f"🔍 [ONBOARD_BROADCAST] Not enough job providers, also added {len(candidates)} candidates")

            if not audience:
                print(f"ℹ️ [ONBOARD_BROADCAST] No audience found for {user_id} (connection_type: {goal})")
                return

            # Get onboarding completion time (when text onboarding was completed)
            user_profile = get_user_profile(user_id) or {}
            onboarding_completed_at = user_profile.get("onboarding_completed_at") or time.time()
            
            # Always use template messages for broadcasts (as per user requirement)
            sent_to = self._send_whatsapp_broadcast(
                message=message,
                audience=audience,
                broadcasted_user_id=user_id,
                broadcasted_user_name=name,
                connection_type=goal,
                onboarding_completed_at=onboarding_completed_at,
                always_use_template=True,  # Always use template messages
            )
            if not sent_to:
                print(f"⚠️ [ONBOARD_BROADCAST] No WhatsApp deliveries for {user_id}")
                return

            # Save broadcast context to conversation history for each recipient
            # This helps the agent know who they're responding about when they say "I need intro"
            try:
                from api.whatsapp_modules.conversation_history import conversation_history
                
                # Always use template messages (as per user requirement)
                used_template = True
                
                broadcast_context = {
                    "type": "onboarding_broadcast",
                    "broadcasted_user_id": user_id,
                    "broadcasted_user_name": name,
                    "connection_type": goal,
                    "timestamp": time.time(),
                    "used_template": True,  # Always using template messages
                }
                for recipient_uid in sent_to:
                    conversation_history.save_message(
                        user_id=recipient_uid,
                        sender="agent",
                        content=message,
                        message_type="template",  # Always use template for broadcasts
                        metadata=broadcast_context,
                    )
                print(f"✅ [ONBOARD_BROADCAST] Saved broadcast context for {len(sent_to)} recipients (always using template)")
            except Exception as e:
                print(f"⚠️ [ONBOARD_BROADCAST] Failed to save broadcast context: {e}")

            self._mark_broadcast_sent(
                user_id=user_id,
                user_type="text_onboarding",
                audience_ids=sent_to,
                profile_link="",
            )
            print(
                f"✅ [ONBOARD_BROADCAST] Broadcast {user_id} (text onboarding) to {len(sent_to)} recipients"
            )
        except Exception as e:
            print(f"❌ [ONBOARD_BROADCAST] Error broadcasting text onboarding for {user_id}: {e}")
            import traceback
            traceback.print_exc()

    def broadcast_for_job_seeker(self, user_id: str, extraction_data: Dict) -> None:
        """
        Broadcast a newly-onboarded job seeker to a small set of relevant job providers.

        Called from the voice onboarding pipeline once all critical fields
        for a job seeker are complete and their public profile is created.
        """
        try:
            if self._already_broadcast(user_id, user_type="job_seeker"):
                print(f"ℹ️ [ONBOARD_BROADCAST] Job seeker {user_id} already broadcast – skipping")
                return

            user_profile = get_user_profile(user_id) or {}
            message, profile_link = self._build_candidate_message(user_profile, extraction_data)
            if not message:
                print(f"⚠️ [ONBOARD_BROADCAST] Cannot build message for job seeker {user_id}")
                return

            # Find 10 job providers for job seeker (as per requirement)
            audience = self._find_job_provider_audience_for_candidate(
                candidate_uid=user_id,
                candidate_profile=user_profile,
                candidate_extraction=extraction_data,
                limit=10,  # Job seekers → 10 job providers
            )

            if not audience:
                print(f"ℹ️ [ONBOARD_BROADCAST] No audience found for job seeker {user_id}")
                return

            # Get onboarding completion time
            onboarding_completed_at = user_profile.get("onboarding_completed_at") or time.time()
            
            # Always use template messages (as per requirement)
            sent_to = self._send_whatsapp_broadcast(
                message=message,
                audience=audience,
                broadcasted_user_id=user_id,
                broadcasted_user_name=user_profile.get("name", ""),
                connection_type="",
                onboarding_completed_at=onboarding_completed_at,
                always_use_template=True,  # Always use template messages
            )
            if not sent_to:
                print(f"⚠️ [ONBOARD_BROADCAST] No WhatsApp deliveries for job seeker {user_id}")
                return

            self._mark_broadcast_sent(
                user_id=user_id,
                user_type="job_seeker",
                audience_ids=sent_to,
                profile_link=profile_link,
            )
            print(
                f"✅ [ONBOARD_BROADCAST] Broadcast job seeker {user_id} to {len(sent_to)} recipients"
            )
        except Exception as e:
            print(f"❌ [ONBOARD_BROADCAST] Error broadcasting job seeker {user_id}: {e}")
            import traceback

            traceback.print_exc()

    def broadcast_for_job_provider(self, user_id: str, extraction_data: Dict) -> None:
        """
        Broadcast a newly-onboarded job provider / founder to a small set of candidates.

        Called from the voice onboarding pipeline once all critical job provider
        fields are complete.
        """
        try:
            if self._already_broadcast(user_id, user_type="job_provider"):
                print(f"ℹ️ [ONBOARD_BROADCAST] Job provider {user_id} already broadcast – skipping")
                return

            user_profile = get_user_profile(user_id) or {}
            message, _ = self._build_job_provider_message(user_profile, extraction_data)
            if not message:
                print(f"⚠️ [ONBOARD_BROADCAST] Cannot build message for job provider {user_id}")
                return

            # Find 20 candidates for job provider (as per requirement)
            audience = self._find_candidate_audience_for_job_provider(
                job_provider_uid=user_id,
                job_provider_profile=user_profile,
                job_provider_extraction=extraction_data,
                limit=20,  # Job providers → 20 candidates
            )

            if not audience:
                print(f"ℹ️ [ONBOARD_BROADCAST] No audience found for job provider {user_id}")
                return

            # Get onboarding completion time
            onboarding_completed_at = user_profile.get("onboarding_completed_at") or time.time()
            
            # Always use template messages (as per requirement)
            sent_to = self._send_whatsapp_broadcast(
                message=message,
                audience=audience,
                broadcasted_user_id=user_id,
                broadcasted_user_name=user_profile.get("name", ""),
                connection_type="",
                onboarding_completed_at=onboarding_completed_at,
                always_use_template=True,  # Always use template messages
            )
            if not sent_to:
                print(f"⚠️ [ONBOARD_BROADCAST] No WhatsApp deliveries for job provider {user_id}")
                return

            self._mark_broadcast_sent(
                user_id=user_id,
                user_type="job_provider",
                audience_ids=sent_to,
                profile_link="",
            )
            print(
                f"✅ [ONBOARD_BROADCAST] Broadcast job provider {user_id} to {len(sent_to)} recipients"
            )
        except Exception as e:
            print(f"❌ [ONBOARD_BROADCAST] Error broadcasting job provider {user_id}: {e}")
            import traceback

            traceback.print_exc()

    def _find_job_providers_by_connection_type(self, connection_type: str, limit: int = 8) -> List[Dict]:
        """
        Find job providers/founders who might be interested in this connection type.
        Uses simple keyword matching on recent extractions.
        Ensures at least limit job providers are found, falling back to all job providers if needed.
        """
        try:
            # Search more broadly to find enough job providers
            docs = (
                fs.collection("extractions")
                .order_by("updated_at", direction=firestore.Query.DESCENDING)
                .limit(500)  # Increased from 100 to 500
                .stream()
            )

            audience: List[Dict] = []
            connection_lower = connection_type.lower()

            for doc in docs:
                uid = doc.id
                data = doc.to_dict() or {}
                if not self._looks_like_job_provider(data):
                    continue

                user_profile = get_user_profile(uid) or {}
                # Try multiple ways to get WhatsApp ID
                wa_id = (
                    user_profile.get("wa_id")
                    or user_profile.get("phone")
                    or user_profile.get("whatsapp")
                    or uid if uid.isdigit() and len(uid) >= 10 else ""
                )
                if not wa_id:
                    continue

                # Simple relevance: if connection_type mentions skills/roles they're hiring for
                job_title = str(data.get("job_title") or "").lower()
                required_skills = str(data.get("required_skills") or "").lower()
                
                score = 0
                if any(kw in connection_lower for kw in ["engineer", "developer", "full stack", "backend", "frontend"]):
                    if any(kw in job_title or kw in required_skills for kw in ["engineer", "developer", "full stack", "backend", "frontend"]):
                        score += 2  # Higher score for specific match
                else:
                    # If no specific match but they're a job provider, include them anyway
                    score = 0.5

                audience.append({
                    "uid": uid,
                    "wa_id": wa_id,
                    "name": user_profile.get("name", "Unknown"),
                    "score": score,
                })

            # If we don't have enough, search more broadly
            if len(audience) < limit:
                print(f"⚠️ [ONBOARD_BROADCAST] Only found {len(audience)} job providers, need {limit}. Searching more broadly...")
                all_docs = (
                    fs.collection("extractions")
                    .order_by("updated_at", direction=firestore.Query.DESCENDING)
                    .limit(1000)
                    .stream()
                )
                for doc in all_docs:
                    uid = doc.id
                    if any(a["uid"] == uid for a in audience):  # Skip if already added
                        continue
                    
                    data = doc.to_dict() or {}
                    if not self._looks_like_job_provider(data):
                        continue
                    
                    user_profile = get_user_profile(uid) or {}
                    wa_id = (
                        user_profile.get("wa_id")
                        or user_profile.get("phone")
                        or user_profile.get("whatsapp")
                        or uid if uid.isdigit() and len(uid) >= 10 else ""
                    )
                    if not wa_id:
                        continue
                    
                    audience.append({
                        "uid": uid,
                        "wa_id": wa_id,
                        "name": user_profile.get("name", "Unknown"),
                        "score": 0.1,  # Very low score for unmatched
                    })
                    
                    if len(audience) >= limit:
                        break

            audience.sort(key=lambda x: x.get("score", 0), reverse=True)
            trimmed = audience[:limit]
            print(f"ℹ️ [ONBOARD_BROADCAST] Found {len(audience)} total job providers, returning top {len(trimmed)}")
            return trimmed

        except Exception as e:
            print(f"❌ [ONBOARD_BROADCAST] Error finding job providers: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _find_candidates_by_connection_type(self, connection_type: str, limit: int = 10) -> List[Dict]:
        """
        Find candidates/job seekers who might be interested in this connection type.
        Uses simple keyword matching on recent extractions.
        Ensures at least limit candidates are found, falling back to all job seekers if needed.
        """
        try:
            # Search more broadly - scan more extractions to find enough candidates
            docs = (
                fs.collection("extractions")
                .order_by("updated_at", direction=firestore.Query.DESCENDING)
                .limit(500)  # Increased from 100 to 500 to find more candidates
                .stream()
            )

            audience: List[Dict] = []
            connection_lower = connection_type.lower()

            for doc in docs:
                uid = doc.id
                data = doc.to_dict() or {}
                if not self._looks_like_job_seeker(data):
                    continue

                user_profile = get_user_profile(uid) or {}
                # Try multiple ways to get WhatsApp ID
                wa_id = (
                    user_profile.get("wa_id")
                    or user_profile.get("phone")
                    or user_profile.get("whatsapp")
                    or uid  # Fallback to UID itself if it's a phone number
                    or ""
                )
                # If still no wa_id and uid looks like a phone number, use it
                if not wa_id and uid.isdigit() and len(uid) >= 10:
                    wa_id = uid

                if not wa_id:
                    continue

                # Match: extract role keywords from connection_type and match with candidate's target_role/skills
                # Example: "hiring full stack engineers" → match candidates with "full stack" in target_role
                target_role = str(data.get("target_role") or "").lower()
                core_skills = str(data.get("core_skills") or "").lower()
                
                score = 0
                # Extract role keywords from connection_type (e.g., "full stack", "engineer", "developer")
                role_keywords = ["engineer", "developer", "full stack", "backend", "frontend", "software", "python", "javascript", "react", "node"]
                for keyword in role_keywords:
                    if keyword in connection_lower:
                        if keyword in target_role or keyword in core_skills:
                            score += 2  # Higher score for specific match
                            break  # Only count once per keyword

                # If no specific match but they're a job seeker, include them anyway (broader match)
                if score == 0:
                    score = 0.5  # Lower score for general match

                audience.append({
                    "uid": uid,
                    "wa_id": wa_id,
                    "name": user_profile.get("name", "Unknown"),
                    "score": score,
                })

            # Sort by score, but ensure we have at least limit candidates
            audience.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # If we don't have enough candidates, try to get more by including lower-scored matches
            if len(audience) < limit:
                print(f"⚠️ [ONBOARD_BROADCAST] Only found {len(audience)} candidates, need {limit}. Searching more broadly...")
                # Get more job seekers without strict matching
                all_docs = (
                    fs.collection("extractions")
                    .order_by("updated_at", direction=firestore.Query.DESCENDING)
                    .limit(1000)
                    .stream()
                )
                for doc in all_docs:
                    uid = doc.id
                    if any(a["uid"] == uid for a in audience):  # Skip if already added
                        continue
                    
                    data = doc.to_dict() or {}
                    if not self._looks_like_job_seeker(data):
                        continue
                    
                    user_profile = get_user_profile(uid) or {}
                    wa_id = (
                        user_profile.get("wa_id")
                        or user_profile.get("phone")
                        or user_profile.get("whatsapp")
                        or uid if uid.isdigit() and len(uid) >= 10 else ""
                    )
                    if not wa_id:
                        continue
                    
                    audience.append({
                        "uid": uid,
                        "wa_id": wa_id,
                        "name": user_profile.get("name", "Unknown"),
                        "score": 0.1,  # Very low score for unmatched candidates
                    })
                    
                    if len(audience) >= limit:
                        break
                
                audience.sort(key=lambda x: x.get("score", 0), reverse=True)

            trimmed = audience[:limit]
            print(f"ℹ️ [ONBOARD_BROADCAST] Found {len(audience)} total candidates, returning top {len(trimmed)}")
            return trimmed

        except Exception as e:
            print(f"❌ [ONBOARD_BROADCAST] Error finding candidates: {e}")
            import traceback
            traceback.print_exc()
            return []

    # -------------------------------------------------------------------------
    # Core helpers
    # -------------------------------------------------------------------------

    def _check_text_onboarding_complete(self, user_id: str) -> bool:
        """
        Check if text onboarding is complete: connection_type/goal + name + email + linkedin.
        """
        user_profile = get_user_profile(user_id) or {}
        # Check for goal in multiple places: top-level, profile dict, or arbitrary field
        has_goal = bool(
            user_profile.get("goal") 
            or user_profile.get("primary_goal") 
            or user_profile.get("connection_type")
            or user_profile.get("profile", {}).get("goal")
            or user_profile.get("profile", {}).get("primary_goal")
            or user_profile.get("profile", {}).get("connection_type")
            or user_profile.get("arbitrary", {}).get("connection_type")
            or user_profile.get("arbitrary", {}).get("goal")
        )
        
        has_name = bool(user_profile.get("name") or user_profile.get("profile", {}).get("name"))
        has_email = bool(user_profile.get("email") or user_profile.get("profile", {}).get("email"))
        # Check both linkedin_url and linkedin (can be dict or string)
        linkedin = user_profile.get("linkedin_url") or user_profile.get("linkedin") or user_profile.get("profile", {}).get("linkedin_url")
        if isinstance(linkedin, dict):
            has_linkedin = bool(linkedin.get("linkedin_url") or linkedin.get("url"))
        else:
            has_linkedin = bool(linkedin)
        return has_goal and has_name and has_email and has_linkedin

    def _already_broadcast(self, user_id: str, user_type: str) -> bool:
        """Check idempotency: whether we've already broadcasted this user."""
        doc = fs.collection("onboarding_broadcasts").document(user_id).get()
        if not doc.exists:
            return False

        data = doc.to_dict() or {}
        existing_type = data.get("user_type")
        if existing_type and existing_type != user_type:
            # Different type recorded – we still consider it broadcasted once.
            return True

        return True

    def _mark_broadcast_sent(
        self,
        user_id: str,
        user_type: str,
        audience_ids: List[str],
        profile_link: str,
    ) -> None:
        """Persist broadcast metadata for observability + idempotency."""
        payload = {
            "user_type": user_type,
            "audience_ids": audience_ids,
            "sent_at": time.time(),
            "channel": "whatsapp",
            "profile_link": profile_link,
        }
        fs.collection("onboarding_broadcasts").document(user_id).set(payload, merge=True)

    # -------------------------------------------------------------------------
    # Message builders
    # -------------------------------------------------------------------------

    def _build_candidate_message(
        self, user_profile: Dict, extraction_data: Dict
    ) -> Tuple[str, str]:
        """
        Build the broadcast message for a candidate and return (message, profile_link).
        """
        name = user_profile.get("name") or extraction_data.get("name") or "this candidate"
        role = extraction_data.get("target_role") or user_profile.get("goal") or ""
        location = (
            extraction_data.get("current_location")
            or extraction_data.get("preferred_location")
            or ""
        )
        domain = (
            extraction_data.get("industry_background")
            or extraction_data.get("domain")
            or extraction_data.get("primary_domain")
            or ""
        )

        parts = [p for p in [role, location, domain] if p]
        if parts:
            role_need = " in ".join(parts)
        else:
            role_need = "their next role"

        slug = user_profile.get("slug") or extraction_data.get("slug") or ""
        profile_link = f"https://www.vance.so/{slug}" if slug else ""

        if profile_link:
            msg = (
                f"I just spoke with {name} — they're looking for {role_need}.\n"
                f"Profile: {profile_link}\n"
                f"Need an intro?"
            )
        else:
            msg = (
                f"I just spoke with {name} — they're looking for {role_need}.\n"
                f"Need an intro?"
            )
        return msg, profile_link

    def _build_job_provider_message(
        self, user_profile: Dict, extraction_data: Dict
    ) -> Tuple[str, str]:
        """
        Build the broadcast message for a job provider / founder.
        Returns (message, profile_link) but profile_link is currently unused.
        """
        name = (
            user_profile.get("name")
            or extraction_data.get("company_name")
            or "this founder"
        )

        role = extraction_data.get("job_title") or extraction_data.get("role") or ""
        location = (
            extraction_data.get("office_location")
            or extraction_data.get("preferred_location")
            or ""
        )
        domain = (
            extraction_data.get("industry")
            or extraction_data.get("domain")
            or extraction_data.get("company_stage")
            or ""
        )

        parts = [p for p in [role, location, domain] if p]
        if parts:
            role_need = " in ".join(parts)
        else:
            role_need = "great engineers"

        msg = (
            f"I just spoke with {name} — they're hiring for {role_need}.\n"
            f"Need an intro?"
        )
        return msg, ""

    # -------------------------------------------------------------------------
    # Audience selection
    # -------------------------------------------------------------------------

    def _find_job_provider_audience_for_candidate(
        self,
        candidate_uid: str,
        candidate_profile: Dict,
        candidate_extraction: Dict,
        limit: int = 10,  # Updated default: Job seekers → 10 job providers
    ) -> List[Dict]:
        """
        Find a small audience of job providers / founders to notify about a candidate.

        Strategy:
            - Scan recent `extractions` ordered by updated_at.
            - Keep only users with strong job provider indicators.
            - Prefer those whose location / domain roughly matches the candidate.
        """
        try:
            candidate_location = (
                candidate_extraction.get("current_location", "")
                or candidate_extraction.get("preferred_location", "")
            ).lower()
            candidate_role = (candidate_extraction.get("target_role", "") or "").lower()

            # Scan more extractions to find enough job providers (need 10)
            docs = (
                fs.collection("extractions")
                .order_by("updated_at", direction=firestore.Query.DESCENDING)
                .limit(500)  # Increased from 200 to find more job providers
                .stream()
            )

            audience: List[Dict] = []

            for doc in docs:
                uid = doc.id
                if uid == candidate_uid:
                    continue

                data = doc.to_dict() or {}
                if not self._looks_like_job_provider(data):
                    continue

                user_profile = get_user_profile(uid) or {}
                wa_id = (
                    user_profile.get("wa_id")
                    or user_profile.get("phone")
                    or user_profile.get("whatsapp")
                    or ""
                )
                if not wa_id:
                    continue

                # Basic heuristic matching on location / role keywords
                job_location = (
                    str(data.get("office_location") or data.get("preferred_location") or "")
                ).lower()
                job_role = (
                    str(data.get("job_title") or data.get("role") or "")
                ).lower()

                # If we have candidate role/location, prefer providers that match at least one
                score = 0
                if candidate_location and candidate_location in job_location:
                    score += 1
                if candidate_role and candidate_role.split(" ")[0] in job_role:
                    score += 1

                audience.append(
                    {
                        "uid": uid,
                        "wa_id": wa_id,
                        "score": score,
                    }
                )

            # Sort by heuristic score then keep top N
            audience.sort(key=lambda x: x.get("score", 0), reverse=True)
            trimmed = audience[:limit]

            print(
                f"ℹ️ [ONBOARD_BROADCAST] Selected {len(trimmed)} job providers for candidate {candidate_uid}"
            )
            return trimmed
        except Exception as e:
            print(f"❌ [ONBOARD_BROADCAST] Failed to select audience for candidate {candidate_uid}: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _find_candidate_audience_for_job_provider(
        self,
        job_provider_uid: str,
        job_provider_profile: Dict,
        job_provider_extraction: Dict,
        limit: int = 20,  # Updated default: Job providers → 20 candidates
    ) -> List[Dict]:
        """
        Find a small audience of candidates to notify about a new job provider.

        Strategy:
            - Scan recent `extractions` ordered by updated_at.
            - Keep only users with job seeker indicators.
            - Roughly match on target_role / location vs provider's job_title / office_location.
        """
        try:
            job_location = (
                job_provider_extraction.get("office_location", "")
                or job_provider_extraction.get("preferred_location", "")
                or ""
            ).lower()
            job_role = (
                job_provider_extraction.get("job_title", "")
                or job_provider_extraction.get("role", "")
                or ""
            ).lower()

            # Scan more extractions to find enough candidates (need 20)
            docs = (
                fs.collection("extractions")
                .order_by("updated_at", direction=firestore.Query.DESCENDING)
                .limit(500)  # Increased from 300 to find more candidates
                .stream()
            )

            audience: List[Dict] = []

            for doc in docs:
                uid = doc.id
                if uid == job_provider_uid:
                    continue

                data = doc.to_dict() or {}
                if not self._looks_like_job_seeker(data):
                    continue

                candidate_profile = get_user_profile(uid) or {}
                wa_id = (
                    candidate_profile.get("wa_id")
                    or candidate_profile.get("phone")
                    or candidate_profile.get("whatsapp")
                    or ""
                )
                if not wa_id:
                    continue

                candidate_location = (
                    str(data.get("current_location") or data.get("preferred_location") or "")
                ).lower()
                candidate_role = (
                    str(data.get("target_role") or data.get("role") or "")
                ).lower()

                score = 0
                if job_location and job_location in candidate_location:
                    score += 1
                if job_role and job_role.split(" ")[0] in candidate_role:
                    score += 1

                audience.append(
                    {
                        "uid": uid,
                        "wa_id": wa_id,
                        "score": score,
                    }
                )

            audience.sort(key=lambda x: x.get("score", 0), reverse=True)
            trimmed = audience[:limit]

            print(
                f"ℹ️ [ONBOARD_BROADCAST] Selected {len(trimmed)} candidates for job provider {job_provider_uid}"
            )
            return trimmed
        except Exception as e:
            print(
                f"❌ [ONBOARD_BROADCAST] Failed to select audience for job provider {job_provider_uid}: {e}"
            )
            import traceback

            traceback.print_exc()
            return []

    # -------------------------------------------------------------------------
    # WhatsApp sending
    # -------------------------------------------------------------------------

    def _send_whatsapp_broadcast(
        self, 
        message: str, 
        audience: List[Dict],
        broadcasted_user_id: str = "",
        broadcasted_user_name: str = "",
        connection_type: str = "",
        onboarding_completed_at: float = 0,
        always_use_template: bool = False,
    ) -> List[str]:
        """
        Send the prepared message to each audience member via WhatsApp.
        
        If always_use_template is True OR 24 hours have passed since onboarding completion, uses a template message.
        Template messages don't require the user to have messaged within 24 hours.

        Audience items must have keys: uid, wa_id.
        """
        sent_to: List[str] = []
        
        # Check if we should use template message
        # Always use template if always_use_template is True, otherwise check 24-hour window
        if always_use_template:
            use_template = True
            print(f"📋 [ONBOARD_BROADCAST] Using template message (always_use_template=True)")
        else:
            hours_since_onboarding = (time.time() - onboarding_completed_at) / 3600 if onboarding_completed_at > 0 else 0
            use_template = hours_since_onboarding >= 24
            if use_template:
                print(f"⏰ [ONBOARD_BROADCAST] 24+ hours since onboarding, using template message")

        for item in audience:
            uid = item.get("uid")
            wa_id = item.get("wa_id")
            if not wa_id:
                continue

            try:
                if use_template:
                    # Use template message (required after 24 hours)
                    # Template must be approved in WhatsApp Business Manager
                    # Template format should be: "I just spoke with {{1}} — they're looking to connect with {{2}}. Need an intro?"
                    # Template name: "onboarding_broadcast" (needs to be created/approved in Meta Business Manager)
                    template_name = "onboarding_broadcast"
                    try:
                        payload = MsgComponents.template_scaffold(
                            to=wa_id,
                            template_name=template_name,
                            language_code="en",
                            body_parameters=[broadcasted_user_name or "someone", connection_type or "connections"],
                        )
                    except Exception as template_error:
                        # Fallback to text if template fails (template might not exist yet)
                        print(f"⚠️ [ONBOARD_BROADCAST] Template '{template_name}' failed, falling back to text: {template_error}")
                        payload = MsgComponents.text_scaffold(to=wa_id, text=message)
                        use_template = False  # Update flag for logging
                else:
                    # Regular text message (within 24 hours)
                    payload = MsgComponents.text_scaffold(to=wa_id, text=message)
                
                result = self.sender.send(data=payload)
                sent_to.append(uid)
                msg_type = "template" if use_template else "text"
                print(
                    f"✅ [ONBOARD_BROADCAST] Sent {msg_type} onboarding broadcast to {uid} via WhatsApp (result={result})"
                )
            except Exception as e:
                print(
                    f"⚠️ [ONBOARD_BROADCAST] Failed sending onboarding broadcast to {uid}: {e}"
                )
                import traceback

                traceback.print_exc()

        return sent_to

    # -------------------------------------------------------------------------
    # Data-type heuristics
    # -------------------------------------------------------------------------

    def _looks_like_job_seeker(self, data: Dict) -> bool:
        """Heuristic: does this extraction doc look like a job seeker?"""
        return any(data.get(field) for field in self.JOB_SEEKER_INDICATORS)

    def _looks_like_job_provider(self, data: Dict) -> bool:
        """Heuristic: does this extraction doc look like a job provider / hiring user?"""
        return any(data.get(field) for field in self.JOB_PROVIDER_INDICATORS)


# Singleton instance
onboarding_broadcast_service = OnboardingBroadcastService()


