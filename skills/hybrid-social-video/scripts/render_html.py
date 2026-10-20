#!/usr/bin/env python3
"""render_html.py - route L renderer: an HTML page that draws any instant -> PNG frames, in parallel, determinism-checked.

    python3 render_html.py --page build/index.html --out build/frames --fps 30 [--workers 6] [--duration 36.0]
                           [--times 1.5,4.2,9.0] [--no-check]

Page contract: the page defines `window.render(t)` (seconds, may be async) that sets every element to its state at t and
a number `window.DUR` (seconds). Everything must be a pure function of t: no wall-clock, no animation timers, no random
without a seed, so any frame can be rendered alone and twice gives the same pixels. Host video is drawn by swapping a
pre-extracted frame (`ffmpeg -i host.mp4 -vf fps=30,scale=1080:1920 hf/h%05d.jpg`) and awaiting `img.decode()`, never by
a playing <video>.
With --times it renders only those instants (for a quick look: file names t<seconds>.png); otherwise every frame as
NNNNN.png. Unless --no-check, frame 500 (or the middle frame) is rendered a second time in a fresh browser and the
hashes compared: a mismatch means the page is not deterministic and the output must not be trusted.
Encode afterwards: ffmpeg -framerate 30 -i frames/%05d.png -i mix.wav -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac out.mp4
Needs Playwright with a Chromium. Exit 0 ok | 2 usage | 3 Playwright missing | 5 not deterministic.
"""
from __future__ import annotations

import hashlib
import os
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402

READY = "typeof window.render === 'function'"


def _open(p, page: str):
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.goto(Path(page).resolve().as_uri())
    pg.wait_for_function(READY)
    return b, pg


def _work(args: tuple[str, str, int, int, int]) -> int:
    from playwright.sync_api import sync_playwright
    page, out, fps, lo, hi = args
    with sync_playwright() as p:
        b, pg = _open(p, page)
        for k in range(lo, hi):
            pg.evaluate("t => window.render(t)", k / fps)
            pg.screenshot(path=str(Path(out) / f"{k:05d}.png"))
        b.close()
    return hi - lo


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h", "no-check"})
    if opt.get("help") or opt.get("h") or not (opt.get("page") and opt.get("out")):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        eprint("playwright is required (pip install playwright && playwright install chromium)")
        return 3
    page, out, fps = opt["page"], Path(opt["out"]), int(opt.get("fps", 30))
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b, pg = _open(p, page)
        dur = float(opt["duration"]) if opt.get("duration") not in (None, True) else float(pg.evaluate("window.DUR"))
        if opt.get("times") not in (None, True):
            for t in (float(x) for x in str(opt["times"]).split(",")):
                pg.evaluate("t => window.render(t)", t)
                pg.screenshot(path=str(out / f"t{t:06.2f}.png"))
            b.close()
            print(f"rendered {len(str(opt['times']).split(','))} instants -> {out}")
            return 0
        b.close()
    total = int(dur * fps)
    for f in out.glob("[0-9]*.png"):
        f.unlink()
    n = max(1, min(int(opt.get("workers", min(6, os.cpu_count() or 2))), total))
    step = -(-total // n)
    jobs = [(page, str(out), fps, i, min(total, i + step)) for i in range(0, total, step)]
    with Pool(n) as pool:
        done = sum(pool.map(_work, jobs))
    print(f"frames rendered: {done} of {total} -> {out}")
    if not opt.get("no-check"):
        k = 500 if total > 500 else total // 2
        hs = []
        for _ in range(2):
            with sync_playwright() as p:
                b, pg = _open(p, page)
                pg.evaluate("t => window.render(t)", k / fps)
                hs.append(hashlib.sha256(pg.screenshot()).hexdigest())
                b.close()
        same = hs[0] == hs[1] and hs[0] == hashlib.sha256((out / f"{k:05d}.png").read_bytes()).hexdigest()
        print(f"determinism check on frame {k}: {'ok' if same else 'MISMATCH'}")
        if not same:
            eprint("[render] the page is not deterministic: remove timers, wall-clock reads and unseeded randomness")
            return 5
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
