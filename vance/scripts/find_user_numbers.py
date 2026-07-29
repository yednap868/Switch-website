#!/usr/bin/env python3
"""Find WhatsApp numbers for users by name."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import fs, get_user_profile

def find_users_by_name(names):
    """Find users by name (case-insensitive partial match)."""
    print("=" * 70)
    print("FINDING USER NUMBERS")
    print("=" * 70)
    
    # Get all user profiles
    user_profiles_ref = fs.collection("user_profiles")
    all_users = user_profiles_ref.stream()
    
    found_users = []
    for doc in all_users:
        user_data = doc.to_dict() or {}
        uid = doc.id
        name = user_data.get("name", "").lower()
        
        # Check if name matches any of the search names
        for search_name in names:
            if search_name.lower() in name or name in search_name.lower():
                found_users.append({
                    "uid": uid,
                    "name": user_data.get("name", "N/A"),
                    "wa_id": user_data.get("wa_id") or user_data.get("phone") or user_data.get("whatsapp") or uid,
                    "email": user_data.get("email", "N/A"),
                    "linkedin": user_data.get("linkedin_url") or user_data.get("linkedin", "N/A"),
                })
                break
    
    print(f"\nSearching for: {', '.join(names)}")
    print(f"Found {len(found_users)} matching user(s)\n")
    
    for i, user in enumerate(found_users, 1):
        print(f"{i}. {user['name']}")
        print(f"   UID: {user['uid']}")
        print(f"   WhatsApp Number: {user['wa_id']}")
        print(f"   Email: {user['email']}")
        print(f"   LinkedIn: {user['linkedin']}")
        print("-" * 70)
    
    return found_users

if __name__ == "__main__":
    # Search for Jay and Merlyn
    names_to_find = ["Jay", "Merlyn"]
    find_users_by_name(names_to_find)

