# Threat model

## The threat this tool addresses

A language model, given a few hundred of your ordinary public posts, can infer
sensitive attributes — home area, employer, age, routine, relationships — and
link a pseudonymous account to your real identity. The danger is **aggregation**:
each post is individually harmless, but together they form a *mosaic* that narrows
you down. Researchers have demonstrated LLM attribute-inference from public
Reddit-style text at high accuracy (Staab et al., *Beyond Memorization*, and
subsequent work). Most people have no idea their own history is this legible —
self-reported awareness is in the single digits.

`exposurecheck` runs that adversarial reading on **your own export** so you can fix
the worst contributors before someone hostile does the same thing to you.

## Who this is for

- People with a pseudonymous account they want to keep separate from their legal
  identity (activists, journalists' sources, abuse survivors, dissidents, ordinary
  people who simply don't want to be doxxed).
- Anyone curious how much their public posting reveals in aggregate.

## In scope (what it analyses)

- **Text mosaic** across your Reddit comments/submissions and your tweets.
- **Metadata layer** (especially on X, where it dominates): self-set location
  field, bio, outbound links, image **EXIF/GPS**, device make/model, and
  **posting-time concentration** (which discloses your timezone/active window).
- Both platforms' **public** content only.

## Out of scope (what it does NOT cover)

Treating a clean report as "safe" would be a mistake. The following are real
re-identification vectors this tool does **not** assess:

- **Cross-service correlation** — matching this account to others by timing,
  metadata or content across platforms you didn't export.
- **Stylometry** — authorship attribution from writing style alone.
- **Social graph** — who you follow/reply to, and who replies to you, is itself
  identifying; we surface mention hints but do not analyse the graph.
- **Private data** — DMs, votes, drafts, deleted-but-archived content. Export
  excludes most of these by design; archives/caches may still hold them.
- **The open world** — findings are **closed-set**: limited to the export you
  provided. An adversary combines your posts with data brokers, breaches, voter
  rolls and public records you can't see.

A low score means "this export contributes less obvious signal", **not** "you are
anonymous". `exposurecheck` reduces risk; it does not certify safety.

## Trust assumptions

- **No operator trust required.** The author holds no keys, no servers, no copy
  of your data. The tool does not phone home.
- **Local backend = no egress.** With `--backend local`, nothing leaves your
  machine.
- **Cloud backend = you trust your chosen provider** with the posts you send.
  See the conditional warning in the README and `docs/ABUSE-EVAL.md`: for a
  strictly-anonymous account audited through a real-name AI account, the provider
  itself becomes a deanonymization vector.
- **Minimal trusted base.** Core + backends are Python standard library only.

## Design choices that follow from the model

- **Recall-preserving** prefilter: only truly empty/boilerplate posts are dropped,
  because the mosaic is built from weak signals.
- **No-dossier** output: the tool refuses to synthesize and store a resolved
  profile of you — that artifact would itself be a new exposure. Resolved values
  appear only when you click through to your own post, in-session.
- **Generalise-first** remediation, never auto-delete — and a standing reminder
  that deletion ≠ erasure (archives, caches, screenshots persist).
