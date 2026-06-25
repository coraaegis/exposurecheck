"""The no-dossier invariant: the report surface must never echo a resolved
sensitive value, even though the tool *knows* it (it can show the user's own
post on click). Resolved specifics live only in the user's original posts, which
are surfaced solely through in-session reveal.
"""

from pathlib import Path

from exposurecheck.audit import run_audit
from exposurecheck.backends import HeuristicBackend
from exposurecheck.models import RiskCategory
from exposurecheck.output import render_report
from exposurecheck.output.interactive import build_post_index, reveal_category_text
from exposurecheck.parsers import parse_reddit, parse_twitter

FIX = Path(__file__).parent / "fixtures"

# resolved specifics that appear in the fixtures and must NOT leak into the report
LEAK_TOKENS = ["Northpoint", "Maple Street", "sampleuser.example"]


def _result_and_exports():
    exports = [
        parse_reddit(str(FIX / "reddit_sample")),
        parse_twitter(str(FIX / "twitter_sample")),
    ]
    return run_audit(exports, HeuristicBackend()), exports


def test_report_does_not_echo_resolved_values():
    result, _ = _result_and_exports()
    report = render_report(result)
    for tok in LEAK_TOKENS:
        assert tok not in report, f"report leaked resolved value: {tok!r}"


def test_every_evidence_snippet_is_masked():
    result, _ = _result_and_exports()
    for card in result.cards:
        for e in card.evidence:
            assert "[" in e.masked_snippet and "]" in e.masked_snippet


def test_reveal_shows_own_post_text_that_report_hid():
    result, exports = _result_and_exports()
    index = build_post_index(exports)
    loc = next(c for c in result.cards if c.category == RiskCategory.LOCATION)
    revealed = reveal_category_text(loc, index)
    # the resolved neighbourhood is hidden from the report but visible when the
    # user explicitly clicks through to their OWN post
    assert "Northpoint" in revealed
    assert "Northpoint" not in render_report(result)
