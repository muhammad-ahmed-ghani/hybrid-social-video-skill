#!/usr/bin/env python3
"""animatic.py - watch the whole pacing for ~$0 before spending anything.

Renders one card per beat (layer colour, narration, what the viewer will see) and holds each for
its real or estimated duration, optionally over a scratch voice-over, into a 9:16 mp4. If the
animatic feels slow, repetitive or too long, the final will too: fix the beat map, not the render.

    python3 animatic.py beatmap.json --out animatic.mp4 [--labels labels.json] [--font FILE]
    python3 animatic.py beatmap.json --audio scratch_vo.mp3 --spans spans.json --out animatic.mp4

--spans is [{id,start,end}] from real word timings (preferred when you have a scratch VO);
otherwise each beat lasts speech units / rate (+hold_seconds).

Text is laid out with the font that covers every character in the beat map (found through
fontconfig, see textscript.py) or the one you pass with --font, wrapped by measured pixel width so
scripts written without spaces break correctly, shrunk to fit so nothing is clipped, and aligned to
the direction of each line. Shaping and right-to-left order need Pillow built with Raqm; without
it the card is still produced and the script says so: check the HTML board for those lines.
Interface strings come from ui_labels.py (translate them and pass --labels).
Needs ffmpeg and Pillow. Exit 0 ok | 1 failure | 2 usage.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui_labels  # noqa: E402
from hx_common import eprint, have, load_json, parse_args, run  # noqa: E402
from hx_common import est_beat_seconds as _est_beat_seconds  # noqa: E402
from textscript import beatmap_texts, fonts_covering, needed_codepoints  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont, features
except Exception:  # pragma: no cover
    Image = None

NO_START = set("，。、！？；：,.!?;:%‰）)]}」』”’…‥・")
NO_END = set("（([{「『“‘")
COLORS = {"code": (79, 140, 255), "ai_image": (179, 102, 255), "ai_video": (255, 95, 162),
          "stock": (53, 196, 139), "capture": (245, 165, 36), "host": (255, 122, 69),
          "real": (19, 181, 200)}
FALLBACK_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  "/usr/share/fonts/dejavu/DejaVuSans.ttf"]


def pick_font(bm: dict, forced: str | None) -> tuple[str | None, str]:
    """(path, note). The first installed font that covers every character the cards will show."""
    if forced:
        return forced, "font given on the command line"
    rows = fonts_covering(needed_codepoints(beatmap_texts(bm)))
    usable = [r for r in (rows or []) if r["file"].lower().endswith((".ttf", ".otf", ".ttc"))
              and "unifont" not in r["file"].lower()]  # a pixel-map fallback is not a display face

    def penalty(r: dict) -> int:  # an upright regular or bold face reads best on a card; never pick an italic first
        st = str(r.get("style", "")).lower()
        return (2 if ("italic" in st or "oblique" in st) else 0) + (0 if any(w in st for w in ("regular", "book", "normal", "medium", "bold")) else 1)
    usable.sort(key=penalty)
    if usable:
        return usable[0]["file"], f"covering font: {usable[0]['family']} {usable[0].get('style', '')}".strip()
    for f in FALLBACK_FONTS:
        if Path(f).is_file():
            return f, "NO installed font covers every character: some glyphs may show as boxes"
    return None, "no font found: Pillow's default is used and may not cover the text"


class Typesetter:
    def __init__(self, path: str | None):
        self.path = path
        self.raqm = bool(features.check("raqm"))
        self._cache: dict[int, "ImageFont.FreeTypeFont"] = {}

    def font(self, size: int):
        size = max(int(size), 8)
        if size not in self._cache:
            if self.path:
                try:
                    eng = ImageFont.Layout.RAQM if self.raqm else ImageFont.Layout.BASIC
                    self._cache[size] = ImageFont.truetype(self.path, size, layout_engine=eng)
                except OSError:
                    self._cache[size] = ImageFont.load_default()
            else:
                self._cache[size] = ImageFont.load_default()
        return self._cache[size]

    @staticmethod
    def may_break(cur: str, ch: str) -> bool:
        """Line-breaking rules that do not depend on a language: never start a line with closing punctuation, a
        percent sign or the rest of a number, and never end one on an opening bracket or quote."""
        if ch in NO_START or unicodedata.category(ch) in ("Pe", "Pf"):
            return False
        if cur and (cur[-1] in NO_END or unicodedata.category(cur[-1]) in ("Ps", "Pi")):
            return False
        if cur and cur[-1].isdigit() and (ch.isdigit() or ch in "%.,"):
            return False
        return True

    def wrap(self, text: str, size: int, max_w: float) -> list[str]:
        f = self.font(size)
        lines: list[str] = []
        cur = ""
        for tok in re.findall(r"\S+\s*|\s+", text):
            if f.getlength(tok.rstrip()) > max_w:  # a token wider than the line (no spaces): break by character
                for ch in tok:
                    if f.getlength(cur + ch) > max_w and cur and self.may_break(cur, ch):
                        lines.append(cur)
                        cur = ""
                    cur += ch
                continue
            if f.getlength((cur + tok).rstrip()) > max_w and cur:
                lines.append(cur.rstrip())
                cur = ""
            cur += tok
        if cur.strip():
            lines.append(cur.rstrip())
        return lines or [""]

    def line_height(self, size: int) -> float:
        """Line height from the font's own ascent and descent: tall scripts need far more than 1.3 em."""
        try:
            asc, desc = self.font(size).getmetrics()
            return max((asc + desc) * 1.06, size * 1.2)
        except Exception:
            return size * 1.3

    def fit(self, text: str, size: int, max_w: float, max_h: float, min_size: int = 14):
        s = size
        while True:
            lines = self.wrap(text, s, max_w)
            if len(lines) * self.line_height(s) <= max_h or s <= min_size:
                return s, lines
            s = int(s * 0.92)


def line_is_rtl(line: str) -> bool:
    for ch in line:
        b = unicodedata.bidirectional(ch)
        if b in ("R", "AL"):
            return True
        if b == "L":
            return False
    return False


def draw_lines(d, ts: Typesetter, lines: list[str], size: int, x0: float, y: float, W: float, color):
    f = ts.font(size)
    lh = ts.line_height(size)
    for ln in lines:
        w = f.getlength(ln)
        x = (x0 + W - w) if line_is_rtl(ln) else x0
        d.text((x, y), ln, fill=color, font=f)
        y += lh
    return y


def card(b: dict, idx: int, total: int, t0: float, t1: float, W: int, H: int, ts: Typesetter, L: dict,
         disclose: bool | None, ui: Typesetter) -> "Image.Image":
    col = COLORS.get(b.get("layer"), (136, 136, 136))
    im = Image.new("RGB", (W, H), (16, 18, 22))
    d = ImageDraw.Draw(im)
    mx = W * 0.06
    tw = W - 2 * mx
    d.rectangle((0, 0, W, int(H * 0.012)), fill=col)
    d.rectangle((0, 0, int(W * (idx + 1) / total), int(H * 0.012)), fill=col)
    y = H * 0.045
    d.text((mx, y), f"#{b.get('id')}  {str(b.get('role', '')).upper()}", fill=(160, 168, 180), font=ui.font(W * 0.045))
    if disclose is not None:
        chip = L["ai_label_on"] if disclose else L["ai_label_off"]
        cf = ui.font(W * 0.032)
        cw = cf.getlength(chip) + W * 0.04
        d.rounded_rectangle((W - mx - cw, y, W - mx, y + W * 0.06), radius=10, fill=(70, 76, 88))
        d.text((W - mx - cw + W * 0.02, y + W * 0.012), chip, fill=(235, 238, 245), font=cf)
    y += W * 0.09
    lay = L.get(f"layer_{b.get('layer')}", str(b.get("layer", "")).upper())
    lf = ui.font(W * 0.05)
    lw = lf.getlength(lay) + W * 0.05
    d.rounded_rectangle((mx, y, mx + lw, y + W * 0.085), radius=12, fill=col)
    d.text((mx + W * 0.025, y + W * 0.016), lay, fill=(255, 255, 255), font=lf)
    y += W * 0.13
    if b.get("character"):  # the speaker is a label of its own, never inside the quote
        d.text((mx, y - W * 0.035), str(b["character"]), fill=(150, 158, 170), font=ts.font(W * 0.034))
        y += W * 0.02
    size, lines = ts.fit("“" + str(b.get("text", "")) + "”", int(W * 0.068), tw, H * 0.30)
    y = draw_lines(d, ts, lines, size, mx, y, tw, (240, 243, 248)) + W * 0.03
    # a label on its own line, in the plain UI font, so it never mixes directions with the content
    d.text((mx, y), L["sees_caps"], fill=(130, 138, 150), font=ui.font(W * 0.032))
    y += ui.line_height(int(W * 0.032))
    size, lines = ts.fit(str(b.get("visual", "")), int(W * 0.04), tw, H * 0.24)
    y = draw_lines(d, ts, lines, size, mx, y, tw, (180, 188, 200)) + W * 0.025
    ost = b.get("on_screen_text") or []
    if ost:
        d.text((mx, y), L["text_caps"], fill=(130, 138, 150), font=ui.font(W * 0.032))
        y += ui.line_height(int(W * 0.032))
        size, lines = ts.fit(" / ".join(map(str, ost)), int(W * 0.045), tw, H * 0.12)
        draw_lines(d, ts, lines, size, mx, y, tw, col)
    d.text((mx, H - H * 0.06), f"{t0:4.1f}s - {t1:4.1f}s", fill=(120, 128, 140), font=ui.font(W * 0.04))
    return im


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv)
    if not pos:
        eprint(__doc__)
        return 2
    if Image is None or not have("ffmpeg"):
        eprint("needs Pillow and ffmpeg")
        return 2
    bm = load_json(pos[0])
    beats = bm.get("beats", [])
    meta = bm.get("meta", {})
    wps = float(meta.get("wps", 2.5))
    try:
        L = ui_labels.load(opt.get("labels"))
    except (OSError, ValueError, KeyError) as exc:
        eprint(f"--labels: {exc}")
        return 2
    font_path, note = pick_font(bm, opt.get("font") if isinstance(opt.get("font"), str) else None)
    ts = Typesetter(font_path)
    # interface chrome uses a plain face unless the labels were translated, in which case the covering font is used
    ui = ts if opt.get("labels") else Typesetter(next((f for f in FALLBACK_FONTS if Path(f).is_file()), font_path))
    eprint(f"[animatic] {note}" + ("" if ts.raqm else " | Pillow has no Raqm: complex scripts may not shape or reorder; check the board"))
    disclose = meta.get("disclose") if "disclose" in meta else None
    spans = None
    if opt.get("spans"):
        spans = {str(s["id"]): (float(s["start"]), float(s["end"])) for s in load_json(opt["spans"])}
    W, H = 540, 960
    out = Path(opt.get("out") or "animatic.mp4")
    with tempfile.TemporaryDirectory() as td:
        seg_list, t = [], 0.0
        for i, b in enumerate(beats):
            if spans and str(b["id"]) in spans:
                s0, s1 = spans[str(b["id"])]
                dur = max(s1 - s0, 0.2)
            else:
                dur = max(_est_beat_seconds(b, wps), 0.4)
            png = Path(td) / f"c{i:03d}.png"
            card(b, i, len(beats), t, t + dur, W, H, ts, L, disclose, ui).save(png)
            seg = Path(td) / f"s{i:03d}.mp4"
            # one exact-length segment per beat: -frames:v pins the frame count, so the
            # total tracks the beat map (the concat demuxer's image durations drift)
            r = run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                     "-frames:v", str(max(int(round(dur * 30)), 1)), "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "24", "-pix_fmt", "yuv420p", str(seg)], timeout=120)
            if r.returncode != 0:
                eprint(r.stderr[-800:])
                return 1
            seg_list.append(f"file '{seg}'\n")
            t += dur
        if not seg_list:
            eprint("no beats")
            return 1
        (Path(td) / "in.txt").write_text("".join(seg_list))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(Path(td) / "in.txt")]
        if opt.get("audio"):
            cmd += ["-i", opt["audio"], "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k"]
        else:
            cmd += ["-c", "copy"]
        cmd += ["-movflags", "+faststart", str(out)]
        r = run(cmd, timeout=600)
        if r.returncode != 0 or not out.is_file():
            eprint(r.stderr[-1500:])
            return 1
    print(json.dumps({"animatic": str(out), "seconds": round(t, 1), "beats": len(beats), "font": font_path}))
    eprint(f"[animatic] {out} ~{t:.0f}s. Watch it: is the pace right? any layer repeated too long?")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
