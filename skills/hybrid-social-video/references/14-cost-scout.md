# The cost scout: pricing from the environment you are running in

This skill ships no price, no tier cost, no retry factor and no spend threshold. What a generation costs depends on which
tools this agent holds, which keys are present, which models are live this week and which promotions are running. A
number written into the skill is wrong somewhere, so costing is done at run time by a scout role and recorded in a
per-episode file, `pricebook.json`, where every price carries its source and its age. `scripts/cost_plan.py` does the
arithmetic and writes the questions only the human can answer. `scripts/capability_probe.py` records what the machine can
run.

## Contents
- [What the scout produces](#what-the-scout-produces) · [The steps](#the-steps) · [Where a price may come from](#where-a-price-may-come-from)
- [What to record besides the number](#what-to-record-besides-the-number) · [Unknown is an answer](#unknown-is-an-answer)
- [Local engines](#local-engines) · [The questions](#the-questions) · [Sub-agent brief](#sub-agent-brief)
- [Refreshing and reconciling](#refreshing-and-reconciling)

## What the scout produces

1. `episode/capabilities.json`: what this environment can run (probe output plus the agent's own tools and skills).
2. `episode/pricebook.json`: one entry per capability and route, each with `source`, `fetched_at`, `unit`, `expires`,
   `confidence` and `limits`. Schema `hybrid-pricebook/1`.
3. The cost card: the output of `cost_plan.py plan`, rendered on the Gate 1 board (`storyboard.py --pricebook`). Each line
   shows quantity, route, price per unit, source and age, with a low band and a high band, the missing prices, the cheaper
   alternatives and the questions below.

The scout spends nothing on generation. A price lookup that itself costs money needs the user's consent first.

## The steps

1. **Probe.** `python3 scripts/capability_probe.py --out episode/capabilities.json`. It lists local binaries, Python
   modules, a GPU, an already-installed HyperFrames CLI and the names (never values) of provider credentials in the
   environment. Then add what only you can see: your tool list (image, video, voice, music generators, MCP servers, media
   catalogs) under `agent_tools`, and the skills you can load under `skills`. If the HyperFrames CLI is present, run its
   usage report and record the allowance or write `unknown`. Never install anything to find out.
2. **Get the work list.** `python3 scripts/cost_plan.py init --out episode/pricebook.json`, then
   `cost_plan.py plan --beatmap beatmap.json --pricebook episode/pricebook.json [--bakeoff N]`. With an empty pricebook the
   `missing` list is exactly the capabilities and quantities this beat map needs priced. Include `--bakeoff N` when the
   format needs a style bake-off.
3. **Find a price for each, from the highest source available** (next section). For every route you could use, not only
   the first: the human picks the route, so the card needs the alternatives.
4. **Record it.** `cost_plan.py add --pricebook P --capability ai_video --provider ... --model ... --unit second --usd <x>
   --source-type tool_catalog --source-ref <tool or url> [--qualifier 720p] [--expires YYYY-MM-DD]
   [--limits max_seconds=...,concurrency=...] [--select]`. The command refuses an entry with no source. `--usd` is the
   number exactly as the source states it, per `--unit`. Convert nothing in your head; if the source quotes per minute and
   the plan needs per second, record per minute with `--unit minute` and let the mismatch surface as a question, or record
   the converted figure and write the conversion in `--notes`. If your fetch tool summarises pages, you hold a model's
   paraphrase of the page, not the page: ask it for the exact sentence that states the price and the unit, keep that
   sentence in `--notes`, and record `--confidence reported` unless the unit and the figure were quoted verbatim.
   To switch the chosen route later use `cost_plan.py select --entry <id>` (it leaves prices and timestamps alone), and
   `cost_plan.py unset --retries cap` removes an assumption you no longer stand behind.
5. **Retries.** Rejected generations are paid for, so the cap needs a multiplier for `ai_image`, `ai_video` and `host`.
   Take it from `ledger.py report` of a past episode (`observed_calls_per_beat`) when one exists, otherwise ask the user.
   A style bake-off adds stills the beats do not list: pass `--bakeoff N` to `plan`, `beatmap_lint.py` and `storyboard.py`
   (or set `meta.extra_stills`) so the card counts them. Other quantities the beat map does not list (a series' cast
   sheets and backgrounds, a theme track) go in `plan --extra ai_image=12,music=1`. A fixed series motif is
   `meta.reuse_music: true`, which counts no music track.
   Record it with `cost_plan.py set --retries ai_video=<x>,... --retries-basis "<where it came from>"`. A pricebook with
   no multiplier leaves the high band unknown, and the card says so.
6. **Plan and ask.** Run `cost_plan.py plan` again, render the board, and put the questions to the user in one message,
   in the language they write in: the questions come back as English data and the board's labels take `--labels`.
   Nothing generative runs until Gate 1 is approved and `ledger.py init` has been given the cap the user chose.

## Where a price may come from

Use the first source that answers. Record which one in `--source-type`.

| Rank | Source | `--source-type` | `--confidence` |
|---|---|---|---|
| 1 | a catalog your own tools expose (a media-model listing with price fields, an MCP tool that returns what a call will bill) | `tool_catalog` | `live` |
| 2 | the provider's pricing endpoint, read-only, called with the user's own credential already in the environment | `api` | `live` |
| 3 | the provider's official pricing page, fetched now | `web` | `live` if the page states the unit and date, else `reported` |
| 4 | the user tells you | `user` | `user` |
| 5 | this project's own past spend, from `ledger.py report` | `ledger` | `reported` |
| never | a number remembered from training, a blog post or a forum as the only source, a sibling skill's built-in estimator, a figure in an older episode's pricebook that has not been re-fetched | | |

A `reported` price is allowed on the card and is flagged on it, and the user is asked to confirm it before a large spend.
A secondary source (a review site, a leaderboard) can point you to the official page; it cannot be the price.

Reading a pricing endpoint with a key that is already in the environment is a read. Printing, logging or writing the key
anywhere is never allowed: use the name, never the value.

## What to record besides the number

The number alone misleads. Put these in the entry, because each one has produced a wrong bill:

- **The billing unit and rounding.** Per second, per clip, per image, per token, per UTF-8 byte, per minute. Whether time
  rounds up to a whole second. Whether the price depends on resolution, duration or an "auto" aspect ratio (set the
  aspect explicitly if so). Put the dependency in `--qualifier` (for example the resolution).
- **Limits.** Maximum clip seconds (`max_seconds`; the plan raises a question when a beat needs more), concurrency, rate
  limits, aspect ratios supported, languages supported.
- **Dates.** `--expires` for a promotion or a scheduled price change, and the retirement date of a model or endpoint when
  the source states one. The check warns 14 days ahead and flags an expired entry.
- **Terms.** Commercial-use permission, region exclusions and licence conditions go in `--notes`. A cheap route that
  cannot legally ship the video is not cheap.
- **Whether the call bills on failure.** Many do. If the source says nothing, write that it says nothing.
- **Language support.** For voice, transcription and avatar routes, record the languages the tool lists
  (`--supports-language "<as written in meta.language>"`). With no record the card asks the user; the skill never assumes a
  route handles a language, and a native listen is the final test (`12-localization.md`).
- **Length limits per call.** `max_seconds` for a clip or an avatar call: the plan raises a question when a beat needs more,
  or when the avatar call that covers the whole voice-over exceeds it.

## Unknown is an answer

If no source gives a price, the entry does not exist and the card shows `MISSING PRICE` with the quantity needed. Then:

- ask the user for the price, or for consent to look it up some other way;
- or offer a route that needs no price: a code, stock, capture or real layer, or a local engine;
- or offer to shrink the plan (fewer clips, fewer host seconds, stills with motion in code).

A plan with a missing price is partial: the total printed is only what had a price, it is labelled INCOMPLETE on the card
and in the summary, and it is never read as the cost of the plan. A tool catalog that fails ("account not linked") is itself a
finding: write it into `capabilities.json` and move to the next source.

Do not insert a placeholder to make the plan complete. `confidence: illustrative` exists only for a rehearsal the user
asked for, and the linter marks any plan using one (`E063`) so it cannot pass for a quote.

## Local engines

An engine on this machine (a local speech model, a local transcriber, a GPU model) costs compute and time, not credits.
Record it with `--source-type local --usd 0` so the plan counts it as free of credits, and ask the user whether GPU time
or wall-clock matters, since a local run can be slower than a paid one. Probe output tells you what exists; it does not
tell you what the user would rather spend.

## The questions

`cost_plan.py` generates them from the plan. Put them to the user together, at Gate 1, with the plan cost beside each
option, and use the host's question tool if it has one. Only ask what changes the plan:

| Question | Why it is asked |
|---|---|
| which route for each capability that has more than one | the human picks between a cheaper and a better route, with the plan cost shown |
| a price that is missing | unknown prices are never guessed |
| a price that is stale, expiring, reported or illustrative | a spend decision rests on it; offer refresh or accept |
| how many paid takes per item to assume | sets the high band, and so the cap |
| the spend cap | the ledger refuses anything beyond it; show low and high as the options |
| the single-call amount that triggers a spend card | proposed as half the cap, a ratio; the user may choose otherwise |
| a beat whose clip is longer than the model's limit | split it, shorten it or choose another model |
| a sound-effects source | free library or a priced generator |
| the tier, or the downgrade | the plan can turn every AI clip into its still with motion in code; the card shows what that saves |

Also ask, when it applies and the card cannot decide it: consent to a paid lookup, commercial-use needs, and whether a
real person's likeness or voice is involved (`08-governance.md`).

## Sub-agent brief

When the environment supports sub-agents, the scout can run as one, so the main agent keeps writing the script. Give it
this, with the paths filled in. It is self-contained on purpose: the sub-agent has only what you write.

```
Role: cost scout for a hybrid social video episode. You find what generation costs in THIS environment and record it.
You do not generate anything, install anything, or spend money.

Read: references/14-cost-scout.md in <skill dir>, and <episode>/beatmap.json.
Run, in this order:
 1. python3 <skill dir>/scripts/capability_probe.py --out <episode>/capabilities.json; then add your own tool list and
    skills to agent_tools and skills in that file.
 2. python3 <skill dir>/scripts/cost_plan.py init --out <episode>/pricebook.json
 3. python3 <skill dir>/scripts/cost_plan.py plan --beatmap <episode>/beatmap.json --pricebook <episode>/pricebook.json
    The missing list is your work list.
 4. For each capability on it, find the price from the highest-ranked source you can reach (the table in the brief). Find
    every usable route, not one. Record each with cost_plan.py add, including limits, expiry and billing traps.
Rules: never print, log or write a credential value; never record a price that has no source; when you cannot find one,
leave it missing and say so; a lookup that costs money needs the user's consent first, so report it instead of doing it.
Return: the pricebook path, and at most 200 words: routes found per capability, prices still missing, billing traps you
met, and anything that looked wrong. Do not paste the pricebook.
```

## In a series

A series keeps one pricebook at `series/pricebook.json`. Shared assets (cast sheets, rigs, the theme) are priced and spent
once; each episode is priced on its own, because prices drift between episodes: run `cost_plan.py check` before each one and
refresh what it flags. `series.py rollup` sums the spend and the shared cost spread over the episodes (`15-series.md`).

## Refreshing and reconciling

- Run `cost_plan.py check --pricebook P` before Gate 1, before any spend card, and after a long pause. The default
  freshness window is 24 hours; the user can set a different one with `--max-age-hours`.
- Re-scout when the user changes the route or tier, when a model is retired, or when a real bill differs from its estimate.
- After a run, compare `ledger.py report` to the provider's own usage figure when one exists, and say "estimated" in the
  report when one does not. Keep the observed calls per beat: it is the evidence for next episode's retry multipliers.
- A price from an earlier episode is a lead, not a quote. Fetch it again.
