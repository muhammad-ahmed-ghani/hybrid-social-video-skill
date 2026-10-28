# Flat-vector motion (`flat-vector-motion`)

Family editorial · tier R1 (R2 for ambient clips) · 30 to 90 s · 2.5 words/s · gates G1 plus G2 (style bake-off) · cost scout-priced
(drivers: stills, ambient clips) · build time 30 to 60 min

The big-picture science and "how things work" register: rounded flat shapes, one two-tone shade, no outlines, a
friendly narrator, objects that bounce, orbit and morph. The look is borrowed as an approach, not as any studio's
characters or palette. The reliable way to build it with these tools is vector pieces animated in code, with a
generated image used for pieces, not for the finished motion.

## Use when, avoid when

Use for science, space, biology, economics-for-everyone, climate, anything abstract that a camera cannot film and a friendly
look helps. Intents: mechanism, concept, ladder, numbers (scale), health, culture.

Avoid when the story needs real evidence or real people, when a recurring character set cannot be kept consistent within
budget, and when the topic is sensitive and a cute look would trivialise it.

## Look

Identity `flat-vector` (deep indigo field with yellow, magenta and orange accents, star-field texture, rounded tops, one
darker tone for form, no outlines); alternates `whiteboard-doodle` or `blueprint` for a plainer look. Illustration quality
carries this look: plain shapes alone drift toward generic, so invest in the 3 to 6 recurring pieces.

## Layer mix

ai_image 20 to 80% as separate pieces on transparent backgrounds (or vector output from a model that emits SVG, or icons from a
licensed family), code 20 to 70% (all motion, morphs, labels, counts, parallax, camera), ai_video 0 to 40% only for ambient
loops under code (drifting particles, a slow nebula).

## Beat grammar

Mechanism and ladder skeletons (`data/intents.json`): a question about a familiar thing (H2); the obvious answer or the
misconception; at most 3 causal steps, one state change each; the turn where the simple model breaks; the one-sentence
model and a callback. Objects persist and morph across beats (a bar that is 2019's rent stays 2019's rent). One recurring
character at most per 30 s unless the budget covers an anchor sheet per character. Scale beats use powers-of-ten zooms with a
ruler ("each step is 10x").

## Script voice

Curious, friendly, concrete, second person for novices; analogies flagged with their break; humour only where it does not
trivialise the claim.

## Motion and edit

Buoyant: `back.out(1.4)` 0.6 to 0.9 s on the hero, squash and stretch at most 8%, parallax star drift 2 to 4% per second,
looped breathing on idle characters, zoom-through and camera pans between beats, objects morph instead of cutting. One hero
motion per beat. Entrances come from where the idea comes from. Plain `power3.out` on everything that is not the hero.

## Sound

Warm and playful: pops on the hero, a soft whoosh on zoom-throughs, a riser into the reveal, a bed 14 to 20 dB under the
voice, effects from one family.

## Production route

1. Beat map with `layer: ai_image` for pieces and `code` for motion; claims; lint; board.
2. G2 style bake-off on one beat (3 to 4 looks); lock `style.json`, `art_style.json`, and a character anchor sheet if a
   recurring character exists (one anchor image per character, reused with "do not redesign").
3. Generate pieces text-free, one at a time on a transparent or clean background, JSON-structured prompts; keep per-piece
   consistency with the anchor kit; prefer vector output or SVG icon sets where the model or library offers it, since SVG
   feeds GSAP directly and morphs cleanly.
4. Look at all pieces as a contact sheet; then voice, timings; build the motion in HyperFrames (`/general-video` through
   the handoff, motion from `/hyperframes-animation`); add ambient clips last.
5. QC.

## Failure modes

Characters drifting between frames; an image model drawing labels or counts; a flat look that reads generic (too few
designed pieces); AI video re-lettering or morphing flat shapes; a cute tone on a heavy topic; red text on the navy
without the text-safe variant; the motion reading as slideshow because every beat uses the same bounce.

## QA specifics

The palette and shading rule hold across every piece; recurring characters match their anchor; no generated text; objects
persist across beats; hero-per-beat holds; contrast and size ladder met; at least three distinct motion verbs across the video.
