"""Per-category knowledge: how sensitive it is, why it's risky, how to reduce it.

All wording is GENERIC by design — it explains the *kind* of leak, never the
user's resolved value. The same templates feed the risk card and the
remediation advice.
"""

from __future__ import annotations

from ..models import RiskCategory

# How identifying / dangerous this category is if reconstructed (0..1).
SENSITIVITY: dict[RiskCategory, float] = {
    RiskCategory.LOCATION: 1.0,
    RiskCategory.REAL_NAME: 1.0,
    RiskCategory.IDENTITY_LINK: 0.9,
    RiskCategory.EMPLOYER: 0.8,
    RiskCategory.FAMILY: 0.8,
    RiskCategory.HEALTH: 0.75,
    RiskCategory.SCHEDULE: 0.7,
    RiskCategory.FINANCE: 0.7,
    RiskCategory.AGE_DOB: 0.6,
    RiskCategory.EDUCATION: 0.6,
    RiskCategory.RELATIONSHIPS: 0.5,
    RiskCategory.POLITICS_RELIGION: 0.5,
}

RATIONALES: dict[RiskCategory, str] = {
    RiskCategory.LOCATION:
        "Repeated place, commute and neighbourhood clues across many posts can narrow "
        "your home area far more than any single post suggests.",
    RiskCategory.EMPLOYER:
        "Role, team size, tech-stack and office clues combine to identify a specific "
        "employer, and often you as its only person matching them.",
    RiskCategory.EDUCATION:
        "School, campus and graduation-year mentions narrow you to a small cohort.",
    RiskCategory.FAMILY:
        "References to family members, their ages and their schools expand your "
        "exposure to people who did not choose to be public.",
    RiskCategory.AGE_DOB:
        "Age and birthday clues are a strong join key against other public records.",
    RiskCategory.HEALTH:
        "Health disclosures are sensitive on their own and can anchor a re-identification.",
    RiskCategory.FINANCE:
        "Stated holdings, income or wallet hints raise both targeting and physical risk.",
    RiskCategory.REAL_NAME:
        "Any slip of a real name, or a name embedded in a link/handle, collapses "
        "pseudonymity directly.",
    RiskCategory.SCHEDULE:
        "Posting-time concentration and routine mentions reveal your timezone and daily "
        "rhythm — useful for both correlation and physical timing.",
    RiskCategory.RELATIONSHIPS:
        "Named friends/partners and the reply graph let an analyst pivot through people "
        "who already know who you are.",
    RiskCategory.POLITICS_RELIGION:
        "Affiliation clues narrow the population and raise targeting risk in some "
        "jurisdictions.",
    RiskCategory.IDENTITY_LINK:
        "Outbound links, reused handles and device fingerprints stitch this pseudonymous "
        "account to your other identities.",
}

REMEDIATION: dict[RiskCategory, list[str]] = {
    RiskCategory.LOCATION: [
        "Generalise specifics — region not neighbourhood, 'a coastal city' not the exact route.",
        "Strip image EXIF/GPS before posting; re-check older media.",
        "Clear or coarsen any self-set profile location field.",
    ],
    RiskCategory.EMPLOYER: [
        "Drop the distinctive combination (role + team size + stack + office location).",
        "Avoid 'we're hiring / DM me' posts that tie you to a named org.",
    ],
    RiskCategory.EDUCATION: [
        "Generalise school/campus and avoid graduation-year specifics.",
    ],
    RiskCategory.FAMILY: [
        "Remove family members' ages, schools and routines.",
        "Consider that relatives did not consent to being identifiable.",
    ],
    RiskCategory.AGE_DOB: [
        "Avoid exact age / birthday / 'M34'-style markers.",
    ],
    RiskCategory.HEALTH: [
        "Generalise or remove specific conditions, providers and dates.",
    ],
    RiskCategory.FINANCE: [
        "Avoid stating exact holdings, income or wallet identifiers.",
    ],
    RiskCategory.REAL_NAME: [
        "Remove any post or link that exposes a real name; check link previews and handles.",
    ],
    RiskCategory.SCHEDULE: [
        "Vary posting times; avoid naming fixed, repeated daily slots (the same commute or run each day).",
        "Remember posting-time concentration alone discloses your timezone.",
    ],
    RiskCategory.RELATIONSHIPS: [
        "Avoid naming friends/partners; be aware the reply graph is itself a signal.",
    ],
    RiskCategory.POLITICS_RELIGION: [
        "Consider whether affiliation clues are worth the narrowing they cause.",
    ],
    RiskCategory.IDENTITY_LINK: [
        "Remove outbound links to personal sites; don't reuse this handle elsewhere.",
        "Strip device make/model from image EXIF.",
    ],
}

# Score banding -> level label
_HIGH = 67
_MEDIUM = 34


def level_for(score: float) -> str:
    if score >= _HIGH:
        return "High"
    if score >= _MEDIUM:
        return "Medium"
    return "Low"
