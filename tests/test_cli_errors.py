"""A failure must never echo post content to stderr by default.

A privacy tool's own crash output is part of its attack surface (stderr ->
scrollback -> swap -> shared paste). main() suppresses raw tracebacks and
content-bearing exception messages unless --debug is given.
"""

import pytest

import exposurecheck.cli as cli


def test_uncaught_error_is_sanitized(monkeypatch, capsys):
    def boom(_args):
        raise ValueError("LEAKED_POST_CONTENT lives at 123 Main St")

    monkeypatch.setattr(cli, "cmd_audit", boom)
    rc = cli.main(["audit", "--twitter", "x", "--i-own-this-data"])
    err = capsys.readouterr().err
    assert rc == 7
    assert "LEAKED_POST_CONTENT" not in err   # the post content must not leak
    assert "ValueError" in err                # the exception TYPE is fine to show


def test_debug_reraises_for_full_traceback(monkeypatch):
    def boom(_args):
        raise ValueError("LEAKED_POST_CONTENT")

    monkeypatch.setattr(cli, "cmd_audit", boom)
    with pytest.raises(ValueError):
        cli.main(["audit", "--twitter", "x", "--i-own-this-data", "--debug"])
