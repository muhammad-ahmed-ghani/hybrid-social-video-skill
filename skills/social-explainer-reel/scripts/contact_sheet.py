#!/usr/bin/env python3
"""contact_sheet.py - your eyes for the verify loop.

Samples frames from a video and tiles them into one PNG you can open and LOOK
at, with the platform UI danger zones drawn on every frame. Free and offline.

    python3 contact_sheet.py master.mp4                               # 8 evenly spaced frames
    python3 contact_sheet.py master.mp4 --times 0.4,3.2,7.9           # exact moments
    python3 contact_sheet.py master.mp4 --beatmap beatmap.json        # one frame per beat midpoint
    python3 contact_sheet.py clip.mp4 --frames 4 --cols 4 --no-zones  # raw look at one asset
    python3 contact_sheet.py master.mp4 --platform reels --out qa.png

Beat midpoints: with --beatmap, spans come from --spans spans.json
([{id,start,end}], e.g. from word timings) when given, otherwise from each
beat's estimated seconds.

What to check on the sheet (full checklist: references/09-qa.md):
  - anything important inside a red zone (caption, face, key number)?
  - text legible at thumbnail size? (if you cannot read it here, a phone cannot)
  - hook frame (t~0.4s) is a scroll-stopper with sound off?
  - wrong flags/symbols, garbled AI text, extra fingers, morphing?
  - consistent palette/grain across beats (one film, not a collage of tools)?

Prints the PNG path and per-frame times. Exit 0 ok | 1 unreadable | 2 usage.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, ffprobe_json, have, load_json, parse_args, run, word_count  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except Exception:  # pragma: no cover - PIL is optional
    HAVE_PIL = False


def beat_times(beatmap_path: str, spans_path: str | None, duration: float) -> list[tuple[str, float]]:
    bm = load_json(beatmap_path)
    beats = bm.get("beats", [])
    if spans_path:
        spans = {str(s["id"]): (float(s["start"]), float(s["end"])) for s in load_json(spans_path)}
        return [(str(b["id"]), sum(spans[str(b["id"])]) / 2) for b in beats if str(b["id"]) in spans]
    wps = float(bm.get("meta", {}).get("wps", 2.5))
    t, out = 0.0, []
    for b in beats:
        s = b.get("est_seconds") or (word_count(b.get("text", "")) / wps + float(b.get("hold_seconds", 0) or 0))
        out.append((str(b.get("id")), t + s / 2))
        t += s
    scale = duration / t if t > 0 else 1.0  # fit estimated spans onto the real duration
    return [(i, m * scale) for i, m in out]


def grab(video: Path, t: float, out: Path, width: int) -> bool:
    r = run(["ffmpeg", "-y", "-ss", f"{max(t, 0):.3f}", "-i", str(video), "-frames:v", "1",
             "-vf", f"scale={width}:-2", str(out)], timeout=120)
    return r.returncode == 0 and out.is_file()


def draw_zones(img: "Image.Image", platform: str) -> None:
    z = data("platforms")["safe_zones_1080x1920"]
    margins = z["platforms"].get(platform) or z["platforms"]["common"]
    W, H = img.size
    sx, sy = W / 1080.0, H / 1920.0
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    red = (255, 40, 40, 38)                      # light tint so the real palette stays readable; the band edge is the line
    line = (255, 60, 60, 220)
    top, bot, left, right = (margins[k] for k in ("top", "bottom", "left", "right"))
    for box in ((0, 0, W, top * sy), (0, H - bot * sy, W, H),
                (0, top * sy, left * sx, H - bot * sy), (W - right * sx, top * sy, W, H - bot * sy)):
        d.rectangle(box, fill=red)
    d.rectangle((left * sx, top * sy, W - right * sx, H - bot * sy), outline=line, width=2)
    rail = margins.get("rail")
    if rail:  # TikTok action rail: extra right margin for every row below from_y
        d.rectangle((W - (right + rail["extra_right"]) * sx, rail["from_y"] * sy, W - right * sx, H - bot * sy),
                    fill=(255, 140, 0, 90))
    img.alpha_composite(ov)


def sheet(video: Path, times: list[tuple[str, float]], out: Path, cols: int, zones: bool,
          platform: str, width: int = 270) -> bool:
    with tempfile.TemporaryDirectory() as td:
        frames = []
        for i, (label, t) in enumerate(times):
            f = Path(td) / f"f{i}.png"
            if grab(video, t, f, width):
                frames.append((label, t, f))
        if not frames:
            return False
        if not HAVE_PIL:
            # fallback: raw tiles via ffmpeg, no labels / zones
            lst = Path(td) / "in.txt"
            lst.write_text("".join(f"file '{f}'\nduration 1\n" for _, _, f in frames))
            rows = (len(frames) + cols - 1) // cols
            r = run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf",
                     f"tile={cols}x{rows}", "-frames:v", "1", str(out)])
            return r.returncode == 0
        ims = []
        for label, t, f in frames:
            im = Image.open(f).convert("RGBA")
            if zones:
                draw_zones(im, platform)
            ImageDraw.Draw(im).rectangle((0, 0, im.width, 16), fill=(0, 0, 0, 200))
            ImageDraw.Draw(im).text((4, 2), f"beat {label}  t={t:.1f}s", fill=(255, 255, 255, 255),
                                    font=ImageFont.load_default())
            ims.append(im)
        w, h = ims[0].size
        rows = (len(ims) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * w + (cols + 1) * 6, rows * h + (rows + 1) * 6), (24, 24, 28))
        for k, im in enumerate(ims):
            r_, c_ = divmod(k, cols)
            canvas.paste(im.convert("RGB"), (6 + c_ * (w + 6), 6 + r_ * (h + 6)))
        canvas.save(out)
        return True


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"no-zones", "no-hook"})
    if not pos:
        eprint(__doc__)
        return 2
    if not (have("ffmpeg") and have("ffprobe")):
        eprint("ffmpeg/ffprobe not found")
        return 2
    video = Path(pos[0])
    if not video.is_file():
        eprint(f"no such file: {video}")
        return 1
    dur = float(ffprobe_json(video).get("format", {}).get("duration") or 0)
    if dur <= 0:
        eprint(f"{video}: unreadable or zero duration - regenerate it")
        return 1
    if opt.get("times"):
        times = [(str(i), min(max(float(t), 0.0), max(dur - 0.05, 0.0)))
                 for i, t in enumerate(str(opt["times"]).split(","))]
    elif opt.get("beatmap"):
        times = beat_times(opt["beatmap"], opt.get("spans"), dur)
    else:
        n = int(opt.get("frames", 8))
        times = [(str(i), max(0.1, dur * (i + 0.5) / n)) for i in range(n)]
    if not opt.get("times") and not opt.get("no-hook"):
        times = [("hook 0.4s", min(0.4, max(dur - 0.05, 0.0)))] + times       # Q11: the hook frame, judged with sound off
    cols = int(opt.get("cols", 4))
    out = Path(opt.get("out") or video.with_suffix(".sheet.png"))
    ok = sheet(video, times, out, cols, not opt.get("no-zones"), opt.get("platform", "common"))
    if not ok:
        eprint("could not build the sheet")
        return 1
    print(json.dumps({"sheet": str(out), "frames": [{"label": l, "t": round(t, 2)} for l, t in times]}))
    eprint(f"[sheet] {out}  ({len(times)} frames; red = platform UI danger zone). Open it and look.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
