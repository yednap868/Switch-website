# 🤖 Vance Admin Dashboard

A web-based admin interface for manually sending curated profiles to users via WhatsApp.

## 🚀 Quick Start

### 1. Start the Dashboard
```bash
# From your project root directory
./start_admin.sh
```

### 2. Access the Dashboard
Open your browser and go to:
```
http://localhost:5001/admin
```

### 3. Login
- **Username:** `admin`
- **Password:** `vance2024`

## 📋 Features

### ✅ Authentication
- Simple login/password protection
- Session management
- Secure logout

### ✅ Profile Sending
- Send 1 or multiple profiles to any user
- Real-time WhatsApp integration
- Same message format as your existing system
- Automatic state management

### ✅ Firebase Integration
- Stores profiles in same format as existing system
- Compatible with your email workflow
- Tracks manual vs automated profiles

### ✅ User Management
- Search existing user profiles
- View profile history
- Track sending statistics

## 🔧 How It Works

### 1. Send Profiles
1. Enter user's WhatsApp number (without + or spaces)
2. Fill in profile details:
   - **Name** (required)
   - **Email** (optional)
   - **LinkedIn URL** (required)
   - **Summary** (required)
   - **Match Reason** (optional)
3. Add multiple profiles if needed
4. Click "Send Profiles"

### 2. User Receives Profiles
- User gets formatted WhatsApp messages
- Same format as your existing profile suggestions
- User state automatically set to `"profiles_suggested"`

### 3. Email Workflow Activates
- When user replies "I want to connect with John"
- Your existing email workflow takes over
- Consent → Details collection → Email sending
- Uses your existing templates and logic

## 🔐 Security

### Change Default Credentials
Set environment variables:
```bash
export ADMIN_USERNAME="your_username"
export ADMIN_PASSWORD="your_secure_password"
```

Or modify the `start_admin.sh` script.

### Production Deployment
For production use:
1. Use a reverse proxy (nginx)
2. Enable HTTPS
3. Use strong passwords
4. Consider IP restrictions

## 📊 Firebase Storage Format

Profiles are stored in Firestore exactly like your existing system:

```json
{
  "suggested_profiles": {
    "user_phone_number": {
      "profiles": [
        {
          "uid": "manual_1698123456_0",
          "name": "John Smith",
          "email": "john@company.com",
          "profile_summary": "Senior Product Manager...",
          "linkedin_url": "https://linkedin.com/in/johnsmith",
          "match_reason": "Perfect fit because...",
          "source": "manual_admin",
          "suggested_at": 1698123456.789
        }
      ],
      "created_at": 1698123456.789,
      "source": "manual_admin"
    }
  }
}
```

## 🔄 Integration with Existing System

### WhatsApp Messages
- Uses your existing `WhatsAppSender` class
- Uses your existing `MsgComponents.text_scaffold()`
- Same message formatting as automated suggestions

### State Management
- Uses your existing `state_manager`
- Sets user state to `"profiles_suggested"`
- Compatible with your router logic

### Email Workflow
- Works with your existing `EmailWorkflow` class
- Uses your existing email templates
- Same consent and details collection flow

## 🛠 Troubleshooting

### Dashboard Won't Start
```bash
# Make sure you're in the project root
cd /path/to/your/project

# Check if virtual environment exists
ls venv/

# Install Flask if needed
pip install Flask

# Run directly
python admin_dashboard.py
```

### WhatsApp Messages Not Sending
1. Check your environment variables:
   - `PHONE_NUMBER_ID`
   - `META_SYS_USER_TOKEN`
2. Verify phone number format (no + or spaces)
3. Check console logs for error messages

### Firebase Errors
1. Ensure Firebase credentials are properly configured
2. Check if `utils.db.fs` is accessible
3. Verify Firestore permissions

## 📱 Usage Examples

### Single Profile
```
User Phone: 1234567890
Name: Sarah Johnson
LinkedIn: https://linkedin.com/in/sarahjohnson
Summary: VP of Engineering at Stripe with 10+ years leading high-performance teams...
Match Reason: Perfect for your scaling challenges and has experience with fintech products.
```

### Multiple Profiles
Add multiple profiles for the same user to give them options.

## 🔗 URLs

- **Login:** `http://localhost:5001/login`
- **Dashboard:** `http://localhost:5001/admin`
- **API Endpoint:** `http://localhost:5001/send-profile` (POST)
- **User Search:** `http://localhost:5001/get-user-profiles/<phone>`

## 📞 Support

The admin dashboard integrates seamlessly with your existing Vance system. All profiles sent through this interface will work with your existing email introduction workflow.

For issues, check the console logs in both the admin dashboard and your main application.
