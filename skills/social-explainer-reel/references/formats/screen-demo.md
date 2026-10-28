# Screen-capture explainer (`screen-demo`)

Family code-native (capture plus code callouts) · tier R0 · 20 to 90 s · 2.5 words/s · gate G1 ·
cost scout-priced (drivers: voice, music) · build time 20 to 45 min

Real screens, designed. A product, a site, a tool, a dashboard, a code change or a filing is the subject.
The capture is the evidence; code supplies the zoom, the callouts, the cursor, the captions and the frame.
Nothing about the UI is invented.

## Use when, avoid when

Use for tutorials, "what changed" explainers, tool comparisons, a PR or release walkthrough, reading a
filing or dashboard. Intents: howto, news, versus, paper (figure and abstract), case, mechanism (for
software).

Avoid when you cannot legally capture the screen, when a third party's product would be
misrepresented, or when you are selling (a promo is `/product-launch-video`, not this).

## Look

Clean and quiet so the UI is the star: swiss-grid, editorial-serif or tech-terminal frame with a
neutral background, the capture floated on a plate with a soft shadow. The frame owns type, captions and the
step counter. Never approximate the launched product's UI: a third-party tool shown as context is rebuilt
faithfully from a capture.

## Layer mix

capture 50 to 90%, code 10 to 50% (zoom, highlight boxes, cursor, callouts, captions, step counter, redaction
bars), stock only for a non-product establishing beat. No AI video. An AI still for a title background is the
most that fits.

## Beat grammar

The how-to skeleton: utility promise (H10) in 0 to 3 s; the finished result shown first; prerequisite in one
line; 3 steps, each imperative with one action per beat (60 s allows 5 plus a checkpoint); the common mistake;
recap. News and PR variant: what changed, before and after, impact, what to do next.

Rules: the frame shows the thing the sentence names, on the word; zoom to the target before the cursor
arrives; one highlight per beat; the step counter persists (1 of 3); the real UI version, region and language
are stated; a "close on the command or the address" beat.

## Script voice

Imperative, concrete, second person. Say what to click by the label on screen. Numbers and shortcuts as
digits and glyphs in `text`.

## Motion and edit

Zoom and pan are code (keyframes on an inner wrapper, 0.4 to 0.7 s `power2.inOut`); a cursor or content that
scrolls out leaves through the frame edge, not by fading mid-frame; one continuous window across beats (scrub
every cut: whatever persists must not jump); a redaction bar (opaque, not a blur) over anything personal;
beats are 2 to 7 s with a hold on the result.

## Sound

Soft key and click sounds only if the capture has none; a quiet bed; a hit on the result.

## Production route

1. Capture first. Use a capture tool the HyperFrames family provides (`/website-to-video` for a site,
   `/pr-to-video` for a pull request) or a screen recording from the user; probe real files before planning
   around them (resolution, fps, duration, audio). Hold an empty slot labelled with a placeholder until a
   missing capture arrives.
2. Mask data: customer, personal or secret data must be fictional or masked BEFORE capture.
3. Beat map: `layer: capture` base, `overlays` for every callout; lint; storyboard; Gate 1.
4. Voice and timings; build through `/general-video` or the matching workflow with the capture as an asset.
5. QC, then check frame by frame that no personal data is legible.

## Failure modes

Wrong UI version or region; a skipped step; stale pricing or UI; sensitive data visible; the capture at the
wrong aspect (letterboxed); a zoom that overshoots the target; a tool "rebuilt" from memory; claims about
speed or results with no source; captions over the UI's key area.

## QA specifics

Every named control is visible on the word; no personal data legible in any frame; the capture is crisp at
1080 wide; the step counter matches the steps; safe-zone check on captions; claims sourced, with the
product version and date stated.
