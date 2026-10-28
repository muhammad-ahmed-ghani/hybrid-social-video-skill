# Host plus overlays: a working composition page

The page behind the demo video: a talking host (full frame, or a circular bubble over a blurred, tinted copy of the host)
with code-drawn overlays that follow the host's own words. It is the verified route of `references/11-routing.md`
("Host plus overlays") and `references/17-ai-models-and-tools.md` (the talking-host recipe).

Files: `index.html` (the page: `window.render(t)` and `window.DUR`, a pure function of time), `gen_data.py` (writes `data.js`),
`timing.sample.json` (what `host_assemble.py` produces), `clips.sample.json` (its input).

```bash
python3 scripts/host_assemble.py --beatmap beatmap.json --clips clips.json --out build
mkdir -p build/hf && ffmpeg -i build/host.mp4 -vf fps=30,scale=1080:1920 -q:v 3 build/hf/h%05d.jpg
cp examples/host-overlay-composition/index.html build/ && python3 examples/host-overlay-composition/gen_data.py build
python3 scripts/render_html.py --page build/index.html --out build/frames --fps 30
python3 scripts/mix_audio.py --voice build/host.mp4 --duration 35.2 --out build/mix.wav
ffmpeg -framerate 30 -i build/frames/%05d.png -i build/mix.wav -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac master.mp4
```

The page is a template: the beat functions (`diagram`, `hostOv`) and the `MODE` table at the top are specific to the demo's eight
beats. Keep the structure (timing from `timing.json`, host frame swap, mode morph, captions from the host's words, text at the QC
sizes inside the safe box) and replace the beats.
