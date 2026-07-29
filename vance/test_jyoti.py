"""
Local Jyoti test — no server, no DB needed.
Usage: python test_jyoti.py
"""

import os
import sys

# Load env vars from env_vars.sh
env_file = os.path.join(os.path.dirname(__file__), "env_vars.sh")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                key, _, val = line[7:].partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"'))

import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY not set. Check env_vars.sh")
    sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """Aap Jyoti hain — Switch platform ki AI assistant. Aap ek professional aur caring helper hain jo workers ki poori madad karti hain.

Aapka kaam:
- Har sawaal ka clear jawab dena — jobs, salary, documents, interview, joining process
- Jobs dhundne mein madad karna
- App use karne mein guide karna: app.switchlocally.com
- OTP, check-in, joining date — sab clearly explain karna

Baat karne ka tarika:
- Hindi aur Hinglish mix — respectful aur clear
- Short aur focused replies — 2-4 lines max
- Thoda emoji use karo jab natural lage
- Hamesha polite aur patient raho

Sirf Switch aur worker ki job life se related cheezein discuss karo."""

history = []

print("Jyoti Local Test — type 'quit' to exit\n")
print("=" * 50)

while True:
    try:
        user_input = input("\nYou: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nBye!")
        break

    if user_input.lower() in ("quit", "exit", "q"):
        break
    if not user_input:
        continue

    history.append({"role": "user", "content": user_input})

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM,
            messages=history,
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        print(f"\nJyoti: {reply}")
    except Exception as e:
        print(f"\nERROR: {e}")
