#!/usr/bin/env python3
"""
Check today's introductions and candidate notifications.
"""

import sys
import os
from datetime import datetime, timezone
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile, get_extraction_data
from api.whatsapp_modules.conversation_history import conversation_history


def get_today_timestamp():
    """Get start of today in UTC as timestamp."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start.timestamp()


def check_todays_intros():
    """Check all intro_requests created today."""
    print("=" * 70)
    print("CHECKING TODAY'S INTRODUCTIONS")
    print("=" * 70)
    
    today_start = get_today_timestamp()
    print(f"\nToday's start timestamp: {today_start} ({datetime.fromtimestamp(today_start, tz=timezone.utc)})")
    
    # Get all intro_requests
    intro_requests_ref = fs.collection("intro_requests")
    all_intros = intro_requests_ref.stream()
    
    todays_intros = []
    for doc in all_intros:
        data = doc.to_dict() or {}
        requested_at = data.get("requested_at")
        
        # Handle both timestamp (float) and string timestamps
        if isinstance(requested_at, str):
            try:
                requested_at = float(requested_at)
            except:
                continue
        
        if requested_at and requested_at >= today_start:
            todays_intros.append({
                "doc_id": doc.id,
                "data": data,
                "requested_at": requested_at,
            })
    
    print(f"\n📊 Total intro requests today: {len(todays_intros)}")
    
    if todays_intros:
        print("\n" + "=" * 70)
        print("TODAY'S INTRO REQUESTS")
        print("=" * 70)
        
        for i, intro in enumerate(todays_intros, 1):
            data = intro["data"]
            requested_at = intro["requested_at"]
            requested_time = datetime.fromtimestamp(requested_at, tz=timezone.utc)
            
            requester_uid = data.get("requester_uid") or data.get("job_provider_uid", "N/A")
            requester_name = data.get("requester_name") or data.get("job_provider_name", "N/A")
            candidate_uid = data.get("candidate_uid", "N/A")
            candidate_name = data.get("candidate_name", "N/A")
            status = data.get("status", "N/A")
            source = data.get("source", "N/A")
            
            print(f"\n{i}. Intro Request")
            print(f"   Time: {requested_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Requester: {requester_name} (UID: {requester_uid})")
            print(f"   Candidate: {candidate_name} (UID: {candidate_uid})")
            print(f"   Status: {status}")
            print(f"   Source: {source}")
            print("-" * 70)
    else:
        print("\n⚠️ No intro requests found for today")
    
    return todays_intros


def check_candidate_notifications():
    """Check if candidates were notified today."""
    print("\n" + "=" * 70)
    print("CHECKING CANDIDATE NOTIFICATIONS")
    print("=" * 70)
    
    today_start = get_today_timestamp()
    
    # Get all intro_requests from today
    intro_requests_ref = fs.collection("intro_requests")
    all_intros = intro_requests_ref.stream()
    
    todays_intros = []
    for doc in all_intros:
        data = doc.to_dict() or {}
        requested_at = data.get("requested_at")
        
        if isinstance(requested_at, str):
            try:
                requested_at = float(requested_at)
            except:
                continue
        
        if requested_at and requested_at >= today_start:
            candidate_uid = data.get("candidate_uid")
            if candidate_uid:
                todays_intros.append({
                    "candidate_uid": candidate_uid,
                    "candidate_name": data.get("candidate_name", "N/A"),
                    "requester_name": data.get("requester_name") or data.get("job_provider_name", "N/A"),
                    "requester_uid": data.get("requester_uid") or data.get("job_provider_uid", "N/A"),
                })
    
    print(f"\n📊 Checking notifications for {len(todays_intros)} candidates...")
    
    notified_candidates = []
    not_notified_candidates = []
    
    for intro in todays_intros:
        candidate_uid = intro["candidate_uid"]
        candidate_name = intro["candidate_name"]
        
        # Get candidate's WhatsApp ID
        candidate_profile = get_user_profile(candidate_uid) or {}
        candidate_wa_id = (
            candidate_profile.get("wa_id")
            or candidate_profile.get("phone")
            or candidate_profile.get("whatsapp")
            or candidate_uid
        )
        
        # Check conversation history for notification messages today
        try:
            messages = conversation_history.get_recent_messages(candidate_wa_id, limit=50)
            
            # Look for notification messages from today
            found_notification = False
            for msg in messages:
                msg_time = msg.get("timestamp")
                if msg_time:
                    if isinstance(msg_time, str):
                        try:
                            msg_time = float(msg_time)
                        except:
                            continue
                    
                    if msg_time >= today_start:
                        content = msg.get("content", "")
                        metadata = msg.get("metadata", {})
                        
                        # Check if it's a notification message
                        if (metadata.get("notification_type") == "profile_presented" or
                            "profile was just shown" in str(content).lower() or
                            "introduced you to" in str(content).lower()):
                            found_notification = True
                            break
            
            if found_notification:
                notified_candidates.append({
                    "candidate_uid": candidate_uid,
                    "candidate_name": candidate_name,
                    "candidate_wa_id": candidate_wa_id,
                    "requester_name": intro["requester_name"],
                })
            else:
                not_notified_candidates.append({
                    "candidate_uid": candidate_uid,
                    "candidate_name": candidate_name,
                    "candidate_wa_id": candidate_wa_id,
                    "requester_name": intro["requester_name"],
                })
        except Exception as e:
            print(f"⚠️ Error checking notifications for {candidate_name} ({candidate_uid}): {e}")
            not_notified_candidates.append({
                "candidate_uid": candidate_uid,
                "candidate_name": candidate_name,
                "candidate_wa_id": candidate_wa_id,
                "requester_name": intro["requester_name"],
                "error": str(e),
            })
    
    print(f"\n✅ Notified candidates: {len(notified_candidates)}")
    print(f"❌ Not notified candidates: {len(not_notified_candidates)}")
    
    if notified_candidates:
        print("\n" + "=" * 70)
        print("NOTIFIED CANDIDATES")
        print("=" * 70)
        for i, candidate in enumerate(notified_candidates, 1):
            print(f"{i}. {candidate['candidate_name']} (UID: {candidate['candidate_uid']})")
            print(f"   WA ID: {candidate['candidate_wa_id']}")
            print(f"   Introduced to: {candidate['requester_name']}")
            print("-" * 70)
    
    if not_notified_candidates:
        print("\n" + "=" * 70)
        print("NOT NOTIFIED CANDIDATES")
        print("=" * 70)
        for i, candidate in enumerate(not_notified_candidates, 1):
            print(f"{i}. {candidate['candidate_name']} (UID: {candidate['candidate_uid']})")
            print(f"   WA ID: {candidate['candidate_wa_id']}")
            print(f"   Should be introduced to: {candidate['requester_name']}")
            if candidate.get("error"):
                print(f"   Error: {candidate['error']}")
            print("-" * 70)
    
    return notified_candidates, not_notified_candidates


def check_specific_user(uid: str):
    """Check if a specific user received notifications and if they were actually introduced."""
    print("\n" + "=" * 70)
    print(f"CHECKING USER: {uid}")
    print("=" * 70)
    
    # Get user profile
    user_profile = get_user_profile(uid) or {}
    user_wa_id = (
        user_profile.get("wa_id")
        or user_profile.get("phone")
        or user_profile.get("whatsapp")
        or uid
    )
    
    print(f"Name: {user_profile.get('name', 'N/A')}")
    print(f"WhatsApp ID: {user_wa_id}")
    
    # Check if this user is a candidate (has intro_requests where they are the candidate)
    intro_requests_ref = fs.collection("intro_requests")
    all_intros = intro_requests_ref.stream()
    
    intros_as_candidate = []
    for doc in all_intros:
        data = doc.to_dict() or {}
        candidate_uid = data.get("candidate_uid")
        if candidate_uid == uid:
            intros_as_candidate.append({
                "doc_id": doc.id,
                "data": data,
            })
    
    print(f"\n📊 Intro requests where {uid} is the candidate: {len(intros_as_candidate)}")
    
    if intros_as_candidate:
        print("\nIntro Requests:")
        for i, intro in enumerate(intros_as_candidate, 1):
            data = intro["data"]
            requester_uid = data.get("requester_uid") or data.get("job_provider_uid", "N/A")
            requester_name = data.get("requester_name") or data.get("job_provider_name", "N/A")
            status = data.get("status", "N/A")
            requested_at = data.get("requested_at")
            
            if requested_at:
                if isinstance(requested_at, str):
                    try:
                        requested_at = float(requested_at)
                    except:
                        requested_at = None
                if requested_at:
                    requested_time = datetime.fromtimestamp(requested_at, tz=timezone.utc)
                    print(f"   {i}. Requested by: {requester_name} (UID: {requester_uid})")
                    print(f"      Status: {status}")
                    print(f"      Time: {requested_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            else:
                print(f"   {i}. Requested by: {requester_name} (UID: {requester_uid})")
                print(f"      Status: {status}")
    else:
        print(f"\n⚠️ No intro requests found where {uid} is the candidate")
    
    # Check conversation history for notifications
    print(f"\n📱 Checking conversation history for notifications...")
    try:
        messages = conversation_history.get_recent_messages(user_wa_id, limit=50)
        
        today_start = get_today_timestamp()
        notification_messages = []
        
        for msg in messages:
            msg_time = msg.get("timestamp")
            if msg_time:
                if isinstance(msg_time, str):
                    try:
                        msg_time = float(msg_time)
                    except:
                        continue
                
                if msg_time >= today_start:
                    content = msg.get("content", "")
                    metadata = msg.get("metadata", {})
                    sender = msg.get("sender", "")
                    
                    # Check if it's a notification message
                    if (sender == "agent" and
                        (metadata.get("notification_type") == "profile_presented" or
                         "profile was just shown" in str(content).lower() or
                         "introduced you to" in str(content).lower())):
                        notification_messages.append({
                            "content": content,
                            "metadata": metadata,
                            "timestamp": msg_time,
                        })
        
        if notification_messages:
            print(f"\n✅ Found {len(notification_messages)} notification message(s) today:")
            for i, notif in enumerate(notification_messages, 1):
                msg_time = datetime.fromtimestamp(notif["timestamp"], tz=timezone.utc)
                print(f"   {i}. Time: {msg_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"      Content: {notif['content'][:200]}...")
                print(f"      Metadata: {notif['metadata']}")
        else:
            print(f"\n⚠️ No notification messages found in conversation history today")
            
    except Exception as e:
        print(f"⚠️ Error checking conversation history: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if len(intros_as_candidate) > 0:
        print(f"✅ User {uid} HAS been introduced ({len(intros_as_candidate)} intro request(s))")
    else:
        print(f"❌ User {uid} has NOT been introduced (no intro requests found)")
    
    if notification_messages:
        print(f"✅ User {uid} HAS received notification(s) today")
    else:
        print(f"❌ User {uid} has NOT received notification(s) today")


def main():
    # Check today's intros
    todays_intros = check_todays_intros()
    
    # Check candidate notifications
    notified, not_notified = check_candidate_notifications()
    
    # Check specific user
    check_specific_user("918368828660")
    
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total intro requests today: {len(todays_intros)}")
    print(f"Candidates notified: {len(notified)}")
    print(f"Candidates NOT notified: {len(not_notified)}")
    print("=" * 70)


if __name__ == "__main__":
    main()

