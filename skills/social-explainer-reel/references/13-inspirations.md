# Inspirations: what each source taught, and what was taken

The skill was built from the existing codebase (`ml-explainer-reel`, `explainer-reel-skill`, the Computer skills tree, the
HyperFrames skill set) and seven research tracks run on 2026-10-20 with web access and local measurement: editorial
families, retention and platforms, code-rendered maths and science, pipeline governance, the AI layer, motion data and
sound, and writing and accuracy. Every number in the references carries a verified, reported or inference tag in its
source report. Those reports are not shipped, but the claims that matter are restated with their evidence level where used.

Limits to remember: the web-search budget ran out part-way through, several platform help pages are JavaScript-only and
could not be read, the fetch tool summarises pages with a small model, and nearly everything format-specific about
retention is inference because no public format-level performance data exists. The unknowns list at the end says what was
not found.

## Contents
- [The four inspirations](#the-four-inspirations) · [Families surveyed](#families-surveyed)
- [Series, language and attention](#series-language-and-attention-added-2026-10-20) · [Pipelines and governance](#pipelines-and-governance) · [Licences and what we did not copy](#licences-and-what-we-did-not-copy)
- [What was measured](#what-was-measured) · [Open questions](#open-questions)

## The four inspirations

| Inspiration | What it is | What the skill takes | Where |
|---|---|---|---|
| Maths and science as code (3Blue1Brown lineage, Manim skills) | visuals generated as code, not diffusion | the picture-first and colour-as-meaning rules, audio-first timing, a vertical frame contract, a verification ladder, engine routing between Manim and HTML | `formats/math-science-manim.md`, `05b-data-and-math.md` |
| Paper-collage editorial (`Alisa0808/vox-director` and the Vox register) | a beat-map-first, style-bake-off-first pipeline; a torn-paper look | the two human gates, two shots per beat, anti-monotony camera rules, a bake-off on one beat; the collage assembled in code from AI pieces; and the correction that "Vox style" is three different things | `formats/vox-collage.md`, `formats/map-evidence.md`, `08-governance.md` |
| Talking host plus AI b-roll, 9:16 (`explainer-reel-skill`) | a fal-based pipeline: script, voice, avatar, b-roll, ffmpeg master, QC | kept intact as the build for `host-broll`; this skill adds the beat map, the layer decision, claims, a look-pack gate, a spend card and QC | `formats/host-broll.md`, `11-routing.md` |
| A full studio with real footage, cost caps and many pipelines (`calesthio/OpenMontage`) | an agent-orchestrated studio with 12 pipelines, approval gates and a cost tracker | its better ideas (below); not its volume of gates, not its code or prose | `08-governance.md`, `01-formats.md` |

## Families surveyed

Twenty families were mapped; thirteen became explainer formats (two narrative formats were added later for series). What each contributed:

| Family | Exemplars | Borrowed idea (never branding or imagery) | Became |
|---|---|---|---|
| map-led narrated documentary | Vox Atlas and Borders, RealLifeLore, Polymatter, Wendover | a clean custom-styled map with labels removed and added by hand, camera as latitude, longitude, zoom, bearing and pitch, one map move per beat; headline plate, stock, highlighted country, number card as a code-reproducible grammar | `map-evidence` |
| on-camera host with maps | Johnny Harris | a host there for a reason, not as a crutch | `host-broll` guidance |
| flat-vector motion, narrator only | Kurzgesagt | claim in the first sentence, 3 to 5 mechanism beats, a cost or number kicker, no intro or outro; recomposed natively for vertical | `flat-vector-motion` |
| fast tech and meme insert | Fireship | numbered promise on the first frame, 1 to 2 s cuts, one meme per beat at most | pace notes, `screen-demo` |
| presenter-led practical demo | Veritasium, Mark Rober, Cleo Abram | a bold hook over the most visual frame at 0 s, cuts every 1 to 2.5 s | `host-broll` pace |
| talking head with kinetic captions | Hormozi, Ali Abdaal | keyword-bold captions; the edge is the person | `talking-head-package` |
| newsroom data vertical | The Economist | cream chart cards with a source line, "personality without a person", strands | `news-brief`, `data-story` |
| publisher news vertical | NYT, Bloomberg, Axios | one sentence per plate for sound-off | `news-brief` |
| news explainer | local newsrooms, Vox TikTok | hook with a stat or question in 3 s, then what happened, why it matters, what is unknown | `news-brief` |
| whiteboard and doodle | RSA Animate lineage, MinutePhysics, Common Craft | one idea per drawing, reveal top to bottom; the effectiveness claim is unproven | `whiteboard-doodle` identity |
| illustrated hosted shows | Crash Course, SciShow, TED-Ed | a different art style per lesson | variation rule |
| mascot-led | Duolingo | works only with an ownable character and a product loop | not offered |
| long-form chaptered narration | Nexpo, Lemmino, Wendigoon | cold open and one reveal only | not ported |
| split-screen over satisfying footage, street interview, podcast clip, chat story, ELI5 expert Q and A | various | no measured grammar found | `chat-dialogue` (code only); the rest not offered |

Where the table says "became", the profile is in `data/formats.json` and the file is in `references/formats/`.

## Series, language and attention (added 2026-10-20)

Three later research passes, each with web access, tagged V (read on the primary page), R (reported) or I (inference):

- **Series craft, market and policy.** YouTube's text allows "a series following a set of characters across episodes" with
  "a distinct storyline, focus, or concept" per video and rules out the same situation with the same outcome and generic AI
  templates (V); YouTube announced Shorts series on 2026-09-23 and Meta a Series test on 2026-06-02 (V); no platform
  publishes cadence, ordering or episode-retention data (R); cliffhangers raise arousal but not enjoyment or intent to
  continue in the one controlled experiment, N = 133 (V); professional comedians rated LLM comedy bland and found models help
  with setups and structure but not punchlines (V). Rules in `15-series.md` and the two narrative formats.
- **Consistency and animation.** No video model keeps a cast consistent on its own: a July 2026 benchmark of eight models
  found none strong on all four dimensions, and drift grows with the distance between appearances (V). That is why the cartoon
  route animates layered puppets in code and uses generative clips for hero moments only. Licences were read for the tools named
  (V).
- **Pre-publish attention curves.** Researched as a separate question; the findings are in `16-attention-prediction-sota.md`. The one result that shaped this skill: per-second claims must be tested against the mean curve by
  position, which carried a result of r = 0.47 down to a partial correlation of +0.058 on 48 videos (V).

Not found, so not claimed: sourced comic timing numbers, serial-arc pacing across 5, 10 or 30 episodes, episode-to-episode
retention for any platform's series, a named case of a templated series demonetised, and a learned audio-to-viseme model proven on
flat 2D rigs.

## Pipelines and governance

From the open-source and commercial pipelines read, the ideas worth keeping (all re-implemented in our own words, none copied):

- A gate is the end of an assistant turn; approval is per gate; gate state lives on disk with ordered prerequisites. We
  enforce it in `ledger.py`.
- Estimate, reserve, reconcile, with a holdback and a rule to refuse to guess an unknown price.
- Lock the delivery promise at plan time so a cheaper fallback cannot be substituted silently.
- Never auto-retry a paid submission; persist the job id and resume.
- A content-addressed cache keyed by the call's declared inputs.
- Exact text lives in the deterministic layer, never in a generated image.
- Narration duration comes from measured audio; fix the script, not the audio.
- A post-render check that the rendered audio matches the script.
- A review finding carries a concrete fix or is demoted.
- Source media is probed before it is planned around.
- Storyboard stills approved before video renders and then reused as the clip reference; a clean-context final reviewer that
  cites frame numbers; locked identity "passports" before any shot prompt; captions burned from script text with the
  transcriber used only for timing; per-shot redo flags.

What the research flagged as weak, so we did not copy it: five or six blocking gates to authorise a default budget of a few
dollars; a budget tracker that production code never instantiated (an open issue), defaulting to warn-only; retry-policy
metadata that almost nothing consumes; a slideshow-risk score that counts metadata fields rather than pixels; no IP,
likeness or provenance policy; and advice in one collage pipeline to route celebrity and logo content to whichever model
"allows" it (we treat a vendor refusal as a hard stop).

Gaps found in `explainer-reel-skill` by reading its code (for its owner to weigh, not changed here): the paid submit is retried
client-side while fal documents no idempotency and retries infrastructure failures itself; the request id is not persisted
before polling so a timeout resubmits; the cost ledger records an estimate only; still and clip are generated in one call with
no human look between; QC lacks strobe, first-frame and safe-zone checks. This skill's ledger and QC cover the last three.

## Licences and what we did not copy

| Source | Licence | Treatment |
|---|---|---|
| `calesthio/OpenMontage` | AGPL-3.0 for the whole repository, no separate carve-out for its skill prose | ideas and architectures only; none of its code or distinctive prose is copied or closely paraphrased |
| `Alisa0808/vox-director` | MIT | ideas only; its docs disagree with themselves on the gate count |
| `adithya-s-k/manim_skill` | MIT overall, but its ManimGL examples adapt 3b1b/videos under CC BY-NC-SA 4.0 | ideas only; vendor none of its example code |
| `devamsheth21/3b1b-video-skill` | MIT | ideas only; its `loudnorm` suggestion conflicts with the no-processing rule for generated audio |
| other Manim skills read (Yusuke710, ApliroAI, Hermes `manim-video`) | MIT | ideas only; verify every CLI flag against the installed Manim version, since several are dead in CE 0.22 |
| HyperFrames | Apache-2.0 | used through its own skills; not re-explained here |
| Remotion | custom: free for individuals, for-profit organisations up to 3 employees, non-profits; a company licence above that | not used; decide before adopting |
| GSAP | its own standard licence, free for commercial use with a no-code-builder restriction | check terms before shipping a product that generates videos for end users |
| `riso-colors` palette values | MIT | palette values only |
| Kurzgesagt-like palette | a fan palette, not official | the `flat-vector` identity borrows an approach, not any brand asset |
| Fonts in `data/identities.json` | OFL except four Apache-2.0 families | bundle files; no CDN fetch at render time |

## What was measured

Run locally, reproducible from the commands in the references: GSAP ease curves (overshoot and settle times), WCAG contrast
of all 14 identities and the scrim table, tabular-figure behaviour of 20 fonts, Arabic, Urdu and Devanagari splitting and
line-height minima in headless Chromium, banding against grain type, sidechain ducking depths, two-pass loudnorm accuracy,
audio and video sync detection, ffmpeg detector behaviour (black, freeze, silence, scene), Manim CE 0.22 frame rounding,
vertical frame geometry and font capacity, an Euler versus RK4 pendulum, KaTeX in a HyperFrames 1080x1920 composition, and the
Shorts and long-form cut-rate and pace data in `01-formats.md`. The retention and platform numbers are reported, not measured:
no platform publishes a retention benchmark.

## Open questions

Not found, so stated as unknown and never as fact: any platform-published retention, completion or swipe-away benchmark; any
format-level 2026 performance data for map, motion-graphic, Hormozi-style, avatar, chat-story, ELI5, screen-recording or
split-screen explainers; platform loudness targets (only EBU R128 and Spotify are documented); official organic safe-zone
templates for Reels and Shorts (the measured bands are ad templates); TikTok and Instagram AI-label mechanics beyond the
published rules; current-generation video-model failure rates for text, counts and hands; Urdu TTS quality; reading-speed limits
for Arabic, Urdu, Hindi, Chinese and Korean captions; whether first and last frame modes reliably hold a still end frame; any
controlled comparison of JSON and prose prompts for cross-frame consistency; the effect of film grain, imperfection prompts or
real-footage mixing on viewer perception or platform flagging; how Vox's own map grammar (cut rate, frame-rate treatment, palette)
works beyond one creator's account of his tooling; and real-speech ducking settings (the table used a synthetic voice).
