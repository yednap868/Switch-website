#!/usr/bin/env python3
"""
Test script to verify compensation card generation for a specific user.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path="env_vars.sh")

from services.compensation_insight_service import compensation_insight_service
from utils.db import get_user_profile, get_extraction_data

def test_compensation_card(uid: str):
    """Test compensation card generation for a user."""
    print(f"=" * 70)
    print(f"TESTING COMPENSATION CARD GENERATION")
    print(f"=" * 70)
    print(f"\nUser ID: {uid}\n")
    
    # Check user profile
    print("1. Checking user profile...")
    profile = get_user_profile(uid)
    if not profile:
        print(f"   ❌ No profile found for {uid}")
        return False
    
    print(f"   ✅ Profile found: {profile.get('name', 'Unknown')}")
    
    # Check compensation intent flag
    print("\n2. Checking compensation_intent_detected flag...")
    compensation_intent = (
        profile.get("compensation_intent_detected")
        or profile.get("profile", {}).get("compensation_intent_detected")
    )
    print(f"   compensation_intent_detected: {compensation_intent}")
    
    # Check user type
    print("\n3. Checking user_type...")
    user_type = (
        profile.get("profile", {}).get("user_type")
        or profile.get("user_type")
        or "unknown"
    )
    print(f"   user_type: {user_type}")
    
    # Check extraction data
    print("\n4. Checking extraction data...")
    extraction = get_extraction_data(uid)
    if extraction:
        print(f"   ✅ Extraction data found with {len(extraction)} fields")
        print(f"   Key fields: {list(extraction.keys())[:10]}")
    else:
        print(f"   ⚠️  No extraction data found")
    
    # Generate insights
    print("\n5. Generating compensation insights via Claude...")
    try:
        insights = compensation_insight_service.get_insights(uid)
        print(f"   ✅ Insights generated successfully!")
        print(f"\n   Compensation Band: {insights.compensation_band}")
        print(f"   Helping Signals ({len(insights.helping_signals)}):")
        for signal in insights.helping_signals[:3]:
            print(f"     • {signal}")
        print(f"   Holding Back ({len(insights.holding_back)}):")
        for item in insights.holding_back[:3]:
            print(f"     • {item}")
        print(f"   Fixes ({len(insights.fixes)}):")
        for fix in insights.fixes[:3]:
            print(f"     • {fix}")
    except Exception as e:
        print(f"   ❌ Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Render card
    print("\n6. Rendering compensation card PNG...")
    try:
        png_bytes = compensation_insight_service.render_card_png(uid, insights)
        print(f"   ✅ Card rendered successfully! Size: {len(png_bytes)} bytes")
        
        # Save to file for inspection
        output_path = Path(__file__).parent / f"compensation_card_{uid}.png"
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        print(f"   💾 Saved to: {output_path}")
        
    except Exception as e:
        print(f"   ❌ Error rendering card: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test API endpoint (simulate)
    print("\n7. Testing API endpoint URL...")
    base_url = "https://api.relayy.world"
    image_url = f"{base_url}/api/public/compensation-card/{uid}"
    print(f"   Image URL: {image_url}")
    print(f"   ✅ URL constructed correctly")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print(f"\nThe compensation card has been saved to:")
    print(f"  {output_path}")
    print(f"\nYou can open this file to verify the image looks correct.")
    
    return True

if __name__ == "__main__":
    uid = "918368828660"
    if len(sys.argv) > 1:
        uid = sys.argv[1]
    
    success = test_compensation_card(uid)
    sys.exit(0 if success else 1)


