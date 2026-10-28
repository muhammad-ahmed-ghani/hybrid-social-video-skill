#!/usr/bin/env python3
"""beatmap_to_brief.py - hand the approved plan to HyperFrames without re-interviewing the user.

    python3 beatmap_to_brief.py episode/beatmap.json --out episode/hf/ [--spans episode/spans.json]
                                [--workflow faceless-explainer] [--tts-text] [--series series/]
                                [--host-video public/host.mp4]

Writes, into --out (a HyperFrames project directory, created by `npx hyperframes init`
BEFORE you copy these in; init refuses a non-empty directory):
  BRIEF.md   the intent document the HyperFrames router reads: when it exists the router
             executes `workflow:` and asks no brief questions. flow=automation and
             storyboard=no because Gate 1 already approved the plan; do not approve it twice.
  SCRIPT.md  the locked narration in HyperFrames' shape: one `## Line N` section per beat
             with Time, Delivery and the indented spoken text.

The vocabulary for `destination`, `angle` and `aspect` is defined by the installed
HyperFrames `brief-contract.md`: if it differs from what is written here, edit BRIEF.md.
Beat ids are the join key: line N in SCRIPT.md is beat id N in beatmap.json.
`meta.language` is required and written through as the user gave it: no language is assumed. The
brief also states the text's direction and the script fonts, both read from the text itself.
A beat with `character` gets a Speaker line, and with --series the voice stored in that
character's passport, so every episode speaks with the same voice.

Each beat's `scene` spec (references/03-beat-map.md) and its `device` become the design asks under "Customizations", with the
beat's seconds from --spans (or timing.json), so HyperFrames draws the same picture the beat map describes.
`--host-video` is for a video that already has a speaking host (host_assemble.py's host.mp4): the workflow becomes
`talking-head-recut` (designed overlays over existing footage, the footage's own audio untouched), the file is listed under Assets as the
master clock, and SCRIPT.md is the transcript to time the overlays to. Unless the HyperFrames skills are installed this file is
just a brief: see references/19-hyperframes.md for connecting HyperFrames first.

Exit 0 ok | 1 beat map unreadable | 2 usage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, load_json, parse_args  # noqa: E402
from hx_common import est_beat_seconds as _est_beat_seconds  # noqa: E402
from textscript import beatmap_texts  # noqa: E402
from textscript import profile as text_profile  # noqa: E402

LABEL = {"hook": "Hook", "context": "Context", "build": "Build", "turn": "Turn",
         "reveal": "Reveal", "payoff": "Payoff", "loop": "Loop", "cold-open": "Cold open",
         "title": "Title", "recap": "Recap", "setup": "Setup", "escalate": "Escalate",
         "punchline": "Punchline", "tag": "Tag", "cliffhanger": "Cliffhanger"}
DELIVERY = {"hook": "Land the claim on the first word; sound from frame 0.",
            "context": "Calm, orienting.", "build": "Steady, one idea per breath.",
            "turn": "Slow slightly, leave the gap.", "reveal": "Hit the number; breath before it.",
            "payoff": "Resolve the hook in one sentence.", "loop": "Echo the opening line.",
            "cold-open": "Already inside the scene; no introduction.", "title": "Say the title once, clean.",
            "recap": "Brisk, one line per earlier event.", "setup": "Plain and quick; plant what the punchline uses.",
            "escalate": "Raise the stakes at the same rhythm.", "punchline": "Land it clean, stop, leave the gap.",
            "tag": "A short button after the laugh.", "cliffhanger": "Stop on the unresolved beat; do not resolve it in the voice."}


def scene_ask(b: dict) -> str:
    """One plain-language design ask for a beat's scene spec, so HyperFrames draws what the beat map describes."""
    sc = b.get("scene")
    if not sc:
        return ""
    t = sc.get("type")
    def txt(x):
        return x.get("text", "") if isinstance(x, dict) else str(x)
    if t == "stat":
        return f"a huge count-up number {sc.get('value')} labelled '{sc.get('label', '')}'"
    if t in ("steps", "flow", "cycle"):
        key = "items" if t == "steps" else "nodes"
        extra = f", centre label '{sc['center']}'" if sc.get("center") else ""
        return f"{t} of " + " -> ".join(txt(i) for i in sc.get(key, [])) + extra
    if t == "compare":
        return f"two columns: '{(sc.get('left') or {}).get('title', '')}' against '{(sc.get('right') or {}).get('title', '')}'"
    if t == "bars":
        return "exact bars from zero: " + ", ".join(f"{txt(i.get('label'))} {i.get('value')}" for i in sc.get("items", []) if isinstance(i, dict))
    if t == "kinetic":
        return "kinetic type: " + " / ".join(txt(i) for i in sc.get("lines", []))
    if t == "terminal":
        return "a terminal typing: " + " then ".join(txt(i) for i in sc.get("lines", []))
    if t == "quote":
        return f"a large quotation: '{sc.get('text', '')}'"
    return str(t)


def brief(bm: dict, workflow: str, lock_state: bool = False, spans: dict | None = None, host_video: str | None = None) -> str:
    m = bm["meta"]
    tp = text_profile(beatmap_texts(bm))
    fonts = m.get("script_fonts") or ({"rtl": m["rtl_font"]} if m.get("rtl_font") else {})
    series = m.get("series") or {}
    beats = bm["beats"]
    overlays = []
    for b in beats:
        for ov in b.get("overlays") or []:
            kind = ov.get("kind") if isinstance(ov, dict) else ov
            content = ov.get("content", "") if isinstance(ov, dict) else ""
            overlays.append(f"- beat {b['id']}: {kind} {content}".rstrip())
        when = ""
        if spans and str(b["id"]) in spans:
            when = f" ({spans[str(b['id'])][0]:.1f}-{spans[str(b['id'])][1]:.1f}s)"
        ask = scene_ask(b)
        if ask:
            overlays.append(f"- beat {b['id']}{when}: {ask}")
        if b.get("device") and not ask:
            overlays.append(f"- beat {b['id']}{when}: device `{b['device']}` ({b.get('visual', '')})")
    assets = []
    for b in beats:
        a = (b.get("assets") or {})
        if a.get("visual"):
            assets.append(f"- {a['visual']} - beat {b['id']} ({b.get('layer')}): {b.get('visual', '')}")
    claims = len(bm.get("claims") or [])
    lines = [
        "---",
        f"workflow: {workflow}",
        "flow: automation",
        "storyboard: no",
        f'message: "{m["thesis"].replace(chr(34), chr(39))}"',
        "destination: vertical-social",
        "aspect: 1080x1920",
        f"language: {m['language']}",
        f"length: {int(m.get('target_seconds', 0))}s",
        f"angle: {m.get('intent', 'concept')}",
        "---",
        "",
        "## Intent",
        "",
        f"{m['topic']}. Approved at Gate 1; the plan below is final. Do not re-plan, re-order or re-write "
        f"the script. Format: {m.get('format')}, style: {m.get('style', {}).get('name', 'see style.json')}.",
    ]
    if series:
        locked = bool(lock_state)
        lines += ["", f"Episode {series.get('episode')} of the series {series.get('id')}. "
                  + ("The look, the cast and the voices are locked: " if locked else
                     "The look and the cast are NOT locked yet, so they may still change, but within this episode keep them identical: ")
                  + "use the series' style files and character passports verbatim, and change nothing about how a character looks "
                  "or sounds.", ""]
    lines += [
        "",
        "## Assets",
        "",
    ]
    if host_video:
        assets.insert(0, f"- {host_video} - the speaking host, already recorded: its own audio is the master clock and plays unchanged; "
                         "design overlays over it, never replace or retime it")
    lines += assets or ["- none supplied beyond the beat map; code-layer beats are built from the plan"]
    lines += ["", "## Customizations", ""]
    lines += overlays or ["- none"]
    lines += [
        "", "## Notes", "",
        "- Source of truth: beatmap.json (beat ids are permanent). Code-layer beats are yours; other layers arrive as files.",
        "- Design: use style.json and style.css verbatim (palette, type, motion verbs). Numbers use tabular figures.",
        "- Every number on screen equals the spoken digit in beatmap.json `text`; text and numbers are never baked into images.",
        f"- {claims} claims are on file; show a source chip with each number for 1.5 s or more.",
        "- Keep hero text, captions and key data inside the platform safe box (x 120-888, y 288-1248; x <= 780 below y 840).",
        "- Report any beat you could not realise instead of substituting another layer.",
        f"- Text direction: {tp['direction']}; dominant script: {tp['dominant_script']}; counted in {tp['unit_mode']}."
        + (" Mirror layouts, isolate opposite-direction runs, never split cursive text into characters." if tp["direction"] in ("rtl", "mixed") else ""),
    ]
    if fonts:
        lines.append("- Script fonts (bundle the files; never fetch at render time): "
                     + ", ".join(f"{k}: {v}" for k, v in fonts.items()))
    return "\n".join(lines) + "\n"


def cast_voices(bm: dict, series_dir: str | None) -> dict:
    """Character id -> (display name, voice string), from the series passports or meta.cast_voices."""
    out = {}
    if series_dir and (Path(series_dir) / "series.json").is_file():
        for c in load_json(Path(series_dir) / "series.json").get("characters", []):
            v = c.get("voice") or {}
            out[c["id"]] = (c.get("name", c["id"]), " ".join(str(x) for x in (v.get("engine"), v.get("voice_id"), v.get("notes")) if x))
    for cid, v in (bm["meta"].get("cast_voices") or {}).items():
        out.setdefault(cid, (cid, str(v)))
    return out


def script(bm: dict, spans: dict | None, use_tts: bool, series_dir: str | None = None) -> str:
    m = bm["meta"]
    cast = cast_voices(bm, series_dir)
    voice = (bm.get("audio") or {}).get("voice", "see beatmap audio.voice")
    out = [f"# SCRIPT - {m['topic']}", "",
           f"**Voice:** {voice}", "**Voice settings:** default",
           f"**Voice direction:** {voice}", "", "---", ""]
    wps = float(m.get("wps", 2.5))
    t = 0.0
    for b in bm["beats"]:
        if spans and str(b["id"]) in spans:
            s0, s1 = spans[str(b["id"])]
        else:
            s0, s1 = t, t + _est_beat_seconds(b, wps)
        t = s1
        text = (b.get("tts_text") if use_tts and b.get("tts_text") else b.get("text", "")).strip()
        speaker = []
        if b.get("character"):
            name, v = cast.get(b["character"], (b["character"], ""))
            speaker = [f"**Speaker:** {name}"] + ([f"**Voice:** {v}"] if v else [])
        out += [f"## Line {b['id']} - {LABEL.get(b.get('role'), 'Beat')} (Frame {b['id']})", "",
                f"**Time:** {s0:.1f} - {s1:.1f}s", *speaker, f"**Delivery:** {DELIVERY.get(b.get('role'), 'Natural.')}", "",
                f"    {text}", ""]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"tts-text"})
    if not pos or not opt.get("out"):
        eprint(__doc__)
        return 2
    try:
        bm = load_json(pos[0])
    except (OSError, json.JSONDecodeError) as exc:
        eprint(f"cannot read {pos[0]}: {exc}")
        return 1
    if not bm["meta"].get("language"):
        eprint("meta.language is required: it is the language the user wrote in, or the one they chose")
        return 1
    fmt = bm["meta"].get("format")
    default_wf = data("formats")["formats"].get(fmt, {}).get("hyperframes_workflow", "general-video")
    spans = None
    if opt.get("spans"):
        spans = {str(s["id"]): (float(s["start"]), float(s["end"])) for s in load_json(opt["spans"])}
    out = Path(opt["out"])
    out.mkdir(parents=True, exist_ok=True)
    locked = False
    if opt.get("series") and (Path(opt["series"]) / "series.json").is_file():
        locked = bool(load_json(Path(opt["series"]) / "series.json").get("locks"))
    workflow = opt.get("workflow") or ("talking-head-recut" if opt.get("host-video") else default_wf)
    (out / "BRIEF.md").write_text(brief(bm, workflow, locked, spans, opt.get("host-video") if opt.get("host-video") not in (None, True) else None), encoding="utf-8")
    (out / "SCRIPT.md").write_text(script(bm, spans, bool(opt.get("tts-text")), opt.get("series")), encoding="utf-8")
    print(json.dumps({"brief": str(out / "BRIEF.md"), "script": str(out / "SCRIPT.md"),
                      "workflow": workflow, "beats": len(bm["beats"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
