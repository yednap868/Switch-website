#!/usr/bin/env python3
"""
Check AI Apply status via API.
Usage: python3 scripts/check_apply_via_api.py 917059303328
"""

import sys
import requests
import json
from datetime import datetime

API_BASE_URL = "https://api.relayy.world"


def check_user_applications(user_id: str):
    """Check applications via API."""
    print(f"\n🔍 Checking AI Apply status for user: {user_id}\n")
    print("=" * 80)
    
    try:
        url = f"{API_BASE_URL}/api/job-applications/status/{user_id}"
        print(f"📡 Querying: {url}\n")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return
        
        data = response.json()
        
        if data.get("status") != "success":
            print(f"❌ API returned error: {data.get('detail', 'Unknown error')}")
            return
        
        applications = data.get("applications", [])
        
        if not applications:
            print(f"❌ No job applications found for user {user_id}")
            print("\nPossible reasons:")
            print("  - User hasn't applied to any jobs yet")
            print("  - Applications are stored under a different user_id")
            print("  - Application process hasn't started")
            return
        
        print(f"✅ Found {len(applications)} application(s)\n")
        
        for i, app in enumerate(applications, 1):
            print(f"\n📋 Application #{i}")
            print("-" * 80)
            print(f"Application ID: {app.get('application_id', 'N/A')}")
            print(f"Job Title: {app.get('job_title', 'N/A')}")
            print(f"Company: {app.get('company', 'N/A')}")
            print(f"Status: {app.get('status', 'N/A')}")
            print(f"Current Step: {app.get('current_step', 'N/A')}")
            
            if app.get('applied_at'):
                try:
                    applied_time = datetime.fromtimestamp(app.get('applied_at'))
                    print(f"Applied At: {applied_time.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"Applied At: {app.get('applied_at')}")
            
            if app.get('updated_at'):
                try:
                    updated_time = datetime.fromtimestamp(app.get('updated_at'))
                    print(f"Last Updated: {updated_time.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"Last Updated: {app.get('updated_at')}")
            
            if app.get('error_message'):
                print(f"❌ Error: {app.get('error_message')}")
            
            if app.get('form_fields'):
                print(f"✅ Form Fields Filled: {len(app.get('form_fields', []))}")
                for field in app.get('form_fields', [])[:5]:  # Show first 5
                    label = field.get('label', field.get('field_name', 'N/A'))
                    value = str(field.get('value', 'N/A'))[:50]
                    print(f"   - {label}: {value}")
                if len(app.get('form_fields', [])) > 5:
                    print(f"   ... and {len(app.get('form_fields', [])) - 5} more fields")
            
            if app.get('screenshots'):
                screenshots = app.get('screenshots', {})
                print(f"📸 Screenshots: {', '.join(screenshots.keys())}")
            
            # Status summary
            status = app.get('status', 'unknown')
            if status == 'submitted':
                print("✅ SUCCESS: Application was submitted successfully!")
            elif status == 'processing':
                print("⏳ IN PROGRESS: Application is still being processed")
            elif status == 'failed':
                print("❌ FAILED: Application failed")
            elif status == 'form_filled':
                print("⚠️ PARTIAL: Form was filled but may need manual submission")
            elif status == 'pending':
                print("⏳ PENDING: Application is queued")
            
            print()
        
        print("=" * 80)
        
        # Summary
        statuses = [app.get('status', 'unknown') for app in applications]
        print(f"\n📊 Summary:")
        print(f"   Total Applications: {len(applications)}")
        print(f"   Submitted: {statuses.count('submitted')}")
        print(f"   Processing: {statuses.count('processing')}")
        print(f"   Failed: {statuses.count('failed')}")
        print(f"   Form Filled: {statuses.count('form_filled')}")
        print(f"   Pending: {statuses.count('pending')}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "917059303328"
    check_user_applications(user_id)


