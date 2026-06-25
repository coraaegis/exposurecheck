"""Aggregate raw inferences into one Finding per category.

The classic adversary pipeline ends in a "Summarizer" that resolves a unified
person profile. We deliberately stop short of that: building a resolved dossier
would itself be the exposure the tool exists to prevent. Instead we aggregate
*per category* — merge and de-duplicate the evidence, keep the references back
to the user's own posts, and carry the strongest confidence forward. The risk
score (sensitivity x diversity x volume x recency ...) is computed downstream.
"""

from __future__ import annotations

from collections import defaultdict

from ..backends.base import RawInference
from ..models import Confidence, Evidence, Finding, RiskCategory


def summarize(raws: list[RawInference]) -> list[Finding]:
    by_cat: dict[RiskCategory, list[RawInference]] = defaultdict(list)
    for r in raws:
        by_cat[r.category].append(r)

    findings: list[Finding] = []
    for cat, items in by_cat.items():
        seen: set[tuple] = set()
        evidence: list[Evidence] = []
        best = Confidence.LOW
        for r in items:
            key = (r.post_id, r.evidence_type, r.source)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(Evidence(
                masked_snippet=r.masked_snippet,
                evidence_type=r.evidence_type,
                source=r.source,
                post_id=r.post_id,
                permalink=r.permalink,
            ))
            if r.confidence.weight > best.weight:
                best = r.confidence
        findings.append(Finding(category=cat, confidence=best, evidence=evidence))
    return findings
