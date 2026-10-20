#!/usr/bin/env python3
"""voice_render.py - the free, offline voice route: pick the best local voice for the language and render the script.

    python3 voice_render.py --list [--lang es-MX]
    python3 voice_render.py --beatmap episode/beatmap.json --out episode/vo.wav [--voice NAME] [--target-seconds 30] [--lang es-MX]

Use it when no better voice is reachable (the voice ladder, references/06-sound.md). It never asks: it ranks the voices installed on
this machine for the language (macOS `say`, else espeak-ng), drops novelty and classic robotic voices, prefers Premium, Enhanced and
Siri voices (a neural voice that is free and offline: they count as the neural rung, not as draft) and then the well-known standard
voices, and renders the whole script in one call so the prosody does not reset at beat boundaries. A pause of 0.26 s plus each
beat's `hold_seconds` is placed between beats. With --target-seconds it searches `say -r` to land near that length: the rate is
quantised (nearby values give an identical file), so it tries a few and keeps the closest. Output: a 48 kHz mono wav and a JSON line
with the voice, rate, seconds, and `quality`: `system-hq` (Premium, Enhanced or Siri) or `system` (draft: ship it only if nothing
better is reachable, and say so). Then run `speech_align.py spans` for word times and `voice_check.py --kind system` or
`system-hq` to check the words. Exit 0 ok | 2 usage | 3 no local voice engine.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402

NOVELTY = {"albert", "bad news", "bahh", "bells", "boing", "bubbles", "cellos", "wobble", "good news", "jester", "organ", "superstar",
           "trinoids", "whisper", "zarvox", "hysterical", "pipe organ", "deranged", "fred", "junior", "kathy", "ralph", "agnes", "bruce",
           "victoria", "princess", "grandma", "grandpa"}
PREFERRED = ["samantha", "daniel", "karen", "moira", "tessa", "alex", "ava", "allison", "susan", "monica", "paulina", "jorge", "juan",
             "diego", "angelica", "amelie", "thomas", "anna", "luca", "alice", "joana", "luciana", "kyoko", "yuna", "ting-ting", "milena"]


def list_voices() -> list[dict]:
    """Voices on this machine: name, locale, quality class, engine. macOS `say` first, then espeak-ng."""
    out: list[dict] = []
    if shutil.which("say"):
        r = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            m = re.match(r"^(.+?)\s+([a-z]{2,3}_[A-Za-z0-9]+)\s+#", line)
            if not m:
                continue
            name, loc = m.group(1).strip(), m.group(2)
            base = re.sub(r"\s*\(.*\)$", "", name).strip().lower()
            if re.search(r"premium|enhanced|siri", name, re.I):
                q, score = "system-hq", 4
            elif base in NOVELTY:
                q, score = "novelty", -9
            elif base in PREFERRED:
                q, score = "system", 2 + (len(PREFERRED) - PREFERRED.index(base)) / 100
            else:
                q, score = "system", 1
            if not any(o["name"] == name and o["locale"] == loc for o in out):          # `say -v ?` can list a voice twice
                out.append({"engine": "say", "name": name, "locale": loc, "quality": q, "score": score, "offline": True})
    elif shutil.which("espeak-ng"):
        r = subprocess.run(["espeak-ng", "--voices"], capture_output=True, text=True)
        for line in r.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                out.append({"engine": "espeak-ng", "name": parts[3], "locale": parts[1], "quality": "system", "score": 0.5, "offline": True})
    return out


def pick_voice(voices: list[dict], lang: str) -> dict | None:
    """Best voice for a language tag like 'es', 'es-MX' or 'es_MX': the exact locale first, then any locale of the language."""
    tag = lang.replace("-", "_")
    base = tag.split("_")[0].lower()
    cands = [v for v in voices if v["quality"] != "novelty" and v["locale"].lower().split("_")[0] == base]
    cands.sort(key=lambda v: (v["locale"].lower() == tag.lower(), v["score"]), reverse=True)
    return cands[0] if cands else None


def script_text(bm: dict) -> str:
    parts = []
    for b in bm["beats"]:
        parts.append((b.get("tts_text") or b["text"]).strip())
        parts.append(f"[[slnc {int(260 + 1000 * float(b.get('hold_seconds') or 0))}]]")
    return " ".join(parts[:-1])


def _dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout.strip() or 0)


def render_say(text: str, voice: str, rate: int | None, out: Path) -> float:
    with tempfile.TemporaryDirectory() as td:
        aiff = Path(td) / "v.aiff"
        cmd = ["say", "-v", voice, "-o", str(aiff)] + (["-r", str(rate)] if rate else []) + [text]   # the text is an argument: -f ignores -r
        subprocess.run(cmd, check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", "48000", "-ac", "1", str(out)], check=True)
    return _dur(out)


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"list", "help", "h"})
    if opt.get("help") or opt.get("h"):
        print(__doc__)
        return 0
    voices = list_voices()
    if not voices:
        eprint("no local voice engine found (macOS `say` or espeak-ng): the voice route is unavailable here")
        return 3
    lang = str(opt.get("lang") or "")
    if opt.get("list"):
        shown = [v for v in voices if not lang or v["locale"].lower().startswith(lang.replace("-", "_").lower()[:2])]
        print(json.dumps(sorted(shown, key=lambda v: -v["score"]), indent=1))
        return 0
    if not (opt.get("beatmap") and opt.get("out")):
        eprint(__doc__)
        return 2
    bm = json.loads(Path(opt["beatmap"]).read_text(encoding="utf-8"))
    lang = lang or str(bm.get("meta", {}).get("language_tag") or "en")
    v = next((x for x in voices if x["name"].lower() == str(opt["voice"]).lower()), None) if opt.get("voice") not in (None, True) else pick_voice(voices, lang)
    if not v:
        eprint(f"no local voice for '{lang}': the skill falls back to a hosted or neural route if one is reachable, else a draft in another language is wrong; stop and report")
        return 3
    out = Path(opt["out"])
    out.parent.mkdir(parents=True, exist_ok=True)
    text = script_text(bm)
    out.with_suffix(".txt").write_text(re.sub(r"\s*\[\[slnc \d+\]\]\s*", " ", text), encoding="utf-8")   # the plain script, for voice_check.py --text-file
    rate = None
    if v["engine"] != "say":
        subprocess.run(["espeak-ng", "-v", v["name"], "-w", str(out), re.sub(r"\[\[slnc \d+\]\]", ",", text)], check=True)
        secs = _dur(out)
    else:
        secs = render_say(text, v["name"], None, out)
        target = float(opt["target-seconds"]) if opt.get("target-seconds") not in (None, True) else None
        if target:
            tried = {None: secs}
            best = (abs(secs - target), None, secs)
            r = 175.0
            for _ in range(5):
                r = max(120.0, min(210.0, r * secs / target))   # above about 210 wpm a voice stops being intelligible
                ri = int(round(r / 5.0) * 5)
                if ri in tried:
                    ri += 5 if secs > target else -5
                if ri in tried:
                    break
                secs = render_say(text, v["name"], ri, out)
                tried[ri] = secs
                if abs(secs - target) < best[0]:
                    best = (abs(secs - target), ri, secs)
                if abs(secs - target) <= 0.4:
                    break
            rate, secs = best[1], render_say(text, v["name"], best[1], out)
    info = {"voice": v["name"], "locale": v["locale"], "engine": v["engine"], "rate": rate, "seconds": round(secs, 2),
            "quality": v["quality"], "draft": v["quality"] != "system-hq"}
    out.with_suffix(".json").write_text(json.dumps(info))                    # read by build_video.py to record the voice in provenance.json
    print(json.dumps({"voice": v["name"], "locale": v["locale"], "engine": v["engine"], "rate": rate, "seconds": round(secs, 2),
                      "quality": v["quality"], "out": str(out),
                      "draft": v["quality"] != "system-hq",
                      "note": "system voice: draft quality; ship only if nothing better is reachable" if v["quality"] != "system-hq" else "high-quality local voice"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
