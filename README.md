<h1 align="center"><img src="assets/mascot-small.png" height="72" align="absmiddle" alt="Slate, the mascot"> Social Explainer Reel</h1>

<p align="center">
An <a href="https://agentskills.io">Agent Skill</a> that directs 9:16 reels, TikToks and Shorts: a human host with code-drawn overlays,
AI imagery and video, stock or real footage, each beat given to the layer that can't get it wrong.<br>
It runs end to end without asking you questions, and it knows, and tells you, which AI models made what.
</p>

<p align="center">
<a href="https://github.com/muhammad-ahmed-ghani/social-explainer-reel-skill/actions/workflows/ci.yml"><img src="https://github.com/muhammad-ahmed-ghani/social-explainer-reel-skill/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
<img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT">
<img src="https://img.shields.io/badge/skill-v1.5-informational" alt="skill v1.5">
<img src="https://img.shields.io/badge/Agent_Skills-compatible-success" alt="Agent Skills compatible">
</p>

## See it work

<p align="center">
<img src="demo/demo.webp" width="300" alt="The demo reel: a host explains the skill with motion graphics over the footage. Silent preview of the full 35 second video.">
</p>

<p align="center">Silent preview of the full 35 s reel. <a href="https://github.com/muhammad-ahmed-ghani/social-explainer-reel-skill/raw/main/demo/social-explainer-reel-demo.mp4"><b>Download it with sound (mp4)</b></a>.</p>

That reel was made by this skill from one sentence: *"create a video explaining that if you want social reels or explainer
videos, go to this repository and tell your agent to use it."* The agent chose the format, wrote and linted the plan, priced it,
generated a fictional presenter and one talking clip per beat, timed everything from the host's own words, handed the motion design
over the footage to HyperFrames (sources in [`demo/hyperframes/`](demo/hyperframes/)), mixed the sound, and passed QC. The host and his voice are AI-generated and labelled as such.
The reel was recorded before the skill took this name, so its host still says the old one aloud.
How it was made, model by model: [`demo/AI-USE.md`](demo/AI-USE.md) · the plan: [`demo/beatmap.json`](demo/beatmap.json).

### Effects that know where the speaker is

<p align="center">
<img src="assets/person-fx.webp" width="300" alt="One host clip with eight effects in turn: a word behind the head, golden light, an ink stamp, a graph-paper room, a counting number, a glass stat card, brackets that lock onto the face, message banners.">
</p>

<p align="center">One clip, eight effects, silent preview. Each one is placed by the tracker, so type sits behind the head and nothing lands on the face.</p>

```bash
python3 skills/social-explainer-reel/scripts/person_fx.py check   plan.json host.mp4 out/ --words host.words.json   # one frame per effect, a contact sheet, a face-cover audit
python3 skills/social-explainer-reel/scripts/person_fx.py render  plan.json host.mp4 host_fx.mp4 --words host.words.json
```

A plan is a short list such as `{"fx": "word-behind", "on": "everything", "text": "EVERYTHING"}`: the effect starts on the word the speaker says. The catalogue, the options and
the rules are in [`references/20-person-aware-effects.md`](skills/social-explainer-reel/references/20-person-aware-effects.md).

## Use it in one line

Install it (below), then tell your agent:

> use social-explainer-reel to make a 35 second reel that explains how compound interest works

That is all. It decides the format, length, platforms, language, voice, look and renderer, writes each choice into the plan, and
shows you the decisions once, at the end. It stops to ask only for what exists nowhere but in your head: money with no
authorisation, a real person's likeness or voice, a credential. A plan that costs nothing never asks.

## What it does

- **Human first.** For explainers and promos the frame carries a person (a host, real or AI-generated and disclosed) with overlays
  drawn in code over them: the host full frame for the hook and the payoff, a bubble beside a diagram while it explains.
- **A voice people believe.** A ladder, best first: your own recording, host-native speech, a neural voice, and only then a system
  voice, which is marked draft. It auditions voices itself (`voice_check.py`) instead of asking you to listen.
- **It looks before it makes.** A reference scan reads 5 to 10 public reels on your topic (hook type, length, pace, what is overused)
  so it can choose a different, better opener and a pace that fits the feed. Craft only: it never copies content, never bypasses a
  login, and deletes what it downloads.
- **A different look for each video.** `style_lock.py pick` ranks looks by topic and spreads consecutive videos apart, so one palette
  does not take over everything it makes. A brand colour sets the accent only.
- **Motion design by HyperFrames.** When [HyperFrames](https://github.com/heygen-com/hyperframes) is reachable the skill hands the motion design and the
  render to it (`/talking-head-recut` for designed overlays over a host video, `/faceless-explainer` and `/general-video` for the rest), writing the
  brief from the approved plan. It references HyperFrames and never copies its skills. Without it, a built-in route takes over.
- **Effects that know where the speaker is.** With a person on screen, `person_fx.py` tracks the face and cuts a soft matte of the person, then draws against it: type
  *behind* the head, cards that follow the face and never cover it, light that leaves the speaker lit, camera pushes, liquid-glass stat cards, interface mock-ups,
  stamps and hand-drawn marks (45 effects). It cues them on the words the speaker says, checks one frame per effect and fails a covered face, and checks every
  figure against the plan's claims. Free and local. See below.
- **A faceless fallback that builds itself.** Give each beat a `scene` (a stat that counts up, steps, a flow, a closed loop, a comparison, bars, kinetic type,
  a terminal, a quote, with 26 built-in icons) and `build_video.py` does the rest: it picks the look, aligns the voice-over word by word, draws the frames with text fitted
  inside the safe box, mixes the sound, encodes the master, writes the captions and runs QC. `layout_check.py` then measures text size, the
  safe box and collisions from the page itself.
- **A voice route that needs no one.** `voice_render.py` picks the best local voice for the language (Premium, Enhanced and Siri voices
  count as neural; novelty voices never), fits the length, and `voice_check.py` ranks routes by round-trip word accuracy, in any language.
  A draft voice is recorded and the upgrade is named, never hidden.
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

**The `.skill` file** — download [`dist/social-explainer-reel.skill`](dist/social-explainer-reel.skill) (a zip with the skill folder at its root):

```bash
unzip -o dist/social-explainer-reel.skill -d ~/.claude/skills/
```

For Claude.ai or Claude Desktop: Settings, Capabilities, Skills, upload the `.skill` file.

**Claude Code plugin marketplace**

```
/plugin marketplace add muhammad-ahmed-ghani/social-explainer-reel-skill
/plugin install social-explainer-reel@social-explainer-reel-marketplace
```

**Clone**

```bash
git clone https://github.com/muhammad-ahmed-ghani/social-explainer-reel-skill.git
cp -R social-explainer-reel-skill/skills/social-explainer-reel ~/.claude/skills/
```

Start a new session afterwards so the skill is picked up.

**For the best motion design, connect HyperFrames.** In an agent with a filesystem (Claude Code, Cursor, Codex) install its skills with
`npx skills add heygen-com/hyperframes`; the skill does this itself when the host allows it. In a chat client with no filesystem (Claude.ai, ChatGPT, Grok)
connect the hosted MCP by following the [HyperFrames MCP guide](https://hyperframes.heygen.com/guides/mcp) (endpoint
`https://mcp.heygen.com/mcp/hyperframes/`, HeyGen sign-in). The hosted MCP refuses compose and render from local CLI agents, so there the local skills are the way.
Details: [`references/19-hyperframes.md`](skills/social-explainer-reel/references/19-hyperframes.md).

## Requirements

- `python3` (3.9+) and `ffmpeg` / `ffprobe`. The scripts use the standard library, with `Pillow` for sheets and `numpy` for the mix.
- For the person-aware effects: `pip install numpy opencv-python pillow onnxruntime` (the first three are required; onnxruntime gives the real person matte). The first run downloads about 28 MB of
  models and fonts from their upstream projects ([`THIRD-PARTY.md`](skills/social-explainer-reel/THIRD-PARTY.md)); offline it falls back to a rougher matte and system fonts.
- For the host-plus-overlay route: `playwright` with Chromium (`pip install playwright && playwright install chromium`) and
  `faster-whisper` for word timings.
- Faceless route: Playwright with Chromium, `faster-whisper`, `numpy` and `Pillow`; a local voice (macOS `say`, espeak-ng or better).
- Optional, used when present: an image, video, voice or music tool (for example an MCP server such as ImagineArt, or fal), the
  HyperFrames CLI, a Manim skill, `explainer-reel-skill`. `references/11-routing.md` says how the skill degrades without them.

## Repository layout

```
.
├── skills/social-explainer-reel/   the skill (what gets installed)
│   ├── SKILL.md                    entry point: operating mode, the bar, rules, loop
│   ├── references/                 formats, beat map, style, sound, governance, QA, routing, series, AI models and tools
│   ├── scripts/                    lint, cost plan, ledger, provenance, voice check, host assembly, HTML renderer, mixer, QC, series, person tracking and effects
│   ├── data/                       formats, intents, identities, platforms (thresholds, no prices), the effects catalogue, pinned third-party files
│   ├── examples/                   linting beat maps and the host-plus-overlay page behind the demo
│   └── tests/                      pytest suite pinning the skill's invariants
├── demo/                           the demo reel, its animated preview, its plan, its HyperFrames sources, and its AI-use statement
├── assets/                         the mascot, the social preview image and the effects preview
├── dist/social-explainer-reel.skill packaged skill, rebuilt by tools/package_skill.py
├── tools/package_skill.py          validate and pack
├── .claude-plugin/marketplace.json
├── .github/workflows/ci.yml        validate, test, check the .skill is current
├── CHANGELOG.md · CONTRIBUTING.md · LICENSE
```

## Development

```bash
pip install pytest pillow numpy opencv-python-headless
python3 -m pytest -q skills/social-explainer-reel/tests/     # media tests need ffmpeg
python3 tools/package_skill.py                              # validate and rebuild dist/
```

CI fails if `dist/social-explainer-reel.skill` is out of date, so rebuild and commit it with any change to the skill.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

## Credits

The mascot, Slate, is an AI-generated image (GPT Image 2.5 Flare through the ImagineArt MCP). The demo's presenter is a fictional
AI-generated person (Nano Banana Pro for the portrait, Veo 3.1 Fast for the talking clips); every model is listed in
[`demo/AI-USE.md`](demo/AI-USE.md).

The person matte and face detector are open models that run locally: MODNet (Apache-2.0) and YuNet (MIT). Fonts are SIL OFL or Apache-2.0. Nothing is bundled; the files, their
licences and their sources are listed in [`THIRD-PARTY.md`](skills/social-explainer-reel/THIRD-PARTY.md).

## License

[MIT](LICENSE)
