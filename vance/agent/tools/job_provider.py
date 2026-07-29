"""
Tools specific to job providers (hiring managers, recruiters).
These tools handle candidate matching, presentation, and interview scheduling.
"""

import traceback
from typing import List

import pendulum
from pydantic_ai import RunContext

from agent.models import AgentDeps, StoredCandidate
from services.claude_profile_service import claude_profile_service
from services.hybrid_matching_service import HybridMatchingService
from services.jd_scraping_service import jd_scraping_service
from services.interview_scheduling_service import (
    interview_scheduling_service,
    notify_candidate_interview_scheduled,
    notify_candidate_profile_presented,
)
from utils.db import get_extraction_data, get_user_profile, save_data_merge


async def find_job_seeker_matches(
    ctx: RunContext[AgentDeps],
    job_title: str = "",
    required_skills: str = "",
    experience_level: str = "",
    location: str = "",
    work_model: str = "",
    max_results: int = 3,
) -> str:
    """
    Search for job seekers matching the hiring requirements.
    Uses hybrid search (vector + filters) and AI ranking.

    Args:
        job_title: The role being hired for (e.g., "Senior Python Developer")
        required_skills: Comma-separated skills (e.g., "Python, Django, FastAPI")
        experience_level: Required experience (e.g., "5+ years", "Senior")
        location: Office location or "Remote"
        work_model: "Remote", "Hybrid", or "On-site"
        max_results: Maximum candidates to return
    """
    try:
        matching_service = HybridMatchingService()

        # Build job provider data from parameters and extraction data
        extraction_data = get_extraction_data(ctx.deps.uid) or {}

        job_provider_data = {
            **extraction_data,
            "job_title": job_title or extraction_data.get("job_title", ""),
            "required_skills": required_skills
            or extraction_data.get("required_skills", ""),
            "experience_level": experience_level
            or extraction_data.get("experience_level", ""),
            "office_location": location or extraction_data.get("office_location", ""),
            "work_model": work_model or extraction_data.get("work_model", ""),
        }

        print(f"[TOOL] find_job_seeker_matches: Searching with {job_provider_data}")
        print(
            f"[TOOL] find_job_seeker_matches: Excluding job provider uid={ctx.deps.uid}"
        )

        # Find matches
        try:
            matches = await matching_service.find_job_seeker_matches(
                job_provider_data=job_provider_data,
                limit=max_results,
                min_score=0.5,
                job_provider_uid=ctx.deps.uid,
            )
            print(
                f"[TOOL] find_job_seeker_matches: Found {len(matches) if matches else 0} matches"
            )
        except Exception as e:
            print(f"[TOOL] find_job_seeker_matches: Error: {e}")
            import traceback

            traceback.print_exc()
            return f"Error searching for candidates: {str(e)}"

        if not matches:
            print(
                f"[TOOL] find_job_seeker_matches: No matches found for job provider {ctx.deps.uid}"
            )
            return "No matching candidates found. Try broadening your search criteria."

        # Store candidates for later selection
        candidates_for_storage: List[StoredCandidate] = [
            StoredCandidate(
                uid=match.uid,
                name=match.name,
                email=match.email,
                linkedin_url=match.linkedin_url,
                target_role=match.target_role,
                core_skills=match.core_skills,
                work_experience=match.work_experience,
                current_location=match.current_location,
                match_score=match.match_score,
                match_reason=match.match_reason,
            )
            for match in matches
        ]

        # Store in user's session (convert to dicts for Firestore)
        save_data_merge(
            ctx.deps.uid,
            "users",
            {"suggested_candidates": [c.model_dump() for c in candidates_for_storage]},
        )

        # Notify candidates that their profiles are being presented
        job_provider_name = ctx.deps.profile.get("name", "A company")
        job_provider_linkedin = ctx.deps.profile.get("linkedin_url", "")
        candidates_dicts = [c.model_dump() for c in candidates_for_storage]
        job_provider_data = get_extraction_data(ctx.deps.uid) or {}

        for candidate in candidates_dicts:
            candidate_uid = candidate.get("uid")
            candidate_name = candidate.get("name", "")
            if not candidate_uid:
                continue
            
            # Get WhatsApp ID from candidate's profile, not from the candidate dict
            candidate_profile = get_user_profile(candidate_uid) or {}
            candidate_wa_id = (
                candidate_profile.get("wa_id")
                or candidate_profile.get("phone")
                or candidate_profile.get("whatsapp")
                or candidate_uid if candidate_uid.isdigit() and len(candidate_uid) >= 10 else ""
            )
            
            if candidate_wa_id:
                try:
                    await notify_candidate_profile_presented(
                        candidate_wa_id=candidate_wa_id,
                        job_provider_uid=ctx.deps.uid,
                        job_provider_name=job_provider_name,
                        candidate_name=candidate_name,
                        extraction_data=job_provider_data,
                        linkedin_url=job_provider_linkedin,
                    )
                    print(f"✅ [TOOL] Notified candidate {candidate_name} ({candidate_uid}) at {candidate_wa_id}")
                except Exception as e:
                    print(f"⚠️ [TOOL] Failed to notify candidate {candidate_name} ({candidate_uid}): {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"⚠️ [TOOL] No WhatsApp ID found for candidate {candidate_name} ({candidate_uid}), skipping notification")

        # Format for WhatsApp display
        formatted = interview_scheduling_service.format_candidate_presentation(
            candidates_dicts,
            include_match_reason=True,
        )

        print(f"[TOOL] find_job_seeker_matches: Found {len(matches)} candidates")
        return formatted

    except Exception as e:
        traceback.print_exc()
        return f"Error searching for candidates: {e}"


async def find_job_seeker_matches_from_jd(
    ctx: RunContext[AgentDeps],
    jd_url: str,
    max_results: int = 3,
) -> str:
    """
    Find matching job seekers directly from a shared JD link.

    Flow:
    1. Scrape the JD URL and extract structured requirements
    2. Merge with any existing extraction data for this job provider
    3. Run the hybrid matching service to find relevant candidates
    4. Store suggested candidates and notify them
    5. Return a formatted list of candidates for WhatsApp

    Args:
        jd_url: Public URL to the job description (Lever/Greenhouse/Notion/Google Doc/etc.)
        max_results: Maximum number of candidates to return
    """
    try:
        if not jd_url or not jd_url.strip():
            return (
                "Please share a valid job description link (JD URL) so I can scan it "
                "and find relevant candidates for you."
            )

        print(f"[TOOL] find_job_seeker_matches_from_jd: Processing JD URL: {jd_url}")

        # Step 1: Process the JD link (scrape + structured extraction)
        jd_result = await jd_scraping_service.process_jd_link(
            url=jd_url.strip(),
            user_id=ctx.deps.uid,
        )

        if not jd_result.get("success"):
            error = jd_result.get("error", "Unknown error")
            print(f"[TOOL] find_job_seeker_matches_from_jd: JD processing failed: {error}")
            return (
                "I couldn't read that job description link.\n\n"
                f"Reason: {error}\n\n"
                "Please double-check that the link is public and accessible, "
                "or paste the key details of the JD directly here."
            )

        requirements = jd_result.get("requirements")
        raw_preview = jd_result.get("raw_content", "")

        # Convert structured requirements to dict
        jd_data = {}
        if requirements is not None:
            try:
                jd_data = requirements.model_dump()
            except Exception as e:
                print(f"[TOOL] find_job_seeker_matches_from_jd: Error dumping requirements: {e}")
                jd_data = {}

        print(
            f"[TOOL] find_job_seeker_matches_from_jd: Extracted fields from JD: "
            f"{[k for k, v in jd_data.items() if v]}"
        )

        matching_service = HybridMatchingService()

        # Step 2: Merge JD-derived requirements with any existing extraction data
        extraction_data = get_extraction_data(ctx.deps.uid) or {}

        job_provider_data = {
            **extraction_data,
            **jd_data,
            "jd_url": jd_url.strip(),
            "jd_preview": raw_preview,
        }

        print(
            "[TOOL] find_job_seeker_matches_from_jd: Searching with job_provider_data "
            f"keys={list(job_provider_data.keys())}"
        )
        print(
            f"[TOOL] find_job_seeker_matches_from_jd: Excluding job provider uid={ctx.deps.uid}"
        )

        # Step 3: Find matches using the hybrid matching service
        try:
            matches = await matching_service.find_job_seeker_matches(
                job_provider_data=job_provider_data,
                limit=max_results,
                min_score=0.5,
                job_provider_uid=ctx.deps.uid,
            )
            print(
                f"[TOOL] find_job_seeker_matches_from_jd: Found {len(matches) if matches else 0} matches"
            )
        except Exception as e:
            print(f"[TOOL] find_job_seeker_matches_from_jd: Error during matching: {e}")
            traceback.print_exc()
            return f"Error searching for candidates from that JD link: {str(e)}"

        if not matches:
            preview_msg = (
                f"\n\nHere's a quick summary of what I read from the JD:\n\n{raw_preview}"
                if raw_preview
                else ""
            )
            return (
                "I scanned your job description link but couldn't find strong matches in my current network. "
                "You can try sharing a slightly broader JD or tell me what trade-offs you're open to."
                f"{preview_msg}"
            )

        # Step 4: Store candidates for later selection
        candidates_for_storage: List[StoredCandidate] = [
            StoredCandidate(
                uid=match.uid,
                name=match.name,
                email=match.email,
                linkedin_url=match.linkedin_url,
                target_role=match.target_role,
                core_skills=match.core_skills,
                work_experience=match.work_experience,
                current_location=match.current_location,
                match_score=match.match_score,
                match_reason=match.match_reason,
            )
            for match in matches
        ]

        save_data_merge(
            ctx.deps.uid,
            "users",
            {"suggested_candidates": [c.model_dump() for c in candidates_for_storage]},
        )

        # Step 5: Notify candidates that their profiles are being presented
        job_provider_name = ctx.deps.profile.get("name", "A company")
        job_provider_linkedin = ctx.deps.profile.get("linkedin_url", "")
        candidates_dicts = [c.model_dump() for c in candidates_for_storage]

        for candidate in candidates_dicts:
            candidate_uid = candidate.get("uid")
            candidate_name = candidate.get("name", "")
            if not candidate_uid:
                continue

            # Get WhatsApp ID from candidate's profile, not from the candidate dict
            candidate_profile = get_user_profile(candidate_uid) or {}
            candidate_wa_id = (
                candidate_profile.get("wa_id")
                or candidate_profile.get("phone")
                or candidate_profile.get("whatsapp")
                or candidate_uid
                if isinstance(candidate_uid, str) and candidate_uid.isdigit() and len(candidate_uid) >= 10
                else ""
            )

            if candidate_wa_id:
                try:
                    await notify_candidate_profile_presented(
                        candidate_wa_id=candidate_wa_id,
                        job_provider_uid=ctx.deps.uid,
                        job_provider_name=job_provider_name,
                        candidate_name=candidate_name,
                        extraction_data=job_provider_data,
                        linkedin_url=job_provider_linkedin,
                    )
                    print(
                        f"✅ [TOOL] (JD) Notified candidate {candidate_name} ({candidate_uid}) at {candidate_wa_id}"
                    )
                except Exception as e:
                    print(
                        f"⚠️ [TOOL] (JD) Failed to notify candidate {candidate_name} ({candidate_uid}): {e}"
                    )
                    traceback.print_exc()
            else:
                print(
                    f"⚠️ [TOOL] (JD) No WhatsApp ID found for candidate {candidate_name} ({candidate_uid}), skipping notification"
                )

        # Step 6: Format for WhatsApp display
        formatted = interview_scheduling_service.format_candidate_presentation(
            candidates_dicts,
            include_match_reason=True,
        )

        header = (
            "I scanned your job description link and found these candidates who look like a strong fit:\n\n"
        )

        print(
            f"[TOOL] find_job_seeker_matches_from_jd: Returning {len(matches)} candidates to user"
        )
        return header + formatted

    except Exception as e:
        traceback.print_exc()
        return f"Error searching for candidates from that JD link: {e}"

def select_candidates_for_interview(
    ctx: RunContext[AgentDeps],
    candidate_numbers: List[int],
    reject_reason: str = "",
) -> str:
    """
    Mark specific candidates for interview scheduling.
    Use the numbers from the candidate presentation (1-indexed).

    Args:
        candidate_numbers: List of candidate numbers to interview (e.g., [1, 3])
        reject_reason: Optional reason for rejecting other candidates
    """
    try:
        # Get stored candidates and parse as typed models
        profile = get_user_profile(ctx.deps.uid) or {}
        candidates_raw = profile.get("suggested_candidates", [])

        if not candidates_raw:
            return "No candidates available. Please search for candidates first."

        candidates: List[StoredCandidate] = [
            StoredCandidate.model_validate(c) for c in candidates_raw
        ]

        # Validate numbers and select candidates
        selected: List[StoredCandidate] = []
        for num in candidate_numbers:
            if 1 <= num <= len(candidates):
                selected.append(candidates[num - 1])
            else:
                return f"Invalid candidate number {num}. Please choose from 1 to {len(candidates)}."

        if not selected:
            return "Please specify which candidates you'd like to interview."

        # Check for missing emails using typed method
        missing_emails = [c for c in selected if not c.has_email()]
        has_emails = [c for c in selected if c.has_email()]

        # Store selected candidates (convert to dicts for Firestore)
        save_data_merge(
            ctx.deps.uid,
            "users",
            {"selected_candidates": [c.model_dump() for c in selected]},
        )

        # Trigger founder referral prompt when marking candidates as interviewing
        # Fire-and-forget async call
        from services.founder_referral_service import founder_referral_service
        try:
            import asyncio
            # Schedule in background (non-blocking)
            asyncio.ensure_future(
                founder_referral_service.send_referral_prompt(
                    founder_uid=ctx.deps.uid,
                    trigger_reason="interviewing"
                )
            )
        except Exception as e:
            print(f"⚠️ [REFERRAL] Failed to trigger referral prompt: {e}")

        # Format response
        selected_names = [c.name for c in selected]

        if missing_emails:
            missing_names = [c.name for c in missing_emails]
            return (
                f"Great choices! Selected {', '.join(selected_names)} for interviews.\n\n"
                f"Note: {', '.join(missing_names)} don't have email addresses on file. "
                f"I can notify them via WhatsApp instead.\n\n"
                f"When would you like to schedule the interviews?"
            )

        return (
            f"Excellent! Selected {', '.join(selected_names)} for interviews.\n\n"
            f"When would you prefer to schedule them? You can say something like "
            f'"tomorrow at 2pm" or "next Monday morning".'
        )

    except Exception as e:
        traceback.print_exc()
        return f"Error selecting candidates: {e}"


async def schedule_interviews(
    ctx: RunContext[AgentDeps],
    time_preference: str,
    duration_minutes: int = 30,
    gap_minutes: int = 15,
) -> str:
    """
    Schedule interviews with the selected candidates.
    Creates calendar events and sends notifications.

    Args:
        time_preference: Natural language time (e.g., "tomorrow 2pm", "Monday 10am")
        duration_minutes: Length of each interview (default 30)
        gap_minutes: Time between interviews (default 15)
    """
    try:
        # Get selected candidates and parse as typed models
        profile = get_user_profile(ctx.deps.uid) or {}
        selected_raw = profile.get("selected_candidates", [])

        if not selected_raw:
            return "No candidates selected. Please select candidates first."

        selected: List[StoredCandidate] = [
            StoredCandidate.model_validate(c) for c in selected_raw
        ]

        # Backfill missing emails from Firestore
        for candidate in selected:
            if not candidate.has_email() and candidate.uid:
                user_profile = get_user_profile(candidate.uid)
                extraction = get_extraction_data(candidate.uid)
                backfilled_email = user_profile.get("email", "") or extraction.get(
                    "email", ""
                )
                if backfilled_email:
                    candidate.email = backfilled_email
                    print(
                        f"[TOOL] Backfilled email for {candidate.name}: {backfilled_email}"
                    )

        # Parse time expression
        parsed = await claude_profile_service.parse_time_expression(time_preference)
        ptype = (parsed.get("type") or "none").lower()

        if ptype in ("none", "ambiguous") or not parsed.get("start_time_utc"):
            return (
                f"I couldn't understand '{time_preference}'. "
                f"Please try something like 'tomorrow at 2pm' or 'next Monday at 10am'."
            )

        # Get start time
        start_time_str = parsed.get("start_time_utc")
        assert start_time_str is not None

        start_time = pendulum.parse(start_time_str)
        assert isinstance(start_time, pendulum.DateTime)

        # Get user timezone (default to IST for now)
        user_tz = profile.get("timezone", "Asia/Kolkata")
        start_time = start_time.in_timezone(user_tz)

        # Validate time is in future
        now = pendulum.now(user_tz)
        if start_time < now:
            return "That time is in the past. Please choose a future time."

        # Filter candidates with emails (required for calendar invites)
        schedulable = [c for c in selected if c.has_email()]
        not_schedulable = [c for c in selected if not c.has_email()]

        if not schedulable:
            return (
                "I need email addresses to send calendar invites. "
                f"Could you provide emails for: {', '.join([c.name for c in selected])}?"
            )

        # Build hiring user info
        hiring_user = {
            "name": profile.get("name", "Hiring Manager"),
            "email": profile.get("email", ""),
        }

        if not hiring_user["email"]:
            return "I need your email address to send calendar invites. Could you share it?"

        # Schedule interviews (convert to dicts for service)
        schedulable_dicts = [c.model_dump() for c in schedulable]
        results = interview_scheduling_service.schedule_multiple_interviews(
            hiring_user=hiring_user,
            candidates=schedulable_dicts,
            start_time=start_time,
            duration_minutes=duration_minutes,
            gap_minutes=gap_minutes,
        )

        # Notify candidates
        for result in results:
            if "error" not in result:
                candidate = next(
                    (
                        c
                        for c in schedulable
                        if c.email == result.get("candidate_email")
                    ),
                    None,
                )
                if candidate and candidate.uid:
                    try:
                        notify_candidate_interview_scheduled(
                            candidate_wa_id=candidate.uid,
                            hiring_user_name=hiring_user["name"],
                            interview_time=result.get("start_time"),
                            meet_link=result.get("meet_link", ""),
                        )
                    except Exception as e:
                        print(f"[TOOL] Failed to notify candidate: {e}")

        # Format confirmation
        confirmation = interview_scheduling_service.format_confirmation(results)

        # Add note about unschedulable candidates
        if not_schedulable:
            names = ", ".join([c.name for c in not_schedulable])
            confirmation += (
                f"\n\nNote: Couldn't schedule {names} - missing email addresses."
            )

        # Clear session data
        save_data_merge(
            ctx.deps.uid,
            "users",
            {"suggested_candidates": None, "selected_candidates": None},
        )

        print(f"[TOOL] schedule_interviews: Scheduled {len(results)} interviews")
        return confirmation

    except Exception as e:
        traceback.print_exc()
        return f"Error scheduling interviews: {e}"


def mark_hire_successful(
    ctx: RunContext[AgentDeps],
    candidate_name: str,
    role_title: str = "",
) -> str:
    """
    Mark a candidate hire as successful.
    This triggers the founder referral prompt.

    Args:
        candidate_name: Name of the candidate who was hired
        role_title: Optional role title they were hired for
    """
    try:
        from utils.db import fs
        
        # Store hire record
        hire_data = {
            "candidate_name": candidate_name,
            "role_title": role_title,
            "hired_at": pendulum.now().timestamp(),
            "founder_uid": ctx.deps.uid,
        }
        
        # Store in Firestore
        fs.collection("successful_hires").add(hire_data)
        
        # Trigger founder referral prompt
        from services.founder_referral_service import founder_referral_service
        try:
            import asyncio
            asyncio.ensure_future(
                founder_referral_service.send_referral_prompt(
                    founder_uid=ctx.deps.uid,
                    trigger_reason="hired"
                )
            )
        except Exception as e:
            print(f"⚠️ [REFERRAL] Failed to trigger referral prompt: {e}")
        
        return (
            f"🎉 Congratulations! Marked {candidate_name} as successfully hired"
            + (f" for {role_title}" if role_title else "")
            + ".\n\n"
            "Thanks for using Switch!"
        )
        
    except Exception as e:
        traceback.print_exc()
        return f"Error marking hire: {e}"


def resuggest_candidates(
    ctx: RunContext[AgentDeps],
    rejection_reason: str = "",
    different_criteria: str = "",
) -> str:
    """
    Get new candidate suggestions when the previous ones weren't suitable.

    Args:
        rejection_reason: Why the previous candidates weren't suitable
        different_criteria: Updated search criteria
    """
    try:
        # Store feedback
        if rejection_reason:
            log_data = {"last_rejection_reason": rejection_reason}
            save_data_merge(ctx.deps.uid, "extractions", log_data)

        # Search with potentially updated criteria
        return find_job_seeker_matches(
            ctx,
            job_title=different_criteria if different_criteria else "",
            max_results=5,
        )

    except Exception as e:
        traceback.print_exc()
        return f"Error getting new suggestions: {e}"


# List of tools available to job providers
# ==========================================================================
# VANCE TOOLS DISABLED - Switch uses its own data extraction via voice calls
# These tools search the Vance database (professional networking), not Switch
# ==========================================================================
# JOB_PROVIDER_TOOLS = [
#     find_job_seeker_matches,      # DISABLED - Vance database
#     select_candidates_for_interview,  # DISABLED - Vance workflow
#     schedule_interviews,          # DISABLED - Vance workflow
#     mark_hire_successful,         # DISABLED - Vance workflow
#     resuggest_candidates,         # DISABLED - Vance database
# ]

# Import Switch tools for job providers
try:
    from agent.tools.switch import SWITCH_TOOLS
    JOB_PROVIDER_TOOLS = SWITCH_TOOLS
    print(f"✅ [JOB_PROVIDER] Loaded SWITCH_TOOLS: {[t.__name__ for t in SWITCH_TOOLS]}")
except Exception as e:
    print(f"❌ [JOB_PROVIDER] Failed to import SWITCH_TOOLS: {e}")
    import traceback
    traceback.print_exc()
    JOB_PROVIDER_TOOLS = []
