# Changelog

All notable changes to this skill. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.3.0] - 2026-10-21

### Added
- **Reference scan** (`scripts/reference_scan.py`, `references/18-reference-scan.md`): an automatic, optional look at 5 to 10 public reels on the
  topic before the format and hook are chosen. `find` reads YouTube Shorts through the hashtag Shorts tab; `add` takes TikTok and Instagram
  URLs from the agent's own web search; `analyze` measures each (length, cuts, average shot, loudness, hook text and type) in a temporary
  download that is deleted; `summarize` names the overused opener, the typical pace and length. Public pages only, walls are never bypassed,
  no personal data, technique not content. A `reference` role in `provenance.py` records that it ran.
- **Look picker** (`style_lock.py pick`): ranks the 14 identities by topic register, fixes the look when the format defines it, and spreads
  consecutive videos apart (recent looks and the same colour family are penalised). The skill had no rule against reusing one palette; now
  no look is a default and support assets (mascot, host backdrop) follow the video's look.

## [1.2.0] - 2026-10-21

### Changed
- **Autonomous by default.** The skill decides and records format, length, language, platforms, voice, music, look, tier and renderer
  instead of asking, and shows a decision record once at the end. It stops only for money with no authorisation, a real
  person's likeness or voice, a credential, or a permission the host denies (never worked around). A free plan needs no ledger.
  `ledger.py` keeps its gates by default; autonomy is the explicit `--autonomous` choice once the user has authorised a budget.
- **A quality bar.** Human presence by default for explainers and promos, a voice ladder where system voices are draft only,
  transitions that carry meaning (no flash, dip or decorative wipe), text at the QA sizes, never editing the picture to satisfy a metric.
- `qc_master.py` pacing now measures motion: a long shot fails only when nothing moves in it. Hard-cut counting alone had rewarded fake cuts.
- HyperFrames is an optional upgrade named in the final note, never a blocking question.

### Added
- **Model awareness.** `capability_probe.py` writes `ai_models`; `scripts/provenance.py` records which AI models and tools made what
  at the moment of use and prints the AI-use statement and a disclosure verdict; `references/17-ai-models-and-tools.md` covers discovery,
  route choice, the verified talking-host recipe, credits, consent and failures.
- `scripts/voice_check.py` (round-trip word error, pace and level; system voices marked draft), `scripts/host_assemble.py`
  (talking clips to a master track with word timings), `scripts/render_html.py` (parallel, determinism-checked HTML frames),
  `scripts/mix_audio.py` (master voice untouched, ducked bed, meaningful cues, loudness), `scripts/speech_align.py`.
- `examples/host-overlay-composition/` and `examples/host-broll-skill-demo.json`: the page and plan behind the demo reel.
- A demo reel made by the skill itself, with its plan, provenance and AI-use statement under `demo/`; a mascot and social preview under `assets/`.

### Fixed
- Credits-billed providers: guidance for measuring a price from the balance and keeping a credits ledger (`14-cost-scout.md`).

## [1.1.0] - 2026-10-20

### Added
- Packaged repository: `.skill` archive, plugin marketplace manifest, CI, packaging tool, docs.

### Fixed
- `fonts_covering` now skips the macOS `.LastResort` placeholder font. It claims every code point, so any text looked covered by an installed font.

### Skill content
- 15 formats, 21 story intents, 14 style identities, series support, cost scout and ledger, 16 reference documents, 14 scripts, 122 tests.
