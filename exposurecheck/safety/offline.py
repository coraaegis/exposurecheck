"""Enforce a no-off-machine-egress guarantee for ``--offline`` runs.

Hard-blocks any socket connection to a non-loopback (off-machine) address, so a
local or heuristic audit can be *proven* — and tested — never to phone home.
Loopback is allowed, so a local Ollama backend on 127.0.0.1 still works; that
traffic never leaves the machine. stdlib-only.
"""

from __future__ import annotations

import socket


class NetworkEgressBlocked(RuntimeError):
    """Raised when ``--offline`` blocks a connection to an off-machine address."""


def _is_loopback(host: object) -> bool:
    if host is None:
        return False
    h = str(host)
    return h in ("localhost", "::1", "::ffff:127.0.0.1") or h.startswith("127.")


def enforce_no_egress() -> None:
    """Monkeypatch socket ``connect`` / ``connect_ex`` to refuse any non-loopback
    target. Idempotent and stdlib-only. Loopback (on-machine, e.g. a local Ollama)
    is allowed; everything else raises :class:`NetworkEgressBlocked` before any
    bytes leave the machine.
    """
    if getattr(socket.socket.connect, "_ec_guarded", False):
        return

    _orig_connect = socket.socket.connect
    _orig_connect_ex = socket.socket.connect_ex

    def _host_of(address: object) -> object:
        return address[0] if isinstance(address, tuple) else address

    def connect(self, address, *args, **kwargs):
        host = _host_of(address)
        if not _is_loopback(host):
            raise NetworkEgressBlocked(
                f"--offline: blocked a network connection to {host!r}. Only "
                "loopback (on-machine, e.g. a local Ollama) is permitted offline."
            )
        return _orig_connect(self, address, *args, **kwargs)

    def connect_ex(self, address, *args, **kwargs):
        host = _host_of(address)
        if not _is_loopback(host):
            raise NetworkEgressBlocked(
                f"--offline: blocked a network connection to {host!r}."
            )
        return _orig_connect_ex(self, address, *args, **kwargs)

    connect._ec_guarded = True       # type: ignore[attr-defined]
    connect_ex._ec_guarded = True    # type: ignore[attr-defined]
    socket.socket.connect = connect       # type: ignore[assignment]
    socket.socket.connect_ex = connect_ex  # type: ignore[assignment]
