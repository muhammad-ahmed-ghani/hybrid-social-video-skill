# Series: episodic reels that stay one show

A series is not a list of videos. It has a frame that never changes, a payload that must change every
episode, a memory of what has happened, and one budget. `scripts/series.py` keeps that state on disk so a
fresh agent can continue the show from the folder alone, and it checks the set of episodes, not one episode at
a time. Evidence levels used below: V read on the primary page, R reported by a secondary source, I inference.
Dated facts are as of 2026-10-20 and drift; re-check before relying on one.

## Contents
- [Frame and payload](#frame-and-payload) · [Series types](#series-types) · [The series gate](#the-series-gate)
- [The cast](#the-cast) · [Three routes for characters](#three-routes-for-characters) · [Voice and music](#voice-and-music)
- [Writing episodes](#writing-episodes) · [Comedy](#comedy) · [Memory](#memory) · [Budget](#budget)
- [Publishing](#publishing) · [The learning loop](#the-learning-loop) · [What is not known](#what-is-not-known)

## Frame and payload

| Frame: never changes | Payload: changes every episode |
|---|---|
| the look (`style.json`, `art_style.json`), the cast and their passports, the voices, the music motif and sting | the situation, the stakes, the location, the outcome |
| recurring segment slots, the episode skeleton (the roles in order), the language | the hook formula, the treatment of each beat (layer and device), the topic and its claims |

A series may repeat its frame. It may not repeat its situation with the same outcome. YouTube's monetisation text
says so in its own words (V): it allows "a series following a set of characters across episodes" when "each video has
a distinct storyline, focus, or concept", allows a shared intro and outro, and rules out "characters put in the same
situation over and over again with the same outcome" and AI content "made with generic or unoriginal templates giving
the impression of mass production". Its reviewers look at several videos in a row from one channel (V), so the unit
that gets judged is the set. That is why `series.py episode add` refuses an episode with no declared change
(`--changes location=docks,stakes=job,outcome=wins`) and why `series.py check` compares each episode with the ones
before it. The July 2025 change was a rename, "repetitious" to "inauthentic" content, and YouTube says that kind of
content was always ineligible (V).

## Series types

| Type | Formats | What carries over | What to watch |
|---|---|---|---|
| Technology or science explainer series | any explainer format; `host-broll` or `talking-head-package` for a recurring host | the look, the host or voice, recurring segment slots ("one number", "the myth of the week"), callbacks to earlier explainers | claims go stale across episodes: every claim keeps its date; the topic changes, the structure must not become a template |
| Comedy series | `comedy-sketch` | cast, running gags, the skeleton (cold open, setup, escalate, punchline, tag) | a spent gag; AI-written punchlines (see Comedy) |
| Cartoon series | `cartoon-episode` | cast rigs, voices, locations, serial arcs | character drift if generative video is used for the cast; a state that never changes |
| News or recap series | `news-brief` | the look, the segment slots | stale facts; reposted or unoriginal material is demoted (see Publishing) |

## The series gate

One human gate per series, before any episode: the user approves, and then `series.py lock` pins the look and the
cast. The gate's own artifacts (cast sheets, a voice sample, the look bake-off, the music motif) cost money before
anything is approved, and the ledger refuses spend until a gate exists. So the user first approves a **setup allowance**,
a number they choose: `ledger.py init --episode series/shared --budget <allowance> --require series_setup`, then
`ledger.py gate --episode series/shared --name series_setup --note "user: allowance approved"`, and record the allowance
with `series.py set --budget setup_allowance=<n>`. Everything spent on the gate's artifacts goes through that ledger. Present
all of it in one message, in the user's language:

1. The premise in one sentence, the audience, the language (the one the user writes in unless they chose another).
2. The format, and the cast sheets: the canonical reference for each character, and a voice sample in the series'
   language that the user listens to.
3. The look pack: the usual look bake-off (`04-style-bible.md`), done once for the series.
4. The music motif and sting as rendered files, and the episode skeleton.
5. The variation policy, which only the user can set, then stored with `series.py set --variation ...`: the axes an
   episode may change on (`--axes`, for example location, stakes, outcome), how many must change between episodes
   (`min_changed_axes`), how alike two hooks, two scripts, two endings and two treatments may be (`max_hook_similarity`,
   `max_script_similarity`, `max_ending_similarity`, `max_structure_similarity`), how often a running gag may return
   within the window (`max_gag_uses`), and how many earlier episodes count (`window`). Until they are set,
   `series.py check` reports the measured number and asks. The numbers are a floor, not a verdict: a reworded copy can
   slip under them, which is why the check also reports the maximum over every earlier episode and warns when one outside
   the window is a copy, and why the declared changes and a human read of the loglines are the real check.
6. The first three loglines, each with its declared changes.
7. The series budget: shared assets (cast sheets, rigs, theme) once, then a per-episode envelope, from the cost scout
   (`14-cost-scout.md`) with its own `series/pricebook.json` and `cost_plan.py plan --extra ai_image=<n>` for the shared
   assets the beat map does not list. Store it with `series.py set --budget cap=...,per_episode_envelope=...`.
8. The disclosure decision. YouTube asks for disclosure only of realistic altered or synthetic content and exempts
   non-realistic and fully animated content (V); TikTok asks for a label on AI content showing "realistic-looking
   scenes or people" (V); Meta labels from self-disclosure or industry indicators (V). A cartoon carries little
   label burden; a photoreal AI cast carries all of it on every platform (I).
9. The cliffhanger default. It is a convention with mixed evidence: the one controlled experiment found cliffhangers
   raise arousal but "do not increase enjoyment or the intention to continue watching" (V, Wirz et al., N = 133, lab,
   episodes of a drama series). Default it on for serial story, off for explainers, and let the user decide.

After the lock, each episode needs only its own Gate 1 (plan, claims, the cost card for this episode, the deltas).
There is no second look gate unless the look changes, and a changed look is a new lock with a reason the user gave. The
lock hashes the style files, the reference images, each character's name, role, description, prompt anchor, voice and
rig, so adding a voice id after the lock is drift: re-lock with a reason. The reason is a record of what the user said,
not a proof that they said it. Move an episode through `planned`, `scripted`, `approved`, `produced`, `published` with
`series.py episode set`.

## The cast

A character passport lives in `series.json` and `characters/<id>/`: id, name, role, description, reference images
(hashed), a prompt anchor, the voice (engine, stored voice id, notes, measured speech rate) and, for a puppet, the rig
(`rig.json`, schema in `formats/cartoon-episode.md`, checked with `series.py character rig-check`). Rules:

- **The first clear appearance caps every later one.** Cross-shot consistency degrades sharply as the gap between
  appearances grows, and an explicit memory of verified references gave the best character fidelity (EntityBench,
  GroundShot; V). So approve the canonical sheet before anything else, keep a bank of approved frames only, and add
  to it only shots a person has accepted.
- **Compare with the canonical sheet, never with the previous episode.** Drift is cumulative (V).
- **A pass mark comes from the series' own references, not from a constant (I, untested).** Compute the similarity
  of every approved sheet view to the others (the genuine distribution) and to other cast members and generic
  characters in the same style (the impostor distribution) with one fixed encoder. The user chooses a low percentile
  of the genuine distribution as the pass mark and a high percentile of the impostors as the ceiling it must clear;
  if the two overlap, that encoder cannot tell this art style apart, so change the encoder or use a human judge.
  Treat anything above the references' own ceiling as a pasted copy, because copy-pasted references score high on
  embedding similarity (V, MultiRef-Compass). `series.py calibrate` does the arithmetic and refuses to run without the
  two percentiles. Face-identity encoders are trained on real faces; ViStoryBench itself switches to CLIP for
  non-realistic characters (V), so expect a weaker signal for flat cartoon casts. Check the encoder's licence:
  InsightFace code is MIT but its pretrained models are non-commercial unless the maintainers agree (V); DINOv2 is
  Apache 2.0 (V).

## Three routes for characters

No video model keeps a cast consistent on its own. A July 2026 benchmark of eight models found none strong on all
four dimensions, reference consistency falling as reference sets got more complex, and neither of the two leading
closed models reliably preserving a voice from a reference (V, MultiRef-Compass, arXiv 2607.14189). Pick the route
per format.

| Route | Use for | Why | Limits |
|---|---|---|---|
| **Puppet in code** | `cartoon-episode`, high-volume comedy | the same rig is the same character in every episode, with no drift, deterministic frame by frame | the rig has to be authored once per character; art style suits layered flat or anime-like art |
| **Reference-conditioned AI video** | hero moments only | models accept reference images, first and last frame, and video references | drift with distance, copy-paste, weak voice from reference; stills first and approved, then the clip |
| **Trained identity (LoRA or similar)** | a stable cast when you own the training | strongest identity when it works | 20 or more varied images; adapters do not port freely between checkpoints (V) |

**The puppet route in detail (I, a design, not a tested pipeline).** Cut the approved sheet into layers (by hand, or
with a layer-decomposition model: See-through splits an anime-style image into up to 23 inpainted layers with draw
order, code Apache-2.0, weights licence not stated, and does no rigging; Qwen-Image-Layered splits any image into 3 to
8 layers, Apache 2.0; V). Place the layers as sprites or SVG groups, author the pivots and the mouth set once, and drive
them with a GSAP timeline inside the HyperFrames composition (`11-routing.md`), rendering by seeking a paused timeline
frame by frame so the output is identical across episodes. Mouth shapes come from the audio with Rhubarb Lip Sync
(MIT; 6 basic shapes A to F plus 3 optional; its speech recogniser is English-only, its phonetic recogniser works for
other languages with lower precision, and a dialogue file improves reliability; V); expect to swap 6 to 9 mouth
sprites from its cue table. Auto-rigging is not solved: no tool turns an AI character into a rigged one, so the rig
fields are written by hand per character. Layer-decomposition failures reported by users: merged ponytails, dropped
footwear, props over the face, heavy chibi proportions, full scenes with backgrounds (V, one hands-on write-up).

Runtime licences (V): GSAP is free for commercial use, with a ban on use inside no-code animation builders that compete
with Webflow's; lottie-web MIT; the Rive web runtime MIT; Spine runtimes require each user to hold a Spine Editor
licence; Live2D is proprietary with a publication licence on release; Inochi2D BSD-2-Clause.

**The generative route in detail.** Reference limits differ by model and change monthly, so read them from the tool
catalog through the cost scout (`limits`), never from this file. For orientation as of 2026-10-20 (V, vendor docs):
several models take up to 3 to 9 reference images and a few seconds of reference video, first and last frame control
is common, video-to-video restyle exists, and one model line's preview versions shut down on 2026-10-22. Gemini Omni
documents audio references and voice editing as unsupported. Keep every generated clip short, begin from an approved
still, regenerate from the original reference and never from drifted output, and count a clip that fails the
consistency check as a failed beat.

## Voice and music

- **Dialogue is generated outside the video model, with a stored voice.** Design or clone a voice once and store its
  id (ElevenLabs: Voice Design gives previews, then `create` returns a permanent `voice_id`; Qwen3-TTS, Apache 2.0:
  generate a reference clip and reuse the clone prompt; V). Output is nondeterministic even with a seed ("subtle
  differences may still occur"; V), so a seed is not the consistency mechanism: the stored voice is. Request limits
  per call differ by engine (one engine caps the summed dialogue text per request): read them from the scout's
  `limits`.
- Measure each character's speech rate from a sample in the series' language (`speech_rate.py`) and store it in the
  passport. Play the sample to the user at the series gate: support for a language is read from the tool, and a
  native listen is the final test.
- **The music motif and the sting are fixed rendered files**, reused every episode. Generators steer style from a
  reference but "do not copy" a melody (ElevenLabs Music; V), so regeneration produces variations, not the theme.

## Writing episodes

- Start with `series.py next`: it returns the bible, the cast, the open threads, the gags and how often each was used,
  the facts established, the last episodes' hooks and treatments, the last lessons, and the budget left.
- Declare the payload (`episode add --changes`), write the beat map with `meta.series`, `meta.cast`, and a
  `character` on every spoken beat, then lint, then `series.py check`.
- **Rotate the hook.** Use a different archetype from the last episodes (`02-intents-and-scripts.md`, H12 to H15 for
  stories). `series.py check` measures hook similarity against the window.
- **Callbacks** use `callback_to: {episode, beat}` and must point at an earlier episode. Record what a later episode
  can call back to with `series.py record --type callback`.
- **Cliffhangers and threads** are recorded (`--type cliffhanger|thread --due N`) and must be paid off (`--type
  paid_off --ref <id>`); the check warns when one is not.
- **Recap** only when the series needs it, one line per earlier event, never a minute of it.

## Comedy

What is sourced, and what is not, because an agent writing comedy will otherwise invent rules.

- **AI is weak at the punchline (V).** Twenty professional comedians rated LLM comedy bland and generic, with a
  Creativity Support Index mean of 54.6 (SD 18.1), and found that LLMs helped with setups and structure while humans
  supplied the punchline (Mirowski et al., FAccT 2024). One study found over 90% of 1,008 generated jokes were the same
  25 jokes (R). So the process is: the agent drafts setups, structure and escalation; for each punchline it offers
  three options; the human picks or rewrites at Gate 1. This is the punchline pass, and it is not optional for a
  comedy series.
- **Rules with a working-writer source (V):** put the key topic element next to the punchline and the key word
  last (Toplyn); cut distracting specifics; repeat a key word if the punchline depends on it; avoid the passive;
  exaggerate; make everything clear (Toplyn). The rule of three, the inappropriate response and comic opposites locked
  in a situation (Vorhaus).
- **Not found:** any sourced number for setup length, pause length, dialogue speed or cutting on the laugh, and any
  controlled test of the rule of three. The format profile's `punchline_max_seconds` and `hold_seconds` are house
  heuristics: tune them by watching the animatic and, later, the series' own retention.

## Memory

`continuity.jsonl` is append-only; gag counts are taken over the window, so a running gag can run again after it has rested. Types: `fact` (established in the story or in the world, with a source if it is a
real claim), `gag` (a running joke, with a `ref` so uses can be counted), `thread` and `cliffhanger` (open until a
`paid_off` row references them), `callback` (something later episodes may use), `state` (a change in a character or
the situation). `series.py next` hands the agent the relevant slice, so nothing depends on the agent remembering.

## Budget

- Shared assets (cast sheets, rigs, the theme) are spent once in `<series>/shared/` with `ledger.py`, and the episode
  ledgers stay per episode. `series.py rollup` sums both, shows the shared cost spread over the episodes produced, the
  average episode, and, with `--planned N`, an estimate for N more (an average, not a quote).
- Prices drift between episodes, so run the cost scout again for each episode against the series pricebook
  (`cost_plan.py check`). The cap is the user's number, set at the series gate.

## Publishing

- Number episodes in the title and description. No platform publishes ordering, part-numbering or cadence rules for
  series (R), and ordering is now a product feature, so numbering is a convention.
- Platform series features, newest first (V unless noted): YouTube announced Shorts series on 2026-09-23 with seasons,
  episodes, custom thumbnails and sequential playback for Partner Program creators; Meta announced a test of Series
  for Reels on 2026-06-02 for selected creators, with monetisation under consideration; TikTok Series dates from 2023 as
  a paywalled collection (its help page could not be read, so limits such as video counts are unverified, R).
- Reposted or unoriginal material is demoted: Meta says "simply stitching together clips or adding your watermark does
  not qualify as meaningful enhancement" (V, 2025-07-14), and Instagram extended its no-recommendation penalty for
  reposters on 2026-04-30 (V). This bites stock-heavy episodes and cross-posting the same cut.

## The learning loop

After an episode is published, bring the platform's own retention back: `series.py analytics --episode N --file
retention.csv --seconds <the user's hook window> [--window W]` reads a CSV with `second` and `retention` (or
`viewers`), reports retention at the seconds the user named, the steepest fall over the window the user named, and the
steepest fall after the hook window (the opening seconds always fall fastest, so the later one is the one that teaches),
and stores it with the episode. It picks no hook window itself because platforms disagree on what a hook is (Instagram's
skip rate covers the first 3 seconds; YouTube's retention "Intro" is the share still watching after 30 seconds). Then
write what the numbers taught with `series.py lesson`; the next `series.py next` shows the last lessons and the last
episodes' numbers. A predicted curve before publishing is the subject of a separate research file
(`16-attention-prediction-sota.md`); nothing here depends on it.

## What is not known

No platform source gives episode-to-episode retention, completion or binge data for Shorts, Reels or TikTok series,
or a recommended cadence; the binge data that exist come from dedicated drama apps through a vendor-sponsored survey.
Microdrama conventions (1 to 2 minute episodes, 20 to 100 episodes, a cliffhanger at the end of nearly every episode)
come from Wikipedia and vendor blogs only (R). There is no sourced pacing for a serial arc across 5, 10 or 30
episodes, no sourced comic timing numbers, no named case of a templated series being demonetised, and no learned
audio-to-viseme model proven on flat 2D rigs. Of the live-action versus AI contest in vertical drama, the one datum is
that at one app live-action titles were more likely than AI titles to stay in the top 10% by views 30 days after
release (V, trade press, 2026-10-20); the source does not say why. The percentile recipe for consistency pass marks is
untested.
