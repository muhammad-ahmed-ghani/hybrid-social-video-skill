# Math and science, code-rendered (`math-science-manim`)

Family code-native · tier R0 · 30 to 90 s · 2.2 words/s (deliberate) · gate G1 only · cost voice
and music only, scout-priced · build time minutes to an hour including renders

The 3Blue1Brown lineage: the picture arrives first, the equation second, every move explains
something. Pixels come from code (Manim, or HTML with KaTeX for light cases), never from a
diffusion model, because equations, counts and exact geometry are the cases diffusion gets wrong.

## Use when, avoid when

Use for an idea a viewer can see: geometry, graphs and transformations, algorithms, physics with the
right law, probability, a derivation with a few steps, scale and structure diagrams. Intents:
mechanism, concept, ladder, paper, numbers, finance (compound growth), health (risk icon arrays).

Avoid for organic or photographic content, opinion, long derivations (a short has room for one
idea), and when LaTeX or Manim cannot be installed (then use HTML with KaTeX, and say so). The
strongest maths Shorts observed are single-question puzzles with a visual hook, not condensed lectures.

## Look

Dark canvas by default (blueprint, tech-terminal) or whiteboard-doodle for tutoring. The palette is a
colour map from concept to colour, assigned once and never reassigned (`04-style-bible.md`,
`style_lock.py --colormap`). House map: blue main object, yellow active or key term, green
good or secondary, red naive or wrong, grey labels, no sixth colour. Proportional sans for text, LaTeX for
maths, mono only for code.

## Layer mix

code 90 to 100%. A single stock or AI still may open a real-world case. Never AI video.

## Beat grammar

Hook 0 to 3 s: the object already doing its job plus the question in 4 to 8 words, no title card.
Setup 3 to 10 s: one concrete case, colours assigned. Build beats of 6 to 10 s, 3 to 8 of them, one idea
each, one sentence of narration: change 1 to 1.5 s, read 0.5 to 1 s, point 0.5 s. Show the naive attempt
failing, then the repair. Concrete instance, then pattern, then symbol. Payoff with a 1 s breath before
the reveal and the longest hold (3 to 4 s) after it, the last frame answering the first frame's question.
Misconception beat for mechanism, concept and ladder intents.

## Script voice

Narration says why, the visual shows what; do not read the screen aloud. Visual lands 0.2 to 0.4 s
before its word. 130 to 150 wpm, a 60 s short is 6 to 8 beats and about 150 to 200 words. One sentence per
beat. Name the 1 to 3 terms with a label before using them.

## Motion and edit

Moves of 1 to 1.5 s with 0.5 to 1 s holds; 3 to 4 s only at the payoff. One focal winner at full
brightness, the rest at 0.2 to 0.4 opacity, pointing by rectangles and opacity rather than flashes. Transform
objects into their next representation instead of replacing them; demote finished results to a corner.
Equations: break across lines aligned on the equals sign, light terms in the order of understanding.
Stack comparisons vertically. Every rule is detailed in `05b-data-and-math.md`.

## Sound

Minimal bed 14 to 20 dB under a calm voice, almost no effects: a soft tick at a reveal, a riser into the
payoff, silence at the breath before it. Silence is part of the pacing here.

## Production route

1. Script and beat map (R0). Beat `device`s are Manim scene verbs or HTML devices.
2. Voice first with measured durations and word timings (`spans.json`). Never time scenes before the voice.
3. Hand a Manim skill the scene list, narration per scene, colour map, the vertical contract (four config
   values, explicit axes sizes, authored line breaks) and the timing helper (`05b-data-and-math.md`).
   Preflight LaTeX and fonts; pin CLI flags to the installed version.
4. Render drafts at 540x960 and 15 fps, finals at 1080x1920 and 30 fps. One continuous scene per short.
5. Compose captions, brand and the hook text in HTML through HyperFrames; place the Manim render as a
   clip or composite it with a transparent overlay (`--transparent --format mov`). Share the colour map.
6. Verification ladder, then `qc_master.py` and the contact sheet.

## Failure modes

Letterboxed frame from `-r 1080,1920` alone; `Axes()` too wide; `Text` overflow; counters and tick labels
crashing without LaTeX; frame-rounding drift against the voice (a 14.8 s plan rendered 16.0 s);
frame-rate-dependent Euler physics; a z-order bug hiding text; stale CLI flags; slow renders; equations
wider than 9 units; a colour reused for a second concept. Code makes false statements look exact:
spot-check the 2 or 3 most surprising claims against a source and test simulations against an
independent reference.

## QA specifics

Geometry audit of every mobject against the safe rectangle; contact sheet; `freezedetect` with a very low
noise floor; duration against the voice; determinism hash with a fixed seed; a vision-model critic with at
most 2 repair passes; check z-order by eye. Draft and final frame rates must agree.

Combines with `data-story` for finance and with `diagram-mechanism` for structure.
