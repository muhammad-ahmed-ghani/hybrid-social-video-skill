#!/usr/bin/env python3
"""speech_rate.py - measure how fast THIS voice speaks THIS text, instead of trusting a constant.

Speech rate depends on the language, the voice, the style and the text. The format profiles carry
a starting prior only; the plan is only as good as its length arithmetic, so replace the prior with
a measurement as soon as any audio in the real voice exists (a 10 s sample is enough).

    python3 speech_rate.py measure --audio sample.wav --text "the words spoken in it"
    python3 speech_rate.py measure --audio vo.wav --beatmap beatmap.json [--write]

Units follow `textscript.speech_units`: words, or characters for scripts written without spaces.
Leading and trailing silence is excluded, so the figure is the speaking rate, not the file length.
`--write` stores it in the beat map: meta.wps (units per second), meta.rate_source "measured",
meta.rate_sample {seconds, units, audio}. The linter then treats duration checks as measured.

Exit: 0 ok | 2 usage | 3 audio unreadable or no speech found.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, ffprobe_json, have, load_json, parse_args  # noqa: E402
from textscript import speech_units  # noqa: E402


def speaking_window(audio: str, noise_db: int = -35, min_sil: float = 0.15) -> tuple[float, float, float]:
    """(start, end, total) of the sound in the file, from silencedetect."""
    total = float(ffprobe_json(audio).get("format", {}).get("duration", 0) or 0)
    if total <= 0:
        raise ValueError("cannot read the audio duration")
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", audio, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_sil}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    start = ends[0] if starts and starts[0] <= 0.05 and ends else 0.0
    end = total
    if starts and (len(starts) > len(ends) or (ends and ends[-1] >= total - 0.05)):
        end = starts[-1]
    return max(start, 0.0), min(end, total), total


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"write"})
    if not pos or pos[0] != "measure":
        eprint(__doc__)
        return 2
    audio = opt.get("audio")
    if not audio or not Path(str(audio)).is_file() or not have("ffmpeg") or not have("ffprobe"):
        eprint("--audio FILE is required, and ffmpeg and ffprobe must be installed")
        return 3
    bm = load_json(opt["beatmap"]) if opt.get("beatmap") else None
    if opt.get("text"):
        text = str(opt["text"])
    elif bm:
        text = " ".join((b.get("tts_text") or b.get("text") or "") for b in bm.get("beats", []))
    else:
        eprint("give --text, or --beatmap to take the spoken text from every beat")
        return 2
    units = speech_units(text)
    try:
        start, end, total = speaking_window(audio)
    except ValueError as exc:
        eprint(str(exc))
        return 3
    secs = end - start
    if units <= 0 or secs < 1.0:
        eprint(f"no usable sample: {units} units over {secs:.2f} s of speech")
        return 3
    rate = round(units / secs, 3)
    out = {"units": units, "speech_seconds": round(secs, 2), "file_seconds": round(total, 2),
           "units_per_second": rate, "audio": str(audio)}
    if opt.get("write") and bm is not None:
        meta = bm.setdefault("meta", {})
        meta["wps"] = rate
        meta["rate_source"] = "measured"
        meta["rate_sample"] = {"seconds": out["speech_seconds"], "units": units, "audio": Path(str(audio)).name,
                               "measured": time.strftime("%Y-%m-%d")}
        Path(opt["beatmap"]).write_text(json.dumps(bm, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        out["written"] = str(opt["beatmap"])
    elif opt.get("write"):
        eprint("--write needs --beatmap")
        return 2
    print(json.dumps(out, indent=2))
    eprint(f"[rate] {units} units in {secs:.1f} s of speech = {rate} units/s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
