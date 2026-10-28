# HyperFrames first: motion design and rendering

[HyperFrames](https://github.com/heygen-com/hyperframes) (HeyGen) renders video from HTML, and its skills carry a far deeper motion-design
craft than anything this skill ships: choreography, transitions, blocks, captions, audio mixing, a design system per project. This skill
does not copy or re-teach them. It decides the story, the claims, the cost, the look and the QC, and **hands the motion design and the
render to HyperFrames whenever it is reachable**. The built-in faceless template and the host-plus-overlay page are the fallback for when
it is not, and they are plainer: say so in the final note when you used them.

## Contents
- [Is it reachable?](#is-it-reachable) · [Get it](#get-it) · [Which workflow for which video](#which-workflow-for-which-video)
- [The hand-off](#the-hand-off) · [What stays ours](#what-stays-ours) · [When it is unreachable](#when-it-is-unreachable) · [Read, do not remember](#read-do-not-remember)

## Is it reachable?

`capability_probe.py` prints a `HyperFrames:` line: which of its skills are installed (`hyperframes`, `faceless-explainer`,
`talking-head-recut`, `general-video`, `embedded-captions`, `motion-graphics`, `media-use` ...) and whether the CLI answers. Your own skill
list and tool list are the other signal: a `/hyperframes` skill, or tools named `compose`, `render_video`, `list_projects`.

## Get it

Verified 2026-10-21.

1. **An agent with a filesystem (Claude Code, Cursor, Codex): the local skills.**

   ```bash
   npx skills add heygen-com/hyperframes        # the skills (entry point: /hyperframes); a third-party install into the agent's skill folders
   npx hyperframes doctor                         # the CLI check: browser, fonts, GSAP
   ```

   Run it yourself: the host's permission prompt is the user's consent for a third-party install, so do not ask first and do not run it
   outside that prompt. If it is declined or fails, carry on with the fallback and put the line in the final note.
2. **The hosted MCP: for chat clients with no filesystem** (Claude.ai web and desktop, ChatGPT, Grok). Read the guide,
   https://hyperframes.heygen.com/guides/mcp, and follow it. Endpoint `https://mcp.heygen.com/mcp/hyperframes/`; it needs a HeyGen
   account and an OAuth sign-in that only the user can complete (in Claude: Customize, Connectors, Add custom connector; the guide covers
   ChatGPT and Grok). In Claude Code the standard way to add a remote MCP server is
   `claude mcp add --transport http hyperframes https://mcp.heygen.com/mcp/hyperframes/` and then authorising it from `/mcp`. Its read
   tools (`list_projects`, `get_project`, `get_project_status`) work there, but **`compose` and `render_video` are refused for local
   CLI and IDE agents** with a pointer to the local skills: for those agents the hosted MCP is not a way to render, the local skills are.
   `compose` takes a prompt and a `designSource` preset (`blockframe`, `claude`, `mat`, `monochrome`, `signal`), builds a project in the
   cloud with its own narration and music (linked audio files are ignored), renders the MP4 itself, and cannot edit the user's footage; media must be
   public `https` URLs; `render_video` is a paid action.
3. Never connect a server other than the production endpoint shown in the guide, and never send secrets through it.

## Which workflow for which video

| The video | HyperFrames workflow | Notes |
|---|---|---|
| a host speaks on screen (host-broll, talking-head-package, any generated or recorded speaker) | `/talking-head-recut` | designed overlays over the existing footage; the footage's own audio stays as it is: the host's audio is the master clock (rule 10) |
| a faceless explainer (diagram-mechanism, kinetic-type-essay, data-story, flat-vector-motion) | `/faceless-explainer` | it builds the frames, narration, captions and music itself; our voice route is the fallback and the voice it uses is recorded in provenance |
| captions only on footage that exists | `/embedded-captions` | |
| anything custom, long, or mixed layers | `/general-video` | |
| short unnarrated motion, stat hits, transparent overlays | `/motion-graphics` | |
| a website, a pull request or a product as the subject | `/product-launch-video`, `/pr-to-video` | |
| maths | a Manim skill (`11-routing.md`) | |

`data/formats.json` names the default workflow per format (`hyperframes_workflow`).

## The hand-off

HyperFrames' router reads a `BRIEF.md` and then asks no brief questions. This skill writes one from the approved beat map, including each
beat's `scene` spec as a design ask with its seconds, so HyperFrames draws what the plan describes:

```bash
npx hyperframes init "$EP/hf" --non-interactive --example=blank --skill=<workflow>     # first: it refuses a non-empty folder
python3 scripts/beatmap_to_brief.py $EP/beatmap.json --out $EP/hf --spans $EP/spans.json [--host-video public/host.mp4]
cp $EP/build/host.mp4 $EP/hf/public/host.mp4                                              # host videos only
```

Then invoke `/hyperframes` (it reads the brief and runs the workflow). Tell it what is decided: the plan is approved and not to be
re-opened, the claims and the numbers, the look (a style preset that fits `style.json`, or the colours verbatim), the safe box, and for a host video that
the footage and its audio are untouched. HyperFrames keeps its own checks (`lint`, `check`, `snapshot`) and renders; run them. Ask it to report any
beat it could not realise instead of substituting another layer.

## Depth first, cards second

HyperFrames draws on top of the footage; it cannot put a word behind a head or follow a face through the picture. When a person is on screen and the plan wants
that, run `scripts/person_fx.py render` first (`20-person-aware-effects.md`) and give its `host_fx.mp4` to `/talking-head-recut` as the input video. If a card should
sit by the face, export the track (`person_track.py export host_fx.mp4 --out face.json`: per frame `cx, cy, fw, fh, top, shoulder` as 0..1 fractions) and place the
card from those numbers in the composition. The host's audio is still the master clock.

## What stays ours

Whichever route draws the picture: the story, intent and claims; the cost scout and the ledger for every paid call (a HyperFrames hosted
render or a generated voice is a paid call); the host generation; the contact sheet and `qc_master.py` on the final MP4 (the picture QC is not
HyperFrames' job); `provenance.py` (record HyperFrames as `--role code --ai false`, and HeyGen voice or music as `tts` or `music` with the
model it reports); the disclosure decision; the final note.

## When it is unreachable

Do not stop. Take the fallback (`build_video.py` for faceless, `examples/host-overlay-composition/` for a host), mark the video's motion design as the
plainer route in the decision record under accepted defects, and give the user the one-line install, `npx skills add heygen-com/hyperframes`, so the next
run is better. If the user has said they want HyperFrames and it cannot be reached, say so first in the final note.

## Lessons from the demo build

The demo reel in `demo/hyperframes/` was built this way; its generator is a worked example. Things `hyperframes lint` and `check` rejected, and what works:

- Never tween `visibility` or `autoAlpha` on an element with `class="clip"`: the framework owns clip visibility from `data-start` and `data-duration`. Fade the
  card's inner `.card` element instead.
- Never tween `left`, `top`, `width` or `height` (they snap to whole pixels and stutter under frame-by-frame capture). To move the host into a round
  picture-in-picture, keep `#video-wrap` full size and tween `x`, `y`, `scale` and `clipPath: circle(...)` about the face's centre (`transformOrigin`), with the ring
  as its own element. To return, tween them back to `x:0, y:0, scale:1`.
- Keep a pip card alive until the host has finished growing back, or the cut shows an empty frame. Run `snapshot` at every card boundary, not only mid-card.
- Put the caption lane clear of every card (here y 1330 on a 1920 frame) so graphics and captions never share pixels; check text on the host's face and hands.
- Quantise cue times to the frame (1/30 s) and read them from the host's word timings, never from an estimate.

## Read, do not remember

The HyperFrames skills and the hosted connector change independently of this file. Before relying on a name, a flag or a workflow here, read
the current source: the skill list at https://github.com/heygen-com/hyperframes/tree/main/skills, the entry point `skills/hyperframes/SKILL.md`, the
workflow you route to, and the guide above. If they differ from this page, they win; write the difference into `meta.notes`.
