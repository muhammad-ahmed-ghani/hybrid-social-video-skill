#!/usr/bin/env python3
"""encode_master.py - frames + mix -> master.mp4 with the delivery profile from data/platforms.json.

    python3 encode_master.py --frames build/frames --audio build/mix.wav --out episode/master.mp4 [--fps 30] [--crf 18]

Encodes the PNG sequence (NNNNN.png) and the mix with the profile the QC expects: H.264 High, yuv420p, BT.709 tagged,
AAC-LC 48 kHz at the bitrate in platforms.json, moov atom first (+faststart), the length of the shorter stream. Prints one
JSON line with the path, duration and size. Run qc_master.py next. Exit 0 ok | 2 usage | 1 ffmpeg failed.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, parse_args  # noqa: E402


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h"})
    if opt.get("help") or opt.get("h") or not (opt.get("frames") and opt.get("audio") and opt.get("out")):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    dl = data("platforms")["delivery"]
    fps = int(opt.get("fps", dl.get("preferred_fps", 30)))
    m = re.search(r"(\d+)\s*kbps", str(dl.get("audio", "")))
    abr = f"{m.group(1)}k" if m else "384k"
    out = Path(opt["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(Path(opt["frames"]) / "%05d.png"), "-i", str(opt["audio"]),
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", str(opt.get("crf", 18)), "-preset", "medium",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "aac", "-b:a", abr, "-ar", "48000", "-movflags", "+faststart", "-shortest", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        eprint(r.stderr.strip()[-600:])
        return 1
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True).stdout.strip() or 0)
    print(json.dumps({"master": str(out), "seconds": round(dur, 2), "mb": round(out.stat().st_size / 1e6, 1), "fps": fps, "audio_kbps": abr}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
