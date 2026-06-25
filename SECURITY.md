# Security & responsible disclosure

This is a privacy tool. A bug here can expose the very people it's meant to
protect, so security and privacy reports are taken seriously and welcomed.

## What to report

- Any way the **report surface** leaks a *resolved* personal value (a real
  place, name, employer, handle, or coordinates) instead of a masked reference.
- Any path that writes user data, findings, or a profile to disk unexpectedly.
- Any **network egress** when running `--backend local` (there should be none).
- Parser flaws that could crash on, or mishandle, a crafted export.
- Anything that weakens the dual-use guards in `docs/ABUSE-EVAL.md`.

## How to report

Email **cora@cypherpunkguide.com**, encrypted with PGP.

- Fetch the key via WKD: `gpg --locate-keys cora@cypherpunkguide.com`
- Key fingerprint: `<PASTE FINGERPRINT — verify against https://cypherpunkguide.com>`

Please give us a reasonable window to fix before public disclosure. We will
credit you (or keep you anonymous — your call). There is no paid bounty; this is
a small, non-commercial project.

## Good-faith safe harbor

We will not pursue or support action against researchers who:

- act in good faith, test only against **their own** accounts/exports,
- avoid privacy violations of third parties and avoid data destruction, and
- give us time to remediate before disclosing.

## Scope

The `selfaudit` codebase in this repository. The companion website
(cypherpunkguide.com) and unrelated infrastructure are out of scope here.
