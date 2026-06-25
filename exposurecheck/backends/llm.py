"""LLM-driven backend: the real mosaic-inference engine.

Wraps a Transport (cloud or local). The model only ever decides *which* post
leaks *which* category, at what confidence — it is never asked for, and never
trusted to produce, the masked snippet or rationale (we generate those). That
keeps the no-dossier guarantee independent of model behaviour.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ..models import Confidence, Post, RiskCategory, Source
from .base import Backend, RawInference
from ._mask import masked_reference
from .transports import Transport

_CATS = [c.value for c in RiskCategory]
_CAT_BY_VALUE = {c.value: c for c in RiskCategory}

# Generic, developer-controlled evidence labels. The model is NEVER trusted to
# supply display text: it only chooses category/confidence/post_id, and the label
# shown on the card and inside the masked snippet is looked up here. This keeps
# the no-dossier guarantee independent of model behaviour (a model that tries to
# smuggle a resolved value into `evidence_type` cannot reach the output surface).
_LLM_EVIDENCE_LABEL: dict[RiskCategory, str] = {
    RiskCategory.LOCATION: "location signal",
    RiskCategory.EMPLOYER: "employer signal",
    RiskCategory.EDUCATION: "education signal",
    RiskCategory.FAMILY: "family signal",
    RiskCategory.AGE_DOB: "age / DOB signal",
    RiskCategory.HEALTH: "health signal",
    RiskCategory.FINANCE: "financial signal",
    RiskCategory.REAL_NAME: "real-name signal",
    RiskCategory.SCHEDULE: "routine / timing signal",
    RiskCategory.RELATIONSHIPS: "relationship signal",
    RiskCategory.POLITICS_RELIGION: "affiliation signal",
    RiskCategory.IDENTITY_LINK: "account-linkage signal",
}
_CAT_ALIASES = {
    "dob": RiskCategory.AGE_DOB, "age": RiskCategory.AGE_DOB,
    "job": RiskCategory.EMPLOYER, "work": RiskCategory.EMPLOYER, "company": RiskCategory.EMPLOYER,
    "name": RiskCategory.REAL_NAME, "identity": RiskCategory.REAL_NAME,
    "link": RiskCategory.IDENTITY_LINK, "account": RiskCategory.IDENTITY_LINK,
    "money": RiskCategory.FINANCE, "financial": RiskCategory.FINANCE,
    "politics": RiskCategory.POLITICS_RELIGION, "religion": RiskCategory.POLITICS_RELIGION,
    "home": RiskCategory.LOCATION, "address": RiskCategory.LOCATION, "city": RiskCategory.LOCATION,
    "school": RiskCategory.EDUCATION,
}

_ROUTE_SYS = (
    "You rank a user's OWN social-media posts by how much identifying personal "
    "information they could leak when AGGREGATED with the rest (location, employer, "
    "family, schedule, finances, identity links, etc.). Output strict JSON only: an "
    'array of {"i": <index int>, "s": <float 0..1>}. Higher s = more identifying '
    "signal. Include every index given. Short or weak posts can still score moderate; "
    "only truly empty or boilerplate posts score near 0."
)

_EXTRACT_SYS = (
    "You are a privacy auditor helping a user reduce their OWN re-identification risk. "
    "You see only the user's own posts. Acting as a careful adversary, decide which "
    "posts leak which categories of personal information when aggregated across the "
    "whole history, including weak individually-innocuous signals.\n"
    "Output STRICT JSON only: an array of objects "
    '{"post_id": str, "category": one of ' + json.dumps(_CATS) + ', '
    '"confidence": "low"|"medium"|"high"}.\n'
    "HARD RULES:\n"
    "- Do NOT output any resolved value (no real city, neighbourhood, street, employer "
    "name, person name, handle, exact age, or coordinates). Return only the structured "
    "fields above; the tool generates all displayed text itself.\n"
    "- Only use post_id values that appear in the input.\n"
    "- One object per (post, category) you find. Omit posts that leak nothing."
)


class LLMBackend(Backend):
    def __init__(self, transport: Transport, *, cheap_model: str, expensive_model: str,
                 route_chunk: int = 25, name: Optional[str] = None):
        self.transport = transport
        self.cheap_model = cheap_model
        self.expensive_model = expensive_model
        self.route_chunk = route_chunk
        self.name = name or f"llm:{transport.name}"
        self.is_local = transport.is_local
        self.sends_data_offsite = transport.sends_data_offsite

    # -- cheap tier -------------------------------------------------------- #
    def route(self, posts: list[Post]) -> list[float]:
        scores = [0.3] * len(posts)  # recall-preserving default: nothing starts at 0
        for start in range(0, len(posts), self.route_chunk):
            chunk = posts[start:start + self.route_chunk]
            payload = [{"i": i, "t": (p.text or "")[:280]} for i, p in enumerate(chunk)]
            try:
                raw = self.transport.complete(
                    _ROUTE_SYS, json.dumps(payload), self.cheap_model,
                    max_tokens=400, temperature=0.0)
            except Exception:
                continue  # keep defaults for this chunk on transport failure
            for obj in _loads_array(raw):
                try:
                    i = int(obj["i"])
                    s = float(obj["s"])
                except (KeyError, TypeError, ValueError):
                    continue
                if 0 <= i < len(chunk):
                    scores[start + i] = max(0.0, min(1.0, s))
        return scores

    # -- expensive tier ---------------------------------------------------- #
    def extract(self, batch: list[Post]) -> list[RawInference]:
        by_id = {p.post_id: p for p in batch}
        payload = [{
            "post_id": p.post_id,
            "community": p.community or "",
            "date": p.created_at.date().isoformat() if p.created_at else "",
            "text": (p.text or "")[:600],
        } for p in batch]
        try:
            raw = self.transport.complete(
                _EXTRACT_SYS, json.dumps(payload), self.expensive_model,
                max_tokens=900, temperature=0.0)
        except Exception:
            return []

        out: list[RawInference] = []
        for obj in _loads_array(raw):
            if not isinstance(obj, dict):
                continue
            cat = _to_category(obj.get("category"))
            pid = obj.get("post_id")
            post = by_id.get(pid)
            if cat is None or post is None:
                continue  # ignore hallucinated ids / unknown categories
            # label is mechanical (never the model's free text) — see _LLM_EVIDENCE_LABEL
            label = _LLM_EVIDENCE_LABEL.get(cat, "personal signal")
            out.append(RawInference(
                category=cat,
                confidence=_to_conf(obj.get("confidence")),
                masked_snippet=masked_reference(post, label),   # we generate it
                evidence_type=label,
                source=Source.TEXT,
                post_id=post.post_id,
                permalink=post.permalink,
                platform=post.platform,
            ))
        return out


# --------------------------------------------------------------------------- #
#  parsing helpers
# --------------------------------------------------------------------------- #

def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _loads_array(text: str) -> list:
    text = _strip_fences(text or "")
    try:
        v = json.loads(text)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            for k in ("inferences", "results", "items", "data"):
                if isinstance(v.get(k), list):
                    return v[k]
    except json.JSONDecodeError:
        pass
    i, j = text.find("["), text.rfind("]")
    if 0 <= i < j:
        try:
            v = json.loads(text[i:j + 1])
            return v if isinstance(v, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _to_category(s) -> Optional[RiskCategory]:
    if not s:
        return None
    key = str(s).strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    if key in _CAT_BY_VALUE:
        return _CAT_BY_VALUE[key]
    # whole-token match so "accountant" != "account", "worker" != "work"
    tokens = set(key.split("_"))
    for alias, cat in _CAT_ALIASES.items():
        if alias in tokens:
            return cat
    return None


def _to_conf(s) -> Confidence:
    key = str(s or "").strip().lower()
    return {
        "low": Confidence.LOW, "medium": Confidence.MEDIUM, "med": Confidence.MEDIUM,
        "high": Confidence.HIGH,
    }.get(key, Confidence.LOW)
