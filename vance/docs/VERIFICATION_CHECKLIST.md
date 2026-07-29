# Verification Checklist: Resume Phone & Profile Link Integration

## Pre-Deployment Verification

### ✅ Code Changes

- [x] **CSV Generation Script**
  - File: `scripts/create_candidate_csv_from_resumes.py`
  - Extracts name, phone (with 91 prefix), brief from PDFs
  - Status: ✅ Created

- [x] **Post-Call Workflow**
  - File: `services/post_call_workflow.py`
  - Extracts resume phone numbers
  - Creates profiles with call + resume data
  - Status: ✅ Updated (method exists but commented out - handled in webhook)

- [x] **Webhook Handler**
  - File: `api/webhooks.py`
  - Function: `_send_profile_link_to_candidate()`
  - Uses resume phone number (priority)
  - Sends via WhatsApp template
  - Status: ✅ Updated

- [x] **Template Registration**
  - Template Name: `profile_ready`
  - Status: ✅ Registered (per user)

### ✅ Integration Points

1. **Resume Phone Extraction**
   - Location: `services/resume_number_extraction_service.py`
   - Already integrated in `voice_extraction_service._sync_job_seeker_profile()`
   - Extracts phone during profile sync
   - Status: ✅ Working

2. **Profile Creation**
   - Location: `services/voice_extraction_service.py`
   - Method: `_sync_job_seeker_profile()`
   - Combines call data + resume data
   - Creates slug and public profile
   - Status: ✅ Working

3. **Profile Link Sending**
   - Location: `api/webhooks.py`
   - Function: `_send_profile_link_to_candidate()`
   - Called after post-call workflow completes
   - Status: ✅ Updated with template + resume phone

## Testing Checklist

### Test 1: Resume Phone Extraction
```bash
# Test with a user who has a resume
python3 scripts/test_profile_link_sending.py <uid>
```

**Expected:**
- ✅ Resume phone number extracted
- ✅ Phone formatted correctly (10 digits → 91 prefix)
- ✅ Phone source logged

### Test 2: Profile Creation
```bash
# Check if profile exists and has all fields
python3 scripts/test_profile_link_sending.py <uid>
```

**Expected:**
- ✅ Profile exists in `user_profiles/{uid}`
- ✅ Has `slug` field
- ✅ Has `extraction_data` with resume numbers
- ✅ Profile URL: `https://profiles.vance.so/{slug}`

### Test 3: Template Message (Dry Run)
```bash
# Test template payload without sending
python3 scripts/test_profile_link_sending.py <uid>
```

**Expected:**
- ✅ Template payload generated correctly
- ✅ Parameters: [candidate_name, profile_url]
- ✅ Phone number from resume (if available)

### Test 4: Template Message (Live)
```bash
# Actually send the message
python3 scripts/test_profile_link_sending.py <uid> --send
```

**Expected:**
- ✅ Template message sent successfully
- ✅ Message received on WhatsApp
- ✅ Profile link is clickable

### Test 5: End-to-End Flow
1. Make an outbound call to a candidate with a resume
2. After call ends, check logs for:
   - ✅ Profile created
   - ✅ Resume phone extracted
   - ✅ Template message sent
   - ✅ Message delivered

## Verification Steps

### Step 1: Check Code Integration

```bash
# Verify webhook handler has resume phone logic
grep -A 20 "Extract phone number from resume" api/webhooks.py

# Verify template is used
grep -A 10 "template_name = \"profile_ready\"" api/webhooks.py
```

### Step 2: Check Template Registration

1. Go to Meta Business Suite → WhatsApp Manager → Message Templates
2. Verify `profile_ready` template exists
3. Verify status is "Approved"
4. Verify template format matches:
   ```
   Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you.
   ```

### Step 3: Test with Real Data

1. **Find a test user with resume:**
   ```python
   # Check Firestore for user with resume
   # user_profiles/{uid}/extraction_data/resume_extracted_numbers/phone_number
   ```

2. **Run test script:**
   ```bash
   python3 scripts/test_profile_link_sending.py <test_uid>
   ```

3. **Verify output:**
   - Resume phone extracted
   - Profile exists
   - Template payload correct

### Step 4: Monitor Production Logs

After deployment, monitor logs for:
- `[PROFILE_LINK] Using phone from resume: {wa_id}`
- `[PROFILE_LINK] Sent via template 'profile_ready'`
- `[PROFILE_LINK] Profile link sent to {uid} at {wa_id}`

## Common Issues & Solutions

### Issue 1: Template Not Found
**Symptom:** `Template 'profile_ready' failed, falling back to text`

**Solution:**
- Verify template is registered and approved
- Check template name matches exactly: `profile_ready`
- Wait for template approval (24-48 hours)

### Issue 2: No Resume Phone
**Symptom:** `Using phone from profile: {wa_id}` (not resume)

**Solution:**
- Check if resume was processed: `extraction_data/resume_extracted_numbers`
- Verify resume URL exists in profile
- Check resume extraction service logs

### Issue 3: Profile Not Created
**Symptom:** `No user_profiles document for {uid}`

**Solution:**
- Verify `_sync_job_seeker_profile()` is called
- Check extraction data exists
- Verify user_type is "job_seeker" or "candidate"

### Issue 4: Phone Format Wrong
**Symptom:** Message fails to send

**Solution:**
- Verify phone formatting logic (10 digits → 91 prefix)
- Check phone number is valid WhatsApp number
- Verify phone doesn't have extra characters

## Deployment Checklist

Before moving to production:

- [ ] All code changes reviewed
- [ ] Template `profile_ready` registered and approved
- [ ] Test script passes for test user
- [ ] End-to-end test completed successfully
- [ ] Logs verified for correct behavior
- [ ] Fallback to text message works if template fails
- [ ] Phone number formatting verified
- [ ] Profile creation verified

## Post-Deployment Monitoring

Monitor these metrics:
1. **Profile Link Send Rate:** % of first calls that receive profile links
2. **Template Usage:** % using template vs text fallback
3. **Resume Phone Usage:** % using resume phone vs profile phone
4. **Delivery Success:** % of messages successfully delivered

## Files Changed

1. `api/webhooks.py` - Updated `_send_profile_link_to_candidate()`
2. `services/post_call_workflow.py` - Updated `_step_send_profile_to_candidate()` (backup)
3. `scripts/create_candidate_csv_from_resumes.py` - New CSV generation
4. `scripts/test_profile_link_sending.py` - New test script
5. `docs/profile_ready_template_registration.md` - Template guide
6. `docs/RESUME_PHONE_PROFILE_INTEGRATION.md` - Integration docs
7. `docs/VERIFICATION_CHECKLIST.md` - This file

