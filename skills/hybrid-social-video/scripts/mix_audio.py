#!/usr/bin/env python3
"""mix_audio.py - final mix: the master voice untouched, a ducked synthesised bed, soft cues, then loudness normalisation.

    python3 mix_audio.py --voice build/host.mp4 --duration 36.0 --out build/mix.wav [--cues cues.json] [--no-bed] [--lufs -14]

--voice is any file with the master speech (the host video's own audio, or a voice-over). It is never retimed or
replaced. cues.json: {"hits": [seconds], "ticks": [seconds], "whooshes": [seconds]}: a low hit, a soft tick and a short
upward sweep, synthesised here (no samples, no licences). The bed is a quiet pad that ducks under speech. The chain is a
gentle compressor, a limiter and two-pass EBU R128 loudnorm to --lufs (default -14) with true peak -1.5 dBTP.
Cues belong to meaning: a tick where a state completes, a hit on the payoff, a sweep with a real transition. Needs numpy.
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402

SR = 48000


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h", "no-bed"})
    if opt.get("help") or opt.get("h") or not (opt.get("voice") and opt.get("duration") and opt.get("out")):
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    try:
        import numpy as np
    except ImportError:
        eprint("numpy is required")
        return 3
    D, out = float(opt["duration"]), Path(opt["out"])
    cues = {"hits": [], "ticks": [], "whooshes": []}
    if opt.get("cues") not in (None, True):
        cues.update(json.loads(Path(opt["cues"]).read_text()))
    tmp = out.with_suffix(".voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", opt["voice"], "-vn", "-ac", "1", "-ar", str(SR), str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    tmp.unlink()
    n = int(D * SR); t = np.arange(n) / SR
    voice = np.zeros(n); voice[:min(n, len(raw))] = raw[:n]
    rng = np.random.default_rng(11)

    def add(buf, start, sig):
        i = int(start * SR); j = min(len(buf), i + len(sig))
        if 0 <= i < len(buf):
            buf[i:j] += sig[:j - i]
    tt = np.arange(int(0.15 * SR)) / SR
    tick = np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt / 0.02) * 0.22
    th = np.arange(int(0.6 * SR)) / SR
    hit = np.sin(2 * np.pi * (55 + 95 * np.exp(-th / 0.05)).cumsum() / SR) * np.exp(-th / 0.14) * 0.5 + rng.standard_normal(len(th)) * np.exp(-th / 0.03) * 0.06
    tw = np.arange(int(0.5 * SR)) / SR
    noise = rng.standard_normal(len(tw)); wh = np.zeros(len(tw)); y = 0.0
    for i in range(len(tw)):
        y += (0.02 + 0.5 * tw[i] / 0.5) * (noise[i] - y); wh[i] = y
    whoosh = wh * np.sin(np.pi * np.clip(tw / 0.5, 0, 1)) ** 2 * 0.55
    sfx = np.zeros(n)
    for c in cues["ticks"]: add(sfx, c, tick)
    for c in cues["hits"]: add(sfx, c, hit)
    for c in cues["whooshes"]: add(sfx, c, whoosh)
    bed = np.zeros(n)
    if not opt.get("no-bed"):
        for f, a in [(110, .5), (164.81, .35), (220, .3), (261.63, .22), (329.63, .12)]:
            bed += a * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.07 * t)) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t + f))
        bed *= np.minimum(1, t / 1.5) * np.minimum(1, (D - t) / 1.5) * 0.05
        win = int(0.05 * SR); env = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, "same"))
        env = np.convolve(env, np.ones(int(0.15 * SR)) / int(0.15 * SR), "same")
        bed *= 1 - 0.7 * np.clip(env / 0.08, 0, 1)
    mix = np.tanh((voice + bed + sfx) * 0.9)
    pre = out.with_suffix(".pre.wav")
    with wave.open(str(pre), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    lufs = str(opt.get("lufs", -14))
    chain = f"acompressor=threshold=0.12:ratio=3:attack=5:release=90,alimiter=limit=0.9,loudnorm=I={lufs}:TP=-1.5:LRA=7"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(pre), "-af", chain + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    j = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    af = chain + f":measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pre), "-af", af, "-ar", "48000", "-ac", "2", str(out)], check=True)
    pre.unlink()
    print(json.dumps({"mix": str(out), "cues": {k: len(v) for k, v in cues.items()}, "input_lufs": j["input_i"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
