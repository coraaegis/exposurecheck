"""Export parsers. Deterministic, no LLM, no network."""

from __future__ import annotations

from ..models import Export, Platform
from .reddit import parse_reddit
from .twitter import parse_twitter

__all__ = ["parse_reddit", "parse_twitter", "parse_export"]


def parse_export(path: str, platform: Platform) -> Export:
    if platform == Platform.REDDIT:
        return parse_reddit(path)
    if platform == Platform.TWITTER:
        return parse_twitter(path)
    raise ValueError(f"unsupported platform: {platform}")
