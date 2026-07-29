import dataclasses
import hashlib
import traceback

import pendulum
from google.api_core import exceptions as google_exceptions
from google.cloud import firestore
from google.cloud.firestore_v1.transaction import Transaction
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils.gmail.settings import Collections
from utils.gmail.types import ParsedEmailThread


def get_encoded_message_id(message_id: str):
    """
    Generate a unique hash for storing email messages.
    """
    print(f"Encoding message ID: {message_id}")
    encoded_message_id = hashlib.sha256(message_id.encode())
    result = encoded_message_id.hexdigest()
    print(f"Encoded result: {result}")
    return result


def log_email_threads(assistant_email: str, threads: list[ParsedEmailThread]):
    """
    Log scheduling-related threads to firestore in the threads collection.
    """
    for thread in threads:
        log_thread(assistant_email, thread, Collections.THREADS.value)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)
    ),
)
def log_thread(assistant_email: str, thread: ParsedEmailThread, collection_name: str):
    """
    Writes a thread to the specified firestore collection
    for later processing or moderator approval.
    """
    print(f"Attempting to log thread to {collection_name}")

    try:
        from utils.firebase_init import fs as db
        threads_ref = (
            db.collection(Collections.EMAILS.value)
            .document(assistant_email)
            .collection(collection_name)
        )

        @firestore.transactional
        def log_thread_transaction(transaction: Transaction):
            assert thread.thread_id is not None
            thread_doc = threads_ref.document(thread.thread_id).get(
                transaction=transaction
            )
            message_id = get_encoded_message_id(thread.thread_id)

            if thread_doc.exists:
                print(f"Updating existing thread: {thread.thread_id}")
                update_existing_thread(transaction, thread_doc, thread, message_id)
            else:
                print(f"Creating new thread: {thread.thread_id}")
                create_new_thread(transaction, threads_ref, thread, assistant_email)

            return True

        transaction = db.transaction()
        success = log_thread_transaction(transaction)

        if success:
            print(
                f"Successfully logged thread to {collection_name}: {thread.thread_id}"
            )
            return True
        else:
            print(f"Failed to log thread to {collection_name}: {thread.thread_id}")
            return False
    except Exception:
        traceback.print_exc()


def update_existing_thread(transaction: Transaction, thread_doc, thread, message_id):
    """
    Update an existing thread in the database.
    """
    thread_data = thread_doc.to_dict()
    thread_started_by = thread_data.get("thread", {}).get("thread_started_by")

    print(f"Updating existing thread {thread.thread_id}")
    print(f"Original message ID: {thread.message_id}")
    print(f"Thread has {len(thread.replies)} replies")

    # Check existing replies
    existing_replies = list(thread_doc.reference.collection("replies").get())
    print(f"Found {len(existing_replies)} existing replies in database")

    # Use the actual message's ID for encoding, not the thread ID
    message_id = get_encoded_message_id(thread.message_id)
    print(f"Using message-specific encoded ID: {message_id}")

    reply_doc_ref = thread_doc.reference.collection("replies").document(message_id)
    thread.thread_started_by = thread_started_by

    transaction.set(reply_doc_ref, dataclasses.asdict(thread), merge=True)
    transaction.update(
        thread_doc.reference,
        {
            "updated_at": pendulum.now(),
        },
    )


def sanitize_email(email):
    if "<" in email and ">" in email:
        return email.split("<")[1].split(">")[0].strip()
    return email


def create_new_thread(transaction: Transaction, threads_ref, thread, self_email):
    """
    Create data for a new thread in the database.
    """
    email = sanitize_email(str(thread.og_from))

    thread.thread_started_by = email
    new_thread_data = {
        "self_email": self_email,
        "user_email": email,
        "thread": dataclasses.asdict(thread),
        "ts": pendulum.now(),
        "response": "",
        "updated_at": pendulum.now(),
    }
    transaction.set(threads_ref.document(thread.thread_id), new_thread_data)
