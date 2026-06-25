"""Render the no-dossier report to plain text.

Shows category cards (level, score, why, masked examples, remediation) — never a
synthesized "you are X" profile, and never an exported value. The only way to
see a resolved value is the user clicking through to their OWN post in-session.
"""

from __future__ import annotations

import textwrap

from ..models import AuditResult, RiskCard
from ..remediation import global_caveats

_LEVEL_TAG = {"High": "[HIGH]", "Medium": "[MED ]", "Low": "[LOW ]"}
_WIDTH = 76


def render_report(result: AuditResult) -> str:
    L: list[str] = []
    bar = "=" * _WIDTH
    L.append(bar)
    L.append(" exposurecheck  --  re-identification risk (no-dossier)")
    L.append(bar)
    L.append(f" backend     : {result.backend_name}")
    L.append(f" platforms   : {', '.join(p.value for p in result.platforms) or '-'}")
    m = result.meta
    L.append(f" posts       : {result.post_count} parsed | "
             f"{result.candidate_count} analyzed | {m.get('dropped', 0)} empty skipped")
    if m.get("not_analyzed"):
        L.append(f" budget note : {m['not_analyzed']} kept posts were below the analysis "
                 f"budget — NOT deleted; re-run with --full to include them.")
    if m.get("media_count"):
        L.append(f" media       : {m['media_count']} image(s) — EXIF/metadata only; visual "
                 f"content NOT analyzed (review your photos yourself)")

    if not result.cards:
        L.append("")
        L.append(" No category-level risks surfaced.")
        if result.backend_name.startswith("heuristic"):
            L.append(" WARNING: heuristic backend has near-zero recall. This is NOT an all-clear.")
    for c in result.cards:
        L += _render_card(c)

    L.append("")
    L.append("-" * _WIDTH)
    L.append(" Limits & honest caveats")
    for cv in global_caveats():
        L += _bullet(cv, indent=3)
    L.append("")
    L.append(" See your own posts behind a category (in-session, nothing is saved):")
    L.append("   exposurecheck audit <args> --interactive")
    L.append("")
    return "\n".join(L)


def _render_card(c: RiskCard) -> list[str]:
    out = ["", f" {_LEVEL_TAG.get(c.level, '[    ]')} {c.category.label.upper()}  (score {c.risk_score})"]
    out.append(f"        {c.summary}")
    for w in textwrap.wrap("Why: " + c.rationale, _WIDTH - 8):
        out.append("        " + w)
    if c.evidence_types:
        out.append("        Evidence: " + ", ".join(c.evidence_types[:8]))
    examples = [e.masked_snippet for e in c.evidence[:5]]
    if examples:
        out.append("        Examples (masked):")
        out += ["          - " + ex for ex in examples]
    if c.to_review_count:
        out.append(f"        To review: {c.to_review_count} of your own posts (reveal in-session)")
    if c.remediation:
        out.append("        Reduce:")
        for r in c.remediation:
            wrapped = textwrap.wrap(r, _WIDTH - 12)
            if wrapped:
                out.append("          - " + wrapped[0])
                out += ["            " + w for w in wrapped[1:]]
    return out


def _bullet(text: str, indent: int) -> list[str]:
    pad = " " * indent
    wrapped = textwrap.wrap(text, _WIDTH - indent - 2)
    if not wrapped:
        return []
    out = [f"{pad}- {wrapped[0]}"]
    out += [f"{pad}  {w}" for w in wrapped[1:]]
    return out
