#!/usr/bin/env python3
"""style_lock.py - one source of truth for an episode's look.

Writes the same look in the three places that must agree: the code layer's CSS
variables, the AI layer's `art_style` prompt block, and a machine-readable
style.json that the beat map points at. Two layers drifting apart is how a hybrid
video ends up looking like a collage of tools.

    python3 style_lock.py list
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
    ident["color_map"] = colormap or {}
    ident["canvas"] = {"width": 1080, "height": 1920, "fps": 30}
    ident["safe_box_px"] = data("platforms")["safe_zones_1080x1920"]["common_safe_box"]
    return ident


def css(ident: dict) -> str:
    t, f = ident["tokens"], ident["fonts"]
    lines = [":root {"]
    for k, v in t.items():
        lines.append(f"  --{k.replace('_', '-')}: {v};")
    for k, v in ident["text_safe"].items():
        lines.append(f"  --{k.replace('_', '-')}-text: {v};")
    for k, v in ident.get("color_map", {}).items():
        lines.append(f"  --cm-{k.replace('_', '-')}: {v};")
    lines += [f"  --font-hero: '{f['hero'].split(' ')[0]}', sans-serif;",
              f"  --font-body: '{f['body'].split(' ')[0]}', sans-serif;",
              f"  --font-numbers: '{f['numbers_font']}', sans-serif;",
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
    if cmd == "build":
        try:
            ident = build(opt.get("identity", ""), opt.get("accent"), parse_colormap(opt.get("colormap")))
        except KeyError:
            eprint(f"unknown identity '{opt.get('identity')}'. Try: style_lock.py list")
            return 2
        except ValueError as exc:
            eprint(str(exc))
            return 2
        out = Path(opt.get("out", "."))
        out.mkdir(parents=True, exist_ok=True)
        (out / "style.json").write_text(json.dumps(ident, indent=2, ensure_ascii=False))
        (out / "style.css").write_text(css(ident))
        (out / "art_style.json").write_text(json.dumps(art_style(ident), indent=2, ensure_ascii=False))
        print(json.dumps({"identity": ident["id"], "out": str(out), "text_safe": ident["text_safe"],
                          "contrast": ident["contrast"]}))
        return 0
    eprint(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
