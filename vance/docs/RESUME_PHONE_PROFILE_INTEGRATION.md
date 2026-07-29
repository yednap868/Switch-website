# Resume Phone Number & Profile Link Integration

## Overview

After outbound calls end, Vance now:
1. Extracts phone numbers from candidate resumes (if available)
2. Creates a profile using call data + resume data
3. Sends profile link via WhatsApp template message using the resume phone number

## Components

### 1. CSV Generation Script

**File:** `scripts/create_candidate_csv_from_resumes.py`

**Usage:**
```bash
# Process resumes from a directory
python3 scripts/create_candidate_csv_from_resumes.py ~/Downloads/linkedin_resumes_direct

# Specify output file
python3 scripts/create_candidate_csv_from_resumes.py ~/Downloads/linkedin_resumes_direct --output candidates.csv
```

**Output CSV Columns:**
- `name` - Candidate name extracted from resume
- `phone` - Phone number (10 digits automatically prefixed with 91)
- `brief` - Brief description/about section
- `file` - Original PDF filename

**Phone Number Formatting:**
- If phone number is 10 digits → automatically adds "91" prefix (India country code)
- Example: `9876543210` → `919876543210`

### 2. Post-Call Workflow Integration

**File:** `services/post_call_workflow.py`

**Changes:**
- Modified `_step_send_profile_to_candidate()` method
- Extracts phone number from resume if available
- Uses resume phone number for WhatsApp delivery
- Sends profile link via WhatsApp template message

**Phone Number Priority:**
1. Resume extracted phone number (highest priority)
2. Profile phone number
3. Extraction data phone number
4. User ID (fallback)

### 3. Profile Creation

Profiles are created using:
- **Call data** - Extracted from voice call transcript
- **Resume data** - Extracted numbers, skills, experience from PDF
- Combined into a complete candidate profile

**Profile includes:**
- Name, email, LinkedIn
- Skills and experience
- Target role
- Work history
- Public profile URL: `https://profiles.vance.so/{slug}`

## WhatsApp Template Message

### Template Details

**Template Name:** `profile_ready`  
**Category:** UTILITY  
**Language:** English

**Template Format:**
```
Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you.
```

**Parameters:**
1. `{{1}}` - Candidate name
2. `{{2}}` - Profile URL (https://profiles.vance.so/{slug})

### Registration Required

You need to register this template in WhatsApp Business Manager:

1. Go to [Meta Business Suite](https://business.facebook.com)
2. Navigate to **WhatsApp Manager** → **Message Templates**
3. Create new template:
   - **Name:** `profile_ready`
   - **Category:** UTILITY
   - **Language:** English
   - **Body:** `Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you.`
4. Add 2 text variables: `{{1}}` and `{{2}}`
5. Submit for approval (24-48 hours)

**Full registration guide:** See `docs/profile_ready_template_registration.md`

### Fallback Behavior

If the template is not registered or fails:
- System automatically falls back to regular text message
- Profile links still get sent
- No interruption to workflow

## Workflow Flow

```
Outbound Call Ends
    ↓
Post-Call Workflow Starts
    ↓
1. Extract call data
2. Extract resume data (if resume URL exists)
   - Phone number
   - Experience
   - Skills
   - Other numbers
    ↓
3. Create/Update Profile
   - Merge call + resume data
   - Generate public slug
   - Store in Firestore + Qdrant
    ↓
4. Send Profile Link
   - Get phone from resume (priority) or profile
   - Format phone (add 91 if 10 digits)
   - Send via WhatsApp template
   - Template: "Hey {name}, ... {profile_url} ..."
    ↓
Profile Link Delivered ✅
```

## Testing

### Test CSV Generation
```bash
# Test with your downloaded resumes
python3 scripts/create_candidate_csv_from_resumes.py ~/Downloads/linkedin_resumes_direct --output test_candidates.csv
```

### Test Profile Link Sending
1. Make an outbound call to a candidate with a resume
2. After call ends, check:
   - Profile created in Firestore (`user_profiles/{uid}`)
   - Phone number extracted from resume
   - WhatsApp message sent with profile link
   - Message uses template (if registered) or text (fallback)

## Important Notes

1. **Phone Number Format:**
   - 10-digit numbers automatically get "91" prefix
   - Already formatted numbers (with country code) are used as-is

2. **Resume Phone Priority:**
   - Resume phone numbers take priority over profile phone numbers
   - This ensures we use the most up-to-date contact information

3. **Template Registration:**
   - Template must be approved before use
   - System falls back to text if template unavailable
   - No workflow interruption if template fails

4. **Profile Creation:**
   - Profiles combine call insights + resume data
   - More complete profiles = better matching
   - Public profile URL generated automatically

## Files Modified

1. `scripts/create_candidate_csv_from_resumes.py` - New CSV generation script
2. `services/post_call_workflow.py` - Updated to use resume phone + template
3. `docs/profile_ready_template_registration.md` - Template registration guide
4. `docs/RESUME_PHONE_PROFILE_INTEGRATION.md` - This document

## Next Steps

1. ✅ CSV generation script created
2. ✅ Post-call workflow updated
3. ⏳ **Register WhatsApp template** `profile_ready` in Meta Business Manager
4. ⏳ Test with real outbound calls
5. ⏳ Verify profile links are sent correctly

