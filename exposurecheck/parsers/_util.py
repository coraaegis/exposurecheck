"""Small parsing helpers shared by both platform parsers."""

from __future__ import annotations

import re

_URL_RE = re.compile(r'https?://[^\s<>"\')\]]+', re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    """Pull outbound links from free text, de-duplicated, trailing punctuation trimmed."""
    if not text:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for m in _URL_RE.findall(text):
        u = m.rstrip(".,);]'\"")
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out
