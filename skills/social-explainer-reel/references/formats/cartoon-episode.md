# Cartoon episode (`cartoon-episode`)

Family narrative · tier R1 · 25 to 90 s · 2.6 speech units/s (a prior, measured per voice) · gates G1, and for a series the
series gate (`15-series.md`) · cost scout-priced (drivers: the cast and sets once, voices, any hero clips) · build time falls
sharply after the first episode because the cast, rigs and voices are reused

An animated short with a recurring cast, told in cut-out puppets animated in code. The format exists because code does what
generative video cannot do across episodes: the same character, the same way, every time. Generative art makes the cast and
the sets once; code moves them.

## Use when, avoid when

Use for serial stories, animated comedy, a mascot-led explainer series, anything where the cast must stay identical across
dozens of episodes. Intents: serial-story, sketch.

Avoid when the show needs fluid full-body 3D motion, camera moves through space, or photoreal humans; use hero clips for a
moment or two and accept their limits. Avoid a copy of a known property's characters, worlds or voices.

## Look

One flat or lightly textured style, locked once (`style.json`, `art_style.json`) and approved at the series gate. Art with
clear shapes, separable parts and a limited palette splits into layers best. Backgrounds are separate layers with parallax.
Grain and light are overlays in code, shared across every source so generated and drawn parts agree.

## Layer mix

code 30 to 95% (puppets, backgrounds, text, timing), ai_image 5 to 60% (the cast sheet, props, backgrounds, made once),
ai_video up to 30% (hero moments). Three identical beats in a row are allowed: that is how dialogue is cut.

## The puppet pipeline

(A design, not a tested pipeline; see `15-series.md` for the evidence and the licences.)

1. **The sheet.** One canonical character sheet per character, approved at the series gate: front, three-quarter, side,
   the mouth set, two or three expressions, one prop. Generate it once, with the JSON-structured prompt and the style swatch
   as references (`07-ai-layer.md`).
2. **The layers.** Split the sheet into parts by hand or with a layer-decomposition model, then check the result by eye;
   these models fail on ponytails, footwear, props over the face and heavy chibi proportions. Recipe: cut along natural joints
   (head, torso, each limb, each prop, eyes open and closed), keep every part on a transparent canvas the size of the sheet so
   it needs no repositioning, paint what a moving part reveals behind it (a neck behind the head), name the files after the
   parts, and put the pivot at the joint, not the centre.
3. **The rig.** Author the pivots, the draw order, the blink and the mouth sprites once per character and store them in the
   passport as `characters/<id>/rig.json` (add it with `series.py character add --id ID --rig rig.json --replace`, check it
   with `series.py character rig-check`). No tool rigs an AI character automatically. The shape (`hybrid-rig/1`):

   ```json
   {"schema": "hybrid-rig/1", "canvas": [1080, 1920],
    "parts": [{"name": "body", "file": "parts/body.png", "pivot": [540, 1200], "parent": null, "z": 0},
              {"name": "head", "file": "parts/head.png", "pivot": [540, 820], "parent": "body", "z": 2}],
    "mouth": {"shapes": {"A": "mouth/a.png", "B": "mouth/b.png"}, "anchor": "head", "offset": [0, 60]},
    "cue": null, "blink": {"parts": ["eyes_open", "eyes_closed"]}}
   ```

   A character with no mouth sets `"mouth": null` and a `cue` that shows speech some other way: `amplitude-bounce` (the body
   or an antenna moves with the audio level), `blink` (a light pulses on the stress points) or `none`. The mouth cue letters
   come from the lip-sync tool you use; do not assume the set. Part files are hashed into the series lock.
4. **The performance.** A GSAP timeline per beat: idle sway, head turn, blink, gesture, entrance and exit, with mouth shapes
   from the audio (Rhubarb or any viseme source) swapped on the cue times. Render by seeking a paused timeline frame by
   frame, so a second render is identical.
5. **The sets.** Backgrounds generated once per location, reused with new camera moves and light; a new location is a
   declared change of the episode.
6. **Hero moments.** A beat that needs motion the rig cannot do (a fall, a chase) is a short generated clip from an approved
   still, compared with the canonical sheet before use.

## Beat grammar

Roles: `cold-open`, `title`, `recap` (only if the series needs it), `setup`, `escalate`, `turn`, `payoff`, `tag`,
`cliffhanger` (optional). Each beat is one exchange or one action. A serial episode changes the story state: something is
different at the end (a fact, a relationship, a position), and `series.py record --type state` stores it.

## Script voice

Characters speak in their own voices and rhythms, in the language the user writes in. Short lines; action carried by the
picture. Every spoken beat has a `character`, and the passport's stored voice is the only voice that character ever has.

## Motion and edit

Entrances and exits are staged, not faded; secondary motion (a swaying hem, a bobbing head) stays small; cuts happen on the
line or the action; a held reaction shot is a tool, not filler. Keep the faces and the key prop inside the safe box, and keep
lower-third captions out of the character's face.

## Sound

Distinct stored voices, a fixed music motif and title sting reused every episode, sparse effects, a bed that ducks under
the dialogue. Do not process generated audio (`06-sound.md`).

## Production route

1. `series.py next`; episode plan with declared changes; beat map with characters; lint; board; animatic.
2. Gate 1 for the episode only: plan, cost card, deltas. The look and the cast are already locked.
3. Voices from the passports, timings, mouth cues, `spans.json`; re-lint on the measured rate.
4. Build the scenes through the handoff (`11-routing.md`); generate only the new locations or props, and hero clips if any.
5. QC; the character check against the canonical sheet; `series.py check`; record the new facts and state.

## Failure modes

A character that drifts (a different face, a different outfit); a state that never changes between episodes; a hero clip
that breaks the cast; a mouth that does not match the audio; a rig tuned to one episode's poses; a regenerated cast sheet
mid-series; backgrounds that clash with the puppets' light; the same location, situation and outcome again.

## QA specifics

Each puppet frame matches the canonical sheet within the series' pass mark and not above its copy-paste ceiling; mouth shapes
change on the speech cues; a second render of a scene is byte-identical in its animation; the look lock is unchanged; the
declared changes are real, and the state record is updated.
