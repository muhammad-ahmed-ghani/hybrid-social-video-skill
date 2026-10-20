# AI models and tools: knowing what you are using

A director that does not know what it is working with makes three kinds of mistake: it decides a layer is missing
when a tool for it was one search away, it ships a draft-quality route as if it were final, and it cannot say
afterwards how the video was made. This file is how to find, choose, use and record the models behind each layer.
It holds no prices and no model ids that would go stale: ids, durations, aspect ratios and costs are read from the
tool in front of you, every time.

## Contents
- [Find what exists](#find-what-exists) · [Choose a route per layer](#choose-a-route-per-layer)
- [The talking host, verified recipe](#the-talking-host-verified-recipe) · [Voice without a host](#voice-without-a-host)
- [Paid calls and credits](#paid-calls-and-credits) · [Record what you used](#record-what-you-used)
- [Consent and disclosure](#consent-and-disclosure) · [Failures seen](#failures-seen)

## Find what exists

Do this once per episode, before the decision record, and write the result into `capabilities.json`.

1. `python3 scripts/capability_probe.py --out episode/capabilities.json`. Its `ai_models` section lists local models
   and synthetic-voice routes, hosted gateways hinted by credential names, and cached weights.
2. Read your own tool list: image, video, voice, music and caption tools, media catalogs, MCP servers, and the skills you
   can load. Put each model a tool exposes into `ai_models.tool_models` with the id exactly as the tool prints it.
3. Tools are not always loaded. Some are deferred (named but without a schema until fetched) and some MCP servers are
   still connecting or need the user to authorise them. Search for them (ToolSearch with a keyword such as `image`,
   `video`, `speech`, `voice`, `music`, the provider's name) before concluding that a layer is missing. If a server needs
   authorisation, say which and carry on with the routes you do have.
4. Providers that group work under an organisation or workspace may need one chosen before the first generation. If the
   picker renders no widget the result lists the options as text: take the user's own primary or personal workspace, say
   which you took, and never the shared or official one of a company unless told to.
5. Read-only calls are free and safe: catalogs, voice lists, balance, status. Learn what a tool accepts (aspect ratios,
   durations per model, whether a model takes a reference image or audio) from its own description, not from memory.

## Choose a route per layer

| Layer | Best first | Then | Draft only |
|---|---|---|---|
| Voice and host speech | the user's own recording; host-native speech from a video model | a neural or human-grade text-to-speech tool | system voices (macOS `say`, espeak, a small local model) |
| Host on screen | a still from an image model, animated by a video model that speaks the line | stock or the user's real footage | none: go voice-over format |
| Stills | an image model chosen from the tool's list, 9:16 | stock | code-drawn |
| Clips | a video model with the needed duration and aspect ratio | a still with parallax and grain in code | none |
| Music | a generated or licensed track from a tool | a synthesised bed (a quiet pad, soft cues) | none |
| Word timings, captions | local Whisper-family speech recognition on the actual master audio | the tool's caption service | none |

Pin one model id per asset type for the whole video. Smoke-test with the cheapest call that exposes the risk (one short
clip for lip-sync and voice, one line of speech for pronunciation). Record the cost of that call from the balance or the
catalog and let it set the plan.

## The talking host, verified recipe

Verified 2026-10-20 through an MCP server that exposes an image tool, a video tool and a speech tool. The same shape works
with any stack that has an image-to-video model with native speech.

1. **Portrait.** One call to an image model, 9:16, photoreal, a fictional person (never a real person without consent).
   Prompt: who they are in one line, clothing, eye-level 35 mm look, shallow depth of field, a tidy backdrop that matches
   the video's palette, head and shoulders in the upper two thirds with empty space below the chest for overlays, no text or
   logos. Look at it before going on. This single image is the host for the whole video.
2. **One clip first.** A video model that speaks, given exactly one reference image, animates that still (image-to-video).
   Choose a duration from the model's own allow-list; pick the smallest that holds the line plus about 0.5 s. Prompt shape:

   > The <person> in the photo looks into the camera and says clearly, with a warm, energetic, natural delivery in a friendly
   > <voice description>: "<the exact line>". He or she starts speaking right away and finishes the sentence before the clip
   > ends. Lips in sync with the words, natural small head movements, blinks and relaxed hand gestures, medium close-up,
   > static camera, same backdrop, no subtitles, no text on screen, no other speech.

   Keep the voice description and the delivery sentence identical in every clip so the voice stays the same person.
3. **Check it.** Transcribe the clip locally. The words must match the line (the models say the line, then may add a stray
   word: `host_assemble.py` trims it). Look at three frames: sync, hands, background. Measure the cost from the balance
   before and after and write it into the ledger with the request id.
4. **The rest.** One clip per beat, or per run of beats that fit the model's longest duration. Every clip starts from the
   same portrait, so the jump cuts between clips are nearly seamless; alternate a small punch-in (1.0 and about 1.06) on
   successive clips so the cut reads as an edit. A clip that says something else is a content defect: change the prompt,
   one respend.
5. **Assemble.** `scripts/host_assemble.py` trims each clip to its real speech, concatenates, and writes per-word timings
   from the host's own audio. That audio is the master clock for captions, the mix and the picture (rule 10).
6. **Overlay.** An HTML page draws the graphics over the host from the timings (`examples/host-overlay-composition/`):
   the host full frame for the hook, the answer and the payoff, shrinking into a circular bubble over a blurred, tinted
   copy of itself for diagram beats, with the diagram beside it. The morph is a smooth interpolation, not a cut or a flash.
   Render with `scripts/render_html.py`, mix with `scripts/mix_audio.py`, encode, run QC.
7. **Disclose.** An AI-generated, photoreal person is disclosed as AI: the platform label on, and a line in the description.

## Voice without a host

When the video has no host, the voice-over still decides whether it feels human. Use a neural or human-grade speech tool
(read its voice list; previews are free to open) over a system voice. Pick the voice yourself by running
`scripts/voice_check.py` on the same two or three lines per route and keeping the best that is not `draft`. Send the whole
script in one call so the prosody does not reset at beat boundaries; mark expressive moments in `tts_text` only as the tool
documents. Measure the real rate with `speech_rate.py`, then lint again. If only a system voice is reachable, ship it as a
draft with the upgrade named in the note.

## Paid calls and credits

- A provider may bill in credits, not currency. Keep the unit honest: the ledger takes a number, so record credits as the
  amount, say "credits" in every `--note`, and keep a credits ledger in its own directory. Do not convert credits to
  money without a source for the rate.
- Estimate from a catalog when one exists. Otherwise run the smallest representative call and take the difference of the
  balance before and after; record it in the pricebook with source type `ledger` and use it for the plan.
- Check the ledger before each call, one call at a time; a total is not a call. Submit once, record the request id, resume
  by polling it. Never auto-retry a paid call. A call is paid even when the content is wrong.
- A host that denies a spend or a tool call is a boundary, not an obstacle: stop that step, finish what does not depend on
  it, and report what you wanted and why. Do not split the call to get under a threshold.

## Record what you used

Record at the moment of use, not at the end:

```bash
python3 scripts/provenance.py init --episode episode --director "<the model you run as>"
python3 scripts/provenance.py add --episode episode --role image --tool <tool> --model <id> --provider <vendor> --runs hosted \
    --used-for "host portrait" --realism photoreal --depicts fictional --request-id <id> --data-sent "text prompt"
python3 scripts/provenance.py add --episode episode --role host --tool <tool> --model <id> --provider <vendor> --runs hosted \
    --used-for "talking clip, beat 2" --beats 2 --realism photoreal --depicts fictional --request-id <id> --data-sent "portrait, spoken line"
python3 scripts/provenance.py add --episode episode --role stt --tool faster-whisper --model <id> --provider local --runs local --used-for "word timings"
python3 scripts/provenance.py check --episode episode --beatmap episode/beatmap.json
python3 scripts/provenance.py report --episode episode
```

The report is the AI-use statement for the final note and the disclosure verdict (`08-governance.md`). Count the director
(the model that wrote the plan, script and code), speech recognition used for timings, and any synthetic voice.

## Consent and disclosure

- Only a fictional presenter, or the user's own photos, or a person who has given the user clear permission. Never a
  photograph of anyone else, never a minor, never an identity document or a health or payment image.
- A real person's voice is cloned only with their written permission.
- An AI-generated, photoreal person or scene is labelled as AI (platform toggle plus the description) and is never passed
  off as footage; AI imagery of a real person or event is not made. See `08-governance.md` and `10-platforms.md`.

## Failures seen

| Failure | Cause | Rule |
|---|---|---|
| a free web voice endpoint returned HTTP 403 | an unofficial client the vendor blocks | never rely on an unofficial endpoint; keep a fallback |
| the generation tool refused to run: no organisation selected | the provider scopes calls to a workspace | pick one (user's own), say which, retry once |
| a clip added a stray word after the line | the model kept talking | trim by the aligned last word, not the clip end |
| the voice should match across clips | each clip is a separate roll | same voice description in every prompt; check by transcription and by ear-free metrics |
| a robotic voice shipped as final | the cheapest route was taken | the voice ladder: system voices are draft only |
| white flashes added between sections | a metric wanted a cut | never edit the picture to please a check; fix the check |
| a spend was denied by the host | a large call over the host's own threshold | stop that call, report, never split it |
