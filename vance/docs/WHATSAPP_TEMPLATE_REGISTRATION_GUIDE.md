# WhatsApp Template Registration Guide (REQUIRED for OTP)

## ⚠️ IMPORTANT: Templates are REQUIRED for New Users

Meta WhatsApp Business API **requires** template messages for new users (users who haven't messaged you in the last 24 hours). Plain text messages will **NOT work** for new users.

## Solution: Register Authentication Template

You need to register an **AUTHENTICATION** category template (not UTILITY). Authentication templates don't require app ID/hash.

## Step-by-Step: Register Authentication Template

### 1. Access Meta Business Manager
1. Go to [Meta Business Manager](https://business.facebook.com/)
2. Select your WhatsApp Business Account
3. Navigate to **WhatsApp Manager** → **Message Templates**

### 2. Create New Template
1. Click **"Create Template"** or **"+"** button
2. **IMPORTANT:** Select **Category: AUTHENTICATION** (not UTILITY)
   - Authentication category is specifically for OTP/verification codes
   - Does NOT require app ID or hash
   - Faster approval (usually within hours)

### 3. Fill Template Details
- **Template Name:** `vance_otp`
  - ⚠️ **Must match exactly** - case-sensitive
- **Language:** English (en)
- **Template Type:** Text

### 4. Add Message Body
Paste this exact text:
```
Your Vance verification code is: {{1}}

This code will expire in 5 minutes.
```

**Template Rules:**
- Use `{{1}}` exactly (double curly braces)
- No URLs allowed
- No emojis allowed
- Keep it simple and clear
- Line break between sentences is fine

### 5. Add Parameters
1. Click on `{{1}}` placeholder
2. Configure parameter:
   - **Parameter Type:** Text
   - **Example Value:** "123456"
   - **Character Limit:** 6 (for OTP)

### 6. Submit for Review
1. Review all details
2. Click **"Submit"** or **"Send for Approval"**
3. Wait for approval (usually 2-24 hours for AUTHENTICATION category)

### 7. Verify Template Status
- Check status in Message Templates dashboard
- Status must be **"Approved"** before use
- Once approved, the code will automatically use it

## Alternative: Use UTILITY Category (If Available)

If AUTHENTICATION category is not available in your account:

1. Try **UTILITY** category
2. Some accounts may need business verification first
3. If Meta still asks for app ID, you may need to:
   - Complete business verification
   - Or use a Business Solution Provider (BSP) like Twilio

## Current Code Behavior

The code will:
1. **Try template first** (`vance_otp`)
2. **Fallback to plain text** if template fails (only works if user messaged recently)
3. **Store OTP in Firestore** regardless (user can verify manually if needed)

## Testing After Template Approval

1. Request OTP from onboarding flow
2. Check server logs for "OTP sent via template"
3. Verify message received on WhatsApp
4. If template fails, check error message in logs

## Troubleshooting

**Error: "Template not found"**
- Template not registered or not approved
- Check template name matches exactly: `vance_otp`
- Verify template status is "Approved"

**Error: "Template requires app ID"**
- You're trying UTILITY category
- Switch to AUTHENTICATION category instead
- Authentication doesn't require app ID

**Error: "Cannot send to new user"**
- Template not registered/approved
- Register AUTHENTICATION template as above
- Plain text won't work for new users

## Next Steps

1. Register `vance_otp` template in AUTHENTICATION category
2. Wait for approval (2-24 hours)
3. Test OTP sending
4. Code will automatically use template once approved

