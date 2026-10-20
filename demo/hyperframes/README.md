# HyperFrames source of the demo reel

The motion design of `../hybrid-social-video-demo.mp4` was written for HyperFrames' `talking-head-recut` workflow: a host video, eight designed cards,
a caption track and one paused GSAP timeline that moves the host between full frame and a round picture-in-picture. These are the sources, kept as a
worked example of the hand-off in [`references/19-hyperframes.md`](../../skills/hybrid-social-video/references/19-hyperframes.md).

- `build_hf.py` generates `index.html` and `cards/` from `timing.json` (the host's word times), so every cue lands on the word it belongs to.
- `index.html`, `cards/`, `storyboard.json`, `transcript.json` are the generated output.
- Not included: the host video (`input-video.mp4`, AI-generated, see `../AI-USE.md`), the fonts and `gsap.min.js` that `npx hyperframes init` and the
  `talking-head-recut` skill put in `public/`.

Render: `PRODUCER_BROWSER_GPU_MODE=hardware npx hyperframes render public --skill=talking-head-recut -o output.mp4 --fps 30`, then mux the mixed audio and run
`scripts/qc_master.py`.
