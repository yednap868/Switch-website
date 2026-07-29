# Candidate Brag/Share Feature Implementation

## Overview

Implemented a "brag" feature that encourages candidates to share their success stories on social media at key milestone moments. This helps attract more candidates and founders to Vance.

## Trigger Moments

The brag prompt is sent when **any** of these milestones occur:

1. **Candidate receives first founder intro** - Triggered in `notify_candidate_profile_presented()` when profile is first shown
2. **Candidate progresses to interview stage** - Triggered in `notify_candidate_interview_scheduled()` when interview is scheduled
3. **Candidate gets offer** - Triggered via `mark_offer_received()` tool (candidates can call this)
4. **Candidate hired** - Triggered via `mark_hired()` tool (candidates can call this)

## Implementation Details

### Files Created/Modified

1. **`services/candidate_brag_service.py`** (NEW)
   - `CandidateBragService` class with methods:
     - `_generate_share_templates()` - Creates LinkedIn, Twitter/X, and WhatsApp templates
     - `should_send_brag_prompt()` - Idempotency check (one per milestone)
     - `send_brag_prompt()` - Sends celebratory message with share templates

2. **`services/interview_scheduling_service.py`** (MODIFIED)
   - Added brag trigger in `notify_candidate_profile_presented()` for first intro
   - Added brag trigger in `notify_candidate_interview_scheduled()` for interview milestone
   - Tracks intro count to detect first intro

3. **`agent/tools/candidate.py`** (NEW)
   - `mark_offer_received()` - Tool for candidates to mark offers
   - `mark_hired()` - Tool for candidates to mark successful hires

### Firestore Collections

1. **`candidate_brag_prompts/{candidate_uid}`**
   - Tracks which milestones have been sent
   - Stores `milestones_sent` array, timestamps per milestone
   - Prevents duplicate prompts (idempotency)

2. **`candidate_intro_count/{candidate_uid}`**
   - Tracks number of intros received
   - Used to detect first intro for brag trigger

3. **`candidate_offers/{offer_id}`**
   - Stores offer records
   - Links to candidate_uid, company_name, role_title

4. **`candidate_hires/{hire_id}`**
   - Stores hire records
   - Links to candidate_uid, company_name, role_title

### Share Templates

Each milestone generates three share templates:

**LinkedIn Post:**
```
I stopped applying to 200 jobs.

Instead I used Vance — where founders directly messaged me for real opportunities.

Already got interview(s) lined up 🔥

If you're looking for opportunities, just use Vance.

#JobSearch #TechJobs #Vance
```

**Twitter/X Post:**
```
I stopped applying to 200 jobs.

Instead I used Vance — where founders directly messaged me for real opportunities. Already got interview(s) lined up 🔥 If you're looking for opportunities, just use Vance.
```

**WhatsApp Forward:**
```
I stopped applying to 200 jobs.

Instead I used Vance — where founders directly messaged me for real opportunities.

Already got interview(s) lined up 🔥

If you're looking for opportunities, just use Vance.

Try Vance: https://wa.me/12183180007?text=Hi%20Vance%2C%20connect%20with%20me
```

### Celebratory Messages

**First Intro:**
```
🎉 Nice! You just got an intro to a founder via Vance.
Want to share your journey?
```

**Interview:**
```
🎉 Nice! You just got an interview with a founder via Vance.
Want to share your journey?
```

**Offer:**
```
🎉 Amazing! You just got an offer from a founder via Vance!
Want to share your journey?
```

**Hired:**
```
🎉 Congratulations! You just got hired by a founder via Vance!
Want to share your journey?
```

## Usage

### Automatic Triggers

The brag prompt is automatically sent when:
- First intro is received (detected via intro count)
- Interview is scheduled (via `notify_candidate_interview_scheduled()`)

### Manual Tool Usage

Candidates can mark offers and hires using tools:
```
mark_offer_received(company_name="Tech Corp", role_title="Senior Engineer")
mark_hired(company_name="Tech Corp", role_title="Senior Engineer")
```

## Testing

Run the test script:
```bash
uv run python scripts/test_candidate_brag.py
```

Test results:
- ✅ Share templates generated correctly for all milestones
- ✅ Idempotency check working (one prompt per milestone)
- ✅ All milestones tracked separately
- ✅ Message formatting correct (no "Dubai" in messages)

## Next Steps

1. **Integrate tools into agent**: Add `CANDIDATE_TOOLS` to agent's tool list so candidates can use `mark_offer_received()` and `mark_hired()`
2. **Analytics**: Track brag prompt metrics:
   - Number of prompts sent per milestone
   - Share template usage (if we can track)
   - Conversion from prompt to actual shares
3. **A/B Testing**: Test different message variations and share templates
4. **Location personalization**: Optionally add location back if needed (currently removed per request)

