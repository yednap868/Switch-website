#!/usr/bin/env python3
"""
Script to send compensation card and profile link to a user via WhatsApp.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db import get_user_profile, fs
from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from services.compensation_insight_service import compensation_insight_service


def send_compensation_card(uid: str):
    """Send compensation card image and profile link to user."""
    print(f"📤 Sending compensation card to UID: {uid}")
    
    # Get user profile
    user_profile = get_user_profile(uid)
    if not user_profile:
        print(f"❌ No user profile found for {uid}")
        return False
    
    # Get WhatsApp ID
    wa_id = (
        user_profile.get("wa_id")
        or user_profile.get("phone")
        or user_profile.get("whatsapp")
        or uid
    )
    
    if not wa_id:
        print(f"❌ No WhatsApp ID found for {uid}")
        return False
    
    print(f"✅ Found WhatsApp ID: {wa_id}")
    
    # Generate insights
    print("🧠 Generating compensation insights...")
    insights = compensation_insight_service.get_insights(uid)
    print(f"✅ Generated insights: {insights.compensation_band[:50]}...")
    
    # Send compensation card image
    base_url = "https://api.relayy.world"
    image_url = f"{base_url}/api/public/compensation-card/{uid}"
    
    print(f"📸 Sending compensation card image from: {image_url}")
    payload = {
        "messaging_product": "whatsapp",
        "to": wa_id,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": "Here's how founders would price your profile today — and how to level it up.",
        },
    }
    
    sender = WhatsAppSender()
    result = sender.send(data=payload)
    
    if isinstance(result, dict) and result.get("status") == "success":
        print(f"✅ Compensation card sent successfully! Message ID: {result.get('message_id', 'N/A')}")
    else:
        print(f"⚠️ Compensation card send result: {result}")
    
    # Send profile link
    print("🔗 Fetching profile link...")
    profile_doc = fs.collection("user_profiles").document(uid).get()
    if profile_doc.exists:
        profile_data = profile_doc.to_dict() or {}
        slug = (
            profile_data.get("slug")
            or profile_data.get("public_slug")
            or profile_data.get("username")
            or uid
        )
        profile_url = f"https://profiles.vance.so/{slug}"
        
        print(f"📤 Sending profile link: {profile_url}")
        profile_text = (
            f"Here's your profile: {profile_url}\n\n"
            "This is what I'll share with founders when I introduce you."
        )
        
        result2 = sender.send(data=MsgComponents.text_scaffold(to=wa_id, text=profile_text))
        
        if isinstance(result2, dict) and result2.get("status") == "success":
            print(f"✅ Profile link sent successfully! Message ID: {result2.get('message_id', 'N/A')}")
        else:
            print(f"⚠️ Profile link send result: {result2}")
    else:
        print(f"⚠️ No profile found for {uid}, skipping profile link")
    
    print("✅ Done!")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_compensation_card.py <uid>")
        sys.exit(1)
    
    uid = sys.argv[1]
    send_compensation_card(uid)


