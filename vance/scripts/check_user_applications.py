#!/usr/bin/env python3
"""
Check what jobs a user applied to and what Vance filled on their behalf.

Usage:
    python3 scripts/check_user_applications.py 918368828660
"""

import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def check_user_applications(user_id: str):
    """Check all job applications for a user and what was filled."""
    print(f"\n{'='*80}")
    print(f"Checking Job Applications for UID: {user_id}")
    print(f"{'='*80}\n")
    
    # Query job_applications collection for this user
    apps_ref = fs.collection("job_applications")
    user_apps = apps_ref.where("user_id", "==", user_id).stream()
    
    applications = []
    for app_doc in user_apps:
        app_data = app_doc.to_dict() or {}
        applications.append({
            "application_id": app_doc.id,
            **app_data
        })
    
    if not applications:
        print(f"❌ No job applications found for user {user_id}")
        return
    
    print(f"✅ Found {len(applications)} job application(s):\n")
    
    for i, app in enumerate(applications, 1):
        print(f"\n{'─'*80}")
        print(f"Application #{i}: {app['application_id']}")
        print(f"{'─'*80}")
        
        # Basic info
        print(f"\n📋 Job Details:")
        print(f"   Job Title: {app.get('job_title', 'N/A')}")
        print(f"   Company: {app.get('company', 'N/A')}")
        
        # Status
        status = app.get('status', 'unknown')
        status_emoji = {
            'submitted': '✅',
            'form_filled': '⏳',
            'processing': '🔄',
            'pending': '⏳',
            'form_partial': '⚠️',
            'error': '❌'
        }.get(status, '📝')
        print(f"   Status: {status_emoji} {status}")
        
        if app.get('current_step'):
            print(f"   Current Step: {app.get('current_step')}")
        
        # Timestamp
        if app.get('applied_at'):
            applied_date = datetime.fromtimestamp(app.get('applied_at'))
            print(f"   Applied At: {applied_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Form fields filled
        form_fields = app.get('form_fields', [])
        if form_fields:
            print(f"\n📝 Form Fields Filled by Vance ({len(form_fields)} fields):")
            for j, field in enumerate(form_fields, 1):
                print(f"   {j}. {field.get('label', field.get('field_name', 'Unknown'))}")
                value = field.get('value', '')
                if len(value) > 100:
                    value = value[:100] + "..."
                print(f"      Value: {value}")
                if field.get('selector'):
                    print(f"      Selector: {field.get('selector')}")
        else:
            print(f"\n⚠️  No form fields captured")
        
        # Timeline
        timeline = app.get('timeline', [])
        if timeline:
            print(f"\n⏱️  Application Timeline ({len(timeline)} steps):")
            for j, step in enumerate(timeline, 1):
                step_time = datetime.fromtimestamp(step.get('timestamp', 0))
                print(f"   {j}. {step.get('action', 'Unknown action')}")
                print(f"      Step: {step.get('step', 'N/A')}")
                print(f"      Time: {step_time.strftime('%H:%M:%S')}")
                if step.get('fields_filled'):
                    print(f"      Fields Filled: {step.get('fields_filled')}")
                if step.get('url'):
                    print(f"      URL: {step.get('url')}")
        else:
            print(f"\n⚠️  No timeline data")
        
        # Screenshots
        screenshots = app.get('screenshots', {})
        if screenshots:
            print(f"\n📸 Screenshots Captured ({len(screenshots)} screenshots):")
            for key in screenshots.keys():
                screenshot_data = screenshots[key]
                if screenshot_data:
                    # Calculate size (approx)
                    size_kb = len(screenshot_data) / 1024
                    print(f"   • {key}: {size_kb:.1f} KB (base64 encoded)")
                else:
                    print(f"   • {key}: Empty/Null")
        else:
            print(f"\n⚠️  No screenshots captured")
        
        # Error messages
        if app.get('error_message'):
            print(f"\n❌ Error: {app.get('error_message')}")
        
        # Application URL
        if app.get('application_url'):
            print(f"\n🌐 Application URL: {app.get('application_url')}")
        
        if app.get('job_url'):
            print(f"   Job URL: {app.get('job_url')}")
    
    print(f"\n{'='*80}")
    print(f"Summary: {len(applications)} application(s) found")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check user job applications")
    parser.add_argument("user_id", help="User ID to check applications for")
    args = parser.parse_args()
    
    check_user_applications(args.user_id)

