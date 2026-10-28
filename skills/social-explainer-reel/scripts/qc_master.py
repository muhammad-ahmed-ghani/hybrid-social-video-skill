#!/usr/bin/env python3
"""qc_master.py - technical QC on the finished master. Offline and free.

    python3 qc_master.py master.mp4 [--target 40] [--platform tiktok] [--loop]
                         [--max-freeze 2.5] [--beatmap beatmap.json] [--waive pacing --why "<reason>"]

The JSON report is on stdout and the human summary on stderr (so `json.loads(stdout)` works; do not merge the streams).

Checks (each failure carries a repair hint; report-only, never edits):
  spec          size/aspect/fps/codec/pix_fmt/audio present   (data/platforms.json)
  duration      within 0.8-1.25x of --target, under the platform maximum
  av_delta      |video - audio| stream length <= 0.15 s
  hook_audio    first audible sound <= 0.9 s (no dead air before the hook)
  loudness      integrated LUFS in band, true peak under ceiling
  dead_frames   no black > 0.1 s, no freeze > --max-freeze (default 2.5 s)
  flicker       no more than 5 large frame-to-frame luma jumps inside any 1 s window (a strobing
                clip is a valid MP4 that passes ffprobe: a documented failure of generated video)
  pacing        fails a window in which nothing changes (whole-frame change and active area both near zero); reports cuts and the longest hold
  loop          (--loop) last frame resembles first frame (SSIM >= 0.6)

This is the numeric half of QC. The visual half (legibility, safe zones, face
occlusion, wrong symbols) needs eyes: run contact_sheet.py and LOOK.

`--waive CHECK --why "<reason>"` turns a failing check into a recorded waiver (shown in the report and the summary) for the case
where the check is wrong about a video that plainly passes the bar; the reason is required, and a waiver is never a way to ship
a defect: fix real defects, waive only a false alarm (SKILL.md, the bar).

Exit codes: 0 all pass (or waived) | 5 delivered but >=1 failure | 1 unreadable | 2 usage.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, ffprobe_json, have, load_json, parse_args, run  # noqa: E402

HINTS = {
    "spec": "re-encode: 1080x1920, 30 fps, H.264 yuv420p, AAC 48 kHz, +faststart",
    "duration": "words are the only length knob (~2.5 words/s): fix the script, then re-render; "
                "never stretch audio",
    "av_delta": "re-mux with -shortest or pin -t to the VO length; a persistent delta means a "
                "stream was clipped or padded upstream",
    "hook_audio": "dead air before the hook: trim leading silence at the VO source or tighten beat 0",
    "loudness": "re-run the mix with loudnorm I=-14:TP=-1.5; check music isn't clipping the VO",
    "dead_frames": "black = a segment gap (check clip durations vs beat spans); freeze = a stuck "
                   "loop or a held last frame: re-render that beat",
    "flicker": "a strobing or flickering stretch: inspect that segment on a contact sheet; a generated "
               "clip that strobes is a content defect, regenerate that beat once with a changed prompt",
    "pacing": "a stretch where nothing changes loses viewers: give it a real change (a new overlay state, a camera push or reframe toward the active part, a cut to another layer); never a flash or a fake cut. If the check is wrong about a video that does move, waive it: --waive pacing --why \"<reason>\"",
    "loop": "make the last beat's final frame echo the first (same framing/colour) for a clean loop",
}


def _stream(info: dict, kind: str) -> dict:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == kind), {})


def _fps(v: dict) -> float:
    r = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
    try:
        a, b = r.split("/")
        return float(a) / float(b) if float(b) else 0.0
    except ValueError:
        return 0.0


def _filter_log(path: Path, vf: str | None, af: str | None, timeout: int = 900) -> str:
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path)]
    if vf:
        cmd += ["-vf", vf, "-an"]
    if af:
        cmd += ["-af", af, "-vn"]
    cmd += ["-f", "null", "-"]
    return run(cmd, timeout=timeout).stderr


def check(path: Path, target: float | None, platform: str, loop: bool, max_freeze: float) -> dict:
    plat = data("platforms")
    spec = plat["delivery"]
    pinfo = plat["platforms"].get(platform, {})
    res: dict = {}
    fails: list[str] = []
    warns: list[str] = []

    info = ffprobe_json(path)
    v, a = _stream(info, "video"), _stream(info, "audio")
    dur = float(info.get("format", {}).get("duration") or 0)
    if not v or dur <= 0:
        return {"ok": False, "error": "unreadable or zero-length video"}

    w, h, fps = int(v.get("width", 0)), int(v.get("height", 0)), _fps(v)
    spec_issues = []
    if h and abs(w / h - 9 / 16) > 0.01:
        spec_issues.append(f"aspect {w}x{h} is not 9:16")
    if (w, h) not in [(1080, 1920), (720, 1280)]:
        spec_issues.append(f"{w}x{h} (deliver 1080x1920)")
    if not (spec["fps_range"][0] - 0.5 <= fps <= spec["fps_range"][1] + 0.5):
        spec_issues.append(f"fps {fps:.2f} outside {spec['fps_range']}")
    if v.get("codec_name") != "h264":
        spec_issues.append(f"codec {v.get('codec_name')} (want h264)")
    if v.get("pix_fmt") != "yuv420p":
        spec_issues.append(f"pix_fmt {v.get('pix_fmt')} (want yuv420p)")
    if not a:
        spec_issues.append("no audio stream")
    if a:
        try:
            off = abs(float(v.get("start_time") or 0) - float(a.get("start_time") or 0))
        except ValueError:
            off = 0.0
        if fps and off > 1.5 / fps:
            spec_issues.append(f"audio/video start_time differ by {off * 1000:.0f} ms "
                               "(re-mux; a stream offset shows as a black first frame or early audio)")
    res["spec"] = {"pass": not spec_issues, "width": w, "height": h, "fps": round(fps, 2),
                   "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
                   "acodec": a.get("codec_name"), "issues": spec_issues}
    if (w, h) == (720, 1280) and len(spec_issues) == 1:
        res["spec"]["pass"] = True  # 720p is acceptable, just not preferred
        res["spec"]["note"] = "720x1280 accepted; 1080x1920 preferred"

    max_len = pinfo.get("max_seconds")
    ok_dur = True
    if target:
        ok_dur = 0.8 * target <= dur <= 1.25 * target
    if max_len and dur > max_len:
        ok_dur = False
    res["duration"] = {"pass": ok_dur, "seconds": round(dur, 2), "target": target,
                       "platform_max": max_len}

    a_dur = float(a.get("duration") or 0)
    v_dur = float(v.get("duration") or dur)
    delta = abs(v_dur - a_dur) if a_dur else None
    res["av_delta"] = {"pass": delta is None or delta <= 0.15,
                       "seconds": None if delta is None else round(delta, 3)}

    if a:
        sil = _filter_log(path, None, "silencedetect=noise=-40dB:d=0.3")
        m = re.search(r"silence_start: (-?[\d.]+)", sil)
        e = re.search(r"silence_end: ([\d.]+)", sil)
        first_audible = 0.0
        if m and float(m.group(1)) <= 0.05 and e:
            first_audible = float(e.group(1))
        res["hook_audio"] = {"pass": first_audible <= 0.9, "first_audible_s": round(first_audible, 2)}

        eb = _filter_log(path, None, "ebur128=peak=true")
        tail = eb[eb.rfind("Summary:"):] if "Summary:" in eb else eb
        mi = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
        mp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
        lufs = float(mi.group(1)) if mi else None
        tp = float(mp.group(1)) if mp else None
        lo, hi = spec["lufs_gate"]
        ok_l = lufs is not None and lo <= lufs <= hi and (tp is None or tp <= spec["true_peak_gate"])
        res["loudness"] = {"pass": ok_l, "integrated_lufs": lufs, "true_peak_dbfs": tp,
                           "target_lufs": spec["lufs_target"], "gate": [lo, hi]}
        if ok_l and tp is not None and tp > spec["true_peak_warn"]:
            warns.append(f"true peak {tp} dBFS is hot (< {spec['true_peak_warn']} preferred)")
    else:
        res["hook_audio"] = {"pass": False, "first_audible_s": None}
        res["loudness"] = {"pass": False, "integrated_lufs": None}

    vlog = _filter_log(path, "blackdetect=d=0.1:pix_th=0.03,freezedetect=n=-55dB:d=1.0", None)
    blacks = [(float(s), float(e)) for s, e in
              re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", vlog)]
    blacks = [(s, e) for s, e in blacks if not (s < 0.05 and e < 0.2)]  # allow a 1-frame fade-in
    freezes = [float(d) for d in re.findall(r"freeze_duration: ([\d.]+)", vlog)]
    longest_freeze = max(freezes) if freezes else 0.0
    res["dead_frames"] = {"pass": not blacks and longest_freeze <= max_freeze,
                          "black_segments": blacks[:5], "longest_freeze_s": round(longest_freeze, 2)}

    sc = _filter_log(path, "select='gt(scene,0.30)',showinfo", None)
    cuts = [float(t) for t in re.findall(r"pts_time:([\d.]+)", sc)]

    # flicker: frame-to-frame luma difference (YDIF, 0-255). The `scene` filter scores the CHANGE
    # in change, so a periodic strobe registers once and then reads zero; YDIF does not have that blind spot.
    dl = _filter_log(path, "scale=108:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF", None)
    jumps: list[float] = []
    ydif: list[tuple[float, float]] = []
    t_cur = 0.0
    for line in dl.splitlines():
        m_t = re.search(r"pts_time:([\d.]+)", line)
        if m_t:
            t_cur = float(m_t.group(1))
        m_d = re.search(r"YDIF=([\d.]+)", line)
        if m_d:
            ydif.append((t_cur, float(m_d.group(1))))
            if float(m_d.group(1)) > 40.0:
                jumps.append(t_cur)
    densest = 0
    for i, t0 in enumerate(jumps):
        densest = max(densest, sum(1 for t1 in jumps[i:] if t1 - t0 < 1.0))
    res["flicker"] = {"pass": densest <= 5, "max_big_jumps_in_1s": densest}

    # pacing: a stretch is a problem only when nothing in it changes. Hard cuts are one kind of change; a person talking, an animated
    # diagram or a small moving overlay are others, and seamless jump cuts or same-luma beat changes score as no cut at all. So the
    # picture is read in sliding windows of the hold limit, with two measures: the whole-frame mean change (YDIF) and the active
    # area (the share of pixels that change by more than 10 levels between frames, which sees a small moving element a whole-frame
    # mean misses). A window is static only when both are near zero.
    limit = max(4.5, max_freeze * 1.8)
    al = _filter_log(path, "scale=108:192,format=gray,tblend=all_mode=difference,lut=y='if(gt(val,10),255,0)',signalstats,"
                           "metadata=print:key=lavfi.signalstats.YAVG", None)
    active: list[tuple[float, float]] = []
    t_a = 0.0
    for line in al.splitlines():
        m_t = re.search(r"pts_time:([\d.]+)", line)
        if m_t:
            t_a = float(m_t.group(1))
        m_y = re.search(r"YAVG=([\d.]+)", line)
        if m_y:
            active.append((t_a, float(m_y.group(1)) / 255.0))
    marks = [0.0] + cuts + [dur]
    longest = max((b_ - a_ for a_, b_ in zip(marks, marks[1:])), default=dur)
    static: list[dict] = []
    step = 0.5
    t0 = 0.0
    while t0 + limit <= dur + 1e-6:
        ys = [v for t_, v in ydif if t0 <= t_ < t0 + limit]
        ac = [v for t_, v in active if t0 <= t_ < t0 + limit]
        my = sum(ys) / len(ys) if ys else 0.0
        ma = sum(ac) / len(ac) if ac else 0.0
        if my < 0.3 and ma < 0.0015:
            if static and t0 <= static[-1]["to"]:
                static[-1]["to"] = round(t0 + limit, 2)
            else:
                static.append({"from": round(t0, 2), "to": round(t0 + limit, 2), "mean_change": round(my, 2), "active_area": round(ma, 4)})
        t0 += step
    res["pacing"] = {"pass": not static, "cuts": len(cuts), "avg_shot_s": round(dur / max(len(marks) - 1, 1), 2),
                     "longest_hold_s": round(longest, 2), "static_holds": static,
                     "note": f"a {limit:g} s window fails only when nothing changes in it (whole-frame change < 0.3 and active area < 0.15%); "
                             "never add flashes or fake cuts to satisfy this check"}

    if loop:
        with tempfile.TemporaryDirectory() as td:
            f0, f1 = Path(td, "a.png"), Path(td, "b.png")
            run(["ffmpeg", "-y", "-ss", "0.05", "-i", str(path), "-frames:v", "1", str(f0)])
            run(["ffmpeg", "-y", "-ss", str(max(0, dur - 0.1)), "-i", str(path),
                 "-frames:v", "1", str(f1)])
            out = run(["ffmpeg", "-hide_banner", "-i", str(f0), "-i", str(f1),
                       "-lavfi", "ssim", "-f", "null", "-"]).stderr
            ms = re.search(r"All:([\d.]+)", out)
            ss = float(ms.group(1)) if ms else None
            res["loop"] = {"pass": ss is not None and ss >= 0.6, "ssim_first_last": ss}

    for k, r in res.items():
        if isinstance(r, dict) and r.get("pass") is False:
            fails.append(k)
    return {"ok": not fails, "failures": fails, "warnings": warns, "checks": res,
            "hints": {k: HINTS[k] for k in fails if k in HINTS}}


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"loop"})
    if not pos:
        eprint(__doc__)
        return 2
    if not (have("ffmpeg") and have("ffprobe")):
        eprint("ffmpeg/ffprobe not found")
        return 2
    path = Path(pos[0])
    if not path.is_file():
        eprint(f"no such file: {path}")
        return 1
    target = float(opt["target"]) if opt.get("target") else None
    if not target and opt.get("beatmap"):
        try:
            target = float(load_json(opt["beatmap"])["meta"]["target_seconds"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            target = None
    rep = check(path, target, opt.get("platform", "tiktok"), bool(opt.get("loop")),
                float(opt.get("max-freeze", 2.5)))
    waive = opt.get("waive") if opt.get("waive") not in (None, True) else None
    if waive:
        why = opt.get("why") if opt.get("why") not in (None, True) else ""
        if not why.strip():
            eprint("--waive needs --why with the reason")
            return 2
        for k in [w for w in str(waive).split(",") if w]:
            if k in rep.get("checks", {}) and not rep["checks"][k].get("pass"):
                rep["checks"][k]["waived"] = why
                rep["checks"][k]["pass"] = True
                rep.setdefault("waivers", []).append({"check": k, "why": why})
                rep["failures"] = [f for f in rep["failures"] if f != k]
                rep["hints"].pop(k, None)
        rep["ok"] = not rep["failures"]
    print(json.dumps(rep, indent=2))
    if rep.get("error"):
        eprint("[qc] " + rep["error"])
        return 1
    for k, r in rep["checks"].items():
        eprint(f"  {'PASS' if r.get('pass') else 'FAIL'}  {k}: " +
               ", ".join(f"{a}={b}" for a, b in r.items() if a != "pass"))
    for w in rep["warnings"]:
        eprint(f"  warn  {w}")
    for k, hint in rep["hints"].items():
        eprint(f"  fix[{k}]: {hint}")
    eprint("[qc] " + ("PASS" if rep["ok"] else "FAIL: " + ", ".join(rep["failures"])))
    return 0 if rep["ok"] else 5


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
