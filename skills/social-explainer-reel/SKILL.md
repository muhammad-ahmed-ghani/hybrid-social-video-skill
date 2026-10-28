---
name: social-explainer-reel
description: >-
  Directs a 9:16 social video (Reels, TikTok, Shorts, 20-90 s), one-off or as an
  episodic series: a human host or natural voice with code-drawn overlays, AI imagery
  and video, stock or real footage, each beat given to the layer that is reliable for
  it. Runs end to end without clarifying questions, in the language the user writes
  in. Picks 1 of 15 formats, writes a linted beat map, prices it from the live
  environment, enforces a budget cap, records which AI models and tools made what,
  keeps a series' look, cast and memory consistent, hands each layer to its own skill
  and runs QC. Use for "make an explainer reel", "turn this article or dataset into a
  vertical video", "Vox or 3Blue1Brown style short", "a comedy, cartoon or
  tech-explainer series", "episode 3 of my show". With a person on screen it adds
  effects that know where they are (type behind the head, face-following cards, light,
  camera pushes). Not for a single AI clip, an ad, a music video, or timeline editing.
compatibility: Needs python3 and ffmpeg/ffprobe for the scripts (Pillow for the sheet and animatic; Playwright for the HTML compose route; numpy, OpenCV and optionally onnxruntime for the person-aware effects). Layer skills (HyperFrames first, via its local skills or its hosted MCP; a Manim skill; explainer-reel-skill) and any image, video, voice or music tools (fal, an MCP server such as ImagineArt) are used when present; references/11-routing.md says how to degrade.
metadata:
  version: "1.6"
---

# Social Explainer Reel

You are the director. A hybrid video is not one tool's output. Every moment comes from whichever
layer cannot get it wrong: code draws numbers, labels, diagrams, equations and moves a cast exactly
and for free; AI invents atmosphere and places no camera could reach; real or stock footage proves
things; a human host gives a reason to stay and a voice people believe. This skill chooses the story
and format, assigns layers, spends money only inside an authorisation, keeps a series one show across
episodes, records which AI models made what, and checks the result by eye and by script. It does not
re-teach the tools: the skills that own each layer are named in `references/11-routing.md`.

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

## Operating mode: decide, do, report

The default is to run the whole pipeline in one go. A question costs the user attention and breaks
automation, so the working rule is: **if you can decide it, decide it, record it, and say it in the last
message.** Never ask about format, length, language, platforms, voice, music, captions, look, tier
or renderer. Getting a helper such as HyperFrames is an action, not a question: attempt it and let the host's permission prompt be the consent. Pick the best option the environment supports, write each choice
and its reason into `meta.notes` of the beat map (the decision record), and show the record once, at the
end, with the one-line way to change each item.

Stop and ask only when the answer exists nowhere but in the user's head, and then ask once, with a
recommended default:

1. **Money with no authorisation.** A budget in the request, a standing note in the project or user
   instructions, or a tool the user told you to use ("use the ImagineArt MCP") is authorisation: measure the
   cost (a catalog, or one small call and the balance difference), set a cap inside it, record it, proceed
   (`scripts/ledger.py init --autonomous`). With none, do not stop: deliver the best free version
   (code layer, stock, the best free voice) and offer the paid upgrade in one line with its measured cost.
   A plan that spends nothing needs no ledger and no gate.
2. A real person's likeness or voice (consent), or a regulated-topic AI presenter (`08-governance.md`).
3. A credential only the user can supply, or a vendor moderation refusal.
4. A permission the host denies: stop that step, finish everything that does not depend on it, say what was
   blocked and why you wanted it. Never work around a denial, split a call to slip under a threshold, or edit
   a guard to get past it.

Defaults that replace the usual questions (decide, record, report):

- **Offline first.** Use a network route only when the user's tools or authorisation allow it; never rely on an unofficial hosted
  endpoint (it can be blocked at any time). A free local route is always reachable.
- **Market and locale.** The voice's own locale wins; write it into `meta.language_tag` and match currency, numbers and spelling.
- **A draft voice is a valid end state** for a zero-spend run when nothing better is reachable: record it (`provenance.py add --draft
  true --upgrade ...`), name the upgrade in the final note, and list the voice item of the bar under accepted defects. Faceless with
  the best reachable voice satisfies the human-presence item when no host is authorised.
- **Accepted defects.** Any bar item you knowingly miss goes in the decision record with the reason and the upgrade, never silently.
- **Unverified sources.** Offline, cite the user's text (`confidence: "user"`) or the source you could not open with `verified: false`;
  the linter surfaces it and the final note says so.
- **A QC check that is wrong** about a video that plainly passes is waived with a reason (`qc_master.py --waive pacing --why ...`),
  never satisfied by changing the picture for the check's sake.

The reference scan (a look at 5 to 10 public reels on the topic, `references/18-reference-scan.md`) and the look pick
(`style_lock.py pick`) run by themselves and feed the decision record; neither is ever a question.

Series: the series gate becomes a decision record too. Propose the premise, cast, look and variation policy,
lock them with `series.py lock`, and go; the user can amend by saying so, and the next episode obeys.

## The bar: would a top creator post this?

A technically valid video is not the goal. Check each point before delivery; a miss is a defect to fix, not a
note to add.

- **A human presence by default.** For an explainer, a promo or any "talk to the viewer" reel, the frame
  carries a person (a host, real or AI-generated and disclosed, or at minimum a human-grade voice) with
  code-drawn overlays on top of or beside them. Go faceless only when the story needs it (numbers first, a
  quiet documentary) or the user asked. See `references/formats/host-broll.md` and the verified build in
  `references/17-ai-models-and-tools.md`.
- **Motion design by the best tool.** HyperFrames (HeyGen) carries a far deeper motion-design craft than this skill's own templates. When it is reachable it
  draws the motion graphics and renders; ours is the plainer fallback (`references/19-hyperframes.md`).
- **A voice people believe.** Ladder, best first: the user's own recording; host-native speech from a video
  model; a neural or human-grade text-to-speech voice; a system voice (macOS `say`, espeak, a small local
  model) is **draft only**. Ship a draft voice only if nothing better is reachable, and say so as a defect with
  the named upgrade. Never ask the user to choose between voices by ear: audition programmatically
  (`scripts/voice_check.py`: the words come back right, the pace and loudness are in range) and pick.
- **Transitions that mean something.** Morphs, pushes, scale-through, a cut on action, a reframe. No white or
  black flash frames, no decorative wipes, no dip to a colour between sections (`references/05-motion-and-edit-grammar.md`).
- **Never edit the picture to satisfy a metric.** If a QC check fails, find the cause. If the check is wrong,
  fix the check or explain it. A flash added only so a detector sees a cut is a defect.
- **Phone-first legibility.** Type that reads at arm's length inside the platform safe box, one hero motion per
  beat, captions that follow the host's own words.
- **Look like a viewer.** Open a contact sheet and three full-size frames, read the caption timeline, and ask
  whether you would stop scrolling. Fix, then deliver.

## Fast path: a faceless, zero-spend video in 10 commands

For a simple video (a topic or a pasted article, no authorised host, no paid tool) read only this file and `references/03-beat-map.md`
(plus the format file if you want its grammar). Work from the skill folder (`cd ~/.claude/skills/social-explainer-reel`) and set
`EP=<absolute path of the episode folder>`; scripts print JSON on stdout and a summary on stderr (add `--quiet` to lint for JSON only):

```bash
python3 scripts/capability_probe.py --out $EP/capabilities.json              # a 5-line summary; detail in the file
python3 scripts/provenance.py init --episode $EP --director "<the model you run as>"
python3 scripts/reference_scan.py find --topic "<topic>" --n 8 --out $EP/references.json   # optional: one attempt, then skip it
#  write $EP/beatmap.json: the story, claims, a `scene` per beat (references/03-beat-map.md; start from examples/starter-beatmap.json)
python3 scripts/cost_plan.py init --out $EP/pricebook.json --free            # local voice, recognition, music, effects at price 0
python3 scripts/voice_render.py --beatmap $EP/beatmap.json --out $EP/vo.wav --target-seconds <N>   # best local voice, fitted length
python3 scripts/speech_rate.py measure --audio $EP/vo.wav --beatmap $EP/beatmap.json --write       # the measured rate, so lint judges the real length
python3 scripts/beatmap_lint.py $EP/beatmap.json --pricebook $EP/pricebook.json --require-pricebook
python3 scripts/voice_check.py  --audio $EP/vo.wav --beatmap $EP/beatmap.json --text-file $EP/vo.txt --kind system
python3 scripts/build_video.py  --episode $EP --voice $EP/vo.wav --qc        # look, timing, frames, mix, encode, captions, QC and layout check
python3 scripts/provenance.py check --episode $EP --beatmap $EP/beatmap.json && python3 scripts/provenance.py report --episode $EP
```

With HyperFrames reachable, hand the picture to it instead (`references/19-hyperframes.md`); `build_video.py` is the fallback. `build_video.py` records the speech recogniser and the voice (draft, with the upgrade named) in `provenance.json` and writes the look it
picked into `meta.style`. Then open the contact sheet (`contact_sheet.py episode/master.mp4 --beatmap episode/beatmap.json`), fix what the bar says is wrong
(re-run `build_video.py`: it is free), add `captions.srt`, the decision record and the AI-use statement to the final message. With a
budget authorised, take the host route instead (`references/17-ai-models-and-tools.md`, `examples/host-overlay-composition/`).

## Motion design: HyperFrames first

Motion design and rendering go to HyperFrames whenever it is reachable; this skill's own `build_video.py` template and host-overlay page are the
fallback and look plainer. At G-1 read the probe's `HyperFrames:` line (and your skill and tool lists), and:

- **Reachable** (its skills installed: `/hyperframes`, `/talking-head-recut`, `/faceless-explainer` ...): write the brief with
  `scripts/beatmap_to_brief.py` (add `--host-video` when a host speaks) and hand over, using `/talking-head-recut` for a host on screen (the host's own audio stays
  the master clock) and `/faceless-explainer` or `/general-video` for the rest. You keep the claims, cost, ledger, provenance and QC.
- **Not reachable:** get it, without stopping to ask. In an agent with a filesystem (Claude Code, Cursor, Codex) run `npx skills add heygen-com/hyperframes`:
  the host's permission prompt is the user's consent, and `npx hyperframes doctor` confirms it. In a chat client with no filesystem connect the hosted MCP by
  reading https://hyperframes.heygen.com/guides/mcp (endpoint `https://mcp.heygen.com/mcp/hyperframes/`, a HeyGen sign-in only the user can complete). The hosted
  MCP refuses `compose` and `render_video` for local CLI and IDE agents (verified 2026-10-21), so there the local skills are the way. If it cannot be had, take the fallback
  and give the user the one-line install in the final note.
- Never copy HyperFrames' skills into this skill or re-teach them: read their `SKILL.md` at run time, because they change. Details, the workflow table and
  the hand-off: `references/19-hyperframes.md`.

## Person-aware effects: when a person is on screen

When a host speaks (generated or recorded), the picture can react to them: type behind the head, graphics that follow the face and never cover it, light that
leaves the speaker lit, camera pushes, liquid-glass cards, interface mock-ups, stamps and hand-drawn marks. `scripts/person_fx.py` does it locally and for free: it tracks
the face and cuts a soft matte of the person (`scripts/person_track.py`), draws 45 effects against that (`references/20-person-aware-effects.md`, catalogue in
`data/effects.json`), and its `check` command looks at one frame per effect and fails an effect that covers a face. The loop: word times, a plan (by hand or from the beat
map with `scripts/fx_plan_from_beatmap.py`), `check`, look, `render`. Cues land on the word that names them (`"on": "never wrong"`); a figure an effect draws must come from a
claim (`--beatmap` checks it). Do the depth pass first, then hand `host_fx.mp4` to HyperFrames for cards and captions. Run `person_fx.py doctor --fetch` yourself when it is
missing (a pip install and a 28 MB model download: the host's prompt is the user's consent); offline it degrades to a rougher matte and system fonts. Record the local
models in provenance (`render` writes `out.fx.json` and prints the command). Three well-placed effects beat ten.

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
age, in `episode/pricebook.json` (`references/14-cost-scout.md`). Choose the tier that gives the best video
inside the authorisation: with a budget, that is usually R3 (a host) or R2; with none, the best R0 plan plus
the upgrade line. Upgrade a beat only when the animatic shows it needs it, and never regenerate to fix an
assembly problem.

## Know your models

Before the first call, state what you are working with, and keep it true:

- **The director.** The model you are running as (read it from your own context, never guess) wrote the
  plan, script and any code. Record it.
- **Every layer.** For each generated or AI-derived asset record the tool, the model id, the provider, whether it
  runs locally or hosted, what data it received (a script, a photo, a voice) and where the output may be used.
  Speech recognition used for word timings is an AI model too. A system text-to-speech voice is a synthetic
  voice.
- **Where it lives.** `episode/provenance.json`, written at the moment of use with `scripts/provenance.py`
  (`init`, `add`, `report`, `check`). It feeds the disclosure decision (`references/08-governance.md`), the label note you
  deliver, and any "how was this made?" answer: answer from the file, never from memory.
- **Discover before you decide a layer is missing.** `capability_probe.py` reports local models, modules and
  credentials by name (its `ai_models` section). Your own tool list is the rest: image, video, voice and music
  tools, MCP servers (some are deferred or still connecting: search for them with ToolSearch before concluding
  they are absent), and the skills you can load. Read model ids, durations and aspect ratios from the tool
  itself; they change weekly and are never remembered. Details and the verified recipes:
  `references/17-ai-models-and-tools.md`.
- **Pin and verify.** One model id per asset type per video. Smoke-test a model with its cheapest call before a
  batch; measure the cost from the balance or the catalog; record it with the request id.

## Language

The video is made in the language the user wrote the request in, unless they name another or two. Never
default to English. Talk to the user in that language too: the decision record, the cost lines, the final
note (translate the board's and the animatic's labels with `--labels`). Nothing in this skill assumes a
language: counting, direction, fonts and speaking rate are read from the text and the voice
(`scripts/textscript.py`, `scripts/speech_rate.py`), and whether a voice or transcriber supports the language
is read from the tool and confirmed by a round-trip transcription (`references/12-localization.md`).

## Execution contract

Run the pipeline yourself: invoke each script, read its output, decide, continue. The user
gets a finished `master.mp4`, the cost, the sources, the AI-use statement and a short note, never a list of
commands. Never print a key or token in any message, file or log.

All episode state lives in one directory (`episode/`): `brief.md`, `capabilities.json`, `pricebook.json`,
`beatmap.json`, `style.json`, `spans.json`, `provenance.json`, assets, `ledger.jsonl`, `gates.json`,
`master.mp4`. A series lives in one folder above its episodes (`series.json`, `characters/`, `style/`,
`continuity.jsonl`, `episodes/NN/`). A fresh agent given that path can resume.

Read only what the work needs: the format file, then the references listed for that format in
`data/formats.json` (`read`), then `references/03-beat-map.md`, and `references/08-governance.md` and
`references/09-qa.md` when you reach their steps. Do not read the whole `references/` folder.

## Iron rules

Money
1. Every paid generation is a one-way door, and its price is read from this environment, never
   remembered. Estimate from the pricebook or measure it, check the ledger, then spend (`scripts/ledger.py`:
   it refuses past the cap, and until the plan gate is approved when gates are on). An unknown price is an
   answer: take a route that needs none, or measure it with the smallest call. Free: plans, lint, animatics,
   assembly, QC.
2. Cheapest layer first for what is exact, best layer first for what the viewer feels (the host, the voice).
   Never regenerate a paid asset to fix timing, captions, layout or mix: those are assembly problems and
   assembly is free.
3. One respend per asset, only for a content defect, only after you change the prompt.
   Submit paid calls once, record the request id, resume by id; never auto-retry a paid POST.

Truth
4. Numbers, names, labels, equations and axes come from the code layer. A generative model
   never renders them.
5. No claim without a `claims[]` entry. Date it. Hedge inference in the script. Made-up data is
   labelled on screen.
6. AI imagery of a real person or real event is never presented as footage: use real archival
   or stock, a clearly stylised look, or a visible label. An AI-generated person is disclosed as AI.
7. Every AI prompt carries the `visual_anchor`, re-appended after any prompt rewriter, and every
   generated frame is checked for wrong-country symbols before it is animated.
8. Say what is AI. `provenance.json` is complete before delivery (`provenance.py check`), and the final note
   lists the models used. Never claim a model or tool you did not call.

Sync
9. Speech units set the length (words, or characters in scripts written without spaces); measure the
   voice's own rate. Never stretch or retime audio.
10. If a host speaks, its own returned audio is the master clock. Captions, mix and duration key off it. Never
    mux another voice onto a host clip.

Craft
11. The hook works on mute and in the first 3 seconds. One idea per beat. No three identical
    treatments in a row (shot and reverse shot excepted). Vary structure per video, never ship a template.
12. Never fix a failed check by changing what the viewer sees for the check's sake (the bar, above).

Series
13. The frame (look, cast, voices, music) never changes; the situation always does. Lock the frame
    once, declare what changes in every episode, and judge the episodes as a set.

## Decision record (replaces the intake questionnaire)

Fill these in yourself, in the user's language, and put them in `meta.notes`. Show them once, at the end.

> One video or a series | Format (and the two next-best) | Story intent | Length (default 35 s) | Platforms (TikTok, Reels, Shorts)
> Language and dialect | Tier and why | Spend authorisation: where it came from, the cap, the unit (USD or provider credits)
> Voice route and why | Host: none, AI-generated (disclosed), or the user's own | Music and sound source | Renderer route (H, F or L)
> Sources | AI-content label decision and its reason | The models and tools used (from `provenance.json`)
> Look and why (`style_lock.py pick`, never a default) | Reference scan: how many public reels, and what it changed
> Accepted defects: bar items knowingly missed, the reason and the upgrade (a draft voice, no host, an unverified source)

Run G-1 (the capability probe and your tool list) first, so the record only contains what this environment can
produce.

Ways in, by input:

| The user gives | First step | Default format |
|---|---|---|
| a topic or question | research with sources; find the single surprising true angle | by story: `references/01-formats.md` |
| article, URL, thread, transcript | extract thesis, 4 to 6 facts, 1 to 3 quotes; cut the rest | `host-broll` with a host, else `kinetic-type-essay` or `news-brief` |
| paper, PDF, report | one finding, one figure, one comparison | `diagram-mechanism` or `data-story`, with a host when authorised |
| dataset or CSV | say where the data comes from (real, synthetic, modelled), then find the one surprising comparison | `data-story` |
| equations, an algorithm, a proof | choose the one idea a viewer can see | `math-science-manim` |
| a product, site or PR | capture real screens | `screen-demo`, with a host when authorised |
| existing footage | transcribe, find the standalone moments | `talking-head-package` |
| a finished script | keep their words, add the beat map | whichever fits; do not rewrite unasked |
| a reference video "like this" | analyse cut rate, type, palette, sound; do not copy | nearest format, then adjust |
| 1 to 3 photos of a real person | consent check first | `host-broll` |
| a show idea (comedy, cartoon, a recurring explainer) | the series record: premise, cast, voices, look, variation policy (`references/15-series.md`) | `comedy-sketch`, `cartoon-episode`, or the explainer format |
| a series folder | `series.py next`, and read its brief before anything else | the series' own |

## The loop

Copy into your notes and tick; loop back when a check fails. A step marked (gate) stops for a human only when
the operating mode above says the answer exists nowhere else.

```
Hybrid video:
- [ ] G-1 Capabilities and models known: capability_probe.py (its ai_models section), your tool list, ToolSearch for deferred
         tools, provenance.py init with the director model (references/11-routing.md, 17-ai-models-and-tools.md)
- [ ] S   Series only, once: series.py init + set, cast sheets and voices, look pack, variation policy, series budget; series.py lock
- [ ] G0  Brief written (episode/brief.md): thesis in one sentence, intent, language, sources found, claims[] drafted
         Reference scan (automatic, optional): 5 to 10 public reels on the topic -> hook, length, pace, what is overused (references/18-reference-scan.md)
- [ ] G1  Beat map written -> cost scout builds pricebook.json (references/14-cost-scout.md)
         -> beatmap_lint.py --pricebook exits 0 -> storyboard.py page with the cost card -> animatic.py watched
         (gate) only if money is needed and nothing authorises it; comedy: the punchline pass
- [ ] G2  Look: style_lock.py pick (never the last look, never a default), then build; 2 to 4 bake-off stills when AI defines the look; decide it yourself
- [ ] G3  Voice: audition routes with voice_check.py, pick the best; voice-over or host clips + word timings -> spans.json; re-lint on the measured rate
- [ ] G4  Code layer built (free to iterate); contact sheet reviewed
- [ ] G5  AI stills, then only the clips that need motion; each one looked at; provenance.py add for each
- [ ] G6  Host (R3): portrait, then a one-clip smoke test (cost, lip-sync, voice), then the rest
- [ ] G7  Assemble (free; loop as often as needed)
- [ ] G8  qc_master.py PASS + contact sheet + claims re-checked + the bar above + provenance.py check; series: series.py check
- [ ] Deliver: master, ledger report, sources, captions file (SRT or VTT), AI-use statement (provenance.py report), decision record
- [ ] Series: series.py record (facts, gags, threads), later series.py analytics + lesson from the platform's retention
```

```bash
python3 scripts/capability_probe.py --out episode/capabilities.json          # local facts and ai_models; then add your tools and skills
python3 scripts/provenance.py init  --episode episode --director "<the model you run as>"
python3 scripts/reference_scan.py find --topic "<topic>" --n 8 --out episode/references.json   # then analyze, summarize (references/18)
python3 scripts/textscript.py   episode/beatmap.json                         # script, direction, counting unit, covering fonts
python3 scripts/cost_plan.py init --out episode/pricebook.json [--free]       # --free: the zero-spend path; else the scout fills it: cost_plan.py add ...
python3 scripts/cost_plan.py plan --beatmap episode/beatmap.json --pricebook episode/pricebook.json   # work list, then the cost card
python3 scripts/beatmap_lint.py episode/beatmap.json --pricebook episode/pricebook.json --require-pricebook
python3 scripts/storyboard.py   episode/beatmap.json --lint --pricebook episode/pricebook.json --out episode/board.html [--labels labels.json]
python3 scripts/animatic.py     episode/beatmap.json --out episode/animatic.mp4
python3 scripts/ledger.py init  --episode episode --budget <cap inside the authorisation> --autonomous    # omit --autonomous to require gates (--require plan,look)
python3 scripts/ledger.py gate  --episode episode --name plan --note "user: go"    # only when gates are on
python3 scripts/style_lock.py pick  --topic "<topic>" --intent <id> --format <id> --recent <earlier episodes>   # ranked looks with reasons
python3 scripts/style_lock.py build --identity <the pick> --out episode/        # style.json, style.css, art_style.json
python3 scripts/ledger.py estimate --pricebook episode/pricebook.json --kind ai_image   # price of one call, from the pricebook
python3 scripts/ledger.py check --episode episode --need <that estimate>      # before EVERY paid call, one call at a time
python3 scripts/ledger.py spend --episode episode --kind ai_image --usd <the estimate> --beat 3 --request-id <id> --model <id>
python3 scripts/provenance.py add --episode episode --role image --tool <tool> --model <id> --provider <vendor> --runs hosted --used-for "<what>" --beats 3 --request-id <id>
python3 scripts/voice_render.py --beatmap episode/beatmap.json --out episode/vo.wav --target-seconds <N>   # free local voice: best by language, fitted length
python3 scripts/voice_check.py  --audio vo.wav --beatmap episode/beatmap.json --text-file episode/vo.txt [--kind system|system-hq|neural] # round trip, pace, level, rank
python3 scripts/speech_align.py spans --audio vo.wav --beatmap episode/beatmap.json --out episode/   # spans.json, words.json, timing.json for any voice-over
python3 scripts/build_video.py --episode episode --voice episode/vo.wav --qc     # faceless route: scenes -> frames -> mix -> encode -> captions
python3 scripts/layout_check.py --page episode/build/index.html                  # Q1 text size, Q4 safe box, Q5 collisions, from the DOM
python3 scripts/speech_rate.py measure --audio sample.wav --beatmap episode/beatmap.json --write
python3 scripts/host_assemble.py --beatmap episode/beatmap.json --clips episode/clips.json --out episode/build   # host clips -> trimmed track + word timings
python3 scripts/beatmap_to_brief.py episode/beatmap.json --out episode/hf --spans episode/spans.json [--series series/]
python3 scripts/render_html.py  --page episode/build/index.html --out episode/build/frames --fps 30   # route L: HTML overlays to frames, in parallel, determinism-checked
python3 scripts/mix_audio.py    --voice episode/build/host.mp4 --duration <seconds> --out episode/build/mix.wav --cues cues.json   # master voice untouched, ducked bed, meaningful cues, -14 LUFS
python3 scripts/contact_sheet.py episode/master.mp4 --beatmap episode/beatmap.json --spans episode/spans.json
python3 scripts/qc_master.py    episode/master.mp4 --beatmap episode/beatmap.json --platform tiktok
python3 scripts/provenance.py check  --episode episode --beatmap episode/beatmap.json
python3 scripts/provenance.py report --episode episode                        # the AI-use statement for the final note
python3 scripts/series.py next  --dir series                                  # the brief for the next episode; also init, set, character, lock, episode, record, check, rollup, analytics
```

Human attention is spent only where the operating mode says. When a gate does apply (money with no
authorisation, consent, a credential), it is the end of your turn: present, say what you will do on approval,
stop. When gates are off (`ledger.py init --autonomous`), keep every scripted check and record your decisions
in `beatmap.json`.

## Verify loop

After every generation, look before you pay for the next: open images, build a contact sheet for
any video, judge against `references/09-qa.md`. Verdicts: pass; retry (content defect: change the
prompt, one respend); rework free (timing, captions, layout, mix go to assembly). A beat that fails
twice moves down a layer (AI clip, then still with parallax, then stock or code). A character frame
is judged against the canonical sheet, never against the previous episode.

## Degradation ladder

No video model: stills with parallax and grain in code. No image model: code, stock and real. No
voice model: use the best reachable voice, mark it draft, deliver script, captions and animatic too. No host:
voice-over format. No HyperFrames: try to get it (`references/19-hyperframes.md`); if it is unreachable or declined, route L (your own renderer plus ffmpeg,
`references/11-routing.md`), call the motion design the plainer route under accepted defects, and give the one-line install in the final note. Never stop the run to ask. No way to read
prices (offline, no catalog, no key): plan R0 and list what is unpriced. A voice, transcriber or avatar route
with no record for the video's language: transcribe a sample back and compare. Never fake a missing layer, and
never fill a missing price with a guess.

## Pitfalls

- Choosing the format from the look the user likes instead of from the story and what you can show.
- Defaulting to the cheapest, faceless version when a budget was authorised and a human host would do the job.
- Shipping a system voice as the final voice, or asking the user to pick a voice by ear.
- A flash, dip or wipe added to please a detector or to hide a seam.
- Letting an AI clip carry a statistic. The overlay is the statistic.
- A hook that needs sound, or that arrives after 3 seconds.
- Spending on the host before the plan and the voice are decided, or skipping the one-clip smoke test.
- Quoting a cost from memory, from a sibling skill's built-in estimate or from an old episode. Read it again.
- Assuming a language, a speaking rate or a font: read them from the text, the voice and the machine.
- Sourcing from the model's memory. Search, read, date, cite.
- Three beats in a row with the same layer and device (outside dialogue).
- A faceless, templated series: platforms name it. Keep the frame, vary the situation, the hook and the treatment.
- Regenerating a cast sheet mid-series, or judging an episode on its own instead of against the set.
- AI-written punchlines nobody rewrote.
- An AI "expert" persona on health, legal, finance or politics without the user's recorded decision.
- Copying a named channel's identity, a brand's marks, or any licensed code. Take the technique.
- Reusing one look across unrelated videos, or letting a support asset (a mascot, a host backdrop) carry another video's palette.
- Reading the reference scan as a template to copy instead of a map of what to do differently.
- Claiming a model or tool in the final note that `provenance.json` does not show.
- Working around a permission the host denied instead of reporting it.

## Done means

`master.mp4` passes `qc_master.py` or each failure is explained; every beat was looked at and the bar above is
met; every number traces to a claim; `provenance.py check` passes and the AI-use statement is in the note; AI
disclosure is decided and recorded; the ledger report matches what you tell the user; the user has the file,
the cost, the sources, the decision record and one line on anything accepted or degraded. For a series:
`series.py check` is clean or its warnings are decided, and the continuity memory is updated.

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
| `references/06-sound.md` | voice direction and the voice ladder, loudness, ducking, effects |
| `references/07-ai-layer.md` | prompting and verifying stills, clips, hosts, voice, music; cost drivers |
| `references/08-governance.md` | authorisation and the gates, the ledger, provenance and disclosure; rights, personas, series |
| `references/09-qa.md` | every checklist, the bar, commands and repairs |
| `references/10-platforms.md` | label policy and lengths; safe zones are in `data/platforms.json` |
| `references/11-routing.md` | handing layers to sibling skills; the HyperFrames brief; routes H, F, L and host-plus-overlay |
| `references/12-localization.md` | any video, to confirm the language rules; read fully for non-Latin or right-to-left text |
| `references/13-inspirations.md` | the research behind this, licences, unknowns |
| `references/14-cost-scout.md` | pricing the plan from this environment: probe, sources, pricebook, credits and balance, the questions |
| `references/15-series.md` | any series: frame and payload, the series record, the cast, routes for characters, comedy, memory |
| `references/16-attention-prediction-sota.md` | only when asked to predict or test a cut's attention or retention before publishing: the research, the evidence and a build recommendation |
| `references/20-person-aware-effects.md`, `scripts/person_fx.py`, `person_track.py`, `fx_core.py`, `fx_looks.py`, `fx_ui.py`, `fx_registry.py`, `fx_assets.py`, `fx_plan_from_beatmap.py`, `data/effects.json`, `data/assets.json` | a person is on screen and an effect should react to them: depth, light, camera, cards, glass; the plan, check and render loop |
| `references/19-hyperframes.md` | motion design and rendering: connecting HyperFrames (local skills, hosted MCP), which workflow for which video, the hand-off |
| `references/18-reference-scan.md` | the automatic look at public reels on the topic: how to run it, what to take, the limits |
| `references/17-ai-models-and-tools.md` | finding and using AI models and tools; what to record; the verified talking-host recipe; consent and disclosure |
| `scripts/` | `beatmap_lint`, `capability_probe`, `cost_plan`, `ledger`, `provenance`, `reference_scan`, `voice_render`, `voice_check`, `speech_align`, `host_assemble`, `build_video`, `render_html`, `mix_audio`, `encode_master`, `captions`, `layout_check`, `textscript`, `speech_rate`, `style_lock`, `beatmap_to_brief`, `storyboard`, `animatic`, `ui_labels`, `contact_sheet`, `qc_master`, `series` |
| `data/` | `formats.json`, `intents.json`, `identities.json`, `platforms.json`: thresholds live here. Prices do not: they are per episode |
| `templates/faceless/` | the page `build_video.py` fills in: scenes, fitted text, captions; read it only to extend a scene type |
| `examples/` | beat maps that lint clean (`host-broll-skill-demo.json` is the plan of the demo video, `faceless-money-guard.json` a faceless one with scene specs); `host-overlay-composition/` is the host-plus-overlay page; `tests/` pins the invariants |
