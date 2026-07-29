# Founder Referral Workflow Implementation

## Overview

Implemented a referral workflow that triggers when founders have successful interactions with Vance. The system sends a referral prompt with a unique link, tracks referrals, and attributes new signups to referring founders.

## Trigger Conditions

The referral prompt is sent when **any** of these conditions are met:

1. **Founder receives at least 1 relevant intro** - After profiles are sent via `_send_matched_profiles()`
2. **Founder marks candidate as "interviewing"** - When `select_candidates_for_interview()` is called
3. **Founder marks hire as successful** - When `mark_hire_successful()` is called

## Implementation Details

### Files Created/Modified

1. **`services/founder_referral_service.py`** (NEW)
   - `FounderReferralService` class with methods:
     - `generate_referral_code()` - Creates unique referral codes
     - `get_or_create_referral_link()` - Gets or creates referral URL
     - `should_send_referral_prompt()` - Idempotency check (max once per 7 days)
     - `send_referral_prompt()` - Sends WhatsApp message with referral link
     - `track_referral()` - Tracks when new users sign up via referral

2. **`services/post_call_workflow.py`** (MODIFIED)
   - Added referral trigger after `_send_matched_profiles()` completes
   - Triggers when `user_type` is `"job_provider"` or `"hiring"`

3. **`agent/tools/job_provider.py`** (MODIFIED)
   - Added referral trigger in `select_candidates_for_interview()` when candidates are marked for interview
   - Added new tool `mark_hire_successful()` to mark successful hires and trigger referral

### Firestore Collections

1. **`founder_referrals/{founder_uid}`**
   - Stores referral code and URL for each founder
   - Tracks `referral_count` (number of successful referrals)

2. **`founder_referral_prompts/{founder_uid}`**
   - Tracks when referral prompts were sent
   - Prevents duplicate prompts (idempotency)
   - Stores `trigger_reason`, `sent_at`, `delivery_status`

3. **`referral_relationships/{referred_uid}`**
   - Links new users to their referrer
   - Stores `referrer_uid`, `referral_code`, `created_at`

4. **`successful_hires/{hire_id}`**
   - Tracks successful hires
   - Stores `candidate_name`, `role_title`, `founder_uid`, `hired_at`

### Referral Link Format

Current format:
```
https://wa.me/12183180007?text=Hi%20Vance%2C%20{referral_code}%20sent%20me
```

The referral code is an 8-character uppercase hash based on founder_uid + date.

### Referral Message

```
🎉 Did Vance help?

Invite another Dubai founder hiring tech talent.
They get faster matching. You get priority intros.

{referral_url}
```

## Usage

### Automatic Triggers

The referral prompt is automatically sent when:
- Profiles are sent to founders (post-call workflow)
- Candidates are marked for interview
- Hires are marked as successful

### Manual Tool Usage

Founders can also mark hires as successful using the tool:
```
mark_hire_successful(candidate_name="John Doe", role_title="Senior Engineer")
```

This will:
1. Store the hire record
2. Trigger referral prompt
3. Return confirmation message

## Next Steps (TODO)

1. **Referral Link Parsing**: Update WhatsApp router to detect referral codes in initial messages
   - Location: `api/whatsapp_modules/router_v2.py` or similar
   - When user sends first message, check for referral code
   - Call `founder_referral_service.track_referral(referred_uid, referral_code)`

2. **Referral Attribution**: When new founder signs up via referral link:
   - Store referral relationship
   - Increment referrer's `referral_count`
   - Optionally: Give referrer priority in matching (future enhancement)

3. **Analytics**: Track referral metrics:
   - Number of referral prompts sent
   - Number of successful referrals
   - Conversion rate (prompts → signups)
   - Time between prompt and referral

4. **Priority Intros**: Implement priority matching for founders with referrals
   - Could be added to `hybrid_matching_service.py`
   - Boost match scores for founders with `referral_count > 0`

## Testing

To test the referral workflow:

1. **Test trigger 1 (profiles sent)**:
   - Complete a call as a founder
   - Wait for profiles to be sent
   - Check `founder_referral_prompts/{uid}` for sent prompt

2. **Test trigger 2 (interviewing)**:
   - As founder, select candidates for interview
   - Check for referral prompt

3. **Test trigger 3 (hired)**:
   - Use `mark_hire_successful()` tool
   - Check for referral prompt

4. **Test idempotency**:
   - Trigger multiple times
   - Verify only one prompt sent per 7 days

5. **Test referral tracking**:
   - Use referral link to sign up new user
   - Check `referral_relationships/{new_uid}` for attribution

