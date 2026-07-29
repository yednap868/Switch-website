# Profile Link Sending Check

## ✅ Current Implementation Status

The code **IS configured** to send profile links to candidates after their first call ends. Here's the flow:

### Flow:
1. **Post-call webhook received** → `api/webhooks.py::_handle_post_call_webhook()`
2. **Workflow runs** → `PostCallWorkflow().run(payload)` which includes:
   - Step 3: `save_call_memory` → increments `total_calls` in `user_call_summaries/{uid}`
3. **After workflow completes** → `_send_profile_link_to_candidate(uid)` is called
4. **Checks performed**:
   - ✅ User type must be `"job_seeker"` or `"candidate"` (from `users/{uid}.profile.user_type`)
   - ✅ `total_calls == 1` (first call just completed)
   - ✅ Not already sent (idempotency check via `post_call_profile_links/{uid}`)
   - ✅ Profile exists with slug (`user_profiles/{uid}`)
   - ✅ WhatsApp ID exists
5. **Sends message** via WhatsApp with profile URL

### Code Locations:
- **Main handler**: `api/webhooks.py::_send_profile_link_to_candidate()` (lines 24-134)
- **Webhook entry**: `api/webhooks.py::_handle_post_call_webhook()` (lines 137-198)
- **Call count update**: `api/whatsapp_modules/call_memory.py::_update_user_call_summary()` (lines 142-200)

## ⚠️ Potential Issues to Check

### 1. **WhatsApp Token Issue** (JUST FIXED)
- **Status**: ✅ Fixed in `env_vars.sh`
- **Action**: Make sure prod server has the new token and is restarted

### 2. **User Type Not Set**
- **Check**: `users/{uid}.profile.user_type` must be `"job_seeker"` or `"candidate"`
- **If missing**: Profile link won't be sent
- **Log message**: `"Skipping - user_type is '{user_type}' (not job_seeker/candidate)"`

### 3. **Call Count Not Incremented**
- **Check**: `user_call_summaries/{uid}.total_calls` should be `1` after first call
- **If 0 or missing**: Profile link won't be sent (unless doc doesn't exist, then it assumes first call)
- **Log message**: `"Not first call, skipping"`

### 4. **Profile/Slug Missing**
- **Check**: `user_profiles/{uid}` must exist with a `slug` field
- **If missing**: Profile link won't be sent
- **Log message**: `"No user_profiles document for {uid}"`

### 5. **WhatsApp ID Missing**
- **Check**: `user_profiles/{uid}` must have `whatsapp`, `phone`, `phone_number`, or `whatsapp_number` field
- **If missing**: Profile link won't be sent
- **Log message**: `"No WhatsApp ID found for {uid}"`

### 6. **Already Sent (Idempotency)**
- **Check**: `post_call_profile_links/{uid}` document exists
- **If exists**: Won't send again (idempotency)
- **Log message**: `"Already sent profile link to {uid}"`

## 🔍 How to Debug

### Check if profile link was sent:
```python
# In Firestore console or script
doc = fs.collection("post_call_profile_links").document(uid).get()
if doc.exists:
    print(f"Sent: {doc.to_dict()}")
else:
    print("Not sent yet")
```

### Check call count:
```python
doc = fs.collection("user_call_summaries").document(uid).get()
if doc.exists:
    print(f"Total calls: {doc.to_dict().get('total_calls', 0)}")
```

### Check user type:
```python
profile = get_user_profile(uid)
user_type = profile.get("profile", {}).get("user_type", "general")
print(f"User type: {user_type}")
```

### Check logs for specific UID:
Look for these log messages in your server logs:
- `📤 [PROFILE_LINK] Checking if profile link should be sent to {uid}`
- `🔍 [PROFILE_LINK] Call count check: total_calls={n}, is_first_call={bool}`
- `✅ [PROFILE_LINK] Profile link sent to {uid} at {wa_id} (first call)`
- `❌ [PROFILE_LINK] Failed to send: {error}`

## 🚀 Next Steps

1. **Verify WhatsApp token is live in prod** (restart server after updating `env_vars.sh`)
2. **Test with a new candidate** - complete first call and check logs
3. **Check Firestore** - verify `post_call_profile_links/{uid}` document is created
4. **Monitor logs** - look for the log messages above to identify any failures

