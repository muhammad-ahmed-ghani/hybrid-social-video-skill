#!/usr/bin/env python3
"""fx_plan_from_beatmap.py - turn a beat map's overlays into a person_fx plan, timed on the speaker's own words.

    python3 fx_plan_from_beatmap.py episode/beatmap.json --spans episode/spans.json [--words episode/words.json] --out episode/fx_plan.json [--layers host,real]

For every beat whose layer is a person on screen (default host and real), each `overlays` entry becomes an effect:

    stat, count-up, number, counter     -> big-number      (the figure, with the rest of the content as its label)
    chart, line-chart, bar-chart        -> glass-stat
    kicker, title, kinetic              -> word-behind
    quote, pull-quote                   -> quote-card
    lower-third, name                   -> lower-third
    list, checklist, steps              -> task-list
    verdict, stamp                      -> stamp
    chat, message, notification         -> messages
    toggles                             -> toggles
    countdown                           -> count-badge
    timeline                            -> edit-timeline

The overlay's `content` supplies the text; an entry may also carry `"fx": "<effect>"` and any effect options to choose one by hand. An effect
starts on the word that names it (a figure's number in the spoken text) when word times are given, otherwise a third of a second into its beat,
and ends inside the beat. Run `person_fx.py plan` and `check` on the result: the number lint then compares every figure with the beat map's
claims, so a number on screen is always one the video can source. Exit 0 ok | 2 usage.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

KIND = {"stat": "big-number", "count-up": "big-number", "countup": "big-number", "number": "big-number", "counter": "big-number",
        "chart": "glass-stat", "line-chart": "glass-stat", "bar-chart": "glass-stat", "kicker": "word-behind", "title": "word-behind", "kinetic": "word-behind",
        "quote": "quote-card", "pull-quote": "quote-card", "lower-third": "lower-third", "name": "lower-third", "list": "task-list", "checklist": "task-list",
        "steps": "task-list", "verdict": "stamp", "stamp": "stamp", "chat": "messages", "message": "messages", "notification": "messages", "toggles": "toggles",
        "countdown": "count-badge", "timeline": "edit-timeline"}
NUM = re.compile(r"[$€£]?\d[\d,.]*\s?[kKmMbB%]?")


def _options(fx: str, content: str) -> dict:
    m = NUM.search(content)
    if fx == "big-number":
        return {"text": m.group(0).strip() if m else content, "label": (content.replace(m.group(0), "").strip(" :·-—") if m else "")}
    if fx == "glass-stat":
        return {"to": m.group(0).strip() if m else "100%", "text": (content.replace(m.group(0), "").strip(" :·-—") if m else content) or "Total"}
    if fx == "word-behind":
        return {"text": content}
    if fx in ("task-list", "toggles", "messages"):
        return {"text": "|".join(p.strip() for p in re.split(r"[|;]", content) if p.strip())}
    if fx == "lower-third":
        return {"text": content.replace(" - ", "|").replace(" · ", "|")}
    if fx in ("quote-card", "stamp"):
        return {"text": content}
    if fx == "count-badge":
        return {"from": m.group(0).strip() if m else "3"}
    return {"text": content} if content else {}


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("beatmap")
    ap.add_argument("--spans", required=True, help="spans.json from speech_align.py: [{id, start, end}]")
    ap.add_argument("--words", help="word times (words.json or timing.json) to land a figure on the word that says it")
    ap.add_argument("--out", required=True)
    ap.add_argument("--layers", default="host,real", help="beat layers that show a person (default host,real)")
    a = ap.parse_args(argv)
    try:
        bm = json.loads(Path(a.beatmap).read_text(encoding="utf-8"))
        spans = {int(s["id"]): s for s in json.loads(Path(a.spans).read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot read inputs: {exc}", file=sys.stderr)
        return 2
    words = None
    if a.words:
        from person_fx import load_words
        words = load_words(a.words)
    layers = set(a.layers.split(","))
    plan, notes = [], []
    for b in bm.get("beats", []):
        sp = spans.get(int(b["id"]))
        if not sp or b.get("layer") not in layers:
            continue
        for o in b.get("overlays", []) or []:
            fx = o.get("fx") or KIND.get(str(o.get("kind", "")).lower())
            if not fx:
                notes.append(f"beat {b['id']}: overlay kind '{o.get('kind')}' has no person-aware effect; build it as a HyperFrames card")
                continue
            content = str(o.get("content", ""))
            if fx in ("big-number", "glass-stat") and not NUM.search(content):
                fx = "quote-card"          # a 'stat' with no figure in it (a URL, a phrase) reads as a card, not as a number
            entry = {"fx": fx, **_options(fx, content), **{k: v for k, v in o.items() if k not in ("kind", "content", "fx", "shows_number")}}
            beat_len = float(sp["end"]) - float(sp["start"])
            m = NUM.search(content)
            hit = None
            if words and m:
                from person_fx import find_phrase
                hit = find_phrase([w for w in words if sp["start"] - 0.1 <= w["s"] <= sp["end"] + 0.1], m.group(0).strip().rstrip("%"), float(sp["start"]))
            start = (hit[0] - 0.15) if hit else float(sp["start"]) + 0.35
            entry["start"] = round(max(float(sp["start"]), start), 3)
            entry["end"] = round(min(float(sp["end"]) + 0.2, entry["start"] + max(1.6, min(4.0, beat_len - 0.2))), 3)
            plan.append(entry)
    out = {"schema": "hybrid-fx/1", "source": Path(a.beatmap).name, "note": "; ".join(notes) or "generated from the beat map overlays", "effects": plan}
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(plan)} effects -> {a.out}")
    for n in notes:
        print("  note:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
