# The AI layer: stills, clips, hosts, voice, music

How to use generative models inside a hybrid video without letting them damage it.
Named models are dated evidence, not recommendations: the model lineup changed
heavily between mid-2026 and 2026-10-20 (a leading video API was switched off, image
and video generations turned over), and IDs and prices drift weekly. This skill therefore
ships neither: the cost scout reads the live catalogue and prices before a spend
(`14-cost-scout.md`). Never mix versions of a model inside one reel. Evidence tags: V verified on a first-party page, R reported
(secondary), I inference.

## Contents
- [Rules that never change](#rules-that-never-change) · [Stills](#stills) · [Clips](#clips)
- [Host](#host) · [Voice and timing](#voice-and-timing) · [Music and sound effects](#music-and-sound-effects)
- [Avoiding the AI look](#avoiding-the-ai-look) · [Model classes](#model-classes) · [Cost drivers](#cost-drivers)

## Rules that never change

1. Truth-bearing content is not generated (`00-layer-doctrine.md`). Generate pictures and
   motion, composite all text and numbers in code.
2. Generate text-free. Even short, large, quoted text is only mostly reliable on the
   best image models, and one video test showed a model inventing extra label text on a
   product. Ask for clean negative space and put the words on in code.
3. Anchor every prompt with the `visual_anchor` (below), re-appended after any
   prompt-enhancer or rewriter.
4. Pin one model per asset type per reel. Stills from one family, clips from one.
5. Aspect ratio first. Generate stills at 9:16 before animating: several video models take
   the aspect ratio from the start image.
6. Cheap before expensive, verify before the next spend, one respend per asset
   (`08-governance.md`).
7. Never name an IP, a franchise, a living public figure or a brand mark in a prompt, and
   treat a vendor refusal as a hard stop.

## The visual anchor and the locale line

Image and video models regress to their most common prior. A generic crowd with flags
renders the most common such image the model knows. This is measured, not folklore:
unspecified prompts collapse to a US-like scene, "culture" is signalled by flags and
costumes rather than ordinary context, and explicit cultural expectations in prompts were
missed often in published audits. A single anchor line is not enough, so use an anchor
plus a verification gate.

`meta.visual_anchor`, one line, is the real subject, place, people, era, and the ONLY
flags, emblems and uniforms allowed. For any place-specific shot, add a locale line to the
prompt:

```
LOCALE ANCHOR: <city, country>, <decade>, <setting: street / classroom / clinic / office>.
MUST SHOW (ordinary, checkable cues): <script of signage>, <vehicle types and driving side>,
  <typical clothing for the setting>, <plug or architecture style if visible>, <climate, vegetation>.
MUST NOT SHOW: national flags or emblems (unless the beat is about the flag), landmarks (unless
  named in the narration), ceremonial or traditional dress (unless the topic), readable text,
  generic Western street furniture.
```

Verification gate before paying for animation: look at the frame for wrong-country tells
(flag or emblem, script, driving side, vehicles, plugs, uniforms, banknotes, architecture,
vegetation, stereotyped dress). Wrong or stereotyped: regenerate, switch to stock for that
country, or switch to a clean stylised visual that makes no locale claim (a pictogram cannot
be the wrong country). The same rule covers graphics: a Pakistan chart with the Indian
rupee glyph is the same failure. A local reviewer should sign off any anchor line for a
language or country you do not know.

## Stills

**Structure the prompt in blocks, not prose.** Style described in prose gets treated as
content to draw; with a reference image in the frame an edit model copies the reference.
Keep the style in its own labelled block so it reads as how to render. This is the
JSON-structured pattern: a block for the reference role, a block for the new content, a
block for the art style, a block for rules. No controlled test shows JSON beating prose
for cross-frame consistency; the rule that matters is separate blocks, whatever the syntax.

```json
{
  "task": "generate_image",
  "reference_image_role": "STYLE SWATCH ONLY. Match medium, palette, texture and mood. Do not copy its subject, composition, pose or any text.",
  "new_image": {
    "subject": "<one clear subject, named, anchored to the real topic>",
    "composition": "9:16 portrait, subject in the upper two thirds, lower third calm for captions, room to move",
    "anchor": "<meta.visual_anchor + locale line>"
  },
  "art_style": {
    "medium": "<from style.json>",
    "color_palette": ["#hex", "#hex", "#hex"],
    "lighting": "<one directional source>",
    "texture": "<grain, paper fibre, halftone ...>",
    "color_grading": "<one grade>",
    "mood": "<one word>",
    "signature_technique": "<the thing that makes the look recognisable>"
  },
  "rules": [
    "no text, letters, numbers, logos, watermarks or signage anywhere",
    "no flags, emblems or uniforms other than those in the anchor",
    "no hands visible unless the beat requires them",
    "same light, grain and palette as every other frame of this reel"
  ]
}
```

Consistency across 8 to 20 frames comes from an anchor kit, not luck:

1. Make a style sheet first and pass it as an input labelled by role ("image 1: style
   reference only").
2. One anchor image per recurring character or object, generated once and reused with
   "do not redesign".
3. Restate the invariant block (palette, light, grain, framing) in every prompt; per-frame
   prompts carry only the delta. Some models have a persistent system prompt: put the
   invariants there.
4. Respect per-request reference limits (one current family allows 4 characters and 10
   objects; another 5 characters, 6 objects and 3 style references).
5. Edit hub-and-spoke from the original references, not by chaining from the previous
   output, so errors do not accumulate. Chain only for camera-angle variants of one
   approved scene.
6. Check each output against the references immediately. Add checks for left and right
   swaps (a documented issue) and for item counts.
7. Generate at the tier you will animate. For Ken Burns on a 1080x1920 canvas, plan
   about 15 to 20% headroom on the long edge (about 2208 px or more), so the 2K tier.
8. Budget 1.5 to 2 generations per kept frame for stylised work, more for photoreal people.
9. A single grain and grade overlay in code across all stills hides residual variance.
10. Verify the look on 3 frames before committing a 12-frame storyboard. Nothing in the
    evidence shows any model is reliable for paper-collage or risograph looks across many
    frames; the style sheet approach is what carries it.

What image models do reliably and not: short large quoted text of 1 to 6 words is
usually fine; dense text, numbers you did not supply, counts, enumerations, labelled maps
and charts are not (duplicated axis ticks, units garbled, values changing between runs,
"seven steps" becoming nine cards, plausible numbers invented for any slot left open).
Illustrated metaphors, icons, backgrounds and textures are where they earn their cost.
Vector output exists from at least one model family and can feed GSAP directly.

## Clips

Default: image-to-video from an approved, text-free still. The still has already been
style-matched; the clip only adds motion. Text-to-video is for beats that need no style
match (abstract light, particles, textures under code). First and last frame modes are the
practical way to end on a clean frame or loop; no source tests how well they hold the end
frame.

Prompt structure that the first-party guides converge on:

```
[Camera: ONE named move + speed], [subject + one action],
[environment + light], [secondary motion: one ambient element],
[end state: camera holds still, subject settles, nothing else moves],
[lens or style line], [audio line, or "no dialogue, ambient only"]
```

- One camera move per clip. Stacked moves usually run one and drop the rest. The start
  frame must allow the move: no extreme close-up before a push-in, and an empty frame
  shows no parallax.
- Use rhythm words (slow, gentle, smooth), not technical specs. "Fast" is the word most
  likely to degrade quality. Long crane rises and full orbits rush or stop partway in 5 s.
- Add one piece of secondary motion (steam, spray, ripples, dust) so it feels filmed,
  not animated.
- 2 to 5 s per clip. Several models now allow 8 to 30 s per generation; reliability, not
  length, is the limit. One generation per beat: easier to reject and retry than
  multi-shot.
- Negatives are model-specific; there is no universal negative tail.
  Veo and Gemini Omni: no negative field for Omni; describe what you do not want as nouns
  and avoid "no" and "don't" (one test: "no human hands" produced a hand). Runway: avoid
  negative phrasing, say "locked camera". Kling: a real `negative_prompt` field. Seedance:
  an "avoid ..." list. State any ban positively in the prompt first.
- No faces in close-up, hands, speech or continuity across cuts in b-roll beats. These are
  where AI video still breaks.
- Native audio: discard it when the voice-over owns the mix, or ask for ambience only.
- Verify every clip frame by frame on a contact sheet: morphing, extra text, wrong symbols,
  strobing (a valid MP4 once passed `ffprobe` while playing as unrelated stills; an
  adjacent-frame difference check catches it), start and end frames similar if it loops.
- Real-people and IP: some models block named people and real-face uploads; others do not
  say. Do not assume a provider behaves like another distribution of the same model.

## Host

Order of preference, by drift and uncanny risk: a real recording; a consented digital twin;
a photo-driven avatar driven by your audio; a native-audio video model presenter (last
resort).

- Prefer an audio-driven avatar over a native-audio presenter: the voice is then identical
  across every beat and across a language switch.
- Keep a continuous host shot to about 6 to 12 s, then cut to b-roll or a code overlay while
  the voice continues. This hides drift, trims cost, and matches per-engine reliability.
- Give the avatar emotionally varied audio; flat audio produces a static head, the clearest
  uncanny signal along with rubbery mouth motion, wrong plosive shapes and swimming teeth.
- Near-frontal, head and shoulders, hands out of frame.
- Identity: the person in the photo must be the user or have consented. Refuse celebrity or
  third-party photos. Twins need the provider's consent recording.
- The avatar's returned audio is the master clock (`11-routing.md`): never mux another
  voice onto it, and never retime it. `explainer-reel-skill` documents the sync rules.
- Policy: Instagram requires the AI-generated profile label for profiles featuring an
  AI-generated person; YouTube bars monetisation for AI personas giving health, legal,
  financial or political advice. A clearly non-human narrator over diagrams is lower risk
  than a synthetic "expert".

## Voice and timing

- One continuous voice-over per reel where possible, so prosody does not reset at beat
  boundaries. Engines cap input length (thousands of characters); 90 s is about 1,350.
- Expressiveness: audio tags and caps on engines that support them; a free-text style
  prompt on those that do not. Tags go in `tts_text` only, from a whitelist. An unknown tag
  can be spoken aloud.
- Numbers and abbreviations in `tts_text` are written as spoken; the digit form stays in
  `text` and the overlay.
- Word timing for captions: if the engine returns alignment (character or word level) use
  it; if you hold the script and the audio, force-align the known script instead of
  re-transcribing; if the script is unknown (a screen recording), transcribe with word
  timestamps. Raw Whisper timestamps start words about 150 ms early; forced aligners and
  commercial transcribers are within 30 to 40 ms on clean English. Captions need under
  about 100 ms.
- Caption text comes from the script, not from the aligner. One aligner strips
  punctuation, so "$19.99" aligns as "1999". Use aligners for times only.
- Languages: whether an engine, a transcriber or an aligner supports the video's language is
  read from the tool's own catalog (the cost scout records it per route) and then confirmed by a
  native speaker listening to a sample. Transcribers vary widely by language, and where one's own
  documentation rates a language poorly, caption text comes from the script, never from the
  transcript. Aligners differ in coverage: check before relying on one. Quality for most language
  pairs has not been measured, so nothing here names a language as supported.
- Measure the real duration after synthesis. Off target by more than about 25 percent:
  rewrite words and re-synthesise (cents), never stretch audio.

## Music and sound effects

- Generate instrumentals: "no vocals, no lyrics, sparse arrangement, steady low-mid energy,
  no sudden dynamics". Do not name artists or songs (one provider forbids it, and it is a
  copyright habit to avoid).
- Licences differ and matter. A provider built on licensed data with a clear commercial
  grant on paid plans is the safest; an open-weights family allows commercial output under
  a revenue threshold and needs an enterprise licence above it; free tiers of several
  consumer generators are non-commercial. Read the terms for the plan you use.
- Level and ducking are in `06-sound.md`. The music bed is a separate stem, not part of
  any "no processing on generated clip audio" rule.
- SFX are cheap; generate them in separate calls and place them in code so timing stays
  under your control.

## Avoiding the AI look

The defence with policy backing is structural: truth-bearing beats in code, real or stock;
AI limited to short restrained mood beats; one code-layer grade and typeface across
everything; script-specific content. The prompt-level techniques below are documented
advice, not measured reductions in viewer perception or platform flagging, so use them
and do not promise results.

- Ask for real texture: pores, fabric wear, imperfections; avoid studio-polish words.
- Concrete physical description over quality words ("hard unmodified flash", "bright
  specular pops on wet aluminium"); avoid "cinematic" alone, "epic", "amazing".
- Film grain as a targeted lever, preferably as one overlay in code across all sources.
- Restrained motion, one camera move, a still ending.
- Every AI beat depicts something the narration literally says or a named metaphor. Generic
  "business people at laptops" under a specific claim is a slop signal.
- Mix honestly: a minority share of AI, in short beats, with real, stock or code carrying the
  claims.
- Provenance marks (for example SynthID on several video, image and audio outputs) cannot be
  removed on some distributions, so assume AI clips can be machine-detected whatever they
  look like.

## Model classes

No lineup and no price is listed here. Names, versions and prices turn over in weeks: between mid-2026 and 2026-10-20
a leading video API was switched off and several image and video generations were replaced. The cost scout
(`14-cost-scout.md`) reads what this environment can run and what it costs. Choose from that list on capability.
Independent leaderboards put several image-to-video models within noise of each other, so rank is a weak signal; 9:16
support, restraint, latency and the scout's price decide.

| Class | Choose on | Failure modes seen |
|---|---|---|
| image | 9:16 or a setting that gives it, reference-image support, transparent PNG or SVG output, delivery resolution | one family reports text weakness at 1K, so test at the resolution you ship; text in an image is never trusted anyway |
| video | image-to-video from an approved still, 9:16, the clip-length limit, audio on or off, whether a still end frame holds | billing by tokens that depend on resolution and duration; an "auto" aspect ratio makes a bill unpredictable, so set it explicitly |
| avatar | audio-driven lip-sync from your own voice-over, whether the call covers the whole voice-over, how seconds are rounded | lip-sync failure notes are one ad vendor's anecdotes; one engine rounds up to whole seconds |
| voice | the language and dialect you need, tag support, the billing unit | one vendor bills by UTF-8 bytes, so Urdu, Hindi and Arabic scripts cost two to four times per character |
| music | licence terms by plan, length control, an instrumental option | licence terms differ by plan |

Retirements seen on 2026-10-20, kept as evidence that a hardcoded id is a bug: Sora 2 and its API were switched off
2026-09-24; some Veo 3.1 preview ids shut down 2026-10-22; gpt-image-1 shuts down 2026-10-23; OpenAI TTS endpoints shut
down 2027-01-06. Promotions end too: a price entry carries an `expires` date and the scout asks what happens after it.

## Cost drivers

There is no recipe table: a cost depends on the route chosen, and routes and prices differ per environment. Build the
cost card (`14-cost-scout.md`). The shape to expect, to be checked against the card and not assumed: spend goes to
seconds of AI video and seconds of host, then to retries, and stills, voice and alignment are usually small beside them.
Rejected generations are paid for, which is why the card has a high band.
