"""UPI deep-link generator for Switch employer payments."""

import os
import re
from urllib.parse import quote

UPI_VPA = os.getenv("UPI_VPA", "")
MERCHANT_NAME = "Switch"


def generate_upi_link(amount: float, payment_ref: str) -> str:
    """Return a UPI deep-link string for the given amount and payment reference."""
    if not UPI_VPA:
        raise ValueError("UPI_VPA env var not set")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if round(amount, 2) != amount:
        raise ValueError("Amount can have at most 2 decimal places")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,35}", payment_ref):
        raise ValueError("payment_ref must be alphanumeric/underscore, max 35 chars")
    return (
        f"upi://pay?pa={quote(UPI_VPA)}"
        f"&pn={quote(MERCHANT_NAME)}"
        f"&am={amount:.2f}"
        f"&cu=INR"
        f"&tn={quote(payment_ref)}"
    )
