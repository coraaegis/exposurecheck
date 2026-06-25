# Dual-use safeguards & pre-release abuse evaluation

A tool that reads a post history adversarially is inherently dual-use: the same
reading that helps you audit *yourself* could help someone profile *a target*.
We take that seriously. This document records the guards built into v1 and the
evaluation that must pass **before any public release**.

## Why bulk self-audit is higher-risk than single-post checks

Reading an entire history is exactly what an attacker wants. So the bulk tool
carries the strongest guards, not the weakest.

## Guards in v1 (implemented)

1. **Ownership-gated input.** Input is an account **export** (Reddit GDPR / X
   archive), which only the account owner can generate — not a scrape of an
   arbitrary handle. There is no scraping path in the tool.
2. **Consent attestation.** The run refuses to proceed without an ownership
   attestation (`--i-own-this-data` or an interactive phrase). Intentional
   friction; not a legal shield.
3. **Category-only, masked output.** The report is per-category risk cards with
   **masked** snippets. It never emits a resolved value ("lives in …", "works at
   …", "name is …").
4. **No dossier, no export.** The tool does not assemble or persist a unified
   profile, and has no "save findings" path. Resolved text is shown only by the
   user clicking through to their **own** post, in-session.
5. **No action surface.** No posting, no deletion, no following — nothing that
   could be weaponised against an account.
6. **Local-first.** A strictly-anonymous audit can run with zero network egress.

These guards are degrade-gracefully: even on the offline heuristic backend, the
output shape (masked, category-only, no export) is identical.

## The abuse-eval gate (MUST run before public release)

**Hypothesis to falsify:** "An adversary can use this tool, unchanged, to turn a
*consenting third party's* public export into an actionable attack list (resolved
identity, address, employer)."

**Procedure**
1. With explicit consent, run the tool over a volunteer's real export.
2. Inspect the output for any **resolved** personal value (not masked references).
3. Attempt, as a red-teamer, to recover resolved values from the report alone
   (without the in-session reveal). The no-dossier guarantee should make this
   impossible from the report surface.
4. Repeat with the cloud and local backends and with adversarially-worded prompts
   injected via post content (prompt-injection resistance of the masking layer).

**Pass condition:** the report surface yields **no** resolved identity value; the
only path to resolved text is the owner's explicit in-session click on their own
post. Any leak of a resolved value into a card, example, rationale or score
breakdown is a **fail**.

**On fail:** ship local-only, narrow scope (e.g. metadata-only), or hold release
until the masking layer is fixed.

## v1 self-assessment

- The masking layer is enforced **mechanically**, not by the model: masked
  snippets are generated from post metadata in `backends/_mask.py`, and the LLM is
  never asked for (nor trusted to produce) snippet/rationale text. Automated test
  `tests/test_no_dossier.py` asserts the report never echoes known resolved tokens
  from the fixtures, while in-session reveal does.
- **Residual risk:** the *user's own* in-session reveal naturally shows resolved
  text — that is the point, and it stays on their machine. A determined operator
  could fork the code to remove the guards; that is true of any open tool, and the
  guards raise the cost and remove the "batteries-included attack tool" framing.

## Status

> **The abuse-eval gate above has NOT yet been run.** v1 ships the guards; the
> consenting-third-party evaluation is a prerequisite for the first public
> release and for the companion article's "try it yourself" call to action.
