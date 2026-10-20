# Style bible: lock one look before producing anything

Mixed sources look like a collage of tools unless one look governs them. The style lock
is a small set of decisions made once, written to files, and read by every layer: the code
layer through CSS variables, the AI layer through an `art_style` block, the sound layer
through a motion character. `scripts/style_lock.py` writes all three from
`data/identities.json` so they cannot drift apart.

## Contents
- [The process](#the-process) · [Tokens](#tokens) · [Text legibility](#text-legibility)
- [Canvas, grain and banding](#canvas-grain-and-banding) · [Type and numbers](#type-and-numbers)
- [The fourteen identities](#the-fourteen-identities) · [Choosing](#choosing) · [Icons and brand kits](#icons-and-brand-kits)

## The process

1. Pick an identity by the story's register (below). Brand colours or fonts from the user
   override the identity's accent and type, never its structure.
2. Build the files:
   ```bash
   python3 scripts/style_lock.py list
   python3 scripts/style_lock.py build --identity paper-collage --out episode/
   python3 scripts/style_lock.py build --identity swiss-grid --accent "#0057B8" --out episode/
   ```
   Outputs: `style.json` (tokens, text-safe variants, fonts, texture, motion verbs,
   traps, safe box), `style.css` (variables and a static grain class), `art_style.json`
   (the JSON block for image prompts). A brand accent that fails 4.5:1 as text gets a
   derived text-safe variant; the accent itself stays for fills.
3. When AI imagery defines the look (collage, flat vector, archival, risograph), run a
   bake-off before anything else: one representative beat in 3 to 4 identities, as stills,
   shown at Gate 2. Three or four stills is the whole cost of this step; the cost card lists it as the bake-off line. The human picks by
   eye; you do not.
4. Lock. After approval the three files are read-only inputs. A style change after G2 is a
   new gate, because every AI asset depends on it.

For each AI asset the prompt carries `art_style.json` verbatim. Pass a style reference
image labelled "style swatch only" so the model reads it as how to render, not what to
draw. See `07-ai-layer.md`.

## Tokens

Seven tokens, and nothing else in the composition: `bg`, `surface`, `ink`, `muted`,
`accent`, `accent2`, `signal` (semantic up/down or good/bad, only when the claim has a
direction).

- Proportion: about 60% `bg`, 30% `surface` plus `ink`, at most 10% `accent`. The accent
  lives where the eye must land. If more than about 15% of the frame is accent, nothing is
  highlighted.
- One accent hue means "the thing this video is about" for the whole episode: the line,
  the bar, the underline, the word. Red and green alone fail colour-blind viewers; add
  arrows or labels, or use blue and orange.
- Fewer colours: at most 3 data colours plus grey. Show shades, not hues. Emphasise one
  mark, grey the rest, and de-emphasise by opacity (30 to 40%) rather than by a new hue.
- Contrast targets: body text 4.5:1 or better; text at about 66 px regular or 52 px bold or
  larger may be 3:1 at 1080 wide; data marks 3:1; muted text stays at 4.5:1. If an accent
  fails as text, keep it for fills and use its text-safe variant for type. Check any pair:
  `style_lock.py contrast --fg "#E4572E" --bg "#F4EBDD"`.

## Text legibility

Palette contrast does not hold against moving footage. A black scrim of alpha a over pure
white footage gives white text: 0.30 -> 2.1:1, 0.40 -> 2.9, 0.50 -> 4.0, 0.55 -> 4.7,
0.60 -> 5.7, 0.70 -> 8.5. Minimum alpha: 0.42 for 3:1, 0.54 for 4.5:1, 0.65 for 7:1.

Strategy ladder: calm footage behind the text zone; a gradient scrim of 0.55 or more at
the text; a hard-offset or soft shadow; an outline stroke (`-webkit-text-stroke` with
`paint-order: stroke fill`, about 7 to 8% of font size); a solid text box on the busiest
footage. Yellow text needs 0.6 or more, or a stroke. Glass panels pass only on some
backgrounds (white text on a 0.38 navy tint is 2.47:1 over white): raise the tint to 0.5 to
0.6. Test text against the real background in every scene.

## Canvas, grain and banding

- Never pure black or pure white as the dominant canvas: `#0A0A0A` to `#111111` and
  `#F2F2F0` to `#FFF1E5`. Medium-brightness canvases leave no contrast headroom, and both
  TikTok and Reels draw white UI on the right and bottom.
- One canvas family per episode. Switch only for a deliberate register shift (a flashback,
  a quote card) and return within one beat. Mixing more than two identities reads as
  templated or incoherent.
- Smooth dark gradients band badly after the platform's re-encode. In a synthetic test
  (540x960 gradient, second-generation low-bitrate encode), the longest flat band was 520
  rows of 960 with no noise, 560 with animated grain (the re-encode destroyed it), and 28 to
  82 with static fixed-pattern noise at strength 8 to 12. So bake anti-banding grain as a
  static overlay (PNG or SVG `feTurbulence`), never an animated one; animated grain also
  inflated a test master from 11 KB to 11 MB. Best fix is design: avoid large smooth dark
  gradients and use texture or noise-rich footage as the canvas. One check after encode: the
  longest flat plateau on any smooth gradient stays under about 100 of 960 rows. This is one
  synthetic test: confirm on real footage.
- A single grain and grade overlay above AI, stock and capture layers, below the type, is
  the cheapest way to make them one film.

## Type and numbers

- Size ladder at 1080 wide (a phone shows it at roughly 2.8 px per point): hero 140 to 300
  px (one per beat, 1 to 3 words, 60 to 80% of width); headline 78 to 130; captions 48 to 72
  (56 to 72 typical); kicker 44 to 56 uppercase; chart labels 40 to 44 minimum; source line
  36 to 40 minimum. Nothing a viewer must read goes below 36 px.
- Emphasis tiers: T0 hero (1 per beat), T1 one word per 5 to 7 words in accent or weight,
  T2 base, T3 meta (never animated hard). No more than three sizes and two large elements.
- Edit the copy to fit the frame rather than rescuing it with tiny type or tight tracking.
  Break by meaning, never leave a number apart from its unit, use `text-wrap: balance` on
  hero stacks, never hyphenate hero text.
- Animated numbers jitter in fonts without tabular figures. Measured: Poppins, Oswald,
  Anton, DM Serif Display, Fraunces and Patrick Hand ignore `tabular-nums` (16 to 49% width
  change between "1111" and "8888"); Inter, Montserrat, Space Grotesk, Plus Jakarta Sans,
  Bricolage Grotesque and Cormorant Garamond work; Bebas Neue, JetBrains Mono and Archivo
  Black are fixed-width by design. The identity file names a `numbers_font` for each look:
  use it for counters, or render each digit in a fixed-width cell.
- Fonts: all families listed in `data/identities.json` are OFL except Luckiest Guy,
  Permanent Marker, Special Elite and Roboto Slab (Apache-2.0, also commercial-safe).
  Bundle the font files; do not fetch from a CDN at render time (determinism).
- Right-to-left and Indic type: `12-localization.md`.

## The fourteen identities

Hex values are design proposals; contrast ratios are computed. Full tokens, fonts,
texture recipes, motion verbs and traps are in `data/identities.json`; `style_lock.py build`
exports them. None has been A/B tested for retention.

| Id | Register | Palette (bg / ink / accent / accent2) | Hero type | Texture | Motion character |
|---|---|---|---|---|---|
| editorial-serif | journalism, economics, history | `#FFF1E5` `#1A1817` `#990F3D` `#0F5499` | Fraunces + Inter | paper noise 10% | unhurried; `power3.out`, rules and line reveals |
| newsroom | current affairs | `#0B1F3A` `#FFFFFF` `#FFD400` `#E10600` | Oswald + Source Sans 3 | plate gradient | fast; `expo.out`, slams and angled wipes |
| creator-shorts | hosted shorts, opinion | `#1C1C24` `#FFFFFF` `#FFE600` `#FF2D55` | Anton + Montserrat | stroke and shadow | percussive; `back.out(1.7)` on the hero word |
| tech-terminal | software, AI | `#0A0E14` `#D6E2F0` `#39FF88` `#4CC2FF` | JetBrains Mono + Space Grotesk | scanlines, grid | discrete; type, scan, decode |
| blueprint | how it works | `#0F3D7A` `#F2F7FF` `#7FDBFF` `#FFD166` | Share Tech Mono | two-level grid | drafting; stroke draws, dimension lines |
| paper-collage | human stories, culture | `#D9C7A3` `#2B2118` `#E4572E` `#2E86AB` | DM Serif Display + Caveat | kraft noise 16%, torn edges | stop-motion at 8 to 12 fps |
| halftone-pop | pop-science, comic | `#FFF4D6` `#111111` `#E8262D` `#0074D9` | Bangers + Archivo Black | halftone dots | comic snap; `back.out(2.5)` |
| risograph | culture, art | `#F4EFE6` `#1D2A5B` `#0078BF` `#FF48B0` | Bricolage Grotesque + DM Mono | noise 22%, overprint | print press; misregistration settles |
| flat-vector | science, space | `#001372` `#FFFFFF` `#FBBE00` `#E30050` | Poppins | star field | buoyant; `back.out(1.4)`, objects morph |
| glass-keynote | product, fintech | `#1B1464` `#FFFFFF` `#00C2FF` `#FF6A88` | Plus Jakarta Sans | frosted blur | slow, floaty; rack focus |
| neo-brutalist | startup, opinion | `#FFFDF5` `#000000` `#FFD60A` `#FF6B6B` | Space Grotesk | hard offset shadows | sticker slap; stepped transitions |
| swiss-grid | authority, data | `#F2F2F0` `#0A0A0A` `#E3000F` `#0A0A0A` | Inter Tight + Inter | grid, one red circle | exact; rules extend, no bounce |
| dark-luxe | premium, documentary | `#0A0A0A` `#F3EDE2` `#C8A96A` `#7A1F2B` | Cormorant Garamond | vignette, gold frame | slow; dissolves, glints |
| whiteboard-doodle | education, reasoning | `#FBFBF8` `#1F2A44` `#E63946` `#2A9D8F` | Patrick Hand + Caveat | paper grid | drawn on, in speech order |

Traps recorded while building them: red `#E10600` on navy is 3.33:1 (fill only, or
`#FF4B45`); tomato on kraft is 2.2:1 (ink or `#B8401B`); riso pink and yellow are never
text; neo-brutal coral and blue are fills with black text; `clip-path` on a bar clips its
absolutely positioned labels (clip a background shape instead); deep luxe red is
decoration only; hairline serifs vanish when compressed, so keep heroes at 140 px or
larger.

## Choosing

Pick by topic register, then delivery. Current events and finance: newsroom, editorial,
swiss-grid. Software and AI: tech-terminal, glass-keynote, neo-brutalist. Science and how
things work: flat-vector, blueprint, whiteboard-doodle. Culture, history, food:
paper-collage, risograph, editorial-serif. Hosted shorts and fast opinion: creator-shorts,
neo-brutalist, halftone-pop. Premium product: dark-luxe, glass-keynote. Match the format
too: `vox-collage` is paper-collage by definition; `flat-vector-motion` is flat-vector;
`math-science-manim` takes the palette as a colour map (below).

For maths and science, assign colours to concepts once, write the map into `style.json`
(`color_map`), and reuse it for every shape, label and equation term of that concept.
Never reuse a colour for a second concept and never change the map between scenes. A
common house map: blue main object, yellow active or key term, green good or secondary,
red naive or wrong, grey labels; add no sixth colour.

## Icons and brand kits

One icon family, one stroke weight, one corner style per episode; heavy looks 6 to 10 px
strokes at 1080 wide, hairline looks 3 to 4 px; never mix filled and outline sets.
Licences read from package metadata on 2026-10-20: Lucide ISC; Phosphor, Tabler, Heroicons,
Iconoir, Feather, Bootstrap Icons and Fluent UI icons MIT; Material Symbols, Material
Design Icons and Remix Icon Apache-2.0; Font Awesome Free needs CC BY 4.0 attribution for
icons; OpenMoji is CC BY-SA 4.0 (share-alike: avoid in shipped video without review).

A brand kit is tokens, type, texture, motion verbs and one logo lockup, stored in
`style.json` and `style.css`. Keep the brand bug and logo outside the platform UI zones.
Instagram counts visible watermarks as non-original, so do not burn a platform watermark
into the picture.
