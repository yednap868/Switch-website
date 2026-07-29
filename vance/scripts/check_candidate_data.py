#!/usr/bin/env python3
"""Check candidate extraction data format."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_extraction_data, get_user_profile

# Check Merlyn's data (Technical PM)
uid = '916364054808'
ext_data = get_extraction_data(uid) or {}
user_profile = get_user_profile(uid) or {}

print('='*70)
print(f'Merlyn (UID: {uid})')
print('='*70)
print(f'Target Role: {ext_data.get("target_role", "N/A")}')
print(f'Years of Experience: {ext_data.get("years_of_experience", "N/A")}')
print(f'Work Experience Type: {type(ext_data.get("work_experience", None))}')
print(f'Work Experience:')
print(json.dumps(ext_data.get("work_experience", []), indent=2, default=str))
print('='*70)

# Check Ashuthosh (AI Product Manager)
uid2 = '917507544152'
ext_data2 = get_extraction_data(uid2) or {}
print(f'\nAshuthosh (UID: {uid2})')
print('='*70)
print(f'Target Role: {ext_data2.get("target_role", "N/A")}')
print(f'Years of Experience: {ext_data2.get("years_of_experience", "N/A")}')
print(f'Work Experience Type: {type(ext_data2.get("work_experience", None))}')
print(f'Work Experience:')
print(json.dumps(ext_data2.get("work_experience", []), indent=2, default=str))
print('='*70)

