"""Pluggable inference backends and a small factory.

  heuristic  - offline regex stub (no key, low recall — dev/CI/demo only)
  cloud      - OpenAI-compatible endpoint, bring-your-own-key (sends data offsite)
  local      - local Ollama server (no network egress)
"""

from __future__ import annotations

from typing import Optional

from .base import Backend, RawInference
from .heuristic import HeuristicBackend
from .llm import LLMBackend
from .transports import CloudTransport, LocalTransport, TransportError

__all__ = [
    "Backend", "RawInference", "HeuristicBackend", "LLMBackend",
    "CloudTransport", "LocalTransport", "TransportError", "build_backend",
]


def build_backend(
    kind: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    cheap_model: Optional[str] = None,
    expensive_model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Backend:
    kind = (kind or "heuristic").lower()
    if kind == "heuristic":
        return HeuristicBackend()
    if kind == "cloud":
        transport = CloudTransport(
            api_key or "",
            base_url=base_url or "https://api.openai.com/v1",
            timeout=timeout or 60.0,
        )
        return LLMBackend(
            transport,
            cheap_model=cheap_model or "gpt-4o-mini",
            expensive_model=expensive_model or "gpt-4o",
        )
    if kind == "local":
        transport = LocalTransport(
            base_url=base_url or "http://localhost:11434",
            timeout=timeout or 120.0,
        )
        model = expensive_model or cheap_model or "llama3.1"
        return LLMBackend(
            transport,
            cheap_model=cheap_model or model,
            expensive_model=model,
        )
    raise ValueError(f"unknown backend: {kind!r} (use heuristic|cloud|local)")
