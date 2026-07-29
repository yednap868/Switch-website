"""
Switch-specific tools for job providers.
These tools search switch_users collection and send profile cards via WhatsApp.
"""

import traceback
from typing import Optional

from pydantic_ai import RunContext

from agent.models import AgentDeps
from services.switch_matching_service import switch_matching_service, SwitchCandidate
from services.switch_profile_card_service import switch_profile_card_service
from services.switch_interview_service import switch_interview_service
from models.switch_models import Job
from utils.db import fs, get_user_profile
from utils.whatsapp.whatsapp import WhatsAppSender


async def send_switch_candidates(
    ctx: RunContext[AgentDeps],
    role: str = "Staff",
    location: str = "Delhi NCR",
    max_results: int = 3,
) -> str:
    """
    Search for available candidates in Switch and send their profile cards via WhatsApp.
    Use this when a business asks for candidates, workers, or staff.

    Args:
        role: The job role needed (e.g., "Waiter", "Helper", "Sales", "Kitchen", "Delivery")
        location: Job location/area (e.g., "Delhi NCR", "Gurgaon", "Noida")
        max_results: Maximum candidates to send (default 3)
    """
    try:
        business_phone = ctx.deps.uid
        print(f"🔍 [SWITCH_TOOL] send_switch_candidates called for {business_phone}")
        print(f"🔍 [SWITCH_TOOL] Role: {role}, Location: {location}, Max: {max_results}")

        # Create a Job object for matching
        job = Job(
            id=f"job_{business_phone}_{int(__import__('time').time())}",
            business_id=business_phone,
            role=role,
            positions_count=1,
            salary_min=8000,
            salary_max=15000,
            experience_required="Fresher",
            location=location,
            interview_address=location,
        )

        # Find matching candidates
        matching_candidates = switch_matching_service.find_matching_candidates(job, limit=max_results)

        # FALLBACK: If no matches, get ANY candidates
        if not matching_candidates:
            print(f"⚠️ [SWITCH_TOOL] No matching candidates, trying fallback...")
            matching_candidates = switch_matching_service.find_any_candidates_fallback(limit=max_results)

        if not matching_candidates:
            print(f"⚠️ [SWITCH_TOOL] No candidates found even in fallback")
            return f"Abhi {role} ke liye koi matching candidate nahi mila. Jaise hi milega, turant bhej dungi! 👍"

        print(f"✅ [SWITCH_TOOL] Found {len(matching_candidates)} candidates")

        # Store pending candidates for interview selection
        switch_interview_service.store_pending_candidates(business_phone, matching_candidates)

        # Send profile cards via WhatsApp
        sender = WhatsAppSender()
        sent_count = 0

        for i, candidate in enumerate(matching_candidates[:max_results], 1):
            try:
                # Generate profile card image
                print(f"🎨 [SWITCH_TOOL] Generating profile card for {candidate.name}...")
                card_bytes = switch_profile_card_service.generate_profile_card(candidate)
                print(f"🎨 [SWITCH_TOOL] Card generated, size: {len(card_bytes)} bytes")

                # Create caption
                caption = f"*Candidate {i}: {candidate.name}*\n"
                if candidate.area:
                    caption += f"📍 {candidate.area}\n"
                if candidate.experience_level:
                    caption += f"💼 {candidate.experience_level}\n"
                caption += f"💰 ₹{candidate.expected_salary_min:,}-{candidate.expected_salary_max:,}/month"

                # Send the profile card image
                print(f"📤 [SWITCH_TOOL] Uploading and sending image to {business_phone}...")
                result = sender.send_image(
                    to=business_phone,
                    image_bytes=card_bytes,
                    caption=caption
                )
                print(f"📤 [SWITCH_TOOL] send_image result: {result}")

                if result.get("status") == "success":
                    print(f"✅ [SWITCH_TOOL] Sent profile card {i} for {candidate.name}")
                    sent_count += 1
                else:
                    print(f"❌ [SWITCH_TOOL] Failed to send image: {result.get('error')}")
                    raise Exception(result.get('error', 'Unknown error'))

                # Small delay between messages
                import asyncio
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"❌ [SWITCH_TOOL] Error sending profile card for {candidate.name}: {e}")
                traceback.print_exc()
                # Fall back to text message
                text_msg = {
                    "messaging_product": "whatsapp",
                    "to": business_phone,
                    "type": "text",
                    "text": {
                        "body": f"*Candidate {i}: {candidate.name}*\n📍 {candidate.area}\n💼 {candidate.experience_level}\n💰 ₹{candidate.expected_salary_min:,}-{candidate.expected_salary_max:,}/month"
                    }
                }
                sender.send(text_msg)
                sent_count += 1

        if sent_count > 0:
            return f"Maine {sent_count} candidates bhej diye hain! 👆\n\nKoi pasand aaya? Reply karo 'YES 1' ya 'YES 2' candidate number ke saath, interview fix kar dungi! 😊"
        else:
            return "Candidates bhejne mein problem hui. Please thodi der baad try karo."

    except Exception as e:
        print(f"❌ [SWITCH_TOOL] Error in send_switch_candidates: {e}")
        traceback.print_exc()
        return f"Error finding candidates: {e}"


async def find_switch_candidates(
    ctx: RunContext[AgentDeps],
    role: str = "",
    location: str = "",
) -> str:
    """
    Find available candidates in Switch database (without sending profile cards).
    Returns a text summary of matching candidates.

    Args:
        role: Job role to search for
        location: Location/area preference
    """
    try:
        print(f"🔍 [SWITCH_TOOL] find_switch_candidates: role={role}, location={location}")

        # Get all available candidates
        candidates = switch_matching_service.find_all_available_candidates(limit=10)

        if not candidates:
            # Try fallback
            candidates = switch_matching_service.find_any_candidates_fallback(limit=5)

        if not candidates:
            return "Abhi database mein koi available candidate nahi hai."

        # Format as text list
        result = f"Found {len(candidates)} candidates:\n\n"
        for i, c in enumerate(candidates[:5], 1):
            result += f"{i}. *{c.name}*\n"
            if c.area:
                result += f"   📍 {c.area}\n"
            if c.experience_level:
                result += f"   💼 {c.experience_level}\n"
            if c.preferred_roles:
                result += f"   🎯 {', '.join(c.preferred_roles[:2])}\n"
            result += "\n"

        return result

    except Exception as e:
        print(f"❌ [SWITCH_TOOL] Error in find_switch_candidates: {e}")
        traceback.print_exc()
        return f"Error: {e}"


# List of Switch-specific tools
SWITCH_TOOLS = [
    send_switch_candidates,
    find_switch_candidates,
]
