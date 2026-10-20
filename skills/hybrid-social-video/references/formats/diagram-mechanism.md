# Animated diagram / how it works (`diagram-mechanism`)

Family code-native · tier R0 (R1 for illustrated assets) · 25 to 80 s · 2.4 words/s · gate G1 (and
G2 if illustrated assets define the look) · cost scout-priced (drivers: voice, music, any illustrated assets) · build time 15 to 40 min

A causal model installed in the viewer's head: parts, flow, one state change per step. The diagram is
code (SVG and GSAP), so counts, labels and order cannot drift. Illustration, when used, is icons and
texture, never the structure.

## Use when, avoid when

Use for "how does X work": a system, process, mechanism, supply chain, protocol, biological pathway, an
algorithm at the conceptual level, an ELI5 ladder where one core diagram gains layers. Intents: mechanism,
concept, ladder, paper, health, policy (process flow), howto (concept only).

Avoid when the parts are people or places (use `vox-collage`), when a claim needs a photograph, or when
the topic is an equation-heavy derivation (use `math-science-manim`).

## Look

Blueprint, flat-vector, whiteboard-doodle, swiss-grid, editorial-serif. Pin-and-paper and flat looks both
work. One icon family, one stroke weight per episode (`04-style-bible.md`). If the look needs painted or
collage assets, generate icons as stills from `art_style.json`, composite them in code, and keep every label,
arrow and count in code.

## Layer mix

code 70 to 100%; ai_image up to about 25% for icons, textures and backgrounds; ai_video up to about 10% for
an ambient loop under a diagram; stock only as an establishing frame. Registry blocks (flowcharts and
similar) before hand-building.

## Beat grammar

30 s (about 72 words): hook (H1 misconception or H2 question about a familiar object, 12 words or fewer) in 0
to 3 s; frame in 3 to 8 s: the obvious answer or the misconception and a "three steps" promise; body in
8 to 23 s: at most 3 causal steps joined by "because", about 14 words each, one animated state change per
step; turn in 23 to 28 s: where the simple model breaks; payoff: the model in one sentence plus a callback to
the hook.

60 s adds a naming beat (at most 3 parts, each labelled where it sits), 4 or 5 causal steps, an edge case
("why not X?") and an analogy with its break said aloud.

Rules: a parts list is a failure (use cause and effect); at most 3 to 4 new terms per 30 s; pre-teach the
key terms with a label first; label next to the part, not in a legend; one highlight moves per beat, the
rest dims; build one core diagram that gains layers (progressive disclosure) instead of a new diagram per
beat; the diagram state at each beat equals the narration (step count matches).

## Script voice

"Because A, B." Concrete instance before abstraction. One analogy at most: map relations, say where it breaks
in one sentence, give its elements one icon and colour. Flag simplifications in the script ("roughly") and
keep the limitation that changes the conclusion.

## Motion and edit

Stroke draws 0.6 to 1.4 s `power1.inOut`, labels land after their lines, dimension lines extend then the
number fades in 0.2 s later. Object persistence: a part keeps its identity across beats; transform instead of
replacing. Entrances from where the idea comes from. A beat is 2 to 7 s. See `05-motion-and-edit-grammar.md`.

## Sound

Soft ticks as connections complete, a hit when the model closes, otherwise a quiet bed. Silence before the
turn.

## Production route

1. Beat map: each beat names its diagram state ("pump opens, arrow A to B draws") in `visual`; claims for every
   factual relationship.
2. Voice, timings, `spans.json`.
3. Build: `/faceless-explainer` ships blueprint-style shot shapes and a pin-and-paper preset; use it through a
   BRIEF (`11-routing.md`), or `/general-video` for a custom diagram. Motion rules from
   `/hyperframes-animation`. SVG icons from a licensed family, or R1 stills from `art_style.json`.
4. Check step count against narration, then QC.

## Failure modes

Parts list instead of mechanism; more than 4 new terms in 30 s; unflagged analogy installing a new
misconception; decorative b-roll under a factual explanation; a generated diagram (counts and arrows drift:
seven steps became nine cards in one test); labels in a legend; an illustration that implies detail the claim
does not support; the viewer feels they understood but did not (misconception beat missing).

## QA specifics

Step count equals the narration; every label sits next to its referent; the hero is the biggest changed
region; contrast and size ladder met; the diagram persists across beats; claims cover each causal link; the
payoff is one sentence.
