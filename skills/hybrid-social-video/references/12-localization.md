# Language and script

This skill has no default language and no list of languages. The video is made in the language the user writes
their request in, unless they name another or name two. Everything that depends on the language is read from the
text itself, from the voice, or from the tools in this environment, and written into the beat map. Locale facts below
are from standards pages and Wikipedia (R) unless marked V (verified in a local test); scripting and layout rules are
inference (I) unless marked V. A native reviewer signs off every language before publishing.

## Contents
- [The rule](#the-rule) · [Read from the text](#read-from-the-text) · [Read from the tools](#read-from-the-tools)
- [Fields in the beat map](#fields-in-the-beat-map) · [Adapting, not translating](#adapting-not-translating)
- [Code-switching](#code-switching) · [Right-to-left layout](#right-to-left-layout) · [Type beyond Latin](#type-beyond-latin)
- [Numerals and separators](#numerals-and-separators) · [Locale choices](#locale-choices) · [Cultural pitfalls](#cultural-pitfalls)
- [Voice, captions and timing](#voice-captions-and-timing)

## The rule

1. **The default is the language the user wrote to you in.** Ask only if the request itself is ambiguous: it mixes
   languages without saying which to use, or it names an audience that reads another language. Ask about the market or
   dialect only when it changes the wording (see Locale choices). Never fall back to
   English. A user who names two ("Urdu with some English") has chosen a code-switched register (below).
2. **You talk to the user in that language too:** the intake card, the cost card's questions, the gate messages,
   the notes. The board and the animatic take translated interface strings (`--labels labels.json`, keys in
   `scripts/ui_labels.py`). Script output (lint codes, errors) is for you and stays as it is.
3. `meta.language` holds the language exactly as the user gave it. Optionally `meta.language_tag` holds a BCP 47 tag;
   the board uses it for the page's `lang`. Nothing in a script matches on a language name.
4. AI image and video prompts are written in whichever language the chosen model follows best, usually English; say
   which in `meta.notes`. The linter's prompt checks (E030 text in a prompt, E033 risky scenes) match English wording
   only, so when you write a prompt in another language, review those two things by eye.

## Read from the text

`python3 scripts/textscript.py beatmap.json` reads every string the viewer will hear or read (spoken text, on-screen
text, overlay content) and reports, with Unicode properties and no language knowledge:

| Fact | How it is found | What uses it |
|---|---|---|
| scripts and their share | the first word of each letter's character name | everything below |
| direction: ltr, rtl or mixed | each letter's bidirectional class | E080, the board, the animatic, the HyperFrames brief |
| counting unit: words, or characters | letters in scripts written without spaces (Han, kana, Thai, Lao, Khmer, Myanmar, Tibetan) | every length check: hook size, beat size, on-screen text, the duration estimate |
| fonts that cover every character | a fontconfig charset query, or the files in `--fonts DIR` | E084, the animatic's font |

A font that covers every character is not the same as a font that looks right: render a frame and look. The animatic
picks the first covering font that is not a pixel-map fallback, wraps by measured pixel width so text without spaces
breaks correctly, sizes line height from the font's own metrics (tall scripts need far more than 1.3 em), shrinks text
to fit, and aligns each line to its own direction. Shaping and right-to-left order need Pillow built with Raqm; the script
says so when it is missing.

## Read from the tools

Whether a voice, a transcriber or an avatar engine supports a language is read from the tool's own catalog by the cost
scout and recorded in the pricebook entry (`cost_plan.py add --supports-language "<the language as written>"`). When the
entry has no record, the cost card asks the user; it is never assumed. Even when a tool lists a language, quality varies
and nobody has measured most pairs: play a short sample in the language and have the user listen at the gate.

## Fields in the beat map

| Field | Meaning |
|---|---|
| `meta.language`, `meta.language_tag` | the language as the user gave it; an optional BCP 47 tag |
| `meta.wps`, `meta.rate_source` | speech units per second, and where it came from: `prior` (a format default), `measured`, `engine`, `user`. Duration checks fail a plan only once the rate is measured: `scripts/speech_rate.py measure --audio sample.wav --beatmap beatmap.json --write` |
| `meta.number_words` | the number words of this language (units, tens, hundred, thousand, million, billion) so E051 can flag a spelled-out number in `text`; leave out words that double as articles or pronouns, and for scripts without spaces list only multi-character words; without the list that check is reported as not run |
| `meta.script_fonts` | script to font family, for example `{"ARABIC": "<family>"}`; satisfies E080 and E084 |
| `meta.regulated_topic` | `health`, `legal`, `finance`, `politics` or `none`, judged by you in whatever language the video is in; it drives E083 for an AI presenter |
| `meta.cast_voices` | character id to voice, when there is no series folder |

## Adapting, not translating

A translated script keeps an information gap built for the first audience's prior knowledge, analogies they do not share,
numbers in units they do not use, and visuals with the wrong locale tells.

| Level | What changes | Use when |
|---|---|---|
| L0 | subtitles only | internal, low stakes |
| L1 | translated script, re-timed voice-over | neutral, universal topics |
| L2 | plus local examples, numerals, units, currency, analogies, visuals | default for public content |
| L3 | plus local data and law re-researched, a new `claims[]` | policy, finance, health, news |
| L4 | native re-script from the same thesis and evidence | flagship content, humour, culture |

Checklist: the thesis stays; the hook is rewritten for local prior knowledge; every comparison anchor is swapped for one
the audience knows (their own city's area, not a foreign one); numbers use local units and grouping; claims are re-checked
for local facts; the voice-over is re-timed from a measured sample, not from a word count; visuals are re-checked for
locale tells (`07-ai-layer.md`); idioms are removed or replaced. Law, tax, health systems, holidays and emergency numbers
differ by country: re-research them (L3), do not translate.

## Code-switching

`meta.language` is literal. A single language is written as clean, fluent, grammatical prose with no mixing. Only a
register that names two languages ("Urdu/English", a colloquial blend) invites switching, and then every sentence is still
clean in whichever language it lands in. An unconditional "speak like a bilingual creator" instruction produced broken
English on monolingual reels. Rules (I):

1. Pick a matrix language per video, the grammatical frame, with insertions from the other language for terms that have no
   everyday equivalent. Insertional switching reads and speaks more smoothly than mid-clause alternation.
2. Fix a term policy: the inserted term, or the native term defined once, then consistent. Never alternate two words for the
   same thing inside one video.
3. Switch at clause boundaries for emphasis or quotation; keep numbers and units in one language per sentence.
4. Keep insertions to 1 to 3 words, pronounceable in the voice's phonology; test the voice, because multilingual voices
   over-anglicise or over-adapt inserted words.
5. Choose the caption script per audience and keep it: a blend written in Roman letters has no standard spelling (Hinglish
   and Roman Urdu are examples), so keep a house spelling list; a blend written in the native script embeds Latin-script
   terms as isolated runs (below). Do not write the same word in two scripts within a video.
6. Heavier insertion suits audiences used to it; broader audiences need lighter insertion and native definitions.

## Right-to-left layout

Applies when `textscript.py` reports direction `rtl` or `mixed`.

- Render captions and graphics in HTML and CSS (or a shaping-aware engine) with `dir="rtl"` and `lang` set. A tool with no
  text-shaping engine disconnects or reverses Arabic-script letters.
- Bidirectional text (V, Unicode Bidirectional Algorithm): runs of the other direction inside a sentence reorder as units, so
  a comma or a number can attach to the wrong word. Wrap each opposite-direction phrase, brand name, acronym and number run
  tightly in `<bdi>` or `dir="ltr"` spans; use isolates over older embeddings. This is also how Latin-script words sit inside
  a native-script caption line.
- Mirror the layout: step sequences, progress bars, timelines, list bullets, directional icons, arrows, the lower-third side,
  horizontal bar growth, the stagger order (`from: "end"`), karaoke highlight direction. Numeric axes and mathematical notation
  often stay left to right; confirm with a native reviewer. TikTok ships a mirrored safe-zone layout for Arabic with the action
  rail on the left.
- Never letter-space cursive scripts, never italicise them, and never justify them with gaps; left-align (right-align for RTL).
  Emphasis in such scripts comes from weight or colour. A style rule such as "serif italic for emphasis" applies to Latin text
  only.
- Never bake text into AI images: garbled script. Add it as a code overlay.

## Type beyond Latin

Measured in headless Chromium 1248 (V), on sample strings only. The identity fonts in `data/identities.json` are Latin: choose a
face for each script with `textscript.py`, keep the identity's weight and contrast, record it in `meta.script_fonts`.

- Never split Arabic-script text into characters. Each letter in its own span renders in isolated form and destroys the word;
  GSAP SplitText `type: "chars"` does exactly this. Split by word or line, or reveal the whole line with a mask.
- Devanagari: split by grapheme cluster or word, never by code point (code-point splitting detaches vowel signs). SplitText
  `chars` returned correct clusters; a naive `Array.from(text)` does not; use `Intl.Segmenter` for your own splitter (untested).
- Set `letter-spacing: 0` on Arabic-script and Devanagari text.
- Line height per script, because masks and overflow clip tall scripts. Minimum no-clip line height for the samples: Noto
  Nastaliq Urdu 2.53 em (use at least 2.6), Gulzar 2.61, Noto Naskh Arabic 1.6 (use 1.7), Noto Sans Arabic 1.75 (use 1.8), Amiri
  1.98 (use 2.0 with diacritics), Vazirmatn 1.63, Cairo 1.61, IBM Plex Sans Arabic 1.7, Tajawal 1.71 (its `normal` of 1.2 clips:
  set 1.75 or more), Noto Sans Devanagari 1.33 (use 1.4), Poppins Devanagari 1.61, Hind 1.52, Mukta 1.38, Noto Sans JP 1.37.
  Latin display type can go to 0.9 to 1.0 only if the box does not clip. A line height tuned for Latin in a mask slices tall
  scripts in half: add padding. The animatic reads the same numbers from the font's own metrics.
- A calligraphic style such as Nastaliq is preferred by some audiences but needs size and room: a line occupies about twice the
  vertical space of Naskh (2.5 em versus 1.7 em). Offer a Naskh or sans fallback for small captions and reserve the calligraphic
  face for hero lines. Without such a font installed, text silently falls back to another face.
- CJK: use fonts with the right glyph set, no letter spacing, `text-wrap: balance`, allow `word-break: keep-all` only for
  Korean; Japanese reads at about 4 characters per second on screen, so hold CJK text far longer in character terms. A full CJK
  font can be a 9 MB file: budget font loading.
- Bundle every font file; never fetch fonts from a CDN at render time.

## Numerals and separators

Settle these with the user or a native reviewer per audience; they are choices, not constants.

- Arabic-script text has three digit families: European (0-9), Arabic-Indic (for example Egypt, Saudi Arabia, Iraq) and Eastern
  Arabic-Indic (Iran, Afghanistan). Urdu uses its own shapes for 4, 6 and 7 and the W3C Arabic document does not cover Urdu.
  Default (I): Western digits for pan-regional social video unless the audience is print-style; never use one language's digit
  shapes for another; keep digits consistent between captions and charts. The linter folds Unicode digits to ASCII when it
  compares figures with claims.
- Decimal marks: a comma in Spain, Argentina, Colombia, Chile, Algeria, Morocco, Tunisia, Lebanon; a point in Mexico, Egypt,
  Jordan, Saudi Arabia, UAE, India, Pakistan. Where Eastern Arabic digits are used, the Arabic decimal separator applies.
- Indian grouping uses lakh (10^5) and crore (10^7) in India, Pakistan, Bangladesh, Nepal and Sri Lanka. Say numbers in the unit
  the audience uses and make on-screen digits match the spoken unit.

## Locale choices

Worked examples of the kind of decision a market forces. They are not rules for those languages.

- **Spanish:** choose the target market first (Mexico, Argentina, Colombia, Spain, US Hispanic) and write tú, vos or usted
  accordingly; "neutral Spanish" struggles to sound familiar. Use "mil millones" for 10^9 and "billón" only for 10^12. "Peso" and
  "dólar" are ambiguous across countries: name the country. Day-month-year dates. Do not mix a Castilian voice with Latin
  American text.
- **Arabic diglossia:** the written and media standard differs from what people speak, and less-educated audiences may struggle
  with formal broadcast speech. For wide reach use light standard Arabic with plain vocabulary; for one market write hooks and
  calls to action in that dialect with figures and terms in the standard. Ask the voice tool for the specific dialect and
  diacritise ambiguous words for it.

## Cultural pitfalls

Sports analogies, food and drink imagery, clothing and modesty norms, gestures, colour meanings, humour, religious timing
(Ramadan, Eid, Diwali, Easter) and iconography, names and their pronunciation, and maps and borders (disputed territories:
choose one stated rule per project). AI defaults are measured stereotypes: an audit found 99 of 100 "Mexican person" images showed
a sombrero, 92 of 100 "Indian person" images showed a turban or similar headwear, and all 100 "American person" images carried a
US flag. Models forced to edit a scene often added flag overlays and palette swaps instead of context-consistent changes. The
locale anchor line and verification gate in `07-ai-layer.md` exist for this.

## Voice, captions and timing

- **Duration comes from measurement, not from a word count.** Speaking rate varies with the language, the voice and the text.
  Render a short sample in the chosen voice, run `speech_rate.py measure`, and let the linter treat durations as measured.
  Until then the format's rate is a prior and duration problems are warnings (E013).
- **Caption text comes from the script, never from a transcription of the voice**, in every language: transcribers vary widely
  by language (one rates a language "moderate", 25 to 50% word error, in its own documentation), so use alignment for times
  only, and check that the aligner you hold covers the language: the scout records it, and an unknown is a question.
- **Reading speed differs by script.** English subtitles run up to 20 characters per second, Japanese about 4; limits for most
  other scripts were not found, so measure holds on a native reader.
- Caption lanes and RTL mirroring: `10-platforms.md`.
- Numbers are spoken longer than they are counted ("75%" is one unit and several syllables): measure the rate on a sample
  that contains numbers, or set `est_seconds` on number-heavy beats.
- Line breaking in the animatic never starts a line with closing punctuation or the rest of a number, and never ends one
  on an opening bracket; the HTML board and the final render need the same care in CSS (`line-break`, `word-break`).
- Do not name voice vendors or models here as supporting a language: that is read from the catalog at run time.
