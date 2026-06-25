"""Recall-preserving prefilter.

Deletes ONLY what carries no signal at all: truly empty posts and pure
boilerplate ([deleted]/[removed]/bare punctuation) with no media and no links.
Short posts, bare URLs and "generic" chatter are deliberately kept — the mosaic
effect is assembled from many weak signals, so dropping them would manufacture
false reassurance.
"""

from __future__ import annotations

from ..models import Post

_BOILERPLATE = {"[deleted]", "[removed]", "deleted", "removed", ".", "..", "...", "n/a", "na", "-"}


def is_empty_or_boilerplate(post: Post) -> bool:
    t = (post.text or "").strip()
    has_extra = bool(post.media or post.urls)
    if not t and not has_extra:
        return True
    if t.lower() in _BOILERPLATE and not has_extra:
        return True
    return False


def prefilter(posts: list[Post]) -> tuple[list[Post], int]:
    kept: list[Post] = []
    dropped = 0
    for p in posts:
        if is_empty_or_boilerplate(p):
            dropped += 1
        else:
            kept.append(p)
    return kept, dropped
