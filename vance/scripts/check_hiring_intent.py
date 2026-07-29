#!/usr/bin/env python3
"""
Check unclassified users' conversations for hiring intent.
"""

import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs, get_user_profile, get_extraction_data


def search_conversation_for_hiring_keywords(uid: str) -> dict:
    """Search conversation messages for hiring-related keywords."""
    hiring_keywords = [
        'hire', 'hiring', 'recruit', 'recruiting', 'looking for',
        'need', 'open position', 'open role', 'job opening',
        'candidate', 'engineer', 'developer', 'full stack',
        'backend', 'frontend', 'product manager', 'designer',
        'salary', 'budget', 'experience level', 'work model',
        'remote', 'hybrid', 'on-site', 'office location'
    ]
    
    results = {
        'hiring_signals': [],
        'message_count': 0,
        'has_hiring_intent': False
    }
    
    try:
        # Check conversation messages
        messages_ref = fs.collection("conversations").document(uid).collection("messages")
        
        try:
            messages = messages_ref.order_by("timestamp", direction="DESCENDING").limit(100).stream()
        except:
            try:
                messages = messages_ref.order_by("ts", direction="DESCENDING").limit(100).stream()
            except:
                messages = messages_ref.limit(100).stream()
        
        for msg_doc in messages:
            msg_data = msg_doc.to_dict() or {}
            results['message_count'] += 1
            
            # Get message content
            content = msg_data.get("content", "")
            if isinstance(content, list):
                # Handle structured content
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text", "") or item.get("content", "") or str(item)
                    else:
                        text = str(item)
                    
                    # Check for hiring keywords
                    text_lower = text.lower()
                    for keyword in hiring_keywords:
                        if keyword in text_lower:
                            # Extract context (50 chars before and after)
                            idx = text_lower.find(keyword)
                            start = max(0, idx - 50)
                            end = min(len(text), idx + len(keyword) + 50)
                            context = text[start:end]
                            
                            if keyword not in [s['keyword'] for s in results['hiring_signals']]:
                                results['hiring_signals'].append({
                                    'keyword': keyword,
                                    'context': context,
                                    'full_text': text[:200]  # First 200 chars
                                })
            else:
                # Handle plain text
                text = str(content)
                text_lower = text.lower()
                for keyword in hiring_keywords:
                    if keyword in text_lower:
                        idx = text_lower.find(keyword)
                        start = max(0, idx - 50)
                        end = min(len(text), idx + len(keyword) + 50)
                        context = text[start:end]
                        
                        if keyword not in [s['keyword'] for s in results['hiring_signals']]:
                            results['hiring_signals'].append({
                                'keyword': keyword,
                                'context': context,
                                'full_text': text[:200]
                            })
        
        # Check extraction data for hiring signals
        extraction = get_extraction_data(uid) or {}
        extraction_text = ' '.join([str(v) for k, v in extraction.items() if v]).lower()
        
        for keyword in hiring_keywords:
            if keyword in extraction_text:
                # Check if we already have this keyword
                if keyword not in [s['keyword'] for s in results['hiring_signals']]:
                    # Find where it appears in extraction
                    for k, v in extraction.items():
                        if v and keyword in str(v).lower():
                            results['hiring_signals'].append({
                                'keyword': keyword,
                                'context': f'In field "{k}": {str(v)[:100]}',
                                'full_text': str(v)[:200]
                            })
                            break
        
        # Filter out false positives (generic agent phrases)
        false_positive_phrases = [
            'i need to hear your story',
            'looking forward to helping',
            'what are you looking for',
            'what do you need',
            'i need to see',
            'need to hear',
            'looking for a job',  # This is job seeker, not provider
            'looking for opportunities',  # Job seeker
        ]
        
        # Filter signals
        filtered_signals = []
        for signal in results['hiring_signals']:
            context_lower = signal['context'].lower()
            full_text_lower = signal['full_text'].lower()
            
            # Skip if it's a false positive
            is_false_positive = any(fp in context_lower or fp in full_text_lower for fp in false_positive_phrases)
            
            # Also skip if it's clearly about the user being a job seeker
            if 'looking for a job' in full_text_lower or 'looking for opportunities' in full_text_lower:
                is_false_positive = True
            
            if not is_false_positive:
                filtered_signals.append(signal)
        
        results['hiring_signals'] = filtered_signals
        
        # Determine if there's hiring intent (more strict criteria)
        strong_hiring_keywords = ['hire', 'hiring', 'recruit', 'recruiting', 'candidate', 'open position', 'open role', 'job opening']
        weak_hiring_keywords = ['looking for', 'need']
        
        # Check for strong hiring keywords
        has_strong_signal = any(s['keyword'] in strong_hiring_keywords for s in filtered_signals)
        
        # Check for weak keywords but with hiring context
        has_weak_signal = False
        for signal in filtered_signals:
            if signal['keyword'] in weak_hiring_keywords:
                context = signal['context'].lower()
                # Check if context suggests hiring (not job seeking)
                hiring_context = any(word in context for word in ['engineer', 'developer', 'hire', 'team', 'role', 'position', 'candidate', 'recruit'])
                job_seeker_context = any(word in context for word in ['job', 'opportunity', 'work', 'employment'])
                if hiring_context and not job_seeker_context:
                    has_weak_signal = True
                    break
        
        # Also check extraction data for job provider fields
        has_job_provider_fields = any(
            extraction.get(field) for field in [
                'job_title', 'required_skills', 'experience_level', 
                'hiring_urgency', 'number_of_openings'
            ]
        )
        
        results['has_hiring_intent'] = has_strong_signal or (has_weak_signal and has_job_provider_fields) or has_job_provider_fields
            
    except Exception as e:
        print(f"  ⚠️  Error searching conversations: {e}")
    
    return results


def get_unclassified_users():
    """Get all unclassified users (not job seekers or job providers)."""
    extractions_ref = fs.collection("extractions")
    all_extractions = extractions_ref.stream()
    
    job_providers = []
    job_seekers = []
    unclassified = []
    
    JOB_PROVIDER_FIELDS = [
        'job_title', 'role_description', 'required_skills', 'experience_level',
        'work_model', 'office_location', 'salary_budget', 'hiring_urgency',
        'ideal_candidate', 'company_stage', 'number_of_openings'
    ]
    
    # Filter out test users
    test_user_prefixes = ['test_', 'default', 'Aryan']  # Aryan seems to be a test user
    
    for ext_doc in all_extractions:
        ext_data = ext_doc.to_dict() or {}
        uid = ext_doc.id
        
        # Skip test users
        if any(uid.startswith(prefix) for prefix in test_user_prefixes):
            continue
        
        if ext_data.get('target_role') or ext_data.get('core_skills'):
            job_seekers.append(uid)
        elif any(ext_data.get(field) for field in JOB_PROVIDER_FIELDS):
            job_providers.append(uid)
        else:
            unclassified.append(uid)
    
    return unclassified


def main():
    print("=" * 70)
    print("CHECKING HIRING INTENT IN UNCLASSIFIED USERS")
    print("=" * 70)
    
    unclassified = get_unclassified_users()
    print(f"\nFound {len(unclassified)} unclassified users\n")
    
    users_with_hiring_intent = []
    users_without_hiring_intent = []
    
    for i, uid in enumerate(unclassified, 1):
        profile = get_user_profile(uid) or {}
        name = profile.get("name") or uid
        
        print(f"[{i}/{len(unclassified)}] {name} ({uid})")
        
        results = search_conversation_for_hiring_keywords(uid)
        
        if results['has_hiring_intent']:
            print(f"  ✅ HIRING INTENT DETECTED")
            print(f"     Signals found: {len(results['hiring_signals'])}")
            for signal in results['hiring_signals'][:3]:  # Show first 3
                print(f"     - '{signal['keyword']}': {signal['context'][:80]}...")
            users_with_hiring_intent.append({
                'uid': uid,
                'name': name,
                'signals': results['hiring_signals']
            })
        else:
            if results['hiring_signals']:
                print(f"  ⚠️  Some hiring keywords found but weak signal")
                print(f"     Keywords: {[s['keyword'] for s in results['hiring_signals']]}")
            else:
                print(f"  ❌ No hiring intent detected")
            users_without_hiring_intent.append(uid)
        
        print()
    
    print("=" * 70)
    print(f"SUMMARY:")
    print(f"  ✅ Users with hiring intent: {len(users_with_hiring_intent)}")
    print(f"  ❌ Users without hiring intent: {len(users_without_hiring_intent)}")
    print("=" * 70)
    
    if users_with_hiring_intent:
        print(f"\n📋 USERS WITH HIRING INTENT ({len(users_with_hiring_intent)}):")
        for user in users_with_hiring_intent:
            print(f"\n  - {user['name']} ({user['uid']})")
            print(f"    Keywords found: {', '.join([s['keyword'] for s in user['signals']])}")


if __name__ == "__main__":
    main()

