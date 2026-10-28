"""fx_looks.py - person-aware effects, part one: type behind the head, face-anchored graphics, camera moves, light and grade, hand-drawn marks.

Each function draws one frame of one effect: `c` is the frame (fx_core.Ctx) and `e` the effect instance. Time is `c.lt` (seconds into the
effect) and `e.d` (its length); nothing is stored between frames except through `cached`, so any frame can be drawn on its own.
"""
from __future__ import annotations

import math
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fx_core import (arrow_curve, arrow_head, blur_room, camera, card_image, cached, clamp, comp, count_text, dim_room, ease_back, ease_in, ease_inout, ease_out,
                     ease_spring, face_cam, fit_text, font, grade, grain, icon, keyframes, lerp, luma, mesh, paint_room, path_part, person_over, place, ramp,
                     rgb, room_pattern, rrect, shadowed, shake, stroke, text_img, typed, vary, vignette, vgradient, wobble)
from fx_registry import col, effect, lst, num, opt, times, txt  # noqa: F401


def _x(c):
    """Where a graphic that follows the head horizontally sits: mostly centred, partly on the face."""
    return c.W / 2 * 0.6 + c.fx * 0.4


def _above(c, h, gap=0.0):
    """Centre y for an element of height h that sits above the head, or None when there is no room."""
    cy = c.top - gap - h / 2
    return cy if cy - h / 2 >= c.H * 0.02 else None


def _deck(c, e, w, varied=True):
    """The effect's cards as 9:16 images of width w: the user's images, or varied frames of the video itself."""
    def build():
        src = e.cards or [Image.new("RGB", (270, 480), (60, 60, 80))]
        own = bool(e.o.get("images"))
        return [card_image(im if own or not varied else vary(im, i), w) for i, im in enumerate(src)]
    return cached(e, f"deck{w}", build)


def _sparkle(size, color=(255, 244, 222)):
    s = int(size)
    big = Image.new("RGBA", (s * 4, s * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    c, r, q = s * 2, s * 2, s * 0.3
    d.polygon([(c, c - r), (c + q, c - q), (c + r, c), (c + q, c + q), (c, c + r), (c - q, c + q), (c - r, c), (c - q, c - q)], fill=tuple(color) + (255,))
    return big.resize((s, s), Image.LANCZOS)


# ============================================================================================================== type and depth

@effect("word-behind", "A giant word drops in behind the speaker's head and is hidden wherever the head overlaps it.",
        {"text": "the word", "color": "hex colour (default the theme's paper)", "font": "display | bold | serif | didone | hand", "size": "fraction of frame width (0.94)",
         "lift": "how much of the word the head hides, 0..1 (0.3)", "outline": "outline px", "x": "horizontal offset, fraction of width"},
        family="type", depth="behind", matte=True, seconds=(1.5, 4.0), intents=("myth", "numbers", "news"))
def word_behind(c, e):
    kind = txt(e, "font", "display")
    word = txt(e, "text", "NOW")
    im = cached(e, "im", lambda: fit_text(word.upper() if kind == "display" else word, c.W * num(e, "size", 0.94), kind, fill=col(e, "color", c.th.paper),
                                          stroke=int(num(e, "outline", 0) * c.u), shadow=int(10 * c.u)))
    k = ease_back(c.lt / 0.42)
    y_end = max(c.top - im.height * (0.5 - num(e, "lift", 0.3)), im.height * 0.5 + c.H * 0.02)
    y = -im.height + (y_end + im.height) * k
    place(c, im, _x(c) + num(e, "x", 0) * c.W, y, alpha=clamp((e.d - c.lt) / 0.2), depth="behind")


@effect("type-stack", "Lines of huge type slam in one after another behind the head, alternating colour.",
        {"lines": "lines separated by |", "text": "same as lines", "color": "first colour", "accent": "second colour", "font": "display | bold | didone",
         "gap": "seconds between lines (0.3)"}, family="type", depth="behind", matte=True, seconds=(2.0, 5.0), intents=("numbers", "myth", "payoff"))
def type_stack(c, e):
    lines = (lst(e, "lines") or lst(e, "text", ["THIS", "IS", "IT"]))[:5]
    kind = txt(e, "font", "display")
    cols = [col(e, "color", c.th.paper), col(e, "accent", c.th.accent)]
    maxw = c.W * 0.9
    ims = cached(e, "ims", lambda: [fit_text(l.upper(), maxw, kind, 520, fill=cols[i % 2], stroke=int(4 * c.u), stroke_fill=(14, 14, 18), shadow=int(8 * c.u)) for i, l in enumerate(lines)])
    gap = num(e, "gap", 0.3)
    total = sum(i.height * 0.78 for i in ims)
    y0 = clamp(c.hy - total * 0.55, c.H * 0.04, c.H * 0.9 - total)
    out = clamp((e.d - c.lt) / 0.2)
    y = y0
    for i, im in enumerate(ims):
        t0 = i * gap
        h = im.height * 0.78
        if c.lt >= t0:
            q = clamp((c.lt - t0) / 0.2)
            place(c, im, c.W / 2 + (-1) ** i * c.W * 0.015, y + h / 2, 1.0 + 0.4 * (1 - ease_out(q)), (-1) ** i * 2.0 * (1 - ease_out(q)), q * out, "behind")
        y += h
    landed = [i * gap for i in range(len(lines)) if i * gap <= c.lt]
    if landed:
        shake(c, 6 * c.u * max(0.0, 1 - (c.lt - landed[-1]) / 0.18), c.t)


@effect("neon-sign", "The lights drop and a glowing neon sign types itself out behind the head.",
        {"lines": "lines separated by |", "text": "same as lines", "color": "neon colour (hot pink)", "font": "bold | script | mono", "push": "slow camera push (1.0)"},
        family="light", depth="behind", matte=True, camera=True, seconds=(2.5, 5.0), intents=("hook", "payoff"), aliases=("led-sign",))
def neon_sign(c, e):
    push = num(e, "push", 1.05)
    if push > 1:
        face_cam(c, 1 + (push - 1) * ease_inout(c.lt / e.d))
    k = ramp(c, e, 0.35, 0.3)
    dim_room(c, k, pool=0.3, floor=0.1)
    lines = (lst(e, "lines") or lst(e, "text", ["ON AIR"]))[:3]
    kind = txt(e, "font", "bold")
    base = col(e, "color", (255, 70, 150))
    maxw = c.W * 0.86
    size = int(min(fit_text(max(lines, key=len), maxw, kind, 260).height, c.H * 0.1))
    ims = [text_img(l, size, kind, fill=tuple(min(255, int(v * 0.35 + 190)) for v in base), glow=(base, 22 * c.u), tracking=0.04) for l in lines]
    fl = 0.9 + 0.1 * math.sin(c.lt * 38) if c.lt < 0.8 else 1.0
    y = clamp(c.top - sum(i.height for i in ims) * 0.55, c.H * 0.05, c.H * 0.7)
    for i, (l, im) in enumerate(zip(lines, ims)):
        p = clamp((c.lt - 0.4 - i * 0.55) / max(0.3, 0.12 * len(l)))
        if p > 0:
            shown = text_img(typed(l, p), size, kind, fill=tuple(min(255, int(v * 0.35 + 190)) for v in base), glow=(base, 22 * c.u), tracking=0.04) if p < 1 else im
            place(c, shown, c.W / 2, y + im.height / 2, alpha=k * fl, depth="behind")
        y += im.height * 0.95


@effect("spotlight", "Kill the lights and keep the speaker lit; a word can glow behind the head. look=sparkle adds golden rays and twinkling light.",
        {"text": "a glowing word behind the head", "color": "hex colour", "push": "camera push (1.1)", "font": "serif | display | bold", "look": "sparkle for rays and sparkles"},
        family="light", depth="behind", matte=True, camera=True, seconds=(2.0, 5.0), intents=("hook", "payoff", "myth"), looks={"sparkle": "golden rays burst from behind the head, a gold word with a shine, twinkling sparkles"})
def spotlight(c, e):
    face_cam(c, 1 + (num(e, "push", 1.1) - 1) * ease_inout(c.lt / e.d))
    k = ramp(c, e, 0.3, 0.25)
    sparkle = txt(e, "look") == "sparkle"
    dim_room(c, k, pool=0.5 if not sparkle else 0.3, floor=0.2 if not sparkle else 0.12)
    word = txt(e, "text")
    if sparkle:
        gold = np.float32(col(e, "color", (255, 196, 70))) / 255
        sw, sh = max(8, c.W // 3), max(8, c.H // 3)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        dx, dy = xx - c.hx / 3, yy - (c.hy - c.fh * 0.2) / 3
        dist, ang = np.hypot(dx, dy), np.arctan2(dy, dx)
        rays = (0.5 + 0.5 * np.sin(ang * 13 + c.lt * 0.7)) ** 3 * np.exp(-dist / (sw * 0.75)) * (0.55 + 0.25 * np.sin(ang * 5 - c.lt * 1.1))
        glow = np.exp(-dist / (sw * 0.2)) * 0.55
        field = cv2.resize((rays * 0.9 + glow).astype(np.float32), (c.W, c.H), interpolation=cv2.INTER_LINEAR)[..., None]
        c.img += field * gold * k * (1 - c.m[..., None]) * 0.9
        halo = cv2.GaussianBlur(c.m, (0, 0), 26 * c.u)[..., None]
        c.img += halo * gold * 0.28 * k * (1 - c.m[..., None])
        np.clip(c.img, 0, 1, out=c.img)
        if word:
            im = cached(e, "w", lambda: fit_text(word, c.W * 0.86, txt(e, "font", "bold"), 360, gradient=((255, 236, 170), (214, 150, 40)), glow=((255, 190, 60), 18 * c.u), shadow=int(6 * c.u)))
            place(c, im, c.W / 2, clamp(c.top - im.height * 0.28, im.height * 0.5, c.H), alpha=k, depth="behind")
            sweep = (c.lt * 0.6) % 1.4 - 0.2
            if 0 < sweep < 1:
                band = np.exp(-((np.arange(im.width) / im.width - sweep) / 0.05) ** 2).astype(np.float32)
                a = np.asarray(im.split()[3], np.float32) / 255 * band[None, :]
                lay = np.zeros((im.height, im.width, 4), np.float32)
                lay[..., :3], lay[..., 3] = 1.0, a * 0.8
                comp(c, lay, c.W / 2 - im.width / 2, clamp(c.top - im.height * 0.28, im.height * 0.5, c.H) - im.height / 2, k, "behind")
        rng = random.Random(5)
        for i in range(14):
            sx, sy = rng.uniform(0.08, 0.92) * c.W, rng.uniform(0.05, 0.55) * c.H
            tw = 0.5 + 0.5 * math.sin(c.lt * rng.uniform(2.5, 5) + i * 1.7)
            if tw > 0.15:
                place(c, _sparkle(rng.uniform(26, 60) * c.u * (0.5 + 0.5 * tw)), sx, sy, alpha=tw * k, depth="behind")
    elif word:
        colr = col(e, "color", (255, 183, 165))
        im = cached(e, "w", lambda: fit_text(word, c.W * 0.9, txt(e, "font", "serif"), 420, fill=colr, glow=(colr, 26 * c.u)))
        place(c, im, c.W / 2, c.top - im.height * 0.2, alpha=k, depth="behind")


@effect("grade", "A colour grade over the window, on everything, only the room, or only the person.",
        {"kind": "moody | bw | noir | warm | cool | pop | teal-orange | film-red | pastel", "only": "all | room | person", "strength": "0..1 (1)", "vignette": "0..0.6", "grain": "0..0.08"},
        family="light", depth="none", cover_ok=True, seconds=(2.0, 8.0), intents=("hook", "payoff"))
def grade_fx(c, e):
    k = ramp(c, e, 0.35, 0.35) * num(e, "strength", 1.0)
    g = grade(c.img, txt(e, "kind", "moody"))
    only = txt(e, "only", "all")
    sel = 1.0 if only == "all" else ((1 - c.m) if only == "room" else c.m)[..., None]
    c.img[:] = c.img * (1 - k * sel) + g * k * sel
    if num(e, "vignette", 0.25) > 0:
        vignette(c, num(e, "vignette", 0.25) * k)
    if num(e, "grain", 0.0) > 0:
        grain(c, num(e, "grain", 0.0) * k, int(c.t * c.fps))


@effect("before-after", "A slider sweeps across the frame: the original on one side, a grade on the other.",
        {"kind": "the 'after' grade (pop)", "only": "all | room | person"}, family="light", depth="guard", cover_ok=True, seconds=(2.0, 4.0), intents=("howto",))
def before_after(c, e):
    p = ease_inout(clamp(c.lt / (e.d * 0.8)))
    x = int(p * c.W)
    g = grade(c.img, txt(e, "kind", "pop"))
    only = txt(e, "only", "all")
    sel = 1.0 if only == "all" else ((1 - c.m) if only == "room" else c.m)[..., None]
    after = c.img * (1 - sel) + g * sel
    if x > 0:
        c.img[:, :x] = after[:, :x]
    lw = max(3, int(5 * c.u))
    line = np.zeros((c.H, lw * 2, 4), np.float32)
    line[..., :3], line[..., 3] = 1.0, 0.95
    comp(c, line, x - lw, 0, 1.0, "front")
    knob = cached(e, "knob", lambda: shadowed(rrect(int(96 * c.u), int(96 * c.u), 48 * c.u, (255, 255, 255, 255)), int(8 * c.u), int(4 * c.u), 140))
    comp(c, knob, x - knob.width / 2, c.H * 0.62 - knob.height / 2, 1.0, "front")
    ar = icon("chevron", int(44 * c.u), (30, 30, 34))
    place(c, ar, x + 12 * c.u, c.H * 0.62)
    place(c, ar.transpose(Image.FLIP_LEFT_RIGHT), x - 12 * c.u, c.H * 0.62)
    a = clamp(c.lt / 0.2) * clamp((e.d - c.lt) / 0.2)
    for label, side in (("BEFORE", "right"), ("AFTER", "left")):
        t = cached(e, label, lambda L=label: shadowed(text_img(L, 30 * c.u, "mono", (255, 255, 255), tracking=0.15), int(6 * c.u), 2, 150))
        cx = (x + c.W) / 2 if side == "right" else x / 2
        if 80 * c.u < cx < c.W - 80 * c.u and (c.W - x if side == "right" else x) > 220 * c.u:
            place(c, t, cx, c.H * 0.88, alpha=a, depth="guard")


# ================================================================================================================ camera moves

@effect("punch-in", "A fast punch-in on a word, held, then eased back out.", {"zoom": "1.45 (max 2)", "speed": "seconds to arrive (0.18)", "head_at": "where the face sits, fraction of height (0.42)"},
        family="camera", depth="none", cover_ok=True, camera=True, seconds=(0.8, 2.5), intents=("hook", "myth", "payoff"), aliases=("lean-in",))
def punch_in(c, e):
    z = num(e, "zoom", 1.45)
    arrive = ease_back(c.lt / num(e, "speed", 0.18), 1.2)
    leave = ease_inout((e.d - c.lt) / 0.25)
    face_cam(c, 1 + (z - 1) * clamp(arrive, 0, 1.08) * leave, num(e, "head_at", 0.42))


@effect("slow-push", "A slow cinematic push toward the face while the room melts out of focus.",
        {"zoom": "final zoom (1.6)", "blur": "room blur px (16)", "vignette": "0..0.5 (0.25)"}, family="camera", depth="none", matte=True, cover_ok=True, camera=True,
        seconds=(3.0, 8.0), intents=("hook", "payoff", "story"), aliases=("push",))
def slow_push(c, e):
    p = ease_inout(clamp(c.lt / e.d))
    face_cam(c, 1 + (num(e, "zoom", 1.6) - 1) * p, lerp(0.5, 0.42, p))
    blur_room(c, num(e, "blur", 16) * p)
    vignette(c, num(e, "vignette", 0.25) * p)


@effect("lock-on", "Corner brackets snap onto the face, a tag appears below, and the camera follows the speaker.",
        {"zoom": "1.35", "text": "tag text (LOCKED ON)"}, family="camera", depth="guard", camera=True, seconds=(1.5, 4.0), intents=("hook", "news"))
def lock_on(c, e):
    face_cam(c, 1 + (num(e, "zoom", 1.35) - 1) * ease_out(c.lt / 0.6))
    snap = ease_out(c.lt / 0.22)
    s = c.fw * 0.85 * (1 + 0.6 * (1 - snap))
    al = clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2)
    size = int(2 * s + 40)
    im = Image.new("RGBA", (size, int(size * 1.3)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 20, 20, size - 20, im.height - 20
    L, wd = int(s * 0.32), max(4, int(c.W / 200))
    for px, py, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(px, py + dy * L), (px, py), (px + dx * L, py)], fill=(255, 255, 255, 255), width=wd, joint="curve")
    place(c, shadowed(im, 6, 2, 120), c.fx, c.hy, alpha=al, depth="front")
    tag = text_img(txt(e, "text", "LOCKED ON").upper(), c.W * 0.022, "mono", (22, 22, 24))
    pill = rrect(tag.width + 22, tag.height + 6, (tag.height + 6) / 2, (255, 255, 255, 235))
    pill.alpha_composite(tag, (11, 3))
    place(c, pill, c.fx, c.chin + s * 0.25 + pill.height, alpha=clamp((c.lt - 0.15) / 0.15) * al, depth="guard")


# =================================================================================================================== face-anchored

@effect("orbit", "Cards circle the head: in front at the bottom, behind the head at the top.",
        {"images": "folder of images or clips", "count": "cards (6)", "speed": "radians per second (1.9)", "size": "card width, fraction of frame (0.2)"},
        family="cards", depth="mixed", matte=True, images=True, seconds=(2.0, 5.0), intents=("numbers", "case"))
def orbit(c, e):
    K = int(num(e, "count", 6))
    deck = _deck(c, e, int(c.W * num(e, "size", 0.2)))
    intro, out = ease_out(c.lt / 0.4), clamp((e.d - c.lt) / 0.25)
    rx, ry = c.W * 0.38 * intro, max(c.fw * 1.5, c.H * 0.1)
    oy = c.fy + c.fw * 0.9
    items = []
    for i in range(K):
        th = i * 2 * math.pi / K + c.lt * num(e, "speed", 1.9)
        items.append((math.sin(th), th, i))
    for depth, th, i in sorted(items):
        place(c, deck[i % len(deck)], c.fx + rx * math.cos(th), oy + ry * math.sin(th), (0.78 + 0.24 * (depth + 1) / 2) * (0.5 + 0.5 * intro), -6 * math.cos(th),
              out * clamp(c.lt / 0.15), "behind" if depth < 0 else "guard")


@effect("carousel", "Cards spin around the speaker in a 3D ring, then slow to a stop with one card facing the camera.",
        {"images": "folder of images or clips", "count": "cards (7)", "size": "card width, fraction of frame (0.24)", "turns": "revolutions (1.5)"},
        family="cards", depth="mixed", matte=True, images=True, seconds=(3.0, 6.0), intents=("numbers", "case"))
def carousel(c, e):
    K = int(num(e, "count", 7))
    deck = _deck(c, e, int(c.W * num(e, "size", 0.24)))
    intro, out = ease_out(c.lt / 0.45), clamp((e.d - c.lt) / 0.25)
    rot = ease_out(clamp(c.lt / (e.d * 0.82))) * num(e, "turns", 1.5) * 2 * math.pi
    R, cy = c.W * 0.4 * intro, c.hy + c.fh * 0.7
    items = []
    for i in range(K):
        th = i * 2 * math.pi / K + rot + math.pi / 2
        items.append((math.sin(th), th, i))
    for z, th, i in sorted(items):
        persp = 0.62 + 0.38 * (z + 1) / 2
        place(c, deck[i % len(deck)], c.fx + R * math.cos(th), cy + c.H * 0.06 * z, persp * (0.5 + 0.5 * intro), 0, out * clamp(c.lt / 0.2) * (0.7 + 0.3 * (z + 1) / 2),
              "behind" if z < -0.05 else "guard")


@effect("reel-pile", "Cards pile up behind the head, one every quarter second.", {"images": "folder of images or clips", "size": "card width, fraction of frame (0.34)"},
        family="cards", depth="behind", matte=True, images=True, seconds=(2.0, 5.0), intents=("numbers", "case"), aliases=("noise",))
def reel_pile(c, e):
    cw = int(c.W * num(e, "size", 0.34))
    rnd = random.Random(7)
    n = min(16, max(4, int(e.d / 0.22)))
    pos = cached(e, "pos", lambda: [(rnd.uniform(0.14, 0.86), rnd.uniform(0.12, 0.52), rnd.uniform(-7, 7)) for _ in range(n)])
    deck = _deck(c, e, cw)
    out = clamp((e.d - c.lt) / 0.2)
    for i, (x, y, r) in enumerate(pos):
        t0 = i * 0.22
        if c.lt < t0:
            break
        place(c, deck[i % len(deck)], x * c.W, y * c.H, 0.6 + 0.4 * ease_back((c.lt - t0) / 0.25), r, clamp((c.lt - t0) / 0.08) * out, "behind")


@effect("tile-wall", "A wall of cards fills the frame behind the speaker while a counter ticks up.",
        {"images": "folder of images or clips", "count": "the number to count to (1.2M)", "label": "caption under the number", "cols": "3"}, family="cards", depth="behind",
        matte=True, images=True, seconds=(3.0, 6.0), intents=("numbers", "case"), aliases=("profile-wall",))
def tile_wall(c, e):
    cols = int(num(e, "cols", 3))
    cw = int(c.W / cols * 0.94)
    deck = _deck(c, e, cw)
    ch = deck[0].height
    rows = int(math.ceil(c.H / (ch * 0.9))) + 1
    out = clamp((e.d - c.lt) / 0.2)
    i = 0
    for r in range(rows):
        for q in range(cols):
            t0 = i * 0.07
            i += 1
            if c.lt < t0:
                continue
            place(c, deck[(r * cols + q) % len(deck)], (q + 0.5) * c.W / cols, r * ch * 0.9 + ch * 0.45 - c.H * 0.03, 0.85 + 0.15 * ease_back((c.lt - t0) / 0.25), 0,
                  clamp((c.lt - t0) / 0.1) * out * 0.95, "behind")
    big = txt(e, "count", "1.2M")
    t = cached(e, "lbl", lambda: text_img(txt(e, "label", "views").upper(), 34 * c.u, "mono", c.th.paper, tracking=0.2, shadow=int(6 * c.u)))
    n = text_img(count_text(big, clamp(c.lt / (e.d * 0.7))), 190 * c.u, "display", c.th.paper, stroke=int(5 * c.u), stroke_fill=(14, 14, 18), shadow=int(10 * c.u))
    y = c.chin + c.fh * 0.9 if c.chin + c.fh * 2 < c.H * 0.85 else c.H * 0.84
    place(c, n, c.W / 2, y, alpha=clamp(c.lt / 0.25) * out, depth="guard")
    place(c, t, c.W / 2, y + n.height * 0.5, alpha=clamp(c.lt / 0.25) * out, depth="guard")


@effect("headline-wall", "Headlines pile up behind the head, then a total pops in front.",
        {"text": "headline::meta items separated by |", "total": "the number that pops in (672K)", "label": "its caption"}, family="cards", depth="mixed", matte=True,
        seconds=(3.0, 6.0), intents=("numbers", "news", "case"))
def headline_wall(c, e):
    items = [s.split("::") + [""] for s in lst(e, "text", ["First headline::1.2M views", "Second headline::340K views", "Third headline::88K views"])][:8]
    w = int(c.W * 0.62)

    def build(i, h, m):
        f = fit_text(h, w - 50 * c.u, "bold", int(46 * c.u), fill=(22, 22, 24))
        im = rrect(w, int(f.height + 60 * c.u), 26 * c.u, (250, 248, 242, 245))
        im.alpha_composite(f, (int(24 * c.u), int(12 * c.u)))
        mt = text_img(m[0] if isinstance(m, list) else m, 28 * c.u, "mono", (120, 110, 100))
        im.alpha_composite(mt, (int(26 * c.u), int(f.height + 14 * c.u)))
        return shadowed(im, int(10 * c.u), int(6 * c.u), 110)

    cards = cached(e, "cards", lambda: [build(i, it[0], it[1:]) for i, it in enumerate(items)])
    rnd = random.Random(11)
    pos = cached(e, "pos", lambda: [(rnd.uniform(0.3, 0.7), 0.1 + 0.46 * i / max(1, len(items) - 1) + rnd.uniform(-0.02, 0.02), rnd.uniform(-5, 5)) for i in range(len(items))])
    out = clamp((e.d - c.lt) / 0.2)
    step = min(0.4, (e.d * 0.55) / max(1, len(items)))
    for i, (x, y, r) in enumerate(pos):
        t0 = i * step
        if c.lt < t0:
            break
        q = ease_back((c.lt - t0) / 0.28)
        place(c, cards[i], x * c.W, lerp(c.H * -0.1, y * c.H, clamp(q)), 1.0, r, clamp((c.lt - t0) / 0.08) * out, "behind")
    t_tot = e.d * 0.6
    if c.lt > t_tot and txt(e, "total"):
        n = text_img(txt(e, "total"), 200 * c.u, "display", c.th.accent, stroke=int(6 * c.u), stroke_fill=(14, 14, 18), shadow=int(12 * c.u))
        lb = text_img(txt(e, "label", "TOTAL").upper(), 34 * c.u, "mono", c.th.paper, tracking=0.2, shadow=int(6 * c.u))
        k = ease_back((c.lt - t_tot) / 0.3)
        y = c.chin + c.fh * 0.9 if c.chin + c.fh * 2 < c.H * 0.86 else c.H * 0.84
        place(c, n, c.W / 2, y, 0.7 + 0.3 * k, 0, clamp((c.lt - t_tot) / 0.1) * out, "guard")
        place(c, lb, c.W / 2, y + n.height * 0.5, alpha=clamp((c.lt - t_tot) / 0.2) * out, depth="guard")


@effect("key-rain", "Keycaps rain down behind the speaker.", {"text": "key labels separated by | (K|Enter|Esc|/)", "count": "keys (22)", "color": "keycap colour"},
        family="cards", depth="behind", matte=True, seconds=(2.0, 4.0), intents=("howto",))
def key_rain(c, e):
    labels = lst(e, "text", ["K", "Enter", "Esc", "Tab", "/", "Shift", "Cmd", "Z"])
    n = int(num(e, "count", 30))
    base = col(e, "color", (238, 238, 242))
    rnd = random.Random(3)
    spec = cached(e, "spec", lambda: [(rnd.uniform(0.05, 0.95), rnd.uniform(0.0, 1.0), rnd.uniform(0.7, 1.3), rnd.uniform(-14, 14), labels[i % len(labels)]) for i in range(n)])
    keys = cached(e, "keys", lambda: {l: _keycap(c, l, base) for l in labels})
    out = clamp((e.d - c.lt) / 0.25)
    span = c.H + 400 * c.u
    for x, ph, sp, rot, l in spec:
        y = ((ph * span + c.lt * c.H * 0.32 * sp) % span) - 200 * c.u
        place(c, keys[l], x * c.W, y, 1.0, rot + c.lt * 14 * (1 if x > 0.5 else -1), clamp(c.lt / 0.2) * out, "behind")


def _keycap(c, label, base):
    s = int(118 * c.u)
    wide = len(label) > 2
    w = int(s * (1.9 if wide else 1.0))
    im = rrect(w, s, 26 * c.u, tuple(base) + (255,), (255, 255, 255, 180), 3)
    top = rrect(w - int(18 * c.u), s - int(30 * c.u), 20 * c.u, tuple(int(v * 0.94) for v in base) + (255,))
    im.alpha_composite(top, (int(9 * c.u), int(8 * c.u)))
    t = text_img(label, 52 * c.u if not wide else 40 * c.u, "ui" if False else "mono", (40, 40, 48))
    im.alpha_composite(t, ((w - t.width) // 2, (s - t.height) // 2 - int(8 * c.u)))
    return shadowed(im, int(8 * c.u), int(10 * c.u), 120)


@effect("page-cut", "Newspaper pages cut on one word, the word locked in a red box behind the head.",
        {"text": "the word (the speaker's key word)", "color": "box colour (red)"}, family="cards", depth="behind", matte=True, seconds=(1.5, 3.5), intents=("news", "case"), aliases=("match-cut",))
def page_cut(c, e):
    word = txt(e, "text", "TRUTH").upper()
    boxc = col(e, "color", (220, 30, 36))
    n = 6
    idx = min(n - 1, int(c.lt / 0.17))
    last = c.lt >= 0.17 * (n - 1)

    def page(seed):
        rnd = random.Random(seed)
        w, h = int(c.W * 0.96), int(c.H * 0.34)
        im = Image.new("RGBA", (w, h), (244, 240, 230, 255))
        d = ImageDraw.Draw(im)
        mast = text_img(rnd.choice(["THE DAILY RECORD", "MORNING POST", "THE EVENING NEWS", "WORLD TIMES", "THE HERALD"]), 46 * c.u, "didoneb", (24, 24, 24))
        im.alpha_composite(mast, ((w - mast.width) // 2, int(10 * c.u)))
        d.line([(30 * c.u, 78 * c.u), (w - 30 * c.u, 78 * c.u)], fill=(40, 40, 40, 255), width=int(3 * c.u))
        cols = rnd.choice([3, 4])
        cw = (w - 60 * c.u) / cols
        for ci in range(cols):
            y = 100 * c.u
            while y < h - 30 * c.u:
                bw = cw - 18 * c.u
                d.rectangle([30 * c.u + ci * cw, y, 30 * c.u + ci * cw + bw * rnd.uniform(0.6, 1.0), y + 9 * c.u], fill=(130, 126, 118, 255))
                y += 20 * c.u
        return im

    im = cached(e, f"p{idx}", lambda: page(idx + 1))
    cy = clamp(c.hy - c.fh * 0.2, im.height * 0.5, c.H - im.height * 0.5)
    place(c, im, c.W / 2, cy, 1.0 + 0.02 * idx, (-1) ** idx * 0.8, 1.0, "behind")
    wi = cached(e, "word", lambda: fit_text(word, c.W * 0.62, "didoneb", 240, fill=(255, 255, 255)))
    box = rrect(wi.width + int(36 * c.u), wi.height + int(14 * c.u), 6 * c.u, tuple(boxc) + (255,))
    box.alpha_composite(wi, (int(18 * c.u), int(7 * c.u)))
    place(c, shadowed(box, int(8 * c.u), int(6 * c.u), 120), c.W / 2, cy, 1.0 + (0.0 if last else 0.04), 0, clamp(c.lt / 0.12) * clamp((e.d - c.lt) / 0.2), "behind")


@effect("arc-lineup", "Numbered tiles fan out in an arc above the head.", {"text": "tile names separated by |"}, family="cards", depth="guard", seconds=(2.0, 4.5), intents=("howto", "case"), aliases=("lineup",))
def arc_lineup(c, e):
    names = lst(e, "text", ["Hook", "Context", "Build", "Turn", "Reveal", "Payoff", "Loop"])
    tw = int(c.W * 0.13)

    def tile(i, name):
        im = rrect(tw, int(tw * 1.25), tw * 0.16, (24, 24, 28, 225), (255, 255, 255, 60), 2)
        d = ImageDraw.Draw(im)
        num_ = text_img(f"{i + 1:02d}", tw * 0.42, "serif", c.th.paper)
        im.alpha_composite(num_, ((tw - num_.width) // 2, int(tw * 0.04)))
        words = name.split(" ")
        half = len(words) // 2 or 1
        lines = [" ".join(words[:half]), " ".join(words[half:])] if len(name) > 10 else [name]
        f = font("ui", tw * 0.15)
        for j, ln in enumerate([l for l in lines if l]):
            d.text((tw / 2, tw * (0.78 + 0.19 * j)), ln, font=f, fill=(255, 255, 255, 235), anchor="mm")
        return shadowed(im, 8, 5, 90)

    tiles = cached(e, "tiles", lambda: [tile(i, n) for i, n in enumerate(names)])
    n = len(tiles)
    outer = math.ceil(n / 2 + 0.5)
    inner = n - outer
    cx, cy = _x(c), c.hy + c.fh * 0.2
    slots = []
    for cnt, R in ((outer, c.W * 0.43), (inner, c.W * 0.29)):
        for k in range(cnt):
            a = math.pi * (0.94 - 0.88 * k / max(1, cnt - 1))
            slots.append((cx + R * math.cos(a), cy - R * math.sin(a) * 1.05, math.degrees(a - math.pi / 2) * 0.3))
    out = clamp((e.d - c.lt) / 0.2)
    for i, (x, y, r) in enumerate(slots[:n]):
        t0 = 0.05 * i
        if c.lt >= t0:
            q = ease_back((c.lt - t0) / 0.3)
            place(c, tiles[i], lerp(cx, x, clamp(q)), lerp(cy, y, clamp(q)), 0.5 + 0.5 * clamp(q), r * q, clamp((c.lt - t0) / 0.1) * out, "guard")


@effect("count-badge", "A flip clock counts down above the head.", {"from": "the number to count down from (3)", "label": "text on the last card (GO)"},
        family="cards", depth="guard", seconds=(2.0, 4.0), intents=("howto", "hook"), aliases=("countdown-flip",))
def count_badge(c, e):
    start = int(num(e, "from", 3))
    per = e.d / (start + 1)
    k = min(start, int(c.lt / per))
    n = start - k
    label = txt(e, "label", "GO") if n == 0 else str(n)
    lt = c.lt - k * per
    w, h = int(230 * c.u), int(300 * c.u)

    def face(s):
        im = rrect(w, h, 34 * c.u, (26, 26, 30, 255))
        t = fit_text(s, w * 0.78, "display", int(h * 0.8), fill=(244, 240, 232))
        im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
        return im

    cur = cached(e, f"f{label}", lambda: face(label))
    prev = cached(e, f"f{n + 1}", lambda: face(str(n + 1))) if k > 0 else None
    cy = _above(c, h, 28 * c.u)
    cy = cy if cy is not None else c.chin + h * 0.7
    out = clamp((e.d - c.lt) / 0.2) * clamp(c.lt / 0.15)
    top_new, bot_new = cur.crop((0, 0, w, h // 2)), cur.crop((0, h // 2, w, h))
    top_old, bot_old = (prev.crop((0, 0, w, h // 2)), prev.crop((0, h // 2, w, h))) if prev else (top_new, bot_new)
    x = _x(c)
    f = clamp(lt / 0.26)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.alpha_composite(top_new if f > 0.0 or prev is None else top_old, (0, 0))
    canvas.alpha_composite(bot_old if f < 0.5 and prev else bot_new, (0, h // 2))
    if prev and f < 0.5:                      # the old top half folds down
        sq = max(2, int(h // 2 * (1 - f * 2)))
        canvas.alpha_composite(top_old.resize((w, sq)), (0, h // 2 - sq))
    elif prev and f < 1.0:                    # the new bottom half unfolds
        sq = max(2, int(h // 2 * ((f - 0.5) * 2)))
        canvas.alpha_composite(bot_new.resize((w, sq)), (0, h // 2))
    ImageDraw.Draw(canvas).line([(0, h // 2), (w, h // 2)], fill=(0, 0, 0, 200), width=max(2, int(4 * c.u)))
    place(c, shadowed(canvas, int(10 * c.u), int(8 * c.u), 130), x, cy, 0.7 + 0.3 * ease_back(c.lt / 0.3), 0, out, "guard")


# ===================================================================================================================== light play

@effect("dot-build", "The shot builds itself out of glowing dots, then snaps into the full picture.", {"color": "tint the dots (natural colour by default)", "cell": "dot spacing px (22)"},
        family="frame", depth="none", cover_ok=True, camera=True, seconds=(1.5, 3.5), intents=("hook",), aliases=("dot-reveal",))
def dot_build(c, e):
    cell = max(6, int(num(e, "cell", 22) * c.u))
    p = clamp(c.lt / e.d)
    ww, hh = c.W // cell, c.H // cell
    small = cv2.resize(c.img, (ww, hh), interpolation=cv2.INTER_AREA)
    lum = luma(small)[..., 0]
    grow = ease_out(clamp(p / 0.55))
    rad = (0.14 + 0.36 * lum ** 0.8) * cell * grow
    yy, xx = np.mgrid[0:cell, 0:cell].astype(np.float32)
    dist = np.tile(np.hypot(xx - cell / 2 + 0.5, yy - cell / 2 + 0.5), (hh, ww))
    radf = cv2.resize(rad, (ww * cell, hh * cell), interpolation=cv2.INTER_NEAREST)
    dots = np.clip((radf - dist) / 1.3, 0, 1)[..., None]
    colf = cv2.resize(small, (ww * cell, hh * cell), interpolation=cv2.INTER_NEAREST)
    if e.o.get("color"):
        colf = np.clip(luma(colf) * 1.6 * np.float32(col(e, "color", (80, 200, 255))) / 255, 0, 1)
    field = colf * dots + 0.03 * (1 - dots)
    field = np.clip(field + cv2.GaussianBlur(field, (0, 0), cell * 0.8) * 0.55, 0, 1)
    field = cv2.copyMakeBorder(field, 0, c.H - hh * cell, 0, c.W - ww * cell, cv2.BORDER_REPLICATE)
    snap = ease_inout(clamp((p - 0.62) / 0.3))
    c.img[:] = field * (1 - snap) + c.img * snap


@effect("tunnel", "The room tunnels into itself, spinning, while the speaker stays sharp in front.", {"ratio": "each level's scale (0.78)", "spin": "degrees per level (7)", "depth": "levels (5)"},
        family="frame", depth="behind", matte=True, camera=True, cover_ok=True, seconds=(2.0, 4.0), intents=("hook", "story"), aliases=("rabbit-hole",))
def tunnel(c, e):
    k = ramp(c, e, 0.5, 0.4)
    base = c.img.copy()
    ratio = lerp(1.0, num(e, "ratio", 0.78), ease_out(c.lt / 0.8))
    ang = num(e, "spin", 7) * (0.4 + c.lt * 1.2)
    cur, ones = base, np.ones((c.H, c.W), np.float32)
    for _ in range(int(num(e, "depth", 5))):
        M = cv2.getRotationMatrix2D((c.W / 2, c.H / 2), ang, ratio)
        warped = cv2.warpAffine(cur, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        wm = cv2.warpAffine(ones, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
        edge = np.clip(wm - cv2.erode(wm[..., 0], np.ones((5, 5), np.uint8))[..., None], 0, 1)
        cur = np.clip((base * (1 - wm) + warped * wm * 0.93) * (1 - edge * 0.7) + edge * 0.9, 0, 1)
    m = c.m[..., None]
    c.img[:] = base * (1 - k) + (cur * (1 - m) + base * m) * k


_PALETTES = {"paper": ("grid", (30, 60, 150), (246, 243, 236)), "pastel": (None, None, (214, 200, 255)), "red": (None, None, (206, 18, 26)),
             "dark": (None, None, (14, 14, 20)), "mint": (None, None, (196, 240, 220)), "sun": (None, None, (255, 214, 10))}


@effect("room", "Repaint the room behind the speaker: graph paper, pastel, red, dark or any colour; a giant word can sit behind the head and the person can go black and white.",
        {"look": "paper | pastel | red | dark | mint | sun", "color": "a hex colour instead of a look", "text": "a word behind the head", "grade": "grade the person (bw, noir, pop...)",
         "word_color": "colour of the word"}, family="light", depth="behind", matte=True, cover_ok=True, seconds=(2.0, 6.0), intents=("hook", "myth", "story"))
def room(c, e):
    k = ramp(c, e, 0.35, 0.3)
    look = txt(e, "look", "paper")
    pat, ink, paper = _PALETTES.get(look, (None, None, (240, 240, 240)))
    if e.o.get("color"):
        pat, paper = None, col(e, "color", paper)
    if pat:
        bg = room_pattern(c, pat, ink, paper)
    else:
        top = np.float32(paper) / 255
        g = np.linspace(1.0, 0.9, c.H, dtype=np.float32)[:, None, None]
        bg = np.broadcast_to(top * g, (c.H, c.W, 3)).copy()
    if e.o.get("grade"):
        gr = grade(c.img, txt(e, "grade", "bw"))
        c.img[:] = c.img * (1 - k) + gr * k
    paint_room(c, bg, k)
    if txt(e, "text"):
        lum = float(np.dot(np.float32(paper) / 255, [0.299, 0.587, 0.114]))
        wc = col(e, "word_color", (30, 30, 34) if lum > 0.55 else (244, 240, 232))
        im = cached(e, "w", lambda: fit_text(txt(e, "text").upper(), c.W * 0.94, "display", 500, fill=wc))
        place(c, im, c.W / 2, max(c.top - im.height * 0.2, im.height * 0.5 + c.H * 0.02), alpha=k * ease_out(c.lt / 0.3), depth="behind")


# ============================================================================================================= hand-drawn marks

@effect("freeze-point", "Freeze the frame and point at the speaker with a hand-drawn arrow and a marker label.",
        {"text": "label", "color": "marker colour", "side": "left | right (the emptier side)", "target": "x,y as fractions of the frame instead of the head"},
        family="frame", depth="guard", cover_ok=True, seconds=(1.8, 3.5), intents=("hook", "story", "howto"), aliases=("pause-point",))
def freeze_point(c, e):
    snap = cached(e, "snap", lambda: (c.img.copy(), c.m.copy(), (c.fx, c.fy, c.fw, c.fh, c.top, c.shoulder)))
    c.img[:] = snap[0]
    c.m = snap[1]
    c.set_face(*snap[2])
    c.img *= 0.9
    colr = col(e, "color", c.th.accent)
    left = txt(e, "side", "left" if c.fx > c.W / 2 else "right") == "left"
    room_w = (c.hx - c.hrx * 1.15 - 0.04 * c.W) if left else (c.W - 0.04 * c.W - c.hx - c.hrx * 1.15)
    room_w = max(room_w, 0.18 * c.W)
    lab = cached(e, "lab", lambda: fit_text(txt(e, "text", "THIS PART").upper(), room_w, "hand", int(76 * c.u), fill=colr, stroke=int(2 * c.u), stroke_fill=(14, 14, 18), shadow=int(8 * c.u)))
    lx = (0.04 * c.W + lab.width / 2) if left else (c.W - 0.04 * c.W - lab.width / 2)
    ly = min(max(c.hy - c.hry * 0.6, 0.1 * c.H), c.H * 0.6)
    if e.o.get("target"):
        tx, ty = [float(v) for v in txt(e, "target").split(",")[:2]]
        tx, ty = tx * c.W, ty * c.H
    else:
        tx, ty = c.hx + (-1 if left else 1) * c.hrx * 1.2, c.hy + c.hry * 0.1
    pts = wobble(arrow_curve(lx + (lab.width * 0.3 if left else -lab.width * 0.3), ly + lab.height * 0.55, tx, ty, 0.22 if left else -0.22, 40), 2.2 * c.u)
    p = ease_out(clamp((c.lt - 0.25) / 0.7))
    k = 2
    big = Image.new("RGBA", (c.W // k, c.H // k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    sub = path_part(pts, p)
    stroke(d, [(x / k, y / k) for x, y in sub], colr, 9 * c.u / k)
    if p > 0.96:
        arrow_head(d, [(x / k, y / k) for x, y in pts], colr, 9 * c.u / k, 46 * c.u / k)
    lay = big.resize((c.W, c.H), Image.BILINEAR)
    pad = int(6 * c.u) * 2 + int(4 * c.u)
    comp(c, shadowed(lay, int(6 * c.u), int(4 * c.u), 130), -pad, -pad, 1.0, "guard")
    place(c, lab, lx, ly, 0.85 + 0.15 * ease_back(c.lt / 0.3), -4, clamp(c.lt / 0.15), "guard")


@effect("scribble", "Marker doodles draw themselves around the speaker: a loose circle, sparks, an underline, stars.",
        {"text": "a marker label", "color": "marker colour"}, family="frame", depth="guard", seconds=(2.0, 4.0), intents=("hook", "howto", "story"))
def scribble(c, e):
    colr = col(e, "color", c.th.accent)
    k = 2
    big = Image.new("RGBA", (c.W // k, c.H // k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    w = 8 * c.u / k
    out = clamp((e.d - c.lt) / 0.25)
    rx, ry = c.hrx * 1.45, c.hry * 1.28
    ring = [(c.hx + rx * math.cos(a * 0.0174533 + 4.0), c.hy + ry * math.sin(a * 0.0174533 + 4.0) * 1.0) for a in range(-20, 400, 6)]
    stroke(d, [(x / k, y / k) for x, y in wobble(path_part(ring, ease_out(c.lt / 0.7)), 5 * c.u, 4)], colr, w)
    sx, sy = c.hx + c.hrx * 1.4, c.hy - c.hry * 1.2
    for i, a in enumerate((-70, -35, 0)):
        p = clamp((c.lt - 0.5 - i * 0.12) / 0.2)
        if p > 0:
            r0, r1 = 38 * c.u, 100 * c.u
            ca, sa = math.cos(math.radians(a - 40)), math.sin(math.radians(a - 40))
            stroke(d, [((sx + ca * r0) / k, (sy + sa * r0) / k), ((sx + ca * (r0 + (r1 - r0) * p)) / k, (sy + sa * (r0 + (r1 - r0) * p)) / k)], colr, w)
    p = clamp((c.lt - 0.9) / 0.5)
    uy = c.shoulder + c.fh * 0.35
    und = [(c.hx - c.hrx * 1.2 + t * c.hrx * 2.4, uy + math.sin(t * 6) * 8 * c.u) for t in np.linspace(0, 1, 30)]
    stroke(d, [(x / k, y / k) for x, y in wobble(path_part(und, p), 2 * c.u, 9)], colr, w)
    lay = big.resize((c.W, c.H), Image.BILINEAR)
    pad = int(5 * c.u) * 2 + int(4 * c.u)
    comp(c, shadowed(lay, int(5 * c.u), int(4 * c.u), 120), -pad, -pad, out, "guard")
    if txt(e, "text") and c.lt > 0.7:
        lab = cached(e, "lab", lambda: text_img(txt(e, "text").upper(), 64 * c.u, "hand", colr, stroke=int(2 * c.u), stroke_fill=(14, 14, 18), shadow=int(6 * c.u)))
        place(c, lab, c.W / 2, min(c.H * 0.94, uy + lab.height * 0.9), 0.85 + 0.15 * ease_back((c.lt - 0.7) / 0.3), -3, clamp((c.lt - 0.7) / 0.15) * out, "guard")


@effect("stamp", "A big ink stamp slams onto the frame with a jolt.", {"text": "the stamp (REJECTED)", "color": "ink colour (red)", "angle": "degrees (-12)", "y": "vertical position, fraction (0.64)"},
        family="frame", depth="guard", seconds=(1.2, 3.0), intents=("myth", "howto", "payoff"), aliases=("reject-stamp",))
def stamp(c, e):
    colr = col(e, "color", (214, 28, 36))
    word = txt(e, "text", "REJECTED").upper()

    def build():
        t = fit_text(word, c.W * 0.7, "bold", 300, fill=colr)
        w, h = t.width + int(80 * c.u), t.height + int(60 * c.u)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([6, 6, w - 7, h - 7], int(22 * c.u), outline=tuple(colr) + (255,), width=int(9 * c.u))
        d.rounded_rectangle([int(26 * c.u), int(26 * c.u), w - int(27 * c.u), h - int(27 * c.u)], int(12 * c.u), outline=tuple(colr) + (255,), width=int(3 * c.u))
        im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
        rng = np.random.default_rng(4)
        noise = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), 1.2)
        keep = np.where(noise > 0.34, 1.0, 0.0).astype(np.float32)
        a = np.asarray(im.split()[3], np.float32) * keep
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
        return im

    im = cached(e, "stamp", build)
    hit = 0.16
    k = ease_in(clamp(c.lt / hit))
    s = lerp(2.6, 1.0, k) if c.lt < hit else 1.0 + 0.04 * max(0, 1 - (c.lt - hit) / 0.12)
    out = clamp((e.d - c.lt) / 0.25)
    cy = c.H * num(e, "y", 0.64)
    place(c, shadowed(im, int(5 * c.u), int(5 * c.u), 90, (60, 0, 0)), c.W / 2, cy, s, num(e, "angle", -12), clamp(c.lt / 0.06) * out * (0.93 if c.lt > hit else 0.7), "guard")
    if c.lt > hit:
        shake(c, 16 * c.u * max(0.0, 1 - (c.lt - hit) / 0.28), c.lt)
