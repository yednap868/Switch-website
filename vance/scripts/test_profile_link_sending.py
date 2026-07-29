#!/usr/bin/env python3
"""
Test script to verify profile link sending with resume phone numbers and template messages.

This script simulates the post-call workflow to check:
1. Phone number extraction from resume
2. Profile creation
3. Template message sending
"""

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile, get_extraction_data
from utils.whatsapp.components import MsgComponents
from utils.whatsapp.whatsapp import WhatsAppSender


def test_resume_phone_extraction(uid: str):
    """Test if phone number is extracted from resume."""
    print(f"\n{'='*70}")
    print(f"📱 Testing Resume Phone Extraction for {uid}")
    print(f"{'='*70}")
    
    # Get user profile
    profile_doc = fs.collection("user_profiles").document(uid).get()
    if not profile_doc.exists:
        print(f"❌ No profile found for {uid}")
        return False
    
    profile_data = profile_doc.to_dict() or {}
    extraction_data = profile_data.get("extraction_data", {})
    resume_numbers = extraction_data.get("resume_extracted_numbers", {})
    
    print(f"\n📄 Profile Data:")
    print(f"   Name: {profile_data.get('name', 'Not found')}")
    print(f"   Slug: {profile_data.get('slug', 'Not found')}")
    
    print(f"\n📞 Phone Number Sources:")
    
    # Check resume phone
    resume_phone = resume_numbers.get("phone_number") if isinstance(resume_numbers, dict) else None
    if resume_phone:
        print(f"   ✅ Resume phone found: {resume_phone}")
        # Format check
        import re
        clean_phone = re.sub(r'[^\d]', '', str(resume_phone))
        if len(clean_phone) == 10:
            formatted = '91' + clean_phone
            print(f"   📝 Would format to: {formatted}")
        else:
            print(f"   📝 Already formatted: {clean_phone}")
    else:
        print(f"   ⚠️  No resume phone found")
        print(f"   📋 Resume numbers data: {resume_numbers}")
    
    # Check profile phone
    profile_phone = (
        profile_data.get("whatsapp")
        or profile_data.get("phone")
        or profile_data.get("phone_number")
    )
    if profile_phone:
        print(f"   ✅ Profile phone found: {profile_phone}")
    else:
        print(f"   ⚠️  No profile phone found")
    
    # Check extraction data phone
    extraction_phone = extraction_data.get("phone_number")
    if extraction_phone:
        print(f"   ✅ Extraction data phone found: {extraction_phone}")
    else:
        print(f"   ⚠️  No extraction data phone found")
    
    return True


def test_profile_creation(uid: str):
    """Test if profile is created correctly."""
    print(f"\n{'='*70}")
    print(f"👤 Testing Profile Creation for {uid}")
    print(f"{'='*70}")
    
    profile_doc = fs.collection("user_profiles").document(uid).get()
    if not profile_doc.exists:
        print(f"❌ No profile found for {uid}")
        return False
    
    profile_data = profile_doc.to_dict() or {}
    
    # Check required fields
    required_fields = {
        "name": profile_data.get("name"),
        "slug": profile_data.get("slug"),
        "extraction_data": profile_data.get("extraction_data"),
    }
    
    print(f"\n✅ Profile Fields:")
    all_present = True
    for field, value in required_fields.items():
        if value:
            print(f"   ✅ {field}: {str(value)[:50]}...")
        else:
            print(f"   ❌ {field}: MISSING")
            all_present = False
    
    # Check profile URL
    slug = profile_data.get("slug")
    if slug:
        profile_url = f"https://profiles.vance.so/{slug}"
        print(f"\n🔗 Profile URL: {profile_url}")
    else:
        print(f"\n❌ No slug found - profile URL cannot be generated")
        all_present = False
    
    return all_present


def test_template_message(uid: str, dry_run: bool = True):
    """Test template message sending (dry run by default)."""
    print(f"\n{'='*70}")
    print(f"📨 Testing Template Message for {uid}")
    print(f"{'='*70}")
    
    profile_doc = fs.collection("user_profiles").document(uid).get()
    if not profile_doc.exists:
        print(f"❌ No profile found for {uid}")
        return False
    
    profile_data = profile_doc.to_dict() or {}
    extraction_data = profile_data.get("extraction_data", {})
    resume_numbers = extraction_data.get("resume_extracted_numbers", {})
    resume_phone = resume_numbers.get("phone_number") if isinstance(resume_numbers, dict) else None
    
    # Format phone
    import re
    if resume_phone:
        clean_phone = re.sub(r'[^\d]', '', str(resume_phone))
        if len(clean_phone) == 10:
            wa_id = '91' + clean_phone
        else:
            wa_id = clean_phone
    else:
        wa_id = (
            profile_data.get("whatsapp")
            or profile_data.get("phone")
            or profile_data.get("phone_number")
            or uid
        )
    
    if not wa_id:
        print(f"❌ No WhatsApp ID found")
        return False
    
    # Get candidate name
    candidate_name = (
        profile_data.get("name")
        or extraction_data.get("name")
        or "there"
    )
    
    # Get profile URL
    slug = profile_data.get("slug") or uid
    profile_url = f"https://profiles.vance.so/{slug}"
    
    print(f"\n📋 Template Details:")
    print(f"   Template Name: profile_ready")
    print(f"   Recipient: {wa_id}")
    print(f"   Parameter 1 (name): {candidate_name}")
    print(f"   Parameter 2 (URL): {profile_url}")
    
    # Build template payload
    template_name = "profile_ready"
    payload = MsgComponents.template_scaffold(
        to=wa_id,
        template_name=template_name,
        language_code="en",
        body_parameters=[candidate_name, profile_url],
    )
    
    print(f"\n📦 Template Payload:")
    import json
    print(json.dumps(payload, indent=2))
    
    if dry_run:
        print(f"\n⚠️  DRY RUN - Not sending actual message")
        print(f"   To send actual message, run with --send flag")
        return True
    else:
        print(f"\n📤 Sending template message...")
        sender = WhatsAppSender()
        try:
            result = sender.send(data=payload)
            print(f"✅ Result: {result}")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test profile link sending")
    parser.add_argument("uid", help="User ID to test")
    parser.add_argument("--send", action="store_true", help="Actually send the message (default: dry run)")
    
    args = parser.parse_args()
    
    uid = args.uid
    
    print(f"\n{'='*70}")
    print(f"🧪 Profile Link Sending Test")
    print(f"{'='*70}")
    print(f"User ID: {uid}")
    print(f"Mode: {'LIVE' if args.send else 'DRY RUN'}")
    
    # Run tests
    test_resume_phone_extraction(uid)
    test_profile_creation(uid)
    test_template_message(uid, dry_run=not args.send)
    
    print(f"\n{'='*70}")
    print(f"✅ Test Complete")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

