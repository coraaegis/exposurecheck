"""In-session 'click to reveal your own post'.

By design there is no saved audit and no export, so reveal only works within the
same run that produced the cards. It shows the user's OWN original text (looked
up from the parsed export), never a synthesized value.
"""

from __future__ import annotations

from typing import Callable

from ..models import AuditResult, Export, Post, RiskCard


def build_post_index(exports: list[Export]) -> dict[tuple, Post]:
    # key by (platform, post_id) so Reddit and X ids can never collide
    return {(p.platform, p.post_id): p for ex in exports for p in ex.posts}


def reveal_category_text(card: RiskCard, index: dict[tuple, Post]) -> str:
    lines = [f"Your own posts behind {card.category.label} ({card.level}, score {card.risk_score}):", ""]
    shown: set[tuple] = set()
    for e in card.evidence:
        key = (e.platform, e.post_id)
        if not e.post_id or key in shown:
            continue
        post = index.get(key)
        if post is None:
            continue
        shown.add(key)
        when = post.created_at.isoformat() if post.created_at else "?"
        where = f"r/{post.community}" if post.community else post.platform.value
        lines.append(f"--- {where} | {when} ---")
        if post.permalink:
            lines.append(post.permalink)
        lines.append(post.text or "(no text — media-only post)")
        lines.append("")
    if not shown:
        lines.append("(this category is a profile / EXIF / timing signal — no single post to reveal)")
    return "\n".join(lines)


def reveal_loop(
    result: AuditResult,
    exports: list[Export],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    index = build_post_index(exports)
    cards = result.cards
    if not cards:
        output_fn("Nothing to reveal.")
        return
    while True:
        output_fn("")
        output_fn("Categories: " + " | ".join(
            f"{i + 1}={c.category.label}" for i, c in enumerate(cards)))
        try:
            choice = input_fn("Reveal which? (number, or 'q' to quit): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return
        if choice in ("q", "quit", "exit", ""):
            return
        if choice.isdigit() and 1 <= int(choice) <= len(cards):
            output_fn("")
            output_fn(reveal_category_text(cards[int(choice) - 1], index))
        else:
            output_fn("(enter a listed number, or 'q')")
