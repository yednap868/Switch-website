"""
Common tools available to all user types.
These tools handle profile management, voice calls, and basic networking.
"""

import json
import os
import traceback
from typing import Any, List, Literal, Optional

import requests
from pydantic import EmailStr
from pydantic_ai import RunContext

from agent.models import AgentDeps
from utils.db import fs, get_extraction_data, get_user_profile, save_data_merge
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender

# ElevenLabs configuration
try:
    from elevenlabs import ConversationInitiationClientDataRequestInput, ElevenLabs

    elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
    ELEVENLABS_PHONE_NUMBER_ID = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
except ImportError:
    elevenlabs_client = None
    ELEVENLABS_AGENT_ID = None
    ELEVENLABS_PHONE_NUMBER_ID = None


def log_user_profile(
    ctx: RunContext[AgentDeps],
    primary_goal: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[EmailStr] = None,
    linkedin_url: Optional[str] = None,
    user_type: Optional[str] = None,
) -> str:
    """
    Save or update the user's profile information.
    Use this tool whenever the user shares their name, email, LinkedIn, or goal.

    Args:
        primary_goal: User's primary goal (e.g., "hiring engineers", "looking for a job")
        name: User's full name
        email: User's email address
        linkedin_url: User's LinkedIn profile URL
        user_type: Classification - "job_seeker", "job_provider", or "general"
    """
    data = {}
    if primary_goal is not None:
        data["primary_goal"] = primary_goal
    if name is not None:
        data["name"] = name
    if email is not None:
        data["email"] = email
    if linkedin_url is not None:
        data["linkedin_url"] = linkedin_url
    if user_type is not None:
        data["user_type"] = user_type

    # If primary_goal is set and user_type is not explicitly provided, auto-detect user_type
    if primary_goal is not None and user_type is None:
        from agent.models import detect_user_type
        current_profile = get_user_profile(ctx.deps.uid) or {}
        temp_profile = {**current_profile, "primary_goal": primary_goal, "goal": primary_goal}
        detected_type = detect_user_type(temp_profile)
        detected_user_type_str = detected_type.value if hasattr(detected_type, 'value') else str(detected_type)
        if detected_user_type_str and detected_user_type_str != "general":
            data["user_type"] = detected_user_type_str
            print(f"[TOOL] log_user_profile: Auto-detected user_type='{detected_user_type_str}' from primary_goal='{primary_goal}'")

    if not data:
        return "No profile data provided to save."

    result = save_data_merge(ctx.deps.uid, "users", data)
    print(f"[TOOL] log_user_profile: {result}")
    
    # Check if text onboarding is complete and trigger broadcast
    try:
        from services.onboarding_broadcast_service import onboarding_broadcast_service
        import time
        if onboarding_broadcast_service._check_text_onboarding_complete(ctx.deps.uid):
            print(f"📢 [ONBOARD_BROADCAST] Text onboarding complete for {ctx.deps.uid}, triggering broadcast")
            # Mark onboarding completion time
            save_data_merge(ctx.deps.uid, "users", {"onboarding_completed_at": time.time()})
            onboarding_broadcast_service.broadcast_on_text_onboarding_complete(ctx.deps.uid)
    except Exception as e:
        print(f"⚠️ [ONBOARD_BROADCAST] Error checking/triggering broadcast: {e}")
    
    return f"Profile updated: {', '.join(data.keys())}"


def log_extraction_data(
    ctx: RunContext[AgentDeps],
    story: Optional[str] = None,
    current_focus: Optional[str] = None,
    future_vision: Optional[str] = None,
    top_priorities: Optional[List[str]] = None,
    urgent_needs: Optional[List[str]] = None,
) -> str:
    """
    Save core conversation data extracted from voice calls.
    This data is used for profile matching and context.

    Args:
        story: The user's background and journey
        current_focus: What the user is working on day-to-day
        future_vision: User's long-term goals (6-12 months)
        top_priorities: List of specific, measurable goals
        urgent_needs: Most pressing challenges needing immediate help
    """
    data = {}
    if story is not None:
        data["the_story"] = story
    if current_focus is not None:
        data["current_focus"] = current_focus
    if future_vision is not None:
        data["future_vision"] = future_vision
    if top_priorities is not None:
        data["top_priorities"] = top_priorities
    if urgent_needs is not None:
        data["urgent_needs"] = urgent_needs

    if not data:
        return "No extraction data provided to save."

    result = save_data_merge(ctx.deps.uid, "extractions", data)
    print(f"[TOOL] log_extraction_data: {result}")
    return f"Extraction data saved: {', '.join(data.keys())}"


def log_arbitrary_data(
    ctx: RunContext[AgentDeps],
    collection: Literal["users", "extractions"],
    key: str,
    value: Any,
) -> str:
    """
    Save miscellaneous key-value data not covered by other tools.
    Use 'users' for general info, 'extractions' for conversation details.

    Args:
        collection: Where to save - "users" or "extractions"
        key: The data key (e.g., "connection_type", "mentioned_competitors", "preferred_location")
        value: The data value
    """
    try:
        # If saving connection_type, also detect and set user_type automatically
        if collection == "users" and key == "connection_type":
            from agent.models import detect_user_type
            # Get current profile
            current_profile = get_user_profile(ctx.deps.uid) or {}
            # Create temp profile with connection_type to detect user type
            temp_profile = {**current_profile, "connection_type": str(value), "goal": str(value)}
            detected_type = detect_user_type(temp_profile)
            user_type_str = detected_type.value if hasattr(detected_type, 'value') else str(detected_type)
            
            # Save both connection_type and detected user_type at top level AND in arbitrary dict
            update_data = {
                "connection_type": value,
            }
            if user_type_str and user_type_str != "general":
                update_data["user_type"] = user_type_str
            
            # Save at top level
            save_data_merge(ctx.deps.uid, "users", update_data)
            
            # Also save in arbitrary dict for consistency
            doc_ref = fs.collection(collection).document(ctx.deps.uid)
            doc = doc_ref.get()
            if doc.exists:
                existing_arbitrary = doc.to_dict().get("arbitrary", {})
                existing_arbitrary[key] = value
                doc_ref.update({"arbitrary": existing_arbitrary, **update_data})
            else:
                doc_ref.set({"arbitrary": {key: value}, **update_data})
            
            if user_type_str and user_type_str != "general":
                print(f"[TOOL] log_arbitrary_data: Saved connection_type='{value}' and auto-detected user_type='{user_type_str}'")
                return f"Saved {key}='{value}' and auto-detected user_type='{user_type_str}'"
            else:
                print(f"[TOOL] log_arbitrary_data: Saved connection_type='{value}' (user_type could not be detected)")
                return f"Saved {key}='{value}'"
        
        # Normal flow for other keys
        doc_ref = fs.collection(collection).document(ctx.deps.uid)
        doc = doc_ref.get()
        if doc.exists:
            existing_arbitrary = doc.to_dict().get("arbitrary", {})
            existing_arbitrary[key] = value
            doc_ref.update({"arbitrary": existing_arbitrary})
        else:
            doc_ref.set({"arbitrary": {key: value}})

        msg = f"Saved '{key}' to {collection}"
        print(f"[TOOL] log_arbitrary_data: {msg}")
        return msg
    except Exception as e:
        traceback.print_exc()
        return f"Error saving data: {e}"


def start_voice_call(ctx: RunContext[AgentDeps]) -> str:
    """
    Initiate a voice call with the user via ElevenLabs.
    Only use this when the user has agreed to a call.
    """
    if (
        not elevenlabs_client
        or not ELEVENLABS_AGENT_ID
        or not ELEVENLABS_PHONE_NUMBER_ID
    ):
        return "Voice calling is not configured. Please check ElevenLabs settings."

    try:
        from agent.models import detect_user_type
        
        profile = get_user_profile(ctx.deps.uid) or {}
        
        # Detect user type from profile
        user_type = detect_user_type(profile)
        user_type_str = user_type.value if hasattr(user_type, 'value') else str(user_type)
        
        # Extract connection_type from profile (from WhatsApp conversation)
        connection_type = (
            profile.get("connection_type")
            or profile.get("goal")
            or profile.get("primary_goal")
            or profile.get("arbitrary", {}).get("connection_type")
            or profile.get("profile", {}).get("connection_type")
            or profile.get("profile", {}).get("goal")
            or ""
        )
        
        # Clean up connection_type for job providers (remove "hiring", "looking to hire", etc.)
        if user_type_str == "job_provider" and connection_type:
            connection_type_clean = connection_type.lower()
            # Remove common prefixes
            for prefix in ["hiring", "looking to hire", "looking for", "need to hire", "recruiting"]:
                if connection_type_clean.startswith(prefix):
                    connection_type_clean = connection_type_clean[len(prefix):].strip()
                    break
            # If it still has "for" at the start, remove it
            if connection_type_clean.startswith("for "):
                connection_type_clean = connection_type_clean[4:].strip()
            connection_type = connection_type_clean if connection_type_clean else connection_type
        # For job seekers, keep as is (e.g., "full stack roles", "founders hiring engineers")
        
        # Extract connection_type from primary_goal if it contains hiring/job-seeking info
        primary_goal = profile.get("primary_goal", "") or ""
        if not connection_type and primary_goal:
            # For job providers: extract what they're hiring
            if user_type_str == "job_provider":
                # "hiring full stack engineers" → "full stack engineers"
                primary_goal_lower = primary_goal.lower()
                for prefix in ["hiring", "looking to hire", "looking for", "need to hire", "recruiting"]:
                    if primary_goal_lower.startswith(prefix):
                        connection_type = primary_goal[len(prefix):].strip()
                        if connection_type.startswith("for "):
                            connection_type = connection_type[4:].strip()
                        break
            elif user_type_str == "job_seeker":
                # For job seekers, use primary_goal as-is or extract role type
                # "looking for full stack roles" → "full stack roles"
                primary_goal_lower = primary_goal.lower()
                if "looking for" in primary_goal_lower:
                    parts = primary_goal.split("looking for", 1)
                    if len(parts) > 1:
                        connection_type = parts[1].strip()
                    else:
                        connection_type = primary_goal
                else:
                    connection_type = primary_goal
        
        # Determine call_type for Switch voice agent based on user_type
        # This ensures proper routing in both the voice agent and post-call webhook
        if user_type_str == "job_provider":
            call_type = "business_inbound"
        elif user_type_str == "job_seeker":
            call_type = "candidate_inbound"
        else:
            call_type = ""  # General users don't have a specific Switch call type

        elevenlabs_client.conversational_ai.twilio.outbound_call(
            agent_id=ELEVENLABS_AGENT_ID,
            agent_phone_number_id=ELEVENLABS_PHONE_NUMBER_ID,
            to_number=ctx.deps.uid,
            conversation_initiation_client_data=ConversationInitiationClientDataRequestInput(
                user_id=ctx.deps.uid,
                dynamic_variables={
                    "call_type": call_type,
                    "name": profile.get("name", ""),
                    "uid": ctx.deps.uid,
                    "user_type": user_type_str,
                    "connection_type": connection_type or "",
                    "primary_goal": primary_goal or connection_type or "",
                    "profile": json.dumps(profile, default=str, indent=4),
                },
            ),
        )

        print(f"[TOOL] start_voice_call: Call initiated for {ctx.deps.uid}")
        return "Call initiated. The user should receive a call shortly."
    except Exception as e:
        traceback.print_exc()
        return f"Failed to initiate call: {e}"


def save_linkedin_profile_url(ctx: RunContext[AgentDeps], linkedin_url: str) -> str:
    """
    Save and process a LinkedIn profile URL.
    Scrapes the profile, creates a summary, and adds to vector DB.

    Args:
        linkedin_url: The user's LinkedIn profile URL
    """
    try:
        api_key = os.getenv("SCRAPINGDOG_API_KEY")
        if not api_key:
            # Just save the URL without scraping
            save_data_merge(ctx.deps.uid, "users", {"linkedin_url": linkedin_url})
            return "LinkedIn URL saved (scraping not configured)."

        url = "https://api.scrapingdog.com/linkedin"
        linkedin_id = linkedin_url.strip("/").split("/")[-1]

        params = {
            "api_key": api_key,
            "type": "profile",
            "linkId": linkedin_id,
            "premium": "true",
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            # Save URL even if scraping fails
            save_data_merge(ctx.deps.uid, "users", {"linkedin_url": linkedin_url})
            return "LinkedIn URL saved (could not scrape profile details)."

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        relevant_keys = [
            "fullName",
            "first_name",
            "last_name",
            "headline",
            "location",
            "about",
        ]

        filtered_data = {k: v for k, v in data.items() if k in relevant_keys}

        # Save to user profile
        save_data_merge(
            ctx.deps.uid,
            "users",
            {
                "linkedin_url": linkedin_url,
                "linkedin_data": filtered_data,
            },
        )

        print(f"[TOOL] save_linkedin_profile_url: Saved for {ctx.deps.uid}")
        
        # Check if text onboarding is complete and trigger broadcast
        try:
            from services.onboarding_broadcast_service import onboarding_broadcast_service
            import time
            if onboarding_broadcast_service._check_text_onboarding_complete(ctx.deps.uid):
                print(f"📢 [ONBOARD_BROADCAST] Text onboarding complete for {ctx.deps.uid}, triggering broadcast")
                # Mark onboarding completion time
                save_data_merge(ctx.deps.uid, "users", {"onboarding_completed_at": time.time()})
                onboarding_broadcast_service.broadcast_on_text_onboarding_complete(ctx.deps.uid)
        except Exception as e:
            print(f"⚠️ [ONBOARD_BROADCAST] Error checking/triggering broadcast: {e}")
        
        return f"LinkedIn profile saved: {filtered_data.get('fullName', 'Unknown')}"
    except Exception as e:
        traceback.print_exc()
        save_data_merge(ctx.deps.uid, "users", {"linkedin_url": linkedin_url})
        return f"LinkedIn URL saved (error processing: {e})"


def search_database_connections(
    ctx: RunContext[AgentDeps],
    search_query: str,
    max_results: int = 5,
) -> str:
    """
    Search the internal database for matching profiles.
    Uses semantic search over user profiles in Qdrant.

    Args:
        search_query: Keywords or description of who to find
        max_results: Maximum number of results to return
    """
    try:
        from utils.qdrant import Search

        search = Search("UserProfiles")
        results = search.query(search_query, limit=max_results)

        if not results:
            return "No matching profiles found in the network."

        formatted_results = []
        for result in results:
            metadata = result.get("metadata", {})
            name = metadata.get("name", "Unknown")
            headline = metadata.get("headline", "")
            linkedin = metadata.get("linkedin_url", "")

            formatted = f"- {name}"
            if headline:
                formatted += f" ({headline})"
            if linkedin:
                formatted += f"\n  LinkedIn: {linkedin}"
            formatted_results.append(formatted)

        return f"Found {len(formatted_results)} profiles:\n\n" + "\n\n".join(
            formatted_results
        )
    except Exception as e:
        traceback.print_exc()
        return f"Error searching database: {e}"


def share_contact_card(ctx: RunContext[AgentDeps]) -> str:
    """
    Share Switch's contact card with the user to enable referrals.
    """
    try:
        vance_name = os.getenv("SELF_NAME", "Switch")
        vance_phone = os.getenv("VANCE_PHONE", "+1234567890")
        vance_email = os.getenv("SELF_EMAIL", "switch@switchlocally.com")

        contact_data = MsgComponents.contact_card_scaffold(
            to=ctx.deps.uid, name=vance_name, phone=vance_phone, email=vance_email
        )

        sender = WhatsAppSender()
        sender.send(data=contact_data)

        user_name = ctx.deps.profile.get("name", "User")
        print(f"[TOOL] share_contact_card: Shared with {ctx.deps.uid}")
        return f"Contact card shared. Users can introduce others with: 'Hi Switch, {user_name} introduced us.'"
    except Exception as e:
        traceback.print_exc()
        return f"Could not share contact card: {e}"


def request_network_referral(ctx: RunContext[AgentDeps]) -> str:
    """
    Ask the user to introduce Switch to valuable people in their network.
    Use this after successful interactions.
    """
    try:
        user_name = ctx.deps.profile.get("name", "there")

        referral_message = (
            f"Hey {user_name}! Now that we've connected, would you mind introducing me "
            "to anyone in your network who might benefit from smart introductions? "
            "You can share my contact card with them, and they can reach out directly."
        )

        message_data = MsgComponents.text_scaffold(
            to=ctx.deps.uid, text=referral_message
        )

        sender = WhatsAppSender()
        sender.send(data=message_data)

        print(f"[TOOL] request_network_referral: Requested from {ctx.deps.uid}")
        return "Referral request sent to the user."
    except Exception as e:
        traceback.print_exc()
        return f"Could not send referral request: {e}"


# List of common tools available to all user types
# ==========================================================================
# VANCE-SPECIFIC TOOLS DISABLED - Switch doesn't use professional networking
# ==========================================================================
COMMON_TOOLS = [
    log_user_profile,
    log_extraction_data,
    log_arbitrary_data,
    start_voice_call,
    # save_linkedin_profile_url,    # DISABLED - Vance (professional networking)
    # search_database_connections,  # DISABLED - Vance database search
    # share_contact_card,           # DISABLED - Vance feature
    # request_network_referral,     # DISABLED - Vance feature
]
