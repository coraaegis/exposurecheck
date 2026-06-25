"""Always-on deterministic signal extraction (no LLM, no network).

Runs for every backend, alongside the text cascade. On X especially, the
strongest leaks are not in the prose: a self-set location field, an outbound
website link from a pseudonymous account, image GPS in EXIF, and a tight
posting-time concentration that betrays a timezone. These are extracted
mechanically so a degraded or heuristic backend can never miss them.
"""

from __future__ import annotations

from collections import Counter

from ..backends.base import RawInference
from ..backends.heuristic import scan_text
from ..models import Confidence, Export, RiskCategory, Source

# minimum posts before a timing inference is meaningful
_TIMING_MIN_POSTS = 20


def deterministic_signals(export: Export) -> list[RawInference]:
    out: list[RawInference] = []
    out += _from_profile(export)
    out += _from_exif(export)
    out += _from_timing(export)
    return out


def _ref(export: Export) -> str:
    p = export.profile
    handle = p.handle if p and p.handle else export.platform.value
    return f"@{handle}" if p and p.handle else handle


def _from_profile(export: Export) -> list[RawInference]:
    p = export.profile
    if p is None:
        return []
    out: list[RawInference] = []
    ref = _ref(export)
    pin = p.pinned_post_id

    if p.location_field:
        out.append(RawInference(
            category=RiskCategory.LOCATION, confidence=Confidence.MEDIUM,
            masked_snippet=f"[self-set location field] | {ref}",
            evidence_type="profile location field", source=Source.METADATA,
            post_id=pin, permalink=None,
        ))
    if p.website:
        out.append(RawInference(
            category=RiskCategory.IDENTITY_LINK, confidence=Confidence.MEDIUM,
            masked_snippet=f"[outbound website link] | {ref}",
            evidence_type="profile website link", source=Source.METADATA,
            post_id=pin, permalink=p.website,
        ))
    if p.bio:
        for category, label, conf in scan_text(p.bio):
            # self-description in a bio is more reliable than passing prose
            bumped = Confidence.MEDIUM if conf == Confidence.LOW else conf
            out.append(RawInference(
                category=category, confidence=bumped,
                masked_snippet=f"[{label} in bio] | {ref}",
                evidence_type=f"{label} (bio)", source=Source.METADATA,
                post_id=pin, permalink=None,
            ))
    return out


def _from_exif(export: Export) -> list[RawInference]:
    out: list[RawInference] = []
    for m in export.media:
        if not m.exif:
            continue
        if m.exif.has_location():
            out.append(RawInference(
                category=RiskCategory.LOCATION, confidence=Confidence.HIGH,
                masked_snippet=f"[image GPS in EXIF] | {m.filename}",
                evidence_type="image GPS (EXIF)", source=Source.EXIF,
                post_id=m.parent_post_id, permalink=None,
            ))
        if m.exif.make or m.exif.model:
            out.append(RawInference(
                category=RiskCategory.IDENTITY_LINK, confidence=Confidence.LOW,
                masked_snippet=f"[camera make/model in EXIF] | {m.filename}",
                evidence_type="device fingerprint (EXIF)", source=Source.EXIF,
                post_id=m.parent_post_id, permalink=None,
            ))
    return out


def _from_timing(export: Export) -> list[RawInference]:
    hours = [p.created_at.hour for p in export.posts if p.created_at is not None]
    if len(hours) < _TIMING_MIN_POSTS:
        return []
    counts = Counter(hours)
    # best contiguous 8-hour window (wrap-around)
    best = 0
    for start in range(24):
        window = sum(counts.get((start + k) % 24, 0) for k in range(8))
        best = max(best, window)
    share = best / len(hours)
    if share < 0.70:
        return []
    conf = Confidence.HIGH if share >= 0.85 else Confidence.MEDIUM
    pct = int(round(share * 100))
    return [RawInference(
        category=RiskCategory.SCHEDULE, confidence=conf,
        masked_snippet=f"[posting-time concentration ~{pct}% in an 8h window] | {_ref(export)}",
        evidence_type="posting-time concentration", source=Source.TIMING,
        post_id=None, permalink=None,
    )]
