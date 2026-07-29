"""
Tools for candidates to track their milestones and trigger brag prompts.
"""

import time

from pydantic_ai import RunContext

from agent.models import AgentDeps
from services.candidate_brag_service import candidate_brag_service
from utils.db import fs


async def mark_offer_received(
    ctx: RunContext[AgentDeps],
    company_name: str = "",
    role_title: str = "",
) -> str:
    """
    Mark that candidate received an offer.
    This triggers the brag prompt for the "offer" milestone.

    Args:
        company_name: Name of the company offering the role
        role_title: Title of the role offered
    """
    try:
        # Store offer record
        offer_data = {
            "candidate_uid": ctx.deps.uid,
            "company_name": company_name,
            "role_title": role_title,
            "received_at": time.time(),
        }
        
        # Store in Firestore
        fs.collection("candidate_offers").add(offer_data)
        
        # Trigger brag prompt
        await candidate_brag_service.send_brag_prompt(
            candidate_uid=ctx.deps.uid,
            milestone="offer",
            founder_name=company_name,
        )
        
        return (
            f"🎉 Congratulations on the offer!"
            + (f" from {company_name}" if company_name else "")
            + (f" for {role_title}" if role_title else "")
            + "!\n\n"
            "Check your messages for share templates to celebrate!"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error marking offer: {e}"


async def mark_hired(
    ctx: RunContext[AgentDeps],
    company_name: str = "",
    role_title: str = "",
) -> str:
    """
    Mark that candidate was hired.
    This triggers the brag prompt for the "hired" milestone.

    Args:
        company_name: Name of the company
        role_title: Title of the role
    """
    try:
        import time
        
        # Store hire record
        hire_data = {
            "candidate_uid": ctx.deps.uid,
            "company_name": company_name,
            "role_title": role_title,
            "hired_at": time.time(),
        }
        
        # Store in Firestore
        fs.collection("candidate_hires").add(hire_data)
        
        # Trigger brag prompt
        await candidate_brag_service.send_brag_prompt(
            candidate_uid=ctx.deps.uid,
            milestone="hired",
            founder_name=company_name,
        )
        
        return (
            f"🎉🎉🎉 Congratulations on getting hired!"
            + (f" at {company_name}" if company_name else "")
            + (f" as {role_title}" if role_title else "")
            + "!\n\n"
            "Check your messages for share templates to celebrate your success!"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error marking hire: {e}"


# List of tools available to candidates
CANDIDATE_TOOLS = [
    mark_offer_received,
    mark_hired,
]

