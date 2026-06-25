"""Ownership consent gate (a dual-use guard).

The tool is scoped to auditing your OWN export. The gate is intentional friction,
not a legal shield: combined with ownership-gated export input, category-only
output, masking and no-export, it raises the cost of repurposing the tool to
profile someone else.
"""

from __future__ import annotations

from typing import Callable

CONSENT_TEXT = (
    "This tool analyzes ONLY your own social-media export. By continuing you attest that:\n"
    "  - the export is your own account's data (you own it), and\n"
    "  - you are auditing it to reduce your OWN exposure.\n"
    "Profiling someone else's history with this tool is out of scope and unsupported."
)

_ACCEPT = {"i own this data", "i-own-this-data", "yes", "y"}


def require_consent(
    attested: bool,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> bool:
    """Return True if the user has attested ownership (flag or interactive)."""
    if attested:
        return True
    output_fn(CONSENT_TEXT)
    try:
        ans = input_fn("Type 'I own this data' (or 'yes') to continue: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        output_fn("")
        return False
    return ans in _ACCEPT
