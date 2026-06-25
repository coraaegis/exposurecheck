"""Command-line interface.

    selfaudit audit --reddit ./reddit_export --twitter ./twitter_export \\
        --backend local --i-own-this-data

The API key for the cloud backend is read from an environment variable, never
from the command line (CLI args leak into shell history and process listings).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from . import __version__
from .audit import run_audit
from .backends import TransportError, build_backend
from .models import Platform
from .output import render_report, reveal_loop
from .parsers import parse_export
from .safety import cloud_warning_text, needs_cloud_ack, require_consent


def _eprint(msg: str = "") -> None:
    print(msg, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="selfaudit",
        description="Audit your own social-media export for re-identification (mosaic) risk. "
                    "Local-first, no-dossier, bring-your-own-LLM.",
    )
    p.add_argument("--version", action="version", version=f"selfaudit {__version__}")
    sub = p.add_subparsers(dest="command")

    a = sub.add_parser("audit", help="run an audit over one or more exports")
    a.add_argument("--reddit", metavar="PATH", help="Reddit GDPR export (dir or .zip)")
    a.add_argument("--twitter", metavar="PATH", help="X/Twitter export (dir or .zip)")
    a.add_argument("--backend", choices=["heuristic", "cloud", "local"], default="heuristic",
                   help="inference backend (default: heuristic = offline dev stub, low recall)")
    a.add_argument("--base-url", help="endpoint base URL (cloud: OpenAI-compatible; local: Ollama)")
    a.add_argument("--api-key-env", default="OPENAI_API_KEY",
                   help="env var holding the cloud API key (default: OPENAI_API_KEY)")
    a.add_argument("--cheap-model", help="cheap-tier model name")
    a.add_argument("--expensive-model", help="expensive-tier model name")
    a.add_argument("--anon-account", action="store_true",
                   help="the audited account is pseudonymous and kept separate from your real "
                        "identity (enables the cloud-deanonymization safeguard)")
    a.add_argument("--cloud-ack", action="store_true",
                   help="pre-acknowledge the cloud-deanonymization warning (non-interactive)")
    a.add_argument("--i-own-this-data", action="store_true",
                   help="attest you own the export being audited (non-interactive consent)")
    a.add_argument("--full", action="store_true",
                   help="analyze every kept post (no cost budget); default trims for cloud")
    a.add_argument("--max-candidates", type=int, default=None,
                   help="hard cap on posts sent to the expensive tier")
    a.add_argument("--batch-size", type=int, default=10, help="expensive-tier batch size")
    a.add_argument("-i", "--interactive", action="store_true",
                   help="after the report, reveal your own posts behind a category (nothing saved)")
    return p


def cmd_audit(args: argparse.Namespace) -> int:
    if not args.reddit and not args.twitter:
        _eprint("error: provide at least one of --reddit / --twitter")
        return 2

    if not require_consent(args.i_own_this_data, output_fn=_eprint):
        _eprint("Consent not given. Aborting.")
        return 3

    try:
        backend = build_backend(
            args.backend,
            api_key=os.environ.get(args.api_key_env) if args.backend == "cloud" else None,
            base_url=args.base_url,
            cheap_model=args.cheap_model,
            expensive_model=args.expensive_model,
        )
    except TransportError as e:
        _eprint(f"backend error: {e}")
        if args.backend == "cloud":
            _eprint(f"(set your key in ${args.api_key_env}; never pass it on the command line)")
        return 4

    # cloud safety flow
    if backend.sends_data_offsite:
        _eprint(cloud_warning_text())
        _eprint("")
        if needs_cloud_ack(backend, args.anon_account) and not args.cloud_ack:
            try:
                ans = input("Anonymous account via cloud AI. Type 'I accept the risk' to proceed: ")
            except (EOFError, KeyboardInterrupt):
                _eprint("")
                ans = ""
            if ans.strip().lower() not in ("i accept the risk", "yes"):
                _eprint("Not acknowledged. Use --backend local for a strictly-anonymous audit.")
                return 5

    if args.backend == "heuristic":
        _eprint("NOTE: heuristic backend is an OFFLINE STUB with near-zero recall. Use it to test "
                "the plumbing only; choose --backend local or cloud for a real audit.\n")

    exports = []
    if args.reddit:
        exports.append(parse_export(args.reddit, Platform.REDDIT))
    if args.twitter:
        exports.append(parse_export(args.twitter, Platform.TWITTER))

    if args.full:
        fraction = 1.0
    elif backend.sends_data_offsite:
        fraction = 0.6  # trim cost on cloud unless --full
    else:
        fraction = 1.0

    def progress(done: int, total: int) -> None:
        if total:
            _eprint(f"  analyzing {done}/{total} ...")

    result = run_audit(
        exports, backend,
        candidate_fraction=fraction,
        max_candidates=args.max_candidates,
        batch_size=args.batch_size,
        progress=progress,
    )

    print(render_report(result))

    if args.interactive:
        reveal_loop(result, exports)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    # make non-ASCII post text safe to print on any console
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "audit":
        return cmd_audit(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
