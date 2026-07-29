#!/usr/bin/env python3
"""
Clear hardcoded referral data from a user's profile.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fs


def clear_referral_data(phone: str):
    """
    Clear hardcoded referral data for the given phone number.
    """
    # Normalize phone (remove + and spaces)
    phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    user_id = phone  # user_id is the phone number
    
    print(f"🧹 Clearing referral data for phone: {phone} (user_id: {user_id})")
    print("=" * 70)
    
    try:
        user_ref = fs.collection("switch_users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"❌ User {user_id} not found in switch_users")
            return
        
        user_data = user_doc.to_dict() or {}
        profile = user_data.get("profile", {})
        
        # Check current referral data
        current_referrals = profile.get("referrals", [])
        current_earnings = profile.get("totalReferralEarnings", 0)
        current_count = profile.get("totalReferrals", 0)
        
        print(f"Current referral data:")
        print(f"  - Total referrals: {current_count}")
        print(f"  - Total earnings: ₹{current_earnings}")
        print(f"  - Referrals list: {len(current_referrals)} items")
        
        if current_referrals:
            print(f"\nReferrals:")
            for ref in current_referrals:
                print(f"  - {ref.get('name', 'Unknown')}: {ref.get('status', 'N/A')} (₹{ref.get('earnings', 0)})")
        
        # Clear referral data
        profile["referrals"] = []
        profile["totalReferralEarnings"] = 0
        profile["totalReferrals"] = 0
        
        # Update the document
        user_ref.update({
            "profile": profile,
            "updated_at": time.time() if hasattr(__import__('time'), 'time') else None,
        })
        
        print("\n✅ Cleared all referral data")
        print(f"   - Set referrals to: []")
        print(f"   - Set totalReferralEarnings to: 0")
        print(f"   - Set totalReferrals to: 0")
        
    except Exception as e:
        print(f"❌ Error clearing referral data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import time
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/clear_referral_data.py <phone_number>")
        print("Example: python3 scripts/clear_referral_data.py 918368828660")
        sys.exit(1)
    
    phone = sys.argv[1]
    clear_referral_data(phone)
