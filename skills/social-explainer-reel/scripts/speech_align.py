"""speech_align.py - shared helpers: normalise text to spoken tokens, align a transcript to a script.

Used by voice_check.py, host_assemble.py and the `spans` command below. Stdlib only (the command needs faster-whisper and ffmpeg).

    python3 speech_align.py spans --audio vo.wav --beatmap episode/beatmap.json --out episode/ [--snap 0.4] [--lang es]

`spans` turns a plain voice-over into per-beat spans and per-word times: it transcribes the audio locally, aligns the words to the script
of each beat, snaps beat boundaries to the real pauses (ffmpeg silencedetect, because a recogniser's word start can lag by a quarter of
a second), and writes words.json, spans.json ([{id,start,end}]) and timing.json (the format host_assemble.py writes: beats with their
words, and the duration). The language comes from meta.language_tag (override with --lang); an English-only model is never used on
another language. Exit 0 ok | 2 usage | 3 no recogniser | 4 too few words matched.
 English number words are handled for 0-999
(digits in a script are spoken as words, and a transcriber may return either); other languages compare
their tokens as written, so a language with its own digit words should pass `numbers=False` and list its
number words in the beat map (`meta.number_words`).
"""
from __future__ import annotations

import difflib
import re

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def number_words(n: int) -> list[str]:
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [_ONES[n // 100], "hundred"] + (number_words(n % 100) if n % 100 else [])
    return [str(n)]


_ES_ONES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece", "catorce",
            "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidos", "veintitres", "veinticuatro",
            "veinticinco", "veintiseis", "veintisiete", "veintiocho", "veintinueve"]
_ES_TENS = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
_ES_HUND = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
PERCENT = {"en": ["percent"], "es": ["por", "ciento"], "pt": ["por", "cento"], "fr": ["pour", "cent"], "de": ["prozent"], "it": ["per", "cento"]}


def _strip_accents(w: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")


def number_words_lang(n: int, lang: str) -> list[str] | None:
    """Spoken words for 0-999 in a language that has a table (en, es); None otherwise (the digits are then left as written)."""
    if lang == "en":
        return number_words(n)
    if lang == "es" and n < 1000:
        if n < 30:
            return [_ES_ONES[n]]
        if n < 100:
            return [_ES_TENS[n // 10]] + (["y", _ES_ONES[n % 10]] if n % 10 else [])
        if n == 100:
            return ["cien"]
        return [_ES_HUND[n // 100]] + (number_words_lang(n % 100, "es") or [] if n % 100 else [])
    return None


def tokens(text: str, numbers: bool = True, lang: str = "en") -> list[str]:
    """Lower-cased spoken tokens: hyphens and punctuation split words, accents are folded for comparison, digits become words (0-999)
    in languages that have a table, and a percent sign becomes the spoken word. Other languages keep digits as written."""
    out: list[str] = []
    text = text.replace("%", f" {' '.join(PERCENT.get(lang, PERCENT['en']))} ")
    for w in re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE):
        w = _strip_accents(w)
        words = number_words_lang(int(w), lang) if (numbers and w.isdigit() and int(w) < 1000) else None
        out += words if words else [w]
    return out


def display_tokens(word: str, numbers: bool = True, lang: str = "en") -> list[str]:
    return tokens(word, numbers, lang)


def align(expected: list[str], heard: list[str]) -> dict[int, int]:
    """Map index in `expected` -> index in `heard` for the tokens that match, in order."""
    sm = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
    return {blk.a + i: blk.b + i for blk in sm.get_matching_blocks() for i in range(blk.size)}


def wer(expected: list[str], heard: list[str]) -> float:
    """Word error rate by Levenshtein distance over tokens (0 = identical)."""
    n, m = len(expected), len(heard)
    if n == 0:
        return 0.0 if m == 0 else 1.0
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (expected[i - 1] != heard[j - 1]))
        prev = cur
    return prev[m] / n


# ----------------------------------------------------------------------------- spans command
def silences(audio: str, noise_db: int = -35, min_s: float = 0.12) -> list[tuple[float, float]]:
    import subprocess
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", audio, "-af", f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def beat_timings(bm: dict, heard: list[tuple[str, float, float]], lang: str, sil: list[tuple[float, float]], snap: float = 0.4) -> dict:
    """Align `heard` (token, start, end) to the beats' text; return {"beats": [...], "matched": n, "expected": m}."""
    use_num = lang in ("en", "es")
    exp: list[str] = []
    disp: list[dict] = []
    for b in bm["beats"]:
        for w in b["text"].split():
            t = tokens(w, use_num, lang)
            if t:
                disp.append({"beat": b["id"], "word": w, "lo": len(exp), "hi": len(exp) + len(t) - 1})
                exp += t
    match = align(exp, [h[0] for h in heard])
    n = len(exp)
    st: list[float | None] = [None] * n
    en: list[float | None] = [None] * n
    for i, j in match.items():
        st[i], en[i] = heard[j][1], heard[j][2]
    for i in range(n):
        if st[i] is None:
            p = max((x for x in range(i) if st[x] is not None), default=None)
            q = min((x for x in range(i + 1, n) if st[x] is not None), default=None)
            a = en[p] if p is not None else 0.0
            z = st[q] if q is not None else a + 0.3
            gap = [x for x in range(i, n) if st[x] is None and (q is None or x < q)]
            for g, x in enumerate(gap):
                st[x], en[x] = a + g * (z - a) / len(gap), a + (g + 1) * (z - a) / len(gap)
    for d in disp:
        d["s"], d["e"] = round(st[d["lo"]], 3), round(en[d["hi"]], 3)
    beats = []
    for b in bm["beats"]:
        ws = [{"word": d["word"], "s": d["s"], "e": d["e"]} for d in disp if d["beat"] == b["id"]]
        beats.append({"id": b["id"], "s": ws[0]["s"], "e": ws[-1]["e"], "words": ws})
    # snap each boundary to the real pause between two beats
    for k in range(1, len(beats)):
        prev, cur = beats[k - 1], beats[k]
        for a, z in sil:
            if z >= prev["e"] - 0.1 and a <= cur["s"] + snap and abs(z - cur["s"]) <= snap and z > prev["e"] - 0.1:
                if z > cur["s"]:                       # the recogniser started the beat early, inside the pause
                    shift = z - cur["s"]
                    for w in cur["words"][:1]:
                        w["s"] = round(z, 3)
                    cur["s"] = round(z, 3)
                    _ = shift
                if a < prev["e"]:
                    prev["e"] = round(max(a, prev["words"][-1]["s"] + 0.05), 3)
                    prev["words"][-1]["e"] = min(prev["words"][-1]["e"], prev["e"])
                break
    return {"beats": beats, "matched": len(match), "expected": n}


def _model_for(lang: str):
    from faster_whisper import WhisperModel
    names = ["base.en", "base", "tiny.en"] if lang == "en" else ["base", "small", "tiny"]
    last = None
    for name in names:
        try:
            return WhisperModel(name, device="cpu", compute_type="int8")
        except Exception as exc:                         # not cached and no network: try the next size
            last = exc
    raise RuntimeError(f"no speech model could be loaded for '{lang}': {last}")


def main(argv: list[str]) -> int:
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hx_common import eprint, parse_args
    pos, opt = parse_args(argv, flags={"help", "h"})
    if opt.get("help") or opt.get("h") or not pos:
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    if pos[0] != "spans" or not (opt.get("audio") and opt.get("beatmap") and opt.get("out")):
        eprint("usage: speech_align.py spans --audio FILE --beatmap FILE --out DIR")
        return 2
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        eprint("faster-whisper is required to read word times from the audio (pip install faster-whisper)")
        return 3
    bm = json.loads(Path(opt["beatmap"]).read_text(encoding="utf-8"))
    lang = str(opt.get("lang") or bm.get("meta", {}).get("language_tag") or "en")[:2].lower()
    model = _model_for(lang)
    segs, _ = model.transcribe(str(opt["audio"]), word_timestamps=True, language=lang)
    heard = [(t, w.start, w.end) for s in segs for w in s.words for t in tokens(w.word, lang in ("en", "es"), lang)]
    res = beat_timings(bm, heard, lang, silences(str(opt["audio"])), float(opt.get("snap", 0.4)))
    if res["matched"] < 0.8 * res["expected"]:
        eprint(f"only {res['matched']} of {res['expected']} words were heard: the voice mispronounces or the language is wrong")
        return 4
    import subprocess
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(opt["audio"])],
                               capture_output=True, text=True).stdout.strip() or 0)
    out = Path(opt["out"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "words.json").write_text(json.dumps([{"w": t, "start": round(a, 3), "end": round(b, 3)} for t, a, b in heard], indent=1))
    (out / "spans.json").write_text(json.dumps([{"id": b["id"], "start": b["s"], "end": b["e"]} for b in res["beats"]], indent=1))
    (out / "timing.json").write_text(json.dumps({"beats": res["beats"], "duration": round(dur, 3), "language": lang}, indent=1))
    print(json.dumps({"beats": len(res["beats"]), "matched": res["matched"], "expected": res["expected"], "duration": round(dur, 2), "out": str(out)}))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
