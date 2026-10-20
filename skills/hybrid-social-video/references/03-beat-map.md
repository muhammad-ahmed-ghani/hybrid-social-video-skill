# The beat map: the one artifact everything hangs on

One JSON file, `beatmap.json`, is the plan, the contract with every layer, the
thing a human approves at Gate 1, and the manifest the production steps fill in.
Never fork it. Never keep a second plan in prose. `scripts/beatmap_lint.py`
checks it for free; `scripts/storyboard.py` turns it into the page a human
reads; `scripts/animatic.py` turns it into a watchable draft.

## Contents
- [Why a beat map](#why-a-beat-map) · [Schema](#schema) · [Field rules](#field-rules)
- [Assigning a layer to a beat](#assigning-a-layer-to-a-beat) · [Beat arithmetic](#beat-arithmetic)
- [Overlays vs base layer](#overlays-vs-base-layer) · [Claims](#claims)
- [How the file evolves](#how-the-file-evolves) · [Minimal example](#minimal-example)

## Why a beat map

A script says what is spoken. A storyboard says what is seen. A hybrid video
needs a third thing neither captures: **which layer produces each moment, and
why**. That decision is where money is saved (code is free and exact; AI costs
and wanders) and where quality is won (a number drawn by a diffusion model is
wrong; a rainy street drawn by code is dead). Writing it down per beat forces
the decision before the first paid call, makes it reviewable, and gives the
linter something to enforce.

## Schema

```jsonc
{
  "schema": "hybrid-beatmap/1",
  "meta": {
    "topic": "string, the working title",
    "thesis": "ONE sentence the video proves. If you need 'and', check whether it is two videos",
    "intent": "finance",              // one of the 21 ids in data/intents.json (unknown ids are an error)
    "format": "data-story",           // id in data/formats.json
    "tier": "R0",                     // R0 code | R1 +AI stills | R2 +AI clips | R3 +host
    "assembly": "H",                  // H HyperFrames assembles all | F ffmpeg master with an alpha overlay | L no HyperFrames: your own renderer plus ffmpeg (11-routing.md)
    "platform": ["tiktok","reels","shorts"],
    "aspect": "9:16", "fps": 30,
    "target_seconds": 31,
    "language": "as the user gave it", // literal; the default is the language they wrote in; two languages = code-switched
    "language_tag": "xx",             // optional BCP 47 tag, used for the board's lang attribute
    "wps": 2.5,                       // speech units per second (words, or characters for scripts without spaces)
    "rate_source": "prior",           // prior | measured | engine | user; duration checks only fail a plan once measured
    "number_words": ["..."],          // this language's number words, so E051 can flag a spelled-out number in `text`
    "script_fonts": {"SCRIPT": "family"}, // font per script for non-Latin text; satisfies E080 and E084
    "regulated_topic": "none",        // health | legal | finance | politics | none, judged by you; drives E083 for an AI presenter
    "data_origin": "real",            // real | synthetic | mixed | modelled; synthetic or mixed needs a visible label (E057)
    "reuse_music": false,             // true when a series motif is reused: the cost plan counts no music track
    "series": {"id": "slug", "episode": 3}, // a series episode; series.py writes it
    "cast": ["ana", "ben"],           // character ids in this episode
    "extra_stills": 0,                // stills the plan will generate beyond the beats (the cost card counts them)
    "budget_usd": 1.0,                // hard cap the ledger enforces, set inside the user's authorisation (0 for a free plan); never a guess
    "visual_anchor": "...",           // REQUIRED when any AI layer is used (see below)
    "acronyms": ["NASA"],             // ALL-CAPS words that are legitimately caps
    "disclose": false,                // AI-content label decision, with the reason in notes
    "notes": "capabilities found, accepted warnings, downgrades, approvals",
    "misconception_note": "required when the intent wants a misconception beat and none is marked",
    "style": {"name": "ledger paper", "family": "editorial-flat"},
    "rtl_font": "Noto Naskh Arabic"   // RTL languages only
  },
  "claims": [
    {"id": "c1", "text": "...", "confidence": "primary|secondary|computed|inference",
     "source": "https://...", "source_name": "Reuters", "date": "2026-03",
     "method": "computed claims: formula + every assumption"}
  ],
  "beats": [{
    "id": 1,                          // stable forever: asset filenames key off it
    "role": "hook|context|build|turn|reveal|payoff|loop|cold-open|title|recap|setup|escalate|punchline|tag|cliffhanger",
    "character": "ana",               // who speaks this beat (stories); must be in meta.cast
    "callback_to": {"episode": 2, "beat": 4}, // a series callback; must name an earlier episode
    "punchline_options": ["...", "...", "..."], "punchline_approved": false, // the punchline pass: three options, then the user's pick
    "text": "clean spoken words, digits for numbers, no markup",
    "tts_text": "optional: same words performed (caps, ellipses, v3 tags)",
    "layer": "code|ai_image|ai_video|stock|capture|host|real",
    "layer_why": "one clause: why THIS layer is the reliable one",
    "visual": "one sentence: what the viewer SEES while this is spoken",
    "device": "bar-chart|count-up|timeline|map-zoom|diagram-build|collage-parallax|...",
    "overlays": [{"kind": "stat", "content": "$24K vs $72K"}],  // {"kind": "...", "shows_number": true} declares a custom overlay shows the figure
    "on_screen_text": ["<=5 words"],
    "zone": "safe|top|center|lower|right_rail",
    "claim_refs": ["c1"],
    "mute_proof": true,               // hook only: works with sound off
    "misconception": false,           // true on the "what you probably think" beat
    "sfx": ["hit@0.0"],
    "hold_seconds": 0.6,              // silent hold after the words
    "est_seconds": null,              // override words/wps when you know better
    "ai": {"prompt": "...", "motion": "...", "style": "...", "text_ok": false},
    "depicts_real": "none|person|event|place",
    "label_synthetic": false,
    "clip_seconds": 5,
    "est_cost_usd": null,
    "number_is_decorative": false, "claim_exempt": false, "allow_long": false
  }],
  "audio": {"music_brief": "...", "voice": "..."}
}
```

## Field rules

- **Language of free text.** Fields the user reads (`visual`, `layer_why`, `notes`, `punchline_options`, claim `text`) are written
  in the user's language, because the board is what they read. `ai.prompt` and `visual_anchor` are written in the language
  the image or video model follows best, usually English. `text` and `tts_text` are the language of the video.
- **Overlay kinds that count as showing a number** (E031): stat, count-up, countup, bar-chart, line-chart, chart, comparison,
  ranking, scale, number, counter, map-data, table, timeline, equation, data. A kind you invented does not count unless the
  overlay carries `"shows_number": true`.
- **`meta.number_words`** lists this language's number words so E051 can flag a spelled-out number in `text`. Leave out any
  word that doubles as an article or a pronoun in your language (for example "one" or "un"), and for scripts written without
  spaces list only multi-character words, because a single character such as a numeral often serves as an article or a
  measure word and would raise false alarms.
- **Numbers are spoken longer than they are counted.** "75%" is one unit and several syllables in any language. Measure the
  rate on a sample that contains numbers, or set `est_seconds` on number-heavy beats.
- **Platforms** in `meta.platform` should have an entry in `data/platforms.json`; for one that does not, E014 warns and the
  common safe box is used until its zones are read from its own pages.

- **`id`** is permanent. Re-ordering beats never renumbers them; production
  files (`broll/gen_<id>.mp4`) and the cost ledger key off it.
- **`text`** is exactly what is spoken and captioned, in the language of the video. Digits for every number,
  year, range and unit (the transcriber returns digits; spelled-out numbers desync captions). Unicode digit
  shapes are accepted and folded to ASCII when figures are compared with claims. No `[tags]`, no CAPS emphasis: performance markup lives only
  in `tts_text`, so it can never leak into a caption.
- **`visual`** is what is *seen*, not a restatement of the words. If it
  duplicates the narration it is not a visual.
- **`device`** names the explanatory device (a count-up, a timeline, a diagram
  build), not a style. The variety law checks `(layer, device)`.
- **`mute_proof`** on the hook means: a viewer with sound off still gets a
  reason to stay, from a visual device plus <=5 on-screen words.
- **`visual_anchor`** (meta) is one line naming the real subject, place, people
  and the ONLY flags/emblems/uniforms/symbols allowed. It is appended to every
  AI prompt after any enhancer rewrites it. Without it, a generic "crowd with
  flags" scene renders the most common such image the model knows, which is how
  a Pakistan story once rendered Palestinian flags. Minimum: the topic's own
  nouns, reused verbatim.
- **`depicts_real`**: set `person` or `event` whenever an AI image would show a
  real, identifiable person or a real event. Photoreal + real + unlabelled is a
  lint error: use a clearly stylised look, real archival or stock, or label it.
- **`est_seconds` / `hold_seconds`**: words set duration (`words / wps`); holds
  add deliberate silence (a turn, a reveal). Never retime audio to fit.

## The `scene` spec (what `build_video.py` draws)

For the faceless route each beat carries a `scene`: the picture, as data, so no page has to be written. `scripts/build_video.py` turns it
into frames with the text fitted inside the safe box at the QA sizes, a slow reframe per beat, captions from the voice's own word
times, and no flash transitions. An item appears at its `at`: a word of the beat (`"stale"`), a word index, or omitted (spread across
the beat). A beat with no `scene` gets kinetic type from its `on_screen_text`.

| `type` | Fields | Shows |
|---|---|---|
| `kinetic` | `lines`: up to 4 strings or `{text, at}` | big type, one line at a time (hook, turn, payoff) |
| `stat` | `value` ("$24K", "72%", "1,250"), `label`, `sub`, `at` | one huge number that counts up from 0 |
| `steps` | `items`: up to 5 `{text, at}`, optional `title` | numbered chips, the latest highlighted |
| `flow` | `nodes`: up to 4 `{text, at}` | boxes joined by arrows, the latest highlighted |
| `compare` | `left`, `right`: `{title, items: up to 3 {text, at}}` | two columns |
| `bars` | `items`: up to 5 `{label, value, at}`, `unit` | exact bars from zero, values counting up |
| `terminal` | `lines`: up to 6 `{text, at}` | a typed command window |
| `quote` | `text`, `by`, `at` | a large quotation |

Rules: every figure in a scene comes from a claim (the code layer draws it, a model never does); keep each item to a few words; the first
item of the first beat appears at once (the hook must work at 0.4 s); a beat longer than about 5 s needs an item or a change every few
seconds, or `qc_master.py` will report a static stretch. A hosted video uses the host-plus-overlay page instead
(`examples/host-overlay-composition/`). See `examples/faceless-money-guard.json`.

## Assigning a layer to a beat

Walk this top to bottom; the first match wins. Details and the failure modes of
each layer are in `00-layer-doctrine.md`.

1. **Does the viewer need to read an exact number, name, label, equation or
   axis?** -> `code` (HTML/SVG/GSAP via HyperFrames, or Manim for maths).
2. **Is it a process, mechanism, comparison, timeline, map or diagram?** ->
   `code` first; `ai_image` only if the *look* (collage, flat-vector) matters
   more than exact geometry, and then labels are still `code` overlays.
3. **Is it a real thing that must be believed?** (a document, a product UI, a
   headline, a filing, a real person's real words) -> `real`, `capture` or
   `stock`. Never synthesise evidence.
4. **Is it atmosphere, place, texture, emotion or an unfilmable-but-visual
   moment** (a quiet street, a lab, a crowd's energy, an era)? -> `ai_image`,
   escalating to `ai_video` only if motion is the point.
5. **Is a human presence what earns the trust or the energy** (direct address,
   the thesis, the payoff)? -> `host`.
6. Still tied? Pick the cheaper layer. You can always upgrade a beat after the
   animatic; you cannot un-spend.

## Beat arithmetic

- `total_units = target_seconds x wps`. A unit is one word, or one character in scripts written without spaces
  (`scripts/textscript.py` reports which). The `wps` in `data/formats.json` is a prior; replace it with the voice's measured
  rate (`speech_rate.py`, then `meta.rate_source: measured`). Until then duration problems are warnings (E013), and once
  measured the linter fails a plan far outside the target. Fix duration in the **script**, never in the audio.
- A beat is one breath, one idea. Typical 1.5-5 s per format band (`data/formats.json`), which is a handful of spoken units.
- Every beat is a self-contained grammatical line. A length trim may remove its neighbours; it must still read correctly.
- Hook <= the format's `hook_max_words` (in units); the scroll decision happens in about the first 2-3 seconds.

## Overlays vs base layer

`layer` is the **base** of the beat; `overlays` are code-layer elements composed
on top. This is the core hybrid move: an AI clip of a cargo ship (base,
`ai_video`) carrying an exact `count-up` overlay (code) for "369 ships". The
lint rule "narration states a number, something in the code layer must show it"
is satisfied by the overlay. Base-layer share (for `mix` limits) is computed on
the base only.

## Claims

Every fact the video leans on gets a `claims[]` entry and a `claim_refs` link.
`primary` = the original source (filing, paper, official data, the person's own
words); `secondary` = reputable reporting of it; `user` = text the user supplied (cite it as such, no URL needed; the linter notes it
as unverified); `verified: false` marks a claim you could not open at the time (offline), which the linter surfaces (E059); `computed` = you derived it
(state the formula and every assumption in `method`); `inference` = your own
reasoning (hedge it in the script: "likely", "suggests"). More than ~30%
inference is a script problem. Dates matter: a 2023 figure presented as current
is a falsehood.

## How the file evolves

1. **Draft** (Gate 1): everything above except asset paths. Lint -> storyboard
   -> animatic -> human approves, or edits the file and you re-lint.
2. **Locked**: after approval, content fields (`text`, `layer`, `visual`) change
   only through a diff the user sees. Cost-driven swaps (AI clip -> stills with
   parallax) are allowed *downward* in cost without re-approval and must be
   logged in `notes`.
3. **Produced**: production adds `assets` (`{vo, visual, overlay}` paths), a
   `spans.json` from real word timings (`[{id,start,end}]`), and ledger rows.
   The beat map stays the source of truth; spans.json is derived.

## Minimal example

See `examples/` for beat maps that lint clean for different formats:
`data-story-compound-interest.json` is a pure-code R0 plan. A hybrid beat looks
like this:

```json
{"id": 4, "role": "build", "layer": "ai_video",
 "layer_why": "container ships at sea cannot be drawn; motion is the point",
 "text": "369 ships sail this route every single day.",
 "visual": "slow push-in on a container ship in the Strait of Malacca at dusk, a rolling counter climbs to 369",
 "device": "count-up", "overlays": [{"kind": "count-up", "content": "369"}],
 "claim_refs": ["c3"], "depicts_real": "place", "clip_seconds": 5,
 "ai": {"prompt": "a laden container ship in the Strait of Malacca at dusk, steady documentary shot, no text",
        "motion": "slow push-in, settles to near-stillness"}}
```
