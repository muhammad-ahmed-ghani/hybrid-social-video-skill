#!/usr/bin/env python3
"""build_video.py - the faceless route end to end: beat map + voice-over -> master.mp4, with no page to write.

    python3 build_video.py --episode episode --voice episode/vo.wav [--out episode/master.mp4] [--fps 30]
                           [--mix-style pad|warm|pulse] [--no-captions] [--qc]

What it does, in order (every step is a script of its own, run here so nothing is hand-glued):
  1. style      episode/style.json, or `style_lock.py pick` + `build` for the topic and format when it is missing;
  2. timing     `speech_align.py spans` on the voice (skipped when episode/timing.json exists, e.g. from host_assemble.py);
  3. scenes     each beat's `scene` spec (see references/03-beat-map.md) becomes a picture: stat, steps, compare, flow, bars,
                kinetic, terminal or quote, with text fitted inside the safe box at the QA sizes, a slow reframe per beat,
                captions from the voice's own word times, and no flash transitions (templates/faceless/index.html);
  4. render     `render_html.py` (parallel, determinism-checked), `mix_audio.py` (voice untouched, ducked bed, cues on each reveal),
                `encode_master.py`, `captions.py`;
  5. qc         with --qc, `qc_master.py` on the result.
A beat with no `scene` gets a kinetic-type scene from its on_screen_text (or its words), so any beat map builds; write `scene` specs
for the explanatory beats. For a host on screen use the host-plus-overlay route (examples/host-overlay-composition/). Exit 0 ok |
2 usage | 3 a dependency is missing | 1 a step failed (its output is shown).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hx_common import eprint, parse_args  # noqa: E402
from style_lock import STACKS, build as build_style, css, art_style, pick  # noqa: E402

SCENE_LIMITS = {"steps": ("items", 5), "flow": ("nodes", 4), "cycle": ("nodes", 5), "bars": ("items", 5), "kinetic": ("lines", 4), "terminal": ("lines", 6)}
SCENE_TYPES = ("stat", "steps", "compare", "flow", "cycle", "bars", "kinetic", "terminal", "quote")
ICONS = {"sun", "snow", "flame", "drop", "bolt", "coin", "lock", "shield", "check", "cross", "clock", "gear", "loop", "home", "chart", "bulb", "search",
         "cloud", "leaf", "thermo", "arrow", "star", "person", "camera", "mic", "globe"}
TEMPLATE = HERE.parent / "templates" / "faceless" / "index.html"


def _run(cmd: list[str], what: str) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, *[str(c) for c in cmd]], capture_output=True, text=True)
    if r.returncode != 0:
        eprint(f"[build] {what} failed (exit {r.returncode}):\n{(r.stderr or r.stdout).strip()[-900:]}")
    return r


def auto_scene(b: dict) -> dict:
    ost = [x for x in (b.get("on_screen_text") or []) if x]
    return {"type": "kinetic", "lines": ost[:3] if ost else [b["text"]]}


def reveal_times(beat: dict, sc: dict) -> list[float]:
    """Seconds at which each item of a scene appears (the same rule as the page's `when`)."""
    key = {"steps": "items", "flow": "nodes", "cycle": "nodes", "bars": "items"}.get(sc.get("type", ""))
    items = sc.get(key) or []
    words = beat["words"]
    out = []
    for k, it in enumerate(items):
        at = it.get("at") if isinstance(it, dict) else None
        if isinstance(at, int) and at < len(words):
            out.append(words[at]["s"])
        elif isinstance(at, str):
            w = next((w for w in words if at.lower().strip(".,?!") in w["word"].lower()), None)
            out.append(w["s"] if w else beat["s"] + k / max(len(items), 1) * max(0.5, (beat["e"] - beat["s"]) * 0.8))
        else:
            out.append(beat["s"] + k / max(len(items), 1) * max(0.5, (beat["e"] - beat["s"]) * 0.8))
    if sc.get("type") == "stat":
        out = [beat["s"]]
    return out


def _record_provenance(ep: Path, voice: str, lang: str) -> None:
    """When the episode keeps a provenance.json, add what this build used: the speech recogniser and, when voice_render wrote its
    sidecar, the voice (marked draft unless it is a high-quality local voice). Never duplicates an entry."""
    pj = ep / "provenance.json"
    if not pj.is_file():
        return
    have = json.loads(pj.read_text(encoding="utf-8")).get("entries", [])
    add = [sys.executable, str(HERE / "provenance.py"), "add", "--episode", str(ep)]
    if not any(e.get("role") == "stt" for e in have):
        model = "Systran/faster-whisper-base.en" if lang[:2] == "en" else "Systran/faster-whisper-base"
        subprocess.run(add + ["--role", "stt", "--tool", "faster-whisper", "--model", model, "--provider", "local", "--runs", "local",
                              "--used-for", "word timings for captions and picture cues"], capture_output=True)
    side = Path(voice).with_suffix(".json")
    if side.is_file() and not any(e.get("role") == "tts" for e in have):
        v = json.loads(side.read_text(encoding="utf-8"))
        cmd = add + ["--role", "tts", "--tool", v.get("engine", "say"), "--model", v.get("voice", "system voice"), "--provider", "local", "--runs", "local",
                     "--used-for", "narration"]
        if v.get("draft"):
            cmd += ["--draft", "true", "--upgrade", "a Premium or Enhanced local voice, a neural voice or host-native speech"]
        subprocess.run(cmd, capture_output=True)


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h", "no-captions", "qc"})
    if opt.get("help") or opt.get("h") or not opt.get("episode"):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    ep = Path(opt["episode"])
    bm_path = ep / "beatmap.json"
    if not bm_path.is_file():
        eprint(f"{bm_path} is missing")
        return 2
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            eprint(f"{tool} is required")
            return 3
    try:
        import playwright  # noqa: F401
    except ImportError:
        eprint("playwright is required: pip install playwright && playwright install chromium")
        return 3
    bm = json.loads(bm_path.read_text(encoding="utf-8"))
    meta = bm.get("meta", {})
    fps = int(opt.get("fps", meta.get("fps", 30)))
    work = ep / "build"
    work.mkdir(parents=True, exist_ok=True)
    log: dict = {"warnings": []}

    # 1. style: decide, never ask
    sj = ep / "style.json"
    if not sj.is_file():
        top = pick(str(meta.get("topic", "")), str(meta.get("intent", "")), str(meta.get("format", "")), [], [], 1)[0]
        ident = build_style(top["id"])
        sj.write_text(json.dumps(ident, indent=2, ensure_ascii=False))
        (ep / "style.css").write_text(css(ident))
        (ep / "art_style.json").write_text(json.dumps(art_style(ident), indent=2, ensure_ascii=False))
        log["style"] = {"picked": top["id"], "why": top["why"]}
        eprint(f"[build] look picked: {top['id']} ({top['why']}); record it in meta.notes")
    style = json.loads(sj.read_text(encoding="utf-8"))
    if "style" in log:                                                      # this run picked the look: write it into the plan
        meta["style"] = {"name": style.get("name", style["id"]), "family": style["id"]}
        meta["notes"] = (meta.get("notes", "") + f" Look: {style['id']} (picked by style_lock.py: {log.get('style', {}).get('why', 'existing style.json')}).").strip()
        bm["meta"] = meta
        bm_path.write_text(json.dumps(bm, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. timing
    tj = Path(opt["timing"]) if opt.get("timing") not in (None, True) else ep / "timing.json"
    voice = opt.get("voice") if opt.get("voice") not in (None, True) else None
    if not tj.is_file():
        if not voice:
            eprint("--voice FILE is required (or an existing timing.json): the picture follows the voice's own word times")
            return 2
        r = _run([HERE / "speech_align.py", "spans", "--audio", voice, "--beatmap", bm_path, "--out", ep], "word alignment")
        if r.returncode != 0:
            return 1 if r.returncode != 3 else 3
        tj = ep / "timing.json"
    timing = json.loads(tj.read_text(encoding="utf-8"))
    if not voice:
        eprint("--voice FILE is required for the mix")
        return 2

    # 3. scenes -> data.js
    by_id = {b["id"]: b for b in timing["beats"]}
    beats = []
    for b in bm["beats"]:
        tb = by_id.get(b["id"])
        if not tb:
            eprint(f"[build] beat {b['id']} has no timing: re-run the alignment")
            return 1
        sc = b.get("scene") or auto_scene(b)
        if sc.get("type") not in SCENE_TYPES:
            log["warnings"].append(f"beat {b['id']}: unknown scene type {sc.get('type')!r}, drawn as kinetic type")
            sc = auto_scene(b)
        lim = SCENE_LIMITS.get(sc["type"])
        if lim and lim[0] in sc and isinstance(sc[lim[0]], list) and len(sc[lim[0]]) > lim[1] and sc["type"] != "compare":
            log["warnings"].append(f"beat {b['id']}: {sc['type']} shows at most {lim[1]} {lim[0]}; the rest are dropped")
        for key in ("items", "nodes"):                                   # an unknown icon name is drawn as a plain badge: say so
            for it in sc.get(key, []):
                if isinstance(it, dict) and it.get("icon") and it["icon"] not in ICONS:
                    log["warnings"].append(f"beat {b['id']}: unknown icon '{it['icon']}' (one of {', '.join(sorted(ICONS))})")
        times = reveal_times({"s": tb["s"], "e": tb["e"], "words": tb["words"]}, sc)
        if times and sc["type"] != "stat" and (times[0] - tb["s"] > 0.8 or len(set(round(x, 2) for x in times)) < len(times)):
            log["warnings"].append(f"beat {b['id']}: the first item appears {times[0] - tb['s']:.1f} s after the beat starts, or two items share an anchor word: "
                                   "the beat may look empty; set earlier or distinct `at` words")
        beats.append({"id": b["id"], "s": tb["s"], "e": tb["e"], "words": tb["words"], "scene": sc})
    dur = round(max(timing["duration"], beats[-1]["e"]) + 0.9, 2)
    tk = dict(style["tokens"])
    tk.setdefault("panel", "rgba(0,0,0,0.55)")
    fr = style.get("fonts_resolved") or {}
    video = {"duration": dur, "captions": not opt.get("no-captions"),
             "style": {"tokens": tk, "texture": "grid" if style.get("texture", {}).get("kind") == "grid" else "none",
                       "safe": style.get("safe_box_px"),
                       "fonts": {"hero_stack": (fr.get("hero") or {}).get("stack") or STACKS["sans"],
                                 "body_stack": (fr.get("body") or {}).get("stack") or STACKS["sans"], "mono_stack": STACKS["mono"]}},
            "beats": beats}
    (work / "data.js").write_text("window.VIDEO=" + json.dumps(video, ensure_ascii=False) + ";\n", encoding="utf-8")
    shutil.copy(TEMPLATE, work / "index.html")

    # 4. render, mix, encode, captions
    frames = work / "frames"
    r = _run([HERE / "render_html.py", "--page", work / "index.html", "--out", frames, "--fps", fps, "--duration", dur], "frame render")
    if r.returncode != 0:
        return 1
    ticks, hits = [], []
    for b in beats:
        times = reveal_times(b, b["scene"])
        (hits if b["scene"]["type"] == "stat" else ticks).extend(times)
    hits.append(beats[-1]["e"] - 0.1)
    (work / "cues.json").write_text(json.dumps({"ticks": ticks, "hits": hits, "whooshes": []}))
    r = _run([HERE / "mix_audio.py", "--voice", voice, "--duration", dur, "--out", work / "mix.wav", "--cues", work / "cues.json",
              "--style", opt.get("mix-style", "pad")], "audio mix")
    if r.returncode != 0:
        return 1
    mix_info = json.loads(r.stdout.strip().splitlines()[-1])
    out = Path(opt.get("out") or ep / "master.mp4")
    r = _run([HERE / "encode_master.py", "--frames", frames, "--audio", work / "mix.wav", "--out", out, "--fps", fps], "encode")
    if r.returncode != 0:
        return 1
    enc = json.loads(r.stdout.strip().splitlines()[-1])
    _run([HERE / "captions.py", "--timing", tj, "--out", ep / "captions.srt", "--vtt"], "captions")
    _record_provenance(ep, voice, lang=str(meta.get("language_tag") or "en"))
    res = {"master": enc["master"], "seconds": enc["seconds"], "mb": enc["mb"], "loudness_lufs": mix_info.get("output_lufs"),
           "captions": str(ep / "captions.srt"), "scenes": [b["scene"]["type"] for b in beats], **log}
    if opt.get("qc"):
        q = subprocess.run([sys.executable, str(HERE / "qc_master.py"), str(out), "--beatmap", str(bm_path)], capture_output=True, text=True)
        try:
            rep = json.loads(q.stdout)
            res["qc"] = {"ok": rep["ok"], "failures": rep["failures"]}
        except ValueError:
            res["qc"] = {"ok": False, "failures": ["unreadable qc output"]}
        lc = subprocess.run([sys.executable, str(HERE / "layout_check.py"), "--page", str(work / "index.html")], capture_output=True, text=True)
        try:
            lay = json.loads(lc.stdout)
            res["layout"] = {"ok": lay["ok"], "issues": [f"{i['rule']}: {i['text']} ({i['detail']})" for i in lay["issues"]]}
        except ValueError:
            res["layout"] = {"ok": False, "issues": ["layout_check could not run"]}
        res["qc"]["ok"] = res["qc"]["ok"] and res["layout"]["ok"]            # one verdict: the picture QC and the text layout both pass
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
