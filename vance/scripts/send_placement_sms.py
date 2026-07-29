"""
Send a placement confirmation SMS to a worker.
Usage:
  python3 scripts/send_placement_sms.py --phone 917078827869 --name "Shivam Gola" --role "ITI Fitter" --date "16 March 2026"
"""
import os, argparse
from twilio.rest import Client

def get_twilio_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        with open("/Users/alt/Vance-1/env_vars.sh") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export TWILIO_ACCOUNT_SID"):
                    sid = line.split("=", 1)[1].strip().strip('"').strip("'")
                if line.startswith("export TWILIO_AUTH_TOKEN"):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "+15625260001")
    return Client(sid, token), from_number


PLACEMENT_SMS = """🎉 बधाई हो {first_name}!

आपकी *{role}* नौकरी पक्की हो गई।
Joining: {date}

App खोलो — सारी details और confirm button वहाँ है:
https://app.switchlocally.com

— Switch Team"""


def send_placement_sms(phone: str, name: str, role: str, date: str, dry_run: bool = False):
    first_name = name.split()[0] if name else "भाई"
    to = "+" + phone.strip().lstrip("+").replace(" ", "").replace("-", "")
    if not to[1:].startswith("91"):
        to = "+91" + to[1:]
    body = PLACEMENT_SMS.format(first_name=first_name, role=role, date=date)

    if dry_run:
        print(f"[DRY RUN] → {to}\n{body}")
        return

    client, from_number = get_twilio_client()
    msg = client.messages.create(body=body, from_=from_number, to=to)
    print(f"✅ Sent to {phone} — SID: {msg.sid}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--role", default="ITI Fitter")
    parser.add_argument("--date", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    send_placement_sms(args.phone, args.name, args.role, args.date, args.dry_run)
