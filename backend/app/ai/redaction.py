from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


SINGAPORE_ID_PATTERN = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
SINGAPORE_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\w)"
)


@dataclass(frozen=True)
class RedactionResult:
    text: str
    replacements: dict[str, int]


def redact_phi(text: str, *, known_names: Iterable[str]) -> RedactionResult:
    """Redact the deterministic first-version PHI categories before LLM use."""
    redacted, id_count = SINGAPORE_ID_PATTERN.subn("[ID]", text)
    redacted, phone_count = SINGAPORE_PHONE_PATTERN.subn("[PHONE]", redacted)

    name_count = 0
    names = sorted({name.strip() for name in known_names if name.strip()}, key=len, reverse=True)
    for name in names:
        pattern = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.IGNORECASE)
        redacted, replacements = pattern.subn("[PATIENT_NAME]", redacted)
        name_count += replacements

    return RedactionResult(
        text=redacted,
        replacements={"name": name_count, "phone": phone_count, "id": id_count},
    )
