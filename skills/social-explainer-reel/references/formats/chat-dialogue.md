# Chat / dialogue explainer (`chat-dialogue`)

Family code-native · tier R0 · 15 to 60 s · 2.8 words/s · gate G1 · cost scout-priced (drivers: one or two voices, music) ·
build time 15 to 30 min

An explanation delivered as a conversation: a curious person asks, an informed one answers, in a message-thread UI. The
format works because questions install the information gap for the viewer and each reply closes one loop. It is entirely
code, so it is cheap, exact and fast. Because it is easy to clone, it is the format most at risk of looking like a
template.

## Use when, avoid when

Use for misconceptions, "ask the expert" explainers, finance and everyday-science Q and A, ladders of increasing depth,
objections handled one at a time. Intents: myth, concept, ladder, versus, finance, howto, mechanism (light).

Avoid when the claim needs proof the viewer must see (use `screen-demo` or `map-evidence`), when the "expert" would be an
AI persona advising on health, legal, financial or political topics (monetisation risk; frame it as a clearly fictional Q and
A with a human-sounding but non-expert-claiming voice and cite sources), and for real people's private messages (never
reproduce real conversations without consent).

## Look

A generic message-thread UI built in HTML: rounded bubbles, a typing indicator, small reaction chips. Do not copy any real
app's chrome, logo, colours or typefaces; the look must read as a thread without imitating a product. Identities: glass-keynote,
neo-brutalist, creator-shorts, whiteboard-doodle. Two clearly different bubble colours for the two voices, at 4.5:1 text
contrast, and one accent for the answer that matters. Avatars are simple shapes or icons, never real photos.

## Layer mix

code 85 to 100%. Optional ai_image or stock for a single illustrative interlude. No AI video.

## Beat grammar

Each beat is one message or a small cluster of two: question, then answer, with the typing indicator providing the open loop.
Hook is the question that carries the misconception ("Wait, is it really cheaper to rent?") in the first message, on screen at
frame 0. Escalate: each answer raises the next question (H2 information gap). A turn where the first answer is complicated
("sort of, but"). Payoff: the one-sentence answer, with the hero number as a count-up inside the thread. Messages are 3 to 14
words on screen; narration may be the answer spoken while the bubble types in, or a two-voice read.

Rules: the answer bubble never shows more text than the narration speaks in that beat (no second script); one new idea per reply;
facts in answers have `claims[]` with a source chip as a small footer on the bubble; names are fictional.

## Script voice

Casual, specific, short. Questions voice the viewer's likely belief, replies correct it concretely. No filler small talk.
Numbers as digits on screen and spoken words in `tts_text`.

## Motion and edit

Bubbles rise in 0.25 to 0.35 s with `power3.out` and a 2 to 4 px settle; the typing indicator 0.6 to 1.0 s before a reply
(varies per beat); the thread scrolls up by one message per beat, never jumps; the hero reply enlarges slightly (scale 1.0 to
1.05) and takes the accent; hard cuts to a full-frame number or chart for the payoff. Keep the thread in the safe box, newest
message above the caption lane. Vary the typing delay and the reaction chips between beats.

## Sound

Soft message pops on arrival (vary pitch plus or minus 2 semitones), a gentle bed, a hit on the payoff. A dropout before the final
reply.

## Production route

1. Script as a thread, claims, beat map with one `device` per beat (`message`, `typing`, `count-up`, `reaction`); lint; board.
2. Voice: one narrator reading both sides, or two distinct voices (no impersonation of real people); timings.
3. Build with `/general-video` through the handoff; the UI is HTML and CSS; fonts bundled; right-to-left threads mirror the layout
   (`12-localization.md`).
4. QC; check no brand chrome is imitated.

## Failure modes

Imitating a real messenger's design; walls of text in bubbles; the same typing delay on every beat; a thread that scrolls in jumps;
the answer bubble repeating the narration word for word while the voice says something else; the "expert" character giving
unsourced advice; real names or real private messages; every episode in the same palette and shell.

## QA specifics

Bubble text 48 px or larger and at 4.5:1; messages inside the safe box; bubble text equals or abbreviates the narration; each fact has
a source chip; the hero reply is the biggest changed region; at least three different reaction or device types per video.
