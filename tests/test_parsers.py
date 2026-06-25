from pathlib import Path

from exposurecheck.metadata import read_exif
from exposurecheck.models import Platform
from exposurecheck.parsers import parse_reddit, parse_twitter

FIX = Path(__file__).parent / "fixtures"


def test_reddit_parse_counts_and_fields():
    ex = parse_reddit(str(FIX / "reddit_sample"))
    assert ex.platform == Platform.REDDIT
    assert len(ex.posts) == 12  # 10 comments + 2 submissions
    kinds = {p.kind for p in ex.posts}
    assert kinds == {"comment", "submission"}
    c1 = next(p for p in ex.posts if p.post_id == "c1")
    assert c1.community == "SampleCity"
    assert c1.created_at is not None and c1.created_at.year == 2023
    assert c1.permalink and c1.permalink.startswith("https://www.reddit.com/")


def test_reddit_keeps_weak_signals():
    ex = parse_reddit(str(FIX / "reddit_sample"))
    bodies = {p.post_id: p.text for p in ex.posts}
    assert bodies["c8"] == "ok"            # short post kept
    # bare-URL comment kept, URL extracted
    c9 = next(p for p in ex.posts if p.post_id == "c9")
    assert c9.urls == ["https://example.org/some-guide"]


def test_twitter_parse_metadata_and_media():
    ex = parse_twitter(str(FIX / "twitter_sample"))
    assert ex.platform == Platform.TWITTER
    assert len(ex.posts) == 3
    assert ex.profile.handle == "sampleuser"
    assert ex.profile.location_field == "Northpoint, SampleCity"
    assert ex.profile.website == "https://sampleuser.example"
    # entities
    t2 = next(p for p in ex.posts if p.post_id == "1500000000000000002")
    assert "@somecoworker" in t2.mentions
    assert "https://blog.example/oncall" in t2.urls
    assert t2.permalink == "https://twitter.com/sampleuser/status/1500000000000000002"
    # media + EXIF attached to the right tweet
    t5 = next(p for p in ex.posts if p.post_id == "1500000000000000005")
    assert len(t5.media) == 1
    assert t5.media[0].exif is not None
    assert t5.media[0].exif.has_location()


def test_exif_gps_decoded():
    jpg = FIX / "twitter_sample" / "data" / "tweets_media" / "1500000000000000005-AbCd1234.jpg"
    exif = read_exif(str(jpg))
    assert exif is not None
    assert abs(exif.gps_lat - 47.6) < 1e-4
    assert abs(exif.gps_lon - (-122.32)) < 1e-4
    assert exif.make == "Cam"
