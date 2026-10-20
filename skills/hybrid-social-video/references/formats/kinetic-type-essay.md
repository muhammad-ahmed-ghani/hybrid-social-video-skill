# Kinetic-type essay (`kinetic-type-essay`)

Family code-native · tier R0 · 15 to 75 s · 2.7 words/s · gate G1 · cost scout-priced (drivers: voice, music) · build time 10 to 30 min

A faceless voice-over carried by designed typography: each beat is a hero phrase with one supporting device. It is
the cheapest, fastest hybrid format, and so the one most at risk of looking like every other video. Platforms demote
templated, mass-produced output, so vary the identity, the devices and the structure per episode.

## Use when, avoid when

Use for concepts, opinions, myths, lists, quotes, definitions, short essays, "things nobody tells you". Intents:
concept, myth, list, versus, ladder, predict, policy, finance, culture.

Avoid when the viewer needs to see a thing to believe it (a place, a person, a product, a map), when the claim needs data
(use `data-story`), and when you intend to publish a dozen near-identical episodes: that is the template pattern
YouTube's inauthentic-content policy names.

## Look

Creator-shorts, neo-brutalist, swiss-grid, editorial-serif, halftone-pop, glass-keynote, dark-luxe. Hero 140 to 300 px, 60 to
80% of width, one per beat, 1 to 3 words (`04-style-bible.md`). Emphasis tiers: hero, one accent word, base, meta. A
background that is never dead flat: slow drift, texture, parallax. Static grain, not animated.

## Layer mix

code 75 to 100%. Short stock or AI-still interludes up to about 25% for pacing and relief; no AI video. A real number or
quote is shown in code, not described.

## Beat grammar

Each beat is a hero phrase with at most one supporting device: an underline, a shape, an icon, a number, a strike-through
for a myth. The hook phrase is on screen at frame 0 and the voice starts mid-claim. Intents drive the skeleton
(`02-intents-and-scripts.md`): myth labels the claim MYTH on screen and in voice first; list uses numbered cards on one
template, at most 5 items at 60 s; ladder gains layers on one core visual. Hero text equals or abbreviates the narration of
that beat: never a different sentence. Captions are the phrase-level lane, or the hero text itself for that beat, not both.

Vary per episode: identity, the device sequence, the entrance verbs, the layout of the hero (left, centred, stacked), the
palette accent. No two consecutive beats share the same entrance, ease and duration.

## Script voice

Short declarative sentences, the new term at the end where stress falls, one idea per beat, 4 to 10 words, 1.2 to 5 s.
Emphasis words chosen as the surprise, not the subject. A misconception beat in 6 s or less.

## Motion and edit

Word pops timed to the alignment (onset within 1 frame), `back.out(1.4 to 1.7)` on the hero only, plain `power3.out` on the
rest, holds of at least 1.2 s for a hero. Right-to-left languages split by word and stagger from the end, never by character
(`12-localization.md`). Hard cuts on phrase boundaries; at most two transition types; a rehook every 8 to 15 s in longer cuts.

## Sound

Percussive and sparing: pops on the hero word only, a hit on the reveal, a riser into the payoff, a bed 14 to 20 dB under the
voice. Same effect family for the whole video.

## Production route

1. Script, claims, `style.json` from `style_lock.py`, beat map, lint, board, Gate 1.
2. Voice with alignment timings, `spans.json`.
3. Build with `/faceless-explainer` through a BRIEF (`11-routing.md`) or `/general-video` for a custom look; motion from
   `/hyperframes-animation`; caption skin from the chosen identity; fonts bundled.
4. QC: legibility at thumbnail size, safe lanes, hero-per-beat.

## Failure modes

A wall of text; every beat the same pop; hero text that paraphrases the narration (a second script); 4-word-plus heroes that shrink
until unreadable; caption and hero both showing the same words; text over busy footage with no scrim; the same identity and devices
across a whole series; no source for a quoted figure; RTL text split into characters.

## QA specifics

The hero is the biggest changed region; one accent word per 5 to 7 words at most; text sizes at the ladder; contrast 4.5:1; each
beat holds for the reading time; at least three distinct devices across the video; claims cover every factual sentence.
