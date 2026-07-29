#!/usr/bin/env python3
"""
Find LinkedIn URLs from WhatsApp conversations, call transcripts, and other sources.
"""

import sys
import os
import re
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_extraction_data, get_user_profile


def extract_linkedin_url(text: str) -> str:
    """Extract LinkedIn URL from text using regex."""
    if not text:
        return ""
    
    # Pattern to match LinkedIn URLs
    patterns = [
        r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?',
        r'linkedin\.com/in/[\w\-]+/?',
        r'www\.linkedin\.com/in/[\w\-]+/?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            url = matches[0]
            # Ensure it starts with https://
            if not url.startswith('http'):
                url = 'https://' + url
            # Remove trailing slash
            url = url.rstrip('/')
            return url
    
    return ""


def search_conversation_messages(uid: str) -> str:
    """Search through WhatsApp conversation messages for LinkedIn URL."""
    try:
        messages_ref = fs.collection("conversations").document(uid).collection("messages")
        
        # Try timestamp field first
        try:
            messages = messages_ref.order_by("timestamp", direction="DESCENDING").limit(200).stream()
        except:
            # Fallback to ts field
            try:
                messages = messages_ref.order_by("ts", direction="DESCENDING").limit(200).stream()
            except:
                # Just get all messages
                messages = messages_ref.limit(200).stream()
        
        for msg_doc in messages:
            msg_data = msg_doc.to_dict() or {}
            
            # Check content field (can be string or list)
            content = msg_data.get("content", "")
            if isinstance(content, list):
                # Handle structured content (pydantic-ai format)
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text", "") or item.get("content", "") or str(item)
                        linkedin = extract_linkedin_url(text)
                        if linkedin:
                            return linkedin
                    else:
                        text = str(item)
                        linkedin = extract_linkedin_url(text)
                        if linkedin:
                            return linkedin
            else:
                # Handle plain text
                linkedin = extract_linkedin_url(str(content))
                if linkedin:
                    return linkedin
            
            # Also check if content is directly in the message
            text_content = msg_data.get("text", "") or str(msg_data)
            linkedin = extract_linkedin_url(text_content)
            if linkedin:
                return linkedin
        
        return ""
    except Exception as e:
        print(f"  ⚠️  Error searching messages: {e}")
        return ""


def search_call_transcripts(uid: str) -> str:
    """Search through call transcripts for LinkedIn URL."""
    try:
        # Check user_calls collection
        calls_ref = fs.collection("user_calls").document(uid).collection("calls")
        calls = calls_ref.order_by("timestamp", direction="DESCENDING").limit(10).stream()
        
        for call_doc in calls:
            call_data = call_doc.to_dict() or {}
            transcript = call_data.get("transcript", "") or call_data.get("conversation_transcript", "")
            if transcript:
                linkedin = extract_linkedin_url(transcript)
                if linkedin:
                    return linkedin
            
            # Check user_messages in call data
            user_messages = call_data.get("user_messages", [])
            for msg in user_messages:
                if isinstance(msg, dict):
                    text = msg.get("text", "") or msg.get("content", "") or str(msg)
                else:
                    text = str(msg)
                linkedin = extract_linkedin_url(text)
                if linkedin:
                    return linkedin
        
        return ""
    except Exception as e:
        print(f"  ⚠️  Error searching transcripts: {e}")
        return ""


def search_call_memory(uid: str) -> str:
    """Search through call memory for LinkedIn URL."""
    try:
        # Check user_call_summaries
        summary_doc = fs.collection("user_call_summaries").document(uid).get()
        if summary_doc.exists:
            summary_data = summary_doc.to_dict() or {}
            # Check any text fields
            for key, value in summary_data.items():
                if isinstance(value, str):
                    linkedin = extract_linkedin_url(value)
                    if linkedin:
                        return linkedin
        
        return ""
    except Exception as e:
        print(f"  ⚠️  Error searching call memory: {e}")
        return ""


def search_all_sources(uid: str) -> str:
    """Search all possible sources for LinkedIn URL."""
    linkedin = ""
    
    # 1. Check user profile
    user_profile = get_user_profile(uid) or {}
    linkedin = user_profile.get("linkedin_url", "")
    if linkedin:
        return linkedin
    
    # 2. Check extraction data
    extraction = get_extraction_data(uid) or {}
    linkedin = extraction.get("linkedin_url", "")
    if linkedin:
        return linkedin
    
    # 3. Check user_profiles collection
    profile_doc = fs.collection("user_profiles").document(uid).get()
    if profile_doc.exists:
        profile_data = profile_doc.to_dict() or {}
        linkedin = profile_data.get("linkedin_url", "")
        if linkedin:
            return linkedin
        
        # Check nested profile dict
        nested_profile = profile_data.get("profile", {})
        if isinstance(nested_profile, dict):
            linkedin = nested_profile.get("linkedin_url", "")
            if linkedin:
                return linkedin
        
        # Check arbitrary field
        arbitrary = profile_data.get("arbitrary", {})
        if isinstance(arbitrary, dict):
            linkedin = arbitrary.get("linkedin_url", "")
            if linkedin:
                return linkedin
        
        # Check extraction_data within profile
        extraction_in_profile = profile_data.get("extraction_data", {})
        if isinstance(extraction_in_profile, dict):
            linkedin = extraction_in_profile.get("linkedin_url", "")
            if linkedin:
                return linkedin
    
    # 4. Search conversation messages
    print(f"  🔍 Searching conversation messages...")
    linkedin = search_conversation_messages(uid)
    if linkedin:
        return linkedin
    
    # 5. Search call transcripts
    print(f"  🔍 Searching call transcripts...")
    linkedin = search_call_transcripts(uid)
    if linkedin:
        return linkedin
    
    # 6. Search call memory
    print(f"  🔍 Searching call memory...")
    linkedin = search_call_memory(uid)
    if linkedin:
        return linkedin
    
    return ""


def get_all_job_seekers():
    """Get all job seekers from extractions collection."""
    extractions_ref = fs.collection("extractions")
    all_extractions = extractions_ref.stream()
    
    job_seekers = []
    for ext_doc in all_extractions:
        ext_data = ext_doc.to_dict() or {}
        uid = ext_doc.id
        
        # Check if it's a job seeker (has target_role or core_skills)
        if ext_data.get("target_role") or ext_data.get("core_skills"):
            user_profile = get_user_profile(uid) or {}
            name = user_profile.get("name") or ext_data.get("name") or uid
            
            job_seekers.append({
                "uid": uid,
                "name": name,
            })
    
    return job_seekers


def main():
    print("=" * 70)
    print("FINDING LINKEDIN URLs FROM CONVERSATIONS")
    print("=" * 70)
    
    job_seekers = get_all_job_seekers()
    print(f"\nFound {len(job_seekers)} job seekers\n")
    
    found_count = 0
    missing_count = 0
    results = []
    
    for i, js in enumerate(job_seekers, 1):
        print(f"[{i}/{len(job_seekers)}] {js['name']} ({js['uid']})")
        
        linkedin = search_all_sources(js['uid'])
        
        if linkedin:
            print(f"  ✅ Found: {linkedin}")
            found_count += 1
        else:
            print(f"  ❌ Not found")
            missing_count += 1
        
        results.append({
            "uid": js['uid'],
            "name": js['name'],
            "linkedin_url": linkedin,
        })
        print()
    
    print("=" * 70)
    print(f"SUMMARY:")
    print(f"  Found: {found_count}")
    print(f"  Missing: {missing_count}")
    print("=" * 70)
    
    # Update profiles with found LinkedIn URLs
    if found_count > 0:
        print(f"\n📝 Updating profiles with found LinkedIn URLs...")
        updated = 0
        for result in results:
            if result["linkedin_url"]:
                try:
                    # Update user_profiles
                    fs.collection("user_profiles").document(result["uid"]).set(
                        {"linkedin_url": result["linkedin_url"], "updated_at": time.time()},
                        merge=True
                    )
                    # Update users collection
                    fs.collection("users").document(result["uid"]).set(
                        {"linkedin_url": result["linkedin_url"]},
                        merge=True
                    )
                    updated += 1
                    print(f"  ✅ Updated {result['name']}")
                except Exception as e:
                    print(f"  ❌ Error updating {result['name']}: {e}")
        
        print(f"\n✅ Updated {updated} profiles with LinkedIn URLs")


if __name__ == "__main__":
    main()

