from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?44\s?\d{3,4}|0\d{3,4})[\s()-]?\d{3,4}[\s-]?\d{3,4}(?!\w)")


def redact_pii(text: str) -> str:
    text = EMAIL_PATTERN.sub("[EMAIL REDACTED]", text)
    return PHONE_PATTERN.sub("[PHONE REDACTED]", text)

