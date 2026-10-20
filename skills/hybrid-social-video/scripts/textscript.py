#!/usr/bin/env python3
"""textscript.py - facts read from the user's own text, never from a language name.

The skill does not know which language a video is in. The user writes in one or chooses one, and
everything language-dependent is read from the text itself with Unicode properties:

  scripts         which writing systems the letters belong to, and their share
  direction       ltr, rtl or mixed, from each letter's bidirectional class
  unit_mode       how to count speech: 'words', or 'chars' where words are not separated by spaces
  fonts           which installed (or bundled) font files cover every character the video will show

    python3 textscript.py beatmap.json [--fonts DIR]      # JSON on stdout, summary on stderr
    python3 textscript.py --text "any string"             # same, for a quick look

`--fonts DIR` checks the font files in DIR (the ones you will bundle) instead of the system fonts.
Coverage means every character has a glyph. It does not mean the font looks right: render a frame
and look. A font that covers everything because it is a bitmap fallback is listed like any other.

Exit 0 always. Library use: `from textscript import profile, speech_units, needed_codepoints`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Scripts whose words are not separated by spaces: a "word" count is meaningless, so speech is
# counted in characters. Detected from the Unicode character name, so no language list is involved.
UNSEGMENTED = ("CJK", "HIRAGANA", "KATAKANA", "THAI", "LAO", "KHMER", "MYANMAR", "TIBETAN")
_TAG_RE = re.compile(r"\[[^\]]{1,24}\]")  # performance tags such as [pause] are not spoken text
_FONT_EXT = {".ttf", ".otf", ".ttc", ".otc"}


def script_of(ch: str) -> str | None:
    """Unicode script family of a letter (the first word of its character name), else None."""
    if not ch.isalpha():
        return None
    try:
        return unicodedata.name(ch).split(" ")[0]
    except ValueError:
        return None


def is_unsegmented(ch: str) -> bool:
    return script_of(ch) in UNSEGMENTED


def speech_units(text: str) -> int:
    """What a speaker says, counted in units: one per space-separated word, and one per character
    in scripts written without spaces. Tags and pure punctuation are not units."""
    clean = _TAG_RE.sub(" ", text or "")
    n = 0
    for tok in clean.split():
        seg = sum(1 for ch in tok if is_unsegmented(ch))
        rest = "".join(ch for ch in tok if not is_unsegmented(ch))
        n += seg + (1 if re.search(r"\w", rest, re.UNICODE) else 0)
    return n


def profile(texts: list[str]) -> dict:
    """Scripts, direction and counting mode of a set of strings."""
    scripts: Counter = Counter()
    rtl = ltr = 0
    for t in texts:
        for ch in _TAG_RE.sub(" ", t or ""):
            s = script_of(ch)
            if not s:
                continue
            scripts[s] += 1
            bidi = unicodedata.bidirectional(ch)
            if bidi in ("R", "AL"):
                rtl += 1
            elif bidi == "L":
                ltr += 1
    total = sum(scripts.values())
    share = {k: round(v / total, 3) for k, v in scripts.most_common()} if total else {}
    unseg = sum(v for k, v in scripts.items() if k in UNSEGMENTED) / total if total else 0.0
    rtl_share = rtl / (rtl + ltr) if (rtl + ltr) else 0.0
    return {
        "letters": total,
        "scripts": share,
        "dominant_script": next(iter(share), None),
        "direction": "none" if not total else "rtl" if rtl_share >= 0.8 else "ltr" if rtl_share <= 0.05 else "mixed",
        "rtl_share": round(rtl_share, 3),
        "unit_mode": "chars" if unseg >= 0.5 else "mixed" if unseg > 0 else "words",
        "beyond_basic_latin": sum(v for k, v in scripts.items() if k != "LATIN"),
    }


def needs_font_check(texts: list[str]) -> bool:
    """True when any letter lies outside Latin through Latin Extended-B (U+0000 to U+024F): the
    identity fonts cannot be assumed to cover it."""
    return any(script_of(ch) and ord(ch) > 0x24F for t in texts for ch in (t or ""))


def needed_codepoints(texts: list[str], cap: int = 400) -> list[int]:
    """Distinct letters, marks and digits the video will show, as code points (capped)."""
    cps = {ord(ch) for t in texts for ch in _TAG_RE.sub(" ", t or "") if unicodedata.category(ch)[0] in "LMN"}
    return sorted(cps)[:cap]


def _parse_charset(s: str) -> set[int]:
    out: set[int] = set()
    for part in s.split():
        a, _, b = part.partition("-")
        lo, hi = int(a, 16), int(b or a, 16)
        out.update(range(lo, hi + 1))
    return out


def fonts_covering(cps: list[int], fonts_dir: str | None = None) -> list[dict] | None:
    """Fonts that have a glyph for every code point. None when fontconfig is not installed."""
    if not cps:
        return []
    if fonts_dir:
        if not shutil.which("fc-scan"):
            return None
        need, rows = set(cps), []
        for f in sorted(Path(fonts_dir).rglob("*")):
            if f.suffix.lower() not in _FONT_EXT:
                continue
            p = subprocess.run(["fc-scan", "--format", "%{family}|%{style}|%{charset}\n", str(f)],
                               capture_output=True, text=True)
            for line in p.stdout.splitlines():
                fam, _, rest = line.partition("|")
                style, _, cs = rest.partition("|")
                if need <= _parse_charset(cs):
                    rows.append({"family": fam.split(",")[0], "file": str(f), "style": style.split(",")[0]})
                    break
        return rows
    if not shutil.which("fc-list"):
        return None
    pattern = ":charset=" + " ".join(f"{c:x}" for c in cps)
    p = subprocess.run(["fc-list", "--format", "%{family}|%{file}|%{style}\n", pattern], capture_output=True, text=True)
    seen, rows = set(), []
    for line in p.stdout.splitlines():
        fam, _, rest = line.partition("|")
        file, _, style = rest.partition("|")
        key = (fam.split(",")[0], file, style.split(",")[0])
        if key[0].startswith(".LastResort"):  # macOS placeholder font: claims every code point, draws boxes
            continue
        if key not in seen:
            seen.add(key)
            rows.append({"family": key[0], "file": file, "style": key[2]})
    return rows


def beatmap_texts(bm: dict) -> list[str]:
    """Every string the viewer will hear or read: spoken text, on-screen text, overlay content."""
    out: list[str] = []
    for b in bm.get("beats", []):
        out += [b.get("text") or "", b.get("tts_text") or ""]
        ost = b.get("on_screen_text") or []
        out += [ost] if isinstance(ost, str) else [str(x) for x in ost]
        for ov in b.get("overlays") or []:
            out.append(str(ov.get("content", "")) if isinstance(ov, dict) else str(ov))
    return [t for t in out if t]


def main(argv: list[str]) -> int:
    from hx_common import eprint, load_json, parse_args
    pos, opt = parse_args(argv)
    if opt.get("text"):
        texts = [str(opt["text"])]
    elif pos:
        texts = beatmap_texts(load_json(pos[0]))
    else:
        eprint(__doc__)
        return 2
    rep = profile(texts)
    rep["speech_units"] = sum(speech_units(t) for t in texts)
    rep["needs_font_check"] = needs_font_check(texts)
    cps = needed_codepoints(texts)
    rep["code_points"] = len(cps)
    fonts = fonts_covering(cps, opt.get("fonts") if isinstance(opt.get("fonts"), str) else None)
    rep["fonts_covering_all"] = fonts
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    eprint(f"[script] {rep['dominant_script']} | {rep['direction']} | count in {rep['unit_mode']} | "
           + ("fontconfig missing: cannot check fonts" if fonts is None else
              f"{len(fonts)} font file(s) cover all {len(cps)} characters"
              + ("" if fonts else ": none, bundle one that does")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
