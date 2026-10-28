#!/usr/bin/env python3
"""person_track.py - where the speaker is, frame by frame: a face box, the head top, the shoulder line and a soft person matte.

    python3 person_track.py scan    host.mp4 [--windows 3:6,10:13] [--track-fps 15] [--matte auto|modnet|grabcut|param] [--json out.json]
    python3 person_track.py preview host.mp4 --out preview.mp4 [--windows ...]      # the matte tinted over the footage, to check it by eye
    python3 person_track.py export  host.mp4 --out face.json                        # normalised 0..1 face track, for a HyperFrames or HTML overlay

Why: an overlay that does not know where the person is either covers the face or floats in front of the head. With a matte a word can
sit behind the speaker, a card can follow the head, a light can leave the speaker lit. `fx_core.py` and `person_fx.py` read this module.

How: the matte comes from a portrait-matting network (MODNet, ONNX, run on CPU with onnxruntime, about 0.15 s per frame at 540 x 960) and
is tightened with a guided filter against the footage so the edge follows the hair. The face comes from OpenCV's YuNet, then a Haar
cascade, then the matte itself. Tracking runs every Nth frame (default 15 fps) and is interpolated; the face and the lines derived from the
matte are smoothed with a two-pass filter, so the smoothing adds no lag. Everything is cached under ~/.cache/hybrid-social-video/track, keyed on
the file, so a second run, or a check frame, costs nothing.

Backends degrade, never stop: with no network and no cached model the matte falls back to GrabCut seeded from the face box, then to a
body shape drawn from the face. `Track.quality` says which ("good" or "approx"); an approximate matte is good enough to place things
around a person but not to tuck a word behind a head, and `person_fx.py` says so.

Needs numpy and OpenCV (opencv-python); onnxruntime for the network matte (pip install onnxruntime). Exit 0 ok | 2 usage | 3 missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_assets  # noqa: E402

VERSION = 4
COLS = ("cx", "cy", "fw", "fh", "top", "shoulder")


def _need():
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as exc:
        print(f"person_track needs numpy and opencv-python ({exc}). pip install numpy opencv-python onnxruntime", file=sys.stderr)
        raise SystemExit(3)


# ---------------------------------------------------------------------------------------------------------------- video i/o

def probe(path: str) -> dict:
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate,width,height,nb_frames:format=duration", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    fps = float(num) / float(den or 1)
    rot = 0
    try:   # a phone clip stored sideways: ffmpeg autorotates on read, so swap the reported size
        side = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream_side_data=rotation", "-of", "csv=p=0", path],
                              capture_output=True, text=True).stdout.strip()
        rot = abs(int(float(side.split(",")[0]))) if side else 0
    except Exception:
        rot = 0
    w, h = int(s["width"]), int(s["height"])
    if rot in (90, 270):
        w, h = h, w
    dur = float(j["format"]["duration"])
    return {"fps": fps, "w": w, "h": h, "dur": dur, "n": max(1, int(dur * fps + 1e-6))}


def read_frames(path: str, w: int, h: int, step: int = 1, fps: float | None = None):
    """Yield (index, rgb uint8 array) for every `step`th frame, scaled to w x h. `fps` makes ffmpeg conform the rate first."""
    import numpy as np
    vf = ([f"fps={fps}"] if fps else []) + ([f"select=not(mod(n\\,{step}))"] if step > 1 else []) + [f"scale={w}:{h}:flags=bicubic", "format=rgb24"]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", ",".join(vf), "-fps_mode", "passthrough", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE, bufsize=10 ** 8)
    n, i = w * h * 3, 0
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield i * step, np.frombuffer(b, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        if p.poll() is None:
            p.kill()
        p.stdout.close()
        p.wait()


# ---------------------------------------------------------------------------------------------------------------- filters

def guided_filter(guide, src, r: int = 8, eps: float = 2e-3):
    """He et al. guided filter with box filters: makes `src` (a soft matte) follow the edges of `guide` (grey footage, 0..1)."""
    import cv2
    import numpy as np
    k = (2 * r + 1, 2 * r + 1)
    box = lambda x: cv2.boxFilter(x, -1, k)
    mg, ms = box(guide), box(src)
    a = (box(guide * src) - mg * ms) / (box(guide * guide) - mg * mg + eps)
    b = ms - a * mg
    return np.clip(box(a) * guide + box(b), 0, 1)


def smooth_rows(rows, fps: float, tau: float = 0.18):
    """Fill gaps by interpolation, then smooth forward and backward with an exponential filter (zero net lag). Rows may hold NaN."""
    import numpy as np
    arr = np.array(rows, np.float64)
    if arr.ndim != 2 or not len(arr):
        return arr
    idx = np.arange(len(arr))
    for k in range(arr.shape[1]):
        col = arr[:, k]
        good = ~np.isnan(col)
        if not good.any():
            continue
        col[~good] = np.interp(idx[~good], idx[good], col[good])
        arr[:, k] = col
    a = 1 - math.exp(-1 / max(1e-3, fps * tau))
    for i in range(1, len(arr)):
        arr[i] = arr[i - 1] + a * (arr[i] - arr[i - 1])
    for i in range(len(arr) - 2, -1, -1):
        arr[i] = arr[i + 1] + a * (arr[i] - arr[i + 1])
    return arr


# ---------------------------------------------------------------------------------------------------------------- backends

class _Matte:
    name = "none"

    def __call__(self, rgb, face):   # -> float32 (h, w) 0..1
        raise NotImplementedError


class ModnetMatte(_Matte):
    name = "modnet"

    def __init__(self, path: Path):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        self.sess = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
        self.inp = self.sess.get_inputs()[0].name

    def __call__(self, rgb, face):
        import cv2
        import numpy as np
        h, w = rgb.shape[:2]
        rw = 512
        rh = max(64, int(round(rw * h / w / 32)) * 32)
        x = cv2.resize(rgb, (rw, rh), interpolation=cv2.INTER_AREA).astype(np.float32) / 127.5 - 1
        m = self.sess.run(None, {self.inp: x.transpose(2, 0, 1)[None]})[0][0, 0]
        m = cv2.resize(np.clip(m, 0, 1), (w, h), interpolation=cv2.INTER_LINEAR)
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
        m = guided_filter(g, m.astype(np.float32), r=6, eps=1e-3)
        return np.clip((m - 0.5) * 1.5 + 0.5, 0, 1).astype(np.float32)


class GrabCutMatte(_Matte):
    """No network, no model: GrabCut seeded from the face box. Slower and rougher; fine for placing things around a person."""
    name = "grabcut"

    def __call__(self, rgb, face):
        import cv2
        import numpy as np
        h, w = rgb.shape[:2]
        s = 320 / max(w, h)
        small = cv2.resize(rgb, (max(32, int(w * s)), max(32, int(h * s))), interpolation=cv2.INTER_AREA)
        sh, sw = small.shape[:2]
        cx, cy, fw, fh = (face if face is not None else (w / 2, h * 0.3, w * 0.2, w * 0.26))
        cx, cy, fw, fh = cx * s, cy * s, fw * s, fh * s
        mask = np.full((sh, sw), cv2.GC_PR_BGD, np.uint8)
        mask[: int(max(0, cy - fh * 1.4)), :] = cv2.GC_BGD
        lx, rx = int(max(0, cx - fw * 2.2)), int(min(sw, cx + fw * 2.2))
        if lx > 0:
            mask[:, :lx] = cv2.GC_BGD
        if rx < sw:
            mask[:, rx:] = cv2.GC_BGD
        y0 = int(max(0, cy - fh * 0.7))
        mask[y0:, int(max(0, cx - fw * 1.9)): int(min(sw, cx + fw * 1.9))] = cv2.GC_PR_FGD
        cv2.ellipse(mask, (int(cx), int(cy)), (max(2, int(fw * 0.55)), max(2, int(fh * 0.7))), 0, 0, 360, cv2.GC_FGD, -1)
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mask, None, bgd, fgd, 3, cv2.GC_INIT_WITH_MASK)
        except cv2.error:
            return ParamMatte()(rgb, face)
        m = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1.0, 0.0).astype(np.float32)
        m = cv2.GaussianBlur(cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR), (0, 0), max(1.0, w / 180))
        return np.clip((m - 0.5) * 2 + 0.5, 0, 1)


class ParamMatte(_Matte):
    """Last resort: a head ellipse and a shoulder block drawn from the face box. Good enough to keep graphics off the body."""
    name = "param"

    def __call__(self, rgb, face):
        import cv2
        import numpy as np
        h, w = rgb.shape[:2]
        cx, cy, fw, fh = (face if face is not None else (w / 2, h * 0.3, w * 0.2, w * 0.26))
        m = np.zeros((h, w), np.float32)
        cv2.ellipse(m, (int(cx), int(cy - fh * 0.1)), (int(fw * 0.62), int(fh * 0.85)), 0, 0, 360, 1.0, -1)
        pts = np.array([[cx - fw * 0.3, cy + fh * 0.6], [cx + fw * 0.3, cy + fh * 0.6], [cx + fw * 2.1, cy + fh * 1.5], [cx + fw * 2.4, h], [cx - fw * 2.4, h], [cx - fw * 2.1, cy + fh * 1.5]], np.int32)
        cv2.fillPoly(m, [pts], 1.0)
        return cv2.GaussianBlur(m, (0, 0), max(1.0, w / 120))


class FaceFinder:
    """YuNet first, a Haar cascade next. Returns (cx, cy, fw, fh) in the analysis image's pixels, or None."""

    def __init__(self, w: int, h: int, prefer: str = "auto"):
        import cv2
        self.yunet = None
        self.haar = None
        self.name = "none"
        if prefer in ("auto", "yunet"):
            p = fx_assets.ensure("yunet")
            if p:
                try:
                    self.yunet = cv2.FaceDetectorYN.create(str(p), "", (w, h), 0.6, 0.3, 20)
                    self.name = "yunet"
                except Exception:
                    self.yunet = None
        if self.yunet is None and prefer in ("auto", "haar"):
            hc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            if not hc.empty():
                self.haar, self.name = hc, "haar"

    def __call__(self, rgb):
        import cv2
        import numpy as np
        if self.yunet is not None:
            _, f = self.yunet.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            if f is not None and len(f):
                r = max(f, key=lambda r: r[2] * r[3] * r[-1])
                return (float(r[0] + r[2] / 2), float(r[1] + r[3] / 2), float(r[2]), float(r[3]))
        if self.haar is not None:
            g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            f = self.haar.detectMultiScale(g, 1.1, 5, minSize=(max(24, g.shape[1] // 14),) * 2)
            if len(f):
                x, y, w, h = max(f, key=lambda r: r[2] * r[3])
                return (float(x + w / 2), float(y + h / 2), float(w), float(h))
        return None


def make_matte(prefer: str = "auto") -> _Matte:
    if prefer in ("auto", "modnet"):
        try:
            p = fx_assets.ensure("modnet")
            if p:
                return ModnetMatte(p)
        except Exception as exc:
            if prefer == "modnet":
                raise
            print(f"person_track: network matte unavailable ({type(exc).__name__}); using GrabCut", file=sys.stderr)
    if prefer in ("auto", "modnet", "grabcut"):
        return GrabCutMatte()
    return ParamMatte()


def matte_geometry(m, face):
    """From a matte (float 0..1) and a face box: (top, shoulder) in the matte's pixels."""
    import numpy as np
    h, w = m.shape
    cx, cy, fw, fh = face
    x0, x1 = int(max(0, cx - fw * 0.4)), int(min(w, cx + fw * 0.4))   # a narrow band over the crown, so a wide hairline row does not read as empty
    top = float("nan")
    band = m[: int(max(1, cy)), x0:x1]
    if band.size:
        rows = np.where(band.mean(1) > 0.4)[0]
        if len(rows):
            top = float(rows[0])
    if math.isnan(top):
        top = cy - fh * 0.75
    shoulder = cy + fh * 1.5
    y = int(cy + fh * 0.5)
    widths = (m[y:] > 0.5).sum(1)
    hit = np.where(widths > fw * 1.9)[0]
    if len(hit):
        shoulder = float(y + hit[0])
    return top, shoulder


# ---------------------------------------------------------------------------------------------------------------------- Track

@dataclass
class Track:
    fps: float
    n: int
    aw: int
    ah: int
    step: int
    face: "object"                                   # (n, 6) float64: cx cy fw fh top shoulder, in analysis pixels, smoothed; NaN outside windows
    mattes: dict = field(default_factory=dict)       # tracked frame index -> uint8 (ah, aw)
    backend: dict = field(default_factory=dict)

    @property
    def quality(self) -> str:
        return "good" if self.backend.get("matte") == "modnet" and self.backend.get("face") in ("yunet", "haar") else "approx"

    def row(self, i: int):
        i = min(max(0, i), len(self.face) - 1)
        return self.face[i]

    def matte_at(self, i: int):
        """The matte for source frame i, blended between the two nearest tracked frames. float32 (ah, aw) 0..1, or None."""
        import numpy as np
        if not self.mattes:
            return None
        k0 = (i // self.step) * self.step
        k1 = k0 + self.step
        a = self.mattes.get(k0)
        b = self.mattes.get(k1)
        if a is None and b is None:
            near = min(self.mattes, key=lambda k: abs(k - i))
            return self.mattes[near].astype(np.float32) / 255
        if a is None:
            return b.astype(np.float32) / 255
        if b is None or k0 == i:
            return a.astype(np.float32) / 255
        t = (i - k0) / self.step
        return (a.astype(np.float32) * (1 - t) + b.astype(np.float32) * t) / 255

    def to_normalised(self):
        """Per-frame face geometry as 0..1 fractions of the frame: what an HTML overlay needs."""
        out = []
        for i in range(self.n):
            r = self.face[i]
            if r[0] != r[0]:
                out.append(None)
                continue
            out.append({"t": round(i / self.fps, 4), "cx": round(r[0] / self.aw, 4), "cy": round(r[1] / self.ah, 4), "fw": round(r[2] / self.aw, 4),
                        "fh": round(r[3] / self.ah, 4), "top": round(r[4] / self.ah, 4), "shoulder": round(r[5] / self.ah, 4)})
        return out


def _cache_key(path: str, aw: int, ah: int, step: int, matte: str) -> str:
    st = Path(path).stat()
    raw = f"{VERSION}|{Path(path).resolve()}|{st.st_size}|{st.st_mtime_ns}|{aw}x{ah}|{step}|{matte}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def scan(path: str, windows: list[tuple[float, float]] | None = None, track_fps: float = 15.0, matte: str = "auto",
         analysis_short: int = 540, margin: float = 0.5, quiet: bool = False, use_cache: bool = True) -> Track:
    """Track the speaker through `path`. `windows` are (start, end) seconds; None tracks the whole clip."""
    _need()
    import numpy as np
    info = probe(path)
    fps, n = info["fps"], info["n"]
    short = analysis_short
    if info["w"] <= info["h"]:
        aw, ah = short, int(round(short * info["h"] / info["w"] / 2)) * 2
    else:
        ah, aw = short, int(round(short * info["w"] / info["h"] / 2)) * 2
    step = max(1, int(round(fps / track_fps)))
    wins = [(max(0.0, a - margin), b + margin) for a, b in (windows or [(0.0, info["dur"])])]
    need = sorted({k for k in range(0, n, step) for a, b in wins if a * fps - step <= k <= b * fps + step})
    key = _cache_key(path, aw, ah, step, matte)
    cdir = fx_assets.cache_dir() / "track" / key
    raw_face, mattes, backend = {}, {}, {}
    if use_cache and (cdir / "meta.json").is_file():
        try:
            meta = json.loads((cdir / "meta.json").read_text())
            z = np.load(cdir / "mattes.npz")
            for k, row, m in zip(z["idx"], z["face"], z["matte"]):
                raw_face[int(k)] = row
                mattes[int(k)] = m
            backend = meta["backend"]
        except Exception:
            raw_face, mattes, backend = {}, {}, {}
    todo = [k for k in need if k not in mattes]
    if todo:
        ff = FaceFinder(aw, ah)
        mt = make_matte(matte)
        backend = {"matte": mt.name, "face": ff.name}
        want = set(todo)
        if not quiet:
            print(f"person_track: {len(todo)} frames to track at {aw}x{ah} (matte={mt.name}, face={ff.name}) ...", file=sys.stderr)
        prev, done = None, 0
        for k, fr in read_frames(path, aw, ah, step=step):
            if k not in want:
                prev = None
                continue
            face = ff(fr)
            m = mt(fr, face)
            if face is None:     # no detector hit: read the head off the matte
                rows = np.where((m > 0.5).sum(1) > aw * 0.01)[0]
                if len(rows):
                    top = rows[0]
                    band = m[top: top + max(4, int(ah * 0.06))] > 0.5
                    xs = np.where(band.any(0))[0]
                    fw = max(8.0, float((xs.max() - xs.min()) * 0.8)) if len(xs) else aw * 0.18
                    face = (float(xs.mean()) if len(xs) else aw / 2, top + fw * 0.7, fw, fw * 1.25)
            if prev is not None:
                m = 0.72 * m + 0.28 * prev
            prev = m
            if face is not None:
                t, s = matte_geometry(m, face)
                raw_face[k] = np.array([*face, t, s], np.float64)
            else:
                raw_face[k] = np.full(6, np.nan)
            mattes[k] = (np.clip(m, 0, 1) * 255).astype(np.uint8)
            done += 1
            if not quiet and done % 60 == 0:
                print(f"  tracked {done}/{len(todo)}", file=sys.stderr)
        if use_cache and mattes:
            cdir.mkdir(parents=True, exist_ok=True)
            ks = sorted(mattes)
            np.savez_compressed(cdir / "mattes.npz", idx=np.array(ks), face=np.stack([raw_face[k] for k in ks]), matte=np.stack([mattes[k] for k in ks]))
            (cdir / "meta.json").write_text(json.dumps({"backend": backend, "aw": aw, "ah": ah, "step": step, "src": str(Path(path).resolve()), "version": VERSION}))
    # per-frame face rows: interpolate between tracked frames, then smooth inside each window
    rows = np.full((n, 6), np.nan)
    ks = sorted(k for k in raw_face if k < n)
    if ks:
        ks_arr = np.array(ks)
        vals = np.stack([raw_face[k] for k in ks])
        for a, b in wins:
            i0, i1 = max(0, int(a * fps)), min(n, int(b * fps) + 1)
            if i1 <= i0:
                continue
            seg = []
            idx = np.arange(i0, i1)
            for c in range(6):
                col = vals[:, c]
                good = ~np.isnan(col)
                seg.append(np.interp(idx, ks_arr[good], col[good]) if good.any() else np.full(len(idx), np.nan))
            seg = np.stack(seg, 1)
            rows[i0:i1] = smooth_rows(seg, fps)
    if not np.isnan(rows).all():     # frames outside every window: hold the nearest tracked value so a late effect never sees NaN
        good = np.where(~np.isnan(rows[:, 0]))[0]
        for c in range(6):
            rows[:, c] = np.interp(np.arange(n), good, rows[good, c])
    return Track(fps=fps, n=n, aw=aw, ah=ah, step=step, face=rows, mattes=mattes, backend=backend)


# ---------------------------------------------------------------------------------------------------------------------- CLI

def _windows(s: str | None):
    if not s:
        return None
    out = []
    for part in s.split(","):
        a, b = part.split(":")
        out.append((float(a), float(b)))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scan", "preview", "export"])
    ap.add_argument("video")
    ap.add_argument("--windows", help="start:end seconds, comma separated; default the whole clip")
    ap.add_argument("--track-fps", type=float, default=15.0)
    ap.add_argument("--matte", default="auto", choices=["auto", "modnet", "grabcut", "param"])
    ap.add_argument("--json", help="scan: write a summary here")
    ap.add_argument("--out", help="preview: the mp4 to write | export: the json to write")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args(argv)
    if not Path(a.video).is_file():
        print(f"no such file: {a.video}", file=sys.stderr)
        return 2
    _need()
    import cv2
    import numpy as np
    tr = scan(a.video, _windows(a.windows), a.track_fps, a.matte, use_cache=not a.no_cache)
    if a.cmd == "scan":
        got = tr.face[~np.isnan(tr.face[:, 0])]
        summary = {"video": a.video, "fps": tr.fps, "frames": tr.n, "analysis": [tr.aw, tr.ah], "tracked": len(tr.mattes), "backend": tr.backend, "quality": tr.quality,
                   "face_median_px": [round(float(v), 1) for v in np.median(got, 0)] if len(got) else None}
        print(json.dumps(summary, indent=1))
        if a.json:
            Path(a.json).write_text(json.dumps(summary, indent=1))
        return 0
    if not a.out:
        print("--out is required", file=sys.stderr)
        return 2
    if a.cmd == "export":
        Path(a.out).write_text(json.dumps({"schema": "hybrid-facetrack/1", "fps": tr.fps, "backend": tr.backend, "frames": tr.to_normalised()}))
        print("wrote", a.out)
        return 0
    info = probe(a.video)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{tr.aw}x{tr.ah}", "-r", str(tr.fps), "-i", "-",
                            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    for i, fr in read_frames(a.video, tr.aw, tr.ah):
        m = tr.matte_at(i)
        out = fr.copy()
        if m is not None:
            tint = np.array([255, 60, 120], np.float32)
            out = (fr * (1 - 0.45 * m[..., None]) + tint * 0.45 * m[..., None]).astype(np.uint8)
            r = tr.row(i)
            if r[0] == r[0]:
                cv2.rectangle(out, (int(r[0] - r[2] / 2), int(r[1] - r[3] / 2)), (int(r[0] + r[2] / 2), int(r[1] + r[3] / 2)), (255, 255, 255), 2)
                cv2.line(out, (0, int(r[4])), (tr.aw, int(r[4])), (255, 214, 10), 1)
                cv2.line(out, (0, int(r[5])), (tr.aw, int(r[5])), (61, 219, 176), 1)
        enc.stdin.write(out.tobytes())
    enc.stdin.close()
    enc.wait()
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
