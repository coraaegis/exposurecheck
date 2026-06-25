"""Turn scored findings into category risk cards (the no-dossier surface)."""

from __future__ import annotations

from ..models import Finding, RiskCard
from .categories import RATIONALES, REMEDIATION, level_for
from .scoring import score_all


def build_cards(findings: list[Finding]) -> list[RiskCard]:
    score_all(findings)  # scores in place and sorts by risk_score desc
    cards: list[RiskCard] = []
    for f in findings:
        post_ids = {e.post_id for e in f.evidence if e.post_id}
        sources = sorted({e.source.value for e in f.evidence})
        types: list[str] = []
        for e in f.evidence:
            if e.evidence_type not in types:
                types.append(e.evidence_type)
        cards.append(RiskCard(
            category=f.category,
            level=level_for(f.risk_score),
            risk_score=f.risk_score,
            summary=_summary(len(f.evidence), len(post_ids), sources),
            rationale=RATIONALES.get(f.category, ""),
            evidence_types=types,
            evidence=f.evidence,
            to_review_count=sum(1 for e in f.evidence if e.permalink),
            remediation=REMEDIATION.get(f.category, []),
        ))
    return cards


def _summary(n_signals: int, n_posts: int, sources: list[str]) -> str:
    parts = [f"{n_signals} signal" + ("s" if n_signals != 1 else "")]
    if n_posts:
        parts.append(f"{n_posts} post" + ("s" if n_posts != 1 else ""))
    parts.append(("sources: " if len(sources) != 1 else "source: ") + ", ".join(sources))
    return " · ".join(parts)
