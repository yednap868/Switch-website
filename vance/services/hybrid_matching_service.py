"""
Hybrid profile matching service for job providers.
Uses hard filters + vector search to pre-filter candidates, then Claude ranks them.
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from utils.db import get_extraction_data, get_user_profile
from utils.qdrant import Search, ensure_collections_exist


class JobProviderRequirements(BaseModel):
    """Structured job provider requirements extracted from voice call data."""

    job_title: str = Field(
        default="",
        description="The specific job title being hired for (e.g., 'Senior Python Developer', 'Product Manager')",
    )
    role_description: str = Field(
        default="",
        description="Brief description of what the role involves and day-to-day responsibilities",
    )
    required_skills: str = Field(
        default="",
        description="Comma-separated list of must-have technical skills and technologies",
    )
    experience_level: str = Field(
        default="",
        description="Required years of experience or seniority level (e.g., '3-5 years', 'Senior', 'Mid-level')",
    )
    work_model: str = Field(
        default="",
        description="Work arrangement: 'Remote', 'Hybrid', 'On-site', or specific details",
    )
    office_location: str = Field(
        default="", description="Office location or city where the role is based"
    )
    salary_budget: str = Field(
        default="",
        description="Salary range or budget for the role (e.g., '20-30 LPA', '$150k-$180k')",
    )
    hiring_urgency: str = Field(
        default="",
        description="How urgent is the hire: 'Immediate', 'Within 1 month', 'Flexible', etc.",
    )
    ideal_candidate: str = Field(
        default="",
        description="Description of the ideal candidate profile, soft skills, or cultural fit",
    )
    must_haves: str = Field(
        default="", description="Non-negotiable requirements that candidates must have"
    )
    must_avoid: str = Field(
        default="", description="Traits or backgrounds to avoid in candidates"
    )


class ExtractedCandidateDetails(BaseModel):
    """Details extracted from candidate profile during reranking."""

    target_role: str = Field(
        default="", description="Target job role the candidate is seeking"
    )
    core_skills: str = Field(
        default="", description="Comma-separated core technical skills"
    )
    work_experience: str = Field(
        default="", description="Years/description of work experience"
    )
    current_location: str = Field(default="", description="Current city/location")
    salary_expectations: str = Field(
        default="", description="Expected salary/compensation"
    )


class RankedCandidate(BaseModel):
    """A single ranked candidate with score and reasoning."""

    candidate_id: int = Field(description="Index of the candidate in the input list")
    compatibility_score: float = Field(
        ge=0.0, le=1.0, description="Compatibility score from 0.0 to 1.0"
    )
    match_reason: str = Field(
        description="Explanation of why this candidate is a good match"
    )
    extracted_details: ExtractedCandidateDetails = Field(
        default_factory=ExtractedCandidateDetails,
        description="Details extracted from profile_summary if structured fields were empty",
    )


class CandidateRankingResult(BaseModel):
    """Result of reranking candidates for a job."""

    ranked_candidates: list[RankedCandidate] = Field(
        default_factory=list,
        description="Candidates ranked by compatibility score descending",
    )


@dataclass
class MatchedProfile:
    """Represents a matched job seeker profile."""

    uid: str
    name: str
    email: str
    linkedin_url: str
    target_role: str
    core_skills: str
    work_experience: str
    current_location: str
    salary_expectations: str
    match_score: float
    match_reason: str
    extraction_data: Dict


class HybridMatchingService:
    """
    Service for hybrid profile matching using:
    1. LLM extraction (convert raw data to structured requirements)
    2. Hard filters (intent)
    3. Vector search (semantic similarity)
    4. LLM reranking (intelligent scoring)
    """

    # Model configuration
    MODEL_DEFAULT = "anthropic:claude-sonnet-4-20250514"  # Full capability
    MODEL_LIGHT = "anthropic:claude-3-5-haiku-20241022"  # Fast/cheap tasks

    # Field priorities for building search queries
    # Structured fields: (field_name, template) - template uses {value} placeholder
    STRUCTURED_FIELDS = [
        ("job_title", "Role: {value}"),
        ("required_skills", "Skills: {value}"),
        ("experience_level", "Experience: {value}"),
        ("office_location", "Location: {value}"),
        ("work_model", "Work Model: {value}"),
        ("role_description", None),  # No prefix, use raw value (truncated)
    ]

    # Unstructured fallback fields: (field_name, template) - used when no structured fields
    UNSTRUCTURED_FIELDS = [
        ("urgent_needs", None),  # Most specific for hiring needs
    ]

    # System prompt for extracting job provider requirements
    EXTRACTION_SYSTEM_PROMPT = """You are an expert HR assistant that extracts structured job requirements from conversational data.

You will receive raw extraction data from a voice call with a job provider (hiring manager/recruiter).
The data contains fields like: the_story, current_focus, top_priorities, future_vision, urgent_needs.

Your task is to extract structured job requirements from this conversational data.

Guidelines:
- Extract ONLY information that is explicitly mentioned or can be directly inferred
- For job_title: Look for specific role names (e.g., "hiring a senior engineer", "need a product manager")
- For required_skills: Extract technical skills, technologies, tools mentioned
- For experience_level: Look for years of experience or seniority mentions
- For work_model: Look for remote/hybrid/on-site preferences
- For office_location: Extract city or location mentions
- For salary_budget: Extract any compensation/salary/CTC mentions
- For hiring_urgency: Look for timeline mentions (immediate, ASAP, this quarter, etc.)
- Leave fields empty ("") if information is not available - DO NOT make up data
- Be concise and specific in extractions"""

    # System prompt for reranking candidates
    RERANKING_SYSTEM_PROMPT = """You are a professional recruiter matching job seekers to job openings.
Given job requirements and a list of candidates, rank the top candidates by compatibility.

Consider:
1. Skills match (required_skills vs core_skills OR infer from profile_summary)
2. Experience alignment (experience_level vs work_experience OR infer from profile_summary)
3. Location compatibility (office_location vs current_location OR relocation_openness)
4. Work model fit (work_model vs work_model_preference)
5. Salary alignment if both provided
6. If structured fields are empty, use "profile_summary" to infer skills and experience

IMPORTANT: Some candidates may have empty structured fields but contain a "profile_summary" field with their full profile text. Extract and fill in the missing details from this text.

For "extracted_details": Extract any missing information from the profile_summary. Only include fields you can confidently extract. Leave out fields you cannot determine.

Sort by compatibility_score descending. You MUST return at least 1 candidate if any are provided."""

    def __init__(self):
        # Initialize pydantic-ai agent for structured extraction
        self.extraction_agent = Agent(
            self.MODEL_DEFAULT,
            output_type=JobProviderRequirements,
            system_prompt=self.EXTRACTION_SYSTEM_PROMPT,
        )

        # Initialize pydantic-ai agent for candidate reranking
        self.reranking_agent = Agent(
            self.MODEL_DEFAULT,
            output_type=CandidateRankingResult,
            system_prompt=self.RERANKING_SYSTEM_PROMPT,
        )

    async def _extract_structured_requirements(
        self, raw_extraction_data: Dict
    ) -> JobProviderRequirements:
        """
        Convert raw voice call extraction data to structured job provider requirements.

        Args:
            raw_extraction_data: Raw extraction data with fields like the_story, urgent_needs, etc.

        Returns:
            JobProviderRequirements with structured fields
        """
        try:
            # Check if data already has structured fields (skip extraction)
            structured_fields = [
                "job_title",
                "required_skills",
                "experience_level",
                "office_location",
            ]
            has_structured_data = any(
                raw_extraction_data.get(field) for field in structured_fields
            )

            if has_structured_data:
                print(
                    "📋 [EXTRACTION] Data already has structured fields, using directly"
                )
                return JobProviderRequirements(
                    job_title=raw_extraction_data.get("job_title", ""),
                    role_description=raw_extraction_data.get("role_description", ""),
                    required_skills=raw_extraction_data.get("required_skills", ""),
                    experience_level=raw_extraction_data.get("experience_level", ""),
                    work_model=raw_extraction_data.get("work_model", ""),
                    office_location=raw_extraction_data.get("office_location", ""),
                    salary_budget=raw_extraction_data.get("salary_budget", ""),
                    hiring_urgency=raw_extraction_data.get("hiring_urgency", ""),
                    ideal_candidate=raw_extraction_data.get("ideal_candidate", ""),
                    must_haves=raw_extraction_data.get("must_haves", ""),
                    must_avoid=raw_extraction_data.get("must_avoid", ""),
                )

            # Format raw data for LLM extraction
            raw_text_parts = []
            for key, value in raw_extraction_data.items():
                if value and str(value).strip():
                    formatted_key = key.replace("_", " ").title()
                    raw_text_parts.append(f"{formatted_key}: {value}")

            raw_text = "\n".join(raw_text_parts)

            if not raw_text.strip():
                print("⚠️ [EXTRACTION] No raw data to extract from")
                return JobProviderRequirements()

            print(
                f"🤖 [EXTRACTION] Extracting structured requirements from raw data..."
            )

            # Use pydantic-ai agent for structured extraction (async)
            result = await self.extraction_agent.run(
                f"Extract job requirements from this hiring conversation data:\n\n{raw_text}"
            )

            extracted = result.output
            skills_preview = (
                extracted.required_skills[:50] if extracted.required_skills else ""
            )
            print(
                f"✅ [EXTRACTION] Extracted: job_title='{extracted.job_title}', skills='{skills_preview}...'"
            )

            return extracted

        except Exception as e:
            print(f"❌ [EXTRACTION] Error extracting structured requirements: {e}")
            # Return empty requirements on error
            return JobProviderRequirements()

    async def find_job_seeker_matches(
        self,
        job_provider_data: Dict,
        limit: int = 3,
        min_score: float = 0.6,
        job_provider_uid: Optional[str] = None,
    ) -> List[MatchedProfile]:
        """
        Main entry point - finds matching job seekers for a job provider.

        Args:
            job_provider_data: Extraction data from job provider's voice call
            limit: Number of matches to return (default 3)
            min_score: Minimum compatibility score (default 0.6)
            job_provider_uid: User ID of the job provider (to exclude from results)

        Returns:
            List of MatchedProfile objects
        """
        print(f"🔍 [HYBRID_MATCH] Starting job seeker matching for job provider")
        if job_provider_uid:
            print(
                f"🔍 [HYBRID_MATCH] Excluding job provider's own profile: {job_provider_uid}"
            )

        try:
            # Step 0: Extract structured requirements from raw data (async)
            structured_requirements = await self._extract_structured_requirements(
                job_provider_data
            )

            # Convert to dict for downstream use
            structured_data = structured_requirements.model_dump()
            # Merge with original data (structured takes precedence for non-empty fields)
            merged_data = {**job_provider_data}
            for key, value in structured_data.items():
                if value:  # Only override if extracted value is non-empty
                    merged_data[key] = value

            print(
                f"📋 [HYBRID_MATCH] Using structured requirements: {list(k for k, v in structured_data.items() if v)}"
            )

            # Step 1: Get target intent for filtering
            target_intent = self._get_target_intent()

            # Step 2: Execute hybrid search (vector search + manual filter)
            candidates = self._hybrid_search(
                merged_data,
                target_intent,
                pre_filter_limit=50,
                job_provider_uid=job_provider_uid,
            )

            if not candidates:
                print(f"⚠️ [HYBRID_MATCH] No candidates found, trying fallback search")
                candidates = self._fallback_search(
                    merged_data, job_provider_uid=job_provider_uid
                )

            if not candidates:
                print(f"❌ [HYBRID_MATCH] No candidates found even with fallback")
                return []

            print(
                f"✅ [HYBRID_MATCH] Found {len(candidates)} candidates, sending for reranking"
            )

            # Step 3: LLM reranking (use merged_data with structured requirements)
            ranked_profiles = await self._rerank_candidates(
                job_provider_data=merged_data,
                candidates=candidates,
                limit=limit,
                min_score=min_score,
            )

            if not ranked_profiles:
                print(f"⚠️ [HYBRID_MATCH] Reranking failed, using fallback ranking")
                ranked_profiles = self._fallback_ranking(candidates, limit)

            print(
                f"✅ [HYBRID_MATCH] Returning {len(ranked_profiles)} matched profiles"
            )
            return ranked_profiles

        except Exception as e:
            print(f"❌ [HYBRID_MATCH] Error in find_job_seeker_matches: {e}")
            raise

    def _get_target_intent(self) -> str:
        """
        Return the target intent for filtering job seekers.
        """
        return "job_seeker_need"

    def _build_search_query(self, job_provider_data: Dict) -> str:
        """
        Build semantic search query from job provider requirements.

        Uses a priority-based approach:
        1. Try structured fields first (job_title, required_skills, etc.)
        2. Fall back to unstructured fields (urgent_needs) if no structured data
        3. Return empty string if no data available (caller handles this)
        """
        parts = []
        query_source = None

        # Try structured fields first
        for field, template in self.STRUCTURED_FIELDS:
            value = job_provider_data.get(field)
            if value and str(value).strip():
                value_str = str(value)[:200]  # Truncate long values
                if template:
                    parts.append(template.format(value=value_str))
                else:
                    parts.append(value_str)
                if not query_source:
                    query_source = field

        # Fallback to unstructured fields if no structured data
        if not parts:
            for field, template in self.UNSTRUCTURED_FIELDS:
                value = job_provider_data.get(field)
                if value and str(value).strip():
                    value_str = str(value)[:300]  # Allow longer for unstructured
                    if template:
                        parts.append(template.format(value=value_str))
                    else:
                        parts.append(value_str)
                    query_source = field
                    break  # Use first non-empty unstructured field

        if not parts:
            print(
                "⚠️ [HYBRID_MATCH] No search query could be built - empty extraction data"
            )
            return ""

        query = " | ".join(parts)
        print(f"🔍 [HYBRID_MATCH] Search query (from {query_source}): {query[:100]}...")
        return query

    def _hybrid_search(
        self,
        job_provider_data: Dict,
        target_intent: str,
        pre_filter_limit: int = 50,
        job_provider_uid: str = None,
    ) -> List[Dict]:
        """
        Execute hybrid search: vector similarity + manual intent filtering.
        Uses the existing Search class from utils/qdrant.py.

        Args:
            job_provider_data: Job provider requirements
            target_intent: Intent to filter for (e.g., "job_seeker_need")
            pre_filter_limit: Max candidates to retrieve

        Returns:
            List of candidate profiles with scores
        """
        try:
            # Ensure Qdrant collections exist before searching
            ensure_collections_exist()

            # Build search query
            query_text = self._build_search_query(job_provider_data)

            if not query_text:
                print("❌ [HYBRID_MATCH] Cannot search: no query data available")
                return []

            all_candidates = []

            # Search UserProfiles collection using existing Search class
            try:
                profiles_search = Search("UserProfiles")
                # Get more results than needed since we'll filter by intent
                print(
                    f"🔍 [HYBRID_MATCH] Querying UserProfiles with: '{query_text[:100]}...' (limit={pre_filter_limit * 2})"
                )
                profiles_results = profiles_search.query(
                    query_text, limit=pre_filter_limit * 2
                )
                print(
                    f"🔍 [HYBRID_MATCH] Query returned {len(profiles_results)} raw results from UserProfiles"
                )

                for result in profiles_results:
                    candidate = self._extract_candidate_from_search_result(
                        result, target_intent, "UserProfiles"
                    )
                    if candidate:
                        all_candidates.append(candidate)

                print(
                    f"📊 [HYBRID_MATCH] Found {len(profiles_results)} from UserProfiles, {len([c for c in all_candidates if c.get('source') == 'UserProfiles'])} match intent"
                )

            except Exception as e:
                print(f"⚠️ [HYBRID_MATCH] UserProfiles search failed: {e}")

            # Search UserUrgentNeeds collection using existing Search class
            try:
                needs_search = Search("UserUrgentNeeds")
                needs_results = needs_search.query(
                    query_text, limit=pre_filter_limit * 2
                )

                for result in needs_results:
                    candidate = self._extract_candidate_from_search_result(
                        result, target_intent, "UserUrgentNeeds"
                    )
                    if candidate:
                        all_candidates.append(candidate)

                print(
                    f"📊 [HYBRID_MATCH] Found {len(needs_results)} from UserUrgentNeeds, {len([c for c in all_candidates if c.get('source') == 'UserUrgentNeeds'])} match intent"
                )

            except Exception as e:
                print(f"⚠️ [HYBRID_MATCH] UserUrgentNeeds search failed: {e}")

            # Deduplicate by user_id, keeping highest score, and exclude job provider's own profile
            seen_users = {}
            for candidate in all_candidates:
                uid = candidate.get("uid", "")
                # Skip job provider's own profile
                if job_provider_uid and uid == job_provider_uid:
                    print(
                        f"  ⚠️ [HYBRID_MATCH] Excluding job provider's own profile: {uid}"
                    )
                    continue
                if uid:
                    if uid not in seen_users or candidate.get(
                        "vector_score", 0
                    ) > seen_users[uid].get("vector_score", 0):
                        seen_users[uid] = candidate

            unique_candidates = list(seen_users.values())

            # Sort by vector score descending
            unique_candidates.sort(key=lambda x: x.get("vector_score", 0), reverse=True)

            print(
                f"✅ [HYBRID_MATCH] {len(unique_candidates)} unique candidates after dedup"
            )
            return unique_candidates[:pre_filter_limit]

        except Exception as e:
            print(f"❌ [HYBRID_MATCH] Hybrid search failed: {e}")
            return []

    def _extract_candidate_from_search_result(
        self, result: Dict, target_intent: str, source: str
    ) -> Optional[Dict]:
        """
        Extract candidate data from Search class result and filter by intent.

        Args:
            result: Result dict from Search.query() with keys: id, document, metadata, distance
            target_intent: Intent to filter for (e.g., "job_seeker_need")
            source: Source collection name

        Returns:
            Candidate dict if intent matches, None otherwise
        """
        try:
            metadata = result.get("metadata", {})

            # Check if intent matches (manual filtering)
            candidate_intent = metadata.get("intent", "")

            # Get extraction data to check for job seeker fields
            extraction_data = metadata.get("extraction_data", {})

            # If intent doesn't match, check if user has job seeker fields (fallback for "general" intent)
            if candidate_intent != target_intent:
                # For job seeker matching, also accept "general" intent if they have job seeker fields
                if target_intent == "job_seeker_need" and candidate_intent == "general":
                    # Check if user has job seeker indicators
                    has_job_seeker_fields = any(
                        extraction_data.get(field)
                        for field in [
                            "target_role",
                            "core_skills",
                            "work_experience",
                            "job_search_urgency",
                        ]
                    )
                    # Check document for job seeker keywords
                    doc_text = result.get("document", "") or metadata.get(
                        "document", ""
                    )
                    has_job_seeker_keywords = any(
                        kw in doc_text.lower()
                        for kw in [
                            "looking for a job",
                            "job seeker",
                            "seeking role",
                            "seeking job",
                            "applying for",
                            "target role",
                            "work experience",
                            "salary expectations",
                            "job references",
                            "seeking employment",
                            "looking for work",
                            "career change",
                            "new opportunity",
                        ]
                    )
                    # Check for job provider fields (exclude if they're clearly a job provider)
                    has_job_provider_fields = any(
                        extraction_data.get(field)
                        for field in [
                            "job_title",
                            "required_skills",
                            "hiring_urgency",
                            "company_culture",
                        ]
                    )

                    # Accept if has job seeker indicators and NOT job provider indicators
                    if (
                        has_job_seeker_fields or has_job_seeker_keywords
                    ) and not has_job_provider_fields:
                        print(
                            f"  ℹ️ [HYBRID_MATCH] Accepting 'general' intent user with job seeker fields: {metadata.get('name', 'Unknown')}"
                        )
                        # Continue processing - don't return None
                    else:
                        # Debug why user was rejected
                        if has_job_provider_fields:
                            print(
                                f"  ⚠️ [HYBRID_MATCH] Rejecting '{metadata.get('name', 'Unknown')}': has job provider fields"
                            )
                        elif not has_job_seeker_fields and not has_job_seeker_keywords:
                            print(
                                f"  ⚠️ [HYBRID_MATCH] Rejecting '{metadata.get('name', 'Unknown')}': no job seeker indicators"
                            )
                        return None  # Skip - not a job seeker
                else:
                    return None  # Skip candidates that don't match the target intent

            # Fallback: if extraction_data is empty, use document field
            document = result.get("document", "") or metadata.get("document", "")

            # Get email with Firestore fallback if missing from Qdrant
            email = metadata.get("email", "")
            if not email and metadata.get("user_id"):
                user_profile = get_user_profile(metadata.get("user_id"))
                ext_data = get_extraction_data(metadata.get("user_id"))
                email = user_profile.get("email", "") or ext_data.get("email", "")

            return {
                "uid": metadata.get("user_id", ""),
                "name": metadata.get("name", "Unknown"),
                "email": email,
                "linkedin_url": metadata.get("linkedin_url", ""),
                "target_role": extraction_data.get("target_role", ""),
                "core_skills": extraction_data.get("core_skills", ""),
                "work_experience": extraction_data.get("work_experience", ""),
                "current_location": extraction_data.get("current_location", ""),
                "relocation_openness": extraction_data.get("relocation_openness", ""),
                "salary_expectations": extraction_data.get("salary_expectations", ""),
                "work_model_preference": extraction_data.get(
                    "work_model_preference", ""
                ),
                "notice_period": extraction_data.get("notice_period", ""),
                "extraction_data": extraction_data,
                "document": document,  # Raw document for fallback
                "vector_score": result.get(
                    "distance", 0
                ),  # Search class returns 'distance' as score
                "source": source,
            }
        except Exception as e:
            print(f"⚠️ [HYBRID_MATCH] Failed to extract candidate: {e}")
            return None

    def _fallback_search(
        self, job_provider_data: Dict, limit: int = 30, job_provider_uid: str = None
    ) -> List[Dict]:
        """
        Fallback search with relaxed filters when primary search returns empty.
        Uses Search class with more results and filters by intent manually.
        """
        try:
            # Ensure Qdrant collections exist before searching
            ensure_collections_exist()

            query_text = self._build_search_query(job_provider_data)

            if not query_text:
                print(
                    "❌ [HYBRID_MATCH] Fallback cannot search: no query data available"
                )
                return []

            target_intent = self._get_target_intent()

            candidates = []

            # Search with larger limit using existing Search class
            profiles_search = Search("UserProfiles")
            results = profiles_search.query(
                query_text, limit=limit * 3
            )  # Get more to filter from

            for result in results:
                candidate = self._extract_candidate_from_search_result(
                    result, target_intent, "fallback"
                )
                if candidate:
                    # Skip job provider's own profile
                    if job_provider_uid and candidate.get("uid") == job_provider_uid:
                        continue
                    candidates.append(candidate)

            print(
                f"📊 [HYBRID_MATCH] Fallback found {len(candidates)} candidates (from {len(results)} results)"
            )
            return candidates[:limit]

        except Exception as e:
            print(f"❌ [HYBRID_MATCH] Fallback search failed: {e}")
            return []

    async def _rerank_candidates(
        self,
        job_provider_data: Dict,
        candidates: List[Dict],
        limit: int,
        min_score: float,
    ) -> List[MatchedProfile]:
        """
        Use LLM to intelligently rerank candidates based on mutual fit.
        Uses pydantic-ai for structured output.
        """
        if not candidates:
            return []

        try:
            # Prepare job provider context
            job_context = self._format_job_provider_context(job_provider_data)

            # Prepare candidates for reranking (limit to 20 for token efficiency)
            candidates_for_reranking = candidates[:20]
            candidates_json = []

            for i, candidate in enumerate(candidates_for_reranking):
                candidate_data = {
                    "id": i,
                    "name": candidate.get("name", "Unknown"),
                    "target_role": candidate.get("target_role", ""),
                    "core_skills": candidate.get("core_skills", ""),
                    "work_experience": candidate.get("work_experience", ""),
                    "current_location": candidate.get("current_location", ""),
                    "relocation_openness": candidate.get("relocation_openness", ""),
                    "salary_expectations": candidate.get("salary_expectations", ""),
                    "work_model_preference": candidate.get("work_model_preference", ""),
                    "notice_period": candidate.get("notice_period", ""),
                    "vector_score": round(candidate.get("vector_score", 0), 3),
                }
                # If extraction fields are empty, include raw profile document
                has_extraction_data = any(
                    [
                        candidate.get("target_role"),
                        candidate.get("core_skills"),
                        candidate.get("work_experience"),
                    ]
                )
                if not has_extraction_data and candidate.get("document"):
                    # Truncate document to save tokens
                    candidate_data["profile_summary"] = candidate.get("document", "")[
                        :500
                    ]
                candidates_json.append(candidate_data)

            prompt = f"""JOB REQUIREMENTS:
{job_context}

CANDIDATES (pre-filtered by semantic similarity):
{json.dumps(candidates_json, indent=2)}

TASK: Rank the top {limit} candidates that best match the job requirements.
Include candidates with compatibility_score >= {min_score}. If you cannot determine fit, assign a moderate score (0.5-0.7) based on vector_score."""

            # Use pydantic-ai agent for structured output
            result = await self.reranking_agent.run(prompt)
            ranking_result = result.output  # CandidateRankingResult - already validated

            print(
                f"🤖 [HYBRID_MATCH] Reranking returned {len(ranking_result.ranked_candidates)} candidates"
            )

            matched_profiles = []
            for rank in ranking_result.ranked_candidates[:limit]:
                if 0 <= rank.candidate_id < len(candidates_for_reranking):
                    candidate = candidates_for_reranking[rank.candidate_id]
                    extracted = rank.extracted_details

                    # Use extracted details to fill in missing fields
                    profile = MatchedProfile(
                        uid=candidate.get("uid", ""),
                        name=candidate.get("name", "Unknown"),
                        email=candidate.get("email", ""),
                        linkedin_url=candidate.get("linkedin_url", ""),
                        target_role=candidate.get("target_role")
                        or extracted.target_role,
                        core_skills=candidate.get("core_skills")
                        or extracted.core_skills,
                        work_experience=candidate.get("work_experience")
                        or extracted.work_experience,
                        current_location=candidate.get("current_location")
                        or extracted.current_location,
                        salary_expectations=candidate.get("salary_expectations")
                        or extracted.salary_expectations,
                        match_score=rank.compatibility_score,
                        match_reason=rank.match_reason,
                        extraction_data=candidate.get("extraction_data", {}),
                    )
                    matched_profiles.append(profile)

            print(f"✅ [HYBRID_MATCH] Reranked {len(matched_profiles)} profiles")
            return matched_profiles

        except Exception as e:
            print(f"❌ [HYBRID_MATCH] Reranking failed: {e}")
            return []

    def _format_job_provider_context(self, job_provider_data: Dict) -> str:
        """Format job provider data for Claude prompt."""
        lines = []

        field_labels = {
            "job_title": "Job Title",
            "role_description": "Role Description",
            "required_skills": "Required Skills",
            "experience_level": "Experience Required",
            "work_model": "Work Model",
            "office_location": "Office Location",
            "relocation_allowed": "Relocation Support",
            "salary_budget": "Salary Budget",
            "role_type": "Role Type",
            "qualifications": "Qualifications",
            "company_stage": "Company Stage",
            "hiring_urgency": "Hiring Urgency",
            "ideal_candidate": "Ideal Candidate",
            "must_haves": "Must Haves",
            "must_avoid": "Must Avoid",
        }

        for field, label in field_labels.items():
            value = job_provider_data.get(field)
            if (
                value
                and str(value).strip()
                and str(value).lower() not in ["n/a", "none", "null"]
            ):
                lines.append(f"- {label}: {value}")

        return "\n".join(lines) if lines else "No specific requirements provided"

    def _fallback_ranking(
        self, candidates: List[Dict], limit: int
    ) -> List[MatchedProfile]:
        """
        Fallback ranking using vector similarity scores when Claude fails.
        """
        try:
            # Sort by vector score
            sorted_candidates = sorted(
                candidates, key=lambda x: x.get("vector_score", 0), reverse=True
            )[:limit]

            profiles = []
            for candidate in sorted_candidates:
                profile = MatchedProfile(
                    uid=candidate.get("uid", ""),
                    name=candidate.get("name", "Unknown"),
                    email=candidate.get("email", ""),
                    linkedin_url=candidate.get("linkedin_url", ""),
                    target_role=candidate.get("target_role", ""),
                    core_skills=candidate.get("core_skills", ""),
                    work_experience=candidate.get("work_experience", ""),
                    current_location=candidate.get("current_location", ""),
                    salary_expectations=candidate.get("salary_expectations", ""),
                    match_score=candidate.get("vector_score", 0.0),
                    match_reason="Matched based on profile similarity",
                    extraction_data=candidate.get("extraction_data", {}),
                )
                profiles.append(profile)

            print(
                f"✅ [HYBRID_MATCH] Fallback ranked {len(profiles)} profiles by vector score"
            )
            return profiles

        except Exception as e:
            print(f"❌ [HYBRID_MATCH] Fallback ranking failed: {e}")
            return []


# Singleton instance
hybrid_matching_service = HybridMatchingService()
