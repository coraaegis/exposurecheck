"""Mechanical masked-snippet generation.

The masked snippet shown in a risk card is ALWAYS generated here from post
metadata (evidence label + where + when) — never from model free-text. This
guarantees the no-dossier invariant holds regardless of what an LLM returns:
the resolved value can only ever appear when the user clicks through to their
OWN original post.
"""

from __future__ import annotations

from ..models import Post


def masked_reference(post: Post, evidence_type: str) -> str:
    when = post.created_at.date().isoformat() if post.created_at else "?"
    where = f"r/{post.community}" if post.community else post.platform.value
    return f"[{evidence_type}] | {where} | {when}"
