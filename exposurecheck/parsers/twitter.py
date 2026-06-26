"""Parse an X / Twitter data export.

The export is a directory (or .zip) with a ``data/`` folder of ``window.YTD.*``
JavaScript files plus a ``tweets_media/`` image folder. A large archive splits its
tweets across ``tweets.js`` + ``tweets-part1.js`` … and every part is read. Unlike Reddit, X leakage
is **metadata-driven**: the bio, self-set location field, pinned tweet, posting
times/timezone, outbound links, the mention graph, and image EXIF/GPS often leak
more than the tweet text. This parser pulls all of those layers, not just text —
a text-only X audit would be false reassurance.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from ..metadata import read_exif_bytes
from ..models import AccountProfile, Export, MediaRef, Platform, Post
from ._source import ExportSource


def parse_twitter(path: str) -> Export:
    with ExportSource(path) as src:
        account = _parse_wrapped(src.read_text("account.js"), "account")
        profile = _parse_wrapped(src.read_text("profile.js"), "profile")
        handle = (account or {}).get("username")
        # A large archive splits tweets across tweets.js + tweets-part1.js, …
        # (legacy: tweet.js). Read every part, not just the first. The regex
        # excludes the separate tweet-headers.js / note-tweets.js files.
        items: list = []
        for rel in src.find_matching(r"tweets?(-part\d+)?\.js"):
            data = src.read_bytes(rel)
            if data:
                items.extend(_load_js_array(data.decode("utf-8", "replace")))
        posts = _parse_tweet_items(items, handle)

        media_by_post = _attach_media(src)
        for p in posts:
            if p.post_id in media_by_post:
                p.media = media_by_post[p.post_id]
        all_media = [m for ms in media_by_post.values() for m in ms]

        prof = _build_profile(account, profile)
        # mark the pinned tweet if account.js exposes it
        pinned = (account or {}).get("pinnedTweetId") or (profile or {}).get("pinnedTweetId")
        if pinned:
            prof.pinned_post_id = str(pinned)
    return Export(platform=Platform.TWITTER, posts=posts, profile=prof, media=all_media)


# --------------------------------------------------------------------------- #
#  window.YTD.<name>.partN = [ ... ];  ->  python list
# --------------------------------------------------------------------------- #

def _load_js_array(text: Optional[str]) -> list:
    if not text:
        return []
    idx = text.find("=")
    if idx == -1:
        return []
    payload = text[idx + 1:].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _parse_wrapped(text: Optional[str], key: str) -> dict:
    arr = _load_js_array(text)
    if arr and isinstance(arr[0], dict) and key in arr[0]:
        return arr[0][key] or {}
    return {}


def _parse_tweet_items(items: list, handle: Optional[str]) -> list[Post]:
    out: list[Post] = []
    for item in items:
        tw = item.get("tweet") if isinstance(item, dict) else None
        if not isinstance(tw, dict):
            continue
        tid = str(tw.get("id_str") or tw.get("id") or "").strip()
        full = tw.get("full_text") or tw.get("text") or ""
        ent = tw.get("entities") or {}
        urls = [u.get("expanded_url") or u.get("url")
                for u in ent.get("urls", []) if isinstance(u, dict)]
        urls = [u for u in urls if u]
        mentions = ["@" + m["screen_name"]
                    for m in ent.get("user_mentions", [])
                    if isinstance(m, dict) and m.get("screen_name")]
        hashtags = ["#" + h["text"]
                    for h in ent.get("hashtags", [])
                    if isinstance(h, dict) and h.get("text")]
        permalink = f"https://twitter.com/{handle}/status/{tid}" if handle and tid else None
        out.append(Post(
            platform=Platform.TWITTER,
            post_id=tid or f"t_{len(out)}",
            text=full,
            created_at=_parse_date(tw.get("created_at")),
            raw_created_at=(tw.get("created_at") or "").strip() or None,
            permalink=permalink,
            urls=urls,
            mentions=mentions,
            hashtags=hashtags,
            kind="tweet",
        ))
    return out


def _attach_media(src: ExportSource) -> dict[str, list[MediaRef]]:
    by_post: dict[str, list[MediaRef]] = {}
    for rel in src.list_dir("tweets_media", "tweet_media"):
        fn = os.path.basename(rel)
        tid = fn.split("-", 1)[0]
        if not tid.isdigit():
            continue
        exif = None
        if fn.lower().endswith((".jpg", ".jpeg")):
            data = src.read_bytes(rel)
            if data:
                exif = read_exif_bytes(data)
        by_post.setdefault(tid, []).append(
            MediaRef(path=rel, filename=fn, parent_post_id=tid, exif=exif)
        )
    return by_post


def _build_profile(account: dict, profile: dict) -> AccountProfile:
    desc = (profile or {}).get("description") or {}
    return AccountProfile(
        platform=Platform.TWITTER,
        handle=(account or {}).get("username"),
        display_name=(account or {}).get("accountDisplayName"),
        bio=desc.get("bio") or None,
        location_field=desc.get("location") or None,
        website=desc.get("website") or (profile or {}).get("website") or None,
        created_at=_parse_date((account or {}).get("createdAt")),
    )


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    # classic tweet format: "Tue Mar 14 13:45:22 +0000 2023"
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        pass
    try:  # account/profile ISO format: "2013-03-14T12:34:56.000Z"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
