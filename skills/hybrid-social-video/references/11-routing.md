# Routing: who builds each layer

This skill decides and governs. It does not re-teach tools that have their own skills. For every
layer below, load the named skill and give it the handoff payload. Read the sibling's own `SKILL.md`
first: it owns its steps, gates and commands, and those change between versions. Names below match the
HyperFrames skill set as of 2026-10-20; if a name is missing, ask the router.

## Contents
- [Check what is installed](#check-what-is-installed) · [Layer to skill map](#layer-to-skill-map)
- [The HyperFrames handoff](#the-hyperframes-handoff) · [Other handoffs](#other-handoffs)
- [Two assembly routes](#two-assembly-routes) · [When a sibling is missing](#when-a-sibling-is-missing)
- [Rules for every handoff](#rules-for-every-handoff)

## Check what is installed

Before the intake card, list what this environment can do from the skills in your context and your tool
list. Run `python3 scripts/capability_probe.py --out episode/capabilities.json` for the local facts (binaries,
modules, GPU, credential names, never values), then add your own tools and skills to that file. Write the
answer into `meta.notes` of the beat map, so the plan only uses layers you can produce. What each capability
costs is a separate question, answered by the cost scout (`14-cost-scout.md`) from the same inventory.

| Capability | How to detect | If absent |
|---|---|---|
| HTML-to-video authoring and render | a `hyperframes` skill is listed; `npx --no-install hyperframes --version` works (without `--no-install`, npx fetches the package) | ask once, then `npx skills add heygen-com/hyperframes --all` |
| Math animation | a Manim skill is listed; `python3 -c "import manim"` | HyperFrames with SVG and KaTeX for light cases |
| Image generation | an image tool or fal MCP in the tool list | code, stock and real only; no `ai_image` beats |
| Video generation | a video tool or fal MCP | stills with parallax and grain in code; no `ai_video` beats |
| Voice and word timings | a TTS tool, fal MCP, or `/media-use` | script, captions and animatic only; say so |
| Talking host | an avatar endpoint | voice-over format; never fake a host with a still |
| ffmpeg and ffprobe | `ffmpeg -version` | install yourself; everything local needs it |

Side effect to expect: running the HyperFrames CLI from an agent can install or refresh its whole skill set
into global agent directories (`~/.claude/skills`, `~/.agents` and others). That is documented behaviour of
`hyperframes init`, not a bug; tell the user if it happens.

## Layer to skill map

| Layer or job | Load | What it owns |
|---|---|---|
| any code-rendered build | `/hyperframes` | the entry point and router; reads `BRIEF.md`, installs the owning workflow with `npx hyperframes skills update <workflow>` |
| composition contract: timing attributes, tracks, sub-compositions, determinism | `/hyperframes-core` | what a valid composition is; creator edit recipes |
| motion, transitions, scene blueprints | `/hyperframes-animation`, `/hyperframes-keyframes` | how things move and settle; punch-ins and camera moves |
| palette, type, `frame.md`, narration craft, storyboard recipe | `/hyperframes-creative` | the design system of a composition |
| voice-over, music, SFX sourcing, transcription, captions, background removal, grades | `/media-use` | audio and media assets; word timings |
| mixing placed audio: ducking, voice-over carve, fades, effect chains, submix buses | `/hyperframes-audio` | the mix inside a composition |
| a named look or block (chart, map, count-up, grain, glitch, CRT, transitions) | `/hyperframes-registry` | about 400 hosted blocks: search BEFORE hand-building |
| timeline layout, one caption track, safe zones | `/hyperframes-studio` | how a project reads in Studio |
| init, lint, `check`, snapshot, preview, render, batch, doctor | `/hyperframes-cli` | the dev loop (`validate` and `inspect` are deprecated aliases of `check`) |
| faceless code-only explainer | `/faceless-explainer` (via the router) | formats `kinetic-type-essay`, `diagram-mechanism`, `data-story` |
| short unnarrated hit, or a transparent overlay | `/motion-graphics` | stat hits, lower thirds, alpha overlays for route F |
| existing footage plus designed cards | `/talking-head-recut` | `talking-head-package` (cards) |
| existing footage plus captions | `/embedded-captions` | `talking-head-package` (captions) |
| a site, a pull request or a product as the subject | `/website-to-video`, `/pr-to-video`, `/product-launch-video` | capture sources for `screen-demo`; a promo is a different job |
| anything custom or long | `/general-video` | the workflow for the editorial formats |
| equations, graphs, algorithms | a Manim skill (for example `maths-animation`, `manim-video`, `adithya-s-k/manim_skill`, `devamsheth21/3b1b-video-skill`) | `math-science-manim`; check each skill's flags against the installed Manim version |
| host avatar, AI b-roll, ffmpeg master, fal transport | `explainer-reel-skill` | format `host-broll`; its scripts, gates and cost rules apply as written |
| image prompts | `nano-banana-prompt-crafter`, `gpt-image-2-storyboard` | model-specific prompt craft; you still supply the style lock and anchor |
| whiteboard look; cutting the user's own footage on a timeline | `whiteboard-animation`, `video-editor` (Computer environment) | out of scope here: route away |

## The HyperFrames handoff

The router reads a `BRIEF.md` and, when it exists, executes its `workflow` and asks no brief questions.
Because Gate 1 already approved the plan, give it one:

```bash
npx hyperframes init episode/hf --non-interactive          # init first: it refuses a non-empty directory
python3 scripts/beatmap_to_brief.py episode/beatmap.json --out episode/hf --spans episode/spans.json
cp episode/style.json episode/style.css episode/beatmap.json episode/hf/
```

`beatmap_to_brief.py` writes `BRIEF.md` (workflow from `data/formats.json`, `flow: automation`,
`storyboard: no` so the plan is not approved twice, the thesis as `message`, 1080x1920, the overlays and devices
per beat as Customizations, notes that fix the source of truth and the safe box) and `SCRIPT.md` (the locked
narration, one `## Line N` per beat, times from `spans.json` when you have real word timings). Check the
installed router's `brief-contract.md` if `destination`, `angle` or `aspect` vocabulary differs.

Then invoke `/hyperframes` and let it route. Tell it what is decided:

```
Approved plan, do not re-open the brief or the script. Source of truth: beatmap.json (code-layer beats are yours,
ids <list>; other layers arrive as files in assets/). Timing: spans.json. Design: style.json and style.css verbatim.
Canvas 1080x1920 at 30 fps. Keep the platform danger zones clear (scripts/contact_sheet.py draws them).
Return: the composition path, a per-beat render check, and any beat you could not realise.
```

HyperFrames keeps its own checks (lint, `check`, snapshot) and its render approval; run them. Do not run its workflow's
audio or caption steps on top of audio you already built; point it at your stems.

## Other handoffs

**A Manim skill** (`math-science-manim`): the scene list from the beat map (one continuous scene per short), narration
per scene, the colour map from `style.json`, the vertical contract and timing helper from `05b-data-and-math.md`, and
word timings so waits match speech. Ask for a contact sheet per scene before the full render.

**`explainer-reel-skill`** (`host-broll`): its `plan.json` shape, derived from the beat map with the table in
`formats/host-broll.md`. Keep its cost gates; mirror its `costs.jsonl` into the ledger (`ledger.py import`).

**An image or video generator**: one JSON-structured prompt per asset (`07-ai-layer.md`), `art_style.json`, the anchor,
the aspect ratio, the beat id as the filename key. Never a raw prose seed.

## Two assembly routes

Pick one per episode and write it in `meta.assembly` (`H`, `F` or `L`).

| Route | When | How | Watch for |
|---|---|---|---|
| H, HyperFrames assembles everything | R0 to R2, no lip-sync-critical host audio | AI clips, stills, stock and capture are media clips in one composition with the code layer, captions and audio; one render | render time on small CPUs; keep AI clips short and pre-trimmed |
| L, no HyperFrames: your own renderer plus ffmpeg | HyperFrames is not installed and the user declined to install it | render the code layer yourself: HTML and SVG in a headless browser (Playwright if present) with a seekable GSAP timeline, one PNG per frame at the target fps; Manim for maths; Pillow or Cairo for flat charts; then concat, burn captions (SRT or ASS) and mux with ffmpeg | none of HyperFrames' hard-won rules carry over (frame-seek safety, caption fonts, determinism): render one frame twice and compare hashes, check fonts with `textscript.py`, and say plainly what you could not build |
| F, ffmpeg master with an alpha overlay track | R3 with a host avatar, or any episode where the host's own audio is the clock | render the code layer as a transparent overlay (`/motion-graphics` supports alpha output), cut the base with `-ss` after `-i`, composite, mux | overlay alpha must be QTRLE `.mov` or a PNG sequence: VP9 alpha composites as opaque black through ffmpeg `overlay`; concat paths absolute; one shared encode profile |

In route F the avatar's returned audio is the master voice: captions, music mix and duration key off it. Never mux
a separate voice-over onto an avatar clip. `explainer-reel-skill` documents the sync rules; follow them. Project
timeline conventions for route H (one caption track, one element kind per track, every scene a sub-composition) are in
`/hyperframes-studio`; its generic 90% and 80% safe boxes are looser than the measured platform bands in
`10-platforms.md`, so use the platform bands for anything that matters.

## Host plus overlays (route L, verified)

When the video carries a talking host, the host video is the base layer and the code layer is drawn over it: no HyperFrames
needed. `scripts/host_assemble.py` joins the clips and writes per-word timings from the host's own audio; an HTML page
(`examples/host-overlay-composition/`) draws the picture as a pure function of time over pre-extracted host frames:
the host full frame for the hook, the answer and the payoff, and a circular bubble over a blurred, tinted copy of the host
while a diagram takes the stage; `scripts/render_html.py` renders the frames in parallel and checks determinism;
`scripts/mix_audio.py` mixes the host's untouched audio with a ducked bed and meaningful cues; ffmpeg encodes; `qc_master.py`
checks. HyperFrames stays an optional upgrade for the final note, never a question.

## When a sibling is missing

1. Say which skill is missing and what it would add, in one line.
2. Do not stop to ask. Mention the install command once in the final note as an optional upgrade; install only when the user asked for it.
3. Continue with the degradation in the table above. A plan that needs a layer you cannot produce is re-planned at Gate 1,
   not discovered at render time.
4. Never improvise a replacement for a missing skill's hard-won rules (frame seek safety, caption fonts, avatar sync).
   Asking is cheaper than rebuilding.

## Characters and voices in a series

Cast layers come from the series folder, never from a fresh prompt: a puppet rig authored once and animated by a GSAP
timeline inside the composition (the code layer), approved stills for hero clips, and a stored voice id per character.
`beatmap_to_brief.py --series DIR` writes each spoken beat's speaker and voice into `SCRIPT.md`, so every episode speaks with
the same voices. See `15-series.md` for the three routes, the licences and the evidence.

## Rules for every handoff

- One owner per file. The beat map belongs to this skill; compositions belong to HyperFrames; `plan.json` belongs to
  `explainer-reel-skill`. Convert at the boundary, never edit across it.
- Pass ids, not copies. Beat ids are the join key between every system.
- Ask the sibling to report what it could not do instead of silently substituting. A silent substitution is how a number
  ends up in an AI frame.
- Re-lint after any sibling step that changes timing: `beatmap_lint.py`, then regenerate `spans.json`.
- Credentials never appear in handoff text, files or logs. Use a placeholder.
