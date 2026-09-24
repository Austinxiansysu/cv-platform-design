"""Remove contact details from text before optional model requests."""

from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def redact_contact_details(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[local reference omitted]" if key == "source_reference"
            else redact_contact_details(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_contact_details(item) for item in value]
    if isinstance(value, str):
        return PHONE_RE.sub("[phone omitted]", EMAIL_RE.sub("[email omitted]", value))
    return value
