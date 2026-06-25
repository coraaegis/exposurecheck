# ExposureCheck

**Audit your own social-media history for re-identification risk — before someone
else does it to you.**

Modern language models can read a few hundred of your ordinary public posts and
infer where you live, where you work, your routine, your family, and link a
pseudonymous account back to your real name — not from one careless post, but
from the *mosaic* of many individually-innocuous ones. Researchers have shown
this works at scale and with unsettling accuracy. `exposurecheck` runs that same
adversarial reading **on your own export, on your own terms**, and shows you
which of *your* posts to generalise or edit.

It is **local-first**, produces **no dossier**, and never writes a profile of you
to disk.

📖 Plain-language explainer of the threat: **https://cypherpunkguide.com** (the
companion article — read it first if "mosaic re-identification" is new to you).

---

## What it does

- Parses your **Reddit** GDPR export and your **X / Twitter** export (directory or `.zip`).
- Runs a **recall-preserving cascade**: a cheap pass ranks every post, an
  expensive pass reads the high-priority ones, and weak signals are *kept* — the
  mosaic is built from weak signals, so throwing them away would be false comfort.
- Extracts the **metadata layer** deterministically (this is where X leaks most):
  the self-set location field, outbound links, image **EXIF/GPS**, device model,
  and posting-time concentration that betrays your timezone.
- Reports **category risk cards** (Location, Employer, Family, Schedule,
  Finances, Account-linkage, …) ranked by **risk contribution**, each with masked
  examples and concrete, *generalise-first* remediation.

## What it deliberately does **not** do

- ❌ No dossier. It never prints "you live in X / work at Y / your name is Z".
  Cards show **masked** snippets; the resolved value only ever appears when *you*
  click through to *your own* original post, **in-session, never saved**.
- ❌ No export of findings. ❌ No scraping (export input only). ❌ No posting/
  deletion on your behalf. ❌ No analysing anyone else's history.
- ❌ It does not make you anonymous. It **reduces** risk. "Low" is not "safe".

## Bring your own model — cloud **or** local

The inference runs on a backend **you** choose:

| backend | what it is | data leaves your machine? |
|---|---|---|
| `local` | a local Ollama (or llama.cpp/LM Studio) model | **no** |
| `cloud` | any OpenAI-compatible endpoint, your own key | **yes** |
| `heuristic` | offline regex stub, **near-zero recall** | no — *dev/CI only, not an audit* |

### ⚠️ The one cloud caveat that actually matters

If the account you are auditing is a **pseudonymous** one you keep separate from
your real identity, **and** your AI/cloud account is registered under your real
name or paid with a real-name method, then sending your history to the cloud lets
the provider link *real identity ↔ anonymous account* on their side (subpoena,
breach, insider). That is the exact deanonymization this tool exists to prevent.

So: **auditing a strictly-anonymous account → use `--backend local`** (or a cloud
account opened and paid for anonymously). Auditing your real-name / public
account → cloud is fine. The CLI states this and requires acknowledgement when it
applies. We never force local (that would shrink the audience to nobody); we make
the trade-off explicit.

---

## Install

Core (parsing, EXIF, cascade, **and** the cloud/local HTTP backends) is **Python
standard library only** — no third-party code touches your export.

```bash
git clone <repo>
cd exposurecheck
pip install -e .          # or just run `python -m exposurecheck`
```

## Usage

Get your data first:
- Reddit → *Settings → Privacy → Request a copy of your data* (the `.zip`).
- X → *Settings → Your account → Download an archive of your data*.

```bash
# Local model — nothing leaves your machine (recommended for anonymous accounts)
exposurecheck audit \
  --reddit ./reddit_export.zip \
  --twitter ./twitter_export \
  --backend local --expensive-model llama3.1 \
  --i-own-this-data

# Cloud (bring your own key; set it in the ENV, never on the command line)
export OPENAI_API_KEY=sk-...
exposurecheck audit --twitter ./twitter_export --backend cloud --i-own-this-data

# See your own posts behind a category (in-session, nothing is saved)
exposurecheck audit --reddit ./reddit_export --backend local -i --i-own-this-data
```

The API key is read from an environment variable on purpose — command-line args
leak into shell history and process listings.

## Cost (cloud)

Roughly **$0.59 per profile** for ~125 posts on a GPT-4-class model; a real
1–3k-post history lands around **$4–15**, trimmed by the recall-preserving
pre-filter. Local models are free (lower accuracy — the tool warns you).

## How it works

```
export ─▶ parse ─▶ prefilter (drop only TRUE-empty) ─┬─▶ deterministic: profile + EXIF + timing ─┐
                                                      └─▶ cascade: cheap route ─▶ expensive read ─┤
                                                                                                  ▼
                                          risk-contribution scoring ─▶ category cards ─▶ no-dossier report
```

See [`docs/THREAT-MODEL.md`](docs/THREAT-MODEL.md) for what is and isn't in scope,
and [`docs/ABUSE-EVAL.md`](docs/ABUSE-EVAL.md) for the dual-use safeguards and the
pre-release abuse evaluation.

## Status

`v0.1` alpha — Reddit + X, EXIF/GPS, the full cascade and the no-dossier report
are working end-to-end. Roadmap: real-corpus recall/false-positive evaluation
(SynthPAI), more platforms (Mastodon), single-post / pre-post checks.

## Security & contact

Found a privacy or safety flaw? See [`SECURITY.md`](SECURITY.md). Reach the author
at `cora@cypherpunkguide.com` (PGP via WKD: `gpg --locate-keys cora@cypherpunkguide.com`).

## License

License not finalised — see [`LICENSE`](LICENSE). Built by **Cora Aegis**
([cypherpunkguide.com](https://cypherpunkguide.com)).
