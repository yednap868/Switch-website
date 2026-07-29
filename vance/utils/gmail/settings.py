"""
Project settings
"""

import os
from enum import Enum

SELF_EMAIL = os.getenv("SELF_EMAIL", "relay@relayy.world")
SELF_NAME = os.getenv("SELF_NAME", "Vance")
COLLECTION_NAME = "emails"
LABEL = "Vance - An experiment in autonomous action."
PUB_SUB_TOPIC_NAME = os.getenv("PUB_SUB_TOPIC_NAME")
PUB_SUB_SUBSCRIPTION_ID = os.getenv("PUB_SUB_SUBSCRIPTION_ID")


class Collections(Enum):
    EMAILS = "emails"
    THREADS = "threads"
    REPLIES = "replies"
