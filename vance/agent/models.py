"""
Agent data models and dependencies.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class UserType(str, Enum):
    """User type classification for tool injection."""

    JOB_SEEKER = "job_seeker"
    JOB_PROVIDER = "job_provider"
    GENERAL = "general"  # For users whose type is not yet determined


class AgentDeps(BaseModel):
    """
    Dependencies required for the agent to run.
    Passed to each tool via RunContext.
    """

    uid: str = Field(..., description="The user's WhatsApp ID (phone number)")
    mode: Literal["voice", "text"] = "text"
    profile: dict[str, Any] = Field(
        default_factory=dict,
        description="The user's profile data from Firestore",
    )
    user_type: UserType = Field(
        default=UserType.GENERAL,
        description="The user's type for tool injection",
    )
    extraction_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Extraction data from voice calls",
    )

    class Config:
        use_enum_values = True


class StoredCandidate(BaseModel):
    """
    Candidate stored in Firestore suggested_candidates/selected_candidates.
    Used for type-safe handling of candidate data in job_provider tools.
    """

    uid: str
    name: str
    email: str = ""
    linkedin_url: str = ""
    target_role: str = ""
    core_skills: str = ""
    work_experience: str = ""
    current_location: str = ""
    match_score: float = 0.0
    match_reason: str = ""

    def has_email(self) -> bool:
        """Check if candidate has a valid email address."""
        return bool(self.email)


# Keywords for user type detection
JOB_PROVIDER_KEYWORDS = [
    "hiring",
    "hire",
    "recruit",
    "recruiting",
    "looking for candidates",
    "job provider",
    "need to fill",
    "open position",
    "team needs",
    "looking to hire",
    "building a team",
    "need engineers",
    "need developers",
    "staffing",
    "headcount",
]

JOB_SEEKER_KEYWORDS = [
    "looking for a job",
    "job seeker",
    "job search",
    "seeking employment",
    "looking for work",
    "career change",
    "new opportunity",
    "open to opportunities",
    "actively looking",
    "job hunting",
    "searching for a role",
    "want to work",
    "need a job",
]


def detect_user_type(profile: dict) -> UserType:
    """
    Detect user type from profile data.
    Checks multiple fields: user_type (explicit), connection_type (from WhatsApp), goal, primary_goal.

    Args:
        profile: User profile dict from Firestore

    Returns:
        UserType enum value
    """
    # Check explicit user_type field first (most reliable)
    user_type_explicit = profile.get("user_type", "").lower()
    if user_type_explicit:
        if user_type_explicit == "job_provider":
            return UserType.JOB_PROVIDER
        elif user_type_explicit == "job_seeker":
            return UserType.JOB_SEEKER

    # Get connection_type from WhatsApp conversation (most reliable for new users)
    connection_type = (
        profile.get("connection_type")
        or profile.get("goal")
        or profile.get("arbitrary", {}).get("connection_type")
        or profile.get("profile", {}).get("connection_type")
        or ""
    ).lower()

    # Get primary_goal as fallback
    primary_goal = (profile.get("primary_goal") or "").lower()

    # Combine connection_type and primary_goal for checking
    combined_text = f"{connection_type} {primary_goal}".lower()

    # Check for job provider keywords (hiring, recruiting, etc.)
    job_provider_keywords = JOB_PROVIDER_KEYWORDS + [
        "engineers", "developers", "full stack", "backend", "frontend", 
        "hiring", "recruiting", "looking to hire", "need to hire",
        "founders hiring", "recruiters", "hiring managers"
    ]
    for kw in job_provider_keywords:
        if kw in combined_text:
            # Check if it's actually about them hiring (not them being hired)
            # If they say "looking for engineers" or "hiring engineers", they're job providers
            if any(phrase in combined_text for phrase in ["looking for engineers", "hiring engineers", "looking to hire", "need engineers", "recruiting"]):
                return UserType.JOB_PROVIDER

    # Check for job seeker keywords (looking for roles, jobs, opportunities)
    job_seeker_keywords = JOB_SEEKER_KEYWORDS + [
        "looking for roles", "looking for opportunities", "founders hiring engineers",
        "recruiters", "job opportunities", "software engineering roles",
        "full stack roles", "backend roles", "frontend roles"
    ]
    for kw in job_seeker_keywords:
        if kw in combined_text:
            # If they say "looking for founders" or "looking for recruiters", they're job seekers
            if any(phrase in combined_text for phrase in ["looking for founders", "looking for recruiters", "looking for roles", "looking for opportunities"]):
                return UserType.JOB_SEEKER

    # Check extraction data for job provider indicators (job_title, required_skills)
    # This helps for users who have completed voice calls
    if profile.get("extraction_data"):
        extraction = profile.get("extraction_data") or {}
        if extraction.get("job_title") or extraction.get("required_skills") or extraction.get("hiring_urgency"):
            return UserType.JOB_PROVIDER
        if extraction.get("target_role") or extraction.get("core_skills") or extraction.get("job_search_urgency"):
            return UserType.JOB_SEEKER

    # Fallback: Check if connection_type mentions specific role types (likely job provider)
    if connection_type:
        # If connection_type mentions role types without "looking for founders/recruiters", likely job provider
        role_types = ["engineers", "developers", "full stack", "backend", "frontend", "software engineer"]
        if any(role in connection_type for role in role_types) and "founders" not in connection_type and "recruiters" not in connection_type:
            return UserType.JOB_PROVIDER

    return UserType.GENERAL
