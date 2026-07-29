"""
Interview Scheduling Service for Vance.
Orchestrates the interview scheduling flow including candidate presentation,
selection handling, and calendar event creation.
"""

import json
import time
from datetime import datetime
from typing import Any

import pendulum
from pydantic import BaseModel
from pydantic_ai import Agent

from api.whatsapp_modules.conversation_history import conversation_history
from utils.calendar.google_calendar import VanceCalendarClient, is_calendar_configured
from utils.db import fs, save_data_merge
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


class JobProviderDescription(BaseModel):
    """Structured output for job provider description."""

    description: str


_job_provider_description_agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    output_type=JobProviderDescription,
    system_prompt="""Generate a 1-sentence professional description of a job provider for a candidate notification.
Mention the role and one key detail (culture, stage, or location). Keep it under 15 words. No emojis.""",
)


class InterviewSchedulingService:
    """
    Service for scheduling interviews between hiring users and candidates.
    """

    def __init__(self):
        """Initialize the service. Calendar client is lazy-loaded."""
        self._calendar: VanceCalendarClient | None = None

    @property
    def calendar(self) -> VanceCalendarClient:
        """Lazy-load the calendar client."""
        if self._calendar is None:
            self._calendar = VanceCalendarClient()
        return self._calendar

    def is_available(self) -> bool:
        """Check if the calendar is configured and ready to use."""
        return is_calendar_configured()

    def schedule_interview(
        self,
        hiring_user: dict,
        candidate: dict,
        start_time: datetime,
        duration_minutes: int = 30,
    ) -> dict[str, Any]:
        """
        Schedule an interview between a hiring user and a candidate.

        Args:
            hiring_user: Dict with 'name' and 'email' of the hiring manager
            candidate: Dict with 'name', 'email', and optionally 'linkedin_url', 'profile_summary'
            start_time: Interview start time
            duration_minutes: Duration of the interview (default 30 min)

        Returns:
            Dict with event_id, html_link, meet_link, start_time, candidate_name
        """
        description = self._build_description(hiring_user, candidate)

        result = self.calendar.create_interview_event(
            hiring_user_email=hiring_user["email"],
            candidate_email=candidate["email"],
            candidate_name=candidate["name"],
            start_time=start_time,
            duration_minutes=duration_minutes,
            description=description,
        )

        return {
            "event_id": result.get("id"),
            "html_link": result.get("htmlLink"),
            "meet_link": self._extract_meet_link(result),
            "start_time": start_time,
            "candidate_name": candidate["name"],
            "candidate_email": candidate["email"],
        }

    def schedule_multiple_interviews(
        self,
        hiring_user: dict,
        candidates: list[dict],
        start_time: datetime,
        duration_minutes: int = 30,
        gap_minutes: int = 15,
    ) -> list[dict[str, Any]]:
        """
        Schedule multiple interviews back-to-back.

        Args:
            hiring_user: Dict with 'name' and 'email' of the hiring manager
            candidates: List of candidate dicts
            start_time: Start time for the first interview
            duration_minutes: Duration of each interview
            gap_minutes: Gap between interviews

        Returns:
            List of scheduled interview results
        """
        results = []
        current_time = start_time

        if isinstance(current_time, datetime) and not isinstance(
            current_time, pendulum.DateTime
        ):
            current_time = pendulum.instance(current_time)

        for candidate in candidates:
            try:
                result = self.schedule_interview(
                    hiring_user=hiring_user,
                    candidate=candidate,
                    start_time=current_time,
                    duration_minutes=duration_minutes,
                )
                results.append(result)

                # Move to next slot
                current_time = current_time.add(minutes=duration_minutes + gap_minutes)

            except Exception as e:
                print(f"Failed to schedule interview with {candidate.get('name')}: {e}")
                results.append(
                    {
                        "error": str(e),
                        "candidate_name": candidate.get("name"),
                        "candidate_email": candidate.get("email"),
                    }
                )

        return results

    def _build_description(self, hiring_user: dict, candidate: dict) -> str:
        """Build the event description with relevant details."""
        lines = [
            "Interview scheduled by Vance",
            "",
            f"Candidate: {candidate.get('name', 'N/A')}",
        ]

        if candidate.get("linkedin_url"):
            lines.append(f"LinkedIn: {candidate['linkedin_url']}")

        if candidate.get("profile_summary"):
            lines.append(f"\nProfile: {candidate['profile_summary']}")

        if candidate.get("headline"):
            lines.append(f"Current Role: {candidate['headline']}")

        lines.extend(
            [
                "",
                f"Hiring Manager: {hiring_user.get('name', 'N/A')}",
                f"Email: {hiring_user.get('email', 'N/A')}",
            ]
        )

        return "\n".join(lines)

    def _extract_meet_link(self, event: dict) -> str:
        """Extract Google Meet link from event response."""
        conference_data = event.get("conferenceData", {})
        entry_points = conference_data.get("entryPoints", [])

        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                return ep.get("uri", "")

        return ""

    def format_candidate_presentation(
        self,
        candidates: list[dict],
        include_match_reason: bool = True,
    ) -> str:
        """
        Format candidates for WhatsApp presentation.

        Args:
            candidates: List of candidate dicts with name, headline, profile_summary, match_reason
            include_match_reason: Whether to include why they're a match

        Returns:
            Formatted string for WhatsApp message
        """
        lines = [
            "I'd love to introduce you to some candidates that fit your hiring needs:",
            "",
        ]

        for i, candidate in enumerate(candidates, 1):
            name = candidate.get("name", "Unknown")
            headline = candidate.get("headline", "") or candidate.get("target_role", "")
            uid = candidate.get("uid", "")
            profile_url = candidate.get("profile_url", "")

            lines.append(f"*{i}. {name}*")
            if headline:
                lines.append(f"_{headline}_")

            if candidate.get("linkedin_url"):
                lines.append(f"LinkedIn: {candidate['linkedin_url']}")

            # Attach public profile link if available (or can be derived)
            try:
                if not profile_url and uid:
                    # Try to find public profile by user_id
                    public_profiles_ref = fs.collection("public_profiles")
                    slug = None
                    data = {}

                    # First, try direct document (in case slug == uid)
                    doc = public_profiles_ref.document(uid).get()
                    if doc.exists:
                        data = doc.to_dict() or {}
                        slug = doc.id
                    else:
                        # Fallback: query by user_id field
                        try:
                            query = (
                                public_profiles_ref.where("user_id", "==", uid)
                                .limit(1)
                                .stream()
                            )
                            for qdoc in query:
                                data = qdoc.to_dict() or {}
                                slug = qdoc.id
                                break
                        except Exception:
                            slug = None

                    if slug and (data.get("active", True)):
                        profile_url = f"https://profiles.vance.so/{slug}"

                if profile_url:
                    lines.append(f"Profile: {profile_url}")
            except Exception as e:
                # Don't block profile presentation if profile URL lookup fails
                print(f"⚠️ [INTERVIEW] Failed to attach profile URL for {uid}: {e}")

            # Build profile summary from available fields
            profile_summary = candidate.get("profile_summary", "")
            if not profile_summary:
                parts = []
                work_exp = candidate.get("work_experience") or "1+ years"
                parts.append(work_exp)
                if candidate.get("core_skills"):
                    parts.append(f"Skills: {candidate['core_skills']}")
                loc = candidate.get("current_location") or "Sec 24, Gurgaon"
                parts.append(f"Location: {loc}")
                profile_summary = " | ".join(parts)

            if profile_summary:
                if len(profile_summary) > 150:
                    profile_summary = profile_summary[:147] + "..."
                lines.append(profile_summary)

            if include_match_reason and candidate.get("match_reason"):
                lines.append(f"Why they're a match: {candidate['match_reason']}")

            lines.append("")  # Empty line between candidates

        lines.append(
            "Let me know which candidates you'd like to interview and which aren't relevant. "
            "I'll schedule the interviews for you."
        )

        return "\n".join(lines)

    def format_time_request(self, selected_names: list[str]) -> str:
        """
        Format the message asking for preferred interview time.

        Args:
            selected_names: Names of selected candidates

        Returns:
            Formatted string for WhatsApp message
        """
        if len(selected_names) == 1:
            names_str = selected_names[0]
        elif len(selected_names) == 2:
            names_str = f"{selected_names[0]} and {selected_names[1]}"
        else:
            names_str = ", ".join(selected_names[:-1]) + f", and {selected_names[-1]}"

        return (
            f"Great choices! I'll set up interviews with {names_str}.\n\n"
            "When would you prefer to schedule these interviews? You can say something like "
            '"tomorrow at 2pm" or "next Monday morning".'
        )

    def format_confirmation(self, scheduled_interviews: list[dict]) -> str:
        """
        Format confirmation message after scheduling.

        Args:
            scheduled_interviews: List of scheduled interview results

        Returns:
            Formatted string for WhatsApp message
        """
        lines = ["Done! I've scheduled your interviews:", ""]

        for interview in scheduled_interviews:
            if "error" in interview:
                lines.append(
                    f"*{interview.get('candidate_name', 'Unknown')}* - "
                    f"Failed to schedule: {interview['error']}"
                )
            else:
                name = interview.get("candidate_name", "Unknown")
                start_time = interview.get("start_time")

                if isinstance(start_time, (datetime, pendulum.DateTime)):
                    time_str = start_time.strftime("%A, %B %d at %I:%M %p")
                else:
                    time_str = str(start_time)

                lines.append(f"*{name}* - {time_str}")

                if interview.get("meet_link"):
                    lines.append(f"Google Meet: {interview['meet_link']}")

                lines.append("")

        lines.append(
            "Calendar invites have been sent to everyone. Good luck with the interviews!"
        )

        return "\n".join(lines)


# Singleton instance
interview_scheduling_service = InterviewSchedulingService()


# ==================== CANDIDATE NOTIFICATION FUNCTIONS ====================


async def get_job_provider_description(
    job_provider_uid: str,
    job_provider_name: str,
    extraction_data: dict,
    linkedin_url: str = "",
) -> str:
    """
    Get or generate a job provider description using LLM.

    1. Check if 'job_provider_description' exists in extraction_data - return if present
    2. Otherwise, generate via LLM, save to DB, and return
    3. Always append LinkedIn URL if available

    Args:
        job_provider_uid: The job provider's user ID
        job_provider_name: Name of the job provider/hiring manager
        extraction_data: Extraction data containing job details
        linkedin_url: LinkedIn URL of the job provider (optional)

    Returns:
        A short description with LinkedIn URL appended
    """
    # Check cache first
    cached = extraction_data.get("job_provider_description", "").strip()
    if cached:
        # Append LinkedIn if available and not already in cached description
        if linkedin_url and linkedin_url not in cached:
            return f"{cached} LinkedIn: {linkedin_url}"
        return cached

    try:
        # Build context for LLM - just dump all extraction data
        prompt = f"Company/Person: {job_provider_name}\n\nData:\n{json.dumps(extraction_data, indent=2)}"

        # Generate description via LLM
        result = await _job_provider_description_agent.run(prompt)
        description = result.output.description
        print(f"📝 [LLM] Generated job provider description: {description}")

        # Save to DB for future use (without LinkedIn - that's added dynamically)
        save_data_merge(
            job_provider_uid, "extractions", {"job_provider_description": description}
        )

        # Append LinkedIn URL if available
        if linkedin_url:
            return f"{description} LinkedIn: {linkedin_url}"
        return description

    except Exception as e:
        print(f"⚠️ LLM description generation failed: {e}")
        # Fallback to simple format
        job_title = extraction_data.get("job_title", "")
        fallback = f"hiring for {job_title}" if job_title else "hiring"
        if linkedin_url:
            return f"{fallback} LinkedIn: {linkedin_url}"
        return fallback


async def notify_candidate_profile_presented(
    candidate_wa_id: str,
    job_provider_uid: str,
    job_provider_name: str,
    candidate_name: str,
    extraction_data: dict,
    linkedin_url: str = "",
) -> bool:
    """
    Send WhatsApp notification to candidate that their profile was presented to a job provider.
    This is sent when a job provider searches and views candidate profiles.

    Args:
        candidate_wa_id: Candidate's WhatsApp ID (phone number)
        job_provider_uid: The job provider's user ID
        job_provider_name: Name of the job provider/hiring manager
        candidate_name: Name of the candidate
        extraction_data: Job provider's extraction data
        linkedin_url: Job provider's LinkedIn URL (optional)

    Returns:
        True if notification sent successfully, False otherwise
    """
    try:
        job_provider_description = await get_job_provider_description(
            job_provider_uid=job_provider_uid,
            job_provider_name=job_provider_name,
            extraction_data=extraction_data,
            linkedin_url=linkedin_url,
        )

        text = (
            f"Hey! Just wanted to let you know - your profile was just shown to "
            f"*{job_provider_name}* who's looking for candidates like you. "
            f"I'll keep you posted if they want to connect!"
        )

        job_provider = job_provider_name + " - " + job_provider_description
        template_payload = MsgComponents.template_scaffold(
            to=candidate_wa_id,
            template_name="profile_introduction",
            language_code="en",
            body_parameters=[candidate_name, job_provider],
        )
        result = WhatsAppSender.send(template_payload)
        success = result.get("status") == "success"
        print(f"📱 [NOTIFY] Sent template message to {candidate_wa_id}")

        # Log to conversation history for context continuity
        if success:
            conversation_history.save_message(
                user_id=candidate_wa_id,
                sender="agent",
                content=text,
                message_type="text",
                metadata={
                    "notification_type": "profile_presented",
                    "job_provider": job_provider_name,
                },
            )

        print(f"📱 [NOTIFY] Profile presented notification sent to {candidate_wa_id}")
        
        # Trigger candidate brag prompt for first intro
        # Check if this is the first intro for this candidate
        from services.candidate_brag_service import candidate_brag_service
        try:
            # Check if candidate has received any intros before
            intro_count_doc = fs.collection("candidate_intro_count").document(candidate_wa_id).get()
            is_first_intro = not intro_count_doc.exists or intro_count_doc.to_dict().get("count", 0) == 0
            
            if is_first_intro:
                # Update intro count
                fs.collection("candidate_intro_count").document(candidate_wa_id).set({
                    "count": 1,
                    "first_intro_at": time.time(),
                })
                
                # Send brag prompt for first intro
                await candidate_brag_service.send_brag_prompt(
                    candidate_uid=candidate_wa_id,
                    milestone="intro",
                    founder_name=job_provider_name,
                )
            else:
                # Increment count
                intro_data = intro_count_doc.to_dict() or {}
                fs.collection("candidate_intro_count").document(candidate_wa_id).update({
                    "count": intro_data.get("count", 0) + 1,
                })
        except Exception as e:
            print(f"⚠️ [BRAG] Failed to trigger brag prompt: {e}")
        
        return success

    except Exception as e:
        print(f"⚠️ [NOTIFY] Failed to notify candidate {candidate_wa_id}: {e}")
        return False


def notify_candidate_interview_scheduled(
    candidate_wa_id: str,
    hiring_user_name: str,
    interview_time: datetime,
    meet_link: str,
) -> bool:
    """
    Send WhatsApp notification to candidate about a scheduled interview.

    Args:
        candidate_wa_id: Candidate's WhatsApp ID (phone number)
        hiring_user_name: Name of the hiring manager
        interview_time: Scheduled interview time
        meet_link: Google Meet link for the interview

    Returns:
        True if notification sent successfully, False otherwise
    """
    try:

        if isinstance(interview_time, datetime):
            interview_time = pendulum.instance(interview_time)
            time_str = interview_time.to_rfc850_string()
        else:
            raise ValueError("interview_time must be a datetime object")

        text = (
            f"Great news! *{hiring_user_name}* wants to interview you!\n\n"
            f"Interview scheduled for *{time_str}*\n"
            f"Google Meet: {meet_link}\n\n"
            f"A calendar invite has been sent to your email. Good luck!"
        )

        template_payload = MsgComponents.template_scaffold(
            to=candidate_wa_id,
            template_name="interview_notif",
            language_code="en",
            body_parameters=[hiring_user_name, time_str, meet_link],
        )
        result = WhatsAppSender.send(template_payload)

        success = result.get("status") == "success"
        print(f"📱 [NOTIFY] Sent template message to {candidate_wa_id}")

        # Log to conversation history for context continuity
        if success:
            conversation_history.save_message(
                user_id=candidate_wa_id,
                sender="agent",
                content=text,
                message_type="text",
                metadata={
                    "notification_type": "interview_scheduled",
                    "hiring_user": hiring_user_name,
                    "interview_time": time_str,
                    "meet_link": meet_link,
                },
            )
        else:
            print("Response from WhatsAppSender.send():", str(result))
            raise ValueError("WhatsAppSender.send() returned an unexpected response")

        print(f"📱 [NOTIFY] Interview scheduled notification sent to {candidate_wa_id}")
        
        # Trigger candidate brag prompt for interview milestone
        from services.candidate_brag_service import candidate_brag_service
        try:
            import asyncio
            # Fire-and-forget async call
            asyncio.ensure_future(
                candidate_brag_service.send_brag_prompt(
                    candidate_uid=candidate_wa_id,
                    milestone="interview",
                    founder_name=hiring_user_name,
                )
            )
        except Exception as e:
            print(f"⚠️ [BRAG] Failed to trigger brag prompt: {e}")
        
        return success

    except Exception as e:
        print(f"⚠️ [NOTIFY] Failed to notify candidate {candidate_wa_id}: {e}")
        return False
