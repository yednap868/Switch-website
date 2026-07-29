# Create Users from Resumes

## Overview

This script creates complete Firestore user records from resume data, storing all information including:
- User document in `users` collection
- Extraction data in `extractions` collection
- Profile document in `user_profiles` collection
- Resume file path/URL
- Extracted phone numbers, experience, skills, etc.

## Usage

### From CSV File

```bash
# Basic usage
python3 scripts/create_users_from_resumes.py --csv candidate_details.csv

# With resume directory (to match resume files)
python3 scripts/create_users_from_resumes.py --csv candidate_details.csv --resume-dir ~/Downloads/linkedin_resumes_direct
```

**CSV Format:**
- `name` - Candidate name (required)
- `phone` - Phone number (required)
- `brief` - Brief description (optional)
- `file` - Resume PDF filename (optional, if resume-dir provided)

### From Resume Directory

```bash
# Process all PDFs in a directory
python3 scripts/create_users_from_resumes.py --resume-dir ~/Downloads/linkedin_resumes_direct
```

The script will:
1. Extract name, phone, email, LinkedIn, brief from each PDF
2. Extract numbers (experience, salary, etc.)
3. Create complete user records

### From Single Resume

```bash
python3 scripts/create_users_from_resumes.py \
  --resume /path/to/resume.pdf \
  --name "John Doe" \
  --phone "919876543210" \
  --email "john@example.com" \
  --linkedin "https://linkedin.com/in/johndoe"
```

## What Gets Created

### 1. User Document (`users/{user_id}`)

```json
{
  "wa_id": "919876543210",
  "phone": "919876543210",
  "email": "john@example.com",
  "name": "John Doe",
  "profile": {
    "user_type": "job_seeker",
    "name": "John Doe",
    "email": "john@example.com",
    "linkedin_url": "https://linkedin.com/in/johndoe"
  },
  "state": "onboarding",
  "created_at": 1234567890,
  "last_interaction": 1234567890,
  "source": "resume_import"
}
```

### 2. Extraction Data (`extractions/{user_id}`)

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "phone_number": "919876543210",
  "the_story": "Brief description...",
  "summary": "Brief description...",
  "resume_path": "/path/to/resume.pdf",
  "resume_url": "/path/to/resume.pdf",
  "resume_filename": "John_Doe_Resume.pdf",
  "resume_extracted_numbers": {
    "phone_number": "919876543210",
    "years_of_experience": 5.0,
    "salary_expectation": "15L",
    "years_at_companies": [2.0, 3.0],
    "number_of_companies": 2,
    "graduation_year": 2018
  },
  "work_experience": "5 years"
}
```

### 3. Profile Document (`user_profiles/{user_id}`)

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "extraction_data": { /* full extraction data */ },
  "intent": "job_seeker_need",
  "slug": "john-doe",
  "created_at": 1234567890,
  "updated_at": 1234567890,
  "source": "resume_import"
}
```

## User ID Generation

User IDs are generated with priority:
1. **Phone number** (primary) - Used as WhatsApp ID
   - 10 digits → adds "91" prefix
   - Example: `9876543210` → `919876543210`
2. **Email hash** (fallback) - If no phone
3. **Name hash** (fallback) - If no phone or email
4. **Timestamp** (last resort)

## Resume Storage

Currently, the script stores the resume file path. Options:

1. **File Path** (current) - Stores full path to resume file
2. **Copy to Storage** (future) - Can be updated to copy resumes to a central directory
3. **Firebase Storage** (future) - Can be updated to upload to Firebase Storage and store URL

## Profile Sync

After creating the user, the script automatically:
- Syncs the profile using `voice_extraction_service._sync_job_seeker_profile()`
- Generates a proper slug
- Creates complete profile structure
- Makes the profile discoverable for matching

## Integration with Post-Call Workflow

When an outbound call is made to these users:
1. Call data is extracted
2. Combined with existing resume data
3. Profile is updated
4. Profile link is sent via WhatsApp template using resume phone number

## Example

```bash
# Process your CSV
python3 scripts/create_users_from_resumes.py \
  --csv ~/Downloads/candidate_details.csv \
  --resume-dir ~/Downloads/linkedin_resumes_direct
```

**Output:**
```
📁 Reading CSV: ~/Downloads/candidate_details.csv

👤 Creating user: 919876543210
   Name: John Doe
   Phone: 919876543210
   Email: john@example.com
   LinkedIn: https://linkedin.com/in/johndoe
   ✅ Created user document: users/919876543210
   ✅ Saved extraction data: extractions/919876543210
   ✅ Created profile document: user_profiles/919876543210
   ✅ Synced complete profile with slug

======================================================================
✅ Created 31 users
⚠️  Skipped 0 rows
======================================================================
```

## Verification

After running, verify users were created:

```python
from utils.db import fs, get_user_profile

# Check user
user_doc = fs.collection("users").document("919876543210").get()
print(user_doc.to_dict())

# Check profile
profile = get_user_profile("919876543210")
print(profile)
```

## Notes

- **Duplicate Handling:** If a user with the same phone already exists, data is merged (not overwritten)
- **Phone Formatting:** 10-digit numbers automatically get "91" prefix
- **Resume Extraction:** Numbers, experience, skills are automatically extracted from PDFs
- **Profile Completeness:** Profiles are synced to ensure they're complete and discoverable

