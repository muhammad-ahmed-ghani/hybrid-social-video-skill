# Hybrid Social Video

[![CI](https://github.com/muhammad-ahmed-ghani/hybrid-social-video-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/muhammad-ahmed-ghani/hybrid-social-video-skill/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Skill version](https://img.shields.io/badge/skill-v1.1-informational)
![Format](https://img.shields.io/badge/Agent_Skills-compatible-success)

An [Agent Skill](https://agentskills.io) that directs 9:16 social videos (Reels, TikTok, Shorts, 20 to 90 seconds), as one-offs or as an episodic series.

A hybrid video is not one tool's output. Every moment comes from the layer that cannot get it wrong:
code draws numbers, labels, diagrams and equations exactly and for free, AI invents atmosphere no camera could reach,
real or stock footage proves things, and a host gives a human reason to stay. This skill picks the story and format,
assigns layers, spends money last and only after approval, keeps a series looking like one show, and checks the result.

## What you get

- **15 formats in 5 families**, chosen from the story and what can be shown, not from a look the user likes.
- **A linted beat map** (`beatmap.json`) that every later step reads, with word budgets, hook checks and claim tracking.
- **Live pricing.** No price is hardcoded. A cost scout reads the environment and writes a dated pricebook.
- **Approval gates and a budget cap.** A ledger refuses a paid call until the plan is approved and the cap allows it.
- **Series memory.** Look, cast, voices and music stay locked while the situation changes each episode.
- **Layer routing.** Each layer is handed to the skill that owns it (HyperFrames, Manim, explainer-reel-skill), with a degradation ladder when one is missing.
- **QC.** Contact sheets, platform safe zones, loudness and caption checks before delivery.
- **Any language.** Counting, direction, fonts and speaking rate are read from the text and the voice.

### Formats

| Family | Formats |
|---|---|
| Code-native | `data-story`, `math-science-manim`, `kinetic-type-essay`, `diagram-mechanism`, `screen-demo`, `chat-dialogue` |
| Editorial | `vox-collage`, `map-evidence`, `archival-documentary`, `flat-vector-motion` |
| Presenter | `host-broll`, `talking-head-package` |
| Reporting | `news-brief` |
| Narrative | `comedy-sketch`, `cartoon-episode` |

### Tiers

| Tier | Layers | What drives the bill |
|---|---|---|
| R0 | code, stock, capture, real | nothing generative |
| R1 | R0 + AI stills, parallax and grain in code | number of stills |
| R2 | R1 + a few AI clips | seconds of clip |
| R3 | R2 + a talking host | host seconds |

## Install

### Option 1: the `.skill` file

Download [`dist/hybrid-social-video.skill`](dist/hybrid-social-video.skill) (a zip with the skill folder at its root).

**Claude Code**

```bash
unzip -o dist/hybrid-social-video.skill -d ~/.claude/skills/
```

**Claude.ai or Claude Desktop:** Settings, Capabilities, Skills, then upload the `.skill` file.

### Option 2: Claude Code plugin marketplace

```
/plugin marketplace add muhammad-ahmed-ghani/hybrid-social-video-skill
/plugin install hybrid-social-video@hybrid-social-video-marketplace
```

The repo is private, so your GitHub credentials must have access to it.

### Option 3: clone

```bash
git clone https://github.com/muhammad-ahmed-ghani/hybrid-social-video-skill.git
cp -R hybrid-social-video-skill/skills/hybrid-social-video ~/.claude/skills/
```

Start a new Claude Code session afterwards so the skill is picked up.

## Requirements

- `python3` (3.9+). The scripts use only the standard library.
- `ffmpeg` and `ffprobe` for assembly, QC and the animatic.
- `Pillow` for the contact sheet and animatic (`pip install pillow`).

Layer skills (HyperFrames, a Manim skill, explainer-reel-skill) and any image, video or voice tools are used when present.
`references/11-routing.md` explains how the skill degrades when one is missing.

## Usage

Ask in plain language. The skill triggers on requests like:

- "Make an explainer reel about how compound interest works."
- "Turn this article into a vertical video."
- "A Vox or 3Blue1Brown style short about the Eiffel Tower."
- "Start a comedy series, then write episode 3."

It fills in an intake card with defaults, builds the plan and cost card, and stops at each human gate for approval.
You receive `master.mp4`, the cost, the sources and a short note.

Not for: a single AI clip, an ad, a music video, or timeline editing.

## Repository layout

```
.
├── skills/hybrid-social-video/   the skill itself (what gets installed)
│   ├── SKILL.md                  entry point: rules, loop, gates
│   ├── references/               formats, beat map, style, sound, governance, QA, routing, series
│   ├── scripts/                  lint, cost plan, ledger, storyboard, animatic, QC, series (stdlib Python)
│   ├── data/                     formats, intents, identities, platforms (thresholds, no prices)
│   ├── examples/                 beat maps that lint clean
│   └── tests/                    pytest suite pinning the skill's invariants
├── dist/hybrid-social-video.skill   packaged skill, rebuilt by tools/package_skill.py
├── tools/package_skill.py        validate and pack
├── .claude-plugin/marketplace.json
├── .github/workflows/ci.yml      validate, test, check the .skill is current
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

## Development

```bash
pip install pytest pillow
python3 -m pytest -q skills/hybrid-social-video/tests/     # 122 tests; media tests need ffmpeg
python3 tools/package_skill.py                              # validate and rebuild dist/
```

CI fails if `dist/hybrid-social-video.skill` is out of date with the skill folder, so rebuild and commit it with any change to the skill.
See [CONTRIBUTING.md](CONTRIBUTING.md).

## Versioning

The skill version lives in `SKILL.md` frontmatter (`metadata.version`). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
