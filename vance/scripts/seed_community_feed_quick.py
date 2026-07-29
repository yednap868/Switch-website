#!/usr/bin/env python3
"""
Quick script to seed community feed with a small number of posts for testing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.community_ai_service import seed_community_content


def main():
    """Main function to seed community content with 10 posts."""
    print("🌱 Starting Community Feed Content Seeding (Quick Test)...")
    print("=" * 70)
    
    try:
        result = seed_community_content(posts_per_day=10)
        
        print("=" * 70)
        print(f"✅ Seeding complete!")
        print(f"   Posts created: {result['posts_created']}")
        print(f"   Comments created: {result['comments_created']}")
        print(f"   Likes created: {result['likes_created']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
