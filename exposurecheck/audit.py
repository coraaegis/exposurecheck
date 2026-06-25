"""Top-level orchestration: parsed exports + a backend -> AuditResult."""

from __future__ import annotations

from typing import Callable, Optional

from .backends.base import Backend
from .cascade import run_cascade
from .models import AuditResult, Export
from .risk import build_cards


def run_audit(
    exports: list[Export],
    backend: Backend,
    *,
    candidate_fraction: float = 1.0,
    max_candidates: Optional[int] = None,
    batch_size: int = 10,
    progress: Optional[Callable[[int, int], None]] = None,
) -> AuditResult:
    outcome = run_cascade(
        exports, backend,
        candidate_fraction=candidate_fraction,
        max_candidates=max_candidates,
        batch_size=batch_size,
        progress=progress,
    )
    cards = build_cards(outcome.findings)
    return AuditResult(
        cards=cards,
        findings=outcome.findings,
        backend_name=backend.name,
        post_count=outcome.post_count,
        candidate_count=outcome.candidate_count,
        platforms=[ex.platform for ex in exports],
        meta={
            "dropped": outcome.dropped_count,
            "kept": outcome.kept_count,
            "not_analyzed": outcome.not_analyzed_count,
            "raw": outcome.raw_count,
            "media_count": sum(len(ex.media) for ex in exports),
        },
    )
