"""HTTP transports for LLM backends, standard-library only (urllib, no requests).

Two shapes, both selected by the user:
  CloudTransport  - any OpenAI-compatible /chat/completions endpoint (OpenAI,
                    OpenRouter, or a self-hosted gateway). Bring your own key.
  LocalTransport  - a local Ollama server (/api/chat). No network egress.

A local OpenAI-compatible server (llama.cpp, LM Studio) can also be driven by
CloudTransport pointed at http://localhost:... with any placeholder key.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Optional


class TransportError(RuntimeError):
    pass


class Transport(ABC):
    name: str = "transport"
    is_local: bool = False
    sends_data_offsite: bool = False

    @abstractmethod
    def complete(self, system: str, user: str, model: str, *,
                 max_tokens: int = 800, temperature: float = 0.0) -> str:
        ...


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500] if e.fp else ""
        raise TransportError(f"HTTP {e.code} from {url}: {detail}") from e
    except urllib.error.URLError as e:
        raise TransportError(f"cannot reach {url}: {e.reason}") from e


class CloudTransport(Transport):
    is_local = False
    sends_data_offsite = True

    def __init__(self, api_key: str, *, base_url: str = "https://api.openai.com/v1",
                 timeout: float = 60.0, name: Optional[str] = None):
        if not api_key:
            raise TransportError("cloud backend needs an API key (set it via env, never on the CLI)")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.name = name or f"cloud({self.base_url})"

    def complete(self, system, user, model, *, max_tokens=800, temperature=0.0) -> str:
        data = _post_json(
            f"{self.base_url}/chat/completions",
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            {"Authorization": f"Bearer {self.api_key}"},
            self.timeout,
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise TransportError(f"unexpected response shape: {str(data)[:300]}") from e


class LocalTransport(Transport):
    is_local = True
    sends_data_offsite = False

    def __init__(self, *, base_url: str = "http://localhost:11434",
                 timeout: float = 120.0, name: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.name = name or f"local({self.base_url})"

    def complete(self, system, user, model, *, max_tokens=800, temperature=0.0) -> str:
        data = _post_json(
            f"{self.base_url}/api/chat",
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            {},
            self.timeout,
        )
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise TransportError(f"unexpected Ollama response: {str(data)[:300]}") from e
