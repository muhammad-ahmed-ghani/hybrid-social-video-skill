# Layer doctrine: what each layer is reliable for

The whole skill rests on one sorting rule. Classify every beat before you pick
a tool.

- **Truth-bearing**: the viewer will believe or act on its exact content. A
  number, a name, a quote, a place, a product screen, a face, a flag, an axis.
- **Mood-bearing**: it carries feeling, metaphor, era or rhythm. A quiet street,
  an abstract flow, a lab at night, the sense of scale.

Truth-bearing beats go to code, capture, real or stock. Mood-bearing beats may
go to AI. AI is never the only source of a truth-bearing beat. This rule, not
taste, is what makes a hybrid video trustworthy. It also happens to be cheap:
the exact layers cost the least.

## Contents
- [The seven layers](#the-seven-layers) · [Decision table](#decision-table)
- [Routing algorithm](#routing-algorithm) · [Hybrid moves](#hybrid-moves)
- [Making layers look like one film](#making-layers-look-like-one-film)
- [Downgrade rules](#downgrade-rules) · [Template risk](#template-risk)

## The seven layers

| Layer | What it is | Reliable for | Fails at | Billed by | Owner |
|---|---|---|---|---|---|
| `code` | HTML, SVG, GSAP rendered through HyperFrames; Manim for maths | numbers, labels, quotes, charts, maps from real geodata, timelines, diagrams, equations, captions, brand | organic texture, people, places, "feel" | nothing; free to iterate | `/hyperframes` family, a Manim skill |
| `ai_image` | a generated still, often with parallax and grain added in code | atmosphere, metaphor illustration, collage assets, backgrounds, an avatar source | exact data, long text, maps, counts, real faces, logos and flags | the image | image tool plus `07-ai-layer.md` |
| `ai_video` | a 2 to 5 s clip animated from an approved still | motion that carries meaning: abstract flows, mood, a slow establishing move | text, hands, speech, continuity across cuts, exact camera moves on some models | the second of clip, plus its starting still | video tool plus `07-ai-layer.md` |
| `stock` | licensed footage or photos | accurate generic places, people at work, nature, emotion with a real human | a specific named place or person unless the clip is that thing | the licence, if any | `/media-use`, Pexels, Pixabay |
| `capture` | screen recordings, page and app captures | a product UI, a website, a filing, a headline, a code diff, evidence | anything you cannot legally show | nothing | `/website-to-video`, `/pr-to-video`, browser capture |
| `real` | the user's footage, archival material with rights | a person's actual words, a place, a result | nothing: it is the proof | nothing; rights may cost | `/talking-head-recut`, `/embedded-captions` |
| `host` | a presenter on screen | trust, energy, direct address, the thesis and payoff | long uninterrupted shots; hands; lip-sync drift on some engines | the second of voice-over it covers | `explainer-reel-skill`, a real recording first |

## Decision table

P primary, S secondary (needs QC or a supporting layer), X do not use.

| Content need | code | ai_image | ai_video | stock | capture | real | host |
|---|---|---|---|---|---|---|---|
| a statistic or big number | P | X | X | - | S (real dashboard) | - | S says it, overlay shows it |
| a quote | P | S background only | X | S background | S screenshot of the source | S clip of the speaker, licensed | S |
| a map | P from real geodata | X labelled; S decorative globe | X | S aerial of a region | S real map UI | - | - |
| a process or flow | P | S icons only | X | - | - | - | - |
| a timeline | P | S illustrative era thumbnails | X | S archival | - | S archival | - |
| a chart | P | X | X | - | S real dashboard | - | - |
| a comparison A vs B | P layout | S matched illustrations | S matched clips | S | S | S | - |
| a real person's face | - | X | X | S with a release | - | P with rights | S only the user's own consented twin |
| a historical figure | S type or silhouette | S stylised, labelled as such | X | S public domain | - | P archival, credited | X |
| a real place | S map pin | S generic unnamed place | S generic establishing shot with no claim | P | - | P user's own | - |
| an abstract concept | S generative geometry | P metaphor in the style lock | P short loop | S | - | - | - |
| a product UI or demo | S stylised HTML mock | X invents UI text | X | - | P real recording | - | S |
| a before and after | P reveal between two real frames | S stylised pair from one anchor | S abstract transformation | - | P | P | - |
| an emotional beat | S type and colour | S faceless or back-view | P 3 to 5 s, no faces, hands or speech | P real human | - | P | S |
| generic b-roll under narration | S | S still with Ken Burns | P cheap tier, 2 to 4 s | P | - | S | - |
| hands doing something | - | X | X | P | P if software | P | - |
| a logo, flag or emblem | P official SVG | X | X | S | S | S | - |
| maths, physics, geometry | P Manim | X | X | - | - | - | - |
| captions, lower thirds, CTA | P | X | X | - | - | - | - |
| the presenter | - | S avatar source | S native-audio, last resort | - | - | P real recording | P consented twin or photo avatar |

Why the X marks: a leading image model's own best self-reported infographic
factuality is about 0.52, charts show duplicated axis ticks and values that change
between runs, and a seven-step prompt has produced nine cards. Video models invent
extra label text on products. Models regress to the most common visual prior, so a
generic crowd scene gets another country's flags. No source tested AI map accuracy,
so treat it as unreliable. Details and sources: `07-ai-layer.md`.

## Routing algorithm

1. Mark each beat truth-bearing or mood-bearing.
2. Truth-bearing: code first, then capture, then real or stock. If none is
   possible, drop the beat or soften the claim in the script.
3. Mood-bearing: take the cheapest layer that matches what the narration says. Stock
   if an accurate shot exists; else an AI still with parallax and grain; else an
   AI clip, and only when motion adds meaning.
4. Anywhere a face speaks: real recording, then a consented digital twin, then a
   photo-driven avatar, then a native-audio presenter. Never more than about 12 s
   without a cutaway.
5. Everything the viewer must read is composited in code, last.

## Hybrid moves

These are the combinations that justify the word "hybrid". Write them as a base
`layer` plus `overlays` in the beat map.

| Move | Base | Overlay | Example |
|---|---|---|---|
| Exact number on a living image | ai_video or stock | count-up, stat | "369 ships a day" over a slow shot of a strait |
| Evidence with emphasis | capture or real | highlight box, zoom, redaction bar | a filing with the key line circled |
| Collage in motion | ai_image cut-outs | code parallax, labels in framed carriers, map lines drawing on | the Vox register |
| Host with insets | host | chart, quote card, picture-in-picture | explainer-reel style |
| Abstract motion under type | ai_video loop | kinetic type, captions | a mood beat with one hero word |
| Diagram on texture | ai_image paper or blueprint background | SVG diagram built on the beat | how a process works, in a look |
| Real clip, designed frame | real | lower third, pull quote, progress bar | `talking-head-package` |

## Making layers look like one film

Mixed sources look like a collage of tools unless something unifies them. The code
layer is the cheapest unifier:

- One typeface stack and one accent colour across every overlay.
- One grain and grade pass over everything below the type (a single overlay, so
  AI, stock and capture share a surface).
- One motion vocabulary: the same easing, durations and settle behaviour everywhere
  (`05-motion-and-edit-grammar.md`).
- One style lock for every AI asset (`04-style-bible.md`).
- Same framing rules: subject in the safe region, lower third clear for captions.

## Downgrade rules

A beat that fails twice moves down in cost, it does not go round a third time:

AI clip -> AI still with parallax and grain -> stock or capture -> code (type, diagram
or a held frame) -> cut the beat and shorten the script.

Record the downgrade in the beat map. Downgrades never need re-approval; upgrades do.

## Template risk

Platforms demote repetitive, templated, mass-produced content, and YouTube's policy
says so in terms (see `10-platforms.md`). A hybrid reel whose beats are specific to
its script is the opposite of a template. A hybrid reel that reuses the same chart
shell, the same stock clips and the same caption look for every topic is a template.
Vary structure per episode (format, layer mix, device sequence, palette), not just
assets, and let the story choose them.
