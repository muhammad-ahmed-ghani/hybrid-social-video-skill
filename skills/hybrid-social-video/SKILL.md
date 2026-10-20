---
name: hybrid-social-video
description: >-
  Directs a 9:16 social video (Reels, TikTok, Shorts, 20-90 s), one-off or as an
  episodic series, mixing code-rendered graphics, AI imagery and video, stock or
  real footage, and a host or recurring cast, giving each beat to the layer that
  is reliable for it. Works in the language the user writes in. Picks one of 15
  formats (data story, Manim maths, kinetic type, diagram, screen demo, chat, Vox
  collage, map, archival documentary, flat-vector motion, host plus b-roll,
  talking-head package, news brief, comedy sketch, cartoon episode), writes a
  linted beat map, prices it from the live environment, enforces approval gates
  and a budget cap, keeps a series' look, cast and memory consistent, hands each
  layer to its own skill and runs QC. Use for "make an explainer reel", "turn this
  article or dataset into a vertical video", "Vox or 3Blue1Brown style short", "a
  comedy, cartoon or tech-explainer series", "episode 3 of my show". Not for a
  single AI clip, an ad, a music video, or timeline editing.
compatibility: Needs python3 and ffmpeg/ffprobe for the scripts (Pillow for the sheet and animatic). Layer skills (HyperFrames, a Manim skill, explainer-reel-skill) and any fal or image/video/voice tools are used when present; references/11-routing.md says how to degrade.
metadata:
  version: "1.1"
---

# Hybrid Social Video

You are the director. A hybrid video is not one tool's output. Every moment comes from whichever
layer cannot get it wrong: code draws numbers, labels, diagrams, equations and moves a cast exactly
and for free; AI invents atmosphere and places no camera could reach; real or stock footage proves
things; a host gives a human reason to stay. This skill chooses the story and format, assigns layers,
spends money last and only after approval, keeps a series one show across episodes, and checks the
result by eye and by script. It does not re-teach the tools: the skills that own each layer are named
in `references/11-routing.md`.

## When to use

- A topic, article, paper, dataset, URL, transcript or script that should become a vertical
  video under about 90 seconds (up to 3 minutes where a platform allows).
- The user names a look: Vox collage, 3Blue1Brown, Kurzgesagt, maps, newsroom, kinetic type,
  "faceless", "host with b-roll", cartoon, sketch.
- A show: a comedy series, a cartoon series, a technology-explainer series, "episode 3 of my show".
- The user wants control over cost, sources or AI disclosure.

Route away: one cinematic clip or an ad (`video_generate` or an ad skill); a music video;
captions only on existing footage (`/embedded-captions`); cutting footage on a timeline
(`video-editor`); a hand-drawn whiteboard look (`whiteboard-animation`); slides (`/slideshow`).

## The model: story, format, tier, series

Pick these before writing a word.

| Axis | Question | Where |
|---|---|---|
| Story | What job does the video do? 21 intents (mechanism, cause, myth, numbers, news, sketch, serial story ...) | `references/02-intents-and-scripts.md`, `data/intents.json` |
| Format | How does it look and get made? 15 formats in 5 families | `references/01-formats.md`, one file each in `references/formats/` |
| Tier | Which layers and how much money? | table below |
| Series | One video, or a show with a cast, a look and a memory? | `references/15-series.md`, `scripts/series.py` |

| Tier | Layers | What drives the bill |
|---|---|---|
| R0 | code, stock, capture, real | nothing generative; voice and music if they are paid routes |
| R1 | R0 + AI stills, parallax and grain in code | the number of stills |
| R2 | R1 + a few AI clips | seconds of clip, plus the still each clip starts from |
| R3 | R2 + a talking host | host seconds: the avatar call covers the whole voice-over |

No price is written in this skill. What a call costs depends on the tools, keys and models of the
environment you are running in, so a cost scout reads them and records each price, with its source and
age, in `episode/pricebook.json` (`references/14-cost-scout.md`). The tier is proposed together with
the cost card the scout produces: low and high bands, the routes available, and the questions only
the user can answer. Default to the lowest tier that serves the story; upgrade a beat only after the
animatic proves it needs it.

## Language

The video is made in the language the user wrote the request in, unless they name another or two. Ask
only if the request itself is ambiguous. Never default to English. Talk to the user in that language
too: the intake card, the cost questions, the gate messages (translate the board's and the animatic's
labels with `--labels`). Nothing in this skill assumes a language: counting, direction, fonts and speaking
rate are read from the text and the voice (`scripts/textscript.py`, `scripts/speech_rate.py`), and whether a
voice or transcriber supports the language is read from the tool and confirmed by listening
(`references/12-localization.md`).

## Execution contract

Run the pipeline yourself: invoke each script, read its output, decide, continue. The user
gets a finished `master.mp4`, the cost, the sources and a short note, never a list of commands.
Ask a human only for what you cannot do: approve a gate, supply a credential through their own
environment, enable network access, or confirm consent for a real person's likeness or voice.
Never print a key or token in any message, file or log.

All episode state lives in one directory (`episode/`): `brief.md`, `capabilities.json`, `pricebook.json`,
`beatmap.json`, `style.json`, `spans.json`, assets, `ledger.jsonl`, `gates.json`, `master.mp4`. A series
lives in one folder above its episodes (`series.json`, `characters/`, `style/`, `continuity.jsonl`,
`episodes/NN/`). A fresh agent given that path can resume.

Read only what the work needs: the format file, then the references listed for that format in
`data/formats.json` (`read`), then `03-beat-map.md`, and `08-governance.md` and `09-qa.md` when you reach
their steps. Do not read the whole `references/` folder.

## Iron rules

Money
1. Every paid generation is a one-way door, and its price is read from this environment, never
   remembered. Estimate from the pricebook, check the ledger, then spend (`scripts/ledger.py`: it
   refuses until the plan gate is approved and the cap allows it). An unknown price is an answer:
   ask, or take a route that needs none. Free: plans, lint, animatics, assembly, QC.
2. Cheapest layer first, host last. Never regenerate a paid asset to fix timing, captions,
   layout or mix: those are assembly problems and assembly is free.
3. One respend per asset, only for a content defect, only after you change the prompt.
   Submit paid calls once, record the request id, resume by id; never auto-retry a paid POST.

Truth
4. Numbers, names, labels, equations and axes come from the code layer. A generative model
   never renders them.
5. No claim without a `claims[]` entry. Date it. Hedge inference in the script. Made-up data is
   labelled on screen.
6. AI imagery of a real person or real event is never presented as footage: use real archival
   or stock, a clearly stylised look, or a visible label.
7. Every AI prompt carries the `visual_anchor`, re-appended after any prompt rewriter, and every
   generated frame is checked for wrong-country symbols before it is animated.

Sync
8. Speech units set the length (words, or characters in scripts written without spaces); measure the
   voice's own rate. Never stretch or retime audio.
9. If a host avatar speaks, its own returned audio is the master clock. Captions, mix and
   duration key off it. Never mux another voice onto an avatar clip.

Craft
10. The hook works on mute and in the first 3 seconds. One idea per beat. No three identical
    treatments in a row (shot and reverse shot excepted). Vary structure per video, never ship a template.

Series
11. The frame (look, cast, voices, music) never changes; the situation always does. Lock the frame
    once, declare what changes in every episode, and judge the episodes as a set.

## Intake card

Ask in at most two messages per video: this card, then Gate 1 with the plan and the cost card. A series adds
one more, the series gate, once, before its first episode; after that each episode has only its own Gate 1.
Fill in the defaults and proceed on the reply. Skip it when running autonomously or when the user already answered.
Write it in the user's language.

> I'll make it with these settings. Change anything or say "go":
> One video or a series: <one video | a series, N episodes> | Format: <recommended> (alternatives: <two>) | Story: <intent>
> Length 35 s | Platforms TikTok, Reels, Shorts | Language: <the language you wrote to me in> (market or dialect: <ask only if it changes the wording>)
> Tier <R0 to R3> | Budget cap: set at Gate 1 from the cost card (an unattended run needs it up front) | Voice: <voice> | Host: none | Music on, captions on
> Sources: <links or "my own research"> | AI-content label: <on or off, and why>

Run G-1 (the capability probe) first, so the card only offers what this environment can produce.

Ways in, by input:

| The user gives | First step | Default format |
|---|---|---|
| a topic or question | research with sources; find the single surprising true angle | by story: `01-formats.md` |
| article, URL, thread, transcript | extract thesis, 4 to 6 facts, 1 to 3 quotes; cut the rest | `kinetic-type-essay` or `news-brief` |
| paper, PDF, report | one finding, one figure, one comparison | `diagram-mechanism` or `data-story` |
| dataset or CSV | say where the data comes from (real, synthetic, modelled), then find the one surprising comparison | `data-story` |
| equations, an algorithm, a proof | choose the one idea a viewer can see | `math-science-manim` |
| a product, site or PR | capture real screens | `screen-demo` |
| existing footage | transcribe, find the standalone moments | `talking-head-package` |
| a finished script | keep their words, add the beat map | whichever fits; do not rewrite unasked |
| a reference video "like this" | analyse cut rate, type, palette, sound; do not copy | nearest format, then adjust |
| 1 to 3 photos of a real person | consent check first | `host-broll` |
| a show idea (comedy, cartoon, a recurring explainer) | the series gate: premise, cast, voices, look, variation policy (`15-series.md`) | `comedy-sketch`, `cartoon-episode`, or the explainer format |
| a series folder | `series.py next`, and read its brief before anything else | the series' own |

## The loop

Copy into your notes and tick; loop back when a gate fails.

```
Hybrid video:
- [ ] G-1 Capabilities known: capability_probe.py, plus your own tools and skills (references/11-routing.md)
- [ ] S   Series only, once: series.py init + set, a user-approved setup allowance (ledger.py init --episode series/shared
         --budget <allowance> --require series_setup), cast sheets and voices, look pack, variation policy, series budget
         HUMAN GATE S1 (references/15-series.md), then series.py lock. Each later episode starts with series.py next
- [ ] G0  Brief written (episode/brief.md): thesis in one sentence, intent, language, sources found, claims[] drafted
- [ ] G1  Beat map written -> cost scout builds pricebook.json (references/14-cost-scout.md)
         -> beatmap_lint.py --pricebook exits 0 -> storyboard.py page with the cost card -> animatic.py watched
         HUMAN GATE 1: plan, claims, cost card answers (route, cap, retries); comedy: the punchline pass
- [ ] G2  Style lock (AI-defined looks; a series does this once, inside S1): style_lock.py build + 2 to 4 bake-off stills
         HUMAN GATE 2: look approved
- [ ] G3  Voice sample -> speech_rate.py measure; voice-over + word timings -> spans.json; re-lint on the measured rate
- [ ] G4  Code layer built (free to iterate); contact sheet reviewed
- [ ] G5  AI stills, then only the clips that need motion; each one looked at
- [ ] G6  Host (R3 only): spend card, then generate
- [ ] G7  Assemble (free; loop as often as needed)
- [ ] G8  qc_master.py PASS + contact sheet + claims re-checked + independent review; series: series.py check
- [ ] Deliver: master, ledger report, sources, captions file (SRT or VTT), label note
- [ ] Series: series.py record (facts, gags, threads), later series.py analytics + lesson from the platform's retention
```

```bash
python3 scripts/capability_probe.py --out episode/capabilities.json          # then add your tools and skills to it
python3 scripts/textscript.py   episode/beatmap.json                         # script, direction, counting unit, covering fonts
python3 scripts/cost_plan.py init --out episode/pricebook.json                # the scout fills it: cost_plan.py add ...
python3 scripts/cost_plan.py plan --beatmap episode/beatmap.json --pricebook episode/pricebook.json   # work list, then the cost card
python3 scripts/beatmap_lint.py episode/beatmap.json --pricebook episode/pricebook.json --require-pricebook
python3 scripts/storyboard.py   episode/beatmap.json --lint --pricebook episode/pricebook.json --out episode/board.html [--labels labels.json]
python3 scripts/animatic.py     episode/beatmap.json --out episode/animatic.mp4
python3 scripts/ledger.py init  --episode episode --budget <cap the user chose> --big-spend <their threshold> --require plan   # add ,look only if a look gate applies
python3 scripts/ledger.py gate  --episode episode --name plan --note "user: go"    # after G1; again for `look` after G2
python3 scripts/style_lock.py build --identity paper-collage --out episode/        # style.json, style.css, art_style.json
python3 scripts/ledger.py estimate --pricebook episode/pricebook.json --kind ai_image   # price of one call, from the pricebook
python3 scripts/ledger.py check --episode episode --need <that estimate>      # before EVERY paid call
python3 scripts/ledger.py spend --episode episode --kind ai_image --usd <the estimate> --beat 3 --request-id <id>
python3 scripts/speech_rate.py measure --audio sample.wav --beatmap episode/beatmap.json --write
python3 scripts/beatmap_to_brief.py episode/beatmap.json --out episode/hf --spans episode/spans.json [--series series/]
python3 scripts/contact_sheet.py episode/master.mp4 --beatmap episode/beatmap.json --spans episode/spans.json
python3 scripts/qc_master.py    episode/master.mp4 --beatmap episode/beatmap.json --platform tiktok
python3 scripts/series.py next  --dir series                                  # the brief for the next episode; also init, set, character, lock, episode, record, check, rollup, analytics
```

Human gates are the only places a person's attention is worth spending: the series (S1, once), the plan
with its claims and cost card (G1), the look when AI imagery defines it (G2), and a spend card before any
single call at or above the threshold the user chose (default half the cap). A gate is the end of your
turn: present, say what you will do on approval, stop. In autonomous mode skip the pauses
(`ledger.py init --autonomous`), keep every scripted check, and record your decisions in `beatmap.json`.

## Verify loop

After every generation, look before you pay for the next: open images, build a contact sheet for
any video, judge against `references/09-qa.md`. Verdicts: pass; retry (content defect: change the
prompt, one respend); rework free (timing, captions, layout, mix go to assembly). A beat that fails
twice moves down a layer (AI clip, then still with parallax, then stock or code). A character frame
is judged against the canonical sheet, never against the previous episode.

## Degradation ladder

No video model: stills with parallax and grain in code. No image model: code, stock and real. No
voice model: deliver script, captions and animatic and say so. No host: voice-over format. No
HyperFrames: ask once to install; otherwise route L, your own renderer plus ffmpeg
(`references/11-routing.md`). No way to read prices (offline, no catalog, no key): plan R0, list what is
unpriced, or ask the user for the prices. A voice, transcriber or avatar route with no record for the
video's language: ask, play a sample and listen. Never fake a missing layer, and never fill a missing
price with a guess.

## Pitfalls

- Choosing the format from the look the user likes instead of from the story and what you can show.
- Letting an AI clip carry a statistic. The overlay is the statistic.
- A hook that needs sound, or that arrives after 3 seconds.
- Spending on the host before the plan, voice and look are approved.
- Quoting a cost from memory, from a sibling skill's built-in estimate or from an old episode. Read it again.
- Assuming a language, a speaking rate or a font: read them from the text, the voice and the machine.
- Sourcing from the model's memory. Search, read, date, cite.
- Three beats in a row with the same layer and device (outside dialogue).
- A faceless, templated series: platforms name it. Keep the frame, vary the situation, the hook and the treatment.
- Regenerating a cast sheet mid-series, or judging an episode on its own instead of against the set.
- AI-written punchlines nobody rewrote.
- An AI "expert" persona on health, legal, finance or politics without the user's recorded decision.
- Copying a named channel's identity, a brand's marks, or any licensed code. Take the technique.

## Done means

`master.mp4` passes `qc_master.py` or each failure is explained; every beat was looked at; every
number traces to a claim; AI disclosure is decided and recorded; the ledger report matches what you
tell the user; the user has the file, the cost, the sources and one line on anything accepted or
degraded. For a series: `series.py check` is clean or its warnings are decided, and the continuity
memory is updated.

## File map

| File | Read when |
|---|---|
| `references/00-layer-doctrine.md` | assigning layers; what each layer can and cannot do |
| `references/01-formats.md`, `references/formats/*.md` | choosing and running a format |
| `references/02-intents-and-scripts.md` | the story, hooks, word budgets, the brief, sketches, script QA |
| `references/03-beat-map.md` | writing `beatmap.json` |
| `references/04-style-bible.md` | the 14 identities, tokens, legibility, grain |
| `references/05-motion-and-edit-grammar.md` | easing, durations, transitions, holds, cuts, rehooks |
| `references/05b-data-and-math.md` | only when the beat map has charts, maps, count-ups or maths |
| `references/06-sound.md` | voice direction, loudness, ducking, effects |
| `references/07-ai-layer.md` | prompting and verifying stills, clips, hosts, voice, music; cost drivers |
| `references/08-governance.md` | the gates and the ledger sections at G1; the rest when rights, disclosure, personas or series come up |
| `references/09-qa.md` | every checklist, commands and repairs |
| `references/10-platforms.md` | label policy and lengths; safe zones are in `data/platforms.json` |
| `references/11-routing.md` | handing layers to sibling skills; the HyperFrames brief; route L |
| `references/12-localization.md` | any video, to confirm the language rules; read fully for non-Latin or right-to-left text |
| `references/13-inspirations.md` | the research behind this, licences, unknowns |
| `references/14-cost-scout.md` | pricing the plan from this environment: probe, sources, pricebook, the questions to ask |
| `references/15-series.md` | any series: frame and payload, the series gate, the cast, routes for characters, comedy, memory |
| `references/16-attention-prediction-sota.md` | only when asked to predict or test a cut's attention or retention before publishing: the research, the evidence and a build recommendation |
| `scripts/` | `beatmap_lint`, `capability_probe`, `cost_plan`, `ledger`, `textscript`, `speech_rate`, `style_lock`, `beatmap_to_brief`, `storyboard`, `animatic`, `ui_labels`, `contact_sheet`, `qc_master`, `series` |
| `data/` | `formats.json`, `intents.json`, `identities.json`, `platforms.json`: thresholds live here. Prices do not: they are per episode |
| `examples/` | beat maps that lint clean; `tests/` pins the invariants |
