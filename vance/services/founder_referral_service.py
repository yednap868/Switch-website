"""
Founder referral service for triggering referral prompts after successful matches/intros.

Triggers:
1. Founder receives at least 1 relevant intro (profiles sent)
2. Founder marks candidate as "interviewing"
3. Founder marks hire as successful
"""

import hashlib
import time
from typing import Optional

from utils.db import fs, get_user_profile
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


class FounderReferralService:
    """Service for managing founder referral workflow."""

    def __init__(self):
        self.sender = WhatsAppSender()

    def generate_referral_code(self, founder_uid: str) -> str:
        """
        Generate a unique referral code for a founder.
        Uses a hash of founder_uid + timestamp for uniqueness.
        """
        # Create a stable but unique code
        base_string = f"{founder_uid}_{int(time.time() / 86400)}"  # Changes daily
        code = hashlib.md5(base_string.encode()).hexdigest()[:8].upper()
        return code

    def get_or_create_referral_link(self, founder_uid: str) -> str:
        """
        Get existing referral link or create a new one for a founder.
        Returns the full referral URL with founder's name instead of code.
        """
        from urllib.parse import quote
        
        # Get founder's name
        user_profile = get_user_profile(founder_uid) or {}
        founder_name = user_profile.get("name") or user_profile.get("profile", {}).get("name") or "someone"
        
        # URL encode the name
        encoded_name = quote(founder_name)
        
        # Check if referral already exists
        referral_doc = fs.collection("founder_referrals").document(founder_uid).get()
        
        if referral_doc.exists:
            referral_data = referral_doc.to_dict() or {}
            # Check if stored name matches current name
            stored_name = referral_data.get("founder_name")
            if stored_name == founder_name:
                referral_url = referral_data.get("referral_url")
                if referral_url:
                    return referral_url
            # Reconstruct with current name
            code = referral_data.get("referral_code") or self.generate_referral_code(founder_uid)
            referral_url = f"https://wa.me/12183180007?text=Hi%20Vance%2C%20{encoded_name}%20sent%20me"
            
            # Update with new name and URL
            referral_doc.reference.update({
                "founder_name": founder_name,
                "referral_url": referral_url,
                "updated_at": time.time(),
            })
            return referral_url
        
        # Create new referral
        code = self.generate_referral_code(founder_uid)
        referral_url = f"https://wa.me/12183180007?text=Hi%20Vance%2C%20{encoded_name}%20sent%20me"
        
        # Store referral
        fs.collection("founder_referrals").document(founder_uid).set(
            {
                "founder_uid": founder_uid,
                "founder_name": founder_name,
                "referral_code": code,  # Keep code for tracking
                "referral_url": referral_url,
                "created_at": time.time(),
                "referral_count": 0,
                "updated_at": time.time(),
            }
        )
        
        return referral_url

    def should_send_referral_prompt(self, founder_uid: str) -> bool:
        """
        Check if referral prompt should be sent (idempotency check).
        Only send once per founder, even if multiple triggers occur.
        """
        prompt_doc = fs.collection("founder_referral_prompts").document(founder_uid).get()
        
        if prompt_doc.exists:
            prompt_data = prompt_doc.to_dict() or {}
            # Check if already sent in last 7 days (to allow re-prompting after a week)
            sent_at = prompt_data.get("sent_at", 0)
            days_since_sent = (time.time() - sent_at) / 86400
            
            if days_since_sent < 7:
                print(f"ℹ️ [REFERRAL] Referral prompt already sent to {founder_uid} {days_since_sent:.1f} days ago")
                return False
        
        return True

    async def send_referral_prompt(self, founder_uid: str, trigger_reason: str) -> bool:
        """
        Send referral prompt to founder via WhatsApp.
        
        Args:
            founder_uid: Founder's user ID
            trigger_reason: Why the prompt was triggered ("profiles_sent", "interviewing", "hired")
        """
        try:
            # Check if should send
            if not self.should_send_referral_prompt(founder_uid):
                return False

            # Get or create referral link
            referral_url = self.get_or_create_referral_link(founder_uid)
            
            # Get founder's WhatsApp ID
            user_profile = get_user_profile(founder_uid) or {}
            wa_id = (
                user_profile.get("wa_id")
                or user_profile.get("phone")
                or user_profile.get("whatsapp")
                or founder_uid
            )

            # Send referral message
            message = (
                "🎉 Did Vance help?\n\n"
                "Invite another founder hiring tech talent.\n"
                "They get faster matching. You get priority intros.\n\n"
                f"{referral_url}"
            )

            result = self.sender.send(data=MsgComponents.text_scaffold(to=wa_id, text=message))

            # Track that prompt was sent
            fs.collection("founder_referral_prompts").document(founder_uid).set(
                {
                    "founder_uid": founder_uid,
                    "sent_at": time.time(),
                    "trigger_reason": trigger_reason,
                    "referral_url": referral_url,
                    "wa_id": wa_id,
                    "delivery_status": "sent" if isinstance(result, dict) and result.get("status") == "success" else "failed",
                }
            )

            print(f"✅ [REFERRAL] Sent referral prompt to founder {founder_uid} (trigger: {trigger_reason})")
            return True

        except Exception as e:
            print(f"❌ [REFERRAL] Error sending referral prompt to {founder_uid}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def track_referral(self, referred_uid: str, referral_code: Optional[str] = None, referrer_name: Optional[str] = None) -> Optional[str]:
        """
        Track when a new user signs up via a referral link.
        
        Args:
            referred_uid: The new user's UID
            referral_code: The referral code from the link (if provided, for backward compatibility)
            referrer_name: The referrer's name from the link (e.g., "John Doe sent me")
        
        Returns:
            The founder_uid who made the referral, or None if not found
        """
        try:
            founder_uid = None
            
            # First, try to find by name (new format)
            if referrer_name:
                # Search for founder by name
                referrals_ref = fs.collection("founder_referrals")
                query = referrals_ref.where("founder_name", "==", referrer_name).limit(1)
                docs = list(query.stream())
                
                if docs:
                    referral_doc = docs[0]
                    founder_uid = referral_doc.id
                    referral_code = referral_doc.to_dict().get("referral_code")
            
            # Fallback: try by referral code (old format)
            if not founder_uid and referral_code:
                referrals_ref = fs.collection("founder_referrals")
                query = referrals_ref.where("referral_code", "==", referral_code).limit(1)
                docs = list(query.stream())
                
                if docs:
                    referral_doc = docs[0]
                    founder_uid = referral_doc.id
            
            if founder_uid:
                # Update referral count
                referral_doc = fs.collection("founder_referrals").document(founder_uid).get()
                if referral_doc.exists:
                    referral_data = referral_doc.to_dict() or {}
                    current_count = referral_data.get("referral_count", 0)
                    referral_doc.reference.update({
                        "referral_count": current_count + 1,
                        "updated_at": time.time(),
                    })
                    
                    # Store referral relationship
                    fs.collection("referral_relationships").document(referred_uid).set({
                        "referred_uid": referred_uid,
                        "referrer_uid": founder_uid,
                        "referrer_name": referrer_name or referral_data.get("founder_name"),
                        "referral_code": referral_code,
                        "created_at": time.time(),
                    })
                    
                    print(f"✅ [REFERRAL] Tracked referral: {referred_uid} referred by {founder_uid} ({referrer_name or 'code: ' + str(referral_code)})")
                    return founder_uid
            
            return None

        except Exception as e:
            print(f"❌ [REFERRAL] Error tracking referral: {e}")
            import traceback
            traceback.print_exc()
            return None


# Singleton instance
founder_referral_service = FounderReferralService()

