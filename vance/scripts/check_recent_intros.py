#!/usr/bin/env python3
"""Check recent intro requests."""

import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import fs

# Get all intro_requests from last 7 days
print('='*70)
print('INTRO REQUESTS FROM LAST 7 DAYS')
print('='*70)

week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).timestamp()

intro_requests_ref = fs.collection('intro_requests')
all_intros = intro_requests_ref.stream()

recent_intros = []
for doc in all_intros:
    data = doc.to_dict() or {}
    requested_at = data.get('requested_at')
    
    if isinstance(requested_at, str):
        try:
            requested_at = float(requested_at)
        except:
            continue
    
    if requested_at and requested_at >= week_ago:
        recent_intros.append({
            'doc_id': doc.id,
            'data': data,
            'requested_at': requested_at,
        })

# Sort by time
recent_intros.sort(key=lambda x: x['requested_at'], reverse=True)

print(f'\nTotal intro requests in last 7 days: {len(recent_intros)}\n')

for i, intro in enumerate(recent_intros[:20], 1):  # Show last 20
    data = intro['data']
    requested_at = intro['requested_at']
    requested_time = datetime.fromtimestamp(requested_at, tz=timezone.utc)
    
    requester_uid = data.get('requester_uid') or data.get('job_provider_uid', 'N/A')
    requester_name = data.get('requester_name') or data.get('job_provider_name', 'N/A')
    candidate_uid = data.get('candidate_uid', 'N/A')
    candidate_name = data.get('candidate_name', 'N/A')
    status = data.get('status', 'N/A')
    source = data.get('source', 'N/A')
    
    print(f'{i}. {requested_time.strftime("%Y-%m-%d %H:%M:%S UTC")}')
    print(f'   Requester: {requester_name} ({requester_uid})')
    print(f'   Candidate: {candidate_name} ({candidate_uid})')
    print(f'   Status: {status} | Source: {source}')
    print('-'*70)

