"""
Validate Switch environment configuration.
Checks that all required environment variables are set from env_vars.sh
"""

import os
import sys
from pathlib import Path


def load_env_vars():
    """Load environment variables from env_vars.sh"""
    env_file = Path(__file__).parent.parent / "env_vars.sh"
    
    if not env_file.exists():
        print(f"❌ env_vars.sh not found at {env_file}")
        return False
    
    # Read and parse env_vars.sh
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse export statements
            if line.startswith('export '):
                line = line[7:]  # Remove 'export '
            
            # Parse variable assignments
            if '=' in line:
                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                # Set environment variable
                os.environ[key] = value
    
    return True


def validate_switch_config():
    """Validate all required Switch environment variables."""
    print("=" * 70)
    print("Switch Configuration Validation")
    print("=" * 70)
    print()
    
    # Load env vars
    print("📂 Loading environment variables from env_vars.sh...")
    if not load_env_vars():
        return 1
    print("✅ Environment variables loaded\n")
    
    # Required variables for Switch
    required_vars = {
        "ELEVENLABS_API_KEY": "ElevenLabs API key for voice calls",
        "ELEVENLABS_AGENT_ID": "ElevenLabs agent ID for AI conversations",
        "ELEVENLABS_PHONE_NUMBER_ID": "ElevenLabs phone number ID for outbound calls",
        "TWILIO_ACCOUNT_SID": "Twilio account SID for SMS/voice",
        "TWILIO_AUTH_TOKEN": "Twilio auth token",
        "TWILIO_PHONE_NUMBER": "Twilio phone number (E.164 format)",
        "ANTHROPIC_API_KEY": "Anthropic Claude API key for AI extraction",
        "PHONE_NUMBER_ID": "WhatsApp Business phone number ID",
        "META_SYS_USER_TOKEN": "Meta system user token for WhatsApp API",
    }
    
    # Optional but recommended
    optional_vars = {
        "GOOGLE_APPLICATION_CREDENTIALS": "Firebase credentials path",
        "FIREBASE_PROJECT_ID": "Firebase project ID",
        "QDRANT_API_KEY": "Qdrant vector DB API key",
        "QDRANT_BASE_URL": "Qdrant base URL",
    }
    
    results = {
        "required": {"passed": 0, "failed": []},
        "optional": {"passed": 0, "failed": []}
    }
    
    # Check required variables
    print("🔍 Checking Required Variables")
    print("-" * 70)
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values
            if "KEY" in var_name or "TOKEN" in var_name or "SECRET" in var_name:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  ✅ {var_name:30} = {masked:20} ({description})")
            else:
                print(f"  ✅ {var_name:30} = {value:20} ({description})")
            results["required"]["passed"] += 1
        else:
            print(f"  ❌ {var_name:30} = NOT SET          ({description})")
            results["required"]["failed"].append(var_name)
    
    print()
    
    # Check optional variables
    print("🔍 Checking Optional Variables")
    print("-" * 70)
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            if "KEY" in var_name or "TOKEN" in var_name:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  ✅ {var_name:30} = {masked:20} ({description})")
            else:
                print(f"  ✅ {var_name:30} = {value:20} ({description})")
            results["optional"]["passed"] += 1
        else:
            print(f"  ⚠️  {var_name:30} = NOT SET          ({description})")
            results["optional"]["failed"].append(var_name)
    
    # Summary
    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Required Variables: {results['required']['passed']}/{len(required_vars)} ✅")
    if results["required"]["failed"]:
        print(f"  ❌ Missing: {', '.join(results['required']['failed'])}")
    print(f"Optional Variables: {results['optional']['passed']}/{len(optional_vars)} ✅")
    print()
    
    if results["required"]["failed"]:
        print("❌ Configuration incomplete!")
        print("\nPlease ensure all required variables are set in env_vars.sh")
        return 1
    else:
        print("✅ All required variables are configured!")
        print("\nSwitch is ready to use. Make sure to source env_vars.sh before running:")
        print("  source env_vars.sh")
        print("  ./run.sh")
        return 0


if __name__ == "__main__":
    sys.exit(validate_switch_config())
