# Changelog

All notable changes to this skill. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.5.0] - 2026-10-21

### Changed
- **HyperFrames first.** Motion design and rendering go to HyperFrames whenever it is reachable, because its skills carry a far deeper craft than this skill's
  own template (the faceless output of 1.4 was judged plain next to it). `SKILL.md` has a "Motion design: HyperFrames first" section;
  `references/19-hyperframes.md` gives the verified ways to get it (the local skills for agents with a filesystem, the hosted MCP and its guide for chat
  clients, and the fact that the hosted MCP refuses compose and render from CLI agents), the workflow per kind of video, and the hand-off. The skill references
  HyperFrames and never copies its skills. The built-in route is now the stated fallback.
- `beatmap_to_brief.py` writes each beat's `scene` as a design ask with its seconds, and `--host-video` makes the brief a `talking-head-recut` over the host's
  existing footage (its own audio stays the master clock). `capability_probe.py` reports whether HyperFrames is reachable and how to get it.
- The README plays the demo as an animated WebP (GitHub does not render a video tag from the repo, nor preview the mp4), with a download link for the sound.

## [1.4.0] - 2026-10-21

Found by two independent trials in which fresh agents used the skill, with no paid tools, to make a heat-pump explainer and a Spanish
article video. Both succeeded, scored it 3 to 4 out of 5 on autonomy and reliability, and wrote down 50 frictions; this release fixes them.

A second round of the same two trials, on this release, needed about 20 tool calls each (down from 53 and 52), asked no questions, wrote no tooling of
their own, and passed QC; they scored autonomy 5 and script reliability 4 to 5, and output quality 2.5 to 3 ("clean but plain"). The second pass below
answers their notes: a design upgrade of the faceless template (a 26-icon set, a looping `cycle` scene, dots travelling along flows and loops, drifting
background light, content centred in the space it has, stat count-ups that land on the spoken word), the layout check folded into the build
verdict, the recogniser and voice recorded in provenance automatically, a warning for a beat that starts empty, default number words per
language, a starter beat map, and a scan skip that says why.

### Added
- **Faceless route in one command.** `scripts/build_video.py` (look, word alignment, frames, mix, encode, captions, QC) over
  `templates/faceless/index.html`, with eight scene types (`kinetic`, `stat`, `steps`, `flow`, `compare`, `bars`, `terminal`, `quote`) specified
  per beat in the beat map; text is measured and fitted inside the safe box, a slow reframe and a moving highlight keep long beats alive, and
  there are no flash transitions. Example: `examples/faceless-money-guard.json`.
- `speech_align.py spans` (word times and beat spans for any voice-over, with beat starts snapped to the real pauses; English and Spanish
  numbers), `captions.py` (SRT and VTT), `voice_render.py` (best local voice by language, fitted length), `encode_master.py`,
  `layout_check.py` (Q1, Q4 and Q5 from the DOM).
- `cost_plan.py init --free` (the zero-spend path), claim `confidence: "user"` and `verified: false`, `provenance.py --draft/--upgrade`,
  `qc_master.py --waive CHECK --why REASON`, `mix_audio.py --style`, a `looks` list per format, and font resolution to same-class system stacks.
- A fast path at the top of `SKILL.md` and a rule for each default that used to be a question (offline first, the voice's locale, a draft
  voice as a valid end state, accepted defects, unverified sources).

### Changed
- `qc_master.py`: pacing is read in sliding windows with two measures (whole-frame change and active area) so small moving elements count;
  dark brand backgrounds are no longer reported as black frames.
- `voice_check.py` reads the language from the beat map, never uses an English-only model on another language, and returns a `rank`.
- `reference_scan.py` makes one attempt inside a time budget and exits 3 with a reason when a site refuses, instead of printing success.
- `style_lock.py pick` respects the format's allowed looks; `capability_probe.py` and `textscript.py` print short summaries; `contact_sheet.py` leads with the
  hook frame and tints the danger bands lightly; the determinism check tolerates anti-aliasing noise but stays strict between fresh renders.
- The remaining "ask the user" passages in the references now say what to decide instead.

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
