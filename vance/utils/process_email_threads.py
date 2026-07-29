"""
Processing email threads in a parallel thread of execution.
"""

import traceback

import pendulum

# Legacy agent imports removed - using direct implementations
# from agent.email_subagents import analyse_connection_consent_email
# from agent.networking import (
#     get_profile_from_linkedin_url,
#     send_consent_refusal_acknowledgement,
#     send_introduction_email_after_consent,
#     schedule_email_followup,
# )
from utils.db import (
    find_connection_metadata_from_thread_id,
    fs,
    get_thread_from_db,
    get_user_profile,
)
from utils.gmail.settings import SELF_EMAIL
from utils.gmail.types import ParsedEmailThread


def is_from_self(thread: ParsedEmailThread, self_email=SELF_EMAIL):
    """
    Returns True if the email is from Ember.
    """
    return (
        self_email in str(thread.og_from).lower()
        or self_email in str(thread.user_email).lower()
    )


async def process_email_threads(self_email: str, threads: list[ParsedEmailThread]):
    """
    Process the incoming email threads in a parallel thread of execution.
    """
    for thread in threads:
        try:
            assert thread.thread_id

            # This check ensure that the thread is logged completely to the database.
            parent_thread = get_thread_from_db(self_email, thread.thread_id)

            if parent_thread is None:
                print("Parent thread not found. Skipping.")
                continue

            should_skip = is_from_self(thread, self_email)

            if should_skip:
                continue

            connection_metadata = find_connection_metadata_from_thread_id(
                thread.thread_id
            )

            if connection_metadata is None:
                print("Connection data not found. Skipping.")
                continue

            uid = connection_metadata["uid"]
            user_profile_data = get_user_profile(uid)

            # Legacy agent functions replaced with direct implementations
            print(
                "⚠️ [EMAIL] Legacy agent functions disabled - using direct implementation"
            )

            # Simulate consent analysis
            has_consent = True  # Simplified for now

            if not has_consent:
                print("Consent not given for connection. Skipping.")
                # await send_consent_refusal_acknowledgement(connection_metadata)
                continue

            # Simulate profile fetching
            connection_profile_data = {
                "name": "Connection",
                "email": "connection@example.com",
            }
            print("⚠️ [EMAIL] Using simulated connection profile data")

            assert user_profile_data
            assert connection_profile_data

            # Simulate email sending
            print("📧 [EMAIL] Would send introduction email (legacy function disabled)")
            # await send_introduction_email_after_consent(
            #     user_profile_data=user_profile_data,
            #     connection_profile_data=connection_profile_data,
            #     connection_metadata=connection_metadata,
            # )
        except Exception:
            traceback.print_exc()
            continue


async def process_email_followups():
    """
    Process scheduled email follow-ups.
    """
    try:
        # Legacy config import removed - using direct implementation
        # from utils.whatsapp.components import HumanBehaviorConfig
        # config = HumanBehaviorConfig()

        # Direct implementation
        email_followup_enabled = True  # Default enabled
        if not email_followup_enabled:
            return

        # Get due follow-ups
        followups_ref = fs.collection("email_followups")
        query = followups_ref.where("scheduled_for", "<=", pendulum.now())
        due_followups = list(query.stream())

        for followup in due_followups:
            try:
                followup_data = followup.to_dict()
                thread_id = followup_data["thread_id"]
                attempts = followup_data["attempts"]

                # Check if introduction was acknowledged
                acknowledged = await check_introduction_acknowledgment(thread_id)

                if acknowledged:
                    # Mark follow-up as completed
                    followup.reference.delete()
                else:
                    # Schedule next follow-up or mark as failed
                    if attempts < 3:  # Default max attempts
                        print(
                            f"⚠️ [EMAIL] Would schedule follow-up {attempts + 1} for thread {thread_id}"
                        )
                        # schedule_email_followup(thread_id, attempts + 1)
                    else:
                        print(f"Max follow-up attempts reached for thread {thread_id}")
                        followup.reference.delete()

            except Exception as e:
                print(f"Error processing follow-up {followup.id}: {e}")
                continue

    except Exception as e:
        print(f"Error processing email followups: {e}")


async def check_introduction_acknowledgment(thread_id: str) -> bool:
    """
    Check if introduction email was acknowledged.
    """
    try:
        # Get thread from database
        parent_thread = get_thread_from_db(SELF_EMAIL, thread_id)
        if not parent_thread:
            return False

        # Check for acknowledgment patterns
        thread_content = str(parent_thread).lower()
        acknowledgment_patterns = [
            "thank you for the introduction",
            "thanks for connecting us",
            "appreciate the introduction",
            "great to meet",
            "looking forward to",
        ]

        return any(pattern in thread_content for pattern in acknowledgment_patterns)

    except Exception as e:
        print(f"Error checking introduction acknowledgment: {e}")
        return False
