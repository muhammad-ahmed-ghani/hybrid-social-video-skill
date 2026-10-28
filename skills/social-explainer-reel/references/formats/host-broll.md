# Host plus b-roll (`host-broll`)

Family presenter-led · tier R3 · 20 to 75 s · 2.5 words/s · gates G1, G2 (look pack) and the spend card ·
cost scout-priced; the drivers are host seconds, engine and retries (the sibling skill's own estimator is
an input to the scout, not a figure to trust) · build time 30 to 60 min,
mostly avatar and clip renders

A presenter delivers a fast "let me explain" while generated and stock b-roll, evidence cards and kinetic
captions cut in. This format is built and run by `explainer-reel-skill`: its scripts, gates and money rules
apply as written. This skill adds the beat map, the layer decision per beat, the claims ledger, the look pack
gate, the spend card and the QC.

## Use when, avoid when

Use when a human presence earns trust or energy: hosted explainers, creator-style commentary, a recurring
channel host, a real person (the user) as the face. Intents: case, myth, news (with real footage as evidence),
list, reveal, versus, mechanism (with code overlays).

Avoid when you have no consent for a real person's photo, when the user's cap cannot cover the scout's low estimate (use
`kinetic-type-essay` or `data-story`), or when the story is numbers-first (the host would only stand in front of charts).

A health, legal, financial or political topic with an AI-generated persona is not forbidden, but it is the user's decision
(YouTube bars monetisation for it; Instagram requires an AI-generated profile label). The linter raises E083; put the three
options on the cost card with their prices (a voice-over format with sources, a real presenter with consent, or the AI host
kept with a label, a not-advice line and the risk accepted on the record), as `08-governance.md` describes. Intent `finance`,
`health` and `policy` usually fit other formats better for this reason.

## Look

The immersive split is the signature: one continuous frame where the host's own backdrop extends upward and
evidence floats in the headroom on a soft shadow, with the host anchored low. Kinetic captions (small sans lead,
large emphasis: serif italic for Latin text, weight or colour for scripts that have no italic), cards chosen by content (quote, headline, feature, banner), a sidechain-ducked
underscore. Identity: creator-shorts, editorial-serif, newsroom, neo-brutalist.

## Layer mix

host 30 to 70% of runtime; ai_video up to about 45%; code (overlays, charts, cards, captions) up to about 40% as
overlays on the other two; ai_image and stock up to about 15%. The hook should not be a bare face: open on the
strongest visual in the top panel with the host band below, or the host in direct address only if no strong
visual exists. Keep a continuous host shot to about 6 to 12 s, then cut away while the voice continues.

## Beat grammar

One beat is one breath, 4 to 8 words, 1.2 to 3.5 s; a cut lands about every 2 s. Roles alternate roughly half host,
half b-roll; never three identical layouts in a row; layouts: `host_full` (direct address, thesis, payoff),
`broll_full` (the image is the moment), `split` (evidence beats and the hook). Every middle beat pays off the
previous question and raises the next, joined by spoken connectives. One climax, then resolve. The close
resolves the hook's loop. Numbers go to a code overlay (a `stat` or `count-up`), never to footage.

## Script voice

Conversational, a native speaker's rhythm, no throat-clearing, `text` clean with digits, `tts_text` performed
with at most one engine tag per two beats (strongest on the hook and the payoff), `caption_emphasis` a verbatim
1 to 4 word fragment of `text`. Single language means no code-switching unless the register names two.

## Motion and edit

The avatar's own returned audio is the master clock (captions, mix, duration key off it); cut host segments with
output seek (`-ss` after `-i`) and a shared encode profile; never retime audio; never motion-interpolate the host
face; conform 25 fps avatars to 30 with duplicate-and-blur, not motion compensation. Hard cuts on phrase
boundaries, whoosh only on layout changes, captions dodge the face, a PiP takes the corner farthest from the face,
an overlay chart that would cover the face escalates to fullscreen.

## Sound

Voice at -14 LUFS delivery after the mix, music bed 14 to 20 dB under the voice, ducked; sparse SFX on layout
changes and impacts. The avatar's audio is kept untouched; ducking applies to the bed.

## Production route

1. Capabilities and consent: an avatar endpoint exists; a real person's photo needs an explicit statement that
   the person is the user or has consented. Refuse celebrity or third-party photos.
2. Beat map with layers and `visual_anchor`; lint; board; animatic; Gate 1 including cost.
3. Convert to the sibling's `plan.json` (table below), then follow its gates: lint, voice (measure duration), portrait
   (verify by eye), host (the money moment), b-roll, words, music, assemble, qc.
4. G2 look pack before the host call: portrait, a 10 s voice sample, a contact sheet of the b-roll stills, spend so far.
   Generate stills first and look at them before any clip (a bad still costs cents, a bad clip a dollar). The sibling
   generates still and clip in one call, so run its still step, review, then the clip step.
5. Person-aware layer (optional, free): when the speaker is on screen, `scripts/person_fx.py` can put a word behind the head, follow the face with a card, light the speaker,
   push the camera, drop a stamp. Plan it from the beat map (`fx_plan_from_beatmap.py`), `check` it, render `host_fx.mp4`, and use that as the base video for the steps below
   (`20-person-aware-effects.md`). One to three effects in a 35 s reel; the hook and the number beat are the best candidates.
6. Code-layer overlays (charts, quote cards, lower thirds, captions): build with HyperFrames as a transparent alpha
   track, assemble the base with `assemble.py --no-captions`, composite the overlay in ffmpeg (route F in
   `11-routing.md`), mux the avatar audio, QC.
7. Mirror the sibling's `costs.jsonl` into the ledger (`ledger.py import`).

Beat map to `plan.json`:

| beat map | plan.json |
|---|---|
| `meta.topic`, `target_seconds`, `language` | `topic`, `target_seconds`, `language` |
| `meta.visual_anchor` | `visual_anchor` (verbatim) |
| `meta.style.name`, `audio.music_brief` | `style_name`, `music_brief` |
| beat `id`, `text`, `tts_text` | `beats[].id`, `text`, `tts_text` (unchanged) |
| layer `host` | `role: "host"`, `layout: "host_full"` |
| layer `ai_video` or `stock` | `role: "broll"`, `layout: "broll_full"` or `"split"` |
| `ai.prompt`, `ai.motion` | `broll_prompt`, `motion` |
| `on_screen_text` emphasis | `emphasis_words`, `caption_emphasis` |
| claims worth a card (at most 3, source and pull quote of 7 words or fewer, no numbers) | `evidence[]` |
| layer `code` overlays (charts, stats) | not in `plan.json`: built as the HyperFrames overlay track |

## Cost

Host seconds dominate: the sibling's avatar call covers the whole voice-over (the host is the clock), so the avatar
is billed for every voice-over second, plus one still and one clip per b-roll beat. That structure is what the cost
scout prices (`14-cost-scout.md`); no figure is kept here because avatar and video prices differ per environment and
change often. Cheaper avatar tiers and fewer host seconds lower it; a premium presenter engine raises it. Set the cap
above the high band that `cost_plan.py plan` prints.

## Failure modes

An AI "expert" persona on a regulated topic; wrong-country symbols in a generic b-roll scene; a host that drifts or
goes static on flat audio; timing fixed by regenerating the host (never: assembly is free); a muxed second voice
causing drift; captions over the face; a hook that is a bare face; three identical layouts in a row; the host's
claims unsourced; every beat the same overlay.

## QA specifics

The same face in every frame; lip-sync proxies (caption coverage, a listen); the hook frame at 0.4 s with sound
off; each b-roll clip on its own beat; the anchor gate on every place-specific frame; the host stays under about
12 s per shot; QC 12 of 12 including A/V delta.

## Verified build (2026-10-20)

A host made from one fictional portrait and a video model that speaks the line, with code overlays over it, was built and
shipped end to end: portrait, one smoke-test clip, one clip per beat, `host_assemble.py` for the track and word timings, an HTML
overlay page, `render_html.py`, `mix_audio.py`, QC. The recipe, the prompt shape, the costs to measure and the failure modes are in
`17-ai-models-and-tools.md`; the working page is `examples/host-overlay-composition/`. Layout used: host full frame on the hook, the
answer and the payoff, with the code layer in the lower third (clear of the eyes and mouth); host in a bubble beside a diagram on
the explaining beats; all text at the Q1 sizes; captions from the host's own audio; no flash transitions.
