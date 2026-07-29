"""Fix malformed JSON file - simpler approach"""
import json

input_file = "/Users/alt/Downloads/gurgaon_startup_jobs.json"
output_file = "/Users/alt/Downloads/gurgaon_startup_jobs_fixed.json"

# Read file as text
with open(input_file, 'r') as f:
    lines = f.readlines()

# Fix line 1323 (index 1322) - incomplete company_stage
fixed_lines = []
for i, line in enumerate(lines):
    if i == 1322:  # Line 1323 (0-indexed)
        line = line.replace('"Late[', '"Late Stage",')
    fixed_lines.append(line)

content = ''.join(fixed_lines)

# Find the end of the first complete JSON array
# Look for the pattern: ] followed by newline and [
bracket_pos = content.find(']\n  {')
if bracket_pos > 0:
    # This means we found duplicate entries starting
    # Find the previous ] which should be the end of first array
    # Actually, the pattern is: ],\n  { (comma before newline)
    # Or ]\n  [ (array ends, new array starts)
    first_array_end = content.rfind(']', 0, bracket_pos)
    if first_array_end > 0:
        # Use everything up to and including this ]
        content = content[:first_array_end + 1]

# Try to parse
try:
    jobs = json.loads(content)
    print(f"✅ Parsed {len(jobs)} jobs")
    
    # Deduplicate
    seen = set()
    unique_jobs = []
    for job in jobs:
        key = (job.get('title', ''), job.get('company', ''))
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    print(f"✅ Deduplicated to {len(unique_jobs)} unique jobs")
    
    with open(output_file, 'w') as f:
        json.dump(unique_jobs, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved to {output_file}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    # Try to find line with error
    try:
        json.loads(content[:2000])
    except json.JSONDecodeError as je:
        print(f"JSON error at line {je.lineno}, column {je.colno}")

