# Archival documentary (`archival-documentary`)

Family editorial · tier R1 (R2 for a few motion beats) · 30 to 90 s · 2.4 words/s · gates G1 plus G2 when AI plates define
the look · cost scout-priced (drivers: AI plates, any clips) · build time 30 to 60 min

History and true stories told with real archival material first: photographs, newsreel, documents, period stock, with
slow camera moves, grain, restraint and a measured voice. It earns trust by being honest about what is real. AI imagery
is allowed only where no real image can exist or be shown, and then as clearly stylised or labelled reconstruction.

## Use when, avoid when

Use for history, biography, true stories, historic objects and places, "what really happened" pieces, disasters and
inventions with a documentary record. Intents: causal, timeline, case, reveal, culture.

Avoid when there is no usable real material and the story depends on specific people and events being seen (an invented
photoreal image of a real event is a deception risk and a likely platform-label case), or when rights to the archival
material cannot be cleared.

## Look

A restrained grade: slightly desaturated, one accent for labels, film grain applied as a single static overlay across every
source so archival, stock and AI plates share a surface. Identities: dark-luxe, editorial-serif, newsroom (current history),
paper-collage (a warmer register). Type is quiet: source captions, dates, small place labels.

## Layer mix

real and stock 30 to 70% (archival photographs, newsreel, period stock, documents), ai_image 0 to 70% as stylised
reconstruction or atmosphere (no identifiable real people, no real events presented as photographs), code 10 to 50% (dates,
maps, captions, labels, count-ups, Ken Burns and grain assembly), ai_video 0 to 20%.

Evidence classes: real archival (E0) may support a claim and is credited; generic stock (E1) is mood only, since juxtaposition
implies specifics; stylised AI illustration (E3) carries an "Illustration" chip when it could be mistaken for evidence; photoreal
AI of a real place or event (E4) and any AI likeness of a real person (E5) are not used.

## Beat grammar

A date-stamped or in medias res hook (H8, H9 or H4), the situation, the pivot (BUT), the consequence (THEREFORE), the
complication, the reframe that returns to the opening image or line. A beat is 3 to 7 s with one image and one idea; hold
long enough to read a caption (0.29 s per word beyond the voice). Dates and eras are signposted ("1953"), and the time
scale is declared when it is not linear.

## Script voice

Measured, warm, present tense for the past, concrete numbers, no hindsight neatness: "the usual answer is X, but the record
shows more than one cause". Hedge what the record does not settle with calibrated words.

## Motion and edit

Slow push or pan on stills (scale 1.00 to 1.04 to 1.08, `none` or `sine.inOut`) with 15 to 20% headroom in the source; hard
cuts and the occasional slow dissolve (0.5 to 0.8 s) for time passing; picture 0 to 3 frames before the keyword it shows; a
callback to the opening image near the end with its state changed. Period accuracy check on every image: props, clothing,
vehicles, signage and technology must fit the date. A visible source line for archival.

## Sound

Room tone under everything, a restrained instrumental bed 14 to 20 dB under the voice, sparing effects (a paper rustle, a
projector tick only if the look supports it), silence before the reveal. One music track.

## Production route

1. Research and rights: find real material first; record source, date, credit and licence per asset in `claims[]` or the asset
   list; public-domain and open archives are candidates but each item needs a rights check. If none exists for a beat, choose
   stylised illustration, a map or a document instead of inventing a photograph.
2. Beat map with the layer per beat (`real`, `stock`, `ai_image`, `code`); set `depicts_real` and `label_synthetic` on any AI
   plate; lint; board; animatic; Gate 1; G2 if AI plates define the look.
3. Generate AI plates only for atmosphere and no-identifiable-person scenes, text-free, with the anchor and an era line in the
   prompt; verify each against the period list.
4. Assemble in HyperFrames: Ken Burns on stills, one grain overlay, source captions; sound; QC.

## Failure modes

AI "photographs" of real people or events; anachronistic props or clothing; archival used without a credit or rights; generic
stock under a specific claim; hindsight single-cause narrative; a Ken Burns that crops out the subject; grain animated
instead of static (it vanishes in re-encode); different grades per source; claims without dates; a label missing on a
reconstruction.

## QA specifics

Every real image credited; every AI plate stylised or labelled and free of identifiable real people; period check passed;
the grade and grain are uniform; dates on screen match the voice; the closing image echoes the opening; the disclosure
decision is recorded.
