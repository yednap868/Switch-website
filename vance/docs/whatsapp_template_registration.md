# WhatsApp Template Registration for Onboarding Broadcast

## Template Details

**Template Name:** `onboarding_broadcast`  
**Category:** UTILITY (or MARKETING if you prefer)  
**Language:** English (en)

## Template Content

```
I just spoke with {{1}} — they're looking to connect with {{2}}.
Need an intro?
```

**Parameters:**
- `{{1}}` = User's name (e.g., "John Doe")
- `{{2}}` = Connection type/goal (e.g., "software engineers", "founders")

## Step-by-Step Registration Instructions

### 1. Access Meta Business Manager
1. Go to [Meta Business Manager](https://business.facebook.com/)
2. Select your WhatsApp Business Account
3. Navigate to **WhatsApp Manager** → **Message Templates**

### 2. Create New Template
1. Click **"Create Template"** or **"+"** button
2. Select **Category:**
   - **UTILITY** (recommended for transactional messages)
   - OR **MARKETING** (if you prefer, but may have stricter approval)

### 3. Fill Template Details
- **Template Name:** `onboarding_broadcast`
  - ⚠️ **Must match exactly** - this is case-sensitive
- **Language:** English (en)
- **Template Type:** Text

### 4. Add Message Body
Paste this exact text:
```
I just spoke with {{1}} — they're looking to connect with {{2}}.
Need an intro?
```

**Important:**
- Use `{{1}}` and `{{2}}` exactly as shown (double curly braces)
- Keep the line break between the two sentences
- The question mark at the end is important

### 5. Add Parameters
1. Click on the parameter placeholders (`{{1}}` and `{{2}}`)
2. For each parameter:
   - **Parameter Name:** 
     - `{{1}}` → Name it "name" or leave as "1"
     - `{{2}}` → Name it "connection_type" or leave as "2"
   - **Parameter Type:** Text
   - **Example Value:**
     - `{{1}}` → "John Doe"
     - `{{2}}` → "software engineers"

### 6. Submit for Review
1. Review all details
2. Click **"Submit"** or **"Send for Approval"**
3. Wait for Meta's approval (usually 24-48 hours)

### 7. Verify Template Status
- Check the template status in the Message Templates dashboard
- Status should show **"Approved"** before it can be used
- Once approved, the template is ready to use

## Testing the Template

Once approved, you can test it by:
1. Using the admin panel's template message sender (if available)
2. Or wait for the first broadcast that triggers after 24 hours

## Fallback Behavior

The code includes a fallback:
- If the template doesn't exist or fails, it will automatically fall back to a regular text message
- This ensures broadcasts continue to work even if the template isn't ready yet

## Notes

- Template names are case-sensitive: `onboarding_broadcast` must match exactly
- The template will only be used for broadcasts sent **more than 24 hours** after onboarding
- Within 24 hours, regular text messages are used (no template needed)
- Make sure your WhatsApp Business Account has permission to send template messages

