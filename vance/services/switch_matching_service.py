"""
Service for matching candidates to jobs based on criteria.
Uses switch_users collection for candidate data.
"""

import time
from dataclasses import dataclass
from typing import List, Optional
from utils.db import fs
from models.switch_models import Job, JobStatus


@dataclass
class SwitchCandidate:
    """Simplified candidate model for matching, mapped from switch_users collection."""
    id: str
    phone: str
    name: str
    photo_url: Optional[str] = None
    area: str = ""
    experience_level: str = ""
    preferred_roles: List[str] = None
    languages: List[str] = None
    is_available: bool = True
    expected_salary_min: int = 0
    expected_salary_max: int = 15000
    last_active_at: float = 0
    is_verified: bool = False
    jobs_done: int = 0
    availability_type: str = "Immediately"

    def __post_init__(self):
        if self.preferred_roles is None:
            self.preferred_roles = []
        if self.languages is None:
            self.languages = []


class SwitchMatchingService:
    """Service for candidate-job matching using switch_users collection."""

    def find_matching_candidates(
        self,
        job: Job,
        limit: int = 10
    ) -> List[SwitchCandidate]:
        """
        Find candidates matching job requirements from switch_users collection.

        Matching criteria:
        - Role preference matches job role
        - Location proximity (candidate area → job area)
        - isAvailable = true

        Sorted by:
        - Profile completeness (has photo, has experience)
        - Name alphabetically
        """
        print(f"🔍 [MATCHING] Finding candidates for job {job.id} (role: {job.role}, location: {job.location})")
        print(f"🔍 [MATCHING] Querying switch_users collection...")

        # Query all switch_users (we'll filter in memory for flexibility)
        all_users = fs.collection("switch_users").stream()

        matching_candidates = []
        total_users = 0

        for user_doc in all_users:
            total_users += 1
            try:
                user_data = user_doc.to_dict() or {}
                profile = user_data.get("profile", {})

                # DEBUG: Log all available fields for first 3 users
                if total_users <= 3:
                    print(f"📋 [MATCHING] User {user_doc.id} - ALL FIELDS:")
                    print(f"   Top-level keys: {list(user_data.keys())}")
                    print(f"   Profile keys: {list(profile.keys())}")
                    print(f"   photoURL: {profile.get('photoURL', 'NOT FOUND')}")
                    print(f"   photo_url: {profile.get('photo_url', 'NOT FOUND')}")
                    print(f"   profilePhoto: {profile.get('profilePhoto', 'NOT FOUND')}")
                    print(f"   location: {profile.get('location', 'NOT FOUND')}")
                    print(f"   area: {profile.get('area', 'NOT FOUND')}")
                    print(f"   city: {profile.get('city', 'NOT FOUND')}")
                    print(f"   experience: {profile.get('experience', 'NOT FOUND')}")
                    print(f"   experienceLevel: {profile.get('experienceLevel', 'NOT FOUND')}")
                    print(f"   workExperience: {profile.get('workExperience', 'NOT FOUND')}")
                    print(f"   Full profile: {profile}")

                # Skip if not available
                is_available = profile.get("isAvailable", True)
                if not is_available:
                    continue

                # Skip if no name (incomplete profile)
                name = profile.get("name", "")
                if not name:
                    continue

                # Try multiple field names for photo, location, experience
                photo_url = (
                    profile.get("photoURL") or
                    profile.get("photo_url") or
                    profile.get("profilePhoto") or
                    profile.get("imageUrl") or
                    user_data.get("photoURL")  # Also check top-level
                )

                area = (
                    profile.get("location") or
                    profile.get("area") or
                    profile.get("city") or
                    profile.get("currentLocation") or
                    user_data.get("location")  # Also check top-level
                )

                experience_level = (
                    profile.get("experience") or
                    profile.get("experienceLevel") or
                    profile.get("workExperience") or
                    profile.get("totalExperience") or
                    user_data.get("experience")  # Also check top-level
                )

                print(f"🔍 [MATCHING] User {name}: photo={photo_url is not None}, area={area}, exp={experience_level}")

                # Get additional fields for profile card
                is_verified = profile.get("isVerified", False) or profile.get("verified", False) or user_data.get("isVerified", False)
                jobs_done = profile.get("jobsDone", 0) or profile.get("completedJobs", 0) or user_data.get("jobsDone", 0) or 0
                availability_type = profile.get("availabilityType", "Immediately") or profile.get("availability", "Immediately") or "Immediately"
                languages = profile.get("languages", []) or user_data.get("languages", []) or []
                if isinstance(languages, str):
                    languages = [languages]

                # Create SwitchCandidate from switch_users data
                candidate = SwitchCandidate(
                    id=user_doc.id,
                    phone=profile.get("phone", user_doc.id),
                    name=name,
                    photo_url=photo_url,
                    area=area or "",
                    experience_level=experience_level or "",
                    preferred_roles=profile.get("preferredRoles", []),
                    languages=languages,
                    is_available=is_available,
                    expected_salary_min=profile.get("expectedSalaryMin", 0) or 0,
                    expected_salary_max=profile.get("expectedSalaryMax", 15000) or 15000,
                    last_active_at=user_data.get("updatedAt", 0) or user_data.get("createdAt", 0) or 0,
                    is_verified=bool(is_verified),
                    jobs_done=int(jobs_done) if jobs_done else 0,
                    availability_type=str(availability_type),
                )

                # Check role match
                if not self._matches_role(candidate, job.role):
                    continue

                # Check location proximity (relaxed for now - match if any location set)
                if not self._matches_location(candidate, job):
                    continue

                matching_candidates.append(candidate)

            except Exception as e:
                print(f"⚠️ [MATCHING] Error processing user {user_doc.id}: {e}")
                continue

        print(f"🔍 [MATCHING] Processed {total_users} total users")

        # Sort by: has photo, has experience, then alphabetically
        matching_candidates.sort(
            key=lambda c: (
                0 if c.photo_url else 1,  # Has photo first
                0 if c.experience_level else 1,  # Has experience first
                c.name.lower(),  # Alphabetically
            )
        )

        result = matching_candidates[:limit]
        print(f"✅ [MATCHING] Found {len(result)} matching candidates out of {len(matching_candidates)} available")

        return result

    def _matches_role(self, candidate: SwitchCandidate, job_role: str) -> bool:
        """Check if candidate's preferred roles match job role."""
        # If no preferred roles set, consider as match (open to anything)
        if not candidate.preferred_roles:
            return True

        job_role_lower = job_role.lower()

        # Common role mappings
        role_aliases = {
            "waiter": ["waiter", "server", "steward", "f&b"],
            "helper": ["helper", "assistant", "support"],
            "sales": ["sales", "retail", "shop", "counter"],
            "kitchen": ["kitchen", "cook", "chef", "cooking"],
            "delivery": ["delivery", "driver", "courier"],
            "security": ["security", "guard", "watchman"],
        }

        # Get all aliases for the job role
        job_aliases = set()
        for key, aliases in role_aliases.items():
            if any(alias in job_role_lower for alias in aliases):
                job_aliases.update(aliases)
        if not job_aliases:
            job_aliases = {job_role_lower}

        # Check if any preferred role matches
        for preferred in candidate.preferred_roles:
            preferred_lower = preferred.lower()
            # Direct match
            if job_role_lower in preferred_lower or preferred_lower in job_role_lower:
                return True
            # Alias match
            if any(alias in preferred_lower for alias in job_aliases):
                return True

        return False

    def _matches_location(self, candidate: SwitchCandidate, job: Job) -> bool:
        """Check if candidate's area matches job location."""
        # If no location set on either side, consider as match
        if not candidate.area or not job.location:
            return True

        # Simple substring match for now
        job_location_lower = job.location.lower()
        candidate_area_lower = candidate.area.lower()

        # Common area mappings for Delhi NCR
        area_aliases = {
            "delhi": ["delhi", "new delhi", "ncr"],
            "noida": ["noida", "greater noida", "ncr"],
            "gurgaon": ["gurgaon", "gurugram", "ncr"],
            "ghaziabad": ["ghaziabad", "ncr"],
            "faridabad": ["faridabad", "ncr"],
        }

        # Check direct match
        if job_location_lower in candidate_area_lower or candidate_area_lower in job_location_lower:
            return True

        # Check NCR match
        job_in_ncr = any(alias in job_location_lower for aliases in area_aliases.values() for alias in aliases)
        candidate_in_ncr = any(alias in candidate_area_lower for aliases in area_aliases.values() for alias in aliases)

        if job_in_ncr and candidate_in_ncr:
            return True

        # Relaxed matching - if candidate has any location, consider them
        return True  # For now, be permissive with location matching

    def find_all_available_candidates(self, limit: int = 50) -> List[SwitchCandidate]:
        """
        Find all available candidates from switch_users collection.
        Useful for debugging or when no specific job requirements.
        """
        print(f"🔍 [MATCHING] Finding all available candidates...")

        all_users = fs.collection("switch_users").stream()

        candidates = []

        for user_doc in all_users:
            try:
                user_data = user_doc.to_dict() or {}
                profile = user_data.get("profile", {})

                # Skip if not available
                if not profile.get("isAvailable", True):
                    continue

                # Skip if no name
                name = profile.get("name", "")
                if not name:
                    continue

                # Try multiple field names for photo, location, experience
                photo_url = (
                    profile.get("photoURL") or
                    profile.get("photo_url") or
                    profile.get("profilePhoto") or
                    profile.get("imageUrl") or
                    user_data.get("photoURL")
                )

                area = (
                    profile.get("location") or
                    profile.get("area") or
                    profile.get("city") or
                    profile.get("currentLocation") or
                    user_data.get("location")
                )

                experience_level = (
                    profile.get("experience") or
                    profile.get("experienceLevel") or
                    profile.get("workExperience") or
                    profile.get("totalExperience") or
                    user_data.get("experience")
                )

                candidate = SwitchCandidate(
                    id=user_doc.id,
                    phone=profile.get("phone", user_doc.id),
                    name=name,
                    photo_url=photo_url,
                    area=area or "",
                    experience_level=experience_level or "",
                    preferred_roles=profile.get("preferredRoles", []),
                    languages=profile.get("languages", []),
                    is_available=True,
                    expected_salary_min=profile.get("expectedSalaryMin", 0) or 0,
                    expected_salary_max=profile.get("expectedSalaryMax", 15000) or 15000,
                    last_active_at=user_data.get("updatedAt", 0) or 0,
                )

                candidates.append(candidate)

            except Exception as e:
                print(f"⚠️ [MATCHING] Error processing user {user_doc.id}: {e}")
                continue

        # Sort by has photo, then name
        candidates.sort(key=lambda c: (0 if c.photo_url else 1, c.name.lower()))

        print(f"✅ [MATCHING] Found {len(candidates)} available candidates")
        return candidates[:limit]

    def find_any_candidates_fallback(self, limit: int = 3) -> List[SwitchCandidate]:
        """
        FALLBACK: Find ANY candidates from switch_users collection, ignoring availability.
        Used when no matching candidates found to still send some profiles.
        """
        print(f"🔄 [MATCHING] FALLBACK: Finding any candidates (ignoring availability)...")

        all_users = fs.collection("switch_users").stream()

        candidates = []

        for user_doc in all_users:
            try:
                user_data = user_doc.to_dict() or {}
                profile = user_data.get("profile", {})

                # Only require a name - ignore availability
                name = profile.get("name", "")
                if not name:
                    continue

                is_available = profile.get("isAvailable", False)

                # Try multiple field names for photo, location, experience
                photo_url = (
                    profile.get("photoURL") or
                    profile.get("photo_url") or
                    profile.get("profilePhoto") or
                    profile.get("imageUrl") or
                    user_data.get("photoURL")
                )

                area = (
                    profile.get("location") or
                    profile.get("area") or
                    profile.get("city") or
                    profile.get("currentLocation") or
                    user_data.get("location")
                )

                experience_level = (
                    profile.get("experience") or
                    profile.get("experienceLevel") or
                    profile.get("workExperience") or
                    profile.get("totalExperience") or
                    user_data.get("experience")
                )

                print(f"🔄 [MATCHING] FALLBACK User {name}: photo={photo_url is not None}, area={area}, exp={experience_level}")

                candidate = SwitchCandidate(
                    id=user_doc.id,
                    phone=profile.get("phone", user_doc.id),
                    name=name,
                    photo_url=photo_url,
                    area=area or "",
                    experience_level=experience_level or "",
                    preferred_roles=profile.get("preferredRoles", []),
                    languages=profile.get("languages", []),
                    is_available=is_available,
                    expected_salary_min=profile.get("expectedSalaryMin", 0) or 0,
                    expected_salary_max=profile.get("expectedSalaryMax", 15000) or 15000,
                    last_active_at=user_data.get("updatedAt", 0) or 0,
                )

                candidates.append(candidate)

            except Exception as e:
                print(f"⚠️ [MATCHING] Error processing user {user_doc.id}: {e}")
                continue

        # Sort by: has photo, has experience, then name
        candidates.sort(key=lambda c: (0 if c.photo_url else 1, 0 if c.experience_level else 1, c.name.lower()))

        print(f"🔄 [MATCHING] FALLBACK: Found {len(candidates)} total candidates")
        return candidates[:limit]

    def mark_all_candidates_available(self) -> int:
        """
        Mark ALL switch_users as available (isAvailable = true).
        Returns the count of updated users.
        """
        print(f"🔧 [MATCHING] Marking all switch_users as available...")

        all_users = fs.collection("switch_users").stream()
        updated_count = 0

        for user_doc in all_users:
            try:
                user_data = user_doc.to_dict() or {}
                profile = user_data.get("profile", {})

                # Update profile.isAvailable to True
                profile["isAvailable"] = True
                fs.collection("switch_users").document(user_doc.id).update({
                    "profile.isAvailable": True
                })
                updated_count += 1
                print(f"✅ [MATCHING] Marked {user_doc.id} as available")

            except Exception as e:
                print(f"⚠️ [MATCHING] Error updating user {user_doc.id}: {e}")
                continue

        print(f"✅ [MATCHING] Marked {updated_count} users as available")
        return updated_count


switch_matching_service = SwitchMatchingService()
