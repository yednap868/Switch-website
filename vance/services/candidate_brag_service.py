"""
Candidate brag service for sharing success stories on social media.

Triggers:
1. Candidate receives first founder intro
2. Candidate progresses to interview stage
3. Candidate gets offer
4. Candidate hired
"""

import time
from typing import Optional

from utils.db import fs, get_user_profile
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


class CandidateBragService:
    """Service for managing candidate brag/share workflow."""

    def __init__(self):
        self.sender = WhatsAppSender()

    def _generate_share_templates(self, milestone: str, founder_name: Optional[str] = None) -> dict:
        """
        Generate share templates for different platforms.
        
        Args:
            milestone: "intro", "interview", "offer", "hired"
            founder_name: Optional founder name for personalization
        
        Returns:
            Dict with linkedin, twitter, whatsapp templates
        """
        base_message = "I stopped applying to 200 jobs.\n\nInstead I used Switch — where businesses directly messaged me for real opportunities."
        
        if milestone == "intro":
            milestone_text = "Already got intro(s) lined up 🔥"
        elif milestone == "interview":
            milestone_text = "Already got interview(s) lined up 🔥"
        elif milestone == "offer":
            milestone_text = "Just got an offer! 🔥"
        elif milestone == "hired":
            milestone_text = "Just got hired! 🔥"
        else:
            milestone_text = "Already got opportunities lined up 🔥"
        
        closing = "If you're looking for opportunities, just use Switch."

        # LinkedIn post template
        linkedin_post = f"{base_message}\n\n{milestone_text}\n\n{closing}\n\n#JobSearch #LocalJobs #Switch"
        
        # Twitter/X template (280 char limit)
        twitter_post = f"{base_message} {milestone_text} {closing}"
        if len(twitter_post) > 280:
            # Truncate if needed
            twitter_post = f"{base_message[:200]}... {milestone_text} {closing}"
        
        # WhatsApp forward message
        whatsapp_message = f"{base_message}\n\n{milestone_text}\n\n{closing}\n\nTry Vance: https://api.whatsapp.com/message/M3TFOBX5HZDJJ1?autoload=1&app_absent=0"
        
        return {
            "linkedin": linkedin_post,
            "twitter": twitter_post,
            "whatsapp": whatsapp_message,
        }

    def should_send_brag_prompt(self, candidate_uid: str, milestone: str) -> bool:
        """
        Check if brag prompt should be sent (idempotency check).
        Only send once per milestone per candidate.
        """
        prompt_doc = fs.collection("candidate_brag_prompts").document(candidate_uid).get()
        
        if prompt_doc.exists:
            prompt_data = prompt_doc.to_dict() or {}
            milestones_sent = prompt_data.get("milestones_sent", [])
            
            if milestone in milestones_sent:
                print(f"ℹ️ [BRAG] Brag prompt for '{milestone}' already sent to {candidate_uid}")
                return False
        
        return True

    async def send_brag_prompt(
        self,
        candidate_uid: str,
        milestone: str,
        founder_name: Optional[str] = None,
        location: str = "",
    ) -> bool:
        """
        Send brag/share prompt to candidate via WhatsApp.
        
        Args:
            candidate_uid: Candidate's user ID
            milestone: "intro", "interview", "offer", "hired"
            founder_name: Optional founder name for personalization
            location: Optional location of founder (empty by default)
        """
        try:
            # Check if should send
            if not self.should_send_brag_prompt(candidate_uid, milestone):
                return False

            # Get candidate's WhatsApp ID
            user_profile = get_user_profile(candidate_uid) or {}
            wa_id = (
                user_profile.get("wa_id")
                or user_profile.get("phone")
                or user_profile.get("whatsapp")
                or candidate_uid
            )

            # Generate share templates
            templates = self._generate_share_templates(milestone, founder_name)
            
            # Build celebratory message
            location_text = f"{location} " if location else ""
            if milestone == "intro":
                celebration = f"🎉 Nice! You just got an intro to a {location_text}founder via Vance."
            elif milestone == "interview":
                celebration = f"🎉 Nice! You just got an interview with a {location_text}founder via Vance."
            elif milestone == "offer":
                celebration = f"🎉 Amazing! You just got an offer from a {location_text}founder via Vance!"
            elif milestone == "hired":
                celebration = f"🎉 Congratulations! You just got hired by a {location_text}founder via Vance!"
            else:
                celebration = f"🎉 Nice! You just got an opportunity from a {location_text}founder via Vance."

            # Build message with share options
            message = (
                f"{celebration}\n"
                f"Want to share your journey?\n\n"
                f"📱 *LinkedIn Post:*\n"
                f"{templates['linkedin']}\n\n"
                f"🐦 *Twitter/X Post:*\n"
                f"{templates['twitter']}\n\n"
                f"💬 *WhatsApp Forward:*\n"
                f"{templates['whatsapp']}"
            )

            result = self.sender.send(data=MsgComponents.text_scaffold(to=wa_id, text=message))

            # Track that prompt was sent
            prompt_doc = fs.collection("candidate_brag_prompts").document(candidate_uid).get()
            if prompt_doc.exists:
                prompt_data = prompt_doc.to_dict() or {}
                milestones_sent = prompt_data.get("milestones_sent", [])
                if milestone not in milestones_sent:
                    milestones_sent.append(milestone)
            else:
                milestones_sent = [milestone]
                prompt_data = {}

            prompt_data.update({
                f"{milestone}_sent_at": time.time(),
                "milestones_sent": milestones_sent,
                "last_sent_at": time.time(),
                "last_milestone": milestone,
                "delivery_status": "sent" if isinstance(result, dict) and result.get("status") == "success" else "failed",
            })
            
            fs.collection("candidate_brag_prompts").document(candidate_uid).set(prompt_data)

            print(f"✅ [BRAG] Sent brag prompt to candidate {candidate_uid} (milestone: {milestone})")
            return True

        except Exception as e:
            print(f"❌ [BRAG] Error sending brag prompt to {candidate_uid}: {e}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance
candidate_brag_service = CandidateBragService()

