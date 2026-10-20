# Existing footage, packaged (`talking-head-package`)

Family presenter-led · tier R0 · 20 to 180 s · 2.7 words/s (the speaker sets it) · gate G1 · cost scout-priced (drivers: music, transcription; no generation) ·
build time 20 to 60 min

The footage plays untouched; the package is graphics and captions: kinetic titles, lower thirds, data callouts,
pull quotes, side panels, picture-in-picture, a caption identity. No generation is needed, so the cost is mostly
transcription. Retiming, recolouring, reframing, reordering or audio work is NLE editing and out of scope.

## Use when, avoid when

Use for a talk, interview, podcast clip, founder video or a user's own explainer that needs designed graphics and
captions for social. Intents: news, case, myth, paper, howto, policy (the speaker explains, the package proves).

Avoid when the footage is someone else's (rights), when the speaker's claims are false or unverified (the package
amplifies them), when the footage is not a single clear subject, or when the job is cutting (that is
`video-editor` or `/general-video`).

## Look

Quiet beside the speaker: swiss-grid, editorial-serif, newsroom or dark-luxe cards; or a caption identity from the
caption workflow's catalogue. Cards never cover the face; the lower third sits in the safe lane; one accent.

## Layer mix

real 80 to 100% as the base; code overlays are not counted in the base mix and carry everything that is exact.

## Moment selection (for long source footage)

Ideas from clip-factory pipelines (not code): transcribe the whole source first, since the transcript is the search
surface; score candidate moments on hook, coherence, value, energy and platform fit; apply a standalone test (reject
unresolved pronouns, references to earlier context, long lead-ins, endings before the payoff); keep diversity across
sections and speakers; record rejected candidates. A moment should open on its claim within 3 s and close on its
payoff.

## Beat grammar

The speaker's argument is the spine; map it to beats by sentence, not by time. Hook: the speaker's strongest line
with a kinetic title or the claim as text. Cards land on the word that names them: a data callout on the number, a
pull quote on the quote, a lower third at first appearance of a name and again only if the speaker returns. Rehook
at register shifts (a full-bleed card, a quote card) every 8 to 15 s in clips over 45 s. Show sources on screen for
every number the speaker states.

## Script voice

There is none to write: the transcript is the script. Edit nothing. If a claim in the transcript fails the claims check
(`02-intents-and-scripts.md`), either add a correcting card with the source, choose another moment, or decline to package
it. Never present the speaker saying something they did not.

## Motion and edit

Cards enter 0.35 to 0.5 s, hold per the formulas in `05-motion-and-edit-grammar.md`, exit 0.25 to 0.35 s; picture-first by
0 to 3 frames; one hero card per beat; captions at 3 to 5 words per phrase in lane A or B (`10-platforms.md`), never over
the face or the platform rail; the same caption identity for the whole clip.

## Sound

Untouched: the footage's audio plays as recorded. Do not normalise or duck it. Add a music bed only if the user asks, 14 to
20 dB under the voice, and on a separate stem.

## Production route

1. Probe the file for real (resolution, fps, duration, audio); transcribe with word timestamps locally.
2. Beat map: layer `real` base, `overlays` per card with the word it lands on; claims for each number or quote; lint; board;
   Gate 1.
3. Cards: `/talking-head-recut`. Captions: `/embedded-captions` (a verbatim rail, or captions composited behind the
   subject). Both leave the footage untouched. Enter through `/hyperframes`, which routes and installs the workflow.
4. QC: `qc_master.py` (loudness gate applies to the existing mix: if the speaker is quiet, report it, do not process it),
   contact sheet, safe zones, face occlusion.
5. Sidecar SRT or VTT for YouTube.

## Failure modes

Captions or cards over the face; a lower third on every beat; cards that restate the sentence in different words (a second
script); a speaker's unverified claim presented as established; an interview subject who has not consented to a social
cut; the footage reframed or retimed (out of scope); platform watermarks burned in (Instagram counts them as non-original).

## QA specifics

The footage hash or duration is unchanged; every card lands on its word within a frame; the face is clear in every frame;
every number on a card traces to a claim; captions equal the speech; the sidecar file exists.
