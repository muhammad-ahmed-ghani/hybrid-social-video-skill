#!/usr/bin/env python3
"""host_assemble.py - turn generated talking-host clips into one master track with word timings per beat.

    python3 host_assemble.py --beatmap episode/beatmap.json --clips episode/clips.json --out episode/build
                             [--lead 0.15] [--tail 0.30] [--size 720x1280] [--fps 30] [--min-match 0.8]

clips.json is a list in play order: [{"file": "clips/c1.mp4", "beats": [1]}, {"file": "clips/c2.mp4", "beats": [2, 3]}].
Each clip is a host video whose own audio carries the speech (the host's audio is the master clock: SKILL.md rule 10).
For every clip the script transcribes the clip's audio locally, aligns the words to the script of its beats, trims to the
real speech (`--lead` seconds before the first word, `--tail` after the last), conforms to the fps and size, fades the
audio edges to avoid clicks, and concatenates. It fails loudly when fewer than `--min-match` of the expected words are
heard (regenerate or inspect that clip; a clip that says something else is a content defect: one respend).
Outputs in --out: host.mp4 (the master track), timing.json ({"duration", "beats": [{"id", "clip", "s", "e", "cs", "ce",
"words": [{"word", "s", "e"}]}]} in master-track seconds). The HTML overlay page reads timing.json, so pictures and
captions follow the host's own words, and extra words a model speaks after the script are trimmed away.
Needs ffmpeg and faster_whisper. Exit 0 ok | 2 usage | 3 recogniser missing | 4 a clip does not say the script.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402
from speech_align import align, tokens  # noqa: E402


def _run(*a: str) -> None:
    subprocess.run(a, check=True, capture_output=True)


def _dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout.strip() or 0)


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h"})
    if opt.get("help") or opt.get("h") or not (opt.get("beatmap") and opt.get("clips") and opt.get("out")):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        eprint("faster_whisper is required to read word timings from the host audio (pip install faster-whisper)")
        return 3
    bm = json.loads(Path(opt["beatmap"]).read_text(encoding="utf-8"))
    beats = {b["id"]: b for b in bm["beats"]}
    clips_path = Path(opt["clips"]).resolve()
    clips = json.loads(clips_path.read_text(encoding="utf-8"))
    out = Path(opt["out"]); trim = out / "trim"; trim.mkdir(parents=True, exist_ok=True)
    lead, tail = float(opt.get("lead", 0.15)), float(opt.get("tail", 0.30))
    w, h = (int(x) for x in str(opt.get("size", "720x1280")).split("x"))
    fps, min_match = int(opt.get("fps", 30)), float(opt.get("min-match", 0.8))
    lang = str(bm.get("meta", {}).get("language_tag") or "en")[:2]
    model = WhisperModel("base.en" if lang == "en" else "base", device="cpu", compute_type="int8")

    timeline: list[dict] = []; parts: list[Path] = []; offset = 0.0
    for k, c in enumerate(clips):
        src = (clips_path.parent / c["file"]) if not Path(c["file"]).is_absolute() else Path(c["file"])
        exp: list[str] = []
        for bid in c["beats"]:
            for word in beats[bid]["text"].split():
                exp += tokens(word, numbers=(lang == "en"))
        segs, _ = model.transcribe(str(src), word_timestamps=True, language=lang)
        heard = [(t, ww.start, ww.end) for s in segs for ww in s.words for t in tokens(ww.word, numbers=(lang == "en"))]
        match = align(exp, [x[0] for x in heard])
        if len(match) < min_match * len(exp):
            eprint(f"clip {src.name}: only {len(match)} of {len(exp)} expected words were heard; regenerate it (one respend) or inspect it")
            return 4
        first = min(heard[j][1] for j in match.values()); last = max(heard[j][2] for j in match.values())
        t_in, t_out = max(0.0, first - lead), min(_dur(src), last + tail)
        dst = trim / f"t{k}.mp4"
        _run("ffmpeg", "-y", "-ss", f"{t_in:.3f}", "-to", f"{t_out:.3f}", "-i", str(src),
             "-vf", f"scale={w}:{h},fps={fps}",
             "-af", f"aresample=48000,pan=mono|c0=0.5*c0+0.5*c1,afade=t=in:d=0.02,afade=t=out:st={max(0.0, t_out - t_in - 0.05):.3f}:d=0.05",
             "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", str(dst))
        d = _dur(dst)
        n = len(exp); st: list[float | None] = [None] * n; en: list[float | None] = [None] * n
        for i, j in match.items():
            st[i] = heard[j][1] - t_in + offset; en[i] = heard[j][2] - t_in + offset
        for i in range(n):                                   # unmatched tokens: spread between matched neighbours
            if st[i] is None:
                p = max((x for x in range(i) if st[x] is not None), default=None)
                q = min((x for x in range(i + 1, n) if st[x] is not None), default=None)
                a = en[p] if p is not None else offset
                z = st[q] if q is not None else a + 0.3
                gap = [x for x in range(i, n) if st[x] is None and (q is None or x < q)]
                for g, x in enumerate(gap):
                    st[x] = a + g * (z - a) / len(gap); en[x] = a + (g + 1) * (z - a) / len(gap)
        idx = 0
        for bid in c["beats"]:
            ws = []
            for word in beats[bid]["text"].split():
                nt = len(tokens(word, numbers=(lang == "en")))
                if nt:
                    ws.append({"word": word, "s": round(st[idx], 3), "e": round(en[idx + nt - 1], 3)}); idx += nt
            timeline.append({"id": bid, "clip": k, "s": ws[0]["s"], "e": ws[-1]["e"], "cs": round(offset, 3), "ce": round(offset + d, 3), "words": ws})
        parts.append(dst); offset += d
        eprint(f"[host] clip {k} {src.name}: speech {first:.2f}-{last:.2f}s -> kept {t_in:.2f}-{t_out:.2f} ({d:.2f}s)")
    lst = out / "concat.txt"; lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    _run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-crf", "14", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", str(out / "host.mp4"))
    total = _dur(out / "host.mp4")
    (out / "timing.json").write_text(json.dumps({"beats": timeline, "duration": round(total, 3)}, indent=1))
    print(json.dumps({"host": str(out / "host.mp4"), "timing": str(out / "timing.json"), "seconds": round(total, 2), "beats": len(timeline)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
