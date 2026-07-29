# Profile Creation & Audio URL Fixes Summary

## Issues Fixed

### 1. **Profile Creation Before Profile Link Sending**
- **Problem**: Profile link was being sent even if `user_profiles/{uid}` document didn't exist
- **Fix**: Added automatic profile creation in `_send_profile_link_to_candidate()` if profile is missing
- **Location**: `api/webhooks.py::_send_profile_link_to_candidate()`

### 2. **Complete Profile Creation in Post-Call Workflow**
- **Problem**: `_step_store_extraction()` was only storing basic fields, not creating full profile with slug
- **Fix**: For job seekers/candidates, now calls `voice_extraction_service._sync_job_seeker_profile()` to create complete profile with:
  - Slug generation
  - High-signal fields (story, strengths, proof, thoughts)
  - Avatar URL
  - Qdrant indexing
- **Location**: `services/post_call_workflow.py::_step_store_extraction()`

### 3. **Audio URL Attachment Improvements**
- **Problem**: Audio URLs sometimes empty because:
  - `conversation_id` missing from payload
  - Audio webhook arrives before post-call webhook
  - ElevenLabs API call fails silently
- **Fixes**:
  - Added fallback to retrieve `conversation_id` from saved call memory
  - Added tracking of `audio_conversation_id` and `audio_fetch_attempted_at` in profile
  - Improved audio webhook handler to find user_id even if call not saved yet
  - Better error logging and retry logic
- **Locations**: 
  - `services/post_call_workflow.py::_step_attach_profile_audio()`
  - `services/profile_audio_service.py::attach_call_recording_to_profile()`
  - `api/webhooks.py::_handle_post_call_audio()`

### 4. **Empty Profile Fields**
- **Problem**: Some profiles had empty fields (linkedin_url, avatar_url, story, etc.)
- **Root Cause**: Profile creation wasn't always triggered or failed silently
- **Fix**: 
  - Ensure `_sync_job_seeker_profile()` is called for all job seekers in post-call workflow
  - This generates all high-signal fields using Claude
  - Falls back gracefully if generation fails

## Verification Script

Created `scripts/verify_profile_completeness.py` to check:
- User profile existence
- Extraction data completeness
- Public profile fields (slug, audio URLs, story, strengths, etc.)
- Call summary status
- Profile link delivery status
- Latest call conversation_id

Usage:
```bash
uv run python scripts/verify_profile_completeness.py <uid>
```

## Workflow Improvements

### Post-Call Workflow Order (for candidates):
1. `identify_user` - Extract user ID
2. `load_user_data` - Load profile and extraction
3. `save_call_memory` - Save call transcript (increments call count)
4. `attach_profile_audio` - Try to attach audio (non-blocking)
5. `store_extraction` - **NOW CREATES COMPLETE PROFILE** with slug
6. `send_referrals` - Send referral messages
7. `decide_profiles` - Decide if should send profiles (for founders)
8. `find_matches` - Find candidate matches (for founders)
9. `send_profiles` - Send matches (for founders)

### After Workflow Completes:
- `_send_profile_link_to_candidate()` is called
- **NOW CREATES PROFILE IF MISSING** before sending link
- Checks all conditions (user_type, first_call, idempotency)
- Sends profile link via WhatsApp

## Audio Attachment Flow

### Primary Flow (Post-Call Webhook):
1. Post-call webhook arrives with `conversation_id`
2. `_step_attach_profile_audio()` tries to fetch audio from ElevenLabs API
3. If `conversation_id` missing, retrieves from saved call memory
4. Stores audio URLs in `user_profiles/{uid}`

### Fallback Flow (Audio Webhook):
1. Audio webhook arrives later with `conversation_id` and `full_audio`
2. `_handle_post_call_audio()` finds user_id by:
   - Looking up call in `user_calls/{uid}/calls` by `conversation_id`
   - OR checking `user_profiles` for `audio_conversation_id` match
3. Attaches audio to profile

## Testing

To verify everything works:
1. Run verification script on a test UID
2. Check logs for:
   - `✅ [STORAGE] Created complete profile with slug`
   - `✅ [PROFILE_AUDIO] Attached recording to profile`
   - `✅ [PROFILE_LINK] Profile link sent`

## Next Steps

1. **Monitor**: Watch logs for any profile creation failures
2. **Retry Logic**: Consider adding retry for audio fetch if ElevenLabs API fails
3. **Backfill**: Run script to backfill missing profiles for existing users
4. **Validation**: Add validation to ensure all required fields are present before sending profile link

