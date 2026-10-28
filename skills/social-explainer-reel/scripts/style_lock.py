#!/usr/bin/env python3
"""style_lock.py - one source of truth for an episode's look.

Writes the same look in the three places that must agree: the code layer's CSS
variables, the AI layer's `art_style` prompt block, and a machine-readable
style.json that the beat map points at. Two layers drifting apart is how a hybrid
video ends up looking like a collage of tools.

    python3 style_lock.py list
    python3 style_lock.py pick  --topic "compound interest for beginners" [--intent finance] [--format data-story] [--avoid blueprint] [--recent episodes/] [--brand "#E4572E"] [--n 3]
    python3 style_lock.py build --identity paper-collage --out episode/
    python3 style_lock.py build --identity swiss-grid --accent "#0057B8" --out episode/
    python3 style_lock.py build --identity blueprint --colormap "main=#7FDBFF,key=#FFD166,naive=#FF6B6B" --out episode/
    python3 style_lock.py contrast --fg "#E4572E" --bg "#F4EBDD"

`build --colormap name=#hex,...` writes a concept-to-colour map (maths and science: one
colour per concept, reused for every shape, label and equation term, never reassigned);
it is exported as `--cm-<name>` CSS variables and `color_map` in style.json.
`build --accent HEX` replaces the identity's accent with a brand colour. If that
colour fails 4.5:1 as text on the background, a text-safe variant is derived (same
hue, lightness stepped until it passes). The accent itself stays for fills.

`pick` chooses a look for you, so the agent never has to ask and never defaults to the same one: it scores the identities by
topic register (the groups in references/04-style-bible.md "Choosing"), fixes the look when the format defines it (vox-collage
is paper-collage, flat-vector-motion is flat-vector), and then spreads videos apart: anything in `--avoid` or already used by a
`style.json` under `--recent` is excluded, and a candidate whose background sits in the same colour family as the most recent
look is penalised, so a run of videos does not drift into one palette. A brand colour (`--brand`) does not change the pick: it is
the accent, applied with `build --accent`. The same topic always gets the same ranking; different topics spread. It prints the
ranked picks with the reason for each; take the first and record it, with why, in `meta.notes`. With `--format` the pick is limited to
the looks that format's doc allows (data/formats.json `looks`). `build` resolves each identity font against what is installed and
falls back to a same-class system stack (a serif look stays serif), reporting what it did in `fonts_not_installed`.

Outputs in --out: style.json, style.css, art_style.json.
Exit 0 ok | 2 usage / unknown identity.
"""
from __future__ import annotations

import colorsys
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, parse_args  # noqa: E402

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(h: str) -> float:
    r, g, b = (_lin(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def text_safe_variant(color: str, bg: str, target: float = 4.5) -> str:
    """Step the colour's lightness away from the background until it meets `target`."""
    if contrast(color, bg) >= target:
        return color.upper()
    r, g, b = _rgb(color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    direction = -1 if luminance(bg) > 0.4 else 1  # darken on light canvases, lighten on dark
    for _ in range(100):
        l = min(max(l + direction * 0.01, 0.0), 1.0)
        rr, gg, bb = colorsys.hls_to_rgb(h, l, s)
        cand = "#{:02X}{:02X}{:02X}".format(round(rr * 255), round(gg * 255), round(bb * 255))
        if contrast(cand, bg) >= target:
            return cand
    return "#000000" if direction < 0 else "#FFFFFF"


def parse_colormap(raw: str | None) -> dict:
    out: dict = {}
    for pair in (raw or "").split(","):
        if not pair.strip():
            continue
        name, _, val = pair.partition("=")
        if not HEX.match(val.strip()):
            raise ValueError(f"--colormap entry '{pair}' needs name=#RRGGBB")
        out[name.strip()] = val.strip().upper()
    return out


def build(identity_id: str, accent: str | None = None, colormap: dict | None = None) -> dict:
    ids = data("identities")["identities"]
    if identity_id not in ids:
        raise KeyError(identity_id)
    ident = json.loads(json.dumps(ids[identity_id]))  # deep copy
    tokens = ident["tokens"]
    on = ident.get("text_safe_on", "bg")
    if accent:
        if not HEX.match(accent):
            raise ValueError("--accent must be #RRGGBB")
        tokens["accent"] = accent.upper()
        ident["text_safe"].pop("accent", None)
    safe = dict(ident.get("text_safe", {}))
    base_bg = tokens[on]
    for name in ("accent", "accent2"):
        if name not in safe and contrast(tokens[name], base_bg) < 4.5:
            safe[name] = text_safe_variant(tokens[name], base_bg)
    ident["text_safe"] = safe
    ident["contrast"] = {
        "ink_on_bg": round(contrast(tokens["ink"], tokens["bg"]), 2),
        "muted_on_bg": round(contrast(tokens["muted"], tokens["bg"]), 2),
        "accent_on_bg": round(contrast(tokens["accent"], base_bg), 2),
        "accent2_on_bg": round(contrast(tokens["accent2"], base_bg), 2),
        "text_safe_on": on,
    }
    ident["id"] = identity_id
    ident["fonts_resolved"] = resolve_fonts(ident)
    ident["color_map"] = colormap or {}
    ident["canvas"] = {"width": 1080, "height": 1920, "fps": 30}
    ident["safe_box_px"] = data("platforms")["safe_zones_1080x1920"]["common_safe_box"]
    return ident


# topic keyword groups -> identities, from references/04-style-bible.md "Choosing" (order = preference)
REGISTERS = [
    (("finance", "money", "economy", "economics", "news", "policy", "election", "law", "market", "invest", "interest", "tax", "inflation"),
     ["newsroom", "editorial-serif", "swiss-grid"]),
    (("software", "ai", "code", "developer", "security", "agent", "api", "github", "model", "cyber", "cloud", "data"),
     ["tech-terminal", "glass-keynote", "neo-brutalist"]),
    (("science", "how", "works", "mechanism", "biology", "space", "physics", "engineering", "energy", "body", "brain", "climate"),
     ["flat-vector", "blueprint", "whiteboard-doodle"]),
    (("culture", "history", "food", "art", "story", "people", "travel", "music", "language", "city"),
     ["paper-collage", "risograph", "editorial-serif"]),
    (("host", "opinion", "creator", "shorts", "startup", "hot", "take", "tips", "habit", "productivity", "career"),
     ["creator-shorts", "neo-brutalist", "halftone-pop"]),
    (("product", "premium", "luxury", "brand", "design", "fashion", "launch", "car", "watch"),
     ["dark-luxe", "glass-keynote"]),
    (("learn", "lesson", "tutorial", "step", "explain", "beginner", "basics", "school", "math"),
     ["whiteboard-doodle", "flat-vector", "swiss-grid"]),
]
FORMAT_LOOK = {"vox-collage": "paper-collage", "flat-vector-motion": "flat-vector"}


def format_looks(fmt: str) -> list[str]:
    """Identities the format's doc allows (data/formats.json `looks`); empty means any."""
    return list((data("formats")["formats"].get(fmt) or {}).get("looks") or [])


def hue_family(hexcolor: str) -> str:
    """Coarse colour family of a background: dark, light, or a hue name. Used to spread consecutive videos apart."""
    r, g, b = _rgb(hexcolor)
    h, sat, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.16:
        return "dark"
    if sat < 0.12:
        return "light" if v > 0.6 else "dark"
    deg = h * 360
    for name, lo, hi in (("red", 345, 360), ("red", 0, 20), ("orange", 20, 50), ("yellow", 50, 70), ("green", 70, 170), ("blue", 170, 265), ("purple", 265, 345)):
        if lo <= deg < hi:
            return name
    return "other"


def recent_identities(root: str | None) -> list[str]:
    """Identity ids of the style.json files under `root`, newest first (the looks already used)."""
    if not root:
        return []
    found = []
    for p in Path(root).rglob("style.json"):
        try:
            found.append((p.stat().st_mtime, json.loads(p.read_text()).get("id")))
        except (OSError, ValueError):
            continue
    return [i for _, i in sorted(found, reverse=True) if i]


def pick(topic: str, intent: str = "", fmt: str = "", avoid: list[str] | None = None, recent: list[str] | None = None, n: int = 3) -> list[dict]:
    import hashlib
    ids = data("identities")["identities"]
    avoid, recent = set(avoid or []), list(recent or [])
    if fmt in FORMAT_LOOK:
        return [{"id": FORMAT_LOOK[fmt], "score": 10.0, "why": f"the {fmt} format defines its look"}]
    allowed = set(format_looks(fmt))
    words = set(re.findall(r"[a-z]+", f"{topic} {intent} {fmt}".lower()))
    last_family = hue_family(ids[recent[0]]["tokens"]["bg"]) if recent and recent[0] in ids else None
    rows = []
    for iid, ident in ids.items():
        score, why = 0.0, []
        for keys, prefs in REGISTERS:
            hit = sorted(words & set(keys))
            if hit and iid in prefs:
                score += (3.0 - 0.6 * prefs.index(iid)) * min(len(hit), 2)
                why.append(f"register match ({', '.join(hit)})")
        reg = set(re.findall(r"[a-z]+", ident["register"].lower())) & words
        if reg:
            score += 0.8 * len(reg)
            why.append("topic words in its register")
        if iid in avoid or (allowed and iid not in allowed):
            continue
        if allowed:
            why.append(f"allowed for {fmt}")
        if iid in recent:
            score -= 4.0
            why.append("already used in a recent video")
        if last_family and hue_family(ident["tokens"]["bg"]) == last_family:
            score -= 3.5
            why.append(f"same {last_family} colour family as the last look")
        score += int(hashlib.sha256(f"{topic}|{iid}".encode()).hexdigest()[:6], 16) / 0xFFFFFF * 0.5  # spreads topics apart, repeatable
        rows.append({"id": iid, "score": round(score, 2), "why": "; ".join(why) or "general fit"})
    rows.sort(key=lambda r: -r["score"])
    return rows[:max(1, n)]


SERIF = ("fraunces", "playfair", "newsreader", "source serif", "instrument serif", "dm serif", "georgia", "lora", "merriweather")
MONO = ("mono", "jetbrains", "share tech", "courier", "code")
CONDENSED = ("oswald", "anton", "bebas", "league gothic", "barlow condensed", "roboto condensed", "archivo black", "lilita")
HAND = ("caveat", "patrick hand", "permanent marker", "bangers", "architects daughter", "luckiest")
STACKS = {
    "serif": '"Georgia", "Times New Roman", serif',
    "mono": '"Menlo", "Andale Mono", "Courier New", monospace',
    "condensed": '"Avenir Next Condensed", "Arial Narrow", "Impact", sans-serif',
    "hand": '"Marker Felt", "Chalkboard SE", "Bradley Hand", cursive',
    "sans": '"Avenir Next", "Helvetica Neue", "Arial", sans-serif',
}


def _installed_families() -> set[str]:
    import shutil
    import subprocess
    if not shutil.which("fc-list"):
        return set()
    try:
        out = subprocess.run(["fc-list", "--format", "%{family}\\n"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return set()
    return {f.strip().casefold() for line in out.splitlines() for f in line.split(",") if f.strip()}


def font_class(name: str) -> str:
    n = name.lower()
    for key, group in (("hand", HAND), ("condensed", CONDENSED), ("mono", MONO), ("serif", SERIF)):
        if any(g in n for g in group):
            return key
    return "sans"


def resolve_fonts(ident: dict, installed: set[str] | None = None) -> dict:
    """For each of hero/body/numbers: the identity's font if installed, else the first installed alternate, else a generic
    stack of the same class (serif stays serif). `use` is what the css puts first; `installed` says whether it is the real one."""
    installed = _installed_families() if installed is None else installed
    f = ident["fonts"]
    out = {}
    for role, key in (("hero", "hero"), ("body", "body"), ("numbers", "numbers_font")):
        primary = re.sub(r"\s+(\d{3}|uppercase|italic|bold|regular)\b.*$", "", str(f[key]).split("(")[0].strip(), flags=re.I)
        alts = [re.sub(r"\s*\(.*$", "", a).strip() for a in f.get("alternates", [])]
        chosen, real = None, False
        for cand in [primary] + alts:
            if cand and cand.casefold() in installed:
                chosen, real = cand, True
                break
        stack = STACKS[font_class(primary)]
        out[role] = {"wanted": primary, "use": chosen or primary, "installed": real,
                     "stack": (f'"{chosen}", ' if chosen else "") + stack}
    return out


def css(ident: dict) -> str:
    t, f = ident["tokens"], ident["fonts"]
    lines = [":root {"]
    for k, v in t.items():
        lines.append(f"  --{k.replace('_', '-')}: {v};")
    for k, v in ident["text_safe"].items():
        lines.append(f"  --{k.replace('_', '-')}-text: {v};")
    for k, v in ident.get("color_map", {}).items():
        lines.append(f"  --cm-{k.replace('_', '-')}: {v};")
    fr = ident.get("fonts_resolved") or resolve_fonts(ident)
    lines += [f"  --font-hero: {fr['hero']['stack']};",
              f"  --font-body: {fr['body']['stack']};",
              f"  --font-numbers: {fr['numbers']['stack']};",
              "  font-variant-numeric: tabular-nums;", "}"]
    tex = ident["texture"]
    if tex["kind"] == "noise":
        lines += [
            "/* static grain: bake anti-banding noise as a fixed pattern, not an animated one */",
            ".grain { position: absolute; inset: 0; pointer-events: none; z-index: 99; "
            f"opacity: {tex['opacity']}; mix-blend-mode: {tex['blend']};",
            "  background-image: url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
            "width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' "
            "numOctaves='2' seed='4' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  "
            "0 0 0 0 0  0 0 0 .55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\"); }",
        ]
    lines.append(f"/* safe box for hero, captions and key data: x {ident['safe_box_px']['x']}-"
                 f"{ident['safe_box_px']['x'] + ident['safe_box_px']['w']}, y {ident['safe_box_px']['y']}-"
                 f"{ident['safe_box_px']['y'] + ident['safe_box_px']['h']} */")
    if ident["fonts"].get("no_tabular"):
        lines.append(f"/* no tabular figures in: {', '.join(ident['fonts']['no_tabular'])}; "
                     "animate numbers in --font-numbers */")
    return "\n".join(lines) + "\n"


def art_style(ident: dict) -> dict:
    t = ident["tokens"]
    palette = [t[k] for k in ("bg", "surface", "ink", "accent", "accent2") if k in t]
    return {
        "reference_image_role": "STYLE SWATCH ONLY. Match medium, palette, texture and mood. "
                                "Do not copy its subject, composition, pose or any text.",
        "art_style": dict(ident["ai_art_style"], color_palette=palette),
        "rules": ["no text, letters, numbers, logos, watermarks or signage anywhere",
                  "no flags, emblems or uniforms other than those named in the visual anchor",
                  "same light, grain and palette as every other frame of this reel"],
    }


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv)
    if not pos:
        eprint(__doc__)
        return 2
    cmd = pos[0]
    if cmd == "list":
        for k, v in data("identities")["identities"].items():
            print(f"{k:18s} {v['name']}  [{v['register']}]")
        return 0
    if cmd == "contrast":
        if not (HEX.match(opt.get("fg", "")) and HEX.match(opt.get("bg", ""))):
            eprint("--fg and --bg must be #RRGGBB")
            return 2
        r = contrast(opt["fg"], opt["bg"])
        print(json.dumps({"ratio": round(r, 2), "aa_text": r >= 4.5, "aa_large_text": r >= 3.0,
                          "non_text_ui": r >= 3.0}))
        return 0
    if cmd == "pick":
        if not (opt.get("topic") or opt.get("intent") or opt.get("format")):
            eprint("--topic (or --intent / --format) is required")
            return 2
        avoid = [x for x in str(opt.get("avoid", "")).split(",") if x and x is not True]
        recent = recent_identities(opt.get("recent") if opt.get("recent") is not True else None)
        picks = pick(str(opt.get("topic", "")), str(opt.get("intent", "")), str(opt.get("format", "")), avoid, recent, int(opt.get("n", 3)))
        out = {"picks": picks, "avoided": avoid, "recent": recent[:5]}
        if opt.get("brand") not in (None, True):
            out["brand_accent"] = opt["brand"].upper() if HEX.match(opt["brand"]) else None
            out["note"] = "apply the brand colour with: style_lock.py build --identity <pick> --accent " + str(opt["brand"])
        print(json.dumps(out, indent=2))
        return 0
    if cmd == "build":
        try:
            ident = build(opt.get("identity", ""), opt.get("accent"), parse_colormap(opt.get("colormap")))
        except KeyError:
            eprint(f"unknown or missing --identity '{opt.get('identity')}'. Choose one with `style_lock.py pick --topic ... --format ...` "
                   "(or `list`); build_video.py picks and builds one itself when episode/style.json is missing")
            return 2
        except ValueError as exc:
            eprint(str(exc))
            return 2
        out = Path(opt.get("out", "."))
        out.mkdir(parents=True, exist_ok=True)
        (out / "style.json").write_text(json.dumps(ident, indent=2, ensure_ascii=False))
        (out / "style.css").write_text(css(ident))
        (out / "art_style.json").write_text(json.dumps(art_style(ident), indent=2, ensure_ascii=False))
        missing = [f"{r['wanted']} -> {r['use'] if r['installed'] else 'a ' + font_class(r['wanted']) + ' system stack'}"
                   for r in ident["fonts_resolved"].values() if not r["installed"]]
        print(json.dumps({"identity": ident["id"], "out": str(out), "text_safe": ident["text_safe"],
                          "contrast": ident["contrast"], "fonts_not_installed": missing}))
        if missing:
            eprint("[style] fonts not installed here, same-class system stacks are used: " + "; ".join(missing))
        return 0
    eprint(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
