# News brief (`news-brief`)

Family reporting · tier R1 · 25 to 75 s · 2.6 words/s · gate G1 (exception gates for unsourced claims) · cost scout-priced
(drivers: voice, any stills) · build time 20 to 40 min

What happened, why it matters, what is known and what is not, what to watch next. Speed with context and without
over-claiming. Everything is attributed and dated; visuals are real or code, never invented depictions of the event.

## Use when, avoid when

Use for current events, announcements, rulings, filings, product or policy changes, market moves, "what changed this week".
Intents: news, policy, causal, predict, paper (a new study), versus.

Avoid for breaking events you have not verified, for contested political topics where you will not present each side's
strongest sourced claim, and when an AI persona would deliver advice on health, legal, financial or political matters (a
voice-over over graphics is lower risk and monetisable).

## Look

Newsroom, editorial-serif or swiss-grid: a source chip in a fixed slot, a date stamp, a lower-third for named people, a ticker
for numbers. Restrained motion. Never imitate a real broadcaster's brand or chrome.

## Layer mix

code 30 to 80% (maps, tickers, count-ups, timelines, quote cards, annotation, captions), real or capture up to about 40%
(documents, screenshots with permission, licensed footage, official photos), stock up to about 40% for an establishing frame
(mood only), ai_image up to about 25% for clearly stylised illustration of an abstract consequence. No AI imagery of the event
itself, of real people, or of real places presented as footage. No AI news-anchor chrome.

## Beat grammar

Inverted pyramid: the answer first. 30 s (about 78 words): date-stamped hook ("As of 14 October: ..."); what happened (who,
what, when, where); known versus not known; why it matters, one concrete impact; what to watch next. 60 s adds one background
beat, competing explanations, and attribution ("according to the filing"). Each factual sentence has a `claims[]` row; the
source chip appears with it for 1.5 s or more. Judgments are marked in the voice ("analysts judge").

Add an as-of date to anything live and re-check it at the final cut. A numbers beat follows `05b-data-and-math.md`.

## Script voice

Neutral, precise, short sentences, names and titles on first mention, attribution before the claim. No loaded words. Confidence
terms from the fixed lexicon. Contested topics: each side's strongest claim in its own sourced words, the same visual template
for both, funding disclosed.

## Motion and edit

Fast but plain: slides and wipes at 0.25 to 0.5 s, hard cuts on phrase boundaries, a hold on the hero fact, one highlight
per beat. Map and document rules from `map-evidence`. Keep captions in lane A or B (`10-platforms.md`).

## Sound

A low bed 14 to 20 dB under the voice, no music stings that dramatise, soft ticks on the ticker, a single riser only for a
real reveal. No effects over the first or last 100 ms of a spoken word.

## Production route

1. Verify: primary source (filing, statement, dataset, ruling), an independent second source for key numbers and causal claims,
   the date of each, and the denominators. Unsourced claims are an exception gate: stop and ask, or cut them.
2. Beat map; lint; board; Gate 1 with the claims table.
3. Voice, timings; build with `/general-video` (or `/faceless-explainer` for an all-code version) via the handoff
   (`11-routing.md`); document and map blocks from `/hyperframes-registry`.
4. QC; independent final review; corrections path noted in the delivery message (what to update if the story changes).

## Failure modes

Stale facts; no date; unattributed claims; an AI depiction of the event or of a real person; stock footage implying the wrong
place; a headline stronger than the body; opinion presented as news; a chart with a truncated axis; a quote cropped out of
context; a single-source number; an AI-generated "expert" voice with advice; the same template used for every story.

## QA specifics

Every sentence with a fact has a claim with source and date; the as-of date is on screen or in the voice; each source chip is
legible and inside the safe lane; no AI-generated depiction of the event or its people; contested claims balanced; the disclosure
decision is recorded.
