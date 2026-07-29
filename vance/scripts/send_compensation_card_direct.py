#!/usr/bin/env python3
"""
Script to send compensation card directly by uploading image to WhatsApp Media API.
This avoids the need for a publicly accessible URL.
"""

import sys
import os
import io
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db import get_user_profile, fs
from utils.whatsapp.whatsapp import WhatsAppSender
from utils.whatsapp.components import MsgComponents
from services.compensation_insight_service import compensation_insight_service
import requests


def upload_media_to_whatsapp(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Upload image to WhatsApp Media API and return media_id."""
    phone_number_id = os.getenv("PHONE_NUMBER_ID")
    access_token = os.getenv("META_SYS_USER_TOKEN")
    
    if not phone_number_id or not access_token:
        raise ValueError("PHONE_NUMBER_ID or META_SYS_USER_TOKEN not set")
    
    # WhatsApp Media API endpoint
    upload_url = f"https://graph.facebook.com/v16.0/{phone_number_id}/media"
    
    # Prepare the file for upload
    files = {
        'file': ('compensation_card.png', io.BytesIO(image_bytes), mime_type)
    }
    
    data = {
        'messaging_product': 'whatsapp',
        'type': 'image'
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    print(f"📤 Uploading image to WhatsApp Media API ({len(image_bytes)} bytes)...")
    response = requests.post(upload_url, headers=headers, files=files, data=data, timeout=60)
    
    if response.status_code == 200:
        media_id = response.json().get('id')
        print(f"✅ Image uploaded successfully, media_id: {media_id}")
        return media_id
    else:
        error_msg = response.text
        print(f"❌ Failed to upload image: {response.status_code} - {error_msg}")
        raise Exception(f"WhatsApp Media API error: {error_msg}")


def send_compensation_card_direct(uid: str):
    """Send compensation card by uploading image directly to WhatsApp."""
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
    
    # Generate insights and render card
    print("🧠 Generating compensation insights...")
    insights = compensation_insight_service.get_insights(uid)
    print(f"✅ Generated insights: {insights.compensation_band[:50]}...")
    
    print("🎨 Rendering compensation card...")
    image_bytes = compensation_insight_service.render_card_png(uid, insights)
    print(f"✅ Card rendered: {len(image_bytes)} bytes")
    
    # Upload image to WhatsApp Media API
    try:
        media_id = upload_media_to_whatsapp(image_bytes)
    except Exception as e:
        print(f"❌ Failed to upload image: {e}")
        return False
    
    # Send image using media_id
    print(f"📤 Sending image message with media_id: {media_id}")
    payload = {
        "messaging_product": "whatsapp",
        "to": wa_id,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": "Here's how founders would price your profile today — and how to level it up.",
        },
    }
    
    sender = WhatsAppSender()
    result = sender.send(data=payload)
    
    if isinstance(result, dict) and result.get("status") == "success":
        print(f"✅ Compensation card sent successfully! Message ID: {result.get('message_id', 'N/A')}")
    else:
        print(f"⚠️ Compensation card send result: {result}")
        return False
    
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
        print("Usage: python send_compensation_card_direct.py <uid>")
        sys.exit(1)
    
    uid = sys.argv[1]
    send_compensation_card_direct(uid)


