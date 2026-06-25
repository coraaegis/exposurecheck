"""Backend contract for the leak-inference cascade.

A backend answers two questions about the user's OWN posts:

  route(posts)   -> a 0..1 priority per post (cheap tier). Lower priority never
                    means "dropped" — it only means "analyze later / sample less".
  extract(batch) -> structured leak inferences for a small batch (expensive tier).

Backends never return resolved personal values: an inference carries a category,
a confidence, a MASKED snippet and a reference back to the user's own post.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ..models import Confidence, Platform, Post, RiskCategory, Source


@dataclass
class RawInference:
    """One leak signal, pre-aggregation. Holds a reference + masked text only."""
    category: RiskCategory
    confidence: Confidence
    masked_snippet: str
    evidence_type: str
    source: Source = Source.TEXT
    post_id: Optional[str] = None
    permalink: Optional[str] = None
    platform: Optional[Platform] = None   # namespaces post_id across mixed exports
    rationale: str = ""


class Backend(ABC):
    name: str = "base"
    is_local: bool = False
    #: True if running this backend sends the user's posts off their machine.
    #: Drives the conditional cloud-deanonymization warning.
    sends_data_offsite: bool = False

    @abstractmethod
    def route(self, posts: list[Post]) -> list[float]:
        ...

    @abstractmethod
    def extract(self, batch: list[Post]) -> list[RawInference]:
        ...

    def describe(self) -> str:
        return self.name
