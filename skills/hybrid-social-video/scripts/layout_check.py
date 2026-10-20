#!/usr/bin/env python3
"""layout_check.py - the QA text checks (Q1 size, Q4 safe box, Q5 collisions) measured from the page itself, not by eye.

    python3 layout_check.py --page episode/build/index.html [--times 3,8.5,14] [--min-size 40] [--caption-min 48] [--json]

Loads the composition page (the window.render(t) contract of render_html.py), renders each instant, and reads every text element's
bounding box and font size from the DOM, transforms included. At each time it checks:
  size        every text at least --min-size px (default 40, references/09-qa.md Q1), captions at least --caption-min (default 48);
  safe box    every text inside the platform's common safe box (data/platforms.json), captions above the bottom danger band;
  collisions  no two text boxes overlap by more than 4 % of the smaller one (a designed label on its own shape is not text on text).
Without --times it samples each beat of window.VIDEO (just after its start, its middle, just before its end). Prints a JSON report
(and a short summary on stderr). Exit 0 clean | 5 issues found | 3 Playwright missing | 2 usage. A page that draws text as paths or
a canvas cannot be read this way: check those by contact sheet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, parse_args  # noqa: E402

READ = """() => {
  const out = [];
  const add = (el, kind) => {
    const r = el.getBoundingClientRect();
    const txt = (el.textContent || '').trim();
    if (!txt || r.width < 1 || r.height < 1) return;
    const cs = getComputedStyle(el);
    let op = 1, n = el;
    while (n && n.nodeType === 1) { const o = parseFloat(getComputedStyle(n).opacity); if (!isNaN(o)) op *= o; n = n.parentElement; }
    if (op < 0.95) return;                      // still fading or scaling in or out: judged once it has settled
    const fs = parseFloat(el.getAttribute('font-size')) || parseFloat(cs.fontSize);
    const m = el.getScreenCTM ? el.getScreenCTM() : null;
    const scale = m ? Math.hypot(m.a, m.b) : 1;
    out.push({kind, block: el.getAttribute('data-b'), text: txt.slice(0, 40), x: r.left, y: r.top, w: r.width, h: r.height, size: Math.round(fs * scale)});
  };
  document.querySelectorAll('svg text').forEach(e => add(e, 'text'));
  document.querySelectorAll('.pill').forEach(e => add(e, 'caption'));
  return out;
}"""


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h", "json"})
    if opt.get("help") or opt.get("h") or not opt.get("page"):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        eprint("playwright is required")
        return 3
    min_size, cap_min = float(opt.get("min-size", 40)), float(opt.get("caption-min", 48))
    box = data("platforms")["safe_zones_1080x1920"]["common_safe_box"]
    issues: list[dict] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        pg.goto(Path(opt["page"]).resolve().as_uri())
        pg.wait_for_function("typeof window.render === 'function'")
        if opt.get("times") not in (None, True):
            times = [float(x) for x in str(opt["times"]).split(",")]
        else:
            beats = pg.evaluate("(window.VIDEO && window.VIDEO.beats) ? window.VIDEO.beats.map(b => [b.s, b.e]) : []")
            times = []
            for s, e in beats:
                times += [s + 0.9, (s + e) / 2, e - 0.15]
            if not times:
                times = [float(pg.evaluate("window.DUR")) / 2]
        for t in sorted(set(round(x, 2) for x in times)):
            pg.evaluate("t => window.render(t)", t)
            boxes = pg.evaluate(READ)
            for bx in boxes:
                floor = cap_min if bx["kind"] == "caption" else min_size
                if bx["size"] < floor - 0.5:
                    issues.append({"t": t, "rule": "size", "text": bx["text"], "detail": f"{bx['size']} px < {floor:g} px"})
                right, bottom = bx["x"] + bx["w"], bx["y"] + bx["h"]
                if bx["x"] < box["x"] - 3 or right > box["x"] + box["w"] + 3 or bx["y"] < box["y"] - 3 or bottom > box["y"] + box["h"] + 3:
                    issues.append({"t": t, "rule": "safe box", "text": bx["text"],
                                   "detail": f"box x {bx['x']:.0f}-{right:.0f}, y {bx['y']:.0f}-{bottom:.0f} outside x {box['x']}-{box['x'] + box['w']}, y {box['y']}-{box['y'] + box['h']}"})
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    a, c = boxes[i], boxes[j]
                    if a.get("block") is not None and a.get("block") == c.get("block"):
                        continue                                  # two lines of one wrapped text block
                    ia, ic = 0.12 * a["h"], 0.12 * c["h"]         # a text box is taller than its glyphs: compare the inner band
                    ox = min(a["x"] + a["w"], c["x"] + c["w"]) - max(a["x"], c["x"])
                    oy = min(a["y"] + a["h"] - ia, c["y"] + c["h"] - ic) - max(a["y"] + ia, c["y"] + ic)
                    if ox > 2 and oy > 2 and ox * oy > 0.04 * min(a["w"] * a["h"], c["w"] * c["h"]):
                        issues.append({"t": t, "rule": "collision", "text": f"{a['text']} / {c['text']}", "detail": f"overlap {ox:.0f}x{oy:.0f} px"})
        b.close()
    seen, uniq = set(), []
    for it in issues:                                    # the same fault at several instants is one finding, keep the first time
        k = (it["rule"], it["text"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    print(json.dumps({"ok": not uniq, "instants": len(times), "issues": uniq}, indent=2))
    for it in uniq:
        eprint(f"  {it['rule']:10s} t={it['t']}s  {it['text']}: {it['detail']}")
    eprint("[layout] " + ("clean" if not uniq else f"{len(uniq)} issue(s)"))
    return 0 if not uniq else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
