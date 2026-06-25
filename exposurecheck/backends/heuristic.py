"""Deterministic, offline, dependency-free stub backend.

PURPOSE: let the whole pipeline run end-to-end with no API key and no model, for
development, tests and CI. It uses keyword/regex matching only.

IMPORTANT — this is NOT real protection. Regex/keyword matching has near-zero
recall against the actual mosaic threat: the danger is an LLM *reasoning* across
many weak, individually-innocuous posts, which keywords cannot reproduce. Treat
heuristic output as a smoke test of the plumbing, never as an audit. The CLI
prints a loud warning when this backend is selected.
"""

from __future__ import annotations

import re

from ..models import Confidence, Post, RiskCategory, Source
from .base import Backend, RawInference
from ._mask import masked_reference

# (category, evidence_type label, pattern, confidence)
_LEXICON: list[tuple[RiskCategory, str, re.Pattern, Confidence]] = [
    (RiskCategory.LOCATION, "location clue",
     re.compile(r"\b(live|lives|living|moved|move|near|downtown|neighbou?rhood|commute|"
                r"ferry|station|light-rail|marina|reservoir|uptown|my (block|street))\b", re.I),
     Confidence.LOW),
    (RiskCategory.EMPLOYER, "employer mention",
     re.compile(r"\b(my (company|team|employer|office|boss)|at the startup|we hire|we're hiring|"
                r"i work (at|for)|as an? (sre|engineer|developer|manager|analyst))\b", re.I),
     Confidence.MEDIUM),
    (RiskCategory.SCHEDULE, "routine / timing clue",
     re.compile(r"\b(\d{1,2}(:\d{2})?\s?(am|pm)|every (weekday|morning|day)|on-call|"
                r"before work|after work|my (morning|commute) routine)\b", re.I),
     Confidence.LOW),
    (RiskCategory.FAMILY, "family reference",
     re.compile(r"\b(my (daughter|son|kid|kids|child|children|wife|husband|partner|mom|dad)|"
                r"kindergarten|elementary school|drop-off)\b", re.I),
     Confidence.MEDIUM),
    (RiskCategory.FINANCE, "financial disclosure",
     re.compile(r"\b(\d+(\.\d+)?\s?btc|bitcoin|stacking|cold storage|my (portfolio|salary|income)|"
                r"net worth|i hold|i own \d)\b", re.I),
     Confidence.LOW),
    (RiskCategory.AGE_DOB, "age / DOB clue",
     re.compile(r"\b(i'?m \d{2}\b|born in (19|20)\d{2}|turned \d{2}|my birthday|\bm\d{2}\b|\bf\d{2}\b)",
                re.I),
     Confidence.MEDIUM),
    (RiskCategory.IDENTITY_LINK, "cross-account / identity clue",
     re.compile(r"\b(my real name|same (handle|username)|my (other|main) account|on my (blog|site)|"
                r"my personal (site|website))\b", re.I),
     Confidence.MEDIUM),
]


def scan_text(text: str) -> list[tuple[RiskCategory, str, Confidence]]:
    """Run the keyword lexicon over a piece of text. Shared by the heuristic
    backend (post bodies) and the deterministic layer (profile bio)."""
    hits = []
    for category, label, pat, conf in _LEXICON:
        if pat.search(text or ""):
            hits.append((category, label, conf))
    return hits


class HeuristicBackend(Backend):
    name = "heuristic"
    is_local = True
    sends_data_offsite = False

    def route(self, posts: list[Post]) -> list[float]:
        scores = []
        for p in posts:
            s = 0.1
            text = p.text or ""
            if any(pat.search(text) for _c, _l, pat, _conf in _LEXICON):
                s += 0.4
            if p.urls:
                s += 0.15
            if p.mentions:
                s += 0.1
            if any(m.exif and m.exif.has_location() for m in p.media):
                s += 0.5
            scores.append(min(s, 1.0))
        return scores

    def extract(self, batch: list[Post]) -> list[RawInference]:
        out: list[RawInference] = []
        for p in batch:
            text = p.text or ""
            for category, label, pat, conf in _LEXICON:
                if pat.search(text):
                    out.append(RawInference(
                        category=category,
                        confidence=conf,
                        masked_snippet=masked_reference(p, label),
                        evidence_type=label,
                        source=Source.TEXT,
                        post_id=p.post_id,
                        permalink=p.permalink,
                        platform=p.platform,
                        rationale=f"{label} detected by keyword match (low-recall stub).",
                    ))
        return out
