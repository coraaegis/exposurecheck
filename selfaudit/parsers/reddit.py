"""Parse a Reddit GDPR data export (the .zip you get from reddit.com/settings/data-request).

Reads ``comments.csv`` and ``posts.csv``. Reddit exports contain no images, so
there is no EXIF layer here — the leakage surface is text + subreddit + timing.
Robust to column variations via DictReader and ``.get()``.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from ..models import Export, Platform, Post
from ._source import ExportSource
from ._util import extract_urls


def parse_reddit(path: str) -> Export:
    with ExportSource(path) as src:
        posts: list[Post] = []
        comments_csv = src.read_text("comments.csv")
        if comments_csv:
            posts.extend(_parse_comments(comments_csv))
        posts_csv = src.read_text("posts.csv")
        if posts_csv:
            posts.extend(_parse_posts(posts_csv))
    return Export(platform=Platform.REDDIT, posts=posts, profile=None)


def _parse_comments(text: str) -> list[Post]:
    out: list[Post] = []
    for row in csv.DictReader(io.StringIO(text)):
        body = (row.get("body") or "").strip()
        pid = (row.get("id") or "").strip()
        if not pid and not body:
            continue
        out.append(Post(
            platform=Platform.REDDIT,
            post_id=pid or f"c_{len(out)}",
            text=body,
            created_at=_parse_date(row.get("date")),
            raw_created_at=(row.get("date") or "").strip() or None,
            permalink=(row.get("permalink") or "").strip() or None,
            community=(row.get("subreddit") or "").strip() or None,
            parent_id=(row.get("parent") or "").strip() or None,
            thread_link=(row.get("link") or "").strip() or None,
            urls=extract_urls(body),
            kind="comment",
        ))
    return out


def _parse_posts(text: str) -> list[Post]:
    out: list[Post] = []
    for row in csv.DictReader(io.StringIO(text)):
        title = (row.get("title") or "").strip()
        body = (row.get("body") or "").strip()
        link = (row.get("url") or "").strip()
        combined = "\n".join(t for t in (title, body) if t)
        pid = (row.get("id") or "").strip()
        if not pid and not combined:
            continue
        urls = extract_urls(combined)
        if link and link not in urls:
            urls.append(link)
        out.append(Post(
            platform=Platform.REDDIT,
            post_id=pid or f"p_{len(out)}",
            text=combined,
            created_at=_parse_date(row.get("date")),
            raw_created_at=(row.get("date") or "").strip() or None,
            permalink=(row.get("permalink") or "").strip() or None,
            community=(row.get("subreddit") or "").strip() or None,
            urls=urls,
            kind="submission",
        ))
    return out


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    tz = None
    if s.endswith(" UTC"):
        s, tz = s[:-4].strip(), timezone.utc
    dt: Optional[datetime] = None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if tz is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt
