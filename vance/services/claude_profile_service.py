"""
Claude-powered profile search service.
Uses Anthropic Claude API for intelligent profile matching based on intent classification.
"""

import json
import os
import re
import time as _time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from anthropic import Anthropic
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from utils.redis_client import (
    get_cache_key_for_business_context,
    get_cache_key_for_intent_classification,
    get_cache_key_for_profile_matches,
    redis_cache,
)


@dataclass
class ProfileMatch:
    """Represents a matched profile with Claude's reasoning."""

    uid: str
    name: str
    email: str
    profile_summary: str
    urgent_needs: str
    linkedin_url: str
    source: str
    intent: str
    compatibility_score: float
    match_reason: str


class TimeParseResult(BaseModel):
    """Structured result from time expression parsing."""

    type: Literal["absolute", "relative", "range", "ambiguous", "none"] = Field(
        description="Type of time expression"
    )
    start_time_utc: Optional[str] = Field(
        default=None, description="ISO formatted start time in UTC"
    )
    end_time_utc: Optional[str] = Field(
        default=None, description="ISO formatted end time in UTC (for ranges)"
    )
    tz: Optional[str] = Field(
        default=None, description="Best-guess IANA timezone"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score 0-1"
    )
    explanation: str = Field(
        default="", description="Brief explanation of the parsing"
    )


# Agent for parsing time expressions
_time_parse_agent = Agent(
    model="anthropic:claude-sonnet-4-20250514",
    output_type=TimeParseResult,
    system_prompt=(
        "You normalize free-text availability into a precise UTC time or window. "
        "Support expressions like 'in 15 min', '4-6 pm', 'tomorrow 10am', 'after 5', 'tonight'. "
        "Prefer the earliest reasonable moment if a window/range is given (use window start). "
        "If the expression is unclear, set type='ambiguous' and explain why."
    ),
)


class ClaudeProfileService:
    """Service for intelligent profile matching using Claude AI."""

    # Simple intent mappings for profile matching
    INTENT_MAPPINGS = {
        "job_provider": {"complementary_intents": ["job_seeker", "looking_for_job"]},
        "job_seeker": {"complementary_intents": ["job_provider", "hiring"]},
        "hiring": {"complementary_intents": ["job_seeker", "looking_for_job"]},
        "looking_for_job": {"complementary_intents": ["job_provider", "hiring"]},
        "investor": {"complementary_intents": ["founder", "fundraising"]},
        "founder": {"complementary_intents": ["investor", "advisor"]},
        "fundraising": {"complementary_intents": ["investor", "vc"]},
        "general": {"complementary_intents": []},
    }

    # Valid intents for classification
    VALID_INTENTS = set(INTENT_MAPPINGS.keys())

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-7-sonnet-20250219"  # Updated to 3.7 Sonnet

    def _call_claude_api(
        self, prompt: str, max_tokens: int = 150, temperature: float = 0.1
    ) -> str:
        """
        Internal method to call Claude API with consistent error handling.

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation

        Returns:
            Claude's response text
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"❌ [CLAUDE_API] Error calling Claude: {e}")
            raise e

    async def parse_time_expression(
        self,
        text: str,
        now_ts: Optional[float] = None,
        default_tz: Optional[str] = None,
    ) -> dict:
        """
        Parse a natural language time or range using Claude and return a normalized structure.

        Returns dict with keys:
          - type: "absolute" | "relative" | "range" | "ambiguous" | "none"
          - start_time_utc: ISO string or None
          - end_time_utc: ISO string or None
          - tz: best-guess IANA tz or provided default, else None
          - confidence: 0..1
          - explanation: brief note
        """
        # First, try simple pattern matching for common cases
        text_lower = text.lower().strip()

        # Handle "in X min" patterns
        min_match = re.search(r"in\s+(\d+)\s+min", text_lower)
        if min_match:
            minutes = int(min_match.group(1))
            future_time = (now_ts or _time.time()) + (minutes * 60)
            future_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(future_time))
            print(f"✅ [TIME_PARSE] Simple match: 'in {minutes} min' -> {future_iso}")
            return {
                "type": "relative",
                "start_time_utc": future_iso,
                "end_time_utc": None,
                "tz": "UTC",
                "confidence": 0.95,
                "explanation": f"{minutes} minutes from now",
            }

        # Handle "in X hours" patterns
        hour_match = re.search(r"in\s+(\d+)\s+(hour|hr)s?", text_lower)
        if hour_match:
            hours = int(hour_match.group(1))
            future_time = (now_ts or _time.time()) + (hours * 3600)
            future_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(future_time))
            print(f"✅ [TIME_PARSE] Simple match: 'in {hours} hours' -> {future_iso}")
            return {
                "type": "relative",
                "start_time_utc": future_iso,
                "end_time_utc": None,
                "tz": "UTC",
                "confidence": 0.95,
                "explanation": f"{hours} hours from now",
            }

        # Handle "X min" or "X minutes" without "in"
        min_match2 = re.search(r"^(\d+)\s+min", text_lower)
        if min_match2:
            minutes = int(min_match2.group(1))
            future_time = (now_ts or _time.time()) + (minutes * 60)
            future_iso = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(future_time))
            print(f"✅ [TIME_PARSE] Simple match: '{minutes} min' -> {future_iso}")
            return {
                "type": "relative",
                "start_time_utc": future_iso,
                "end_time_utc": None,
                "tz": "UTC",
                "confidence": 0.9,
                "explanation": f"{minutes} minutes from now",
            }

        # Handle "tomorrow" patterns
        if "tomorrow" in text_lower:
            tomorrow = (now_ts or _time.time()) + (24 * 3600)
            tomorrow_iso = _time.strftime(
                "%Y-%m-%dT09:00:00Z", _time.gmtime(tomorrow)
            )  # Default to 9 AM
            print(f"✅ [TIME_PARSE] Simple match: 'tomorrow' -> {tomorrow_iso}")
            return {
                "type": "absolute",
                "start_time_utc": tomorrow_iso,
                "end_time_utc": None,
                "tz": "UTC",
                "confidence": 0.8,
                "explanation": "tomorrow morning",
            }

        # If no simple match, fall back to pydantic-ai agent
        try:
            now_iso = _time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", _time.gmtime(now_ts or _time.time())
            )
            prompt = f"""Current UTC now: {now_iso}
Default timezone (if provided): {default_tz or 'unknown'}

User text: "{text}"

Parse this into a structured time result."""

            result = await _time_parse_agent.run(prompt)
            parsed = result.output.model_dump()
            print(f"✅ [TIME_PARSE] Parsed successfully: {parsed}")
            return parsed
        except Exception as e:
            print(f"❌ [TIME_PARSE] Error: {e}")
            return {
                "type": "none",
                "start_time_utc": None,
                "end_time_utc": None,
                "tz": default_tz,
                "confidence": 0.0,
                "explanation": str(e),
            }

    def _analyze_business_context(
        self, user_intent: str, user_urgent_needs: str
    ) -> str:
        """Analyze what the user actually wants and who can help them with Redis caching."""

        # Check Redis cache first
        cache_key = get_cache_key_for_business_context(user_intent, user_urgent_needs)
        cached_context = redis_cache.get(cache_key, str)

        if cached_context:
            print(f"🎯 [CACHE] Business context cache hit")
            return cached_context

        print(f"❌ [CACHE] Business context cache miss, generating analysis")

        context_map = {
            "capital_need": "User needs funding/investment. Look for: investors, VCs, angel investors who provide capital.",
            "investor_need": "User wants to invest/back companies. Look for: founders seeking funding, startups needing capital.",
            "hiring_need": "User wants to hire people. Look for: job seekers, candidates looking for work.",
            "job_seeker_need": "User is looking for a job. Look for: companies hiring, recruiters with opportunities.",
            "sales_need": "User wants to sell products/services. Look for: buyers, customers, decision makers.",
            "buyer_need": "User wants to buy/purchase. Look for: vendors, sellers, service providers.",
            "founder_need": "User seeks co-founders or business partners. Look for: potential co-founders, business partners.",
            "tech_partnership_need": "User needs technical partnerships. Look for: technical partners, integration opportunities.",
            "mentor_need": "User seeks mentorship. Look for: experienced mentors, advisors.",
            "freelancer_need": "User offers freelance services. Look for: companies needing freelance work.",
        }

        base_context = context_map.get(
            user_intent, "Analyze the user's needs and find complementary profiles."
        )

        # Add specific context from urgent needs
        urgent_analysis = f"User specifically said: '{user_urgent_needs}'"

        business_context = f"{base_context}\n\n{urgent_analysis}\n\nFocus on MUTUAL BENEFIT - find people who need what the user offers, or who can provide what the user needs."

        # Cache the result for 6 hours (21600 seconds)
        redis_cache.set(cache_key, business_context, ttl_seconds=21600)
        print(f"💾 [CACHE] Cached business context analysis")

        return business_context

    def classify_intent(self, urgent_need: str) -> str:
        """
        Classify urgent need text into structured intent using Claude with Redis caching.
        """
        # Validate input - ensure we have meaningful text
        if not urgent_need or len(urgent_need.strip()) < 3:
            print(f"⚠️ [CLAUDE] Input too short for classification: '{urgent_need}'")
            return "general"

        # Clean and prepare the input
        urgent_need = urgent_need.strip()

        # Check Redis cache first
        cache_key = get_cache_key_for_intent_classification(urgent_need)
        cached_intent = redis_cache.get(cache_key, str)

        if cached_intent:
            print(f"🎯 [CACHE] Intent classification cache hit: {cached_intent}")
            return cached_intent

        print(f"❌ [CACHE] Intent classification cache miss, calling Claude API")

        prompt = f"""
        Analyze this urgent need statement and classify it into exactly one of these intent categories:

        ===== HIRING CATEGORY =====
        - hiring_need: Companies/teams looking to hire employees (engineers, designers, PMs, analysts, etc.)
        - job_seeker_need: Individuals looking for employment opportunities or career changes
        - recruiter_need: Recruiters and talent acquisition professionals looking to place candidates
        - freelancer_need: Freelancers/contractors offering services or companies needing freelance work

        ===== SALES CATEGORY =====
        - sales_need: Companies/individuals looking to sell products, services, or generate revenue
        - buyer_need: Companies/individuals looking to purchase products, services, or tools
        - reseller_need: Companies looking to resell or distribute products through partnerships
        - end_user_need: Individuals/teams evaluating tools or products for personal/team use

        ===== PARTNERSHIP CATEGORY =====
        - founder_need: Founders/entrepreneurs looking for co-founders or business partners to start/join a company
        - tech_partnership_need: Companies looking for technical integrations, API partnerships, or platform integrations
        - distribution_need: Companies looking for distribution partners or market expansion opportunities
        - co_marketing_need: Companies looking for co-marketing, joint marketing, or brand partnership opportunities
        - community_need: Individuals/companies looking for community partners, event partners, or networking opportunities

        ===== FUNDRAISING CATEGORY =====
        - capital_need: Founders/startups seeking investment, funding, or capital to grow their business
        - investor_need: Investors, VCs, angels looking to invest in startups, back founders, or fund companies
        - mentor_need: Experienced professionals offering mentorship, advice, or guidance to entrepreneurs

        GENERAL:
        - general: Doesn't fit above categories

        Urgent need: "{urgent_need}"

        Respond with ONLY the intent name (e.g., "hiring_need", "sales_need", etc.).
        """

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )

            intent = response.content[0].text.strip().lower()
            # Validate intent exists in our mappings
            if intent in self.VALID_INTENTS:
                # Cache the result for 6 hours (21600 seconds)
                redis_cache.set(cache_key, intent, ttl_seconds=21600)
                print(f"💾 [CACHE] Cached intent classification: {intent}")
                return intent
            else:
                print(f"⚠️ [CLAUDE] Invalid intent '{intent}', using 'general'")
                # Cache the fallback result
                redis_cache.set(cache_key, "general", ttl_seconds=21600)
                return "general"

        except Exception as e:
            print(f"❌ [CLAUDE] Intent classification failed: {e}")
            return "general"

    def should_send_profiles_to_user(self, extraction_data: dict) -> tuple[bool, str]:
        """
        Dynamically decide if user should receive candidate profiles post-call.

        Uses LLM to analyze extraction data and determine if user is actively hiring.
        Only job providers (those hiring) should receive matched candidate profiles.

        Returns:
            Tuple of (should_send: bool, reason: str)
        """
        if not extraction_data:
            return False, "No extraction data available"

        # Build context text from extraction data
        context_parts = []
        for key, value in extraction_data.items():
            if value and str(value).strip():
                context_parts.append(f"{key}: {value}")

        extraction_text = "\n".join(context_parts)

        if not extraction_text.strip():
            return False, "Empty extraction data"

        # Check Redis cache first
        import hashlib

        cache_key = (
            f"profile_decision:{hashlib.md5(extraction_text.encode()).hexdigest()[:16]}"
        )
        cached = redis_cache.get(cache_key, dict)
        if cached:
            print(f"🎯 [CACHE] Profile decision cache hit")
            return cached.get("should_send", False), cached.get("reason", "cached")

        print(f"❌ [CACHE] Profile decision cache miss, calling Claude API")

        prompt = f"""Analyze this user's data from a voice call and determine if they should receive candidate profiles (job seeker matches).

User Data:
{extraction_text}

A user should ONLY receive candidate profiles if ALL of these are true:
1. They are actively HIRING (looking for employees/candidates)
2. They have a specific job role or position to fill
3. They are in a position to make or influence hiring decisions

A user should NOT receive candidate profiles if:
- They are looking for a JOB themselves (job seeker)
- They are looking for investment/funding
- They are looking for clients/sales
- Their intent is unclear or general networking

Respond with EXACTLY this JSON format (no other text):
{{"should_send": true, "reason": "brief explanation"}}
OR
{{"should_send": false, "reason": "brief explanation"}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,  # Increased from 100 to handle longer reasons
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Parse JSON response
            import json
            import re

            # Try to find JSON object in response (handle cases where response has extra text)
            # Also handle malformed responses with parentheses instead of braces
            json_match = re.search(r"\{[^{}]*\"should_send\"[^{}]*\"reason\"[^{}]*\}", response_text, re.DOTALL)
            if not json_match:
                # Try with parentheses (malformed response)
                json_match = re.search(r"\([^()]*\"should_send\"[^()]*\"reason\"[^()]*\)", response_text, re.DOTALL)
                if json_match:
                    # Convert parentheses to braces for JSON parsing
                    json_str = json_match.group(0).replace("(", "{").replace(")", "}")
                    json_match = type('obj', (object,), {'group': lambda x: json_str})()
            if not json_match:
                # Fallback: try to find any JSON object
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            
            if json_match:
                try:
                    json_str = json_match.group(0)
                    # Try to fix common JSON issues (unclosed strings, etc.)
                    # If response was truncated, try to close the JSON
                    if not json_str.strip().endswith("}"):
                        # Try to extract what we can
                        if '"should_send"' in json_str and '"reason"' in json_str:
                            # Extract should_send value
                            should_send_match = re.search(r'"should_send"\s*:\s*(true|false)', json_str, re.IGNORECASE)
                            reason_match = re.search(r'"reason"\s*:\s*"([^"]*)', json_str)
                            
                            if should_send_match:
                                should_send = should_send_match.group(1).lower() == "true"
                                reason = reason_match.group(1) if reason_match else "Parsed from truncated response"
                                
                                # Cache for 6 hours
                                redis_cache.set(
                                    cache_key,
                                    {"should_send": should_send, "reason": reason},
                                    ttl_seconds=21600,
                                )
                                print(
                                    f"💾 [CACHE] Cached profile decision (from truncated): should_send={should_send}, reason={reason[:100]}"
                                )
                                return should_send, reason
                    
                    result = json.loads(json_str)
                    should_send = result.get("should_send", False)
                    reason = result.get("reason", "")

                    # Cache for 6 hours
                    redis_cache.set(
                        cache_key,
                        {"should_send": should_send, "reason": reason},
                        ttl_seconds=21600,
                    )
                    print(
                        f"💾 [CACHE] Cached profile decision: should_send={should_send}, reason={reason[:100]}"
                    )

                    return should_send, reason
                except json.JSONDecodeError as e:
                    print(f"⚠️ [PROFILE_DECISION] JSON decode error: {e}, response: {response_text[:200]}")
                    # Fallback: if response contains "should_send": true, assume true
                    if '"should_send": true' in response_text.lower() or '"should_send":true' in response_text.lower():
                        reason = "Parsed from response (JSON decode failed but found should_send: true)"
                        redis_cache.set(cache_key, {"should_send": True, "reason": reason}, ttl_seconds=21600)
                        return True, reason
                    return False, "Failed to parse JSON"
            else:
                print(f"⚠️ [PROFILE_DECISION] Could not parse response: {response_text[:200]}")
                # Fallback: if response clearly indicates hiring, return true
                hiring_indicators = ["hiring", "recruit", "looking for", "need", "position", "role"]
                if any(indicator in response_text.lower() for indicator in hiring_indicators):
                    reason = "Parsed from response text (hiring indicators found)"
                    redis_cache.set(cache_key, {"should_send": True, "reason": reason}, ttl_seconds=21600)
                    return True, reason
                return False, "Failed to parse decision"

        except Exception as e:
            print(f"❌ [PROFILE_DECISION] Error: {e}")
            return False, f"Decision error: {str(e)}"

    # Updated find_profile_matches method in claude_profile_service.py
    def find_profile_matches_with_context(
        self,
        user_intent: str,
        user_context: Dict[str, str],  # Complete extraction data
        available_profiles: List[Dict],
        user_profile_summary: Optional[str] = None,
        limit: int = 3,
    ) -> List[ProfileMatch]:
        """
        Use Claude to find and rank compatible profiles using complete user context with Redis caching.
        """
        if not available_profiles:
            return []

        # Check Redis cache first with context-aware key
        cache_key = self.get_cache_key_for_profile_matches_with_context(
            user_intent, user_context, available_profiles, user_profile_summary
        )
        cached_matches = redis_cache.get(cache_key, list)

        if cached_matches:
            print(
                f"🎯 [CACHE] Profile matches cache hit: {len(cached_matches)} matches"
            )
            # Convert cached data back to ProfileMatch objects
            profile_matches = []
            for match_data in cached_matches:
                profile_id = match_data.get("profile_id")
                if profile_id is not None and 0 <= profile_id < len(available_profiles):
                    original_profile = available_profiles[profile_id]
                    match = ProfileMatch(
                        uid=original_profile.get("uid", ""),
                        name=original_profile.get("name", "Unknown"),
                        email=original_profile.get("email", ""),
                        profile_summary=original_profile.get("profile_summary", ""),
                        urgent_needs=original_profile.get("urgent_needs", ""),
                        linkedin_url=original_profile.get("linkedin_url", ""),
                        source=original_profile.get("source", "claude_match"),
                        intent=original_profile.get("intent", "general"),
                        compatibility_score=match_data.get("compatibility_score", 0.0),
                        match_reason=match_data.get("match_reason", ""),
                    )
                    profile_matches.append(match)
            return profile_matches[:limit]

        print(f"❌ [CACHE] Profile matches cache miss, calling Claude API")

        # Get complementary intents
        complementary_intents = self.INTENT_MAPPINGS.get(user_intent, {}).get(
            "complementary_intents", []
        )

        # Prepare profiles data for Claude (consider up to 200 profiles)
        profiles_data = []
        for i, profile in enumerate(available_profiles[:200]):
            profile_entry = {
                "id": i,
                "name": profile.get("name", "Unknown"),
                "intent": profile.get("intent", "general"),
            }

            # NEW: Include ALL extraction data dynamically
            if "extraction_data" in profile and isinstance(
                profile["extraction_data"], dict
            ):
                # Include complete extraction data (truncate long values)
                profile_entry["extraction_data"] = {}
                for key, value in profile["extraction_data"].items():
                    if value:
                        value_str = str(value).strip()
                        if value_str and value_str.lower() not in [
                            "n/a",
                            "none",
                            "null",
                            "",
                        ]:
                            # Truncate to 300 chars per field
                            profile_entry["extraction_data"][key] = value_str[:300]

            # Fallback: use profile_summary if no extraction data
            if not profile_entry.get("extraction_data"):
                profile_entry["profile_summary"] = profile.get("profile_summary", "")[
                    :500
                ]

            profiles_data.append(profile_entry)

        # Build comprehensive user profile context from ALL extraction data dynamically
        user_profile_section = "USER COMPLETE PROFILE:\n"
        user_profile_section += f"- Intent: {user_intent}\n"

        # Add all key-value pairs from user_context dynamically
        for key, value in user_context.items():
            if value and str(value).strip() and str(value).lower() != "n/a":
                # Format key nicely (convert snake_case to Title Case)
                formatted_key = " ".join(word.capitalize() for word in key.split("_"))
                # Truncate very long values
                formatted_value = (
                    str(value)[:500] if len(str(value)) > 500 else str(value)
                )
                user_profile_section += f"- {formatted_key}: {formatted_value}\n"

        if user_profile_summary and user_profile_summary.strip():
            user_profile_section += f"\n- Additional Context: {user_profile_summary}"

        # Analyze business context with full user information
        business_context = self._analyze_business_context_with_full_data(
            user_intent, user_context
        )

        # Update the prompt to Claude
        prompt = f"""
        You are a business networking expert who understands complementary needs and mutual benefit.

        USER COMPLETE PROFILE:
        - Intent: {user_intent}

        USER EXTRACTION DATA (ALL FIELDS):
        {json.dumps(user_context, indent=2)}

        {user_profile_section if user_profile_summary else ""}

        BUSINESS CONTEXT ANALYSIS:
        {business_context}

        MATCHING PHILOSOPHY:
        Find profiles where there's MUTUAL BENEFIT based on COMPLETE USER EXTRACTION DATA - consider ALL fields dynamically.

        AVAILABLE PROFILES TO ANALYZE (with their complete extraction data):
        {json.dumps(profiles_data, indent=2)}

        TASK: Find the top {limit} profiles that create the best MUTUAL VALUE considering ALL extraction data fields from both user and profiles.

        Important: 
        - Analyze ALL fields in extraction_data dynamically (don't expect fixed fields)
        - Match based on complementary information found in any extraction fields
        - Reference specific field names and values in your match_reason
        - Consider the complete context, not just individual fields

        Respond with a JSON object containing:
        {{
            "matches": [
                {{
                    "profile_id": 0,
                    "compatibility_score": 0.95,
                    "match_reason": "Detailed explanation referencing specific extraction data fields and their values that create mutual benefit."
                }}
            ]
        }}

        Only include profiles with compatibility_score >= 0.7.
        Sort by compatibility_score descending.
        """

        # Try with reduced response size first, then retry with smaller limits if needed
        max_retries = 3
        current_limit = limit

        for attempt in range(max_retries):
            try:
                max_tokens = min(
                    2000, 1000 + (current_limit * 150)
                )  # Increased for richer explanations

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}],
                )

                result_text = response.content[0].text.strip()

                try:
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1

                    if json_start != -1 and json_end != -1:
                        json_str = result_text[json_start:json_end]
                        json_str = self._fix_common_json_issues(json_str)
                        result_data = json.loads(json_str)
                    else:
                        result_data = json.loads(result_text)

                    matches_data = result_data.get("matches", [])

                    # Convert to ProfileMatch objects
                    profile_matches = []
                    for match_data in matches_data[:current_limit]:
                        profile_id = match_data.get("profile_id")
                        if profile_id is not None and 0 <= profile_id < len(
                            available_profiles
                        ):
                            original_profile = available_profiles[profile_id]

                            match = ProfileMatch(
                                uid=original_profile.get("uid", ""),
                                name=original_profile.get("name", "Unknown"),
                                email=original_profile.get("email", ""),
                                profile_summary=original_profile.get(
                                    "profile_summary", ""
                                ),
                                urgent_needs=original_profile.get("urgent_needs", ""),
                                linkedin_url=original_profile.get("linkedin_url", ""),
                                source=original_profile.get("source", "claude_match"),
                                intent=original_profile.get("intent", "general"),
                                compatibility_score=match_data.get(
                                    "compatibility_score", 0.0
                                ),
                                match_reason=match_data.get("match_reason", ""),
                            )
                            profile_matches.append(match)

                    print(
                        f"✅ [CLAUDE] Found {len(profile_matches)} compatible matches using full context"
                    )

                    # Cache the results for 6 hours
                    cache_data = []
                    for match_data in matches_data[:current_limit]:
                        cache_data.append(
                            {
                                "profile_id": match_data.get("profile_id"),
                                "compatibility_score": match_data.get(
                                    "compatibility_score", 0.0
                                ),
                                "match_reason": match_data.get("match_reason", ""),
                            }
                        )

                    redis_cache.set(cache_key, cache_data, ttl_seconds=21600)
                    print(
                        f"💾 [CACHE] Cached {len(cache_data)} profile matches with context"
                    )

                    return profile_matches

                except json.JSONDecodeError as e:
                    print(
                        f"❌ [CLAUDE] JSON parsing failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )

                    partial_matches = self._extract_partial_matches(
                        result_text, available_profiles, current_limit
                    )
                    if partial_matches:
                        print(
                            f"✅ [CLAUDE] Extracted {len(partial_matches)} partial matches"
                        )
                        return partial_matches

                    if attempt == max_retries - 1:
                        print(f"Response: {result_text[:500]}...")
                        return []

                    current_limit = max(3, current_limit // 2)
                    print(f"🔄 [CLAUDE] Retrying with reduced limit: {current_limit}")
                    prompt = prompt.replace(f"top {limit}", f"top {current_limit}")

            except Exception as e:
                print(
                    f"❌ [CLAUDE] Request failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt == max_retries - 1:
                    return []

                import time

                time.sleep(2**attempt)
                current_limit = max(3, current_limit // 2)
                print(f"🔄 [CLAUDE] Retrying with reduced limit: {current_limit}")
                prompt = prompt.replace(f"top {limit}", f"top {current_limit}")

        return []

    def _analyze_business_context_with_full_data(
        self, user_intent: str, user_context: Dict[str, str]
    ) -> str:
        """
        Analyze business context using ALL user extraction data dynamically.
        """
        context_parts = []

        # Priority fields for business context (if they exist)
        priority_fields = [
            "the_story",
            "background",
            "current_focus",
            "challenges",
            "goals",
            "objectives",
            "urgent_needs",
            "resources_needed",
            "timeline",
            "stage",
            "industry",
            "company",
            "role",
        ]

        # Add priority fields first
        for field in priority_fields:
            if field in user_context and user_context[field]:
                value = str(user_context[field])
                if value.strip() and value.lower() != "n/a":
                    formatted_key = " ".join(
                        word.capitalize() for word in field.split("_")
                    )
                    # Truncate long values for context
                    formatted_value = value[:200] + "..." if len(value) > 200 else value
                    context_parts.append(f"{formatted_key}: {formatted_value}")

        # Add any remaining fields not in priority list
        for key, value in user_context.items():
            if key not in priority_fields and value:
                value_str = str(value)
                if value_str.strip() and value_str.lower() != "n/a":
                    formatted_key = " ".join(
                        word.capitalize() for word in key.split("_")
                    )
                    formatted_value = (
                        value_str[:200] + "..." if len(value_str) > 200 else value_str
                    )
                    context_parts.append(f"{formatted_key}: {formatted_value}")

        return (
            "\n".join(context_parts) if context_parts else "Limited context available"
        )

    # Helper function for cache key generation with full context
    def get_cache_key_for_profile_matches_with_context(
        self,
        user_intent: str,
        user_context: Dict[str, str],
        available_profiles: List[Dict],
        user_profile_summary: Optional[str] = None,
    ) -> str:
        """Generate cache key for profile matches using complete context."""
        import hashlib

        # Create a stable representation of ALL context data
        # Sort keys to ensure consistent hashing regardless of dict order
        context_str = json.dumps(user_context, sort_keys=True)

        # Hash the profiles
        profile_ids = [p.get("uid", "") for p in available_profiles[:50]]
        profiles_hash = hashlib.md5(
            json.dumps(profile_ids, sort_keys=True).encode()
        ).hexdigest()[:8]

        # Hash the complete context
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:12]

        return f"profile_matches:v3:{user_intent}:{context_hash}:{profiles_hash}"

    def _fix_common_json_issues(self, json_str: str) -> str:
        """Fix common JSON issues that cause parsing errors."""
        try:
            # Remove trailing commas before closing brackets/braces
            import re

            json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)

            # Fix unclosed strings
            json_str = re.sub(r'"([^"]*)$', r'"\1"', json_str)

            # Fix missing closing brackets/braces
            open_braces = json_str.count("{")
            close_braces = json_str.count("}")
            open_brackets = json_str.count("[")
            close_brackets = json_str.count("]")

            # Add missing closing brackets
            if open_brackets > close_brackets:
                json_str += "]" * (open_brackets - close_brackets)

            # Add missing closing braces
            if open_braces > close_braces:
                json_str += "}" * (open_braces - close_braces)

            return json_str

        except Exception as e:
            print(f"⚠️ [CLAUDE] JSON fix failed: {e}")
            return json_str

    def _extract_partial_matches(
        self, result_text: str, available_profiles: list, limit: int
    ) -> list:
        """Extract partial matches from incomplete JSON response."""
        try:
            import re
            from dataclasses import dataclass

            # Find all profile_id patterns in the response
            profile_pattern = r'"profile_id":\s*(\d+)'
            score_pattern = r'"compatibility_score":\s*([\d.]+)'
            reason_pattern = r'"match_reason":\s*"([^"]*(?:\\.[^"]*)*)"'

            profile_ids = re.findall(profile_pattern, result_text)
            scores = re.findall(score_pattern, result_text)
            reasons = re.findall(reason_pattern, result_text)

            if not profile_ids:
                return []

            # Create partial matches
            partial_matches = []
            for i, profile_id in enumerate(profile_ids[:limit]):
                try:
                    profile_id = int(profile_id)
                    if 0 <= profile_id < len(available_profiles):
                        original_profile = available_profiles[profile_id]

                        score = float(scores[i]) if i < len(scores) else 0.8
                        reason = (
                            reasons[i]
                            if i < len(reasons)
                            else "Partial match extracted from incomplete response"
                        )

                        match = ProfileMatch(
                            uid=original_profile.get("uid", ""),
                            name=original_profile.get("name", "Unknown"),
                            email=original_profile.get("email", ""),
                            profile_summary=original_profile.get("profile_summary", ""),
                            urgent_needs=original_profile.get("urgent_needs", ""),
                            linkedin_url=original_profile.get("linkedin_url", ""),
                            source=original_profile.get("source", "claude_match"),
                            intent=original_profile.get("intent", "general"),
                            compatibility_score=score,
                            match_reason=reason,
                        )
                        partial_matches.append(match)

                except (ValueError, IndexError) as e:
                    print(f"⚠️ [CLAUDE] Error processing partial match {i}: {e}")
                    continue

            return partial_matches

        except Exception as e:
            print(f"⚠️ [CLAUDE] Partial match extraction failed: {e}")
            return []

    def get_matching_rules_explanation(
        self, user_intent: str, match_intent: str
    ) -> str:
        """
        Get explanation of why two intents are compatible.
        """
        prompt = f"""
        Explain why these two business intents are compatible for networking:

        User Intent: {user_intent}
        Match Intent: {match_intent}

        Provide a 1-2 sentence explanation of the mutual benefit.
        """

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text.strip()

        except Exception as e:
            print(f"❌ [CLAUDE] Rules explanation failed: {e}")
            return f"Compatible {user_intent} and {match_intent} profiles"

    def _should_trigger_fallback(self, error: Exception) -> bool:
        """
        Check if the error should trigger semantic search fallback.
        Triggers for 400, 429, 500 errors.
        """
        error_str = str(error).lower()

        # Check for specific HTTP status codes
        fallback_indicators = [
            "400",
            "bad request",
            "429",
            "rate limit",
            "too many requests",
            "500",
            "internal server error",
            "server error",
        ]

        return any(indicator in error_str for indicator in fallback_indicators)

    def _semantic_search_fallback(
        self,
        user_extraction_data: dict,  # Changed from user_urgent_needs
        user_profile_summary: Optional[str],
        available_profiles: List[Dict],
        limit: int = 3,
    ) -> List[ProfileMatch]:
        """
        Semantic search fallback using complete extraction data.
        """
        try:
            print("🔍 [FALLBACK] Starting semantic search with extraction data...")

            # Build search text from ALL extraction data dynamically
            search_parts = []
            if user_extraction_data and isinstance(user_extraction_data, dict):
                for key, value in user_extraction_data.items():
                    if value:
                        value_str = str(value).strip()
                        if value_str and value_str.lower() not in [
                            "n/a",
                            "none",
                            "null",
                            "",
                        ]:
                            search_parts.append(value_str)

            search_text = " ".join(search_parts)

            if user_profile_summary and user_profile_summary.strip():
                search_text += " " + user_profile_summary

            if not search_text:
                print(f"⚠️ [FALLBACK] No search text to query")
                return []

            # Use Qdrant for semantic search
            from utils.qdrant import Search

            all_matches = []

            # Search UserProfiles collection
            print("🔍 [FALLBACK] Searching UserProfiles collection...")
            profiles_search = Search("UserProfiles")
            profile_matches = profiles_search.query(search_text, limit=50)

            for match in profile_matches:
                metadata = match.get("metadata", {})

                # Extract complete extraction data from payload
                extraction_data = metadata.get("extraction_data", {})

                profile_result = {
                    "uid": metadata.get("user_id", ""),
                    "name": metadata.get("name", "Unknown"),
                    "email": metadata.get("email", ""),
                    "profile_summary": match.get("document", ""),
                    "urgent_needs": metadata.get("goal", ""),
                    "linkedin_url": metadata.get("linkedin_url", ""),
                    "intent": metadata.get("intent", "general"),
                    "source": "qdrant_profiles",
                    "score": match.get("distance", 0),
                    "extraction_data": extraction_data,  # Complete extraction data
                }
                all_matches.append(profile_result)

            # Search UserUrgentNeeds collection
            print("🔍 [FALLBACK] Searching UserUrgentNeeds collection...")
            needs_search = Search("UserUrgentNeeds")
            needs_matches = needs_search.query(search_text, limit=50)

            for match in needs_matches:
                metadata = match.get("metadata", {})

                # Extract complete extraction data from payload
                extraction_data = metadata.get("extraction_data", {})

                needs_result = {
                    "uid": metadata.get("user_id", ""),
                    "name": metadata.get("name", "Unknown"),
                    "email": metadata.get("email", ""),
                    "profile_summary": match.get("document", ""),
                    "urgent_needs": metadata.get("urgent_needs", ""),
                    "linkedin_url": metadata.get("linkedin_url", ""),
                    "intent": metadata.get("intent", "general"),
                    "source": "qdrant_needs",
                    "score": match.get("distance", 0),
                    "extraction_data": extraction_data,  # Complete extraction data
                }
                all_matches.append(needs_result)

            # Remove duplicates based on user_id
            seen_users = set()
            unique_matches = []
            for match in all_matches:
                match_user_id = match.get("uid", "")
                if match_user_id and match_user_id not in seen_users:
                    seen_users.add(match_user_id)
                    unique_matches.append(match)

            # Sort by score (lower distance = better match)
            unique_matches.sort(key=lambda x: x.get("score", 1.0))

            # Convert to ProfileMatch objects
            profile_matches = []
            for match in unique_matches[:limit]:
                distance = match.get("score", 1.0)
                compatibility_score = max(0.0, 1.0 - distance)

                if compatibility_score >= 0.3:
                    profile_match = ProfileMatch(
                        uid=match.get("uid", ""),
                        name=match.get("name", "Unknown"),
                        email=match.get("email", ""),
                        profile_summary=match.get("profile_summary", ""),
                        urgent_needs=match.get("urgent_needs", ""),
                        linkedin_url=match.get("linkedin_url", ""),
                        source=f"semantic_fallback_{match.get('source', 'unknown')}",
                        intent=match.get("intent", "general"),
                        compatibility_score=compatibility_score,
                        match_reason=f"Semantic similarity match based on complete extraction data (score: {compatibility_score:.2f})",
                    )
                    profile_matches.append(profile_match)

            print(
                f"✅ [FALLBACK] Found {len(profile_matches)} semantic matches using extraction data"
            )
            return profile_matches

        except Exception as e:
            print(f"❌ [FALLBACK] Semantic search fallback failed: {e}")
            import traceback

            traceback.print_exc()
            return []

    def generate_natural_response(
        self, user_id: str, message_text: str, context: Dict
    ) -> Optional[str]:
        """
        Generate natural, contextual responses using Claude with full conversation history and intent awareness.

        Args:
            user_id: User identifier
            message_text: User's latest message
            context: Dict containing:
                - user_name: User's name
                - user_goal: User's primary goal
                - user_intent: User's classified intent
                - user_state: Current conversation state
                - has_complete_profile: Boolean
                - conversation_stage: Stage of conversation
                - recent_history: List of recent messages
                - extraction_data: Full extraction data
                - system_instruction: Optional custom instruction

        Returns:
            Natural response string or None if generation fails
        """
        try:
            # CRITICAL VALIDATION: Ensure user_id is valid and not contaminated
            if not user_id or user_id == "default" or len(user_id) < 5:
                print(f"❌ [CLAUDE_NATURAL] Invalid user_id: {user_id}")
                return None
            from api.whatsapp_modules.conversation_history import conversation_history
            from utils.db import get_extraction_data

            # Extract context
            user_name = context.get("user_name", "there")
            user_goal = context.get("user_goal", "")
            user_intent = context.get("user_intent", "general")
            recent_history = context.get("recent_history", [])
            system_instruction = context.get("system_instruction", "")
            extraction_data = context.get("extraction_data", {})

            # Get comprehensive conversation context from proper systems
            # Memory handled by intelligent user recognition and conversation history systems

            # Build conversation history for Claude
            conversation_context = []
            if recent_history:
                for msg in recent_history[-15:]:  # Last 15 messages
                    sender = msg.get("sender", "")
                    content = msg.get("content", "")

                    if sender == "user":
                        conversation_context.append(f"User: {content}")
                    elif sender == "agent":
                        conversation_context.append(f"You: {content}")

            conversation_history_text = (
                "\n".join(conversation_context)
                if conversation_context
                else "No previous conversation."
            )

            # Get interaction history from proper systems
            # Profile suggestions and introductions handled by intelligent user context
            suggested_profiles = []
            introductions_made = []
            voice_calls = (
                conversation_history.get_voice_call_history(user_id, limit=3) or []
            )

            # Build rich context about user with intent information
            user_context_parts = []

            user_context_parts.append(f"**Intent Classification**: {user_intent}")

            if user_goal:
                user_context_parts.append(f"Primary goal: {user_goal}")

            if extraction_data.get("the_story"):
                user_context_parts.append(
                    f"Background: {extraction_data['the_story'][:200]}"
                )

            if extraction_data.get("urgent_needs"):
                user_context_parts.append(
                    f"Urgent needs: {extraction_data['urgent_needs'][:150]}"
                )

            if extraction_data.get("top_priorities"):
                user_context_parts.append(
                    f"Top priorities: {extraction_data['top_priorities'][:150]}"
                )

            if suggested_profiles:
                user_context_parts.append(
                    f"Profiles suggested: {len(suggested_profiles)}"
                )

            if introductions_made:
                user_context_parts.append(
                    f"Introductions made: {len(introductions_made)}"
                )

            if voice_calls:
                user_context_parts.append(f"Previous calls: {len(voice_calls)}")

            user_context_text = (
                "\n".join(user_context_parts)
                if user_context_parts
                else "Limited context available."
            )

            # Build system prompt if not provided
            if not system_instruction:
                system_instruction = f"""You are Jyoti from Switch, helping {user_name} find jobs or hire staff.

    YOUR PRIMARY ROLE: Connect local businesses with reliable workers through WhatsApp conversations.

    USER'S CLASSIFIED INTENT: {user_intent}

    CURRENT NETWORK STATUS:
    - The network is actively being built across all categories
    - Be HONEST when specific connections aren't available yet
    - Promise to notify users once relevant connections are found
    - Keep the conversation going with helpful questions

    CORE FUNCTIONS:
    1. **Understand their needs** - Ask questions to identify exactly who they need
    2. **Answer questions** - Explain the network, who you know, what you can do
    3. **Handle call requests** - If user explicitly asks for a call, acknowledge and confirm
    4. **Natural conversation** - Chat naturally about their goals and challenges
    5. **Short Responses** - Keep replies concise and to the point (1-2 sentences typically)

    CONVERSATION STYLE:
    - Be warm and personable, like texting a helpful friend
    - Keep responses VERY concise (1-2 sentences, max 3 sentences)
    - Don't repeat information unnecessarily
    - Use their name sparingly (maybe once per response)
    - Match their energy - if brief, be brief; if detailed, be more thorough
    - Be honest about network availability without being negative

    CRITICAL RULES:
    - **NEVER push calls** unless the user explicitly asks for one
    - If they ask for a call, respond positively: "Sure! I can call you right now to discuss [goal]. Ready?"
    - Don't send the same templated message repeatedly
    - Don't be overly formal or sales-y
    - Address their actual question directly
    - When connections aren't available: "I'm building my network for [intent]. I'll notify you once I find good matches. Meantime, what else can I help with?"

    INTENT-BASED APPROACH:
    Based on their intent ({user_intent}), tailor responses:
    - Acknowledge their specific need (hiring/sales/partnerships/fundraising)
    - If they ask for connections and you don't have them: Be honest, promise to notify, keep conversation going
    - Ask clarifying questions that are relevant to their intent
    - Show genuine interest in helping them achieve their goal

    YOUR APPROACH:
    1. User asks question → Answer directly and concisely
    2. User shares need → Acknowledge + Ask clarifying questions if needed
    3. User requests call → Confirm and proceed
    4. User asks for connections → Search OR be honest about building network + notify promise
    5. Stay conversational → Build relationship through helpful, brief interactions

    IMPORTANT: 
    - Keep responses SHORT (1-2 sentences)
    - Be honest about network availability
    - Focus on being helpful, not sales-y"""

            # Build the full prompt
            prompt = f"""{system_instruction}

    USER CONTEXT:
    Name: {user_name}
    {user_context_text}

    RECENT CONVERSATION HISTORY:
    {conversation_history_text}

    USER'S CURRENT MESSAGE:
    "{message_text}"

    Generate a natural, helpful response that:
    1. Directly addresses their message in 1-2 sentences
    2. References their intent ({user_intent}) appropriately if relevant
    3. Is honest about network availability if they're asking for connections
    4. Moves the conversation forward naturally
    5. Feels human and conversational, not robotic

    Remember: VERY SHORT responses (1-2 sentences max). Be helpful and honest.

    Response:"""

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,  # Keep responses concise
                temperature=0.7,  # More natural variation
                messages=[{"role": "user", "content": prompt}],
            )

            generated_response = response.content[0].text.strip()

            # Clean up response (remove quotes if Claude wrapped it)
            if generated_response.startswith('"') and generated_response.endswith('"'):
                generated_response = generated_response[1:-1]

            # Additional cleanup - remove any markdown formatting
            generated_response = generated_response.replace("**", "")

            print(
                f"🤖 [CLAUDE_NATURAL] Generated intent-aware response for {user_name} ({user_intent}): {generated_response[:100]}..."
            )

            return generated_response

        except Exception as e:
            print(f"❌ [CLAUDE_NATURAL] Error generating natural response: {e}")
            return None

    def generate_contextual_greeting(
        self, user_id: str, user_name: str, user_goal: str, greeting_count: int
    ) -> str:
        """
        Generate varied, contextual greetings based on conversation history.

        Args:
            user_id: User identifier
            user_name: User's name
            user_goal: User's primary goal
            greeting_count: Number of times user has been greeted in this state

        Returns:
            Natural greeting string
        """
        try:
            from api.whatsapp_modules.conversation_history import conversation_history

            # Get recent context
            recent_messages = (
                conversation_history.get_recent_messages(user_id, limit=5) or []
            )

            # Check if they have pending actions - handled by intelligent user context
            suggested_profiles = []
            introductions_made = []

            context_hints = []
            if suggested_profiles:
                context_hints.append(
                    f"You have {len(suggested_profiles)} profile suggestions"
                )
            if introductions_made:
                context_hints.append(f"{len(introductions_made)} introduction(s) sent")

            # Build prompt
            prompt = f"""Generate a natural, friendly greeting for {user_name} who is looking to {user_goal.lower()}.

    This is greeting #{greeting_count + 1} in this conversation stage.

    Context:
    {' - '.join(context_hints) if context_hints else 'No pending actions'}

    Requirements:
    - VERY brief (1 sentence max)
    - Natural and warm, not robotic
    - Don't mention the greeting count
    - Vary the greeting style (don't always say "Hey!" or "Hi!")
    - If greeting_count > 2, be more casual and brief
    - Reference their goal naturally if appropriate
    - If there are pending actions, you can subtly reference them

    Examples of good greetings:
    - "Hey {user_name}! What's on your mind?"
    - "Hi! How's {user_goal.lower()} going?"
    - "{user_name}! Good to hear from you 👋"
    - "What's up, {user_name}?"

    Generate greeting:"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=50,
                temperature=0.8,  # More variation
                messages=[{"role": "user", "content": prompt}],
            )

            greeting = response.content[0].text.strip()

            # Clean up
            if greeting.startswith('"') and greeting.endswith('"'):
                greeting = greeting[1:-1]

            print(f"🤖 [CLAUDE_GREETING] Generated greeting: {greeting}")

            return greeting

        except Exception as e:
            print(f"❌ [CLAUDE_GREETING] Error generating greeting: {e}")
            # Fallback greetings
            fallbacks = [
                f"Hey {user_name}! What's up?",
                f"Hi {user_name}! How can I help?",
                f"{user_name}! Good to hear from you.",
                f"Hey! What's on your mind?",
            ]
            return fallbacks[greeting_count % len(fallbacks)]


# Global instance
claude_profile_service = ClaudeProfileService()
