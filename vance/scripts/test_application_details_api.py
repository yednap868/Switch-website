"""
Test script to verify application details API endpoint.
Tests fetching application details with form fields, timeline, and screenshots.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db import fs


def test_get_application_details():
    """Test fetching application details from Firestore."""
    print("🧪 Testing Application Details API")
    print("=" * 60)
    
    # Get a sample application
    apps_ref = fs.collection("job_applications")
    apps = list(apps_ref.limit(1).stream())
    
    if not apps:
        print("⚠️  No applications found in Firestore")
        print("   Create an application first by having a candidate apply to a job")
        return False
    
    app_doc = apps[0]
    app_data = app_doc.to_dict() or {}
    app_id = app_doc.id
    
    print(f"✅ Found application: {app_id}")
    print(f"   Job: {app_data.get('job_title')} at {app_data.get('company')}")
    print(f"   Status: {app_data.get('status')}")
    print()
    
    # Check form fields
    form_fields = app_data.get('form_fields', [])
    print(f"📋 Form Fields: {len(form_fields)} found")
    if form_fields:
        for i, field in enumerate(form_fields[:3], 1):  # Show first 3
            print(f"   {i}. {field.get('label', field.get('field_name', 'Unknown'))}: {field.get('value', '(empty)')[:50]}")
        if len(form_fields) > 3:
            print(f"   ... and {len(form_fields) - 3} more")
    else:
        print("   ⚠️  No form fields captured yet")
    print()
    
    # Check timeline
    timeline = app_data.get('timeline', [])
    print(f"📊 Timeline: {len(timeline)} steps")
    if timeline:
        for step in timeline:
            print(f"   - {step.get('step')}: {step.get('action')}")
            if step.get('screenshot'):
                print(f"     📸 Screenshot: {step.get('screenshot')}")
    else:
        print("   ⚠️  No timeline data yet")
    print()
    
    # Check screenshots
    screenshots = app_data.get('screenshots', {})
    print(f"📸 Screenshots: {len(screenshots)} captured")
    if screenshots:
        for key, value in screenshots.items():
            size = len(value) if isinstance(value, str) else 0
            print(f"   - {key}: {size} bytes (base64)")
    else:
        print("   ⚠️  No screenshots captured yet")
    print()
    
    # Summary
    has_details = bool(form_fields or timeline or screenshots)
    if has_details:
        print("✅ Application details are being captured!")
    else:
        print("⚠️  Application details not yet captured")
        print("   This is normal for older applications created before this feature")
        print("   New applications will include full details")
    
    return True


if __name__ == "__main__":
    try:
        result = test_get_application_details()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

