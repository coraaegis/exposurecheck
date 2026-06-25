"""Risk-contribution scoring.

Triage is by *risk contribution*, not raw model confidence (which is poorly
calibrated). A category's score rises with its intrinsic sensitivity, the
strongest confidence seen, the VOLUME of corroborating evidence (the mosaic
effect — many weak signals compound), and the DIVERSITY of evidence sources and
types. A single high-sensitivity signal (e.g. EXIF GPS) still lands high; a pile
of individually-weak location clues also compounds into high — which is exactly
the failure mode users underestimate.
"""

from __future__ import annotations

import math

from ..models import Finding
from .categories import SENSITIVITY


def score_finding(finding: Finding) -> float:
    sens = SENSITIVITY.get(finding.category, 0.5)
    conf = finding.confidence.weight

    n = len(finding.evidence)
    volume = min(1.0, math.log2(1 + n) / 3.0)            # saturates around n=7

    sources = {e.source for e in finding.evidence}
    types = {e.evidence_type for e in finding.evidence}
    diversity = min(1.0, (len(sources) - 1) * 0.34 + (len(types) - 1) * 0.15)

    raw = sens * (0.45 * conf + 0.35 * volume + 0.20 * diversity + 0.20)
    score = round(min(1.0, raw) * 100.0, 1)

    finding.risk_score = score
    finding.score_breakdown = {
        "sensitivity": round(sens, 2),
        "confidence": round(conf, 2),
        "volume": round(volume, 2),
        "diversity": round(diversity, 2),
        "evidence_count": n,
        "sources": sorted(s.value for s in sources),
    }
    return score


def score_all(findings: list[Finding]) -> list[Finding]:
    for f in findings:
        score_finding(f)
    findings.sort(key=lambda f: f.risk_score, reverse=True)
    return findings
