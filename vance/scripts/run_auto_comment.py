#!/usr/bin/env python3
"""
Script to run auto-comment service continuously.
Should be run as a background service or via cron every minute.
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.community_auto_comment_service import check_and_comment_on_new_posts


def main():
    """Run auto-comment check."""
    print(f"🔄 [AUTO_COMMENT] Checking for posts that need comments... {time.strftime('%Y-%m-%d %H:%M:%S')}")
    check_and_comment_on_new_posts()


if __name__ == "__main__":
    main()
