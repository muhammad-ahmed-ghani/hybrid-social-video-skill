# Paper-collage editorial (`vox-collage`)

Family editorial · tier R1 (R2 for 1 to 3 hero clips) · 30 to 90 s · 2.5 words/s · gates G1 plus G2 (style
bake-off; both are essential here) · cost scout-priced (drivers: still count, hero clips) · build time 20 to 45 min

A story told in 2.5D torn-paper collage: a cold open on a concrete fact, a turn to context, an escalating explanation, a
complication, a reframe that returns to the opening with new meaning. In this skill the collage is ASSEMBLED IN CODE from
AI-generated cut-outs: the AI makes the pieces, code does the parallax, the labels, the route lines and the timing. That is
cheaper than animating every still with a video model, it gives true layer control (an image-to-video "living poster" cannot
separate layers), and it keeps every word exact.

"Vox style" names three different things, and this format is only the third: (a) the 2014 to 2020 explainer register of
narrator, motion graphics and archival with no desk and no talking-head interview; (b) the Atlas and Borders map-led register
(use `map-evidence`); (c) the 2026 AI torn-paper collage look that open-source collage pipelines and some creators describe as
Vox-inspired. No primary source ties torn-paper collage to Vox itself: its own 2026 vertical output is a selfie host, a yellow
headline plate and highlighted-word captions. So treat this as a look, make original work, do not imitate any named channel's
branding or reproduce its imagery, and remember the 2026 risk below.

Ideas borrowed from the open-source collage pipeline (MIT, ideas only, nothing copied): the beat map as an approval gate and a
style bake-off on one beat (our G1 and G2); two shots per narration beat, a wide frame with the headline then a detail cut-in
without it, so the picture cuts mid-sentence while the voice runs on; no two adjacent beats using the same camera move and a
static payoff beat; a hard-limited, flat-safe camera vocabulary (static, push in, pull out, pan, tilt, parallax, element); element
motion as a separate axis from camera motion; a fixed look block reused with only the scene, background and headline changing;
a stability-anchor sentence for lettering.

2026 risk: a locked style block reused verbatim on every beat of every video is exactly the "minimal variation across videos"
pattern the platforms name. Keep the grammar and vary the structure, the arc, the accent colour, the pieces and the data per
episode, add original sourcing, and keep a human anchor where the topic allows.

## Use when, avoid when

Use for stories with a throughline and human or historical stakes: why a thing happened, how an institution or
object got to be, a case study, a culture or etymology explainer, a place and its history. Intents: causal, case,
timeline, reveal, culture, myth.

Avoid for data-first stories (use `data-story`), mechanisms (use `diagram-mechanism`), and any story whose real
visuals matter as evidence and would be replaced by invented collage pieces (use `archival-documentary` or
`map-evidence`).

## Look

Identity `paper-collage` (kraft and cream, ink, one accent, torn edges, halftone, tape, a single hard shadow), with
`editorial-serif` or `risograph` as alternates. Cut-outs are individual contour-cut pieces with white sticker borders
and visible fibres, never props printed flat on rectangles. Key terms live in framed carriers (placards, scroll
cards, pins, title panels), never floating text. One accent colour carried through every frame. Not photoreal, not
3D, not glossy: if a frame could be a movie still it is wrong; if it could be a magazine spread it is right.

Adapt the source material to the subject and keep the grammar constant: Tang China gets ink-wash mountains and seal
stamps, a markets story gets ticker tape and engraved crosshatching, a space story gets archival cut-outs on a
blueprint grid. Borders, halftone, tape and the single accent are the style.

## Layer mix

ai_image 40 to 85% (the cut-outs and backgrounds), code 10 to 50% (parallax assembly, labels, route lines and map
pieces, count-ups, captions), ai_video 0 to 35% (hero beats only: a drifting cloud, a route drawing, one living
detail), stock and real up to about 20% (archival cut-outs when a real one exists: prefer real archival for any
real person or event).

Real people and events: archival cut-outs from real sources, or clearly stylised paper figures; never photoreal AI
of a real person or event. Mark such beats `depicts_real` in the beat map (the linter enforces a stylised look or a
label).

## Beat grammar

Cold open (1 beat, hook): a concrete, surprising fact, image or question, started inside the story ("In the
seventh century, Tang China built the largest city on Earth"), never "today we are going to talk about". The turn
(1 beat): the zoom-out signature ("to understand how, you have to go back to ..."). Escalating explanation (50 to
70% of beats): one throughline, each beat makes the viewer slightly smarter, numbers and comparisons to familiar scale.
Complication (1 or 2 beats): the cost or irony. Resolution and reframe (1 or 2 beats): return to the cold open with
new meaning; the last line is quotable.

Budget for 9:16: 30 s is 5 to 6 beats, 60 s is 8 to 10, 90 s is 12 to 14; roughly 25 words per beat. Hook beat 3 s or
shorter. Vary the camera move between adjacent beats and make the payoff beat static. Two stills per beat at most.

## Script voice

Present tense for history ("Merchants arrive from Persia"), concrete over abstract ("two million people"), a long
sentence then a three-word one, second person sparingly. Measured, warm, curious, lightly documentary. Not trailer
delivery. Read each beat aloud: if you stumble, the voice will.

## Motion and edit

Code-driven, collage-physical: pieces slide in from an edge, get pressed down, pinned, and settle; background layers
drift slower than foreground (parallax, 3 to 5% push over a beat); route lines draw on; framed labels land after
their subject; halftone shimmer. Quantise to 8 to 12 fps for the paper feel and land pieces with plus or minus 3
degrees of rotation. Order of assembly within a beat: background, decorative geometry, midground landmarks, main
subject, then labels. Forbidden: 3D rotation, morphing faces, detached hands or floating props, text warping,
unmotivated rise at the end of a clip, camera shake.

If a hero beat uses an AI clip: graphic and editorial motion, one to three controlled living details, one camera move,
settle to a hold. Generate all clips before judging style drift, and retry only the failures.

## Sound

Paper slap and rustle effects on the land frames, a warm instrumental bed 14 to 20 dB under the voice, no sudden drops,
a riser into the reframe, a dropout before it. One continuous voice-over generated once, one bed generated once the
visual rhythm is known.

## Production route

1. Brief, thesis, claims, intent, beat map with `layer: ai_image` (cut-outs and backgrounds) and `code` (assembly,
   labels, route lines); one `device` per beat; lint; board; animatic.
2. Gate 1: the beat map, claims, cost. Nothing is generated before approval.
3. Style bake-off (Gate 2): render ONE representative beat in 3 to 4 candidate identities as stills (the cost card lists them as
   the bake-off line: `cost_plan.py plan --bakeoff N`), show them side by side, let the human choose by eye, then lock `style.json` and `art_style.json`
   (`04-style-bible.md`). Generate the main visual first: it defines the system and carries the hook.
4. Generate cut-outs on a clean or transparent background (a model feature or `/media-use` background removal), one
   JSON-structured prompt per piece with `art_style.json` and the anchor (`07-ai-layer.md`). Consistency comes from the
   style sheet and anchor kit, not luck: verify 3 frames before committing a 12-frame storyboard.
5. Look at the stills as a contact sheet before any clip or assembly. Wrong-country tells and real-person checks apply.
6. Voice, timings, `spans.json`; build the collage in HyperFrames through the handoff (`11-routing.md`); add the 1 to 3
   hero clips last, only where motion adds meaning.
7. QC and review.

## Cost

Stills dominate: a handful of cut-outs per beat, so a 45 s film with 8 beats is about 24 pieces. A hero clip adds a
per-second charge on top of its still. Re-rolling a still costs one image; animating a weak one costs the clip, so fix
stills first. The cost scout prices both (`14-cost-scout.md`).

## Failure modes

Cut-outs that read as rectangles; style drift between stills (no style sheet or mixed model versions); text baked into an
image and re-lettered by a video model; label floating with no carrier; a cold open that begins "in this video";
photoreal AI of a real figure; the collage grammar drifting toward a movie still; every beat the same push-in
(the camera move has no variety); an accent colour that changes between beats; wrong-country symbols in a generic
scene; a map drawn by an image model.

## QA specifics

The accent and palette hold across every frame; borders, halftone and tape present; labels sit in carriers; the hook is
legible on mute; the last line is quotable and echoes the cold open; every real person or event is archival, stylised or
labelled; camera moves vary between adjacent beats; no text from an image model anywhere.
