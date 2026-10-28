#!/usr/bin/env python3
"""person_fx.py - effects that know where the speaker is: type behind the head, graphics that follow the face, camera moves, light, UI cards.

    python3 person_fx.py list [--family cards] [--json]                       # the effects and their options
    python3 person_fx.py words   host.mp4 [--out host.words.json] [--lang en]  # word times, so an effect can land on a word
    python3 person_fx.py plan    plan.json host.mp4 [--words host.words.json]  # resolve word cues to seconds and lint, no render
    python3 person_fx.py check   plan.json host.mp4 outdir [--at 4.5,9] [--platform tiktok]   # still frames, a contact sheet and the audit
    python3 person_fx.py render  plan.json host.mp4 out.mp4 [--width 1080] [--style style.json] [--crf 17]
    python3 person_fx.py one orbit host.mp4 out.mp4 --start 3 --end 6 [--text "..."] [--opt key=value]   # a single effect, no plan file
    python3 person_fx.py doctor [--fetch]                                     # what is missing; --fetch downloads the models and fonts (about 28 MB, once)
    python3 person_fx.py catalog [--write]                                    # data/effects.json from the registry

A plan (hybrid-fx/1) is {"effects": [{"fx": "word-behind", "on": "never wrong", "dur": 2.4, "text": "EXACT"}, {"fx": "orbit", "start": 3, "end": 6}]}.
`on` is a phrase the speaker says (needs word times); `lead` shifts it (default -0.15 s); `until` ends the effect on another phrase; start/end
are plain seconds. Effects that move the camera run first; the rest in plan order. The soundtrack is copied untouched.

Tracking (person_track.py) runs once per clip and is cached. `check` renders one frame per effect, measures how much of the head each front layer
covers and whether graphics enter the platform's UI bands, and exits 1 on a covered face: fix the plan, do not ship it.
Exit 0 ok | 1 audit failed | 2 usage or plan error | 3 missing dependency.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as exc:     # noqa: BLE001
    print(f"person_fx needs numpy, opencv-python and Pillow ({exc}): pip install numpy opencv-python pillow onnxruntime", file=sys.stderr)
    raise SystemExit(3)

import fx_assets                  # noqa: E402
import fx_core                    # noqa: E402
import fx_registry                # noqa: E402
import fx_looks                   # noqa: E402,F401  (registers the effects)
import fx_ui                      # noqa: E402,F401
import person_track               # noqa: E402
from fx_core import Ctx, Theme    # noqa: E402
from fx_registry import ALIASES, EFFECTS, Fx   # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
LOOK_NAMES = {"glitter-spotlight": ("spotlight", "sparkle")}


# ------------------------------------------------------------------------------------------------------------------- words

_WORD = re.compile(r"[^\w']+", re.U)


def _tok(s: str) -> list[str]:
    return [t for t in _WORD.sub(" ", str(s).lower()).split() if t]


def load_words(path) -> list[dict]:
    """Word times from a flat list ({word|w|text, s|start, e|end}) or from a timing.json ({beats: [{words: [...]}]}); [{t, s, e}] out."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = [w for b in d["beats"] for w in b.get("words", [])] if isinstance(d, dict) and "beats" in d else (d.get("words", d) if isinstance(d, dict) else d)
    out = []
    for w in raw:
        t = w.get("word") or w.get("w") or w.get("text") or ""
        s = w.get("s", w.get("start"))
        e = w.get("e", w.get("end"))
        for tk in _tok(t):
            out.append({"t": tk, "s": float(s), "e": float(e if e is not None else s)})
    return out


def find_phrase(words, phrase, after=0.0):
    """(first word start, last word end, how sure 0..1) of the phrase in the word list at or after `after`, by exact then fuzzy match."""
    want = _tok(phrase)
    if not want or not words:
        return None
    toks = [w["t"] for w in words]
    n = len(want)
    for i in range(len(toks) - n + 1):
        if words[i]["s"] >= after - 0.05 and toks[i:i + n] == want:
            return words[i]["s"], words[i + n - 1]["e"], 1.0
    best = (0.0, None)
    for i in range(len(toks) - n + 1):
        if words[i]["s"] < after - 0.05:
            continue
        r = difflib.SequenceMatcher(None, want, toks[i:i + n]).ratio()
        if r > best[0]:
            best = (r, i)
    if best[1] is not None and best[0] >= 0.72:
        i = best[1]
        return words[i]["s"], words[i + n - 1]["e"], best[0]
    return None


def transcribe(video: str, lang: str | None = None) -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("person_fx words needs faster-whisper (pip install faster-whisper)")
    names = ["base.en", "base"] if (lang or "en") == "en" else ["base", "small"]
    model, last = None, None
    for nm in names:
        try:
            model = WhisperModel(nm, device="cpu", compute_type="int8")
            break
        except Exception as exc:    # not cached and offline: try the next size
            last = exc
    if model is None:
        raise SystemExit(f"no speech model could be loaded: {last}")
    segs, _ = model.transcribe(video, word_timestamps=True, vad_filter=True, **({"language": lang} if lang else {}))
    return [{"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for s in segs for w in (s.words or [])]


# -------------------------------------------------------------------------------------------------------------------- plan

def load_plan(path) -> tuple[list[dict], dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8")) if not isinstance(path, (dict, list)) else path
    meta = {k: v for k, v in d.items() if k != "effects"} if isinstance(d, dict) else {}
    return [dict(x) for x in (d["effects"] if isinstance(d, dict) else d)], meta


def canon(name: str) -> tuple[str, str | None]:
    n = str(name).lower().lstrip("/").strip().replace("_", "-")
    if n in LOOK_NAMES:
        return LOOK_NAMES[n]
    return ALIASES.get(n, n), None


def resolve_plan(plan: list[dict], words: list[dict] | None, dur: float) -> tuple[list[dict], list[dict]]:
    """Canonical names, word cues turned into seconds. Returns (plan, issues); each issue is {level, fx, msg}."""
    issues, out = [], []
    for i, raw in enumerate(plan):
        d = dict(raw)
        name, look = canon(d.get("fx", ""))
        d["fx"] = name
        if look:
            d.setdefault("look", look)

        def bad(level, msg, _n=name, _i=i):
            issues.append({"level": level, "fx": _n, "index": _i, "msg": msg})

        if name not in EFFECTS:
            near = difflib.get_close_matches(name, list(EFFECTS) + list(ALIASES), n=3)
            bad("error", f"unknown effect '{name}'" + (f"; did you mean {', '.join(near)}?" if near else ""))
            continue
        spec = EFFECTS[name]
        after = float(d.get("after", 0.0))
        if "on" in d and d.get("start") is None:
            hit = find_phrase(words or [], d["on"], after) if words else None
            if not words:
                bad("error", f"'on' needs word times (run: person_fx.py words VIDEO, then pass --words)")
                continue
            if not hit:
                bad("error", f"the phrase '{d['on']}' was not heard in the word list")
                continue
            if hit[2] < 1.0:
                bad("warn", f"'{d['on']}' matched approximately ({hit[2]:.2f}); check the timing")
            d["start"] = round(max(0.0, hit[0] + float(d.get("lead", -0.15))), 3)
            if "until" in d and d.get("end") is None:
                u = find_phrase(words, d["until"], d["start"])
                if not u:
                    bad("error", f"the phrase '{d['until']}' was not heard after '{d['on']}'")
                    continue
                d["end"] = round(u[1] + 0.1, 3)
        if d.get("start") is None:
            bad("error", "needs a start (seconds) or an 'on' phrase")
            continue
        d["start"] = float(d["start"])
        if d.get("end") is None:
            d["end"] = d["start"] + float(d.get("dur", sum(spec.seconds) / 2))
        d["end"] = float(d["end"])
        if d["end"] <= d["start"]:
            bad("error", "end is not after start")
            continue
        if d["start"] >= dur:
            bad("error", f"starts at {d['start']:.2f}s, after the clip ends ({dur:.2f}s)")
            continue
        if d["end"] > dur:
            bad("warn", f"ends at {d['end']:.2f}s, after the clip ({dur:.2f}s): shortened")
            d["end"] = dur
        length = d["end"] - d["start"]
        lo, hi = spec.seconds
        if length < lo * 0.5 or length > hi * 2.2:
            bad("warn", f"{length:.1f}s is outside the {lo:g} to {hi:g}s this effect is built for")
        out.append(d)
    # a plan-level judgement: camera clashes, crowding, repetition
    cams = [d for d in out if EFFECTS[d["fx"]].camera]
    for a in range(len(cams)):
        for b in range(a + 1, len(cams)):
            if cams[a]["start"] < cams[b]["end"] and cams[b]["start"] < cams[a]["end"]:
                issues.append({"level": "error", "fx": cams[b]["fx"], "index": -1, "msg": f"{cams[a]['fx']} and {cams[b]['fx']} both move the camera at the same time"})
    for d in out:
        busy = [x for x in out if x is not d and x["start"] < d["end"] and d["start"] < x["end"]]
        if len(busy) >= 3:
            issues.append({"level": "warn", "fx": d["fx"], "index": -1, "msg": f"{len(busy) + 1} effects overlap here: too busy to read"})
            break
    order = sorted(out, key=lambda d: d["start"])
    for a, b, c in zip(order, order[1:], order[2:]):
        if a["fx"] == b["fx"] == c["fx"]:
            issues.append({"level": "warn", "fx": a["fx"], "index": -1, "msg": "three of the same effect in a row: vary the treatment"})
            break
    return out, issues


_NUM_OPTS = {"big-number": ("text",), "glass-stat": ("to", "from"), "headline-wall": ("total",), "tile-wall": ("count",), "count-badge": ("from",), "corner-push": ("to",),
             "glass-widgets": ("text",)}


def _num_tokens(s: str) -> set[str]:
    return {re.sub(r"[,\s]", "", m).lower() for m in re.findall(r"\d[\d,.]*\s?[kKmMbB%]?", str(s))}


def number_lint(plan: list[dict], beatmap: dict) -> list[dict]:
    """Numbers drawn by an effect must come from the beat map (claims, spoken text or an overlay): code draws numbers, it does not invent them."""
    allowed: set[str] = set()
    for cl in beatmap.get("claims", []):
        allowed |= _num_tokens(cl.get("text", ""))
    for b in beatmap.get("beats", []):
        allowed |= _num_tokens(b.get("text", ""))
        for o in b.get("overlays", []) or []:
            allowed |= _num_tokens(o.get("content", ""))
    allowed |= {a.rstrip("kKmMbB%") for a in allowed}
    issues = []
    for d in plan:
        if str(d.get("decorative", "")).lower() in ("1", "true", "yes"):
            continue
        for key in _NUM_OPTS.get(d["fx"], ()):
            for tok in _num_tokens(d.get(key, "")):
                if tok not in allowed and tok.rstrip("kKmMbB%") not in allowed:
                    issues.append({"level": "error", "fx": d["fx"], "index": -1,
                                   "msg": f"the number {tok} (option '{key}') is not in the beat map's claims, spoken text or overlays; take it from a claim, or add \"decorative\": true if it is only a placeholder"})
    return issues


# ------------------------------------------------------------------------------------------------------------------- engine

def load_cards(spec, base: Path, thumbs):
    """Images (or the first frame of videos) from a folder or a list of paths; the video's own frames when none are given."""
    out = []
    items = []
    if isinstance(spec, (list, tuple)):
        items = [Path(base, s) for s in spec]
    elif spec:
        p = Path(base, str(spec))
        items = sorted(p.iterdir()) if p.is_dir() else [p]
    for p in items:
        ext = p.suffix.lower().lstrip(".")
        try:
            if ext in ("jpg", "jpeg", "png", "webp"):
                out.append(Image.open(p).convert("RGB"))
            elif ext in ("mp4", "mov", "m4v", "webm"):
                cap = cv2.VideoCapture(str(p))
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ok, fr = cap.read()
                cap.release()
                if ok:
                    out.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
        except Exception:
            continue
    return out or thumbs


def grab_thumbs(video: str, dur: float, n: int = 10, w: int = 540) -> list:
    info = person_track.probe(video)
    h = int(round(w * info["h"] / info["w"] / 2)) * 2
    out = []
    for k in range(n):
        t = dur * (k + 0.5) / n
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True)
        if len(p.stdout) == w * h * 3:
            out.append(Image.fromarray(np.frombuffer(p.stdout, np.uint8).reshape(h, w, 3).copy()))
    return out


class Session:
    """A clip, its plan, its track: everything needed to produce any frame."""

    def __init__(self, video: str, plan: list[dict], width: int = 1080, theme: Theme | None = None, base: Path | None = None, quiet: bool = False):
        self.video = video
        self.info = person_track.probe(video)
        self.theme = theme or Theme()
        s = self.info
        if s["w"] <= s["h"]:
            self.W, self.H = width, int(round(width * s["h"] / s["w"] / 2)) * 2
        else:
            self.H, self.W = width, int(round(width * s["w"] / s["h"] / 2)) * 2
        self.fxs = [Fx(d) for d in plan]
        self.fxs.sort(key=lambda f: (not EFFECTS[f.name].camera, f.start))     # camera first, then plan order
        wins = [(f.start, f.end) for f in self.fxs]
        self.track = person_track.scan(video, wins, quiet=quiet) if wins else None
        self.thumbs = grab_thumbs(video, s["dur"]) if any(EFFECTS[f.name].images for f in self.fxs) else []
        for f in self.fxs:
            if EFFECTS[f.name].images:
                f.cards = load_cards(f.o.get("images"), base or Path("."), self.thumbs)
        self.sc = self.W / self.track.aw if self.track else 1.0

    def context(self, i: int, frame_rgb_u8) -> Ctx:
        t = i / self.info["fps"]
        img = frame_rgb_u8.astype(np.float32) / 255.0
        m = self.track.matte_at(i) if self.track else None
        m = cv2.resize(m, (self.W, self.H), interpolation=cv2.INTER_LINEAR).astype(np.float32) if m is not None else np.zeros((self.H, self.W), np.float32)
        r = self.track.row(i) * self.sc
        return Ctx(self.W, self.H, self.info["fps"], t, img, m, tuple(r), self.theme)

    def apply(self, c: Ctx, only=None):
        for f in self.fxs:
            if only is not None and f is not only:
                continue
            if f.start <= c.t < f.end + 1e-6 or only is f:
                c.lt = c.t - f.start
                EFFECTS[f.name].fn(c, f)
        return c

    def active(self, t):
        return [f for f in self.fxs if f.start <= t < f.end]


def frame_at(video: str, t: float, W: int, H: int):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1", "-vf", f"scale={W}:{H}:flags=bicubic", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True)
    if len(p.stdout) != W * H * 3:
        raise SystemExit(f"could not read a frame at {t:.2f}s")
    return np.frombuffer(p.stdout, np.uint8).reshape(H, W, 3).copy()


def to_u8(c: Ctx):
    return (np.clip(c.img, 0, 1) * 255 + 0.5).astype(np.uint8)


def audio_codec(video: str) -> str:
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video],
                          capture_output=True, text=True).stdout.strip()


def render(video: str, plan: list[dict], out: str, width=1080, theme=None, base=None, crf=17, quiet=False):
    ses = Session(video, plan, width, theme, base, quiet)
    s, fps = ses.info, ses.info["fps"]
    has_audio = bool(audio_codec(video))
    acodec = ["-c:a", "copy"] if audio_codec(video) == "aac" else ["-c:a", "aac", "-b:a", "192k"]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ses.W}x{ses.H}", "-r", f"{fps:.5f}", "-i", "-", "-i", video,
                            "-map", "0:v", *(["-map", "1:a:0"] if has_audio else []), "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            *acodec, "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = 0
    for i, fr in person_track.read_frames(video, ses.W, ses.H):
        if ses.active(i / fps):
            c = ses.context(i, fr)
            ses.apply(c)
            fr = to_u8(c)
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
        n += 1
        if not quiet and i % int(fps * 5) == 0:
            print(f"  {i / fps:5.1f}s / {s['dur']:.1f}s", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()
    used = sorted({"modnet" if ses.track and ses.track.backend.get("matte") == "modnet" else "", "yunet" if ses.track and ses.track.backend.get("face") == "yunet" else ""} - {""})
    log = {"schema": "hybrid-fxlog/1", "video": video, "out": out, "frames": n, "effects": [{"fx": f.name, "start": round(f.start, 3), "end": round(f.end, 3)} for f in ses.fxs],
           "track": {"backend": ses.track.backend if ses.track else {}, "quality": ses.track.quality if ses.track else None},
           "local_models": [{"id": u, "licence": fx_assets.catalog()[u]["licence"], "about": fx_assets.catalog()[u]["about"]} for u in used],
           "system_font_fallbacks": sorted(fx_core.FONT_FALLBACKS)}
    Path(out).with_suffix(".fx.json").write_text(json.dumps(log, indent=1))
    return n


# -------------------------------------------------------------------------------------------------------------------- audit

def platform_bands(platform: str) -> dict:
    z = json.loads((SKILL_DIR / "data" / "platforms.json").read_text(encoding="utf-8"))["safe_zones_1080x1920"]["platforms"]
    return z.get(platform) or z["common"]


def audit_effect(ses: Session, f: Fx, samples=5, platform="common") -> dict:
    """Render `samples` frames across the window; worst head coverage, graphics inside the UI bands, and what had to fall back."""
    spec = EFFECTS[f.name]
    band = platform_bands(platform)
    worst, in_ui, ts = 0.0, 0.0, [f.start + f.d * (k + 0.5) / samples for k in range(samples)]
    fx_core.FONT_FALLBACKS.clear()
    for t in ts:
        i = min(ses.info["n"] - 1, int(t * ses.info["fps"]))
        c = ses.context(i, frame_at(ses.video, i / ses.info["fps"], ses.W, ses.H))
        c.t = t
        for g in ses.fxs:                       # camera moves first, as in a render; only f's own drawing is measured
            if (EFFECTS[g.name].camera and g.start <= t < g.end) or g is f:
                if g is not f and not EFFECTS[g.name].camera:
                    continue
                c.lt = t - g.start
                c.cover, c.boxes = (0.0, []) if g is f else (c.cover, c.boxes)
                EFFECTS[g.name].fn(c, g)
                if g is f:
                    break
        worst = max(worst, c.cover)
        k = 1080 / ses.W
        for (x0, y0, x1, y1) in c.boxes:
            x0, x1, y0, y1 = x0 * k, x1 * k, y0 * k, y1 * k
            ui = (y1 > 1920 - band["bottom"] and y0 > 1920 - band["bottom"] - 40) or (y0 < band["top"] * 0.5 and y1 < band["top"])
            in_ui = max(in_ui, 1.0 if ui else 0.0)
    out = {"fx": f.name, "start": round(f.start, 2), "end": round(f.end, 2), "head_covered": round(worst, 3), "in_platform_ui": bool(in_ui),
           "fonts_fallback": sorted(fx_core.FONT_FALLBACKS)}
    out["covers_face"] = worst > 0.06 and not spec.cover_ok
    return out


# ------------------------------------------------------------------------------------------------------------------------ CLI

def _opts(kvs):
    out = {}
    for kv in kvs or []:
        k, v = kv.split("=", 1)
        out[k.strip()] = v
    return out


def _prep(a, words_path=None):
    plan, meta = load_plan(a.plan)
    info = person_track.probe(a.video)
    words = load_words(words_path) if words_path else None
    plan, issues = resolve_plan(plan, words, info["dur"])
    bm = getattr(a, "beatmap", None)
    if bm:
        issues += number_lint(plan, json.loads(Path(bm).read_text(encoding="utf-8")))
    return plan, meta, info, issues


def _show(issues):
    for it in issues:
        print(f"  {it['level'].upper():5} {it['fx']}: {it['msg']}")


def cmd_list(a):
    cat = fx_registry.catalog()
    rows = {k: v for k, v in cat.items() if not a.family or v["family"] == a.family}
    if a.json:
        print(json.dumps(rows, indent=1))
        return 0
    fams = {}
    for k, v in rows.items():
        fams.setdefault(v["family"], []).append((k, v))
    for fam, items in fams.items():
        print(f"\n{fam}")
        for k, v in items:
            flags = ("M" if v["needs_matte"] else "-") + ("C" if v["moves_camera"] else "-") + ("I" if v["takes_images"] else "-")
            print(f"  {k:18} {flags}  {v['description']}")
    print(f"\n{len(rows)} effects. flags: M needs a good person matte, C moves the camera, I takes an images folder.  Options: person_fx.py list --json")
    return 0


def cmd_words(a):
    ws = transcribe(a.video, a.lang)
    out = Path(a.out or Path(a.video).with_suffix(".words.json"))
    out.write_text(json.dumps(ws, indent=1))
    print(f"{len(ws)} words -> {out}")
    return 0


def cmd_plan(a):
    plan, meta, info, issues = _prep(a, a.words)
    for d in plan:
        print(f"  {d['start']:7.2f} - {d['end']:7.2f}  {d['fx']}")
    _show(issues)
    return 2 if any(i["level"] == "error" for i in issues) else 0


def cmd_check(a):
    plan, meta, info, issues = _prep(a, a.words)
    _show(issues)
    if any(i["level"] == "error" for i in issues):
        return 2
    base = Path(a.plan).resolve().parent if not isinstance(a.plan, (dict, list)) else Path(".")
    ses = Session(a.video, plan, a.width, Theme.from_style(a.style or meta.get("style")), base)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    if ses.track and ses.track.quality != "good":
        print(f"  WARN  the person matte is approximate ({ses.track.backend}): behind-the-head effects will look rough; install onnxruntime and go online once for the real one")
    shots, report = [], []
    ats = [float(x) for x in a.at.split(",")] if a.at else [f.start + f.d * 0.55 for f in ses.fxs]
    for k, t in enumerate(ats):
        i = min(info["n"] - 1, int(t * info["fps"]))
        c = ses.context(i, frame_at(a.video, i / info["fps"], ses.W, ses.H))
        c.t = t
        ses.apply(c)
        names = "+".join(f.name for f in ses.active(t)) or "none"
        p = out / f"{k + 1:02d}_{t:06.2f}_{names[:40]}.png"
        Image.fromarray(to_u8(c)).save(p)
        shots.append(p)
        print("  frame", p.name)
    for f in ses.fxs:
        r = audit_effect(ses, f, platform=a.platform)
        report.append(r)
        flag = "FAIL" if r["covers_face"] else ("warn" if r["in_platform_ui"] or r["fonts_fallback"] else "ok")
        print(f"  {flag:4} {f.name:18} {f.start:6.2f}-{f.end:6.2f}  head covered {r['head_covered'] * 100:4.1f}%" + ("  in the platform's UI band" if r["in_platform_ui"] else "")
              + (f"  system font used for {r['fonts_fallback']}" if r["fonts_fallback"] else ""))
    (out / "audit.json").write_text(json.dumps({"issues": issues, "effects": report, "quality": ses.track.quality if ses.track else None}, indent=1))
    if shots:                                       # a contact sheet to look at
        th = 480
        ims = [Image.open(p) for p in shots]
        ims = [im.resize((int(im.width * th / im.height), th)) for im in ims]
        cols = min(6, len(ims))
        rows = -(-len(ims) // cols)
        sheet = Image.new("RGB", (cols * ims[0].width, rows * th), (16, 16, 20))
        for j, im in enumerate(ims):
            sheet.paste(im, ((j % cols) * ims[0].width, (j // cols) * th))
        sheet.save(out / "sheet.png")
        print("  sheet", out / "sheet.png")
    bad = [r for r in report if r["covers_face"]]
    if bad:
        print(f"FAIL: {', '.join(r['fx'] for r in bad)} cover the face. Move it (x, y), shorten the text, or choose a different effect.")
        return 1
    print("PASS")
    return 0


def cmd_render(a):
    plan, meta, info, issues = _prep(a, a.words)
    _show(issues)
    if any(i["level"] == "error" for i in issues):
        return 2
    base = Path(a.plan).resolve().parent
    n = render(a.video, plan, a.out, a.width, Theme.from_style(a.style or meta.get("style")), base, a.crf)
    print(f"wrote {a.out} ({n} frames) and {Path(a.out).with_suffix('.fx.json').name}")
    print("record it:  python3 provenance.py add --episode EP --role other --ai true --tool person_fx --model modnet+yunet --provider local --runs local "
          "--used-for 'person matte and face track for overlays' --in-output true --realism none --depicts none")
    return 0


def cmd_one(a):
    d = {"fx": a.name, "start": a.start if a.start is not None else 0.0, "end": a.end if a.end is not None else None, **_opts(a.opt)}
    if a.text:
        d["text"] = a.text
    if a.images:
        d["images"] = a.images
    info = person_track.probe(a.video)
    plan, issues = resolve_plan([d], None, info["dur"])
    _show(issues)
    if not plan:
        return 2
    if a.still is not None:
        ses = Session(a.video, plan, a.width, Theme.from_style(a.style), Path("."))
        for t in [float(x) for x in str(a.still).split(",")]:
            i = min(info["n"] - 1, int(t * info["fps"]))
            c = ses.context(i, frame_at(a.video, i / info["fps"], ses.W, ses.H))
            c.t = t
            ses.apply(c)
            p = a.out if "," not in str(a.still) else a.out.replace(".png", f"_{t:.2f}.png")
            Image.fromarray(to_u8(c)).save(p)
            print("wrote", p)
        return 0
    render(a.video, plan, a.out, a.width, Theme.from_style(a.style), Path("."), a.crf)
    print("wrote", a.out)
    return 0


def cmd_doctor(a):
    """What is missing for person-aware effects, and (with --fetch) get the models and fonts. Exit 1 when something needed is absent."""
    import importlib.util
    import shutil
    bad = 0
    for m, need, pipname in (("numpy", True, "numpy"), ("cv2", True, "opencv-python"), ("PIL", True, "pillow"), ("onnxruntime", False, "onnxruntime"), ("faster_whisper", False, "faster-whisper")):
        ok = importlib.util.find_spec(m) is not None
        bad += 0 if ok or not need else 1
        print(f"  {'ok ' if ok else ('MISSING' if need else 'optional')} {m:16}" + ("" if ok else f" pip install {pipname}" + ("" if need else (" (the real person matte)" if m == "onnxruntime" else " (word times: person_fx.py words)"))))
    for b in ("ffmpeg", "ffprobe"):
        ok = shutil.which(b) is not None
        bad += 0 if ok else 1
        print(f"  {'ok ' if ok else 'MISSING'} {b}")
    for n, sp in fx_assets.catalog().items():
        p = fx_assets.ensure(n, quiet=False) if a.fetch else fx_assets.verified(n)
        print(f"  {'ok ' if p else 'absent '} {n:24}{sp['kind']:6}{sp['licence']}")
    return 1 if bad else 0


def catalog_markdown() -> str:
    """The effect table of references/20-person-aware-effects.md, generated from the registry so the doc cannot drift."""
    cat = fx_registry.catalog()
    order = ["type", "light", "camera", "cards", "ui", "data", "glass", "frame"]
    titles = {"type": "Type and depth", "light": "Light, room and grade", "camera": "Camera", "cards": "Cards and reels", "ui": "Interface cards", "data": "Data callouts",
              "glass": "Liquid glass", "frame": "Frames, marks and covers"}
    out = []
    for fam in order:
        rows = [(k, v) for k, v in cat.items() if v["family"] == fam]
        if not rows:
            continue
        out.append(f"**{titles[fam]}**\n\n| Effect | What it does | Options |\n|---|---|---|")
        for k, v in rows:
            opts = ", ".join(f"`{o}`" for o in v["options"]) or "none"
            flags = " (needs a good matte)" if v["needs_matte"] else ""
            out.append(f"| `{k}` | {v['description']}{flags} | {opts} |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_catalog(a):
    if getattr(a, "doc", False):
        print(catalog_markdown(), end="")
        return 0
    target = SKILL_DIR / "data" / "effects.json"
    if a.write:
        fx_registry.dump_catalog(target)
        print("wrote", target)
        return 0
    cur = target.read_text(encoding="utf-8") if target.is_file() else ""
    ok = cur == fx_registry.dump_catalog()
    print("data/effects.json is current" if ok else "data/effects.json is stale: run person_fx.py catalog --write")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--family")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("words")
    p.add_argument("video")
    p.add_argument("--out")
    p.add_argument("--lang")
    for name in ("plan", "check", "render"):
        p = sub.add_parser(name)
        p.add_argument("plan")
        p.add_argument("video")
        if name == "check":
            p.add_argument("outdir")
            p.add_argument("--at")
            p.add_argument("--platform", default="common")
        if name == "render":
            p.add_argument("out")
            p.add_argument("--crf", type=int, default=17)
        p.add_argument("--words")
        p.add_argument("--beatmap", help="check every number an effect draws against the beat map's claims and text")
        p.add_argument("--width", type=int, default=1080)
        p.add_argument("--style")
    p = sub.add_parser("one")
    p.add_argument("name")
    p.add_argument("video")
    p.add_argument("out")
    p.add_argument("--start", type=float)
    p.add_argument("--end", type=float)
    p.add_argument("--text")
    p.add_argument("--images")
    p.add_argument("--opt", action="append")
    p.add_argument("--still", help="comma separated seconds: write PNG frames instead of a video")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--style")
    p.add_argument("--crf", type=int, default=17)
    p = sub.add_parser("doctor")
    p.add_argument("--fetch", action="store_true", help="download the models and fonts now (about 28 MB, once)")
    p = sub.add_parser("catalog")
    p.add_argument("--write", action="store_true")
    p.add_argument("--doc", action="store_true", help="print the markdown effect table used in the reference")
    a = ap.parse_args(argv)
    if a.cmd in ("plan", "check", "render", "words", "one") and not Path(a.video).is_file():
        print(f"no such video: {a.video}", file=sys.stderr)
        return 2
    return {"list": cmd_list, "words": cmd_words, "plan": cmd_plan, "check": cmd_check, "render": cmd_render, "one": cmd_one, "catalog": cmd_catalog, "doctor": cmd_doctor}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
