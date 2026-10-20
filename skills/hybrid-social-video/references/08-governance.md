# Governance: gates, money, provenance, rights

An agent that can spend money, publish claims and depict people needs rules that
survive being ignored in the moment. The rule that matters most comes from the
open-source video pipelines surveyed: a cap or gate written only in prose is an
honour system. One reviewed project documented "no surprise bills" while no
production code ever instantiated its cost tracker; the default mode only warned.
Here the guard lives in the script that records each paid call (`scripts/ledger.py`).

## Contents
- [The gates](#the-gates) · [The ledger](#the-ledger) · [Paid calls](#paid-calls)
- [Provenance and disclosure](#provenance-and-disclosure) · [Rights and likeness](#rights-and-likeness)
- [AI presenters on regulated topics](#ai-presenters-on-regulated-topics) · [Synthetic data and made-up subjects](#synthetic-data-and-made-up-subjects)
- [Series](#series) · [Independent review](#independent-review) · [Resuming](#resuming) · [Failures seen in the wild](#failures-seen-in-the-wild)

## Authorisation and autonomy

The default is to ask nothing (`SKILL.md`, operating mode). What keeps that safe is that every paid call still passes the ledger.
Authorisation comes from the user, once, in any of these forms: a budget in the request; a standing note in the project or
user instructions; a tool the user told you to use ("use the ImagineArt MCP for the voice"); "go". From it you set a cap inside
what they said, record where it came from in `meta.notes`, and initialise the ledger with `--autonomous` so no further gate
waits on a human. With none of these, the plan is the best free version and the paid upgrade is one line with its measured
cost. A plan that spends nothing needs no ledger.

What still stops the run, because only the user can answer or because the host decides: a real person's likeness or voice, a
regulated-topic AI presenter, a credential, a vendor refusal, and any permission the host denies. A denial is a boundary: stop that
step, finish what does not depend on it, report what you wanted and why. Never split a call to slip under a threshold, never edit
a guard or a ledger to get past it, never retry a denied call with disguised input. The one allowed repeat is the same call after the user
has said, in their own words, that they want it.

## The gates## The gates

Gate count should scale with the cost of an error. Users approve about 93% of
permission prompts and fatigue sets in; five or six blocking approvals to
authorise a small budget is the mismatch to avoid. Gate where the next step spends
money or is hard to undo, where the human holds information the agent lacks
(taste, brand, facts, consent), or where an error compounds downstream. Never gate
what a script can check.

| Gate | When | Contents | Blocking |
|---|---|---|---|
| G1 plan + cost | before ANY paid call; it costs nothing to produce | the hook line, the beat map as `board.html`, the animatic, the claims table (each claim with its source, unsourced ones flagged), format, tier, voice and host choice, the cost card from the scout (each line with its source and age, low and high bands, the open questions), the cap the script will enforce | yes |
| G2 look | right before the first expensive step, only when AI imagery defines the look | 3 to 4 bake-off stills of one beat, the host portrait if any, a contact sheet of per-beat stills, a 10 s voice sample, spend so far, the exact cost of the stage about to start | yes |
| S1 series | once per series, before any episode | premise, audience, language, cast sheets and a voice sample, look pack, music motif, episode skeleton, the variation policy, three loglines with declared changes, the series budget, the disclosure and cliffhanger decisions (`15-series.md`); then `series.py lock` | yes |
| Spend card | one call at or above the big-spend threshold the user chose (default: half the cap) | what, which model, why, the estimate, what it replaces | yes (`big_spend`) |
| G3 delivery | after render | `master.mp4`, the QC report, the ledger total, a contact sheet at beat midpoints, accepted warnings, the disclosure reminder | no, unless QC still fails after the allowed retries |

Event-triggered exception gates (stop and ask): a spend estimate over the cap by more
than a small tolerance; a vendor moderation or likeness refusal (stop, re-brief,
never retry with disguised input); a claim with no source; an asset that failed
review twice; a request to use a paid tool outside the approved plan; a real person,
brand or character appearing in the plan or detected in frames.

A gate is the end of an assistant turn. Present the material, state what you will do
on approval, and stop. Doing more work in the same turn is a gate violation. Approval
is per gate: an early "go ahead" does not cover later gates unless the user says so,
and then you record that. In an autonomous run the gates are skipped, every scripted
check stays, and the decisions you took go into `beatmap.json`.

Enforce it in code:

```bash
python3 scripts/ledger.py init --episode episode --budget N --big-spend N --require plan,look   # N = what the user chose
python3 scripts/ledger.py gate --episode episode --name plan --note "user: go"   # after G1
python3 scripts/ledger.py gate --episode episode --name look --note "style B"    # after G2
python3 scripts/ledger.py init --episode episode --budget N --autonomous           # unattended: gates waived, cap kept
```

`check` and `spend` exit 4 until every required gate exists. Require `look` only when a look gate applies (AI
imagery defines the look): an R0 plan has none, so `--require plan` alone is right for it. The single-call threshold
for the spend card is the amount the user chose with `--big-spend`; without one it is half the cap, a ratio.

What not to gate: research, script polish, a scene plan separate from the beat map,
assembly, per-asset samples of cheap assets, tool choice inside the approved plan,
file-exists and schema checks, publish metadata.

## The ledger

`episode/ledger.jsonl`, one row per paid call, written by `ledger.py spend` before you
move on. Fields: `ts`, `kind` (ai_image, ai_video, host, tts, stt, music, sfx), `beat`,
`est_usd`, `note`, and optionally `request_id` and `model`. Provider-side actual cost
rarely exists per request, so reconcile with the account dashboard when you can and
say "estimated" in the report when you cannot.

- Estimate first: `ledger.py estimate --pricebook episode/pricebook.json --kind ai_video --units 5`.
  The script holds no prices. The pricebook is the one the cost scout built for this episode, each entry with
  its source and timestamp, and a kind with no entry is refused (exit 3), not guessed.
- `--force` waives only the one-respend rule, needs a `--note`, and never lets a spend past the cap. The cap moves only with
  `ledger.py raise --budget N --note "<what the user approved>"`, which records the old and new amounts.
- Cap on attempts, not successes. A cap that counts successes never fires when the
  failing step is the expensive one.
- "Unknown price" is an answer. Say so; never guess a number into the estimate.
- Fold in sibling spend: `ledger.py import --from other/costs.jsonl`.
- Report: `ledger.py report` gives totals by kind and respend count. The figure you
  tell the user must equal it.

## Paid calls

1. Submit once. Do not retry a paid submission automatically. fal's infrastructure
   already retries failed requests up to 10 times, documents no submit-level
   idempotency key, and does not say whether retried attempts are billed. Disable
   provider retries where a flag exists (fal: `x-fal-no-retry`) and retry polls only.
2. Persist the request id the moment a job is accepted (`spend --request-id`), then poll.
   A timeout or crash resumes by id. Resubmitting creates a new paid job.
3. One respend per `(kind, beat)`, only for a content defect, only after the prompt
   changed. The ledger refuses a second respend even with `--force`.
4. Cheap before expensive: still before clip, voice sample before full VO, portrait
   before host. A bad still costs one image; a bad clip built on it costs the clip.
5. A beat that fails twice moves down a layer instead of a third attempt
   (`00-layer-doctrine.md`).
6. Pin one model id per asset type for the whole reel. Models are retired on short
   notice (a Veo 3.1 preview shut down 2026-10-22; gpt-image-1 shuts down
   2026-10-23); keep ids in one table and smoke-test a model before a batch.
7. Rate limits serialise work: some video models allow one concurrent request on a
   new account. Plan wall-clock time accordingly.

## Provenance and disclosure

Keep five records in the episode directory: `beatmap.json` (claims, layers, anchors),
`ledger.jsonl` (what was paid for), `provenance.json` (which AI models and tools made what, written at the moment of use with
`scripts/provenance.py`), `spans.json` (timing), and the final QC report. From these you can state, for any frame, whether it is real, stock,
code or AI, which model made it, and where every number came from. `provenance.py report` prints the AI-use statement and a
disclosure verdict derived from the entries; `provenance.py check` must pass before delivery. Count the director (the model that
wrote the plan and code), speech recognition used for timings, and any synthetic voice.

Disclosure decision. The trigger is realism, not "AI".

| Content | Label |
|---|---|
| clearly stylised or animated imagery, diagrams, code graphics | none needed on YouTube; add an "Illustration" chip if it could pass for evidence |
| photoreal AI of a real place or event, or a real person saying or doing something they did not | do not make it; if unavoidable, platform AI-label toggle on and an on-screen label |
| your own cloned voice, AI-assisted script, captions, upscaling | no YouTube label required |
| an AI-generated person as host or channel persona | Instagram needs the AI-generated profile label or reach is limited; on YouTube an AI persona giving health, legal, financial or political advice is ineligible for monetisation |

Current platform rules and dates are in `10-platforms.md`. Provenance metadata is read
by the platforms: YouTube labels C2PA-tagged content automatically and a creator cannot
remove that label, TikTok reads C2PA and applies invisible watermarks. Stripping it is
pointless. Re-encoding with ffmpeg drops an embedded manifest, so sign the final render
if you sign at all.

A label does not make a misleading video acceptable, and viewers rarely notice labels.
Only 12% of surveyed audiences are comfortable with fully AI-made news.

Template and mass production: YouTube's "inauthentic content" policy and the originality
rules on TikTok and Instagram target interchangeable output. Per-video structure,
sourcing and script are the defence. Do not batch near-identical reels with swapped
topics.

## Rights and likeness

- Never route around a vendor refusal. A moderation or likeness block is a hard stop:
  re-brief. Renaming the prompt or removing a face to slip past a filter is the
  anti-pattern behind the 2026 disputes: within days of one video model's launch,
  studios sent cease-and-desist letters and a performers' union objected.
- No named franchises, actors, characters or brand marks in prompts. Rewrite IP-risk
  concepts to original generic descriptions.
- A real person as host needs an explicit statement that the person in the photo is the
  user or has consented. Refuse celebrity or third-party photos. Digital twins need the
  provider's consent recording.
- Voices: clone only your own or a voice you have written permission for.
- Stock and music licences: Pexels allows commercial use without attribution but not
  implying endorsement; YouTube diverts Short revenue per music track and blocks Shorts
  over 1 minute with an active claim, so use one cleared or generated track.
  `07-ai-layer.md` has the generated-music licence notes.
- Data safety: customer, personal or secret data in a screen capture must be fictional
  or masked before capture.

## AI presenters on regulated topics

YouTube's monetisation policy treats an AI-generated persona presented as a human expert giving advice on health, legal,
financial or political topics as ineligible (read in an earlier research pass and again by an evaluation agent on
2026-10-20; read the current text before relying on it). The linter raises E083 for an AI host on such a topic, from the
agent's own judgement in `meta.regulated_topic` or from an intent flagged regulated in `data/intents.json`. It is the
user's decision, never the agent's. Put three options on the cost card, each with its price: a voice-over format with
sources on screen (usually the cheapest); a real presenter who is the user or has consented, with the consent recorded; or
the AI host kept, labelled as AI on screen and in the description, with a line that it is not advice, no advice aimed at an
individual, sources shown, and the user's acceptance of the monetisation risk recorded in `meta.notes`.

## Synthetic data and made-up subjects

State where the figures come from in `meta.data_origin`: `real` (a dataset you can cite), `synthetic` (made up for the
demo), `mixed`, or `modelled` (computed from stated assumptions). Synthetic or mixed data needs a visible label from the hook
beat (an overlay of kind `synthetic-label`, E057) and the same fact said once in the voice; never name a real place or
person as the source of made-up numbers; mark such claims `computed` with their method, not `primary` or `secondary`
(E058). A computed figure records a sensitivity check in `claims[].method`: how much it moves when a window or an
assumption changes. Photoreal AI imagery of a made-up subject, or of a real place, can pass for footage (E035): use a
stylised look or label it.

## Series

A series is governed as a set. One series gate (above), paid for by a user-approved setup allowance in `series/shared/`
(`ledger.py init --episode series/shared --budget <allowance> --require series_setup`), then `series.py lock` pins the look and the cast, and
`series.py check` runs before every episode ships: language and cast match the series, the lock is intact, the
declared changes are real, hooks and treatments are not repeats, gags and threads are accounted for, and the series budget
holds. The limits are the user's answers, stored in `series.json`; unset limits are reported as measured numbers with a
question, never filled in. Platform policy for series is in `15-series.md`.

## Independent review

The producer has confirmation bias. Before delivery, if a sub-agent facility exists,
start ONE reviewer with a clean context. Give it only `master.mp4`, the contact sheet,
`claims[]` and the QC report, never your reasoning. It returns numbered findings with
timestamps and a concrete fix each; a "critical" without a proposed fix is downgraded
to "investigate". One reviewer, no fan-out, no recursive spawning: unbounded
decomposition has produced runaway token spend in other agent systems. Without sub-agent
support, do a second pass yourself against `09-qa.md` after a break from the plan: look
at frames, not at your notes.

## Resuming

Everything needed to resume is in the episode directory. Per-beat redo flags (re-run
one beat), idempotent file names keyed by beat id, skip any asset that already exists
unless the prompt hash changed, and a note in `beatmap.json` of what was last approved.
A fresh agent given the directory path must be able to continue without the chat.

## Failures seen in the wild

| Failure | Cause | Mitigation here |
|---|---|---|
| runaway spend, cap never enforced | governance lived in prose and an unused library | `ledger.py` guard in the call path |
| cap counted successes | an embed step failed so the counter never moved | count attempts, stop on N consecutive failures |
| platform retries double-bill | server retries, no idempotency key | submit once, persist request id, resume by id |
| agent fan-out burns tokens | a skill encouraged decomposition without a depth limit | one reviewer, no recursion, confirm projected spend |
| off-topic visuals | clips chosen from a global keyword list, not tied to the sentence | beat-level `visual` and `anchor`, per-beat review |
| valid file, broken video | a strobing clip passed `ffprobe` | contact sheets plus an adjacent-frame check on every clip |
| black first frame in a player | `concat -c copy` start-time quirks | re-encode at stitch, check frame 0 |
| text re-lettered in the video stage | text baked into a generated image | text in code only |
| desync | timing taken from script or TTS instead of the shipped audio | timing from the audio actually in the master |
| IP and likeness disputes | users prompted famous characters and people | no named IP, consent for likeness, hard stop on refusal |
| demonetisation | templated mass output | per-video structure, disclosure, original insight |
| vendor drift | hard-coded model ids and prices | none shipped; the cost scout re-reads ids and prices per episode |
