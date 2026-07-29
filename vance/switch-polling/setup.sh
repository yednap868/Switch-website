#!/bin/bash

# Switch Voice AI Setup Script

echo "🚀 Setting up Switch Voice AI..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please update it with your credentials."
else
    echo "✅ .env file already exists"
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your credentials:"
echo "   - MYOPERATOR_X_API_KEY (already set)"
echo "   - MYOPERATOR_NUMBER (already set)"
echo "   - TWILIO_ACCOUNT_SID (from env_vars.sh)"
echo "   - TWILIO_AUTH_TOKEN (from env_vars.sh)"
echo "   - TWILIO_US_NUMBER (use TWILIO_PHONE_NUMBER from env_vars.sh)"
echo "   - ELEVENLABS_API_KEY (from env_vars.sh)"
echo "   - ELEVENLABS_AGENT_ID (from env_vars.sh)"
echo "   - SERVER_URL (use ngrok for testing)"
echo ""
echo "2. Start ngrok:"
echo "   ngrok http 3000"
echo ""
echo "3. Update SERVER_URL in .env with ngrok URL"
echo ""
echo "4. Start the server:"
echo "   npm start"
echo ""
