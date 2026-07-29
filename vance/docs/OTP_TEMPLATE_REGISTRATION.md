# WhatsApp OTP Template Registration (Optional)

## Note: Currently Using Plain Text Messages

The system currently uses **plain text messages** for OTP delivery, which works perfectly within the 24-hour messaging window. Templates are optional and only needed if you want to send OTPs outside the 24-hour window.

**Current Implementation:** Plain text messages (no template required)

## Template Details (Optional - For Future Use)

**Template Name:** `vance_otp`  
**Category:** UTILITY (requires app ID/hash - not recommended)  
**Language:** English (en)

**Note:** Meta requires app ID and hash for template registration, which requires a mobile app setup. Since we don't have a mobile app, we use plain text messages instead.

## Template Content

```
Your Vance verification code is: {{1}}

This code will expire in 5 minutes.
```

**Parameters:**
- `{{1}}` = OTP code (6 digits, e.g., "123456")

## Step-by-Step Registration Instructions

### 1. Access Meta Business Manager
1. Go to [Meta Business Manager](https://business.facebook.com/)
2. Select your WhatsApp Business Account
3. Navigate to **WhatsApp Manager** → **Message Templates**

### 2. Create New Template
1. Click **"Create Template"** or **"+"** button
2. Select **Category:** **UTILITY** (required for transactional messages like OTP)

### 3. Fill Template Details
- **Template Name:** `vance_otp`
  - ⚠️ **Must match exactly** - this is case-sensitive
- **Language:** English (en)
- **Template Type:** Text

### 4. Add Message Body
Paste this exact text:
```
Your Vance verification code is: {{1}}

This code will expire in 5 minutes.
```

**Important:**
- Use `{{1}}` exactly as shown (double curly braces)
- Keep the line break between the two sentences
- The period at the end is important

### 5. Add Parameters
1. Click on the parameter placeholder (`{{1}}`)
2. For the parameter:
   - **Parameter Name:** Leave as "1" or name it "otp_code"
   - **Parameter Type:** Text
   - **Example Value:** "123456"

### 6. Submit for Review
1. Review all details
2. Click **"Submit"** or **"Send for Approval"**
3. Wait for Meta's approval (usually 24-48 hours for UTILITY templates)

### 7. Verify Template Status
- Check the template status in the Message Templates dashboard
- Status should be **"Approved"** before it can be used
- Once approved, the code will automatically use the template

## Fallback Behavior

If the template is not registered or fails to send, the code will automatically fallback to sending a plain text message. This ensures OTP delivery even if the template is not yet approved.

## Testing

After template is approved, test by:
1. Requesting an OTP from the onboarding flow
2. Verify the message is received via template (not plain text)
3. Check server logs for "OTP sent via template" message

