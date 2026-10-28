"""fx_ui.py - person-aware effects, part two: interface cards, liquid glass, data callouts, frames and covers.

Same contract as fx_looks.py: `fn(c, e)` draws one frame from `c.lt`, and keeps nothing between frames except through `cached`.
The interface cards are drawn mock-ups (comment sheets, notifications, switches); they carry no real accounts or data and take every name and number
from the plan, so numbers shown on screen should come from the beat map's claims.
"""
from __future__ import annotations

import math
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fx_core import (GREEN, BLUE, ORANGE, PURPLE, RED, arrow_curve, cached, camera, card_image, clamp, comp, count_text, ease_back, ease_in, ease_inout, ease_out,
                     face_cam, fit_text, font, glass, grade, grain, icon, keyframes, lerp, mesh, paint_room, path_part, place, ramp, rrect, shadowed, shake, stroke, text_img,
                     typed, vary, vgradient, vignette, wobble, ellipse, wrap)
from fx_registry import col, effect, lst, num, opt, times, txt


# ------------------------------------------------------------------------------------------------------------------- helpers

def dock(c, w, h, pos="below", gap=0.025):
    """Where a w x h element sits relative to the head: above | below | left | right. Returns (cx, cy), kept inside the frame."""
    g = gap * c.H
    if pos == "above":
        cy = c.top - g - h / 2
        if cy - h / 2 < c.H * 0.02:
            pos = "below"
    if pos == "below":
        cy = min(c.chin + g + h / 2, c.H * 0.95 - h / 2)
        cx = c.W / 2 * 0.5 + c.fx * 0.5
    elif pos == "above":
        cx = c.W / 2 * 0.5 + c.fx * 0.5
    elif pos == "left":
        cx, cy = c.hx - c.hrx - g - w / 2, c.hy
    else:
        cx, cy = c.hx + c.hrx + g + w / 2, c.hy
    return float(np.clip(cx, w / 2 + c.W * 0.03, c.W - w / 2 - c.W * 0.03)), float(cy)


def face_chip(c, e, size):
    """A round avatar cut from the speaker's own face, grabbed once at the start of the effect."""
    def grab():
        r = c.fw * 0.9
        x0, y0 = int(max(0, c.fx - r)), int(max(0, c.fy - r * 1.05))
        crop = c.img[y0:int(y0 + 2 * r), x0:int(x0 + 2 * r)]
        return Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    src = cached(e, "face", grab).resize((int(size), int(size)), Image.LANCZOS)
    m = Image.new("L", src.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, src.width - 1, src.height - 1], fill=255)
    src.putalpha(m)
    return src


def _x(c):
    """Where a graphic that follows the head horizontally sits: mostly centred, partly on the face."""
    return c.W / 2 * 0.6 + c.fx * 0.4


def tx(c, s, size, kind="uib", fill=(255, 255, 255), **kw):
    return text_img(s, size * c.u, kind, fill, **kw)


def lay(c, w, h):
    return Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))


def tick_mark(d, x, y, s, color=(255, 255, 255, 255), w=None):
    d.line([(x - s * 0.5, y), (x - s * 0.1, y + s * 0.4), (x + s * 0.55, y - s * 0.45)], fill=color, width=int(w or max(2, s * 0.2)), joint="curve")


def spinner(size, t, color=(255, 255, 255)):
    im = Image.new("RGBA", (int(size), int(size)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = max(2, int(size * 0.14))
    d.ellipse([w, w, size - w, size - w], outline=tuple(color) + (60,), width=w)
    a = (t * 420) % 360
    d.arc([w, w, size - w, size - w], a, a + 100, fill=tuple(color) + (255,), width=w)
    return im


def switch(w, h, on, color=GREEN):
    """An on/off switch; `on` is 0..1 for the knob's travel."""
    im = rrect(w, h, h / 2, tuple(int(lerp(120, v, on)) for v in color) + (255,))
    r = h - 8
    x = 4 + (w - h) * on
    d = ImageDraw.Draw(im)
    d.ellipse([x, 4, x + r, 4 + r], fill=(255, 255, 255, 255))
    return im


# =============================================================================================================== social interface

@effect("comment-sheet", "A comments sheet behind the head: a comment types itself into the bar, posts, gets a heart, and optionally a reply.",
        {"text": "the comment (typed)", "handle": "the commenter's name", "reply": "an optional reply line", "count": "comment count in the header (1,204)"},
        family="ui", depth="behind", matte=True, seconds=(3.0, 6.0), intents=("howto", "story"), aliases=("comment-box",))
def comment_sheet(c, e):
    s = c.u
    w, h = int(c.W * 0.9), int(c.H * 0.27)
    word = txt(e, "text", "Try this")
    sheet = cached(e, "sheet", lambda: _comment_base(c, e, w, h))
    k = ease_out(c.lt / 0.4)
    out = clamp((e.d - c.lt) / 0.2)
    top = c.H * 0.02 - (1 - k) * h
    live = sheet.copy()
    d = ImageDraw.Draw(live)
    t_type, t_post = e.d * 0.2, e.d * 0.58
    p = clamp((c.lt - t_type) / (t_post - t_type - 0.15))
    f = font("ui", 36 * s)
    shown = typed(word, p) if c.lt < t_post else ""
    if shown:
        d.text((int(80 * s), h - int(78 * s)), shown + ("|" if int(c.lt * 3) % 2 == 0 else ""), font=f, fill=(255, 255, 255, 255))
    else:
        d.text((int(80 * s), h - int(78 * s)), "Add a comment…", font=f, fill=(255, 255, 255, 110))
    if c.lt >= t_post:
        q = ease_back((c.lt - t_post) / 0.3)
        y0 = int(h * 0.2)
        av = face_chip(c, e, int(80 * s))
        live.alpha_composite(av, (int(34 * s), y0))
        d.text((int(136 * s), y0 + int(2 * s)), txt(e, "handle", "you"), font=font("uib", 30 * s), fill=(255, 255, 255, 235))
        d.text((int(136 * s), y0 + int(42 * s)), word, font=font("ui", 36 * s), fill=(255, 255, 255, 255))
        hc = icon("heart", int(44 * s), RED if c.lt > t_post + 0.7 else (255, 255, 255))
        hs = 0.7 + 0.5 * ease_back((c.lt - t_post - 0.7) / 0.3) if c.lt > t_post + 0.7 else 1.0
        hc = hc.resize((max(2, int(hc.width * hs)), max(2, int(hc.height * hs))), Image.BILINEAR)
        live.alpha_composite(hc, (w - int(100 * s), y0 + int(20 * s)))
        if txt(e, "reply") and c.lt > t_post + 1.0:
            rp = clamp((c.lt - t_post - 1.0) / 0.35)
            d.text((int(136 * s), y0 + int(108 * s)), "↳ " + txt(e, "reply"), font=font("ui", 30 * s), fill=(255, 255, 255, int(220 * rp)))
    comp(c, live, c.W / 2 - w / 2, top, out, "behind")


def _comment_base(c, e, w, h):
    s = c.u
    im = rrect(w, h + int(60 * s), 44 * s, (28, 28, 34, 244))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([w / 2 - 40 * s, 12 * s, w / 2 + 40 * s, 20 * s], 4, fill=(255, 255, 255, 90))
    d.text((w / 2, 52 * s), f"{txt(e, 'count', '1,204')} comments", font=font("uib", 34 * s), fill=(255, 255, 255, 255), anchor="mm")
    d.rounded_rectangle([int(34 * s), h - int(100 * s), w - int(34 * s), h - int(30 * s)], int(34 * s), fill=(52, 52, 60, 255))
    d.ellipse([int(42 * s), h - int(92 * s), int(106 * s), h - int(36 * s)], fill=(90, 90, 100, 255))
    return im


@effect("follow-tap", "A Follow button pops up beside the head and flips to Following with a tap.",
        {"at": "video second of the flip", "text": "name shown on the card", "x": "0..1 (right of the head)", "y": "0..1", "color": "button colour"},
        family="ui", depth="guard", seconds=(2.0, 4.0), intents=("howto", "story"), aliases=("tap",))
def follow_tap(c, e):
    s = c.u
    flip = (float(e.o["at"]) - e.start) if e.o.get("at") else e.d * 0.5
    w, h = int(380 * s), int(116 * s)
    colr = col(e, "color", BLUE)
    on = clamp((c.lt - flip) / 0.2)
    base = rrect(w, h, h / 2, tuple(int(lerp(a, b, on)) for a, b in zip(colr, (60, 60, 68))) + (255,))
    d = ImageDraw.Draw(base)
    label = "Following" if on > 0.5 else "Follow"
    f = font("uib", 44 * s)
    tw = f.getlength(label)
    if on > 0.5:
        ic = icon("check", int(46 * s), (255, 255, 255))
        base.alpha_composite(ic, (int((w - tw) / 2 - 56 * s), int(h / 2 - 23 * s)))
        d.text((w / 2 + 26 * s, h / 2), label, font=f, fill=(255, 255, 255, 255), anchor="mm")
    else:
        d.text((w / 2, h / 2), label, font=f, fill=(255, 255, 255, 255), anchor="mm")
    cx, cy = c.W * 0.7, min(c.chin + 0.06 * c.H, c.H * 0.9)
    if e.o.get("x") is not None:
        cx, cy = num(e, "x", 0.7) * c.W, num(e, "y", 0.5) * c.H
    out = clamp((e.d - c.lt) / 0.2)
    press = 1 - 0.07 * math.sin(clamp((c.lt - flip + 0.08) / 0.16) * math.pi) if abs(c.lt - flip) < 0.2 else 1.0
    place(c, shadowed(base, int(10 * s), int(8 * s), 120), cx, cy, ease_back(c.lt / 0.35) * press, 0, out, "guard")
    if abs(c.lt - flip) < 0.35:                         # the tap: a ring that grows and fades
        q = clamp((c.lt - flip + 0.1) / 0.4)
        ring = ellipse(int(120 * s), int(120 * s), None, (255, 255, 255, int(220 * (1 - q))), max(2, int(5 * s)))
        place(c, ring, cx + w * 0.18, cy + h * 0.25, 0.6 + q, 0, 1.0, "guard")


@effect("messages", "Message notifications pop in one after another as glass cards, stacking down from the top.",
        {"text": "messages separated by | (Title::Body also works)", "title": "app name (Messages)", "y": "top of the stack, fraction (0.06)"},
        family="ui", depth="front", seconds=(3.0, 6.0), intents=("story", "howto"), aliases=("notifications", "texts"))
def messages(c, e):
    s = c.u
    items = [m.split("::") if "::" in m else ["", m] for m in lst(e, "text", ["Your video is ready", "It passed every check", "Ship it"])][:5]
    w, h = int(c.W * 0.88), int(172 * s)
    title = txt(e, "title", "Messages")
    out = clamp((e.d - c.lt) / 0.25)
    step = min(0.9, max(0.35, (e.d - 0.8) / max(1, len(items))))
    stack_h = len(items) * (h + 16 * s)
    y0 = c.H * num(e, "y", 0.0) if e.o.get("y") is not None else (c.H * 0.03 if c.top - c.H * 0.03 > stack_h else min(c.chin + 0.025 * c.H, c.H * 0.94 - stack_h))
    n = sum(1 for i in range(len(items)) if c.lt >= 0.2 + i * step)
    for i in range(len(items)):
        t0 = 0.2 + i * step
        if c.lt < t0:
            break
        q = ease_back((c.lt - t0) / 0.35)
        top = y0 + i_pos(c, e, i, n, step, h, s)
        x0 = c.W / 2 - w / 2
        box = (x0, top - (1 - clamp(q)) * 90 * s, x0 + w, top - (1 - clamp(q)) * 90 * s + h)
        glass(c, box, 46 * s, "guard", tint=(255, 245, 235), tint_amt=0.25, alpha=clamp(q) * out, spec=1.1)
        L = lay(c, w, h)
        d = ImageDraw.Draw(L)
        ic = rrect(int(96 * s), int(96 * s), 24 * s, tuple(GREEN) + (255,))
        ic.alpha_composite(icon("chat", int(58 * s), (255, 255, 255)), (int(19 * s), int(19 * s)))
        L.alpha_composite(ic, (int(28 * s), int(38 * s)))
        d.text((int(150 * s), int(28 * s)), items[i][0] or title, font=font("uib", 32 * s), fill=(255, 255, 255, 255))
        d.text((w - int(30 * s), int(30 * s)), "now", font=font("ui", 28 * s), fill=(255, 255, 255, 190), anchor="ra")
        body = items[i][1] if len(items[i]) > 1 else items[i][0]
        d.text((int(150 * s), int(76 * s)), body, font=font("ui", 36 * s), fill=(255, 255, 255, 240))
        comp(c, L, x0, box[1], clamp(q) * out, "guard")


def i_pos(c, e, i, n, step, h, s):
    """Vertical offset of notification i once n have arrived: each new one pushes the older ones down."""
    t_i = 0.2 + i * step
    slot_now = n - 1 - i
    prev_slot = slot_now - 1 if i < n - 1 else 0
    last_t = 0.2 + (n - 1) * step
    q = ease_out((c.lt - last_t) / 0.3) if i < n - 1 else 1.0
    return lerp(max(0, prev_slot), slot_now, q) * (h + 16 * s)


@effect("toggles", "A settings card with switches that flip on, one line at a time.",
        {"text": "rows separated by |", "ticks": "video seconds when each row flips, separated by |", "pos": "above | below (below)", "color": "switch colour"},
        family="ui", depth="guard", seconds=(3.0, 6.0), intents=("howto",), aliases=("apple-toggles",))
def toggles(c, e):
    s = c.u
    rows = lst(e, "text", ["Hook in 3 seconds", "Numbers from claims", "Captions on", "Safe zones"])[:6]
    tk = times(e)
    w, rh = int(c.W * 0.84), int(112 * s)
    h = rh * len(rows) + int(36 * s)
    colr = col(e, "color", GREEN)
    cx, cy = dock(c, w, h, txt(e, "pos", "below"), 0.015)
    k = ease_back(c.lt / 0.4)
    out = clamp((e.d - c.lt) / 0.2)
    L = rrect(w, h, 44 * s, (246, 246, 250, 238))
    d = ImageDraw.Draw(L)
    for i, r in enumerate(rows):
        y = int(18 * s) + i * rh
        t_flip = tk[i] if i < len(tk) else 0.7 + i * max(0.3, (e.d - 1.2) / len(rows))
        on = ease_inout(clamp((c.lt - t_flip) / 0.22))
        d.text((int(40 * s), y + rh // 2), r, font=font("uim", 40 * s), fill=(24, 24, 28, 255), anchor="lm")
        L.alpha_composite(switch(int(128 * s), int(72 * s), on, colr), (w - int(170 * s), y + (rh - int(72 * s)) // 2))
        if i < len(rows) - 1:
            d.line([(int(40 * s), y + rh), (w - int(40 * s), y + rh)], fill=(0, 0, 0, 28), width=2)
    place(c, shadowed(L, int(14 * s), int(10 * s), 110), cx, cy, 0.85 + 0.15 * k, 0, clamp(c.lt / 0.15) * out, "guard")


@effect("task-list", "An agent task list builds under the chin: each step spins, then ticks green.",
        {"text": "steps separated by | (step::detail also works)", "title": "card title", "pos": "above | below (below)"}, family="ui", depth="guard", seconds=(3.5, 7.0), intents=("howto", "story"),
        aliases=("checklist",))
def task_list(c, e):
    s = c.u
    steps = [x.split("::") + [""] for x in lst(e, "text", ["Read the brief", "Plan the beats", "Price every call", "Render", "Check quality"])][:7]
    w, rh = int(c.W * 0.86), int(98 * s)
    h = int(88 * s) + rh * len(steps)
    cx, cy = dock(c, w, h, txt(e, "pos", "below"), 0.012)
    out = clamp((e.d - c.lt) / 0.2)
    L = rrect(w, h, 40 * s, (30, 30, 36, 240), (255, 255, 255, 40), 2)
    d = ImageDraw.Draw(L)
    d.text((int(36 * s), int(44 * s)), txt(e, "title", "Working on it").upper(), font=font("uib", 30 * s), fill=(210, 210, 222, 255), anchor="lm")
    per = (e.d - 0.8) / len(steps)
    for i, st in enumerate(steps):
        y = int(88 * s) + i * rh
        t0 = 0.5 + i * per
        done = c.lt >= t0 + per * 0.85
        active = t0 <= c.lt < t0 + per * 0.85
        vis = clamp((c.lt - (t0 - 0.2)) / 0.25)
        a = int(255 * (0.35 + 0.65 * vis))
        if done:
            d.ellipse([int(36 * s), y + int(20 * s), int(36 * s) + int(58 * s), y + int(78 * s)], fill=tuple(GREEN) + (a,))
            tick_mark(d, int(65 * s), y + int(49 * s), 24 * s, (255, 255, 255, 255), 5 * s)
        elif active:
            L.alpha_composite(spinner(int(58 * s), c.lt - t0, (255, 255, 255)), (int(36 * s), y + int(20 * s)))
        else:
            d.ellipse([int(36 * s), y + int(20 * s), int(36 * s) + int(58 * s), y + int(78 * s)], outline=(255, 255, 255, 70), width=max(2, int(4 * s)))
        d.text((int(124 * s), y + int(49 * s)), st[0], font=font("uim", 38 * s), fill=(255, 255, 255, a), anchor="lm")
        if st[1]:
            d.text((w - int(36 * s), y + int(49 * s)), st[1], font=font("ui", 28 * s), fill=(170, 170, 186, a), anchor="rm")
    place(c, shadowed(L, int(14 * s), int(10 * s), 130), cx, cy, 0.9 + 0.1 * ease_back(c.lt / 0.35), 0, clamp(c.lt / 0.15) * out, "guard")


@effect("todo", "A checklist card beside the head ticks items off as the speaker talks.",
        {"text": "items separated by |", "ticks": "video seconds when each item ticks, separated by |", "title": "card title", "side": "left | right"},
        family="ui", depth="guard", seconds=(3.0, 6.0), intents=("howto",), aliases=("to-do",))
def todo(c, e):
    s = c.u
    items = lst(e, "text", ["Hook first", "One idea per beat", "Numbers from code", "Captions on"])[:6]
    tk = times(e)
    w, rh = int(c.W * 0.33), int(84 * s)
    h = int(96 * s) + rh * len(items)
    side = txt(e, "side", "left" if c.fx > c.W / 2 else "right")
    cx = c.W * 0.03 + w / 2 if side == "left" else c.W * 0.97 - w / 2
    cy = min(c.hy + c.hry * 0.7, c.H * 0.94 - h / 2)
    out = clamp((e.d - c.lt) / 0.2)
    L = rrect(w, h, 34 * s, (250, 248, 242, 244))
    d = ImageDraw.Draw(L)
    d.text((int(34 * s), int(48 * s)), txt(e, "title", "TO DO"), font=font("uib", 36 * s), fill=(24, 24, 28, 255), anchor="lm")
    for i, it in enumerate(items):
        y = int(96 * s) + i * rh
        t_t = tk[i] if i < len(tk) else 0.6 + i * max(0.3, (e.d - 1.0) / len(items))
        p = ease_out(clamp((c.lt - t_t) / 0.25))
        bx = int(34 * s)
        d.rounded_rectangle([bx, y + int(20 * s), bx + int(50 * s), y + int(70 * s)], int(12 * s), outline=(24, 24, 28, 200), width=max(2, int(4 * s)))
        if p > 0:
            d.rounded_rectangle([bx, y + int(20 * s), bx + int(50 * s), y + int(70 * s)], int(12 * s), fill=tuple(GREEN) + (int(255 * p),))
            tick_mark(d, bx + int(25 * s), y + int(45 * s), 22 * s * p, (255, 255, 255, 255), 5 * s)
        f = font("uim", 30 * s)
        d.text((bx + int(72 * s), y + int(45 * s)), it, font=f, fill=(24, 24, 28, 255 if p < 1 else 150), anchor="lm")
        if p > 0:
            d.line([(bx + int(72 * s), y + int(45 * s)), (bx + int(72 * s) + f.getlength(it) * p, y + int(45 * s))], fill=(24, 24, 28, 200), width=max(2, int(3 * s)))
    place(c, shadowed(L, int(12 * s), int(8 * s), 110), cx, cy, 0.88 + 0.12 * ease_back(c.lt / 0.35), (3 if side == "left" else -3) * (1 - ease_out(c.lt / 0.4)), clamp(c.lt / 0.15) * out, "guard")


@effect("tier-list", "A tier list drops in and an item flies into the top tier.", {"title": "list title", "item": "the item that flies in (the speaker's face by default)", "others": "other items separated by |"},
        family="ui", depth="guard", seconds=(3.5, 6.0), intents=("myth", "case"), aliases=("tier",))
def tier_list(c, e):
    s = c.u
    w, rh = int(c.W * 0.88), int(112 * s)
    tiers = [("S", (255, 99, 99)), ("A", (255, 170, 80)), ("B", (255, 224, 90)), ("C", (150, 220, 110)), ("D", (110, 190, 250))]
    h = rh * len(tiers) + int(70 * s)
    cx, cy = c.W / 2, min(c.chin + 0.02 * c.H + h / 2, c.H * 0.95 - h / 2)
    k = ease_back(c.lt / 0.45)
    out = clamp((e.d - c.lt) / 0.2)
    others = lst(e, "others", ["Template", "Guess", "Stock"])
    L = rrect(w, h, 34 * s, (20, 20, 26, 238))
    d = ImageDraw.Draw(L)
    d.text((w / 2, int(36 * s)), txt(e, "title", "TIER LIST").upper(), font=font("uib", 32 * s), fill=(220, 220, 232, 255), anchor="mm")
    for i, (t, cc) in enumerate(tiers):
        y = int(70 * s) + i * rh
        d.rectangle([int(14 * s), y + 4, int(14 * s) + int(110 * s), y + rh - 4], fill=tuple(cc) + (255,))
        d.text((int(14 * s) + int(55 * s), y + rh / 2), t, font=font("uib", 60 * s), fill=(24, 24, 28, 255), anchor="mm")
        d.line([(int(130 * s), y + rh), (w - int(14 * s), y + rh)], fill=(255, 255, 255, 22), width=2)
    for j, o in enumerate(others):
        r = 2 + j
        chip = rrect(int(160 * s), int(72 * s), 18 * s, (62, 62, 72, 255))
        ImageDraw.Draw(chip).text((chip.width / 2, chip.height / 2), o, font=font("uim", 28 * s), fill=(235, 235, 245, 255), anchor="mm")
        L.alpha_composite(chip, (int(150 * s + j * 176 * s), int(70 * s) + r * rh + int(20 * s)))
    place(c, shadowed(L, int(14 * s), int(10 * s), 130), cx, cy - (1 - clamp(k)) * 120 * s, 0.9 + 0.1 * clamp(k), 0, clamp(c.lt / 0.15) * out, "guard")
    t0 = e.d * 0.42
    if c.lt >= t0:
        q = clamp((c.lt - t0) / (e.d * 0.3))
        top = cy - h / 2 + int(70 * s) + rh / 2
        sx, sy = c.hx, c.chin + 0.06 * c.H            # the item leaves from under the chin, never from the face
        ex, ey = c.W / 2 - w / 2 + int(300 * s), top - (1 - clamp(k)) * 120 * s
        px = lerp(sx, ex, ease_inout(q))
        py = lerp(sy, ey, ease_inout(q)) - math.sin(q * math.pi) * 160 * s
        if e.o.get("item"):
            chip = rrect(int(250 * s), int(80 * s), 20 * s, tuple(c.th.accent) + (255,))
            ImageDraw.Draw(chip).text((chip.width / 2, chip.height / 2), txt(e, "item"), font=font("uib", 32 * s), fill=(24, 24, 28, 255), anchor="mm")
        else:
            chip = face_chip(c, e, int(96 * s))
        place(c, shadowed(chip, int(8 * s), int(6 * s), 130), px, py, 1.0 - 0.15 * q, math.sin(q * 6) * 6, clamp((c.lt - t0) / 0.1) * out, "front")


@effect("progress-glitch", "A progress bar fills, glitches, and the frame breaks apart into shifted slices.",
        {"text": "the label (Uninstalling doubt)", "y": "bar position, fraction (0.74)"}, family="ui", depth="front", cover_ok=True, camera=True, seconds=(2.5, 5.0), intents=("myth", "story"),
        aliases=("uninstall",))
def progress_glitch(c, e):
    s = c.u
    p = clamp(c.lt / (e.d * 0.72))
    glitch = clamp((c.lt - e.d * 0.6) / (e.d * 0.4))
    if glitch > 0:
        rng = np.random.default_rng(int(c.t * c.fps))
        band = max(8, int(c.H / 28))
        for y in range(0, c.H, band):
            if rng.random() < 0.55 * glitch:
                dx = int(rng.normal(0, 60 * s) * glitch)
                c.img[y:y + band] = np.roll(c.img[y:y + band], dx, axis=1)
                c.m[y:y + band] = np.roll(c.m[y:y + band], dx, axis=1)
        sh = int(10 * s * glitch)
        if sh:
            c.img[..., 0] = np.roll(c.img[..., 0], sh, axis=1)
            c.img[..., 2] = np.roll(c.img[..., 2], -sh, axis=1)
    w, h = int(c.W * 0.84), int(118 * s)
    L = rrect(w, h + int(60 * s), 30 * s, (24, 24, 30, 245), (255, 255, 255, 40), 2)
    d = ImageDraw.Draw(L)
    d.text((int(30 * s), int(36 * s)), txt(e, "text", "Uninstalling doubt…"), font=font("uib", 34 * s), fill=(235, 235, 245, 255), anchor="lm")
    d.text((w - int(30 * s), int(36 * s)), f"{int(p * 100)}%", font=font("uib", 34 * s), fill=tuple(c.th.accent) + (255,), anchor="rm")
    d.rounded_rectangle([int(30 * s), int(76 * s), w - int(30 * s), int(106 * s)], int(15 * s), fill=(60, 60, 72, 255))
    if p > 0:
        d.rounded_rectangle([int(30 * s), int(76 * s), int(30 * s) + (w - int(60 * s)) * p, int(106 * s)], int(15 * s), fill=tuple(c.th.accent) + (255,))
    jx = int(np.random.default_rng(int(c.t * c.fps) + 3).normal(0, 14 * s) * glitch)
    place(c, shadowed(L, int(12 * s), int(8 * s), 130), c.W / 2 + jx, c.H * num(e, "y", 0.74), 1.0, 0, clamp(c.lt / 0.15) * clamp((e.d - c.lt) / 0.2), "front")


# ============================================================================================================ frames and covers

def _gradient_bg(c, top, bottom):
    t = np.linspace(0, 1, c.H, dtype=np.float32)[:, None, None]
    return np.broadcast_to(np.float32(top) / 255 * (1 - t) + np.float32(bottom) / 255 * t, (c.H, c.W, 3)).copy()


def _paste_frame(c, frame, m, scale, cx, cy, radius, bg):
    """Shrink the whole frame into a rounded card centred at (cx, cy) on `bg` (an array)."""
    w, h = int(c.W * scale), int(c.H * scale)
    small = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
    mask = np.asarray(rrect(w, h, radius, (255, 255, 255, 255)).split()[3], np.float32)[..., None] / 255
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    out = bg
    gx0, gy0, gx1, gy1 = max(0, x0), max(0, y0), min(c.W, x0 + w), min(c.H, y0 + h)
    sh = cv2.GaussianBlur(np.pad(mask[..., 0], 60), (0, 0), 24 * c.u)
    sx0, sy0 = x0 - 60, y0 + int(18 * c.u) - 60
    hx0, hy0, hx1, hy1 = max(0, sx0), max(0, sy0), min(c.W, sx0 + sh.shape[1]), min(c.H, sy0 + sh.shape[0])
    if hx1 > hx0 and hy1 > hy0:
        out[hy0:hy1, hx0:hx1] *= (1 - 0.45 * sh[hy0 - sy0:hy1 - sy0, hx0 - sx0:hx1 - sx0])[..., None]
    if gx1 > gx0 and gy1 > gy0:
        a = mask[gy0 - y0:gy1 - y0, gx0 - x0:gx1 - x0]
        out[gy0:gy1, gx0:gx1] = out[gy0:gy1, gx0:gx1] * (1 - a) + small[gy0 - y0:gy1 - y0, gx0 - x0:gx1 - x0] * a
    return out


@effect("reel-frame", "The video shrinks into a social card with a handle, side icons and a caption.", {"text": "the handle (@you)", "caption": "the caption line"},
        family="frame", depth="front", cover_ok=True, camera=True, seconds=(2.5, 5.0), intents=("hook", "story"))
def reel_frame(c, e):
    s = c.u
    p = ease_inout(clamp(c.lt / 0.5)) * ease_inout(clamp((e.d - c.lt) / 0.4))
    scale = lerp(1.0, 0.8, p)
    bg = _gradient_bg(c, tuple(int(v * 0.5) for v in c.th.accent2), tuple(c.th.bg))
    frame, m = c.img.copy(), c.m
    bg = _paste_frame(c, frame, m, scale, c.W / 2, c.H * 0.48, 54 * s * scale, bg)
    c.img[:] = bg
    if p > 0.3:
        a = clamp((p - 0.3) / 0.7)
        cw, chh = c.W * scale, c.H * scale
        x1, y1 = c.W / 2 + cw / 2, c.H * 0.48 + chh / 2
        names = txt(e, "text", "@you")
        chip = face_chip(c, e, int(70 * s))
        place(c, chip, c.W / 2 - cw / 2 + 60 * s, c.H * 0.48 - chh / 2 + 62 * s, 1.0, 0, a, "front")
        place(c, text_img(names, 34 * s, "uib", (255, 255, 255), shadow=int(5 * s)), c.W / 2 - cw / 2 + 120 * s + 80 * s, c.H * 0.48 - chh / 2 + 62 * s, 1.0, 0, a, "front")
        for i, ic in enumerate(("heart", "chat", "arrow")):
            place(c, shadowed(icon(ic, int(58 * s), (255, 255, 255)), int(6 * s), int(3 * s), 140), x1 - 62 * s, y1 - 520 * s * scale + i * 120 * s, 1.0, 0, a, "front")
        cap = txt(e, "caption")
        if cap:
            place(c, text_img(cap, 36 * s, "uim", (255, 255, 255), shadow=int(6 * s)), c.W / 2 - cw / 2 + 40 * s + font("uim", 36 * s).getlength(cap) / 2, y1 - 80 * s, 1.0, 0, a, "front")


@effect("grid-place", "The speaker shrinks into the centre tile of a 3x3 grid, then eight tiles pop in around with counts on every tile.",
        {"images": "folder of images or clips", "views": "nine counts separated by | (the ninth is the speaker's)"}, family="frame", depth="front", cover_ok=True, images=True, camera=True,
        seconds=(3.0, 6.0), intents=("numbers", "case"), aliases=("place-in-grid",))
def grid_place(c, e):
    s = c.u
    p = ease_inout(clamp(c.lt / 0.55))
    gap = 14 * s
    tw = (c.W - 4 * gap) / 3
    th = tw * 16 / 9
    top = (c.H - (3 * th + 2 * gap)) / 2
    bg = _gradient_bg(c, (30, 30, 40), (16, 16, 22))
    if p < 1:
        bg = cv2.GaussianBlur(c.img, (0, 0), 28 * s) * 0.35 * (1 - p) + bg * p
    cx, cy = c.W / 2, top + th * 1.5 + gap
    frame, matte = c.img.copy(), c.m
    deck = _deck_plain(c, e, int(tw), int(th))
    views = lst(e, "views", ["1.2M", "340K", "88K", "512K", "2.1M", "97K", "410K", "63K", "9M"])
    order = [0, 1, 2, 3, 5, 6, 7, 8]
    pos = [(r, q) for r in range(3) for q in range(3)]
    c.img = np.ascontiguousarray(bg, np.float32)                  # draw the tiles on their own canvas, then drop the speaker's tile in the middle
    for k, idx in enumerate(order):
        t0 = 0.55 + k * 0.22
        if c.lt < t0:
            continue
        q = ease_back((c.lt - t0) / 0.3)
        r, qq = pos[idx]
        x, y = gap + qq * (tw + gap) + tw / 2, top + r * (th + gap) + th / 2
        L = deck[k % len(deck)].copy()
        d = ImageDraw.Draw(L)
        d.text((int(54 * s), int(th - 40 * s)), views[idx % len(views)], font=font("uib", 34 * s), fill=(255, 255, 255, 255), anchor="lm")
        L.alpha_composite(icon("play", int(30 * s), (255, 255, 255)), (int(14 * s), int(th - 56 * s)))
        place(c, L, x, y, 0.6 + 0.4 * clamp(q), 0, clamp((c.lt - t0) / 0.1) * clamp((e.d - c.lt) / 0.25), "plain")
    c.img = _paste_frame(c, frame, matte, lerp(1.0, tw / c.W, p), lerp(c.W / 2, cx, p), lerp(c.H / 2, cy, p), 24 * s, c.img)
    vv = views[8 % len(views)] if len(views) >= 9 else views[-1]
    if p > 0.95:
        place(c, text_img(vv, 34 * s, "uib", (255, 255, 255), shadow=int(5 * s)), cx - tw / 2 + 80 * s, cy + th / 2 - 42 * s, 1.0, 0, clamp((c.lt - 0.5) / 0.2), "plain")


def _deck_plain(c, e, w, h):
    def build():
        src = e.cards or [Image.new("RGB", (270, 480), (60, 60, 80))]
        own = bool(e.o.get("images"))
        out = []
        for i, im in enumerate(src):
            im = im if own else vary(im, i)
            sw, sh = im.size
            k = max(w / sw, h / sh)
            im = im.resize((max(w, int(sw * k)), max(h, int(sh * k))), Image.LANCZOS)
            l, t = (im.width - w) // 2, (im.height - h) // 2
            im = im.crop((l, t, l + w, t + h)).convert("RGBA")
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(24 * c.u), fill=255)
            im.putalpha(m)
            out.append(im)
        return out
    return cached(e, f"plain{w}x{h}", build)


@effect("split-top", "A headline card (or b-roll still) slides down and pushes the speaker into the bottom half of the frame.",
        {"text": "headline lines separated by |", "hl": "a word to highlight", "images": "a b-roll still for the top panel instead of a headline", "tag": "a price-tag sticker on the b-roll",
         "pill": "a small label above the headline"}, family="frame", depth="front", images=True, camera=True, cover_ok=True, seconds=(2.5, 5.0), intents=("news", "howto", "case"),
        aliases=("split-headline", "broll-split"))
def split_top(c, e):
    s = c.u
    p = ease_inout(clamp(c.lt / 0.5)) * (ease_inout(clamp((e.d - c.lt) / 0.35)))
    ph = int(c.H * 0.44 * p)
    dy = max(0.0, ph - max(0.0, c.top - 0.05 * c.H))
    if dy > 0.5:
        M = np.float32([[1, 0, 0], [0, 1, dy]])
        c.img = cv2.warpAffine(c.img, M, (c.W, c.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        c.m = cv2.warpAffine(c.m, M, (c.W, c.H), flags=cv2.INTER_LINEAR)
        c.set_face(c.fx, c.fy + dy, c.fw, c.fh, c.top + dy, c.shoulder + dy)
    if ph < 4:
        return
    panel = np.empty((ph, c.W, 3), np.float32)
    broll = e.o.get("images")
    if broll:
        im = e.cards[0] if e.cards else Image.new("RGB", (540, 960), (60, 60, 80))
        k = max(c.W / im.width, c.H * 0.44 / im.height)
        im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
        l, t = (im.width - c.W) // 2, (im.height - int(c.H * 0.44)) // 2
        panel[:] = (np.asarray(im.crop((l, t, l + c.W, t + int(c.H * 0.44))), np.float32) / 255)[:ph]
        c.img[:ph] = panel
        if txt(e, "tag"):
            tg = rrect(int(300 * s), int(96 * s), 20 * s, (255, 255, 255, 255))
            ImageDraw.Draw(tg).text((tg.width / 2, tg.height / 2), txt(e, "tag"), font=font("uib", 46 * s), fill=(24, 24, 28, 255), anchor="mm")
            place(c, shadowed(tg, int(10 * s), int(8 * s), 130), c.W * 0.74, ph - 90 * s, 1.0, -6, clamp((c.lt - 0.5) / 0.2), "front")
        return
    paper = np.float32(c.th.paper) / 255
    c.img[:ph] = paper * 0.97 + 0.03
    lines = lst(e, "text", ["THE ONE THING", "NOBODY TELLS YOU"])[:4]
    hl = txt(e, "hl").lower()
    maxw = c.W * 0.88
    size = int(min(c.H * 0.07, min(fit_text(l.upper(), maxw, "display", 300).height for l in lines) * 0.95))
    y = int(ph * 0.5 - (len(lines) * size * 0.62))
    L = lay(c, c.W, ph)
    if txt(e, "pill"):
        pl = rrect(int(60 * s + font("uib", 30 * s).getlength(txt(e, "pill").upper())), int(54 * s), 27 * s, tuple(c.th.accent2) + (255,))
        ImageDraw.Draw(pl).text((pl.width / 2, pl.height / 2), txt(e, "pill").upper(), font=font("uib", 30 * s), fill=(255, 255, 255, 255), anchor="mm")
        L.alpha_composite(pl, (int(c.W * 0.06), max(6, y - int(70 * s))))
    for i, ln in enumerate(lines):
        words = ln.split(" ")
        img = fit_text(ln.upper(), maxw, "display", int(c.H * 0.08), fill=(22, 22, 24))
        if hl and hl in ln.lower():
            box = rrect(img.width + int(30 * s), img.height + int(6 * s), 10 * s, tuple(c.th.accent) + (255,))
            box.alpha_composite(img, (int(15 * s), int(3 * s)))
            img = box
        L.alpha_composite(img, (int(c.W * 0.06), y + int(i * (size * 1.25))))
    comp(c, L, 0, 0, 1.0, "front")


@effect("phone-fan", "Cards fan out like a hand of phones in front, under a two-line headline.", {"images": "folder of images or clips", "text": "headline lines separated by |"},
        family="cards", depth="guard", images=True, seconds=(2.5, 5.0), intents=("numbers", "case"), aliases=("fan",))
def phone_fan(c, e):
    s = c.u
    n = 5
    deck = _deck_c(c, e, int(c.W * 0.28))
    out = clamp((e.d - c.lt) / 0.25)
    cy = c.H * 0.72
    for i in range(n):
        t0 = i * 0.1
        if c.lt < t0:
            continue
        q = ease_back((c.lt - t0) / 0.4)
        a = (i - (n - 1) / 2) * 15
        place(c, deck[i % len(deck)], c.W / 2 + math.sin(math.radians(a)) * c.W * 0.34 * clamp(q), cy - math.cos(math.radians(a)) * 30 * s + abs(a) * 1.3 * s, 0.75 + 0.25 * clamp(q),
              -a * clamp(q), clamp((c.lt - t0) / 0.12) * out, "guard")
    for j, ln in enumerate(lst(e, "text", ["YOUR REELS,", "ALL IN ONE HAND"])[:2]):
        t = fit_text(ln.upper(), c.W * 0.86, "display", int(120 * s), fill=c.th.paper if j == 0 else c.th.accent, stroke=int(4 * s), stroke_fill=(14, 14, 18), shadow=int(8 * s))
        place(c, t, c.W / 2, c.H * 0.86 + j * t.height * 0.78, 0.8 + 0.2 * ease_back((c.lt - 0.4 - j * 0.15) / 0.3), 0, clamp((c.lt - 0.4 - j * 0.15) / 0.15) * out, "guard")


def _deck_c(c, e, w):
    def build():
        src = e.cards or [Image.new("RGB", (270, 480), (60, 60, 80))]
        own = bool(e.o.get("images"))
        return [card_image(im if own else vary(im, i), w) for i, im in enumerate(src)]
    return cached(e, f"deckc{w}", build)


@effect("receipt", "Instructions print out like a receipt, hanging from the top of the frame behind the head.",
        {"text": "lines separated by |", "total": "the last line (TOTAL: 1 prompt)"}, family="type", depth="behind", matte=True, seconds=(3.0, 6.0), intents=("howto",), aliases=("the-bill",))
def receipt(c, e):
    s = c.u
    lines = lst(e, "text", ["ORDER #1021", "1x hook in 3 seconds", "1x host on screen", "1x proof per claim", "cut the dead air"])
    total = txt(e, "total", "TOTAL: 1 prompt")
    w = int(c.W * 0.5)
    lh = int(58 * s)
    h = int(40 * s) + lh * (len(lines) + 2) + int(40 * s)

    def build():
        im = Image.new("RGBA", (w, h), (248, 246, 238, 255))
        d = ImageDraw.Draw(im)
        for i in range(0, w, int(18 * s)):
            d.polygon([(i, h), (i + int(9 * s), h - int(14 * s)), (i + int(18 * s), h)], fill=(0, 0, 0, 0))
        return im
    base = cached(e, "base", build)
    out = clamp((e.d - c.lt) / 0.25)
    grow = ease_out(clamp(c.lt / (e.d * 0.5)))
    im = base.copy()
    d = ImageDraw.Draw(im)
    f = font("mono", 32 * s)
    shown = min(len(lines) + 1, int(grow * (len(lines) + 1) + 0.999))
    for i in range(shown):
        t = lines[i] if i < len(lines) else total
        yy = int(40 * s) + i * lh
        if i == len(lines):
            d.line([(int(30 * s), yy - int(8 * s)), (w - int(30 * s), yy - int(8 * s))], fill=(30, 30, 30, 255), width=max(2, int(3 * s)))
        d.text((int(34 * s), yy + int(10 * s)), t, font=f, fill=(30, 30, 34, 255))
    vis = int(h * grow)
    crop = im.crop((0, 0, w, max(1, vis)))
    x = _x(c)
    comp(c, shadowed(crop, int(10 * s), int(8 * s), 110), x - crop.width / 2 - int(10 * s) * 2 - 8, -int(10 * s) * 2 - 8 - int(8 * s) + c.H * 0.0, out, "behind")


@effect("cover", "The speaker becomes a magazine cover: masthead behind the head, cover lines around, an issue line and a barcode. look=editorial gives a classic serif cover.",
        {"text": "the masthead", "lines": "cover lines separated by |", "issue": "issue line", "color": "accent colour", "look": "editorial for a serif cover"}, family="frame", depth="mixed", matte=True,
        cover_ok=True, seconds=(2.5, 5.0), intents=("story", "hook"), aliases=("cover-star",),
        looks={"editorial": "a soft warm film look, a serif masthead behind the head, an issue line and elegant cover lines"})
def cover(c, e):
    s = c.u
    editorial = txt(e, "look") == "editorial"
    k = ramp(c, e, 0.4, 0.3)
    accent = col(e, "color", (232, 54, 50) if not editorial else (170, 120, 70))
    if editorial:
        g = grade(c.img, "warm")
        c.img[:] = c.img * (1 - 0.6 * k) + g * 0.6 * k
    vignette(c, 0.22 * k)
    mast = txt(e, "text", "THE EDIT" if not editorial else "Vogue-ish").upper() if not editorial else txt(e, "text", "The Edit")
    kind = "didoneb" if editorial else "display"
    im = cached(e, "mast", lambda: fit_text(mast, c.W * 0.92, kind, 520, fill=c.th.paper if not editorial else (250, 244, 232), shadow=int(8 * s)))
    place(c, im, c.W / 2, max(c.top - im.height * 0.12, im.height * 0.5 + c.H * 0.02), alpha=k * ease_out(c.lt / 0.3), depth="behind")
    issue = txt(e, "issue", "ISSUE 01 · 2026")
    place(c, text_img(issue, 28 * s, "mono", c.th.paper, tracking=0.2, shadow=int(5 * s)), c.W / 2, c.H * 0.045 if c.top > c.H * 0.25 else c.H * 0.97, 1.0, 0, k, "guard")
    lines = lst(e, "lines", ["THE METHOD THEY HIDE", "10 RULES FOR HOOKS", "WHY IT WORKS"])[:4]
    for i, ln in enumerate(lines):
        t0 = 0.35 + i * 0.18
        q = ease_out((c.lt - t0) / 0.3)
        left = i % 2 == 0
        t = text_img(ln, 44 * s, "didoneb" if editorial else "uib", c.th.paper if editorial else (255, 255, 255), stroke=0, shadow=int(7 * s))
        if c.lt > t0:
            x = (c.W * 0.07 + t.width / 2) if left else (c.W * 0.93 - t.width / 2)
            yy = c.H * (0.38 + 0.12 * i) if not editorial else c.H * (0.46 + 0.09 * i)
            if not left:
                x = min(x, c.W - t.width / 2 - c.W * 0.04)
            bar = rrect(int(t.width * q * 0.9), int(8 * s), 4 * s, tuple(accent) + (255,))
            place(c, t, x + (1 - q) * (-60 if left else 60) * s, yy, 1.0, 0, q * k, "guard")
            place(c, bar, x - t.width * (1 - q * 0.9) / 2 * (1 if left else -1) * 0 + (-t.width / 2 + bar.width / 2 if left else t.width / 2 - bar.width / 2), yy + t.height * 0.55, 1.0, 0, q * k, "guard")
    bc = cached(e, "bc", lambda: _barcode(c))
    place(c, bc, c.W * 0.86, c.H * 0.93, 1.0, 0, k, "guard")


def _barcode(c):
    w, h = int(150 * c.u), int(96 * c.u)
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    rng = random.Random(2)
    x = int(8 * c.u)
    while x < w - int(8 * c.u):
        bw = rng.choice([2, 2, 4, 6]) * max(1, int(c.u))
        d.rectangle([x, int(8 * c.u), x + bw, h - int(24 * c.u)], fill=(10, 10, 10, 255))
        x += bw + rng.choice([2, 4]) * max(1, int(c.u))
    d.text((w / 2, h - int(12 * c.u)), "0 12345 67890", font=font("mono", 14 * c.u), fill=(10, 10, 10, 255), anchor="mm")
    return im


# ===================================================================================================================== data cards

def _chart_line(w, h, prog, color, u):
    ys = [0.04, 0.07, 0.10, 0.16, 0.22, 0.35, 0.52, 0.74, 1.0]
    n = max(0.02, (len(ys) - 1) * ease_out(prog))
    pts = []
    for i in range(int(n) + 1):
        t = min(i, n)
        i0 = min(int(t), len(ys) - 2)
        f = t - i0
        pts.append((w * t / (len(ys) - 1), h - h * (ys[i0] + (ys[i0 + 1] - ys[i0]) * f)))
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    if len(pts) < 2:
        return im
    ImageDraw.Draw(im).polygon(pts + [(pts[-1][0], h), (pts[0][0], h)], fill=tuple(color) + (60,))
    gl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(gl).line(pts, fill=tuple(color) + (255,), width=int(34 * u), joint="curve")
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(16 * u)))
    d = ImageDraw.Draw(im)
    d.line(pts, fill=tuple(color) + (255,), width=max(2, int(12 * u)), joint="curve")
    ex, ey = pts[-1]
    d.ellipse([ex - 18 * u, ey - 18 * u, ex + 18 * u, ey + 18 * u], fill=tuple(color) + (90,))
    d.ellipse([ex - 9 * u, ey - 9 * u, ex + 9 * u, ey + 9 * u], fill=(235, 255, 240, 255))
    return im


def _chart_bars(w, h, prog, color, u, vals=(1.0, 0.71, 0.63, 0.42, 0.25, 0.2, 0.19)):
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    bw = w / len(vals)
    for i, v in enumerate(vals):
        g = ease_out(clamp(prog * 1.6 - i * 0.1))
        top = h - h * v * g
        bx = i * bw + bw * 0.16
        if i == 0:
            gl = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle([bx, top, bx + bw * 0.68, h], int(12 * u), fill=tuple(color) + (230,))
            im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14 * u)))
        ImageDraw.Draw(im).rounded_rectangle([bx, top, bx + bw * 0.68, h], int(12 * u), fill=tuple(color) + (230 if i == 0 else 120,))
    return im


def _donut(size, pct, color, label, value, u):
    im = Image.new("RGBA", (int(size), int(size)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    wdt = int(size * 0.13)
    d.arc([wdt, wdt, size - wdt, size - wdt], -90, 270, fill=(255, 255, 255, 50), width=wdt)
    d.arc([wdt, wdt, size - wdt, size - wdt], -90, -90 + 360 * pct, fill=tuple(color) + (255,), width=wdt)
    d.text((size / 2, size * 0.46), value, font=font("uib", size * 0.22), fill=(255, 255, 255, 255), anchor="mm")
    d.text((size / 2, size * 0.64), label, font=font("ui", size * 0.1), fill=(255, 255, 255, 190), anchor="mm")
    return im


def glass_stat(c, e, cx, cy, k, prog, label, value, kind, scale=1.0, depth="front"):
    """A see-through glass stat card: a spaced-caps label, a number counting up, a glowing chart."""
    if k <= 0:
        return
    u = c.u * scale
    w, h = 800 * u * (0.82 + 0.18 * ease_back(k)), 480 * u * (0.82 + 0.18 * ease_back(k))
    x0, y0 = cx - w / 2, cy - h / 2 + 28 * u * (1 - k)
    glass(c, (x0, y0, x0 + w, y0 + h), 54 * u, depth, tint=(235, 255, 240), tint_amt=0.2, alpha=clamp(k * 1.5))
    v = w / 800
    L = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    lab, big = font("uim", 24 * v), font("uib", 92 * v)
    x = 34 * v
    for ch in label.upper():
        d.text((x, 34 * v), ch, font=lab, fill=(255, 255, 255, 235))
        x += lab.getlength(ch) + 5 * v
    txt_ = count_text(value, prog)
    d.text((w - 34 * v - big.getlength(txt_), 22 * v), txt_, font=big, fill=(255, 255, 255, 255))
    gx0, gx1, gy0, gy1 = 34 * v, w - 34 * v, 150 * v, h - 40 * v
    for j in range(3):
        d.line([gx0, gy0 + (gy1 - gy0) * j / 2, gx1, gy0 + (gy1 - gy0) * j / 2], fill=(255, 255, 255, 60), width=max(1, int(2 * v)))
    ch_im = _chart_line(gx1 - gx0, gy1 - gy0, prog, GREEN, v) if kind == "line" else _chart_bars(gx1 - gx0, gy1 - gy0, prog, GREEN, v)
    L.alpha_composite(ch_im, (int(gx0), int(gy0)))
    comp(c, L, x0, y0, clamp(k * 1.5), depth)


@effect("glass-stat", "A liquid-glass stat card under the chin: a label, a number that counts up, a glowing chart. look=bento adds a smoked glass screen behind the head and glass tiles in front.",
        {"text": "the label", "from": "starting number (0)", "to": "the number it counts to (197K, 59%)", "kind": "line | bars", "pos": "above | below (below)", "look": "bento"},
        family="glass", depth="front", seconds=(3.0, 6.0), intents=("numbers", "case"), aliases=("liquid-glass-graph",),
        looks={"bento": "the chart moves to a smoked glass screen behind the head; a donut, a KPI and bars sit in front as glass tiles"})
def glass_stat_fx(c, e):
    k = ease_out(c.lt / 0.45) * clamp((e.d - c.lt) / 0.3)
    prog = clamp((c.lt - 0.3) / (e.d * 0.7))
    to = txt(e, "to", "197K")
    if txt(e, "look") == "bento":
        s = c.u
        sw, sh = c.W * 0.78, c.H * 0.26
        top = c.H * 0.03
        glass(c, (c.W / 2 - sw / 2, top, c.W / 2 + sw / 2, top + sh), 50 * s, "behind", dark=1.0, tint=(30, 40, 50), tint_amt=0.8, alpha=k)
        L = Image.new("RGBA", (int(sw), int(sh)), (0, 0, 0, 0))
        L.alpha_composite(_chart_line(sw - 80 * s, sh - 120 * s, prog, GREEN, s), (int(40 * s), int(90 * s)))
        d = ImageDraw.Draw(L)
        d.text((40 * s, 40 * s), txt(e, "text", "Views").upper(), font=font("uim", 28 * s), fill=(255, 255, 255, 235))
        d.text((sw - 40 * s, 40 * s), count_text(to, prog), font=font("uib", 70 * s), fill=(255, 255, 255, 255), anchor="ra")
        comp(c, L, c.W / 2 - sw / 2, top, k, "behind")
        y = c.chin + 0.02 * c.H
        tiles = [("donut", (0.29, "29%", "share")), ("kpi", ("672K", "total")), ("bars", None)]
        tw = c.W * 0.27
        for i, (kind, data) in enumerate(tiles):
            x0 = c.W / 2 - 1.5 * tw - 16 * s + i * (tw + 16 * s)
            kk = clamp((ease_back(c.lt / 0.5 - i * 0.12)))
            glass(c, (x0, y, x0 + tw, y + tw), 40 * s, "front", tint=(235, 255, 240), tint_amt=0.18, alpha=clamp(kk * 1.5) * clamp((e.d - c.lt) / 0.3))
            T = Image.new("RGBA", (int(tw), int(tw)), (0, 0, 0, 0))
            if kind == "donut":
                T.alpha_composite(_donut(int(tw * 0.86), data[0] * ease_out(prog), GREEN, data[2], data[1], s), (int(tw * 0.07), int(tw * 0.07)))
            elif kind == "kpi":
                dd = ImageDraw.Draw(T)
                dd.text((tw / 2, tw * 0.45), count_text(data[0], prog), font=font("uib", tw * 0.26), fill=(255, 255, 255, 255), anchor="mm")
                dd.text((tw / 2, tw * 0.68), data[1], font=font("ui", tw * 0.1), fill=(255, 255, 255, 190), anchor="mm")
            else:
                T.alpha_composite(_chart_bars(tw * 0.74, tw * 0.6, prog, GREEN, s * 0.5), (int(tw * 0.13), int(tw * 0.2)))
            comp(c, T, x0, y, clamp(kk * 1.5) * clamp((e.d - c.lt) / 0.3), "front")
        return
    w, h = 800 * c.u, 480 * c.u
    cx, cy = dock(c, w, h, txt(e, "pos", "below"), 0.012)
    glass_stat(c, e, cx, cy, k, prog, txt(e, "text", "Views · this reel"), to, txt(e, "kind", "line"))


@effect("corner-push", "The camera pushes into one top corner and a glass stat card pops beside the head, then the other corner with a bar card. The head stays in front.",
        {"text": "two labels separated by |", "to": "two numbers separated by | (197K|672K)", "zoom": "2.0"}, family="glass", depth="mixed", matte=True, camera=True, seconds=(5.0, 9.0),
        intents=("numbers", "case"), aliases=("over-the-shoulder-zoom", "ots"))
def corner_push(c, e):
    p = clamp(c.lt / e.d)
    z0 = min(2.0, num(e, "zoom", 2.0))
    lx, rx = c.fx - c.W * 0.17, c.fx + c.W * 0.19
    keys = [(0.0, (1.0, c.fx)), (0.30, (1.04, c.fx)), (0.46, (z0, lx)), (0.66, (z0 + 0.03, lx)), (0.76, (1.05, c.fx)), (0.87, (z0, rx)), (1.0, (z0 + 0.03, rx))]
    z, x = keyframes(p, keys)
    camera(c, z, x, c.fy)
    k1 = clamp((p - 0.42) / 0.065) * (1 - clamp((p - 0.66) / 0.055))
    k2 = clamp((p - 0.84) / 0.065)
    if k1 <= 0 and k2 <= 0:
        return
    a, b = (lst(e, "text") + ["Views · this reel", "Top reels · total"])[:2]
    va, vb = (lst(e, "to") + ["197K", "672K"])[:2]
    w = 800 * c.u * 0.62
    y = max(c.hy - c.hry * 0.2, 0.2 * c.H)
    glass_stat(c, e, max(w / 2 + 0.03 * c.W, c.hx - c.hrx - w * 0.38), y, k1, clamp((p - 0.45) / 0.17), a, va, "line", 0.62, "behind")
    glass_stat(c, e, min(c.W - w / 2 - 0.03 * c.W, c.hx + c.hrx + w * 0.38), y, k2, clamp((p - 0.86) / 0.14), b, vb, "bars", 0.62, "behind")


@effect("glass-widgets", "Frosted glass widgets float around the head: a stat, a ring, a mini chart, a now-playing pill, and a 'Made with' pill.",
        {"text": "the big number (672K)", "name": "the name on the 'Made with' pill", "handle": "handle on the profile widget"}, family="glass", depth="mixed", matte=True, seconds=(3.0, 6.0),
        intents=("numbers", "story"), aliases=("widgets", "glass"))
def glass_widgets(c, e):
    s = c.u
    out = clamp((e.d - c.lt) / 0.3)
    prog = clamp((c.lt - 0.4) / (e.d * 0.6))
    specs = [(0.16, 0.3, 0.27, 0.16, "stat"), (0.84, 0.32, 0.26, 0.2, "ring"), (0.17, 0.52, 0.28, 0.15, "chart"), (0.82, 0.6, 0.3, 0.1, "music")]
    for i, (fx, fy, fw, fh, kind) in enumerate(specs):
        q = clamp(ease_back(c.lt / 0.45 - i * 0.14))
        if q <= 0:
            continue
        w, h = c.W * fw * (0.85 + 0.15 * q), c.H * fh * (0.85 + 0.15 * q)
        cx, cy = c.W * fx, c.H * fy + math.sin(c.lt * 1.6 + i) * 6 * s
        x0, y0 = cx - w / 2, cy - h / 2
        glass(c, (x0, y0, x0 + w, y0 + h), 40 * s, "behind", tint=(235, 245, 255), tint_amt=0.2, alpha=clamp(q * 1.5) * out)
        T = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
        d = ImageDraw.Draw(T)
        if kind == "stat":
            d.text((24 * s, 22 * s), "VIEWS", font=font("uim", 24 * s), fill=(255, 255, 255, 220))
            d.text((24 * s, h - 24 * s), count_text(txt(e, "text", "672K"), prog), font=font("uib", min(h * 0.5, 84 * s)), fill=(255, 255, 255, 255), anchor="ls")
        elif kind == "ring":
            sz = int(min(w, h) * 0.86)
            T.alpha_composite(_donut(sz, 0.72 * ease_out(prog), GREEN, "goal", count_text("72%", prog), s), (int((w - sz) / 2), int((h - sz) / 2)))
        elif kind == "chart":
            T.alpha_composite(_chart_line(w - 48 * s, h - 60 * s, prog, GREEN, s * 0.6), (int(24 * s), int(34 * s)))
        else:
            d.ellipse([20 * s, h / 2 - 28 * s, 76 * s, h / 2 + 28 * s], fill=tuple(c.th.accent2) + (255,))
            d.text((92 * s, h / 2 - 14 * s), "Now playing", font=font("ui", 24 * s), fill=(255, 255, 255, 200), anchor="ls")
            d.text((92 * s, h / 2 + 22 * s), txt(e, "handle", "Your hook"), font=font("uib", 30 * s), fill=(255, 255, 255, 255), anchor="ls")
        comp(c, T, x0, y0, clamp(q * 1.5) * out, "behind")
    if c.lt > 0.9:
        pill = rrect(int(420 * s), int(72 * s), 36 * s, (28, 28, 34, 235))
        d = ImageDraw.Draw(pill)
        d.text((pill.width / 2, pill.height / 2), "Made with " + txt(e, "name", "your agent"), font=font("uib", 30 * s), fill=(255, 255, 255, 255), anchor="mm")
        place(c, shadowed(pill, int(8 * s), int(6 * s), 120), c.W / 2, c.H * 0.93, 0.9 + 0.1 * ease_back((c.lt - 0.9) / 0.3), 0, clamp((c.lt - 0.9) / 0.15) * out, "guard")


@effect("edit-timeline", "A dark red film look with an editing timeline, a REC timecode and a glowing playhead.", {"text": "title (the cut)", "sub": "subtitle", "tc": "start timecode"},
        family="frame", depth="guard", cover_ok=True, seconds=(3.0, 7.0), intents=("howto", "story"), aliases=("timeline",))
def edit_timeline(c, e):
    s = c.u
    k = ramp(c, e, 0.5, 0.4)
    g = grade(c.img, "film-red")
    sel = 0.85 * k
    c.img[:] = c.img * (1 - sel) + g * sel
    vignette(c, 0.3 * k)
    w, h = int(c.W * 0.88), int(250 * s)
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([0, 0, w - 1, h - 1], int(26 * s), fill=(10, 4, 4, 215), outline=(255, 90, 80, 90), width=2)
    rnd = random.Random(6)
    for r in range(3):
        x = int(24 * s)
        while x < w - int(80 * s):
            cw_ = int(rnd.uniform(90, 230) * s)
            d.rounded_rectangle([x, int(26 * s) + r * int(66 * s), min(w - int(24 * s), x + cw_), int(26 * s) + r * int(66 * s) + int(52 * s)], int(10 * s),
                                fill=(200 + rnd.randint(-30, 30), 50 + rnd.randint(-20, 30), 46, 255 if r != 1 else 210))
            x += cw_ + int(10 * s)
    p = clamp(c.lt / e.d)
    px = int(24 * s + (w - 48 * s) * p)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle([px - int(5 * s), 0, px + int(5 * s), h], fill=(255, 255, 255, 255))
    L.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10 * s)))
    d = ImageDraw.Draw(L)
    d.rectangle([px - int(2 * s), 0, px + int(2 * s), h], fill=(255, 255, 255, 255))
    cy = c.H * 0.76
    comp(c, L, c.W / 2 - w / 2, cy - h / 2, ease_out(c.lt / 0.4) * clamp((e.d - c.lt) / 0.2), "guard")
    secs = c.lt
    tc = f"00:{int(secs):02d}:{int((secs % 1) * c.fps):02d}"
    rec = text_img(("● REC  " + tc), 34 * s, "mono", (255, 90, 80), shadow=int(5 * s))
    place(c, rec, c.W * 0.07 + rec.width / 2, c.H * 0.06 if c.top > c.H * 0.2 else c.H * 0.97, 1.0, 0, k * (0.6 + 0.4 * (int(c.lt * 2) % 2)), "guard")
    if txt(e, "text"):
        t = text_img(txt(e, "text").upper(), 54 * s, "bold", c.th.paper, shadow=int(8 * s), tracking=0.06)
        place(c, t, c.W / 2, cy + h / 2 + 70 * s, 1.0, 0, k, "guard")


@effect("lower-third", "A name-and-title bar slides in at lower left, inside the platform's safe lane.", {"text": "name|title", "color": "accent bar colour"},
        family="ui", depth="guard", seconds=(2.5, 5.0), intents=("news", "case", "story"))
def lower_third(c, e):
    s = c.u
    parts = lst(e, "text", ["Name Surname", "Role · Company"])
    name, title = parts[0], parts[1] if len(parts) > 1 else ""
    colr = col(e, "color", c.th.accent)
    fn, ft = font("uib", 54 * s), font("uim", 34 * s)
    w = int(max(fn.getlength(name), ft.getlength(title)) + 80 * s)
    h = int(150 * s)
    p = ease_out(c.lt / 0.45)
    out = ease_in((e.d - c.lt) / 0.3) if e.d - c.lt < 0.3 else 1.0
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle([0, 0, w - 1, h - 1], int(18 * s), fill=(18, 18, 22, 235))
    d.rounded_rectangle([0, 0, int(14 * s), h - 1], int(7 * s), fill=tuple(colr) + (255,))
    d.text((int(40 * s), int(48 * s)), name, font=fn, fill=(255, 255, 255, 255), anchor="lm")
    d.text((int(40 * s), int(104 * s)), title, font=ft, fill=(190, 190, 205, 255), anchor="lm")
    x0 = lerp(-w, c.W * 0.11, p)
    y0 = min(c.H * 0.62, c.H - 672 * s - h)
    comp(c, shadowed(L, int(10 * s), int(8 * s), 110), x0 - int(10 * s) * 2 - 8, y0 - int(10 * s) * 2 - 8, out, "guard")


@effect("big-number", "A huge number counts up beside the head with a label and a source line. Use for a claim's figure.",
        {"text": "the number (59%, $4.2M)", "label": "what it measures", "source": "the source line", "pos": "below | above | left | right", "color": "number colour"},
        family="data", depth="guard", seconds=(2.5, 5.0), intents=("numbers", "case", "news"))
def big_number(c, e):
    s = c.u
    val = txt(e, "text", "59%")
    colr = col(e, "color", c.th.accent)
    prog = clamp((c.lt - 0.1) / min(1.4, e.d * 0.6))
    n = text_img(count_text(val, prog), 230 * s, "display", colr, stroke=int(6 * s), stroke_fill=(14, 14, 18), shadow=int(12 * s))
    lb = text_img(txt(e, "label", "").upper(), 40 * s, "mono", c.th.paper, tracking=0.12, shadow=int(6 * s)) if txt(e, "label") else None
    sr = text_img(txt(e, "source", ""), 28 * s, "uim", (210, 210, 222), shadow=int(5 * s)) if txt(e, "source") else None
    h = n.height + (lb.height * 1.1 if lb else 0) + (sr.height * 1.3 if sr else 0)
    cx, cy = dock(c, n.width, h, txt(e, "pos", "below"), 0.012)
    out = clamp((e.d - c.lt) / 0.25)
    q = ease_back(c.lt / 0.4)
    place(c, n, cx, cy - h / 2 + n.height / 2, 0.8 + 0.2 * clamp(q), 0, clamp(c.lt / 0.12) * out, "guard")
    y = cy - h / 2 + n.height
    if lb:
        place(c, lb, cx, y + lb.height * 0.4, 1.0, 0, clamp((c.lt - 0.25) / 0.2) * out, "guard")
        bar = rrect(int(lb.width * ease_out((c.lt - 0.3) / 0.4)) + 2, int(6 * s), 3 * s, tuple(colr) + (255,))
        place(c, bar, cx, y + lb.height * 0.95, 1.0, 0, out, "guard")
        y += lb.height * 1.1
    if sr:
        place(c, sr, cx, y + sr.height * 0.9, 1.0, 0, clamp((c.lt - 0.6) / 0.2) * out, "guard")


@effect("quote-card", "A pull-quote card with a big quotation mark, revealed word by word, with an attribution.", {"text": "the quote", "by": "attribution", "pos": "below | above (below)"},
        family="ui", depth="guard", seconds=(3.0, 6.0), intents=("news", "case", "story"))
def quote_card(c, e):
    s = c.u
    quote = txt(e, "text", "Make every number come from code.")
    w = int(c.W * 0.84)
    size = 52 * s
    words = quote.split()
    shown = " ".join(words[: max(1, int(len(words) * clamp((c.lt - 0.2) / (e.d * 0.5)) + 0.999))]) if c.lt > 0.2 else ""
    lines = wrap(quote, w - 100 * s, "serifr", size)
    h = int(len(lines) * size * 1.18 + 150 * s + (40 * s if txt(e, "by") else 0))
    cx, cy = dock(c, w, h, txt(e, "pos", "below"), 0.012)
    out = clamp((e.d - c.lt) / 0.25)
    L = rrect(w, h, 34 * s, (248, 244, 234, 244))
    d = ImageDraw.Draw(L)
    d.text((int(36 * s), int(16 * s)), "“", font=font("didoneb", 150 * s), fill=tuple(c.th.accent2) + (255,))
    yy = int(110 * s)
    flat = shown
    rem = len(flat)
    for ln in wrap(quote, w - 100 * s, "serifr", size):
        part = flat[:len(ln)] if rem > 0 else ""
        flat = flat[len(ln) + 1:]
        rem = len(flat)
        d.text((int(44 * s), yy), part, font=font("serifr", size), fill=(24, 24, 28, 255))
        yy += int(size * 1.18)
    if txt(e, "by"):
        d.text((int(44 * s), yy + int(10 * s)), "— " + txt(e, "by"), font=font("uim", 30 * s), fill=(110, 104, 96, 255))
    place(c, shadowed(L, int(12 * s), int(8 * s), 110), cx, cy, 0.92 + 0.08 * ease_back(c.lt / 0.35), 0, clamp(c.lt / 0.15) * out, "guard")
