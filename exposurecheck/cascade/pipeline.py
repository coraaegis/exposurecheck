"""Cascade orchestration: prefilter -> deterministic -> cheap route -> expensive
extract (batched) -> summarize.

Cost control lives in the candidate budget: the cheap tier ranks every kept post,
the expensive tier runs only on the top fraction. Crucially this is a *budget*,
not a filter — posts below the cut are reported as "not deeply analyzed", never
silently dropped, so coverage is always honest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..backends.base import Backend, RawInference
from ..models import Export, Finding
from .deterministic import deterministic_signals
from .prefilter import prefilter
from .summarize import summarize


@dataclass
class CascadeOutcome:
    findings: list[Finding]
    post_count: int          # total parsed posts
    kept_count: int          # survived prefilter
    dropped_count: int       # truly empty / boilerplate removed
    candidate_count: int     # routed to the expensive tier
    not_analyzed_count: int  # kept but below budget — NOT deleted, just not deep-analyzed
    raw_count: int           # raw inferences before aggregation


def run_cascade(
    exports: list[Export],
    backend: Backend,
    *,
    candidate_fraction: float = 1.0,
    max_candidates: Optional[int] = None,
    batch_size: int = 10,
    progress: Optional[Callable[[int, int], None]] = None,
) -> CascadeOutcome:
    all_posts = [p for ex in exports for p in ex.posts]
    kept, dropped = prefilter(all_posts)

    raws: list[RawInference] = []
    for ex in exports:
        raws += deterministic_signals(ex)

    scores = backend.route(kept) if kept else []
    order = sorted(range(len(kept)), key=lambda i: scores[i] if i < len(scores) else 0.0,
                   reverse=True)
    if candidate_fraction >= 1.0:
        k = len(kept)
    else:
        k = max(0, int(round(len(kept) * candidate_fraction)))
    if max_candidates is not None:
        k = min(k, max_candidates)
    candidates = [kept[i] for i in order[:k]]

    for start in range(0, len(candidates), batch_size):
        batch = candidates[start:start + batch_size]
        raws += backend.extract(batch)
        if progress:
            progress(min(start + batch_size, len(candidates)), len(candidates))

    return CascadeOutcome(
        findings=summarize(raws),
        post_count=len(all_posts),
        kept_count=len(kept),
        dropped_count=dropped,
        candidate_count=len(candidates),
        not_analyzed_count=len(kept) - len(candidates),
        raw_count=len(raws),
    )
