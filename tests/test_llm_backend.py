"""LLM-backend correctness with a stub transport (no network).

Locks the no-dossier guarantee for the *LLM* path (the heuristic-only
test_no_dossier.py couldn't catch a model smuggling a resolved value through
the structured fields), plus category mapping and route parsing.
"""

import json

from exposurecheck.backends.llm import LLMBackend, _to_category
from exposurecheck.backends.transports import Transport
from exposurecheck.cascade.summarize import summarize
from exposurecheck.models import AuditResult, Platform, Post, RiskCategory
from exposurecheck.output import render_report
from exposurecheck.risk import build_cards


class StubTransport(Transport):
    name = "stub"
    is_local = True
    sends_data_offsite = False

    def __init__(self, payload: str):
        self._payload = payload

    def complete(self, system, user, model, *, max_tokens=800, temperature=0.0):
        return self._payload


def _post(pid="c1", text="some text"):
    return Post(platform=Platform.REDDIT, post_id=pid, text=text, community="SampleCity")


def test_llm_evidence_type_cannot_leak_resolved_value():
    leak = "lives at 12 Maple St, Northpoint"
    payload = json.dumps([
        {"post_id": "c1", "category": "location", "confidence": "high", "evidence_type": leak},
    ])
    backend = LLMBackend(StubTransport(payload), cheap_model="x", expensive_model="x")
    raws = backend.extract([_post("c1")])
    assert raws and raws[0].category == RiskCategory.LOCATION
    for r in raws:
        assert leak not in r.masked_snippet and leak not in r.evidence_type
        assert "Maple St" not in r.masked_snippet
        assert "Northpoint" not in r.masked_snippet

    # and end-to-end through the rendered report
    findings = summarize(raws)
    result = AuditResult(cards=build_cards(findings), findings=findings,
                         backend_name=backend.name, post_count=1, candidate_count=1,
                         platforms=[Platform.REDDIT])
    report = render_report(result)
    assert "Northpoint" not in report and "Maple St" not in report


def test_llm_ignores_hallucinated_post_ids():
    payload = json.dumps([{"post_id": "NOPE", "category": "location", "confidence": "high"}])
    backend = LLMBackend(StubTransport(payload), cheap_model="x", expensive_model="x")
    assert backend.extract([_post("c1")]) == []


def test_to_category_whole_token_match():
    assert _to_category("location") == RiskCategory.LOCATION
    assert _to_category("account") == RiskCategory.IDENTITY_LINK
    assert _to_category("accountant") is None   # token, not substring
    assert _to_category("worker") is None        # not "work"
    assert _to_category("employer") == RiskCategory.EMPLOYER
    assert _to_category("nonsense") is None


def test_route_parses_and_defaults_recall_preserving():
    payload = json.dumps([{"i": 0, "s": 0.9}])   # only index 0 scored
    backend = LLMBackend(StubTransport(payload), cheap_model="x", expensive_model="x")
    scores = backend.route([_post("a"), _post("b")])
    assert scores[0] == 0.9
    assert scores[1] == 0.3   # unscored posts keep the non-zero default (never dropped)
