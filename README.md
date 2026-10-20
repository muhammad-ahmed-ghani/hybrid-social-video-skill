<h1 align="center"><img src="assets/mascot-small.png" height="72" align="absmiddle" alt="Slate, the mascot"> Hybrid Social Video</h1>

<p align="center">
An <a href="https://agentskills.io">Agent Skill</a> that directs 9:16 reels, TikToks and Shorts: a human host with code-drawn overlays,
AI imagery and video, stock or real footage, each beat given to the layer that can't get it wrong.<br>
It runs end to end without asking you questions, and it knows, and tells you, which AI models made what.
</p>

<p align="center">
<a href="https://github.com/muhammad-ahmed-ghani/hybrid-social-video-skill/actions/workflows/ci.yml"><img src="https://github.com/muhammad-ahmed-ghani/hybrid-social-video-skill/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
<img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT">
<img src="https://img.shields.io/badge/skill-v1.2-informational" alt="skill v1.2">
<img src="https://img.shields.io/badge/Agent_Skills-compatible-success" alt="Agent Skills compatible">
</p>

## See it work

<p align="center">
<a href="demo/hybrid-social-video-demo.mp4"><img src="demo/preview.gif" width="270" alt="Demo reel: a host explains the skill; click for the full 35 second video with sound"></a>
</p>

<p align="center"><a href="demo/hybrid-social-video-demo.mp4"><b>Watch the full 35 s reel with sound</b></a></p>

That reel was made by this skill from one sentence: *"create a video explaining that if you want social reels or explainer
videos, go to this repository and tell your agent to use it."* The agent chose the format, wrote and linted the plan, priced it,
generated a fictional presenter and one talking clip per beat, timed everything from the host's own words, drew the overlays in
code, mixed the sound, and passed QC. The host and his voice are AI-generated and labelled as such.
How it was made, model by model: [`demo/AI-USE.md`](demo/AI-USE.md) · the plan: [`demo/beatmap.json`](demo/beatmap.json).

## Use it in one line

Install it (below), then tell your agent:

> use hybrid-social-video to make a 35 second reel that explains how compound interest works

That is all. It decides the format, length, platforms, language, voice, look and renderer, writes each choice into the plan, and
shows you the decisions once, at the end. It stops to ask only for what exists nowhere but in your head: money with no
authorisation, a real person's likeness or voice, a credential. A plan that costs nothing never asks.

## What it does

- **Human first.** For explainers and promos the frame carries a person (a host, real or AI-generated and disclosed) with overlays
  drawn in code over them: the host full frame for the hook and the payoff, a bubble beside a diagram while it explains.
- **A voice people believe.** A ladder, best first: your own recording, host-native speech, a neural voice, and only then a system
  voice, which is marked draft. It auditions voices itself (`voice_check.py`) instead of asking you to listen.
- **The right layer for each beat.** Code draws numbers, labels and diagrams exactly; AI invents what no camera could reach; real
  or stock footage proves things. A model never renders a number.
- **It knows what it uses.** Tools and models are discovered (local models, MCP servers, credentials by name), pinned, and
  recorded as they are used in `provenance.json`; the delivery note carries the AI-use statement and a disclosure verdict.
- **15 formats in 5 families**, 21 story intents, 14 style identities, a linted beat map, series memory for shows.
- **Money stays safe.** Prices are read from the environment, never remembered; a ledger enforces a cap on every paid call; one
  respend per asset; a host that denies a spend is a boundary, not an obstacle.
- **A real quality bar.** No flash transitions, no editing the picture to please a metric, text at phone-readable sizes inside the
  platform safe box, loudness at -14 LUFS, and a look-like-a-viewer review before delivery.
- **Any language**, read from your request.

| Family | Formats |
|---|---|
| Code-native | `data-story`, `math-science-manim`, `kinetic-type-essay`, `diagram-mechanism`, `screen-demo`, `chat-dialogue` |
| Editorial | `vox-collage`, `map-evidence`, `archival-documentary`, `flat-vector-motion` |
| Presenter | `host-broll`, `talking-head-package` |
| Reporting | `news-brief` |
| Narrative | `comedy-sketch`, `cartoon-episode` |

| Tier | Layers | What drives the bill |
|---|---|---|
| R0 | code, stock, capture, real | nothing generative |
| R1 | R0 + AI stills, parallax and grain in code | number of stills |
| R2 | R1 + a few AI clips | seconds of clip |
| R3 | R2 + a talking host | host seconds |

## Install

**The `.skill` file** — download [`dist/hybrid-social-video.skill`](dist/hybrid-social-video.skill) (a zip with the skill folder at its root):

```bash
unzip -o dist/hybrid-social-video.skill -d ~/.claude/skills/
```

For Claude.ai or Claude Desktop: Settings, Capabilities, Skills, upload the `.skill` file.

**Claude Code plugin marketplace**

```
/plugin marketplace add muhammad-ahmed-ghani/hybrid-social-video-skill
/plugin install hybrid-social-video@hybrid-social-video-marketplace
```

**Clone**

```bash
git clone https://github.com/muhammad-ahmed-ghani/hybrid-social-video-skill.git
cp -R hybrid-social-video-skill/skills/hybrid-social-video ~/.claude/skills/
```

Start a new session afterwards so the skill is picked up.

## Requirements

- `python3` (3.9+) and `ffmpeg` / `ffprobe`. The scripts use the standard library, with `Pillow` for sheets and `numpy` for the mix.
- For the host-plus-overlay route: `playwright` with Chromium (`pip install playwright && playwright install chromium`) and
  `faster-whisper` for word timings.
- Optional, used when present: an image, video, voice or music tool (for example an MCP server such as ImagineArt, or fal), the
  HyperFrames CLI, a Manim skill, `explainer-reel-skill`. `references/11-routing.md` says how the skill degrades without them.

## Repository layout

```
.
├── skills/hybrid-social-video/     the skill (what gets installed)
│   ├── SKILL.md                    entry point: operating mode, the bar, rules, loop
│   ├── references/                 formats, beat map, style, sound, governance, QA, routing, series, AI models and tools
│   ├── scripts/                    lint, cost plan, ledger, provenance, voice check, host assembly, HTML renderer, mixer, QC, series
│   ├── data/                       formats, intents, identities, platforms (thresholds, no prices)
│   ├── examples/                   linting beat maps and the host-plus-overlay page behind the demo
│   └── tests/                      pytest suite pinning the skill's invariants
├── demo/                           the demo reel, its GIF preview, its plan, and its AI-use statement
├── assets/                         the mascot and the social preview image
├── dist/hybrid-social-video.skill  packaged skill, rebuilt by tools/package_skill.py
├── tools/package_skill.py          validate and pack
├── .claude-plugin/marketplace.json
├── .github/workflows/ci.yml        validate, test, check the .skill is current
├── CHANGELOG.md · CONTRIBUTING.md · LICENSE
```

## Development

```bash
pip install pytest pillow numpy
python3 -m pytest -q skills/hybrid-social-video/tests/     # media tests need ffmpeg
python3 tools/package_skill.py                              # validate and rebuild dist/
```

CI fails if `dist/hybrid-social-video.skill` is out of date, so rebuild and commit it with any change to the skill.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

## Credits

The mascot, Slate, is an AI-generated image (GPT Image 2.5 Flare through the ImagineArt MCP). The demo's presenter is a fictional
AI-generated person (Nano Banana Pro for the portrait, Veo 3.1 Fast for the talking clips); every model is listed in
[`demo/AI-USE.md`](demo/AI-USE.md).

## License

[MIT](LICENSE)
