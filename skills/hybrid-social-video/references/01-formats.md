# Formats: choosing one

Fifteen formats in five families. Each has a file in `references/formats/` with the layer mix, beat grammar, motion,
sound, production route and failure modes. Choose the story (`02-intents-and-scripts.md`) first, then pick the format by
what you can show, then by budget and platform risk. The thresholds each format is linted against live in
`data/formats.json`.

## Contents
- [Choose by what you can show](#choose-by-what-you-can-show) · [The catalogue](#the-catalogue)
- [Pace by family, measured](#pace-by-family-measured) · [2026 platform status](#2026-platform-status)
- [Combining formats](#combining-formats) · [Formats not offered](#formats-not-offered) · [When none fits](#when-none-fits)

## Choose by what you can show

Walk down; stop at the first yes.

1. A real person on camera, or the user's own footage? `talking-head-package` (footage exists) or `host-broll` (generate
   a presenter, with consent).
2. A real screen, product, site, PR or document you may capture? `screen-demo` (software), `map-evidence` (documents and
   places), `news-brief` (current events).
3. The thesis is a number, comparison or trend? `data-story`.
4. The idea is geometry, an equation, an algorithm, or a simulation? `math-science-manim`.
5. The idea is a mechanism with parts and flow? `diagram-mechanism` (exact) or `flat-vector-motion` (friendly, illustrated).
6. The story has a throughline and human or historical stakes? `vox-collage` (stylised, no real-evidence need) or
   `archival-documentary` (real archival available).
7. A concept, myth, list or opinion with nothing to show? `kinetic-type-essay`, or `chat-dialogue` when it is
   naturally a question and answer.
8. A recurring cast, a comedy or a cartoon, or a show with episodes? `comedy-sketch` (a joke engine, punchlines a human
   approves) or `cartoon-episode` (puppets animated in code), with the series rules in `15-series.md`. Any other format can
   also be a series: the series layer sits above the format.

Then check budget (tier), platform risk (below) and the languages involved (`12-localization.md`).

## The catalogue

| Format | Family | One line | Base layers | Tier | Length | Gates |
|---|---|---|---|---|---|---|
| `data-story` | code-native | one surprising number or comparison, drawn exactly | code | R0 | 20 to 75 s | G1 |
| `math-science-manim` | code-native | the picture first, the equation second; Manim or KaTeX | code | R0 | 30 to 90 s | G1 |
| `kinetic-type-essay` | code-native | faceless voice-over carried by designed type | code | R0 | 15 to 75 s | G1 |
| `diagram-mechanism` | code-native | parts, flow, one state change per step | code, ai_image icons | R0 to R1 | 25 to 80 s | G1 |
| `screen-demo` | code-native | real captured screens with code callouts | capture, code | R0 | 20 to 90 s | G1 |
| `chat-dialogue` | code-native | an explanation as a message thread | code | R0 | 15 to 60 s | G1 |
| `vox-collage` | editorial | paper-collage story, assembled in code from AI cut-outs | ai_image, code | R1 to R2 | 30 to 90 s | G1, G2 |
| `map-evidence` | editorial | maps and documents carry the argument | code, real, capture | R1 | 30 to 90 s | G1 |
| `archival-documentary` | editorial | real archival first, slow, honest about what is real | real, stock, ai_image | R1 to R2 | 30 to 90 s | G1, G2 |
| `flat-vector-motion` | editorial | rounded flat illustration, animated in code | ai_image, code | R1 to R2 | 30 to 90 s | G1, G2 |
| `host-broll` | presenter | host plus AI b-roll, evidence cards, kinetic captions | host, ai_video, code | R3 | 20 to 75 s | G1, G2, spend card |
| `talking-head-package` | presenter | existing footage plus designed graphics and captions | real, code | R0 | 20 to 180 s | G1 |
| `news-brief` | reporting | what happened, why it matters, known versus not known | code, stock, real | R1 | 25 to 75 s | G1 |
| `comedy-sketch` | narrative | a comic engine with a recurring cast; the punchline is approved by a human | ai_image, code, ai_video | R1 | 20 to 75 s | G1 with the punchline pass; series gate |
| `cartoon-episode` | narrative | a recurring cast of cut-out puppets animated in code | code, ai_image | R1 | 25 to 90 s | G1; series gate |

## Pace by family, measured

Own measurements on 2026-10-20: 48 recent YouTube Shorts from 17 channels (3 per channel, mostly), shot detection with
hard cuts only (slow zooms, dissolves and morphs are under-counted; animated charts and strobing are over-counted) and
words per minute from captions (n=31, manual captions are about plus or minus 10%). Illustrations, not channel norms.
Overall medians: average shot length 5.4 s, narration 201 wpm. The sample is English-language channels; the cut rates carry
over, the words-per-minute figures do not, so measure your own voice (`speech_rate.py`).

| Cluster | Examples (median average shot length) | Narration | Fits formats |
|---|---|---|---|
| ultra-fast demo and meme | Mark Rober 1.1 s, Fireship 1.8 s, Veritasium 2.2 s, Cleo Abram 2.4 s | 177 to 246 wpm | `host-broll`, `screen-demo`, `kinetic-type-essay` (fast) |
| fast news and analysis b-roll | Bloomberg 3.3 s, Economics Explained 3.9 s, Vox 3.9 s, Half as Interesting 5.3 s, NYT 5.6 s, Axios 5.8 s | 134 to 221 wpm | `news-brief`, `map-evidence`, `data-story` |
| steady | Kurzgesagt 7.2 s, Hormozi 7.3 s, Johnny Harris podcast clips 7.1 s | 153 to 256 wpm | `flat-vector-motion`, `talking-head-package` |
| zero-cut single take | MinutePhysics, RealLifeLore map Shorts | 164 to 252 wpm | `math-science-manim`, `diagram-mechanism` (continuous motion), animated maps |

The safe default for content that introduces new terms is 150 to 175 wpm (2.5 to 2.9 words per second): faster delivery
raises overload unless the visuals carry the load. Families that speak at 200 wpm or more are demo, meme and opinion formats
where the picture does the explaining. The long-form sources cut slower than Shorts (Vox Atlas 2.3 to 4.1 s, 142 to 180 wpm;
Atlas is a 6 to 12 minute format, median 9.1 minutes), and one open-source collage pipeline's own examples ran 5.0 s shots at
about 124 wpm: slower than measured vertical explainers. The `beat_seconds` band for each format in `data/formats.json` follows
this: host reels 1.2 to 3.5 s, data stories 1.5 to 6 s, maths 2 to 9 s.

Vertical needs native recomposition, not a crop: a 16:9 slide on a white canvas performed at a fraction of its channel's
long-form views in one report, while Kurzgesagt, MinutePhysics and Economics Explained recompose for vertical.

## 2026 platform status

Platforms write policy against templated, mass-produced, reused and undisclosed-synthetic content, not against AI as such
(`08-governance.md`, `10-platforms.md`). One audit counted 59% of a fresh TikTok feed as AI slop, with History at 33.5% and
Science and Education at 35.0%, against Fashion, Music and Fitness under 2%. The saturated categories are explainer-shaped
(illustration plus voice-over); the safe ones rely on a person or a physical demonstration. A human-made flat-vector video from a
major science channel was mis-flagged as slop by YouTube's detector in 2026, so provenance signals matter even for honest work.

| Format | Status | What protects it |
|---|---|---|
| `host-broll` | edge, if non-sensitive topic and a labelled real or consented host | a named human; AI persona barred on health, legal, finance, politics |
| `talking-head-package` | edge, but the edge is the person and idea, not the caption style | the speaker's original content; subtitles alone do not make a repost original |
| `screen-demo`, `news-brief`, `map-evidence`, `data-story` | edge with original data, reporting and sourcing visible on screen | claims and sources on screen; per-video structure |
| `math-science-manim`, `diagram-mechanism` | edge if the idea is original and correct | exactness; a single-question hook |
| `vox-collage`, `flat-vector-motion`, `archival-documentary`, `kinetic-type-essay`, `chat-dialogue` | exposed: faceless, templated, AI-adjacent categories | per-video variation of structure, visuals and arcs; original sourcing; a named human or an on-camera segment where the topic allows; honest labels |

Cross-cutting rules the evidence supports: vary structure and visuals per video even inside a brand system (a shared intro and
outro are explicitly allowed if the bulk differs); put sources on screen; script for sound-off with plates or 1 to 4 word
captions; keep a human anchor on regulated topics; recompose natively for 9:16; 60 to 90 s is a safe default but not a ceiling
for news and analysis (the Economist's 2026 TikToks run 1.5 to 3 minutes; 55% of weekly TikTok news-video viewers watch clips
under 2 minutes).

## Combining formats

One primary format per episode; borrow devices from at most one other.

| Primary | May borrow from | Rule |
|---|---|---|
| `data-story` | `map-evidence`, `math-science-manim` (compound curves) | the number stays the hero; maps and curves are devices |
| `host-broll` | `data-story` and `map-evidence` overlays, `screen-demo` inserts | overlays are code on top; the host stays under about 12 s per shot |
| `vox-collage` | `map-evidence` (a map piece), `data-story` (a counter) | exact things are code, not collage |
| `diagram-mechanism` | `flat-vector-motion` look | keep the diagram in code and the illustration as pieces |
| `kinetic-type-essay` | `data-story` (one chart beat) | keep one identity |

Never mix more than two identities (`04-style-bible.md`) and never mix more than two formats: it reads as templated or
incoherent.

## Formats not offered

- Narration over unrelated "satisfying" or gameplay footage: no 2026 evidence it outperforms, reused-footage rules are a
  headwind, and reputational risk is real. If a lower panel is wanted, make it relevant (a chart or product UI) under
  `screen-demo` or `data-story`.
- Whiteboard and hand-drawn explainers: a separate skill owns the look (`whiteboard-animation` in the Computer
  environment). The `whiteboard-doodle` identity here is a code-drawn look for `diagram-mechanism` and `math-science-manim`,
  not a hand-reveal generator.
- Mascot-led brand skits: they work only with an ownable character and a product loop. Treat a mascot as the host in
  `host-broll` and plan for the character's anchor sheet.
- Street interviews, podcast clips with visuals, ELI5 expert Q and A: no measured grammar was found. A podcast clip is
  `talking-head-package`; a Q and A written in the abstract is `chat-dialogue`.
- Long-form formats (hours-long chaptered narration): port only the cold open and one reveal, never the structure.

## When none fits

Pick the nearest format, state each deviation in `beatmap.json` `meta.notes`, take the mix bounds of the nearest profile, and
let the linter's warnings be your review. If the new combination recurs, add a profile to `data/formats.json` and a file to
`references/formats/`, and keep `tests/` green (it checks that every format has a file).
