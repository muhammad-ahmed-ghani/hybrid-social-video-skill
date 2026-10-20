#!/usr/bin/env python3
"""voice_check.py - audition a voice without a human: do the words come back right, is the pace and level sane?

    python3 voice_check.py --audio vo.wav --text "the script" [--text-file script.txt] [--max-wer 0.1]
                           [--kind system|neural|host|human] [--wps-range 1.8,3.6] [--lang en]

Round-trip: transcribe the audio with a local speech recogniser (faster-whisper, else the whisper module), then compare
the transcript with the script by word error rate (digits and spoken numbers are treated as equal for 0-999). Also
reports speaking pace (words per second over the audible span), integrated loudness and true peak (ffmpeg ebur128).
`--kind system` marks a system voice (macOS say, espeak, a small local model): the verdict is `draft` however well it
scores, because the skill ships a system voice only when nothing better is reachable (SKILL.md, the bar).
Use it to choose between routes yourself instead of asking the user to listen: render the same 2 to 3 lines on each
reachable route, run this on each, keep the best that is not `draft`. It cannot judge warmth; it removes the routes that
mispronounce, rush, clip or clip-distort. Exit 0 pass | 1 fail | 3 no recogniser (the numbers are still printed).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402
from speech_align import tokens, wer  # noqa: E402


def _ffprobe_duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _loudness(path: str) -> tuple[float | None, float | None]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else r.stderr
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(i.group(1)) if i else None, float(p.group(1)) if p else None)


def transcribe(path: str, lang: str) -> list[tuple[str, float, float]] | None:
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base.en" if lang == "en" else "base", device="cpu", compute_type="int8")
        segs, _ = model.transcribe(path, word_timestamps=True, language=lang)
        return [(w.word, float(w.start), float(w.end)) for s in segs for w in s.words]
    except Exception:
        pass
    try:
        import whisper
        res = whisper.load_model("base").transcribe(path, word_timestamps=True, language=lang)
        return [(w["word"], float(w["start"]), float(w["end"])) for s in res["segments"] for w in s.get("words", [])]
    except Exception:
        return None


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h"})
    if opt.get("help") or opt.get("h") or not opt.get("audio"):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    text = opt.get("text") or ""
    if opt.get("text-file"):
        text = Path(opt["text-file"]).read_text(encoding="utf-8")
    if not text.strip():
        eprint("--text or --text-file is required")
        return 2
    audio = opt["audio"]
    lang = str(opt.get("lang", "en"))
    lo, hi = (float(x) for x in str(opt.get("wps-range", "1.8,3.6")).split(","))
    max_wer = float(opt.get("max-wer", 0.1))
    exp = tokens(text, numbers=(lang == "en"))
    rep: dict = {"audio": audio, "duration_s": round(_ffprobe_duration(audio), 2), "kind": opt.get("kind", "unknown")}
    lufs, tp = _loudness(audio)
    rep["lufs"], rep["true_peak_dbfs"] = lufs, tp
    words = transcribe(audio, lang)
    issues: list[str] = []
    if words is None:
        rep["transcribed"] = False
        issues.append("no local speech recogniser (faster_whisper or whisper) to round-trip the words")
    else:
        heard = [t for w, _, _ in words for t in tokens(w, numbers=(lang == "en"))]
        rep["transcribed"] = True
        rep["wer"] = round(wer(exp, heard), 3)
        span = (words[-1][2] - words[0][1]) if words else 0.0
        rep["words_per_s"] = round(len(exp) / span, 2) if span > 0 else None
        if rep["wer"] > max_wer:
            issues.append(f"word error rate {rep['wer']} is above {max_wer}: the voice mispronounces or drops words")
        if rep["words_per_s"] and not lo <= rep["words_per_s"] <= hi:
            issues.append(f"pace {rep['words_per_s']} words/s is outside {lo} to {hi}")
    if tp is not None and tp > -0.5:
        issues.append(f"true peak {tp} dBFS is at the ceiling: clipping risk")
    if lufs is not None and lufs < -32:
        issues.append(f"integrated loudness {lufs} LUFS is very quiet")
    rep["issues"] = issues
    if rep["kind"] == "system":
        rep["verdict"] = "draft"
        rep["why"] = "a system voice is draft quality: use a neural, host-native or human voice when any is reachable"
    else:
        rep["verdict"] = "pass" if not issues else "fail"
    print(json.dumps(rep, indent=2))
    if words is None:
        return 3
    return 0 if rep["verdict"] in ("pass", "draft") and not any("error rate" in i or "pace" in i for i in issues) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
