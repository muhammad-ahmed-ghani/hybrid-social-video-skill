# Comedy sketch (`comedy-sketch`)

Family narrative · tier R1 · 20 to 75 s · 2.8 speech units/s (a prior, measured per voice) · gates G1 plus the punchline
pass, and for a series the series gate (`15-series.md`) · cost scout-priced (drivers: cast stills once, voices, any hero
clips) · build time depends on the route

A short scene with one comic engine: a situation with a rule, a character who follows or breaks it, an escalation, a
punchline and a tag. It is made to repeat as a series with a recurring cast and running gags, which is also where it
fails: the same gag with the same outcome every episode is what platforms demote.

## Use when, avoid when

Use for a recurring cast in a recognisable setting, character comedy, workplace and everyday-life sketches, parody of a
format (a format, never a named property). Intents: sketch, serial-story.

Avoid when the joke needs a real person's likeness or voice (consent, and a refusal from a vendor is a hard stop), when the
humour trades on a real, named individual or group, and when nobody will write or choose the punchlines: AI-written
punchlines are the documented weak point (below).

## The punchline pass

It applies to any piece with intent `sketch`, whatever its format (a comic cartoon episode included), and to any beat with
role `punchline`.

Twenty professional comedians rated LLM comedy bland and generic and found that models helped with setups and structure
while humans supplied the punchline (V, Mirowski et al., FAccT 2024). So the agent drafts the situation, the setups and
the escalation, and for each punchline offers three options. Record them on the beat in `punchline_options` (the board lists
them); the user picks one or rewrites it at Gate 1, the chosen line becomes the beat's `text`, and you set
`punchline_approved: true`. The linter warns (E107) on a punchline with neither options nor approval, and a beat map with a
punchline nobody approved does not leave Gate 1.

## Look

Any identity that keeps the cast legible at phone size: a clear silhouette, a flat background, one accent for the beat that
matters. The cast and the look are series-level files and never change inside an episode (`15-series.md`). Characters
come from one of three routes: puppets animated in code (the default for volume), reference-conditioned AI clips for hero
moments only, or a trained identity.

## Layer mix

ai_image 10 to 70% (cast and set pieces, made once), code 10 to 70% (puppet scenes, captions, timing devices), ai_video up
to 40% for hero moments. Three beats in a row with the same layer and device are allowed: shot and reverse shot are how
dialogue is cut.

## Beat grammar

Roles: `cold-open` (already inside the scene, no introduction), `title` (a sting, once), `setup` (plant what the punchline
will use), `escalate` (raise the stakes at the same rhythm), `punchline` (the key word last), `tag` (a short button after the
laugh). Every spoken beat has a `character`. One comic engine per sketch.

Rules with a working-writer source (V, Toplyn and Vorhaus): put the key element next to the punchline and the key word last;
cut distracting specifics; repeat a key word if the punchline depends on it; avoid the passive; exaggerate; use the rule of
three; an inappropriate response and comic opposites locked in a situation are engines. Not sourced anywhere I could find:
pause lengths, setup length and dialogue speed, so `punchline_max_seconds` and `hold_seconds` are house heuristics to tune by
watching the animatic.

## Script voice

Short lines, one idea per line, contractions, how the character would actually say it. Every character sounds different
(rhythm, vocabulary, what they never say). Write in the language the user writes in, with that language's own comic
conventions; do not translate a joke, rewrite it. Numbers are rarely the point; when one is, it is a code overlay.

## Motion and edit

Cut on the line, not on the laugh's tail; hold a beat after the punchline in `hold_seconds` and let the tag land. Vary the
framing between exchanges (a close-up, a wide, a reaction) so the same two layers do not feel like one shot. Camera moves
are small and motivated. Keep the face and the key prop inside the safe box.

## Sound

The voices carry the scene: distinct voices per character from stored voice ids, a low bed, a sting at the title, a dropout
before the punchline when it helps. Effects are sparse and diegetic. No audio processing on generated voices
(`06-sound.md`).

## Production route

1. `series.py next`; episode loglines; the declared changes; beat map with roles, characters and `meta.series`; lint; board;
   animatic.
2. Gate 1: plan, claims (if any real fact is used), the cost card, and the punchline pass.
3. Voices from the passports; timings; `spans.json`; re-lint on the measured rate.
4. Build the puppet scenes in code through the handoff (`11-routing.md`), or generate hero clips from approved stills.
5. QC, then `series.py check`, then publish; bring the numbers back with `series.py analytics`.

## Failure modes

A joke explained; unclear stakes; the same gag and the same outcome as last episode; a punchline buried under specifics; a
character who changes voice or face; a spent running gag; lines every character could say; a hook that repeats last week's;
likeness or voice of a real person without consent; an unlabelled realistic synthetic human.

## QA specifics

Every spoken beat has a character and a stored voice; the punchline beat is the shortest spoken beat of its run and is
followed by a hold; the character check passes against the canonical sheet (a pass mark from the series' own references);
`series.py check` is clean or its warnings are decided; the AI label decision is recorded.
