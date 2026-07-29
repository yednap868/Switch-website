# Firebase SMS OTP Setup Guide

## Overview

The system now uses **Firebase Authentication** to send OTP via SMS. This is the recommended approach as it:
- Works for all users (no 24-hour window limitation)
- No template registration required
- Reliable SMS delivery
- Built-in rate limiting and security

## Required Setup

### 1. Enable Phone Authentication in Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (`relay-15824`)
3. Navigate to **Authentication** → **Sign-in method**
4. Enable **Phone** sign-in provider
5. Configure allowed phone number regions (or leave default for all regions)

### 2. Get Firebase API Key

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Scroll to **Your apps** section
3. If you have a Web app, copy the **API Key**
4. If no Web app exists:
   - Click **Add app** → **Web** (</> icon)
   - Register app (name it "Vance API" or similar)
   - Copy the **API Key** from the config

### 3. Set Environment Variable

Add to your environment variables:
```bash
export FIREBASE_API_KEY="your-api-key-here"
export FIREBASE_PROJECT_ID="relay-15824"  # Optional, defaults to relay-15824
```

Or in your deployment environment:
- Add `FIREBASE_API_KEY` to your environment variables
- The API key is safe to expose (it's public, protected by domain restrictions)

### 4. Configure Firebase API Restrictions (Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Find your API key
4. Click **Edit** → **Application restrictions**
5. Set to **HTTP referrers (web sites)**
6. Add your domain: `https://api.relayy.world/*`
7. Save

## How It Works

1. **User requests OTP**: Frontend calls `/api/candidate-onboarding/signup`
2. **Backend sends SMS**: Uses Firebase Auth REST API to send verification code
3. **Firebase sends SMS**: Automatically sends SMS with 6-digit code
4. **User enters OTP**: Frontend sends OTP to `/api/candidate-onboarding/verify-otp`
5. **Backend verifies**: Uses Firebase Auth API to verify the code
6. **User created**: On success, user is created in Firestore

## Code Flow

### Signup Endpoint
- Calls Firebase Auth `sendVerificationCode` API
- Stores `sessionInfo` in Firestore
- Returns success (OTP sent via SMS)

### Verify Endpoint
- Retrieves `sessionInfo` from Firestore
- Calls Firebase Auth `verifyPhoneNumber` API
- On success, creates user and returns session token

## Fallback Behavior

If Firebase Auth fails:
- Falls back to stored OTP verification (manual verification)
- OTP is still stored in Firestore
- User can verify using the stored OTP code

## Testing

1. **Test Phone Numbers**: Firebase allows test phone numbers that don't send real SMS
   - Add test numbers in Firebase Console → Authentication → Sign-in method → Phone → Test phone numbers
   - Format: `+1234567890` with code `123456`

2. **Real Phone Numbers**: Will receive actual SMS with verification code

## Troubleshooting

**Error: "API key not valid"**
- Check `FIREBASE_API_KEY` is set correctly
- Verify API key restrictions allow your domain

**Error: "Phone number format invalid"**
- Phone must be in E.164 format: `+[country code][number]`
- Example: `+919876543210` (not `919876543210`)

**Error: "SMS not received"**
- Check Firebase Console → Authentication → Sign-in method → Phone is enabled
- Verify phone number region is allowed
- Check Firebase quotas/limits
- For test numbers, use the test code from Firebase Console

**Error: "reCAPTCHA required"**
- Firebase Auth REST API may require reCAPTCHA for web clients
- For server-side, this should be handled automatically
- If issues persist, consider using Firebase Admin SDK or Twilio

## Alternative: Using Twilio for SMS

If Firebase Auth doesn't work, you can integrate Twilio:
1. Sign up for Twilio account
2. Get API credentials
3. Install `twilio` package
4. Update code to use Twilio SMS API

## Current Implementation

- ✅ Uses Firebase Auth REST API
- ✅ Sends SMS automatically
- ✅ Verifies OTP via Firebase
- ✅ Falls back to stored OTP if Firebase fails
- ✅ Stores session info in Firestore

