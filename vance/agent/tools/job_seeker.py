"""
Tools specific to job seekers.
These tools handle job opportunity discovery and application.
"""

import traceback
from typing import Optional

import pendulum
from pydantic_ai import RunContext

from agent.models import AgentDeps
from utils.db import fs, get_extraction_data, get_user_profile, save_data_merge
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


def search_job_opportunities(
    ctx: RunContext[AgentDeps],
    role: str = "",
    skills: str = "",
    location: str = "",
    work_model: str = "",
    max_results: int = 5,
) -> str:
    """
    Search for job opportunities matching the job seeker's profile.
    Finds companies/hiring managers looking for candidates like you.

    Args:
        role: Target role (e.g., "Python Developer", "Product Manager")
        skills: Your key skills (e.g., "Python, Django, React")
        location: Preferred location or "Remote"
        work_model: "Remote", "Hybrid", or "On-site"
        max_results: Maximum opportunities to return
    """
    try:
        # Build search query from parameters and extraction data
        extraction_data = get_extraction_data(ctx.deps.uid) or {}
        profile = get_user_profile(ctx.deps.uid) or {}

        search_parts = []

        # Use provided parameters or fall back to profile data
        target_role = role or extraction_data.get("target_role", "")
        if target_role:
            search_parts.append(f"hiring {target_role}")

        user_skills = skills or extraction_data.get("core_skills", "")
        if user_skills:
            search_parts.append(f"skills: {user_skills}")

        user_location = location or extraction_data.get("current_location", "")
        if user_location:
            search_parts.append(f"location: {user_location}")

        if work_model:
            search_parts.append(f"work: {work_model}")

        if not search_parts:
            return (
                "I need more information about what you're looking for. "
                "What role are you interested in, and what are your key skills?"
            )

        search_query = " ".join(search_parts)
        print(f"[TOOL] search_job_opportunities: Query = {search_query}")

        # Lazy import to avoid blocking at module load
        from utils.qdrant import Search

        # Search for job providers (hiring managers)
        search = Search("UserProfiles")

        # Filter for job providers
        results = search.query(search_query, limit=max_results * 2)

        # Filter to only job_provider intent
        job_opportunities = []
        for result in results:
            payload = result.payload or {}
            intent = payload.get("intent", "").lower()
            user_type = payload.get("user_type", "").lower()

            # Only include job providers / hiring intent
            if (
                intent in ("hiring_need", "recruiter_need")
                or user_type == "job_provider"
            ):
                job_opportunities.append(payload)
                if len(job_opportunities) >= max_results:
                    break

        if not job_opportunities:
            return (
                "No matching job opportunities found right now. "
                "I'll keep looking and notify you when something comes up. "
                "Meanwhile, would you like to refine your search criteria?"
            )

        # Store opportunities for later
        save_data_merge(
            ctx.deps.uid, "users", {"viewed_opportunities": job_opportunities}
        )

        # Format results
        formatted = ["Here are some opportunities that might interest you:\n"]

        for i, opp in enumerate(job_opportunities, 1):
            name = opp.get("name", "Company")
            job_title = opp.get("job_title", opp.get("primary_goal", "Open Role"))
            location = opp.get("office_location", "Location not specified")
            company = opp.get("company", "")

            formatted.append(f"*{i}. {job_title}*")
            if company:
                formatted.append(f"   Company: {company}")
            formatted.append(f"   Contact: {name}")
            formatted.append(f"   Location: {location}")
            formatted.append("")

        formatted.append(
            "Let me know which opportunities interest you, and I can help you connect!"
        )

        return "\n".join(formatted)

    except Exception as e:
        traceback.print_exc()
        return f"Error searching for opportunities: {e}"


def express_interest(
    ctx: RunContext[AgentDeps],
    opportunity_number: int,
    message: str = "",
) -> str:
    """
    Express interest in a job opportunity.
    This will notify the hiring manager about your interest.

    Args:
        opportunity_number: The opportunity number from the search results (1-indexed)
        message: Optional personal message to include
    """
    try:
        # Get stored opportunities
        profile = get_user_profile(ctx.deps.uid) or {}
        opportunities = profile.get("viewed_opportunities", [])

        if not opportunities:
            return "No opportunities available. Please search for jobs first."

        if opportunity_number < 1 or opportunity_number > len(opportunities):
            return f"Invalid opportunity number. Please choose from 1 to {len(opportunities)}."

        opportunity = opportunities[opportunity_number - 1]
        hiring_manager_id = opportunity.get("uid")

        if not hiring_manager_id:
            return "Unable to connect with this opportunity. The hiring manager hasn't set up their profile."

        # Store the interest
        interest_data = {
            "seeker_uid": ctx.deps.uid,
            "seeker_name": profile.get("name", "Job Seeker"),
            "seeker_email": profile.get("email", ""),
            "seeker_linkedin": profile.get("linkedin_url", ""),
            "opportunity": opportunity,
            "message": message,
            "status": "pending",
            "created_at": str(pendulum.now()),
        }

        # Save to interests collection
        fs.collection("job_interests").add(interest_data)

        # Notify hiring manager via WhatsApp
        try:
            seeker_name = profile.get("name", "A candidate")
            job_title = opportunity.get(
                "job_title", opportunity.get("primary_goal", "your open role")
            )

            notification = (
                f"Hey! Good news - {seeker_name} is interested in {job_title}.\n\n"
            )
            if profile.get("linkedin_url"):
                notification += f"LinkedIn: {profile['linkedin_url']}\n"
            if message:
                notification += f"\nTheir message: {message}\n"
            notification += "\nWould you like me to set up an introduction?"

            msg_data = MsgComponents.text_scaffold(
                to=hiring_manager_id, text=notification
            )
            sender = WhatsAppSender()
            sender.send(data=msg_data)
        except Exception as e:
            print(f"[TOOL] Failed to notify hiring manager: {e}")

        hiring_name = opportunity.get("name", "the hiring manager")
        return (
            f"I've notified {hiring_name} about your interest. "
            f"I'll let you know when they respond!"
        )

    except Exception as e:
        traceback.print_exc()
        return f"Error expressing interest: {e}"


def update_job_preferences(
    ctx: RunContext[AgentDeps],
    target_role: Optional[str] = None,
    core_skills: Optional[str] = None,
    work_experience: Optional[str] = None,
    current_location: Optional[str] = None,
    salary_expectations: Optional[str] = None,
    work_model_preference: Optional[str] = None,
    relocation_openness: Optional[str] = None,
) -> str:
    """
    Update your job search preferences.
    This helps me find better matching opportunities.

    Args:
        target_role: The role you're looking for
        core_skills: Your key skills (comma-separated)
        work_experience: Years of experience or experience summary
        current_location: Your current location
        salary_expectations: Your salary expectations
        work_model_preference: "Remote", "Hybrid", or "On-site"
        relocation_openness: "Yes", "No", or specific locations
    """
    try:
        data = {}
        if target_role is not None:
            data["target_role"] = target_role
        if core_skills is not None:
            data["core_skills"] = core_skills
        if work_experience is not None:
            data["work_experience"] = work_experience
        if current_location is not None:
            data["current_location"] = current_location
        if salary_expectations is not None:
            data["salary_expectations"] = salary_expectations
        if work_model_preference is not None:
            data["work_model_preference"] = work_model_preference
        if relocation_openness is not None:
            data["relocation_openness"] = relocation_openness

        if not data:
            return "No preferences provided to update."

        save_data_merge(ctx.deps.uid, "extractions", data)

        # Update intent in profile
        save_data_merge(ctx.deps.uid, "users", {"intent": "job_seeker_need"})

        updated = ", ".join(data.keys())
        print(f"[TOOL] update_job_preferences: Updated {updated}")
        return f"Job preferences updated: {updated}. I'll use these to find better matches!"

    except Exception as e:
        traceback.print_exc()
        return f"Error updating preferences: {e}"


def get_application_status(ctx: RunContext[AgentDeps]) -> str:
    """
    Check the status of your job applications/interests.
    """
    try:
        # Query interests collection for this seeker
        interests = (
            fs.collection("job_interests")
            .where("seeker_uid", "==", ctx.deps.uid)
            .stream()
        )

        applications = []
        for interest in interests:
            data = interest.to_dict()
            opp = data.get("opportunity", {})
            applications.append(
                {
                    "role": opp.get("job_title", opp.get("primary_goal", "Unknown")),
                    "company": opp.get("company", opp.get("name", "Unknown")),
                    "status": data.get("status", "pending"),
                    "created_at": data.get("created_at", ""),
                }
            )

        if not applications:
            return (
                "You haven't expressed interest in any opportunities yet. "
                "Would you like me to search for jobs that match your profile?"
            )

        formatted = ["Your applications:\n"]
        for i, app in enumerate(applications, 1):
            status_emoji = {
                "pending": "⏳",
                "viewed": "👀",
                "interested": "✅",
                "declined": "❌",
            }.get(app["status"], "📝")

            formatted.append(
                f"{i}. {app['role']} at {app['company']} {status_emoji} {app['status'].title()}"
            )

        return "\n".join(formatted)

    except Exception as e:
        traceback.print_exc()
        return f"Error checking application status: {e}"


def request_intro_to_broadcast_person(ctx: RunContext[AgentDeps]) -> str:
    """
    When a candidate responds "I need intro" to a broadcast message about a job provider/founder.
    
    This tool:
    1. Finds the broadcast context from conversation history
    2. Sends message to candidate: "Cool, I have sent them a note and will notify you once they approve"
    3. Sends message to job provider: "{candidate_name} wants to connect with you, should I schedule a call?"
    
    Use this when a candidate (job seeker) says "I need intro" in response to a broadcast.
    """
    try:
        from api.whatsapp_modules.conversation_history import conversation_history
        
        # Get candidate info
        candidate_profile = get_user_profile(ctx.deps.uid) or {}
        candidate_name = candidate_profile.get("name", "A candidate")
        candidate_wa_id = (
            candidate_profile.get("wa_id")
            or candidate_profile.get("phone")
            or candidate_profile.get("whatsapp")
            or ctx.deps.uid
        )
        
        # Get recent conversation history to find broadcast context
        messages = conversation_history.get_recent_messages(ctx.deps.uid, limit=20)
        
        # Find the most recent broadcast message
        broadcast_context = None
        for msg in reversed(messages):  # Start from most recent
            metadata = msg.get("metadata", {}) or {}
            if metadata.get("type") == "onboarding_broadcast" or msg.get("type") in ("broadcast", "template"):
                broadcast_context = metadata
                break
        
        if not broadcast_context:
            return "I couldn't find the broadcast message you're responding to. Who are you interested in connecting with?"
        
        # Get the broadcasted person's info
        broadcasted_user_id = broadcast_context.get("broadcasted_user_id")
        broadcasted_user_name = broadcast_context.get("broadcasted_user_name", "someone")
        
        if not broadcasted_user_id:
            return "I couldn't find who you're interested in. Could you tell me their name?"
        
        # Get the job provider's profile and WhatsApp ID
        job_provider_profile = get_user_profile(broadcasted_user_id) or {}
        job_provider_wa_id = (
            job_provider_profile.get("wa_id")
            or job_provider_profile.get("phone")
            or job_provider_profile.get("whatsapp")
            or broadcasted_user_id
        )
        
        # Send message to candidate
        candidate_message = "Cool, I have sent them a note and will notify you once they approve."
        sender = WhatsAppSender()
        candidate_payload = MsgComponents.text_scaffold(to=candidate_wa_id, text=candidate_message)
        sender.send(data=candidate_payload)
        
        # Send message to job provider
        job_provider_message = f"{candidate_name} wants to connect with you, should I schedule a call?"
        job_provider_payload = MsgComponents.text_scaffold(to=job_provider_wa_id, text=job_provider_message)
        sender.send(data=job_provider_payload)
        
        # Save the intro request for tracking
        intro_request = {
            "candidate_uid": ctx.deps.uid,
            "candidate_name": candidate_name,
            "job_provider_uid": broadcasted_user_id,
            "job_provider_name": broadcasted_user_name,
            "status": "pending",
            "requested_at": str(pendulum.now()),
        }
        fs.collection("intro_requests").add(intro_request)
        
        print(f"✅ [INTRO_REQUEST] Candidate {ctx.deps.uid} requested intro to {broadcasted_user_id}")
        
        return candidate_message
        
    except Exception as e:
        traceback.print_exc()
        return f"Error requesting intro: {e}"


# List of tools available to job seekers
# ==========================================================================
# VANCE TOOLS DISABLED - Switch uses its own data extraction via voice calls
# These tools search the Vance database (professional networking), not Switch
# ==========================================================================
JOB_SEEKER_TOOLS = [
    # search_job_opportunities,       # DISABLED - Vance database
    # express_interest,               # DISABLED - Vance workflow
    # update_job_preferences,         # DISABLED - Vance workflow
    # get_application_status,         # DISABLED - Vance workflow
    # request_intro_to_broadcast_person,  # DISABLED - Vance workflow
]
