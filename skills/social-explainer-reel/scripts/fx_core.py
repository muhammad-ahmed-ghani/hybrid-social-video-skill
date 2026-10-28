"""fx_core.py - the drawing, compositing and camera kit behind the person-aware effects (see person_fx.py and fx_library.py).

A frame is a float32 RGB array plus a person matte and a head position. Everything an effect draws goes through `comp`, which takes a
depth: "front" (over everything), "behind" (hidden wherever the person is, so a word sits behind a head) or "guard" (in front, but never over
the face). Front layers are measured against the head, so `person_fx.py audit` can fail an effect that covers a face.

Sizes are written for a 1080 px wide frame and scaled by `c.u`; the renderer works at any size. Needs numpy, opencv-python and Pillow.
"""
from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_assets  # noqa: E402

# ------------------------------------------------------------------------------------------------------------------ colours

CREAM, INK, PEACH, YELLOW = (244, 233, 216), (22, 22, 24), (255, 183, 165), (255, 214, 10)
GREEN, BLUE, PURPLE, ORANGE, RED, WHITE = (34, 197, 94), (10, 132, 255), (124, 92, 255), (217, 119, 87), (238, 34, 34), (255, 255, 255)


def rgb(v, default=WHITE):
    """'#ffcc00', 'ffcc00', (255, 204, 0) or None -> an (r, g, b) tuple."""
    if v is None or v == "":
        return default
    if isinstance(v, (list, tuple)):
        return tuple(int(x) for x in v[:3])
    s = str(v).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


@dataclass
class Theme:
    """The look the effects draw in. `from_style` reads the tokens of an episode's style.json so graphics match the rest of the video."""
    accent: tuple = YELLOW
    accent2: tuple = (255, 45, 85)
    pop: tuple = (43, 255, 136)
    ink: tuple = INK
    paper: tuple = CREAM
    bg: tuple = (28, 28, 36)
    surface: tuple = (42, 42, 54)
    muted: tuple = (180, 180, 198)

    @classmethod
    def from_style(cls, path: str | Path | None):
        t = cls()
        if not path:
            return t
        import json
        try:
            tok = json.loads(Path(path).read_text(encoding="utf-8")).get("tokens", {})
        except Exception:
            return t
        for k, attr in (("accent", "accent"), ("accent2", "accent2"), ("pop", "pop"), ("bg", "bg"), ("surface", "surface"), ("muted", "muted")):
            if k in tok:
                setattr(t, attr, rgb(tok[k], getattr(t, attr)))
        if "ink" in tok:
            t.paper = rgb(tok["ink"], t.paper)
        return t


# ------------------------------------------------------------------------------------------------------------------- easing

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_inout(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def ease_back(x, s=1.7):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def ease_spring(x, damp=7.0, freq=11.0):
    """A damped spring from 0 to 1: overshoots, settles."""
    x = clamp(x)
    return 1 - math.exp(-damp * x) * math.cos(freq * x) if x < 1 else 1.0


def keyframes(p, keys, ease=ease_inout):
    """Interpolate a value through [(position, value), ...] sorted by position; values may be floats or equal-length tuples."""
    if p <= keys[0][0]:
        return keys[0][1]
    for (pa, va), (pb, vb) in zip(keys, keys[1:]):
        if p <= pb:
            q = ease((p - pa) / max(1e-9, pb - pa))
            if isinstance(va, (tuple, list)):
                return tuple(lerp(x, y, q) for x, y in zip(va, vb))
            return lerp(va, vb, q)
    return keys[-1][1]


def pop(c, t0, dur=0.3):
    """0 before t0, then an overshooting 0..1 over `dur` seconds of the effect's local time."""
    return ease_back((c.lt - t0) / dur) if c.lt > t0 else 0.0


def ramp(c, e, t_in=0.25, t_out=0.2):
    """1 inside the effect's window with a fade in and a fade out."""
    a = clamp(c.lt / t_in) if t_in else 1.0
    return a * (clamp((e.d - c.lt) / t_out) if t_out else 1.0)


def split_num(s):
    """'197K' -> (197.0, 'K', 0); '82%' -> (82.0, '%', 0); '1.2M' -> (1.2, 'M', 1); '$4,200' -> (4200.0, '', 0) with the prefix kept by the caller."""
    import re
    m = re.match(r"\s*([^\d.\-]*)([\d.,]+)\s*(.*)", str(s))
    if not m:
        return 0.0, str(s), 0
    num = m.group(2).replace(",", "")
    try:
        val = float(num)
    except ValueError:
        val = 0.0
    return val, m.group(3), (len(num.split(".")[1]) if "." in num else 0)


def count_text(s, p):
    """The text of a number counting up to `s` (keeps a prefix like $ and a suffix like K or %). p is 0..1."""
    import re
    m = re.match(r"\s*([^\d.\-]*)([\d.,]+)\s*(.*)", str(s))
    if not m:
        return str(s)
    val, suf, dec = split_num(s)
    return f"{m.group(1)}{val * ease_out(p):,.{dec}f}{suf}"


def typed(s, p):
    """The first part of a string for typewriter progress p in 0..1."""
    return s[: int(round(len(s) * clamp(p)))]


# ------------------------------------------------------------------------------------------------------------------- fonts

_KIND = {"display": "anton", "bold": "archivo-black", "serif": "instrument-serif-italic", "serifr": "instrument-serif", "mono": "space-mono-bold",
         "hand": "permanent-marker", "script": "caveat", "ui": "inter", "uim": "inter", "uib": "inter", "mont": "montserrat", "monts": "montserrat",
         "montb": "montserrat", "didone": "playfair", "didoneb": "playfair", "didonei": "playfair-italic"}
_AXES = {"ui": (24, 600), "uim": (24, 520), "uib": (32, 860), "mont": (700,), "monts": (600,), "montb": (800,), "didone": (500,), "didoneb": (800,),
         "didonei": (500,), "script": (700,)}
_SYSTEM = {
    "heavy": ["/System/Library/Fonts/Supplemental/Impact.ttf", "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/Library/Fonts/Arial Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "sans": ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/HelveticaNeue.ttc", "/Library/Fonts/Arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"],
    "serif": ["/System/Library/Fonts/Supplemental/Georgia Italic.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", "C:/Windows/Fonts/georgiai.ttf"],
    "mono": ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Courier.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             "C:/Windows/Fonts/consolab.ttf"],
}
_FALL = {"display": "heavy", "bold": "heavy", "serif": "serif", "serifr": "serif", "mono": "mono", "hand": "heavy", "script": "serif",
         "didone": "serif", "didoneb": "serif", "didonei": "serif"}
_fc: dict = {}
_font_missing: set = set()
FONT_FALLBACKS: set = set()     # kinds that had to fall back to a system font: person_fx reports it


def _system_font(kind, size):
    for p in _SYSTEM[_FALL.get(kind, "sans")]:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def font(kind: str, size: float):
    k = (kind, max(8, int(size)))          # some system fonts divide by zero below 8 px
    if k in _fc:
        return _fc[k]
    key = _KIND[kind]
    f = None
    if key not in _font_missing:
        p = fx_assets.ensure(key)
        if p is None:
            _font_missing.add(key)
        else:
            try:
                f = ImageFont.truetype(str(p), k[1])
                if kind in _AXES:
                    try:
                        f.set_variation_by_axes(list(_AXES[kind]))
                    except Exception:
                        pass
            except Exception:
                _font_missing.add(key)
                f = None
    if f is None:
        FONT_FALLBACKS.add(kind)
        f = _system_font(kind, k[1])
    _fc[k] = f
    return f


# -------------------------------------------------------------------------------------------------------------- shapes and text

def to_np(im):
    return np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0


def _aa(w, h, draw, k=3):
    """Draw at k times the size and shrink: anti-aliased shapes from PIL's aliased primitives."""
    big = Image.new("RGBA", (int(w) * k, int(h) * k), (0, 0, 0, 0))
    draw(ImageDraw.Draw(big), k)
    return big.resize((int(w), int(h)), Image.LANCZOS)


def rrect(w, h, r, fill, outline=None, width=0):
    def d(dr, k):
        dr.rounded_rectangle([0, 0, int(w) * k - 1, int(h) * k - 1], int(r * k), fill=fill, outline=outline, width=int(width * k))
    return _aa(w, h, d, 2)


def ellipse(w, h, fill, outline=None, width=0):
    def d(dr, k):
        dr.ellipse([0, 0, int(w) * k - 1, int(h) * k - 1], fill=fill, outline=outline, width=int(width * k))
    return _aa(w, h, d, 3)


def vgradient(w, h, top, bottom, r=0):
    """A vertical gradient, optionally with rounded corners."""
    t = np.linspace(0, 1, int(h), dtype=np.float32)[:, None, None]
    a = (np.array(list(top) + [255], np.float32)[None, None, :] * (1 - t) + np.array(list(bottom) + [255], np.float32)[None, None, :] * t)
    im = Image.fromarray(np.repeat(a, int(w), axis=1).astype(np.uint8), "RGBA")
    if r:
        m = Image.new("L", (int(w), int(h)), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], int(r), fill=255)
        im.putalpha(m)
    return im


def shadowed(im, blur=18, dy=10, alpha=120, color=(0, 0, 0)):
    pad = int(blur * 2 + abs(dy))
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", im.size, tuple(color) + (255,))
    sh.putalpha(a)
    out.paste(sh, (pad, pad + int(dy)), sh)
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def text_img(s, size, kind="display", fill=WHITE, stroke=0, stroke_fill=INK, shadow=0, glow=None, tracking=0.0, gradient=None):
    """Text as an RGBA image. `tracking` is letter spacing in em; `gradient` is (top, bottom) colours; `glow` is (colour, blur px)."""
    f = font(kind, size)
    s = str(s)
    if tracking:
        adv = [f.getlength(ch) + tracking * size for ch in s]
        bb0 = f.getbbox("Hg", stroke_width=stroke)
        tw, th, top_off = int(sum(adv) - tracking * size), bb0[3] - bb0[1], bb0[1]
        bb = (0, top_off, tw, top_off + th)
    else:
        bb = f.getbbox(s, stroke_width=stroke)
        adv = None
    pad = int(size * 0.2 + shadow * 2.5 + (glow[1] * 2.5 if glow else 0)) + 4
    w, h = int(bb[2] - bb[0] + 2 * pad), int(bb[3] - bb[1] + 2 * pad)
    ox, oy = pad - bb[0], pad - bb[1]

    def put(dr, color, dx=0.0, dy=0.0, sw=stroke, sf=None):
        if adv is None:
            dr.text((ox + dx, oy + dy), s, font=f, fill=tuple(color) + (255,) if len(color) == 3 else color, stroke_width=sw, stroke_fill=tuple(sf or stroke_fill) + (255,))
        else:
            x = ox + dx
            for ch, a in zip(s, adv):
                dr.text((x, oy + dy), ch, font=f, fill=tuple(color) + (255,) if len(color) == 3 else color, stroke_width=sw, stroke_fill=tuple(sf or stroke_fill) + (255,))
                x += a

    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        put(ImageDraw.Draw(sh), (0, 0, 0, 160), 0, shadow * 0.5)
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(shadow)))
    if glow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        put(ImageDraw.Draw(g), tuple(glow[0]), sw=int(size * 0.04), sf=tuple(glow[0]))
        g = g.filter(ImageFilter.GaussianBlur(glow[1]))
        im = Image.alpha_composite(Image.alpha_composite(im, g), g)
    if gradient:
        mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        put(ImageDraw.Draw(mask), (255, 255, 255), sw=0)
        col = vgradient(w, h, gradient[0], gradient[1])
        col.putalpha(mask.split()[3])
        if stroke:
            st = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            put(ImageDraw.Draw(st), tuple(stroke_fill), sw=stroke)
            im = Image.alpha_composite(im, st)
        im = Image.alpha_composite(im, col)
    else:
        put(ImageDraw.Draw(im), tuple(fill))
    return im


def fit_text(s, max_w, kind="display", start=400, max_h=None, **kw):
    """Text shrunk until it fits max_w (and max_h) wide and high."""
    size = start
    while size > 10:
        f = font(kind, size)
        tw = f.getlength(str(s)) + (kw.get("tracking", 0) * size * (len(str(s)) - 1))
        bb = f.getbbox("Hg")
        if tw <= max_w and (max_h is None or (bb[3] - bb[1]) <= max_h):
            break
        size = int(size * 0.92)
    return text_img(s, size, kind, **kw)


def wrap(s, max_w, kind, size):
    """Greedy word wrap into lines no wider than max_w."""
    f = font(kind, size)
    lines, cur = [], ""
    for w in str(s).split():
        t = (cur + " " + w).strip()
        if f.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def stack(images, gap=0, align="center", bg=None):
    """Stack RGBA images vertically into one."""
    w = max(i.width for i in images)
    h = sum(i.height for i in images) + gap * (len(images) - 1)
    out = Image.new("RGBA", (w, h), bg or (0, 0, 0, 0))
    y = 0
    for i in images:
        x = {"left": 0, "right": w - i.width}.get(align, (w - i.width) // 2)
        out.alpha_composite(i, (x, y))
        y += i.height + gap
    return out


def lines_fit(lines, max_w, kind, start):
    """The largest size at which every line fits max_w."""
    size = start
    while size > 10 and max(font(kind, size).getlength(str(l)) for l in lines) > max_w:
        size = int(size * 0.92)
    return size


# --------------------------------------------------------------------------------------------------------------------- icons

def icon(kind, size, color=WHITE):
    """Simple vector icons drawn here, no emoji font needed: heart check cross star play chat chevron eye lock bolt plus arrow bell dot."""
    S = int(size)
    col = tuple(color) + (255,)

    def d(dr, k):
        s = S * k
        c = s / 2
        lw = max(2, int(s * 0.12))
        if kind == "heart":
            pts = []
            for i in range(0, 360, 4):
                t = math.radians(i)
                x = 16 * math.sin(t) ** 3
                y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
                pts.append((c + x * s / 36, c * 0.95 + y * s / 36))
            dr.polygon(pts, fill=col)
        elif kind == "check":
            dr.line([(s * 0.2, s * 0.55), (s * 0.42, s * 0.76), (s * 0.8, s * 0.28)], fill=col, width=lw * 2, joint="curve")
        elif kind == "cross":
            dr.line([(s * 0.25, s * 0.25), (s * 0.75, s * 0.75)], fill=col, width=lw * 2)
            dr.line([(s * 0.75, s * 0.25), (s * 0.25, s * 0.75)], fill=col, width=lw * 2)
        elif kind == "star":
            pts = []
            for i in range(10):
                r = s * (0.48 if i % 2 == 0 else 0.2)
                a = -math.pi / 2 + i * math.pi / 5
                pts.append((c + r * math.cos(a), c + r * math.sin(a)))
            dr.polygon(pts, fill=col)
        elif kind == "play":
            dr.polygon([(s * 0.3, s * 0.2), (s * 0.3, s * 0.8), (s * 0.82, s * 0.5)], fill=col)
        elif kind == "chat":
            dr.rounded_rectangle([s * 0.08, s * 0.14, s * 0.92, s * 0.7], int(s * 0.18), fill=col)
            dr.polygon([(s * 0.25, s * 0.66), (s * 0.22, s * 0.9), (s * 0.5, s * 0.68)], fill=col)
        elif kind == "chevron":
            dr.line([(s * 0.35, s * 0.2), (s * 0.68, s * 0.5), (s * 0.35, s * 0.8)], fill=col, width=lw * 2, joint="curve")
        elif kind == "eye":
            dr.ellipse([s * 0.04, s * 0.26, s * 0.96, s * 0.74], outline=col, width=lw)
            dr.ellipse([s * 0.36, s * 0.36, s * 0.64, s * 0.64], fill=col)
        elif kind == "lock":
            dr.rounded_rectangle([s * 0.2, s * 0.44, s * 0.8, s * 0.9], int(s * 0.1), fill=col)
            dr.arc([s * 0.3, s * 0.1, s * 0.7, s * 0.7], 180, 360, fill=col, width=lw)
        elif kind == "bolt":
            dr.polygon([(s * 0.58, s * 0.05), (s * 0.2, s * 0.56), (s * 0.47, s * 0.56), (s * 0.4, s * 0.95), (s * 0.82, s * 0.4), (s * 0.54, s * 0.4)], fill=col)
        elif kind == "plus":
            dr.line([(c, s * 0.2), (c, s * 0.8)], fill=col, width=lw * 2)
            dr.line([(s * 0.2, c), (s * 0.8, c)], fill=col, width=lw * 2)
        elif kind == "arrow":
            dr.line([(s * 0.12, c), (s * 0.86, c)], fill=col, width=lw * 2)
            dr.polygon([(s * 0.9, c), (s * 0.58, s * 0.24), (s * 0.58, s * 0.76)], fill=col)
        elif kind == "bell":
            dr.pieslice([s * 0.2, s * 0.12, s * 0.8, s * 0.78], 180, 360, fill=col)
            dr.rectangle([s * 0.2, s * 0.45, s * 0.8, s * 0.74], fill=col)
            dr.ellipse([s * 0.42, s * 0.78, s * 0.58, s * 0.94], fill=col)
        else:
            dr.ellipse([s * 0.25, s * 0.25, s * 0.75, s * 0.75], fill=col)

    return _aa(S, S, d, 4)


# ----------------------------------------------------------------------------------------------------------------- frame context

class Ctx:
    """One frame being edited: pixels, matte, head position, and the bookkeeping the audit reads."""

    def __init__(self, W, H, fps, t, img, m, face, theme: Theme | None = None):
        self.W, self.H, self.fps, self.t = W, H, fps, t
        self.u = min(W, H) / 1080.0        # sizes are written for a 1080 px short side (portrait); a landscape frame keeps the same type size
        self.img, self.m = img, m
        self.th = theme or Theme()
        self.lt = 0.0
        self.cover = 0.0            # worst fraction of the head hidden by a front layer this frame
        self.boxes: list = []       # (x0, y0, x1, y1) of every front layer drawn
        self.cam = (1.0, 0.0, 0.0)  # zoom and the top-left of the crop, as applied
        self.set_face(*face)

    def set_face(self, cx, cy, fw, fh, top, shoulder):
        self.fx, self.fy = float(cx), float(cy)
        self.fw, self.fh = max(float(fw), self.W * 0.05), max(float(fh), self.W * 0.06)
        self.top = float(min(top, cy - self.fh * 0.35))
        self.chin = self.fy + self.fh / 2
        self.shoulder = float(max(shoulder, self.chin + self.fh * 0.25))
        # the head zone: crown to chin, a little wider than the face box
        self.hx, self.hy = self.fx, (self.top + self.chin) / 2
        self.hrx, self.hry = self.fw * 0.78, (self.chin - self.top) / 2 * 1.06

    def head_soft(self, x0, y0, x1, y1):
        yy, xx = np.ogrid[y0:y1, x0:x1]
        e = ((xx - self.hx) / self.hrx) ** 2 + ((yy - self.hy) / self.hry) ** 2
        return np.clip((1.25 - e) / 0.35, 0, 1).astype(np.float32)

    @property
    def head_box(self):
        return (self.hx - self.hrx, self.hy - self.hry, self.hx + self.hrx, self.hy + self.hry)


def comp(c: Ctx, layer, x, y, alpha=1.0, depth="front"):
    """Alpha-composite an RGBA layer (PIL image or float array) with its top-left at (x, y).
    depth='front' draws over everything; 'behind' hides it wherever the person is; 'guard' draws in front but never over the head; 'plain' ignores the person."""
    L = to_np(layer) if isinstance(layer, Image.Image) else layer
    h, w = L.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(c.W, x + w), min(c.H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0:
        return
    L = L[y0 - y:y1 - y, x0 - x:x1 - x]
    a = L[..., 3:4] * alpha
    if depth == "behind":
        a = a * (1 - c.m[y0:y1, x0:x1, None])
    elif depth != "plain":          # plain: no person involved (a canvas of its own)
        hb = c.head_box
        touches = x1 > hb[0] and x0 < hb[2] and y1 > hb[1] and y0 < hb[3]
        if depth == "guard" and touches:
            a = a * (1 - c.head_soft(x0, y0, x1, y1)[..., None])
        elif depth == "front":
            if touches:
                hs = c.head_soft(x0, y0, x1, y1)
                cov = float((a[..., 0] * hs).sum() / (math.pi * c.hrx * c.hry))
                c.cover = max(c.cover, min(1.0, cov))
            ys, xs = np.where(a[..., 0] > 0.3)
            if len(xs):
                c.boxes.append((x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()), y0 + int(ys.max())))
    dst = c.img[y0:y1, x0:x1]
    dst[:] = dst * (1 - a) + L[..., :3] * a


def place(c, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0, depth="front"):
    """Draw a PIL image centred on (cx, cy), scaled and rotated (degrees, counter-clockwise)."""
    if scale <= 0.01 or alpha <= 0:
        return
    if abs(scale - 1) > 0.005:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    comp(c, im, cx - im.width / 2, cy - im.height / 2, alpha, depth)


def person_over(c: Ctx, before):
    """Put the person back on top of whatever was drawn since `before` (a copy of c.img): use after drawing something that must sit behind them."""
    m = c.m[..., None]
    c.img[:] = c.img * (1 - m) + before * m


# -------------------------------------------------------------------------------------------------------------------- camera

def camera(c: Ctx, zoom, cx, cy, cap=2.0):
    """Zoom the frame (and the matte and the head) toward (cx, cy). Capped so the picture stays sharp."""
    zoom = min(zoom, cap)
    if zoom <= 1.002:
        return
    cw, ch = c.W / zoom, c.H / zoom
    x0, y0 = clamp(cx - cw / 2, 0, c.W - cw), clamp(cy - ch / 2, 0, c.H - ch)
    M = np.float32([[zoom, 0, -x0 * zoom], [0, zoom, -y0 * zoom]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
    z0, ox, oy = c.cam
    c.cam = (z0 * zoom, ox + x0 / z0, oy + y0 / z0)
    c.set_face((c.fx - x0) * zoom, (c.fy - y0) * zoom, c.fw * zoom, c.fh * zoom, (c.top - y0) * zoom, (c.shoulder - y0) * zoom)


def face_cam(c: Ctx, zoom, head_at=0.40, cap=2.0):
    """Zoom on the face, keeping it at `head_at` of the frame height."""
    z = min(zoom, cap)
    camera(c, z, c.fx, c.fy + (c.H / z) * (0.5 - head_at), cap)


def shake(c: Ctx, amp, t, speed=34.0):
    """A short handheld jolt: shift the whole frame by up to `amp` px (amp decays by the caller)."""
    if amp < 0.3:
        return
    dx, dy = amp * math.sin(t * speed * 1.3), amp * math.cos(t * speed)
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
    c.set_face(c.fx + dx, c.fy + dy, c.fw, c.fh, c.top + dy, c.shoulder + dy)


# ---------------------------------------------------------------------------------------------------------- grade and room

def luma(img):
    return (img @ np.float32([0.299, 0.587, 0.114]))[..., None]


def grade(img, kind="moody"):
    """A colour grade on a float RGB image: moody, bw, noir, warm, cool, pop, teal-orange, film-red, pastel."""
    lum = luma(img)
    if kind == "bw":
        return np.repeat(np.clip((lum - 0.5) * 1.25 + 0.5, 0, 1), 3, axis=2)
    if kind == "noir":
        return np.repeat(np.clip((lum - 0.45) * 1.7 + 0.45, 0, 1) ** 1.15, 3, axis=2)
    if kind == "warm":
        return np.clip(img * np.float32([1.08, 1.0, 0.86]) + 0.02, 0, 1)
    if kind == "cool":
        return np.clip(img * np.float32([0.9, 1.0, 1.1]), 0, 1)
    if kind == "pop":
        return np.clip((lum + (img - lum) * 1.35 - 0.5) * 1.12 + 0.5, 0, 1)
    if kind == "teal-orange":
        o = lum + (img - lum) * 1.1
        return np.clip(o + (1 - lum) * np.float32([-0.06, 0.02, 0.07]) + lum * np.float32([0.08, 0.02, -0.07]), 0, 1)
    if kind == "film-red":
        o = np.repeat(np.clip((lum - 0.45) * 1.15 + 0.42, 0, 1) ** 1.25, 3, axis=2) * np.float32([1.0, 0.46, 0.4]) + np.float32([0.05, 0.0, 0.0])
        return np.clip(o, 0, 1)
    if kind == "pastel":
        return np.clip(lum * 0.45 + img * 0.55 + 0.12, 0, 1)
    o = np.power(np.clip(lum + (img - lum) * 0.6, 0, 1), 1.3) * 0.88          # moody
    o = o + (1 - lum) * np.float32([-0.03, 0.035, 0.065]) + lum * np.float32([0.05, 0.015, -0.04])
    return np.clip((o - 0.42) * 1.12 + 0.42, 0, 1)


GRADES = ("moody", "bw", "noir", "warm", "cool", "pop", "teal-orange", "film-red", "pastel")
_vig: dict = {}


def vignette(c: Ctx, strength=0.35):
    k = (c.W, c.H)
    if k not in _vig:
        yy, xx = np.ogrid[0:c.H, 0:c.W]
        _vig[k] = np.clip(((xx - c.W / 2) / (c.W * 0.75)) ** 2 + ((yy - c.H / 2) / (c.H * 0.7)) ** 2, 0, 1).astype(np.float32)
    c.img *= (1 - strength * _vig[k])[..., None]


def grain(c: Ctx, amount=0.04, frame=0):
    rng = np.random.default_rng(1000 + frame)
    n = rng.standard_normal((c.H // 2, c.W // 2)).astype(np.float32)
    n = cv2.resize(n, (c.W, c.H), interpolation=cv2.INTER_LINEAR)
    c.img += n[..., None] * amount
    np.clip(c.img, 0, 1, out=c.img)


_grid: dict = {}


def mesh(c: Ctx):
    if (c.W, c.H) not in _grid:
        yy, xx = np.mgrid[0:c.H, 0:c.W].astype(np.float32)
        _grid[(c.W, c.H)] = (xx, yy)
    return _grid[(c.W, c.H)]


def paint_room(c: Ctx, bg, k=1.0):
    """Replace the room behind the person with `bg` (an (H, W, 3) float array or an (r, g, b) colour), fading in with k."""
    if isinstance(bg, tuple):
        bg = np.empty((c.H, c.W, 3), np.float32)
        bg[:] = np.float32(bg[:3]) / 255
    m = c.m[..., None]
    room = c.img * m + bg * (1 - m)
    c.img[:] = c.img * (1 - k) + room * k


def blur_room(c: Ctx, sigma, k=1.0):
    """Defocus the room behind the person; the person stays sharp. sigma in px of a 1080 wide frame."""
    s = max(0.1, sigma * c.u)
    blurred = cv2.GaussianBlur(c.img, (0, 0), s)
    m = c.m[..., None]
    room = c.img * m + blurred * (1 - m)
    c.img[:] = c.img * (1 - k) + room * k


def room_pattern(c: Ctx, kind="grid", ink=(30, 40, 120), paper=(246, 243, 236), step=56):
    """A flat backdrop to paint behind the person: grid (graph paper), dots, lines, plain."""
    key = ("pat", c.W, c.H, kind, tuple(ink), tuple(paper), step)
    if key in _grid:
        return _grid[key]
    xx, yy = mesh(c)
    st = step * c.u
    base = np.empty((c.H, c.W, 3), np.float32)
    base[:] = np.float32(paper) / 255
    if kind == "grid":
        line = np.minimum(np.minimum(xx % st, st - xx % st), np.minimum(yy % st, st - yy % st))
        a = np.clip(1.4 - line / max(1.0, c.u * 0.9), 0, 1) * 0.30
    elif kind == "dots":
        a = np.clip(1.4 - np.hypot(xx % st - st / 2, yy % st - st / 2) / (c.u * 3.0), 0, 1) * 0.35
    elif kind == "lines":
        a = np.clip(1.4 - np.abs(yy % st - st / 2) / (c.u * 1.2), 0, 1) * 0.25
    else:
        a = np.zeros((c.H, c.W), np.float32)
    out = base * (1 - a[..., None]) + np.float32(ink) / 255 * a[..., None]
    _grid[key] = out
    return out


def dim_room(c: Ctx, k, pool=0.55, power=1.6, floor=0.18):
    """Kill the lights: darken the room with a soft pool of light around the head; the person keeps their light."""
    xx, yy = mesh(c)
    d = ((xx - c.hx) / (c.W * 0.5)) ** 2 + ((yy - (c.hy + c.H * 0.2)) / (c.H * 0.46)) ** 2
    lit = np.clip(1 - d, 0, 1) ** power
    bright = 1 - k * (1 - (floor + pool * lit))
    f = bright * (1 - c.m) + c.m * (1 + 0.04 * k)
    c.img *= f[..., None]


# ------------------------------------------------------------------------------------------------------------------------ glass

def glass(c: Ctx, box, r=None, depth="front", blur=None, tint=WHITE, tint_amt=0.0, dark=0.0, refract=1.0, fringe=1.0, spec=1.0, alpha=1.0):
    """A see-through glass panel at box=(x0, y0, x1, y1), drawn into the frame from whatever sits behind it: a light blur, the room bent at the
    rim like a lens, a red/blue fringe, a specular edge lit from the top-left. depth='behind' keeps the person in front of the glass."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8 or alpha <= 0:
        return
    u = c.u
    r = max(2.0, float(r if r is not None else 56 * u))
    r = min(r, w / 2, h / 2)
    M = int(110 * u * refract) + 6
    X0, Y0, X1, Y1 = max(0, x0 - M), max(0, y0 - M), min(c.W, x1 + M), min(c.H, y1 + M)
    tex = cv2.GaussianBlur(np.ascontiguousarray(c.img[Y0:Y1, X0:X1]), (0, 0), blur or max(2.0, 5.5 * u))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    q = np.stack([np.abs(xx - w / 2) - (w / 2 - r), np.abs(yy - h / 2) - (h / 2 - r)], -1)
    sdf = np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.maximum(q[..., 0], q[..., 1]), 0) - r      # < 0 inside
    d = np.maximum(-sdf, 0) / u                                                                                  # depth under the rim, in 1080-px units
    gy, gx = np.gradient(sdf)
    gl = np.sqrt(gx * gx + gy * gy) + 1e-4
    nx, ny = gx / gl, gy / gl                                                                                    # outward normal
    k = (52 * np.exp(-d / 10) + 26 * np.exp(-d / 52) + 8 * np.exp(-d / 200)) * u * refract
    out = np.zeros((h, w, 3), np.float32)
    for ch, fr in enumerate((1.0 + 0.09 * fringe, 1.0, 1.0 - 0.09 * fringe)):
        mx = (xx + (x0 - X0) + nx * k * fr).astype(np.float32)
        my = (yy + (y0 - Y0) + ny * k * fr).astype(np.float32)
        out[..., ch] = cv2.remap(tex[..., ch], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = out * (1 - 0.25 * dark) * 0.9 + np.float32(tint) / 255 * tint_amt * 0.25 + 0.05 * (1.0 - 0.3 * (yy / h))[..., None] - 0.035
    light = np.exp(-d / 4.5) * np.clip(0.5 * (-nx * 0.6 - ny * 0.8) + 0.42, 0, 1)            # rim facing the top-left
    back = np.exp(-d / 6.0) * np.clip(0.5 * (nx * 0.6 + ny * 0.8) - 0.05, 0, 1) * 0.35        # a faint return light bottom-right
    out = np.clip(out + ((light * 0.9 + back) * spec + np.exp(-d / 28) * 0.08)[..., None], 0, 1)
    a = np.clip(0.5 - sdf, 0, 1)[..., None] * alpha
    gx0, gy0, gx1, gy1 = max(0, x0), max(0, y0), min(c.W, x1), min(c.H, y1)
    sl = (slice(gy0 - y0, gy1 - y0), slice(gx0 - x0, gx1 - x0))
    dst = c.img[gy0:gy1, gx0:gx1]
    new = dst * (1 - a[sl]) + out[sl] * a[sl]
    if depth == "behind":
        mm = c.m[gy0:gy1, gx0:gx1, None]
        new = new * (1 - mm) + dst * mm
    elif depth in ("front", "guard"):
        hb = c.head_box
        if gx1 > hb[0] and gx0 < hb[2] and gy1 > hb[1] and gy0 < hb[3]:
            hs = c.head_soft(gx0, gy0, gx1, gy1)
            if depth == "guard":
                new = new * (1 - hs[..., None]) + dst * hs[..., None]
            else:
                c.cover = max(c.cover, min(1.0, float((a[sl][..., 0] * hs).sum() / (math.pi * c.hrx * c.hry))))
        c.boxes.append((gx0, gy0, gx1, gy1))
    dst[:] = new


# ---------------------------------------------------------------------------------------------------------------- hand-drawn

def wobble(pts, amp=2.0, seed=3):
    """Make a polyline look drawn by hand: a smooth random drift along its length."""
    rng = random.Random(seed)
    out, dx, dy = [], 0.0, 0.0
    for p in pts:
        dx = dx * 0.8 + rng.uniform(-amp, amp) * 0.4
        dy = dy * 0.8 + rng.uniform(-amp, amp) * 0.4
        out.append((p[0] + dx, p[1] + dy))
    return out


def path_part(pts, frac):
    """The first `frac` (0..1) of a polyline, by length: how a stroke draws itself on."""
    frac = clamp(frac)
    if frac <= 0 or len(pts) < 2:
        return pts[:1]
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    goal, out, run = sum(seg) * frac, [pts[0]], 0.0
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if run + s >= goal:
            t = (goal - run) / max(1e-6, s)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            return out
        out.append(b)
        run += s
    return out


def stroke(dr, pts, color, width, k=1):
    """A round-capped, round-joined polyline on a PIL ImageDraw (scaled by k for supersampled layers)."""
    pts = [(x * k, y * k) for x, y in pts]
    if len(pts) == 1:
        pts = pts * 2
    dr.line(pts, fill=tuple(color) + (255,), width=int(width * k), joint="curve")
    r = width * k / 2
    for x, y in (pts[0], pts[-1]):
        dr.ellipse([x - r, y - r, x + r, y + r], fill=tuple(color) + (255,))


def arrow_curve(x0, y0, x1, y1, bend=0.25, n=40):
    """Points along a curved arrow shaft from (x0, y0) to (x1, y1)."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bend, my + dx * bend
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1) for t in (i / n for i in range(n + 1))]


def arrow_head(dr, pts, color, width, size, k=1):
    (x0, y0), (x1, y1) = pts[-4] if len(pts) > 4 else pts[0], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    for s in (-0.5, 0.5):
        stroke(dr, [(x1, y1), (x1 - size * math.cos(a + s), y1 - size * math.sin(a + s))], color, width, k)


# -------------------------------------------------------------------------------------------------------------------- cards

def card_image(im, w, radius=0.07, shadow=True):
    """A 9:16 rounded card from any image, cover-cropped, with a hairline and a soft shadow."""
    h = int(w * 16 / 9)
    src = im.convert("RGB")
    sw, sh = src.size
    s = max(w / sw, h / sh)
    src = src.resize((max(w, int(sw * s)), max(h, int(sh * s))), Image.LANCZOS)
    l, t = (src.width - w) // 2, (src.height - h) // 2
    src = src.crop((l, t, l + w, t + h)).convert("RGBA")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(w * radius), fill=255)
    src.putalpha(m)
    ImageDraw.Draw(src).rounded_rectangle([0, 0, w - 1, h - 1], int(w * radius), outline=(0, 0, 0, 70), width=2)
    return shadowed(src, blur=max(6, w // 16), dy=w // 22, alpha=150) if shadow else src


def vary(im, i):
    """Give each card its own look, so a pile of frames reads as different shots."""
    kind = ("pop", "bw", "warm", "cool", "moody")[i % 5]
    a = np.asarray(im.convert("RGB"), np.float32) / 255
    return Image.fromarray((grade(a, kind) * 255).astype(np.uint8))


def cached(e, key, fn):
    if key not in e.state:
        e.state[key] = fn()
    return e.state[key]
