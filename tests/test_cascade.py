from pathlib import Path

from selfaudit.audit import run_audit
from selfaudit.backends import HeuristicBackend
from selfaudit.cascade.prefilter import is_empty_or_boilerplate, prefilter
from selfaudit.models import Platform, Post, RiskCategory
from selfaudit.parsers import parse_reddit, parse_twitter

FIX = Path(__file__).parent / "fixtures"


def _p(text, **kw):
    return Post(platform=Platform.REDDIT, post_id="x", text=text, **kw)


def test_prefilter_keeps_weak_drops_empty():
    assert is_empty_or_boilerplate(_p(""))
    assert is_empty_or_boilerplate(_p("[deleted]"))
    assert is_empty_or_boilerplate(_p("..."))
    assert not is_empty_or_boilerplate(_p("ok"))          # short kept
    assert not is_empty_or_boilerplate(_p("", urls=["http://x"]))  # url-only kept
    kept, dropped = prefilter([_p(""), _p("[removed]"), _p("hi"), _p("ok")])
    assert dropped == 2 and len(kept) == 2


def test_end_to_end_heuristic_finds_location_high():
    exports = [
        parse_reddit(str(FIX / "reddit_sample")),
        parse_twitter(str(FIX / "twitter_sample")),
    ]
    result = run_audit(exports, HeuristicBackend())
    assert result.post_count == 15
    cats = {c.category: c for c in result.cards}
    assert RiskCategory.LOCATION in cats
    loc = cats[RiskCategory.LOCATION]
    assert loc.level == "High"
    # location compounds text clues + profile field + EXIF GPS across >1 source
    sources = {e.source.value for e in loc.evidence}
    assert {"text", "metadata", "exif"} <= sources
    # cards are sorted by descending risk score
    scores = [c.risk_score for c in result.cards]
    assert scores == sorted(scores, reverse=True)


def test_single_exif_gps_alone_is_high():
    # an X export with one geotagged photo and nothing else should still flag High
    ex = parse_twitter(str(FIX / "twitter_sample"))
    # keep only the media-bearing tweet's export-level media; drop posts text
    for p in ex.posts:
        p.text = ""
    ex.profile.bio = None
    ex.profile.location_field = None
    ex.profile.website = None
    result = run_audit([ex], HeuristicBackend())
    loc = next((c for c in result.cards if c.category == RiskCategory.LOCATION), None)
    assert loc is not None and loc.level == "High"
