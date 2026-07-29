"""
Voice Extraction Service

Handles extraction, normalization, and persistence of user data from voice calls.
Supports three user types: general, job_seeker, job_provider.
"""

import json
import os
import re
import time
import uuid
from typing import Dict, List, Tuple

from anthropic import Anthropic

from utils.db import fs, get_extraction_data, get_user_profile
from utils.qdrant import Search
from utils.scrapingdog import ScrapingDogClient

# Field mappings for normalizing various input keys to standard fields
GENERAL_FIELD_MAPPING = {
    # Story variations
    "story": "the_story",
    "the_story": "the_story",
    "background": "the_story",
    "background_story": "the_story",
    "my_story": "the_story",
    "journey": "the_story",
    "experience": "the_story",
    "history": "the_story",
    # Current focus variations
    "current_focus": "current_focus",
    "focus": "current_focus",
    "currently_working": "current_focus",
    "working_on": "current_focus",
    "current_project": "current_focus",
    "main_focus": "current_focus",
    "primary_focus": "current_focus",
    "what_im_doing": "current_focus",
    # Priority variations
    "top_priority": "top_priorities",
    "top_priorities": "top_priorities",
    "priority": "top_priorities",
    "priorities": "top_priorities",
    "main_priority": "top_priorities",
    "primary_priority": "top_priorities",
    "most_important": "top_priorities",
    "key_priority": "top_priorities",
    "urgent_priority": "top_priorities",
    "immediate_priority": "top_priorities",
    # Vision variations
    "future_vision": "future_vision",
    "vision": "future_vision",
    "future_goals": "future_vision",
    "long_term_goals": "future_vision",
    "aspirations": "future_vision",
    "dreams": "future_vision",
    "where_i_see_myself": "future_vision",
    "future_plans": "future_vision",
    "roadmap": "future_vision",
    # Needs variations
    "urgent_needs": "urgent_needs",
    "needs": "urgent_needs",
    "immediate_needs": "urgent_needs",
    "current_needs": "urgent_needs",
    "what_i_need": "urgent_needs",
    "requirements": "urgent_needs",
    "challenges": "urgent_needs",
    "pain_points": "urgent_needs",
    "help_needed": "urgent_needs",
    "support_needed": "urgent_needs",
}

# Standard fields for each user type
GENERAL_FIELDS = [
    "the_story",
    "current_focus",
    "top_priorities",
    "future_vision",
    "urgent_needs",
]

JOB_SEEKER_FIELDS = [
    "target_role",
    "core_skills",
    "work_experience",
    "current_location",
    "relocation_openness",
    "work_model_preference",
    "notice_period",
    "salary_expectations",
    "role_type_preference",
    "qualifications",
    "industry_background",
    "key_projects",
    "employment_status",
    "job_search_urgency",
    "target_companies",
    "must_haves",
    "must_avoid",
    "motivations",
]

JOB_SEEKER_CRITICAL_FIELDS = [
    "target_role",
    "core_skills",
    "work_experience",
    "current_location",
    "work_model_preference",
]

JOB_PROVIDER_FIELDS = [
    "job_title",
    "role_description",
    "required_skills",
    "experience_level",
    "work_model",
    "office_location",
    "relocation_allowed",
    "salary_budget",
    "role_type",
    "qualifications",
    "industry_preference",
    "number_of_openings",
    "hiring_urgency",
    "interview_process",
    "equity_benefits",
    "company_culture",
    "ideal_candidate",
    "company_stage",
    "must_haves",
    "must_avoid",
    "flexibility",
]

JOB_PROVIDER_CRITICAL_FIELDS = [
    "job_title",
    "required_skills",
    "experience_level",
    "work_model",
    "salary_budget",
]


class VoiceExtractionService:
    """
    Service for handling voice call extraction data.

    Responsibilities:
    - Normalize field names from various input formats
    - Merge new data with existing extraction data
    - Save to Firestore
    - Track missing/complete fields
    """

    def handle_extraction(
        self, user_id: str, data: Dict, user_type: str, existing_data: Dict
    ) -> Dict:
        """
        Main entry point for processing extraction data.

        Args:
            user_id: User identifier
            data: Raw extraction data from voice call
            user_type: One of 'general', 'job_seeker', 'job_provider'
            existing_data: Previously saved extraction data

        Returns:
            Response dict with status, provided/missing fields, etc.
        """
        if user_type == "job_seeker":
            return self._handle_job_seeker(user_id, data, existing_data)
        elif user_type == "job_provider":
            return self._handle_job_provider(user_id, data, existing_data)
        else:
            return self._handle_general(user_id, data, existing_data)

    def get_status(self, user_id: str) -> Dict:
        """
        Get extraction completion status for a user.

        Returns:
            Status dict with completion percentage, missing fields, etc.
        """
        existing_data = get_extraction_data(user_id)

        missing_fields = [
            field
            for field in GENERAL_FIELDS
            if field not in existing_data or not existing_data.get(field)
        ]

        completion_percentage = (
            (len(GENERAL_FIELDS) - len(missing_fields)) / len(GENERAL_FIELDS)
        ) * 100

        return {
            "status": "success",
            "user_id": user_id,
            "extraction_data": existing_data,
            "standard_fields": GENERAL_FIELDS,
            "missing_fields": missing_fields,
            "completion_percentage": round(completion_percentage, 1),
            "all_fields_complete": len(missing_fields) == 0,
            "needs_clarification": len(missing_fields) > 0,
            "clarification_needed": (
                f"Missing fields: {', '.join(missing_fields)}"
                if missing_fields
                else None
            ),
        }

    def _handle_general(self, user_id: str, data: Dict, existing_data: Dict) -> Dict:
        """Handle extraction for general users (founders, entrepreneurs, etc.)."""
        print(f"🔵 [GENERAL] Processing general user extraction")

        normalized_data, provided_fields = self._normalize_fields(
            data, GENERAL_FIELD_MAPPING, GENERAL_FIELDS
        )

        merged_data = self._merge_data(existing_data, normalized_data, "GENERAL")
        missing_fields = self._get_missing_fields(merged_data, GENERAL_FIELDS)

        result = self._save_extraction(user_id, merged_data)
        print(f"✅ [GENERAL] {result}")

        response = {
            "status": "success",
            "message": result,
            "user_type": "general",
            "provided_fields": provided_fields,
            "missing_fields": missing_fields,
            "all_fields_complete": len(missing_fields) == 0,
        }

        if missing_fields:
            response["clarification_needed"] = (
                f"Missing fields: {', '.join(missing_fields)}"
            )
            print(f"🔍 [GENERAL] Agent should ask about: {missing_fields}")

        return response

    def _handle_job_seeker(self, user_id: str, data: Dict, existing_data: Dict) -> Dict:
        """Handle extraction for job seeker users."""
        print(f"🟢 [JOB_SEEKER] Processing job seeker extraction")

        # Job seekers use direct field matching (no mapping needed)
        normalized_data, provided_fields = self._extract_standard_fields(
            data, JOB_SEEKER_FIELDS
        )

        merged_data = self._merge_data(existing_data, normalized_data, "JOB_SEEKER")
        print(f"🔍 [Merged Data]: {merged_data}")

        missing_critical = self._get_missing_fields(
            merged_data, JOB_SEEKER_CRITICAL_FIELDS
        )
        missing_all = self._get_missing_fields(merged_data, JOB_SEEKER_FIELDS)

        result = self._save_extraction(user_id, merged_data)
        print(f"✅ [JOB_SEEKER] {result}")

        # When all critical fields are complete, create/update a searchable candidate profile
        if not missing_critical:
            try:
                self._sync_job_seeker_profile(user_id, merged_data)
            except Exception as e:
                # Non-fatal – profile sync failure shouldn't break extraction flow
                print(f"⚠️ [JOB_SEEKER_PROFILE] Failed to sync profile for {user_id}: {e}")
            # Note: Onboarding broadcast now happens after text onboarding completion,
            # not after voice call completion. See agent/tools/common.py

        response = {
            "status": "success",
            "message": result,
            "user_type": "job_seeker",
            "provided_fields": provided_fields,
            "missing_critical_fields": missing_critical,
            "missing_fields": missing_all,
            "all_critical_complete": len(missing_critical) == 0,
            "all_fields_complete": len(missing_all) == 0,
        }

        if missing_critical:
            response["clarification_needed"] = (
                f"Missing critical fields: {', '.join(missing_critical)}"
            )
            print(f"🔍 [JOB_SEEKER] Agent should prioritize: {missing_critical}")

        return response

    def _sync_job_seeker_profile(self, user_id: str, extraction_data: Dict) -> None:
        """
        Create or update a candidate profile for a job seeker when onboarding is complete.

        This makes the candidate discoverable for matching by storing:
        - A rich profile document in Firestore `user_profiles`
        - A vectorized profile in Qdrant `UserProfiles` collection
        """
        # Fetch core user info (name, email, linkedin) from primary user document
        user_profile = get_user_profile(user_id) or {}

        name = user_profile.get("name", "") or extraction_data.get("name", "")
        email = user_profile.get("email", "") or extraction_data.get("email", "")
        linkedin_url = user_profile.get("linkedin_url", "") or extraction_data.get(
            "linkedin_url", ""
        )

        # Attempt to fetch avatar from LinkedIn if we don't already have one
        avatar_url = (
            user_profile.get("avatar_url")
            or extraction_data.get("avatar_url")
            or self._fetch_avatar_from_linkedin(linkedin_url)
        )

        # Use Claude to generate high-signal narrative fields (story, strengths, proof, thoughts)
        high_signal = self._generate_high_signal_profile(
            user_id=user_id, name=name, extraction_data=extraction_data
        )

        # Generate or reuse a public slug for this user
        slug = self._ensure_public_slug(user_id=user_id, name=name)

        # Extract numbers from resume if available
        resume_url = user_profile.get("resume_url") or extraction_data.get("resume_url")
        if resume_url:
            try:
                from services.resume_number_extraction_service import (
                    resume_number_extraction_service,
                )

                extracted_numbers = (
                    resume_number_extraction_service.update_candidate_profile_with_numbers(
                        user_id=user_id, resume_url=resume_url
                    )
                )
                if extracted_numbers:
                    # Merge extracted numbers into extraction_data
                    numbers_dict = extracted_numbers.model_dump(exclude_none=True)
                    for key, value in numbers_dict.items():
                        if key not in extraction_data or not extraction_data.get(key):
                            extraction_data[key] = value
            except Exception as e:
                print(
                    f"⚠️ [JOB_SEEKER_PROFILE] Error extracting resume numbers for {user_id}: {e}"
                )

        now_ts = time.time()

        # Persist a canonical profile document in Firestore
        profile_doc = {
            "name": name,
            "email": email,
            "linkedin_url": linkedin_url,
            "avatar_url": avatar_url,
            "slug": slug,
            "extraction_data": extraction_data,
            "intent": "job_seeker_need",
            "updated_at": now_ts,
        }

        # Merge in high-signal fields if we generated them
        if high_signal:
            profile_doc.update(high_signal)

        fs.collection("user_profiles").document(user_id).set(profile_doc, merge=True)
        print(f"💾 [JOB_SEEKER_PROFILE] Stored Firestore profile for {user_id} (slug={slug})")

        # Prepare metadata for Qdrant – keep it minimal and focused
        metadata = {
            "name": name,
            "email": email,
            "linkedin_url": linkedin_url,
            "intent": "job_seeker_need",
            "avatar_url": avatar_url,
            "slug": slug,
        }

        # Use a deterministic UUID so repeated syncs overwrite the same logical point
        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        point_id = uuid.uuid5(namespace, f"user_profile_{user_id}").hex

        Search("UserProfiles").add(
            user_id=user_id,
            datalist=[
                {
                    "id": point_id,
                    "extraction_data": extraction_data,
                    "metadata": metadata,
                }
            ],
        )

        print(
            f"✅ [JOB_SEEKER_PROFILE] Synced candidate profile to Qdrant for {user_id} (slug={slug})"
        )

    def _ensure_public_slug(self, user_id: str, name: str) -> str:
        """
        Ensure the user has a unique, human-readable public slug.

        - Base slug is derived from name, lowercased and URL-safe.
        - On conflict, appends a short numeric suffix (-2, -3, ...).
        """
        # First, see if a slug already exists for this user
        try:
            existing = (
                fs.collection("public_profiles")
                .where("user_id", "==", user_id)
                .limit(1)
                .stream()
            )
            for doc in existing:
                data = doc.to_dict() or {}
                if data.get("user_id") == user_id:
                    return doc.id
        except Exception as e:
            print(f"⚠️ [PUBLIC_SLUG] Failed to query existing slug for {user_id}: {e}")

        # Derive base slug from name
        base = name.strip().lower() if name else ""
        if not base:
            # Fallback slug from user_id
            base = f"user-{user_id[-4:]}"

        # Keep only alphanumerics and spaces/hyphens, then collapse to hyphens
        base = re.sub(r"[^a-z0-9\s-]", "", base)
        base = re.sub(r"\s+", "-", base).strip("-")
        if not base:
            base = f"user-{user_id[-4:]}"

        slug = base
        suffix = 2

        while True:
            doc_ref = fs.collection("public_profiles").document(slug)
            doc = doc_ref.get()
            if not doc.exists:
                # Reserve this slug for the user
                now_ts = time.time()
                doc_ref.set(
                    {
                        "user_id": user_id,
                        "active": True,
                        "created_at": now_ts,
                        "updated_at": now_ts,
                    }
                )
                print(f"✅ [PUBLIC_SLUG] Assigned slug '{slug}' to user {user_id}")
                return slug

            data = doc.to_dict() or {}
            if data.get("user_id") == user_id:
                # Slug already mapped to this user
                return slug

            # Conflict: try next suffix
            slug = f"{base}-{suffix}"
            suffix += 1

    def _fetch_avatar_from_linkedin(self, linkedin_url: str) -> str:
        """
        Best-effort fetch of a profile picture URL from LinkedIn via ScrapingDog.
        Returns empty string on failure or missing config.
        """
        try:
            if not linkedin_url:
                return ""

            api_key = os.getenv("SCRAPINGDOG_API_KEY")
            profile_endpoint = os.getenv("SCRAPINGDOG_PROFILE_ENDPOINT")
            search_endpoint = os.getenv("SCRAPINGDOG_SEARCH_ENDPOINT", "https://api.scrapingdog.com/linkedin/search")

            if not api_key or not profile_endpoint:
                return ""

            client = ScrapingDogClient(
                api_key=api_key,
                search_endpoint=search_endpoint,
                profile_endpoint=profile_endpoint,
            )
            details = client.get_profile_details(linkedin_url)
            if not details:
                return ""

            # Try common keys for profile picture URL
            for key in ["profile_pic_url", "profilePictureUrl", "avatar_url", "profile_image"]:
                if details.get(key):
                    return str(details[key])

            return ""
        except Exception as e:
            print(f"⚠️ [AVATAR] Failed to fetch avatar from LinkedIn for {linkedin_url}: {e}")
            return ""

    def _generate_high_signal_profile(
        self, user_id: str, name: str, extraction_data: Dict
    ) -> Dict:
        """
        Use Claude to generate a high-signal narrative profile from raw extraction data.

        Returns a dict that can be merged into user_profiles, e.g.:
          {
            "story": str,
            "strengths": List[{"text": str, "hasAudio": bool}],
            "proofOfWork": List[{company, description, impact, link}],
            "thoughts": List[{content, topic}],
          }
        """
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return {}

            client = Anthropic(api_key=api_key)

            # Build a compact, readable view of extraction data for the prompt
            lines = []
            for key, value in extraction_data.items():
                if value and str(value).strip():
                    formatted_key = " ".join(word.capitalize() for word in key.split("_"))
                    text_value = str(value)
                    if len(text_value) > 350:
                        text_value = text_value[:347] + "..."
                    lines.append(f"- {formatted_key}: {text_value}")

            extraction_summary = "\n".join(lines)

            prompt = f"""
You are building a *founder-facing* candidate profile that must feel 10x sharper and more high-signal than a normal CV or LinkedIn.

Candidate name: {name or "Unknown"}

Below is everything we know about them from a structured onboarding call:

{extraction_summary}

Create a JSON object with these keys:
- "story": a 2–3 sentence, founder-friendly narrative that focuses on leverage, outcomes, and how they operate (not buzzwords).
- "strengths": an array of 4–6 bullet objects, each with:
    - "text": one sharp, specific strength or achievement written in first person or neutral tone.
    - "hasAudio": always false for now.
- "proofOfWork": an array of 3–5 items, each:
    - "company": short label for the context (company, product, project, or type of work).
    - "description": what they built/owned in 1 line.
    - "impact": one high-signal outcome (metric, before/after, or concrete result).
    - "link": empty string "" (we will backfill links later).
- "thoughts": an array of 2–3 short ideas they might share that reveal how they think about their craft, each with:
    - "content": the idea in 1–2 sentences.
    - "topic": short label for the theme (e.g. "Hiring", "Product velocity").

Rules:
- Be specific and concrete; avoid generic phrases like "hard-working" or "results-driven".
- Use information from the extraction data wherever possible; if something is unclear, make a sensible but realistic assumption.
- Keep everything concise and skimmable for a busy founder.

Return ONLY valid JSON, no markdown or commentary.
"""

            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=900,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            # Attempt to extract JSON if wrapped with extra text
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            if json_start != -1 and json_end != -1:
                raw = raw[json_start:json_end]

            data = json.loads(raw)

            story = str(data.get("story", "")).strip()
            strengths = data.get("strengths") or []
            proof = data.get("proofOfWork") or data.get("proof_of_work") or []
            thoughts = data.get("thoughts") or []

            # Basic shape enforcement
            def _norm_strength(s: Dict) -> Dict:
                return {
                    "text": str(s.get("text", "")).strip(),
                    "hasAudio": bool(s.get("hasAudio", False)),
                }

            def _norm_proof(p: Dict) -> Dict:
                return {
                    "company": str(p.get("company", "")).strip(),
                    "description": str(p.get("description", "")).strip(),
                    "impact": str(p.get("impact", "")).strip(),
                    "link": str(p.get("link", "") or "").strip(),
                }

            def _norm_thought(t: Dict) -> Dict:
                return {
                    "content": str(t.get("content", "")).strip(),
                    "topic": str(t.get("topic", "")).strip(),
                }

            strengths_norm = [
                _norm_strength(s) for s in strengths if isinstance(s, dict)
            ]
            proof_norm = [_norm_proof(p) for p in proof if isinstance(p, dict)]
            thoughts_norm = [
                _norm_thought(t) for t in thoughts if isinstance(t, dict)
            ]

            result: Dict = {}
            if story:
                result["story"] = story
            if strengths_norm:
                result["strengths"] = strengths_norm
            if proof_norm:
                result["proofOfWork"] = proof_norm
            if thoughts_norm:
                result["thoughts"] = thoughts_norm

            print(f"✅ [HIGH_SIGNAL] Generated high-signal profile pieces for {name or user_id}")
            return result

        except Exception as e:
            print(f"⚠️ [HIGH_SIGNAL] Failed to generate high-signal profile: {e}")
            return {}

    def _handle_job_provider(
        self, user_id: str, data: Dict, existing_data: Dict
    ) -> Dict:
        """Handle extraction for job provider users."""
        print(f"🟡 [JOB_PROVIDER] Processing job provider extraction")

        # Job providers use direct field matching (no mapping needed)
        normalized_data, provided_fields = self._extract_standard_fields(
            data, JOB_PROVIDER_FIELDS
        )

        merged_data = self._merge_data(existing_data, normalized_data, "JOB_PROVIDER")

        missing_critical = self._get_missing_fields(
            merged_data, JOB_PROVIDER_CRITICAL_FIELDS
        )
        missing_all = self._get_missing_fields(merged_data, JOB_PROVIDER_FIELDS)

        result = self._save_extraction(user_id, merged_data)
        print(f"✅ [JOB_PROVIDER] {result}")

        # Note: Onboarding broadcast now happens after text onboarding completion,
        # not after voice call completion. See agent/tools/common.py

        response = {
            "status": "success",
            "message": result,
            "user_type": "job_provider",
            "provided_fields": provided_fields,
            "missing_critical_fields": missing_critical,
            "missing_fields": missing_all,
            "all_critical_complete": len(missing_critical) == 0,
            "all_fields_complete": len(missing_all) == 0,
        }

        if missing_critical:
            response["clarification_needed"] = (
                f"Missing critical fields: {', '.join(missing_critical)}"
            )
            print(f"🔍 [JOB_PROVIDER] Agent should prioritize: {missing_critical}")

        return response

    def _normalize_fields(
        self, data: Dict, field_mapping: Dict, standard_fields: List[str]
    ) -> Tuple[Dict, List[str]]:
        """
        Normalize input fields using a mapping.

        Returns:
            Tuple of (normalized_data, list of provided fields)
        """
        normalized_data = {}
        provided_fields = []

        for key, value in data.items():
            if key == "user_type":
                continue
            if key in field_mapping:
                standard_field = field_mapping[key]
                normalized_data[standard_field] = value
                provided_fields.append(standard_field)
            elif key in standard_fields:
                normalized_data[key] = value
                provided_fields.append(key)

        return normalized_data, provided_fields

    def _extract_standard_fields(
        self, data: Dict, standard_fields: List[str]
    ) -> Tuple[Dict, List[str]]:
        """
        Extract only standard fields from input data (no mapping).

        Returns:
            Tuple of (extracted_data, list of provided fields)
        """
        extracted_data = {}
        provided_fields = []

        for key, value in data.items():
            if key == "user_type":
                continue
            if key in standard_fields and value and str(value).strip():
                extracted_data[key] = value
                provided_fields.append(key)

        return extracted_data, provided_fields

    def _merge_data(self, existing_data: Dict, new_data: Dict, log_prefix: str) -> Dict:
        """Merge new data into existing data."""
        merged = existing_data.copy()

        for key, value in new_data.items():
            if value and str(value).strip():
                merged[key] = value
                print(f"📝 [{log_prefix}_DIRECT] '{value}' → {key}")

        return merged

    def _get_missing_fields(self, data: Dict, required_fields: List[str]) -> List[str]:
        """Get list of missing/empty fields."""
        return [
            field
            for field in required_fields
            if field not in data or not data.get(field)
        ]

    def _save_extraction(self, user_id: str, data: Dict) -> str:
        """Save extraction data to Firestore."""
        try:
            update_data = {k: v for k, v in data.items() if v is not None}
            if not update_data:
                return "No data provided to save."

            # Track last-updated timestamp for downstream features (e.g. onboarding broadcasts)
            update_data["updated_at"] = time.time()

            fs.collection("extractions").document(user_id).set(update_data, merge=True)
            return f"Successfully saved extraction for {user_id}"
        except Exception as e:
            return f"Error saving extraction for {user_id}: {e}"


# Singleton instance
voice_extraction_service = VoiceExtractionService()
