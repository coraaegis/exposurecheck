"""Core data model.

Design invariant — NO-DOSSIER:
    No type in this module stores a *resolved* personal value (e.g. "lives in
    Brooklyn", "works at Acme", "real name is Jane Doe"). The pipeline only ever
    records:
      - references to the user's OWN posts (post_id / permalink), so the tool can
        show them their original text on demand, and
      - MASKED snippets and GENERIC rationales describing *why* a category is at risk.
    This is enforced by convention here and checked in tests/test_no_dossier.py.
    The point of the tool is to reduce the user's exposure, not to manufacture a
    dossier that itself becomes a new exposure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"  # a.k.a. X


# --------------------------------------------------------------------------- #
#  Parsed export layer (deterministic — no LLM involved)
# --------------------------------------------------------------------------- #

@dataclass
class ExifData:
    """Privacy-relevant EXIF extracted from an attached image."""
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    datetime_original: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def has_location(self) -> bool:
        return self.gps_lat is not None and self.gps_lon is not None


@dataclass
class MediaRef:
    path: str            # path inside the export
    filename: str
    parent_post_id: Optional[str] = None
    exif: Optional[ExifData] = None


@dataclass
class Post:
    """A single user-authored item: a Reddit comment/submission or a tweet.

    Weak signals are deliberately preserved — short posts, bare URLs and
    "generic" text are NOT discarded, because the mosaic effect is built from
    the aggregate of weak signals.
    """
    platform: Platform
    post_id: str
    text: str                              # body / full_text; may be "" for media-only
    created_at: Optional[datetime] = None  # None if unparseable
    permalink: Optional[str] = None        # link back to the user's OWN post
    community: Optional[str] = None         # subreddit; X has none
    parent_id: Optional[str] = None
    thread_link: Optional[str] = None
    urls: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    media: list[MediaRef] = field(default_factory=list)
    raw_created_at: Optional[str] = None    # original string, for auditing the parse
    kind: str = "post"                      # "comment" | "submission" | "tweet"


@dataclass
class AccountProfile:
    """Static profile metadata. On X these fields drive most of the leakage."""
    platform: Platform
    handle: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    location_field: Optional[str] = None    # self-set "location" string
    website: Optional[str] = None
    created_at: Optional[datetime] = None
    pinned_post_id: Optional[str] = None
    follower_hint: Optional[int] = None


@dataclass
class Export:
    """Everything parsed out of one platform's export."""
    platform: Platform
    posts: list[Post] = field(default_factory=list)
    profile: Optional[AccountProfile] = None
    media: list[MediaRef] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.posts)


# --------------------------------------------------------------------------- #
#  Inference layer (LLM-assisted) — still no resolved values stored
# --------------------------------------------------------------------------- #

class RiskCategory(str, Enum):
    LOCATION = "location"
    EMPLOYER = "employer"
    EDUCATION = "education"
    FAMILY = "family"
    AGE_DOB = "age_dob"
    HEALTH = "health"
    FINANCE = "finance"            # holdings, income, wallet hints
    REAL_NAME = "real_name"        # name leakage
    SCHEDULE = "schedule"          # routine / timezone / commute from timing
    RELATIONSHIPS = "relationships"
    POLITICS_RELIGION = "politics_religion"
    IDENTITY_LINK = "identity_link"  # cross-account / cross-platform linkage

    @property
    def label(self) -> str:
        return {
            "location": "Location",
            "employer": "Employer",
            "education": "Education",
            "family": "Family",
            "age_dob": "Age / DOB",
            "health": "Health",
            "finance": "Finances",
            "real_name": "Real name",
            "schedule": "Schedule / routine",
            "relationships": "Relationships",
            "politics_religion": "Politics / religion",
            "identity_link": "Account linkage",
        }[self.value]


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def weight(self) -> float:
        return {"low": 0.34, "medium": 0.67, "high": 1.0}[self.value]


class Source(str, Enum):
    TEXT = "text"
    METADATA = "metadata"      # bio / location field / pinned
    EXIF = "exif"              # image GPS / device
    TIMING = "timing"          # created_at patterns
    GRAPH = "graph"            # mentions / reply network


@dataclass
class Evidence:
    """One contributing signal. Holds a REFERENCE + a MASKED snippet only.

    `masked_snippet` must already be redacted, e.g. "[LOCAL_EVENT] near
    [NEIGHBORHOOD]". It is never the resolved value.
    """
    masked_snippet: str
    evidence_type: str                 # human label: "local event", "EXIF GPS", "bio field"
    source: Source = Source.TEXT
    post_id: Optional[str] = None
    permalink: Optional[str] = None    # so the user can click through to their own post
    created_at: Optional[datetime] = None


@dataclass
class Finding:
    """An inference in ONE category, backed by evidence. No resolved value."""
    category: RiskCategory
    confidence: Confidence
    rationale: str = ""                # generic WHY ("local events + commute clues over
                                       #  19 months can narrow to a neighborhood")
    evidence: list[Evidence] = field(default_factory=list)
    # filled by risk.scoring
    risk_score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)


@dataclass
class RiskCard:
    """Category-level, user-facing output card (the no-dossier surface)."""
    category: RiskCategory
    level: str                         # "High" | "Medium" | "Low"
    risk_score: float
    summary: str                       # "28 posts / 4 communities / 19 months of area mentions"
    rationale: str = ""                # generic WHY this category is at risk
    evidence_types: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    to_review_count: int = 0
    remediation: list[str] = field(default_factory=list)


@dataclass
class AuditResult:
    cards: list[RiskCard] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    backend_name: str = ""
    post_count: int = 0
    candidate_count: int = 0           # posts routed to the expensive tier
    platforms: list[Platform] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
