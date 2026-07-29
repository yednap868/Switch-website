#!/usr/bin/env python3
"""Debug why a user is receiving 'hit a glitch' messages."""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import fs, get_user_profile, load_conversation
from api.whatsapp_modules.conversation_history import conversation_history

def debug_user(uid: str):
    """Debug a specific user's issues."""
    print("=" * 70)
    print(f"DEBUGGING USER: {uid}")
    print("=" * 70)
    
    # Normalize UID (remove + and spaces)
    uid = uid.replace("+", "").replace(" ", "").replace("-", "").strip()
    
    # Get user profile
    user_profile = get_user_profile(uid) or {}
    print(f"\nUser Profile:")
    print(f"  Name: {user_profile.get('name', 'N/A')}")
    print(f"  Email: {user_profile.get('email', 'N/A')}")
    print(f"  WhatsApp ID: {user_profile.get('wa_id', uid)}")
    
    # Check recent conversation history
    print(f"\n📱 Checking conversation history...")
    try:
        messages = conversation_history.get_recent_messages(uid, limit=20)
        print(f"  Found {len(messages)} recent messages")
        
        # Check for tool_use or tool_result blocks
        tool_issues = []
        for i, msg in enumerate(messages):
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type in ["tool_use", "tool_result"]:
                            tool_issues.append({
                                "message_index": i,
                                "block_type": block_type,
                                "block": block,
                            })
        
        if tool_issues:
            print(f"\n⚠️ Found {len(tool_issues)} tool_use/tool_result blocks in conversation history:")
            for issue in tool_issues[:5]:  # Show first 5
                print(f"  Message {issue['message_index']}: {issue['block_type']}")
        else:
            print(f"  ✅ No tool_use/tool_result blocks found")
        
        # Show recent messages
        print(f"\n📝 Recent messages (last 5):")
        for i, msg in enumerate(messages[:5], 1):
            sender = msg.get("sender", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            
            # Format timestamp
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = float(timestamp)
                    except:
                        pass
                if isinstance(timestamp, (int, float)):
                    time_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    time_str = str(timestamp)
            else:
                time_str = "N/A"
            
            # Format content
            if isinstance(content, list):
                content_str = f"[{len(content)} blocks]"
            else:
                content_str = str(content)[:100]
            
            print(f"  {i}. [{sender}] {time_str}")
            print(f"     {content_str}")
        
    except Exception as e:
        print(f"  ❌ Error loading conversation history: {e}")
        import traceback
        traceback.print_exc()
    
    # Check load_conversation (what the agent uses)
    print(f"\n🤖 Checking load_conversation (agent's view)...")
    try:
        agent_messages = load_conversation(uid, limit=20)
        print(f"  Agent sees {len(agent_messages)} messages")
        
        # Check for tool_use or tool_result blocks
        agent_tool_issues = []
        for i, msg in enumerate(agent_messages):
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type in ["tool_use", "tool_result"]:
                            agent_tool_issues.append({
                                "message_index": i,
                                "block_type": block_type,
                            })
        
        if agent_tool_issues:
            print(f"  ⚠️ Agent sees {len(agent_tool_issues)} tool_use/tool_result blocks")
            print(f"  ❌ This is likely causing the 'hit a glitch' error!")
        else:
            print(f"  ✅ Agent conversation history looks clean")
            
    except Exception as e:
        print(f"  ❌ Error loading agent conversation: {e}")
        import traceback
        traceback.print_exc()
    
    # Check for recent errors in logs (if we can access them)
    print(f"\n🔍 Summary:")
    print(f"  User ID: {uid}")
    print(f"  WhatsApp ID: {user_profile.get('wa_id', uid)}")
    if tool_issues or (agent_tool_issues if 'agent_tool_issues' in locals() else []):
        print(f"  ⚠️ ISSUE FOUND: tool_use/tool_result blocks in conversation history")
        print(f"  💡 SOLUTION: The load_conversation function should filter these out")
        print(f"     Check utils/db.py load_conversation function")
    else:
        print(f"  ✅ No obvious issues found in conversation history")
        print(f"  💡 The error might be from a different cause (API error, etc.)")
    
    print("=" * 70)

if __name__ == "__main__":
    # User provided: +91 95580 22176
    uid = "+91 95580 22176"
    debug_user(uid)

