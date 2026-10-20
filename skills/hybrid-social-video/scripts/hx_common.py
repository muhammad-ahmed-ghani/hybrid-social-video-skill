"""hx_common.py - shared helpers for the hybrid-social-video scripts.

Stdlib only (PIL is optional and only used by contact_sheet / animatic).
Data files live in ../data and are the single source of truth for thresholds,
format profiles and platform specs: scripts read them, docs cite them.
Prices are NOT data files: they are discovered per environment (cost_plan.py, references/14-cost-scout.md).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textscript import speech_units  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"

LAYERS = ("code", "ai_image", "ai_video", "stock", "capture", "host", "real")
AI_LAYERS = ("ai_image", "ai_video")
ROLES = ("hook", "context", "build", "turn", "reveal", "payoff", "loop",
         # narrative and series roles: a cold open is the hook of a story, a tag or cliffhanger can close it
         "cold-open", "title", "recap", "setup", "escalate", "punchline", "tag", "cliffhanger")
OPENING_ROLES = ("hook", "cold-open")
CLOSING_ROLES = ("payoff", "loop", "tag", "cliffhanger")
TIERS = ("R0", "R1", "R2", "R3")

# bracketed performance tags such as [excited] or [pause] must never reach captions
_TAG_RE = re.compile(r"\[[^\]]{1,24}\]")


def load_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def data(name: str):
    """Load ../data/<name>.json."""
    return load_json(DATA_DIR / f"{name}.json")


def word_count(text: str) -> int:
    """Speech units in a text: words, or characters for scripts written without spaces. The unit
    is read from the text itself (textscript.speech_units), so no language is assumed."""
    return speech_units(text)


def est_beat_seconds(beat: dict, wps: float) -> float:
    """Spoken duration of one beat: words / wps plus the silent hold, unless est_seconds overrides."""
    if isinstance(beat.get("est_seconds"), (int, float)) and beat["est_seconds"] > 0:
        return float(beat["est_seconds"])
    n = word_count(beat.get("text", ""))
    hold = float(beat.get("hold_seconds", 0) or 0)
    return n / wps + hold if n else max(hold, 0.0)


def have(binary: str) -> bool:
    return shutil.which(binary) is not None


def run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def ffprobe_json(path: str | Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", str(path)], timeout=60)
    try:
        return json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def eprint(*a, **k) -> None:
    print(*a, file=sys.stderr, **k)


def parse_args(argv: list[str], flags: set[str] | None = None):
    """Tiny argv parser: returns (positional, options). `flags` = boolean
    switches that take no value."""
    flags = flags or set()
    opt: dict = {}
    pos: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            body = a[2:]
            if "=" in body:
                k, v = body.split("=", 1)
                opt[k] = v
            elif body in flags:
                opt[body] = True
            elif i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                opt[body] = argv[i + 1]
                i += 1
            else:
                opt[body] = True
        else:
            pos.append(a)
        i += 1
    return pos, opt
