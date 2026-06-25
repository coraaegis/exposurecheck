"""Cross-cutting remediation caveats shown beneath the cards.

Per-category steps live in risk/categories.py. These are the honest limits that
apply to all of them — the tool never deletes anything for you, and a lower
score is not a safety certificate.
"""

from __future__ import annotations


def global_caveats() -> list[str]:
    return [
        "This REDUCES risk; it does not guarantee anonymity. 'Low' is not 'safe'.",
        "Prefer generalising or editing over deleting. The tool never deletes anything for you.",
        "Deleting a post does NOT erase it: archives, search caches, screenshots and other "
        "users' copies can persist (e.g. the Wayback Machine, third-party scrapers).",
        "Re-run the audit after you edit (before/after) to confirm the score actually dropped.",
        "Out of scope: cross-service timing/metadata correlation, writing-style (stylometry), "
        "the follower/reply graph, and anything outside the export you provided. A closed-set "
        "audit is not the open world.",
        "Image CONTENT is not analysed — only EXIF/metadata, which platforms often strip. A "
        "photo can still reveal where you are from its content alone (a storefront, a skyline, "
        "a view), so review your own photos by eye; this tool does not.",
    ]
