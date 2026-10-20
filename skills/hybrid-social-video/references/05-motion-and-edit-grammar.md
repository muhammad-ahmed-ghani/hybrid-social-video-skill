# Motion and edit grammar

The numbers that separate a designed explainer from slideshow animation. Hand them to
`/hyperframes-animation` and `/hyperframes-keyframes` as constraints; do not re-teach
those skills' mechanics here. Evidence tags: V verified (primary source or a local
measurement), R reported (secondary), I inference (reasoned, testable, not established).
Cut-rhythm numbers have no controlled short-form study behind them: treat them as defaults
to test against real retention graphs.

## Contents
- [What survives from classic animation](#what-survives-from-classic-animation)
- [Easing](#easing) · [Durations](#durations) · [Stagger](#stagger)
- [One hero motion per beat](#one-hero-motion-per-beat) · [Template tells](#template-tells)
- [Continuity and transitions](#continuity-and-transitions) · [Checkable rules](#checkable-rules)
- [Hold times](#hold-times) · [Cut grammar](#cut-grammar) · [Beat structure and rehooks](#beat-structure-and-rehooks)

## What survives from classic animation

Easing, staging (becomes layout), anticipation (a small counter-move, used sparingly),
follow-through (settle and overshoot), timing and exaggeration survive. Squash and
stretch and most character principles do not transfer to motion graphics. The useful
replacement vocabulary is intent-bearing moves: offset and delay (order is importance),
value change (count-up, bar growth), masking (line and shape reveals), cloning (a mark
spawns its detail card), transformation (one object becomes the next beat's object),
dolly and zoom (camera-through), obscuration (dim everything but the hero), parallax.

Motion serves four roles: expectation, continuity, narrative, relationship. A move with
none of them is decoration; delete it. "Don't add motion for the sake of adding motion."
Elements that slide in attract attention faster than ones that fade, and fast motion at
the periphery steals attention from the hero.

## Easing

GSAP's default is `power1.out`. Measured on GSAP 3.15.0 (`t(x)` = fraction of the
duration at which the value first reaches x% of the change):

| Ease | t(50%) | t(90%) | t(99%) | Overshoot |
|---|---|---|---|---|
| power2.out | 0.21 | 0.54 | 0.79 | none |
| power3.out | 0.16 | 0.44 | 0.68 | none |
| power4.out | 0.13 | 0.37 | 0.60 | none |
| expo.out | 0.10 | 0.33 | 0.59 | none |
| back.out(1) / (1.4) / (1.7) / (2.5) | 0.15 / 0.14 / 0.13 / 0.11 | 0.37 / 0.33 / 0.30 / 0.24 | 0.48 / 0.41 / 0.36 / 0.28 | 3.7% / 7.1% / 10.0% / 18.9% |
| elastic.out(1,0.3) | 0.04 | 0.07 | 0.07 | 37%, several oscillations |
| power2.inOut | 0.50 | 0.71 | 0.86 | none |

Rules derived from the table:

1. Entrances use `.out`, exits use `.in`, moves between two on-screen positions use
   `.inOut`.
2. An `expo` or `power4` tween feels finished at about 60% of its duration; the rest is a
   nearly invisible tail. To feel done in 0.4 s, set about 0.65 s. `power2.out` needs 78%.
3. Overshoot is a dial: position moves at or below 7% (`back.out(1.4)`), a scale pop on a
   small hero about 10% (`back.out(1.7)`), 19% only for creator or comic looks, elastic for
   one playful hero.
4. One overshooting ease per beat, on the hero. Everything else uses a plain `.out`.
5. Easing is an adverb: `expo.out` confident, `power3.out` smooth default, `power2.inOut`
   calm, `back.out` friendly, elastic comic. Linear only for mechanical things: typewriter,
   progress tied to real time, ambient drift, a line draw synced to a voice cue.
6. A vetted expressive curve in GSAP: `CustomEase.create("emph", "M0,0 C0.05,0 0.133333,0.06
   0.166666,0.4 C0.208333,0.82 0.25,1 1,1")` (Material 3 emphasized).

## Durations

UI research puts most animations at 100 to 500 ms; video usually wants slightly slower
because viewers cannot pause. Data-graphic transitions are best near 1 s per stage.

| Element | Entrance | Hold after landing | Exit | Ease in / out |
|---|---|---|---|---|
| hero word or phrase, 1 to 3 words | 0.40 to 0.65 s | at least 1.2 s | 0.25 to 0.35 s | `expo.out` or `back.out(1.4-1.7)` / `power2.in` |
| per-word kinetic caption | 0.20 to 0.35 s, stagger from speech timing | until the phrase ends | cut or 0.15 s | `back.out(1.7)` or `power3.out` |
| headline, line-by-line mask reveal | 0.5 to 0.8 s per line, line stagger 0.10 to 0.20 s | 2 to 3 s | 0.3 to 0.4 s | `power3.out` / `power2.in` |
| number count-up | 1.0 to 1.6 s | at least 0.8 to 1.0 s after the last digit | 0.25 s | `expo.out` or `power3.out` |
| bar or column growth | 0.7 to 1.0 s per group, 0.08 to 0.12 s between bars | 2 to 3 s | 0.3 s | `power3.out` / `power2.in` |
| line chart draw-on | 1.0 to 1.5 s | 2 to 3 s | 0.3 s | `power1.inOut` or linear to the voice |
| lower third | 0.35 to 0.5 s | 3.5 to 5 s | 0.25 to 0.35 s | `expo.out` / `power2.in` |
| code-layer transition | 0.25 to 0.5 s or a hard cut | n/a | n/a | `power2.inOut`; at most 15% of the beat |
| Ken Burns on a still | beat length | n/a | n/a | `none` or `sine.inOut`; scale 1.00 to 1.04 to 1.08 |
| stroke draw (blueprint, whiteboard) | 0.6 to 1.4 s per stroke | n/a | n/a | `power1.inOut`; draw in reading direction |

One frame is 41.7, 33.3 or 16.7 ms at 24, 30 or 60 fps.

## Stagger

`each` is a fixed gap between starts, `amount` splits a total. Minimum 2 frames per item
(about 67 ms at 30 fps), since anything under one frame is invisible. Words and list items
0.05 to 0.12 s; cards 0.10 to 0.20 s; bars 0.08 to 0.12 s; characters 0.02 to 0.04 s and
only for 12 or fewer. Cap the total cascade at 0.5 to 0.8 s; past that, switch to `amount`.
Order equals importance, so stagger the hero first or last on purpose, never in DOM order.
For right-to-left text stagger from the end. A constant stagger across the whole video is
a template tell.

## One hero motion per beat

1. Each beat has exactly one hero: the element whose big move (travel over about 15% of the
   frame or scale change over about 20%) carries its meaning. At most two secondary
   elements move, small (opacity, or travel under 5%). Everything else is still or drifts
   under 2% scale.
2. What moves first, what moves most, what is largest and what sits at the optical focus
   must agree. If the eye follows a mover while the voice is about a static element, the
   beat fails. Freeze at 0.3 s and 1.0 s: the thing the voice is about must be the biggest
   changed region.
3. Every move explains: shows a quantity, a relationship, a cause or sequence, continuity, a
   reveal, or directs attention.
4. Stillness is a move. Hold the hero after it lands for the reading time. Do not add idle
   breathing to everything.
5. Testable proxy: sample the first second of a beat at 10 fps, compute frame difference
   per region. The hero's region holds the majority of changed pixels, and changed area
   outside it stays under about one third at any instant.

## Template tells

| Tell | Fix |
|---|---|
| same entrance on every element | vary by role: hero scale or mask, labels fade only, data marks grow from baseline |
| one ease and one duration everywhere | use the table above; at most two elements per beat share an ease |
| everything exits, then the next enters | overlap 2 to 6 frames, or let the hero persist and transform |
| elements enter from the screen edge and stop | enter from where the idea comes from |
| bullet lists building line by line | one idea per beat, reveal on the voice cue |
| stock transitions (cube, page curl, star, clock wipe, random) | hard cut, or a transition shaped by the content |
| static background under moving foreground | slow drift, parallax or texture life |
| centred floating text in empty margins | anchor to a grid and fill the frame |
| default drop shadows, uniform rounded boxes | one deliberate edge treatment per identity |
| mixed icon styles | one icon set and stroke weight |
| constant stagger and pace | rhythm: fast, fast, hold, accelerate into the reveal |

## Continuity and transitions

- Object persistence: a mark that represents a data point must not be reused for another
  across a transition. A bar that is 2019's rent stays 2019's rent when the scene changes to
  a line chart; if the meaning changes, remove it and add a new one.
- Match cut: match key shape position and scale (area within about 5 to 10%, centre within
  about 40 px at 1080 wide) and colour, or break the match on purpose.
- Velocity across a cut: exit with an `.in`, enter with its mirror `.out`.
- Consistent screen direction across cuts; reverse only with a visible event.
- Camera-through: the foreground scales until it fills the frame and becomes the next
  scene's background; needs a blur ramp and a riser.

| Transition | Use when | Length | Cheap when |
|---|---|---|---|
| hard cut | default; new idea on a phrase boundary | 0 | cutting mid-word or mid-motion for no reason |
| whip pan | continuing directional motion; at most about one per 8 to 10 s | 4 to 8 frames plus motion blur and a whoosh | on every cut, no blur, wrong direction |
| mask reveal shaped by the content | the shape means something | 0.35 to 0.6 s | a generic wipe |
| zoom-through | scale metaphors, chapter change | 0.5 to 0.8 s with a riser | no blur ramp, the element does not fill the frame |
| match cut | visual rhyme | 0 | imprecise, reads as a jump |
| dissolve | time passing, soft register | 0.3 to 0.6 s | default between unrelated shots |
| glitch or flash cut | register shift, shock | 3 to 6 frames | decoration |

Plan from "start with a straight cut; use a wipe, dissolve or transformation only when it
helps communicate the action". At most 2 distinct transition types per video, each with a
stated narrative purpose.

## Checkable rules

1. Entrance ease is `.out`, exit `.in`, position change `.inOut`.
2. At most one overshooting ease per beat; overshoot at or below 7% for position, 10% for a
   scale pop.
3. For `expo` and `power4`, set duration at least target / 0.6.
4. Stagger `each` at least 2 frames; cascade at most 0.8 s.
5. The hero holds still at least 1.2 s (1 to 3 words); text the voice does not read holds
   at least 0.29 s per word.
6. At most two transition types per video; non-cut transitions at most 0.6 s and 15% of the
   beat.
7. No two consecutive beats share the same entrance direction, ease and duration.
8. The first animation does not start at exactly t=0, except the cold-open hook whose first
   frame must already carry meaning.

## Hold times

Reading speed anchor: English subtitles run up to 20 characters per second (about 3.5 words
per second, 0.29 s per word); Japanese 4 characters per second. A viewer needs about 230 ms
to perceive a change.

Hold for text the voice does not read: `entrance (0.4 to 0.6 s) + 0.29 s x words + 0.3 to
0.5 s dwell`. A 3-word hero is about 1.8 s; a 7-word line about 2.9 s. For text the voice
reads, the ear leads, but the full word should be visible 2 to 3 frames before it is
spoken or on the same frame.

| Element | Fully visible after landing | Typical beat |
|---|---|---|
| hero word or phrase | at least 1.2 s | 1.8 to 2.5 s |
| hero number plus unit | 1.0 to 1.5 s | 2.5 to 3.5 s |
| 2 to 3 bar comparison | about 2.5 s after the last bar | 3.4 to 4.5 s |
| 5-row ranking | 3 s | 4 to 5.5 s |
| line chart, one hero line | 2 to 3 s after the end label | 4 to 6 s |
| map highlight | 2 to 3 s | 3 to 5 s |
| quote or text card the voice does not read | 0.29 s x words + 1.0 s | |
| lower third | 3.5 to 5 s total | |
| still with slow push | 1.5 to 3 s | |
| stock clip | 1.2 to 3 s, cut on a phrase | |
| AI clip | trim to the best 1.5 to 3.5 s; avoid the first and last 0.3 s | |
| host between cutaways | 2 to 6 s | |
| montage shot | 0.4 to 0.8 s, at most 6 shots | |

## Cut grammar

- With a voice-over spine nearly every cut is a split edit. Cut the picture 0 to 3 frames
  (0 to 100 ms at 30 fps) before the spoken keyword it shows. Audio slightly late is the
  better-tolerated direction (detectability thresholds are about +45 ms audio early versus
  125 ms audio late, from a broadcast standard built on newsreader clips). A picture that
  arrives after the word reads as late.
- Sound J-cut: start the next beat's music change, riser or SFX bed 6 to 15 frames (0.2 to
  0.5 s) before the picture cut. L-cut for meaning: let the last phrase ride over the next
  picture when the new image illustrates it. Do not split-edit a hard topic change in a
  short beat; use a clean phrase-boundary cut.
- Cut on action: at peak velocity of a whip or at the landing frame of the hero. In silence:
  topic changes at a voice pause; trim pauses to about 0.25 s in fast edits but keep 0.4 to
  0.8 s before a reveal. Never cut mid-word unless the cut is the joke.
- Cut for emotion and meaning first; accept imperfect geometry if the cut sells the idea.
  Eye-trace: put the next hero within about 25% of the frame width of where the last ended,
  or far away on purpose for a surprise.
- Callbacks: repeat a visual when the voice refers back to it 6 to 20 s later, same framing
  and position, but change its state (crossed out, a second bar added) so it is a
  development, not a reuse. One or two per 60 s. The loop is a callback of the first frame.

## Beat structure and rehooks

| Beat | Job | 20 s | 45 s | 90 s | Visual and sound |
|---|---|---|---|---|---|
| hook | state the tension; no greeting or logo | 0-2 | 0-3 | 0-4 | hero visual and sound at frame 0; hit or riser peaks on the hook line |
| context | orient with one reference the viewer knows | 2-6 | 3-10 | 4-16 | calmer pace, establishing visual |
| escalation | 3 to 5 steps raising stakes; evidence | 6-13 | 10-30 | 16-60 | rising pace, data beats, rehook every 8 to 15 s |
| reveal | the answer or twist | 13-17 | 30-39 | 60-78 | riser into a dropout, then a hit; longest hold so far |
| payoff | implication, takeaway, source line | 17-20 | 39-45 | 78-90 | thinner sound, clean frame |
| loop | last line completes or echoes the first | last 1-2 s | 2-3 s | 3-4 s | last frame near the first; audio tail with no click |

A rehook changes at least two of visual register, sound, pacing, information type, every 8
to 15 s in 45 to 90 s videos, never more often than every 5 to 6 s, and never the same type
twice in a row. Types: open loop ("but that is not the strange part"), a direct question,
a stat reversal, a register shift (inversion, quote card, full-bleed photo, zoom-through),
a sound change (dropout, riser, sting), a visible counter ("reason 2 of 3"), a new image
domain, a pattern interrupt (zoom punch, whip), an escalating number ("now multiply that
by"), direct address. No data shows a 40 to 60% rehook helps; YouTube's own retention
guidance says to move compelling content earlier.

Data charts, maps and maths have their own rules: `05b-data-and-math.md`. Safe zones:
`10-platforms.md`. Sound placement: `06-sound.md`.
