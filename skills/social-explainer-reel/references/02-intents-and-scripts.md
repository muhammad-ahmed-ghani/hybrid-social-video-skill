# Intents and scripts: writing the video before producing it

Tools cannot rescue a script with no thesis. This file covers choosing the story,
turning a source into a beat plan, writing for the ear, and the script checks to
run before any money moves. The evidence behind each rule is in
`13-inspirations.md`; rules marked (inference) are reasoned, not measured.

## Contents
- [Choose the intent](#choose-the-intent) · [The shared grammar](#the-shared-grammar)
- [Word budget](#word-budget) · [Hooks](#hooks) · [Ten laws](#ten-laws)
- [Writing for the ear](#writing-for-the-ear) · [Numbers](#numbers)
- [Calibrated language](#calibrated-language) · [From a source to a thesis](#from-a-source-to-a-thesis)
- [The brief](#the-brief) · [Sketches and serials](#sketches-and-serials) · [Script QA checklist](#script-qa-checklist)

## Choose the intent

`meta.intent` is one id from `data/intents.json`. It fixes the skeleton, the hook
families, the misconception rule and the formats that usually fit. Open that file
for the 30 s skeleton of each.

| Id | Job | Hooks | Carrying visual | Watch for |
|---|---|---|---|---|
| mechanism | install a runnable causal model | H1 H2 H4 | animated diagram, one highlight per beat | parts list; more than 3 new terms |
| causal | argue why one event happened | H9 H6 H4 | timeline with causal arrows, map, documents | single-cause story |
| concept | definition, boundary, example, non-example | H2 | paired example and non-example | dictionary reading |
| versus | clarify differences on few dimensions | H7 H2 | two columns, identical row order | more than 3 dimensions |
| myth | correct a belief without cementing it | H1 H2 | label card with strike-through, primary source for the fact | time spent on the myth |
| timeline | tempo and hinge points | H8 H4 | proportional timeline ribbon | date dump |
| news | what happened, why it matters | H9 | primary document, map, ticker, real footage | stale facts; AI depiction of the event |
| numbers | make one number graspable | H3 | pictogram or scale zoom, counter | digits without unit or denominator |
| howto | enable a task | H10 | first-person screen or hands | skipped step |
| case | transferable lesson from one entity | H6 H11 | documents, timeline, sourced chart | survivorship bias |
| ladder | one idea at 3 levels | H2 | one diagram that gains layers | levels that are not different |
| list | N items by one criterion | H7 | numbered cards on one template | padding |
| reveal | sustain curiosity to a reveal | H6 | uncover and zoom, distinct reveal frame | reveal held to the last second |
| predict | scenarios with calibrated odds | H7 H9 | branching tree or fan chart | false precision |
| paper | question, method, finding, limits | H2 H9 | annotated abstract, one redrawn figure | causal verbs on observational data |
| policy | who, what changes, when | H9 H5 | clause highlight, effective-date calendar | legal-advice tone |
| finance | a mechanism or a figure | H2 H3 | pictogram, counter, indexed line | nominal vs real confusion |
| health | benefit and risk, correctly | H2 H5 | icon array of 100 or 1,000 people | relative risk alone |
| culture | an origin or a shift in meaning | H2 H6 | word tree, language map | folk etymology as fact |
| sketch | a comic engine: a rule, a character, an escalation, a punchline | H12 H13 | the cast in a clear setting, a held reaction | explaining the joke; a spent gag |
| serial-story | a story episode that changes the story state | H12 H14 H15 | the cast and the one set that matters | a state that never changes; an unpaid cliffhanger |

## The shared grammar

```
HOOK    0-3 s    opens ONE specific question, misconception or anomaly
FRAME   3-8 s    "AND": minimum context, why care, the promise
BODY    n beats  "BUT / THEREFORE": one claim + one visual + a causal link to the next
TURN    late     the limit, the twist, or where the simple model breaks
PAYOFF  last 5 s the answer in ONE sentence with the hero number or visual
LOOP    last 1-2 s callback to the hook's wording or image, or a prediction question
```

Between any two beats the honest connector is "but", "therefore" or "because".
If the only true connector is "and then", the pair is a list, not a story: promote
the second beat to a consequence or introduce the obstacle. Count literal "and
then" and "next," in the script: zero.

A beat is one breath and one idea, and it changes one thing on screen. How long it
lasts is the format's call (`data/formats.json` `beat_seconds`): a host reel cuts
every 1.5 to 3 s, a maths explainer holds 5 to 9 s while an equation builds.

## Word budget

Words are the only length knob. About 150 to 160 wpm of continuous speech, with
5 to 10 percent left for breaths, the hook pause and the loop seam. Social
explainers can run 160 to 175 wpm; do not exceed about 175 for anything that
introduces new terms. Other languages: do not scale by word count. Dry-run the TTS
and measure seconds.

| Duration | Script words | Beats |
|---|---|---|
| 20 s | 45 to 51 | 4 |
| 30 s | 68 to 76 | 5 to 6 |
| 45 s | 101 to 114 | 7 to 8 |
| 60 s | 135 to 152 | 8 to 10 |
| 90 s | 202 to 228 | 12 to 15 |

Lengths that work in 2026 are not a race to the shortest. Reels data shows the
weakest median views under 30 s and the strongest at 45 to 60 s, though content
mix confounds it. Defaults: 30 to 60 s for one concept; 60 to 90 s only with 2 to 3
distinct beats and a loop device; nothing over 3 minutes for reach on Instagram.

## Hooks

Platform guidance, quoted from the platforms: state the content proposition in the
first 3 seconds and land the hook within 6 (TikTok ad guidance). Instagram's skip
metric is the first 3 seconds. No platform publishes a retention benchmark and no
source supports "hook in 1 second" or "cut every 2 seconds" as rules.

Mute-proof means the first 3 seconds are legible with sound off (a visual device
plus 5 words or fewer on screen) and a real audio track exists. Instagram demotes
muted reels, so never design for silence.

| Id | Archetype | Template | Risk |
|---|---|---|---|
| H1 | misconception flip | "Everyone says X. The data says the opposite." | strawman: it must be a belief people hold |
| H2 | specific question | "Why does [familiar thing] do [odd thing]?" | too broad or already known: no gap |
| H3 | number shock | "[N units] of X, every [period]." | no unit, denominator or comparator |
| H4 | anomaly in medias res | a striking real image plus one line | image must be real or labelled |
| H5 | stakes | "This changes what you pay on [date]." | fear-bait: keep to verifiable stakes |
| H6 | hidden reason | "The real reason isn't the one you've heard." | must pay off by about 60 to 70% of runtime |
| H7 | prediction | "Which is bigger? Guess first." | payoff must not wait for the last frame |
| H8 | before and after | split frame, then and now | cherry-picked endpoints |
| H9 | date-stamped news | "As of [date]: [what changed]." | stale fact |
| H10 | utility promise | "In 40 seconds you'll be able to [verb]." | promise not delivered |
| H11 | host POV | "I read the 38-page filing so you don't have to." | must be true |
| H12 | cold open in the conflict | the scene already under way, no introduction | the viewer must still know who and what is at stake within 3 s |
| H13 | rule broken | a character's routine or a stated rule is violated in the first line | the rule must be clear without explanation |
| H14 | character want | a character states what they want and what stands in the way | the want must be specific, not "to win" |
| H15 | continuity hook | "Last time: [one clause]. Now: [the new problem]." | for series only; never a minute of recap |

Open exactly one specific loop in the first 3 seconds, a question the viewer can
half-guess. A gap needs a little prior knowledge: "why do planes fly" is too big;
"why does a wing push air down to go up" is a gap. Keep one loop open at a time and
close it inside the video. Never tease what you do not deliver. A myth or false claim
must be labelled on screen and in voice from frame 1, because a viewer who swipes at
2 s sees only the false claim.

## Ten laws

1. One thesis, one open question. Thesis form: "[Subject] [verb] because or so
   [consequence]" in 20 words or fewer. If it needs "and", check it: two separate claims are two
   videos, but one claim with two parts (a cause and what keeps it going) can stay if a single
   sentence still states what the video proves.
2. Name the misconception, then replace it. Smooth explanation that never touches the
   likely misconception leaves viewers feeling informed and unchanged. Cost: 4 to 6 s.
3. Glue is "but", "therefore", "because". Never "and then".
4. One visual idea per narration beat, on the words that state it (temporal
   contiguity is the strongest multimedia effect measured).
5. Narration carries sentences. On-screen text is a label or a number next to the
   thing it labels, 5 words or fewer, never a second script.
6. Visuals are evidence or illustration, never both. AI visuals illustrate; they do not
   stand in for real events, places or people.
7. Every number carries a unit, a denominator and one comparison that makes it graspable.
8. Confidence language is calibrated; judgments are separated from facts.
9. Localise by adapting, not translating (`12-localization.md`).
10. "Viewers said they understood" is not proof of understanding.

Other design rules from the multimedia-learning literature (effect sizes are
medians from a 2021 summary): pre-teach the 1 to 3 key terms with a label before
using them (d 0.78); cut seductive details such as decorative b-roll under factual
claims (d 0.86); signal sparingly with one outline phrase, ordinal words and one
highlight per beat (d 0.70); use "you" for novices; end with something to do in the
last 3 seconds, such as a one-line prediction. The old redundancy figure of 0.86 is
outdated: the 2021 figure is 0.10 and conditional, so burned-in captions that match
the narration are low risk, while a different sentence on screen is not.

## Writing for the ear

- Mean sentence 10 to 14 words, hard maximum 24, vary between 5 and 20. One idea
  per sentence, at most one subordinate clause, the new term at the end where stress
  falls, no parentheses, no stacked noun phrases. Read it aloud once at target speed.
- English reading level on the spoken script: Flesch Reading Ease at least 70 and
  Flesch-Kincaid grade at most 8, excluding terms you pre-teach. The scores do not
  transfer to other languages.
- Write analogies with one rule: map relations, not appearance, say where it breaks in
  one sentence ("unlike water, current is not used up"), one analogy per video.
- `text` (captioned) holds digits and clean words. `tts_text` (performed) holds spelled
  numbers, caps, ellipses and engine tags. Spell numbers, symbols and abbreviations in
  `tts_text` the way they are spoken, because TTS engines mispronounce currency, dates,
  units and URLs. Keep a pronunciation list for names.

## Numbers

Say a number once, show it once. A figure is any number the viewer has to hold: a quantity, a
rate, a ratio. A bare four-digit year is a label, not a figure, and is not counted. One beat holds
at most 3 distinct figures (lint E055, set in `data/formats.json`), and across the video the
hero number, one comparator and one supporting figure are enough; the data-story and numbers
formats carry more by design. A figure in a beat must appear in the claims that beat cites
(lint E054), so a wrong digit cannot hide behind a correct source. Put the
denominator in the same sentence ("4 in 1,000", "per person per year"). Prefer absolute
to relative risk and natural frequencies to conditional probabilities. Say "percentage
points" for differences of percentages. State the window and whether values are nominal
or inflation-adjusted. Bars start at zero: truncation inflates perceived effect across
chart types and warning cues do not remove it. Compare like with like and verify the
arithmetic. Use the audience's unit system (lakh and crore; Spanish "mil millones" for
10^9).

## Calibrated language

Keep one spoken lexicon, taken from US ICD 203 bands: almost no chance 1 to 5%, very
unlikely 5 to 20%, unlikely 20 to 45%, roughly even 45 to 55%, likely 55 to 80%, very
likely 80 to 95%, almost certain 95 to 99%. Do not mix rows in one sentence. "Linked
to" for correlation, "causes" only for experimental or well-identified evidence. Mark
the shift from fact to judgment aloud ("the study suggests"). Add an as-of date to any
live fact.

## From a source to a thesis

1. Record provenance: URL, author, outlet, publication and update date, access date,
   primary or secondary, rights and paywalls.
2. Extract a claim graph: claims, numbers with units and denominators, entities, causal
   links, contrasts, quotes, visuals with rights. Mark the author's judgments.
3. Find the question the source answers. The answer is the candidate thesis.
4. Generate 3 candidate theses and score each 0 to 2 on: fits 20 words; tellable as
   but/therefore; corrects a likely misconception; opens a specific question; strongly
   supported inside the source; visualisable with allowed evidence; passes "so what";
   low harm if misread. Highest total wins. Keep the runners-up as future videos.
5. Keep only claims on the causal path plus the best proof per step. Map to beats with
   the word budget.
6. Verify: re-find the primary behind any secondary, confirm key numbers independently,
   fix as-of dates, fill `claims[]`.
7. Ship "what I cut and why" so a reviewer can restore anything that mattered.

Cut: anything off the causal path; second and third examples under 60 s; methodology
beyond one clause (who, how many, what design); hedges that change nothing; more than
3 named entities per 30 s; numbers beyond the hero number, one comparator and one
supporting figure; non-causal chronology; the history of the field; tangents; promo
adjectives. Never cut: the limitation that would reverse the conclusion, the
denominator, the date, the attribution, the label on an illustration.

| Source | Thesis lives in | Traps |
|---|---|---|
| article or URL | headline, nut graf, kicker | press-release echo, stale, opinion vs news |
| paper or PDF | abstract, key figure, limitations | spin, relative risk, preprint as settled |
| transcript or podcast | the speaker's answer to one question | out of context, rights, never clone a voice |
| tweet thread | tweet 1 plus linked evidence | unsourced, edited or deleted, private people |
| dataset | the largest or most surprising comparison | cherry-picked window, nominal vs real |
| product page | the user problem, not the feature list | unverified superlatives; say "according to the company" |
| GitHub PR | description, linked issue, benchmarks | speculating about intent, unverified benchmark |
| law or policy text | operative clauses and effective-date section | wrong jurisdiction, proposed vs in force |

Dataset to story: define unit, denominator, window and last update; compute totals,
rates, shares, ranks and change; generate candidate comparisons (top vs median, now vs
peak, A vs B on one denominator, the group that breaks the pattern); score each on
expectation gap, magnitude, robustness and visualisability; change baseline, window
and denominator, and if the story flips either make "it depends on the denominator"
the story or drop it. One comparison per 30 to 60 s, one chart whose title states the
message.

## The brief

Before the beat map, write `episode/brief.md` so the next agent (or you, after a break) starts from the same page. Five
lines are enough: the thesis in one sentence of 20 words or fewer; the intent and the format with the reason; the audience and
the language (the one the user wrote in, unless they chose another); the sources found, each with its date; the claims drafted
(`claims[]` ids). Add what the user said verbatim about tone, constraints and anything they ruled out. A series episode also
carries the output of `series.py next`.

## Sketches and serials

Comedy and story episodes use the same beat map with their own roles: `cold-open`, `title`, `recap`, `setup`, `escalate`,
`punchline`, `tag`, `cliffhanger`, and a `character` on every spoken beat. Their rules live in `formats/comedy-sketch.md` and
`formats/cartoon-episode.md`, and the series rules in `15-series.md`. Two points belong here because they decide who writes
what: models help with setups, structure and escalation but are weak at punchlines (V, professional comedians' ratings), so
every punchline is offered as three options for a human to pick or rewrite; and the key element and the key word go last.

## Script QA checklist

Run before the first paid call. B blocks, W needs a fix or a stated reason.

| # | Check | Pass | Gate |
|---|---|---|---|
| 1 | one thesis | one sentence of 20 words or fewer; every beat maps to it | B |
| 2 | hook | within 3 s and the format's word limit; one specific question, misconception or anomaly; no unlabelled false claim | B |
| 3 | open loops | one at a time, each closed inside the video, reveals closed by about 70% | B |
| 4 | causal glue | but/therefore/because between beats; zero "and then" | W |
| 5 | claim and evidence | every factual claim has a `claims[]` row with source and date; key numbers independently confirmed; judgments labelled | B |
| 6 | numbers | at most 3 per 30 s; unit, denominator, comparator; absolute risk; consistent window | B |
| 7 | confidence language | fixed lexicon; no causal verbs for correlation; as-of dates | W |
| 8 | word budget | words within the table; TTS dry run within 5% of target | B |
| 9 | spoken-ability | sentence length, numbers and abbreviations as spoken, pronunciation notes | W |
| 10 | visual-ability | every beat has a device and an evidence class; nothing that cannot be shown | B |
| 11 | text vs voice | on-screen text 5 words or fewer; captions are the narration, never another sentence | W |
| 12 | imagery honesty | no photoreal AI of real events or people; anchor line on every place-specific AI beat; disclosure plan noted | B |
| 13 | misconception and balance | likely misconception addressed in 6 s or less; contested topics give each side its strongest sourced claim and the same visual template | W |
| 14 | localisation | units, numerals, currency, analogies, term policy, RTL and fonts checked | B for multilingual |
| 15 | ending | the last line is the one-sentence answer with the hero number; callback or prediction; only a loop seam after the payoff | W |

Evidence classes for item 10: E0 real primary (cite it), E1 real generic stock (mood
only; juxtaposition implies specifics), E2 code-rendered data or mechanism (cite
source and date), E3 stylised AI illustration (add an "Illustration" chip when it
could be mistaken for evidence), E4 photoreal AI of a real place or event (avoid),
E5 AI likeness of a real person (never).
