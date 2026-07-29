# WhatsApp Template Registration: Profile Ready

## Template Details

**Template Name:** `profile_ready`  
**Category:** UTILITY  
**Language:** English (en)

## Template Content

**Message Body:**
```
Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you.
```

**Parameters:**
1. `{{1}}` - Candidate name (e.g., "John", "Sarah")
2. `{{2}}` - Profile URL (e.g., "https://profiles.vance.so/john-doe")

## Example Message

**With parameters filled:**
```
Hey John, it's Vance. I've just created your profile from our call. https://profiles.vance.so/john-doe This is what I'll share with founders when I introduce you.
```

## Registration Steps

### 1. Access WhatsApp Business Manager
1. Go to [Meta Business Suite](https://business.facebook.com)
2. Navigate to **WhatsApp Manager** → **Message Templates**

### 2. Create New Template
1. Click **"Create Template"** or **"+"** button
2. Select **"UTILITY"** category

### 3. Fill Template Details
- **Template Name:** `profile_ready` (must match exactly)
- **Category:** UTILITY
- **Language:** English

### 4. Add Message Content
- **Message Type:** Text
- **Message Body:** 
  ```
  Hey {{1}}, it's Vance. I've just created your profile from our call. {{2}} This is what I'll share with founders when I introduce you.
  ```

### 5. Add Variables
- Variable 1: `{{1}}` - Text type (for candidate name)
- Variable 2: `{{2}}` - Text type (for profile URL)

### 6. Submit for Approval
- Click **"Submit"**
- Wait for Meta approval (usually 24-48 hours)

### 7. Verify Template Status
- Check the template status in the Message Templates dashboard
- Status should show **"Approved"** before use
- Once approved, the template is ready to use

## Usage in Code

The template is automatically used in `services/post_call_workflow.py` in the `_step_send_profile_to_candidate` method:

```python
payload = MsgComponents.template_scaffold(
    to=wa_id,
    template_name="profile_ready",
    language_code="en",
    body_parameters=[candidate_name, profile_url],
)
```

## Fallback Behavior

- If the template doesn't exist or fails, the system automatically falls back to a regular text message
- This ensures profile links continue to be sent even if the template isn't ready yet

## Important Notes

- Template names are case-sensitive: `profile_ready` must match exactly
- The template will be used for all outbound calls where a profile is created
- Phone numbers are extracted from resumes (if available) or from user profiles
- If a resume phone number is 10 digits, it's automatically prefixed with "91" (India country code)

