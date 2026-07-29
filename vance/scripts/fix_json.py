"""Fix malformed JSON file"""
import json

input_file = "/Users/alt/Downloads/gurgaon_startup_jobs.json"
output_file = "/Users/alt/Downloads/gurgaon_startup_jobs_fixed.json"

# Read file as text
with open(input_file, 'r') as f:
    content = f.read()

# Fix incomplete company_stage at line 1323
content = content.replace('"company_stage": "Late[', '"company_stage": "Late Stage",')

# Find where duplicates start - look for second '['
first_bracket_end = content.find(']')
if first_bracket_end > 0:
    # Check if there's another opening bracket after
    next_open = content.find('[', first_bracket_end + 1)
    if next_open > 0:
        # Remove everything after first ]
        content = content[:first_bracket_end + 1]

# Parse and deduplicate
try:
    jobs = json.loads(content)
    print(f"✅ Parsed {len(jobs)} jobs from original")
    
    # Deduplicate based on title+company
    seen = set()
    unique_jobs = []
    for job in jobs:
        key = (job.get('title', ''), job.get('company', ''))
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    jobs = unique_jobs
    print(f"✅ Deduplicated to {len(unique_jobs)} unique jobs")
    
    # Write fixed file
    with open(output_file, 'w') as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"✅ Fixed file saved to: {output_file}")
    
except Exception as e:
    print(f"❌ Could not parse JSON: {e}")
    import traceback
    traceback.print_exc()
