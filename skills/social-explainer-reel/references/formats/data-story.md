# Data story (`data-story`)

Family code-native · tier R0 (add R1 stills only for mood) · 20 to 75 s · 2.5 words/s ·
gate G1 only · cost scout-priced (drivers: voice, music) · build time minutes

One surprising number or comparison, drawn exactly. The story is "the scale of X", a trend,
a ranking, or "it depends on the denominator". Everything the viewer must read is code, so the
layer is cheap and cannot misquote.

## Use when, avoid when

Use when a number, comparison or trend carries the thesis: finance, economics, public data,
"how big is X", energy, demographics, sports and market figures. Intents: numbers, finance,
versus, timeline, predict, news, paper.

Avoid when you have no verified numbers (this format makes weak claims look exact), when the thesis
is about a person or a scene (use `vox-collage` or `archival-documentary`), or when the data only
supports a causal story it cannot prove.

## Look

Newsroom, editorial-serif, swiss-grid, dark-luxe; tech-terminal for tech data; creator-shorts for a
hosted opinion cut. One accent hue marks "the thing the video is about"; everything else is grey.
Bars on a light canvas, lines on dark. Tabular numerals only (`04-style-bible.md`).

## Layer mix

code 85 to 100% by runtime. A short stock clip or AI still may open or interrupt for mood, up to
about 15%, and never carries a number. Maps are code from real geodata. If a beat needs a place that
cannot be mapped, use stock.

## Beat grammar

30 s (about 70 words): hook with the hero number and unit (H3) or a misconception flip (H1) in 0 to 3
s; frame with what it is and one comparator; two data beats (a comparison, then a change over time),
each ending in one annotation; the turn, usually "but per person" or "but the window matters", which
is the sensitivity flip from the dataset method; payoff with the hero number again and the
one-sentence answer; a source chip.

60 s adds how the number is measured and its uncertainty, the normalised version, what would
change it, and a rehook ("but here is the catch") at 25 to 35 s.

Rules: one comparison per number, at most 3 distinct numbers per 30 s, unit and denominator in the
same sentence, an as-of date on anything live, absolute over relative, bars from zero, a source line on
screen for the last 1.5 s of every data beat.

## Script voice

Conversational "you" for novices, concrete comparisons (a thing the viewer has seen), no digits read
as digits ("seventy-three percent" is `tts_text`, "73%" is `text`). Round to the precision the
claim needs. Say "percentage points" for differences of percentages. Beats are 1.5 to 6 s.

## Motion and edit

Bars grow from the zero baseline (0.7 to 1.0 s, `power3.out`); lines draw one at a time; count-ups 1.0
to 1.6 s then hold; the hero takes the accent and the rest drop to 30 to 40% opacity; the annotation
lands on the voice word. One hero motion per beat. Charts that carry more than the limits in
`05b-data-and-math.md` are split into two beats. Hold budgets are in `05-motion-and-edit-grammar.md`.

## Sound

Minimal pulse bed 14 to 20 dB under the voice, a soft tick or one end-tick on count-ups (never a tick per
integer), a hit on the hero number, a riser into the reveal, a 0.3 to 0.6 s dropout before it.

## Production route

1. Script and `claims[]`: every number with source, date, denominator, or a `computed` claim with the
   formula and assumptions. Save the data table as a file: charts are generated from it.
2. Beat map with `layer: code` and a `device` per beat; lint; storyboard; animatic; Gate 1.
3. Voice and word timings; `spans.json`.
4. Build with HyperFrames: write a BRIEF (workflow `faceless-explainer`, or `general-video` when custom)
   and hand it the beat map and `style.json` (`11-routing.md`). Search `/hyperframes-registry` before
   hand-building a chart, count-up or map. Assert chart honesty on the data (bar height ratios).
5. Captions, sound, render, `qc_master.py`, contact sheet, Q14 and Q16.

## Failure modes

Truncated axis; missing denominator; six numbers in one beat; red and green alone for up and down;
a pie with five slices; a count-up that jitters (font without tabular figures); source line missing;
as-of date missing; a mood image that implies a specific; axis rescaling mid-animation. Fix each with
the rule above, not by restyling.

## QA specifics

Bar heights proportional to values within 2%; unit visible with the first appearance of the number; source
chip on screen; numbers in the voice equal numbers on screen; sensitivity flip checked (change baseline,
window, denominator: if the story flips, say so or drop it).

Worked example: `examples/data-story-compound-interest.json`.
