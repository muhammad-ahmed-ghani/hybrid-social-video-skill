# Person-aware effects: graphics that know where the speaker is

A host (real or generated) is the strongest layer a short video has, and most overlays treat the footage as a flat picture: a title lands on the
face, a card floats in front of the head, a zoom ignores where the person is. This layer reads the footage first. It finds the face, the head top,
the shoulder line and a soft matte of the person in every frame, and then draws with that knowledge: a word sits **behind** the head, a card follows the
face and never covers it, a light leaves the speaker lit and the room dark, the camera pushes toward the eyes while the room defocuses.

## Contents
- [When to use it](#when-to-use-it) · [Setup](#setup) · [How it works](#how-it-works) · [The loop](#the-loop)
- [Plans and word cues](#plans-and-word-cues) · [Choosing effects](#choosing-effects) · [The effects](#the-effects)
- [Rules](#rules) · [With HyperFrames and the other routes](#with-hyperframes-and-the-other-routes) · [Limits and fixes](#limits-and-fixes) · [Provenance](#provenance)

## When to use it

Use it when a **person is on screen** and an effect should react to them: `host-broll`, `talking-head-package`, any generated or recorded speaker. It adds
depth (type behind the head, graphics around it), emphasis (punch-ins, light, stamps) and proof (a figure that counts up beside the face) without touching the
audio. It does not replace the story, the claims or the cost gate: the beat map decides what is said and shown; this layer decides how it sits around the person.

Not for: footage with no person (use the code layer), a rough cut (editing is out of scope), or a video that already has all the motion it needs. Three effects
in a 30 s reel is plenty; the aim is to make the moments that matter land, not to decorate.

## Setup

```bash
python3 scripts/person_fx.py doctor            # what is missing
pip install numpy opencv-python pillow onnxruntime faster-whisper   # the first three are required; onnxruntime gives the real matte; faster-whisper gives word times
python3 scripts/person_fx.py doctor --fetch    # downloads the matting and face models and the fonts, about 28 MB, once
```

Run these yourself when the host's permission prompt allows: it is the user's consent for a pip install and a download from the model providers. The files go to
`~/.cache/hybrid-social-video` (override with `HSV_CACHE`), pinned by size and sha256 in `data/assets.json`, and are never stored in the skill. Offline is a
valid state: the fonts fall back to system fonts and the matte to a rougher one (the probe and `check` say so). `capability_probe.py` prints a `person-aware effects`
line.

## How it works

1. **Track** (`scripts/person_track.py`). A portrait-matting network (MODNet, ONNX, CPU) gives a soft person matte, sharpened with a guided filter so the edge
   follows the hair. A face detector (YuNet, then a Haar cascade) gives the face box; the head top and the shoulder line are read off the matte. Every other frame is
   tracked (15 fps) and interpolated; the face numbers are smoothed with a forward and backward filter so the result is steady and has no lag. About 0.15 s per
   tracked frame at 540 x 960; cached per file, so a second run and every check frame are free.
2. **Layer** (`scripts/fx_core.py`). Everything an effect draws goes through one compositor with three depths: `front`, `behind` (hidden wherever the person is) and
   `guard` (in front, but never over the head). Front layers are measured against the head so the audit can fail a covered face.
3. **Draw** (`scripts/fx_looks.py`, `fx_ui.py`). Each effect is a function of the frame and the time into the effect, so any frame can be drawn on its own: that is what
   makes `check` fast and renders deterministic. Camera effects run first. Glass is real glass: the room behind it is blurred, bent at the rim and fringed, not a
   grey box.
4. **Encode** (`person_fx.py render`). Only frames inside an effect window are touched; the rest pass through. The soundtrack is copied, never re-encoded when it is AAC.

## The loop

```bash
python3 scripts/person_fx.py words   host.mp4                       # word times -> host.words.json (or reuse spans.json / timing.json from speech_align.py)
python3 scripts/fx_plan_from_beatmap.py episode/beatmap.json --spans episode/spans.json --words host.words.json --out episode/fx_plan.json
python3 scripts/person_fx.py plan   episode/fx_plan.json host.mp4 --words host.words.json --beatmap episode/beatmap.json   # resolve cues, lint, check numbers
python3 scripts/person_fx.py check  episode/fx_plan.json host.mp4 episode/fxcheck --words host.words.json --beatmap episode/beatmap.json
python3 scripts/person_fx.py render episode/fx_plan.json host.mp4 episode/host_fx.mp4 --words host.words.json --style episode/style.json
```

`check` writes one frame per effect and a contact sheet. **Look at them.** It also measures every effect: how much of the head a front layer covers (a face under a
card fails, exit 1), whether graphics enter the platform's UI bands (a warning), and whether a font fell back. Fix the plan (move it, shorten the text, choose another
effect) and check again; rendering is the last step, and a render is only about a minute for a 35 s clip. `--platform tiktok|reels|shorts|common` picks the safe zones.

A single effect needs no plan file: `person_fx.py one orbit host.mp4 out.mp4 --start 3 --end 6` (add `--still 4.5` for a PNG).

## Plans and word cues

A plan (`hybrid-fx/1`) is a list of effects; see `examples/person-fx/plan.json`.

```json
{"schema": "hybrid-fx/1", "effects": [
  {"fx": "punch-in",    "on": "Stop asking", "dur": 1.3, "zoom": 1.4},
  {"fx": "word-behind", "on": "everything",  "dur": 2.4, "text": "EVERYTHING", "color": "#FFD166"},
  {"fx": "big-number",  "on": "4 layers",    "dur": 3.2, "text": "4", "label": "layers in every frame"},
  {"fx": "orbit",       "start": 20.0, "end": 23.0, "images": "assets/reels"}
]}
```

- `on` is words the speaker says; the effect starts on the first of them (shifted by `lead`, default -0.15 s so it lands as the word is heard). `until` ends it on
  another phrase, `dur` sets a length, `after` skips earlier matches. `start` and `end` are plain seconds. Say the timing the way the speaker says it, not as a number.
- Every other key is an option of that effect (the table below), `images` is a folder of stills or clips (otherwise frames of the video itself are used), and
  `style.json` from the look lock supplies the colours: the effects draw in the video's own palette.
- Effects that move the camera run before the rest; two of them may not overlap. A plan with three of one effect in a row, or four effects at once, is warned about.
- Stack effects freely in time, not in space: one hero effect per beat.

## Choosing effects

Choose by the job of the beat, then vary the family so no three consecutive beats get the same treatment (iron rule 10).

| The beat | Reach for |
|---|---|
| hook, the first 3 s | `punch-in`, `word-behind`, `type-stack`, `spotlight` (look sparkle), `neon-sign`, `dot-build`, `lock-on` |
| a number or a claim | `big-number`, `glass-stat`, `corner-push`, `headline-wall`, `tile-wall`, `count-badge` |
| a myth, a verdict | `stamp`, `room` (paper, red), `before-after`, `progress-glitch`, `tier-list` |
| a how-to, a list | `task-list`, `todo`, `toggles`, `receipt`, `arc-lineup`, `key-rain` |
| social proof, reels | `orbit`, `carousel`, `reel-pile`, `phone-fan`, `grid-place`, `reel-frame`, `comment-sheet`, `follow-tap`, `messages` |
| a name, a quote, a source | `lower-third`, `quote-card`, `cover` (look editorial), `page-cut` |
| emphasis, a pause | `freeze-point`, `scribble`, `slow-push`, `grade` |
| a closing look | `edit-timeline`, `grade` (film-red, noir), `room` |

Pacing: a window of 1.5 to 4 s per effect (each effect lists its best length in `data/effects.json`); an effect lands on the word that names it, not the sentence
after it; leave air between effects.

## The effects

Generated from the registry (`person_fx.py catalog --doc`); `data/effects.json` has the full metadata. Flags: *needs a good matte* means the effect puts something behind the head,
so an approximate matte (no onnxruntime, offline) will look rough.

<!-- effects:start -->
**Type and depth**

| Effect | What it does | Options |
|---|---|---|
| `receipt` | Instructions print out like a receipt, hanging from the top of the frame behind the head. (needs a good matte) | `text`, `total` |
| `type-stack` | Lines of huge type slam in one after another behind the head, alternating colour. (needs a good matte) | `lines`, `text`, `color`, `accent`, `font`, `gap` |
| `word-behind` | A giant word drops in behind the speaker's head and is hidden wherever the head overlaps it. (needs a good matte) | `text`, `color`, `font`, `size`, `lift`, `outline`, `x` |

**Light, room and grade**

| Effect | What it does | Options |
|---|---|---|
| `before-after` | A slider sweeps across the frame: the original on one side, a grade on the other. | `kind`, `only` |
| `grade` | A colour grade over the window, on everything, only the room, or only the person. | `kind`, `only`, `strength`, `vignette`, `grain` |
| `neon-sign` | The lights drop and a glowing neon sign types itself out behind the head. (needs a good matte) | `lines`, `text`, `color`, `font`, `push` |
| `room` | Repaint the room behind the speaker: graph paper, pastel, red, dark or any colour; a giant word can sit behind the head and the person can go black and white. (needs a good matte) | `look`, `color`, `text`, `grade`, `word_color` |
| `spotlight` | Kill the lights and keep the speaker lit; a word can glow behind the head. look=sparkle adds golden rays and twinkling light. (needs a good matte) | `text`, `color`, `push`, `font`, `look` |

**Camera**

| Effect | What it does | Options |
|---|---|---|
| `lock-on` | Corner brackets snap onto the face, a tag appears below, and the camera follows the speaker. | `zoom`, `text` |
| `punch-in` | A fast punch-in on a word, held, then eased back out. | `zoom`, `speed`, `head_at` |
| `slow-push` | A slow cinematic push toward the face while the room melts out of focus. (needs a good matte) | `zoom`, `blur`, `vignette` |

**Cards and reels**

| Effect | What it does | Options |
|---|---|---|
| `arc-lineup` | Numbered tiles fan out in an arc above the head. | `text` |
| `carousel` | Cards spin around the speaker in a 3D ring, then slow to a stop with one card facing the camera. (needs a good matte) | `images`, `count`, `size`, `turns` |
| `count-badge` | A flip clock counts down above the head. | `from`, `label` |
| `headline-wall` | Headlines pile up behind the head, then a total pops in front. (needs a good matte) | `text`, `total`, `label` |
| `key-rain` | Keycaps rain down behind the speaker. (needs a good matte) | `text`, `count`, `color` |
| `orbit` | Cards circle the head: in front at the bottom, behind the head at the top. (needs a good matte) | `images`, `count`, `speed`, `size` |
| `page-cut` | Newspaper pages cut on one word, the word locked in a red box behind the head. (needs a good matte) | `text`, `color` |
| `phone-fan` | Cards fan out like a hand of phones in front, under a two-line headline. | `images`, `text` |
| `reel-pile` | Cards pile up behind the head, one every quarter second. (needs a good matte) | `images`, `size` |
| `tile-wall` | A wall of cards fills the frame behind the speaker while a counter ticks up. (needs a good matte) | `images`, `count`, `label`, `cols` |

**Interface cards**

| Effect | What it does | Options |
|---|---|---|
| `comment-sheet` | A comments sheet behind the head: a comment types itself into the bar, posts, gets a heart, and optionally a reply. (needs a good matte) | `text`, `handle`, `reply`, `count` |
| `follow-tap` | A Follow button pops up beside the head and flips to Following with a tap. | `at`, `text`, `x`, `y`, `color` |
| `lower-third` | A name-and-title bar slides in at lower left, inside the platform's safe lane. | `text`, `color` |
| `messages` | Message notifications pop in one after another as glass cards, stacking down from the top. | `text`, `title`, `y` |
| `progress-glitch` | A progress bar fills, glitches, and the frame breaks apart into shifted slices. | `text`, `y` |
| `quote-card` | A pull-quote card with a big quotation mark, revealed word by word, with an attribution. | `text`, `by`, `pos` |
| `task-list` | An agent task list builds under the chin: each step spins, then ticks green. | `text`, `title`, `pos` |
| `tier-list` | A tier list drops in and an item flies into the top tier. | `title`, `item`, `others` |
| `todo` | A checklist card beside the head ticks items off as the speaker talks. | `text`, `ticks`, `title`, `side` |
| `toggles` | A settings card with switches that flip on, one line at a time. | `text`, `ticks`, `pos`, `color` |

**Data callouts**

| Effect | What it does | Options |
|---|---|---|
| `big-number` | A huge number counts up beside the head with a label and a source line. Use for a claim's figure. | `text`, `label`, `source`, `pos`, `color` |

**Liquid glass**

| Effect | What it does | Options |
|---|---|---|
| `corner-push` | The camera pushes into one top corner and a glass stat card pops beside the head, then the other corner with a bar card. The head stays in front. (needs a good matte) | `text`, `to`, `zoom` |
| `glass-stat` | A liquid-glass stat card under the chin: a label, a number that counts up, a glowing chart. look=bento adds a smoked glass screen behind the head and glass tiles in front. | `text`, `from`, `to`, `kind`, `pos`, `look` |
| `glass-widgets` | Frosted glass widgets float around the head: a stat, a ring, a mini chart, a now-playing pill, and a 'Made with' pill. (needs a good matte) | `text`, `name`, `handle` |

**Frames, marks and covers**

| Effect | What it does | Options |
|---|---|---|
| `cover` | The speaker becomes a magazine cover: masthead behind the head, cover lines around, an issue line and a barcode. look=editorial gives a classic serif cover. (needs a good matte) | `text`, `lines`, `issue`, `color`, `look` |
| `dot-build` | The shot builds itself out of glowing dots, then snaps into the full picture. | `color`, `cell` |
| `edit-timeline` | A dark red film look with an editing timeline, a REC timecode and a glowing playhead. | `text`, `sub`, `tc` |
| `freeze-point` | Freeze the frame and point at the speaker with a hand-drawn arrow and a marker label. | `text`, `color`, `side`, `target` |
| `grid-place` | The speaker shrinks into the centre tile of a 3x3 grid, then eight tiles pop in around with counts on every tile. | `images`, `views` |
| `reel-frame` | The video shrinks into a social card with a handle, side icons and a caption. | `text`, `caption` |
| `scribble` | Marker doodles draw themselves around the speaker: a loose circle, sparks, an underline, stars. | `text`, `color` |
| `split-top` | A headline card (or b-roll still) slides down and pushes the speaker into the bottom half of the frame. | `text`, `hl`, `images`, `tag`, `pill` |
| `stamp` | A big ink stamp slams onto the frame with a jolt. | `text`, `color`, `angle`, `y` |
| `tunnel` | The room tunnels into itself, spinning, while the speaker stays sharp in front. (needs a good matte) | `ratio`, `spin`, `depth` |
<!-- effects:end -->

Named looks: `spotlight` with `look: sparkle` (golden rays and twinkling light), `cover` with `look: editorial` (a serif magazine cover), `glass-stat` with `look: bento`
(a smoked glass screen behind the head and glass tiles in front).

## Rules

1. **The face stays clear.** Everything either sits behind the person or avoids the head. `check` fails an effect that covers it; move it (`x`, `y`, `pos`), shorten
   the text, or choose another. Effects marked as frame treatments (grades, tunnels, a card the video shrinks into) may change the whole picture and are exempt.
2. **Numbers come from claims.** An effect that draws a figure is checked against the beat map when `--beatmap` is given: a number that is in no claim, spoken line or
   overlay is an error. A placeholder is allowed only with `"decorative": true`, and then it must not look like data.
3. **Mock interfaces are mock.** The comment sheets, message banners, follow buttons and tier lists are drawn, with names and text from the plan. They carry no real
   account, and a viewer could take them for a real screen: keep the wording plainly yours, and label anything that could mislead.
4. **No flashes.** Nothing here flashes white; light effects ramp. Do not add a flash to hide a cut or to pass the pacing check.
5. **Zoom is capped at 2x** so the picture stays sharp; deeper punches need a higher-resolution source.
6. **The audio is untouched.** The host's own track is the master clock; effects follow it, never the reverse.
7. **Keep the safe zones.** The right rail and the bottom band of each platform (`data/platforms.json`) are covered by its own UI; `check` warns when a front graphic enters them.
8. **Say it is AI-assisted** when the footage is generated: the matte and face models run locally and are recorded in provenance (below).

## With HyperFrames and the other routes

HyperFrames' `talking-head-recut` draws cards on top of a host video; this layer works inside the picture. They compose, in this order:

```bash
python3 scripts/person_fx.py render fx_plan.json host.mp4 host_fx.mp4          # depth effects, light, camera: in the footage
python3 scripts/person_track.py export host_fx.mp4 --out face.json             # optional: the face track as 0..1 fractions per frame, for HTML to place cards by
# then give host_fx.mp4 to /talking-head-recut as the input video, and let HyperFrames draw its cards, captions and layout on top
```

Do the depth pass first: HyperFrames cannot put a word behind a head, and a card drawn over the footage afterwards still lands where the head is not if it reads
`face.json`. In the built-in host-plus-overlay route (`examples/host-overlay-composition/`) run `person_fx.py` on the host clip before the overlay page is rendered.

## Limits and fixes

| Symptom | Cause and fix |
|---|---|
| Hair or fingers flicker at the edge of a word behind the head | the matte is soft at fine detail; shorten the window, use `lift` to hide less, or choose a front effect |
| A word is cut by a hand or a prop | correct (it is in front of the word); move the word with `x` and `lift`, or time it for when the hands are low |
| "approximate matte" in `check` | no onnxruntime or no network the first time: `pip install onnxruntime`, then `person_fx.py doctor --fetch` |
| Two people in frame | the largest face is tracked; effects follow that person |
| Face not found, the effect sits high | a turned head or heavy occlusion: the head is read off the matte instead; `person_track.py preview` shows what was found |
| A card overlaps the platform UI | `check` warns; lower the effect, or use `pos` above/below |
| Slow on a long clip | track only what you need (the plan's windows are the only frames tracked); a 3 minute clip is about 8 minutes the first time, then cached |
| System font used | the font download failed; run `doctor --fetch` online once |

## Provenance

`person_fx.py render` writes `out.fx.json` beside the video: the effects, the matte and face backends, the local models used (MODNet, Apache-2.0; YuNet, MIT) and any font
fallback. The models are AI models that run on the machine and process the footage but generate no pixels; record them so the statement is complete both ways:

```bash
python3 scripts/provenance.py add --episode EP --role other --ai true --tool person_fx --model modnet+yunet --provider local --runs local \
  --used-for "person matte and face track for overlays" --in-output true --realism none --depicts none
```

Third-party files are listed in `THIRD-PARTY.md`.
