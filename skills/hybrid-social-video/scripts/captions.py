#!/usr/bin/env python3
"""captions.py - an SRT (and optionally VTT) caption file from word timings, in any language.

    python3 captions.py --timing episode/timing.json --out episode/captions.srt [--vtt] [--max-chars 24] [--max-words 4]

timing.json is what host_assemble.py or `speech_align.py spans` writes. Cues break after punctuation, at a maximum of
--max-words words and --max-chars characters (so they fit the safe box at the caption size), and never leave a one-word
orphan before a punctuation break. A cue starts at its first word and ends where the next starts (the last holds 0.4 s after
its word), so the file matches what the video burns in. Deliver it with every video (SKILL.md, Deliver). Exit 0 ok | 2 usage.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402


def chunks(words: list[dict], max_words: int = 4, max_chars: int = 24) -> list[list[dict]]:
    out: list[list[dict]] = []
    cur: list[dict] = []
    n = 0
    for w in words:
        if cur and (len(cur) >= max_words or n + len(w["word"]) + 1 > max_chars):
            out.append(cur)
            cur, n = [], 0
        cur.append(w)
        n += len(w["word"]) + 1
        if re.search(r"[.?!…]$", w["word"]) or (re.search(r"[,:;]$", w["word"]) and len(cur) >= 2):     # a comma never leaves a one-word cue
            out.append(cur)
            cur, n = [], 0
    if cur:
        out.append(cur)
    return out


def stamp(x: float, comma: bool = True) -> str:
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{',' if comma else '.'}{ms:03}"


def cues(timing: dict, max_words: int, max_chars: int) -> list[tuple[float, float, str]]:
    allw = [w for b in timing["beats"] for w in b["words"]]
    cs = chunks(allw, max_words, max_chars)
    out = []
    for k, c in enumerate(cs):
        st = c[0]["s"]
        en = cs[k + 1][0]["s"] if k + 1 < len(cs) else c[-1]["e"] + 0.4
        out.append((st, max(en, st + 0.2), " ".join(w["word"] for w in c)))
    return out


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"vtt", "help", "h"})
    if opt.get("help") or opt.get("h") or not (opt.get("timing") and opt.get("out")):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    timing = json.loads(Path(opt["timing"]).read_text(encoding="utf-8"))
    cs = cues(timing, int(opt.get("max-words", 4)), int(opt.get("max-chars", 24)))
    out = Path(opt["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{t}\n" for i, (a, b, t) in enumerate(cs, 1)), encoding="utf-8")
    if opt.get("vtt"):
        out.with_suffix(".vtt").write_text("WEBVTT\n\n" + "\n".join(f"{stamp(a, False)} --> {stamp(b, False)}\n{t}\n" for a, b, t in cs), encoding="utf-8")
    print(json.dumps({"cues": len(cs), "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
