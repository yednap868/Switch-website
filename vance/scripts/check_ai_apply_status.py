"""
Check AI Apply status for a specific user.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def check_user_applications(user_id: str):
    """Check all job applications for a user."""
    print(f"\n🔍 Checking AI Apply status for user: {user_id}\n")
    print("=" * 80)
    
    try:
        # Query all applications for this user
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
                applied_time = datetime.fromtimestamp(app.get('applied_at'))
                print(f"Applied At: {applied_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if app.get('updated_at'):
                updated_time = datetime.fromtimestamp(app.get('updated_at'))
                print(f"Last Updated: {updated_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if app.get('error_message'):
                print(f"❌ Error: {app.get('error_message')}")
            
            if app.get('form_fields'):
                print(f"✅ Form Fields Filled: {len(app.get('form_fields', []))}")
                for field in app.get('form_fields', [])[:5]:  # Show first 5
                    print(f"   - {field.get('label', 'N/A')}: {field.get('value', 'N/A')[:50]}")
                if len(app.get('form_fields', [])) > 5:
                    print(f"   ... and {len(app.get('form_fields', [])) - 5} more fields")
            
            if app.get('screenshots'):
                screenshots = app.get('screenshots', {})
                print(f"📸 Screenshots: {', '.join(screenshots.keys())}")
            
            if app.get('status') == 'submitted':
                print("✅ SUCCESS: Application was submitted successfully!")
            elif app.get('status') == 'processing':
                print("⏳ IN PROGRESS: Application is still being processed")
            elif app.get('status') == 'failed':
                print("❌ FAILED: Application failed")
            elif app.get('status') == 'form_filled':
                print("⚠️ PARTIAL: Form was filled but may need manual submission")
            
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
        
    except Exception as e:
        print(f"❌ Error checking applications: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "917059303328"
    check_user_applications(user_id)


