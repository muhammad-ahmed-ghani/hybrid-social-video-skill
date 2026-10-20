#!/usr/bin/env python3
"""capability_probe.py - what can THIS machine run? Local facts only; never prints a secret.

    python3 capability_probe.py --out episode/capabilities.json

Records: binaries (ffmpeg, ffprobe, node, npx, python3, manim, latex, dvisvgm, a headless
Chromium, nvidia-smi, local speech tools, the fal CLI), importable Python modules (PIL, manim,
fal_client, playwright, local TTS and speech-to-text libraries), the HyperFrames CLI if already
installed (never downloads it), CPU count, free disk, a GPU if present, installed font count,
the NAMES of cached model folders (never their contents), and provider access: the NAMES of
credentials in the environment and the NAMES of provider CLI profile folders (never the values).
Credentials can live in a CLI profile instead of an environment variable, so an empty
`credentials_present` does not mean no access: the scout confirms with the provider's own tool.

It cannot see the agent's own tools. The scout fills `agent_tools` by reading its tool list
(image, video, voice, music generators, MCP servers, media catalogs) and `skills` from the
skills it can load. Local models cost compute, not credits: a local GPU is a capability with
its own price (electricity, time), which the scout asks the user about.

Exit 0 always (a probe that finds nothing still reports it).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402

BINARIES = ["ffmpeg", "ffprobe", "node", "npx", "python3", "manim", "latex", "dvisvgm", "nvidia-smi",
            "chromium", "chromium-browser", "google-chrome", "chrome-headless-shell", "yt-dlp",
            "fal", "piper", "whisper", "espeak-ng", "rhubarb", "fc-list", "pdftotext"]
MODULES = ["PIL", "manim", "fal_client", "playwright", "numpy", "cv2", "torch", "transformers",
           "onnxruntime", "edge_tts", "TTS", "kokoro", "piper", "whisper", "faster_whisper",
           "pydub", "fontTools", "h5py"]
# folders that hold a provider login or a model cache; only their NAMES are reported
PROFILE_DIRS = ["~/.fal", "~/.config/fal", "~/.elevenlabs", "~/.config/elevenlabs", "~/.openai",
                "~/.replicate", "~/.config/replicate", "~/.heygen", "~/.config/gcloud"]
CACHE_DIRS = {"huggingface": "~/.cache/huggingface/hub", "whisper": "~/.cache/whisper",
              "torch": "~/.cache/torch/hub", "piper": "~/.local/share/piper"}
# credential NAMES that hint at a reachable provider. Detection only: values are never read into output.
CRED_HINTS = {
    "FAL_KEY": "fal.ai (image, video, avatar, voice, music)",
    "OPENAI_API_KEY": "OpenAI (image, speech)",
    "GOOGLE_API_KEY": "Google (image, video, speech)", "GEMINI_API_KEY": "Google (image, video, speech)",
    "ELEVENLABS_API_KEY": "ElevenLabs (voice, music, transcription)",
    "XAI_API_KEY": "xAI", "ANTHROPIC_API_KEY": "Anthropic", "OPENROUTER_API_KEY": "OpenRouter",
    "REPLICATE_API_TOKEN": "Replicate", "HEYGEN_API_KEY": "HeyGen", "CARTESIA_API_KEY": "Cartesia",
    "RUNWAY_API_KEY": "Runway", "LUMA_API_KEY": "Luma", "STABILITY_API_KEY": "Stability",
    "PEXELS_API_KEY": "Pexels stock", "PIXABAY_API_KEY": "Pixabay stock", "MINIMAX_API_KEY": "MiniMax",
}


def _run(cmd: list[str], timeout: int = 20) -> str:
    """First output line of a command that exited 0, else ''. A failure message is not a version."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return ""
    text = (r.stdout or "").strip() if r.returncode == 0 else ""
    return text.splitlines()[0] if text else ""


def _run_all(cmd: list[str], timeout: int = 20) -> list[str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.splitlines() if r.returncode == 0 else []
    except Exception:
        return []


def probe() -> dict:
    out: dict = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "local": {}, "credentials_present": {},
                 "agent_tools": [], "skills": [], "usage_windows": None}
    loc = out["local"]
    loc["binaries"] = {b: shutil.which(b) for b in BINARIES if shutil.which(b)}
    loc["modules"] = [m for m in MODULES if importlib.util.find_spec(m) is not None]
    loc["cpu_count"] = os.cpu_count()
    loc["free_disk_gb"] = round(shutil.disk_usage(".").free / 1e9, 1)
    if "ffmpeg" in loc["binaries"]:
        loc["ffmpeg_version"] = _run(["ffmpeg", "-version"])
    if "manim" in loc["binaries"]:
        loc["manim_version"] = _run(["manim", "--version"])
    if "nvidia-smi" in loc["binaries"]:
        loc["gpu"] = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    if "npx" in loc["binaries"]:
        # --no-install: report an existing HyperFrames CLI, never fetch one
        loc["hyperframes_cli"] = _run(["npx", "--no-install", "hyperframes", "--version"], timeout=30) or None
    out["credentials_present"] = {k: v for k, v in CRED_HINTS.items() if os.environ.get(k)}
    if "fc-list" in loc["binaries"]:
        installed = {x.split("|")[0].strip().casefold() for x in _run_all(["fc-list", "--format", "%{family}\\n"]) for x in x.split(",")}
        try:
            idents = json.loads((Path(__file__).resolve().parent.parent / "data" / "identities.json").read_text())
        except (OSError, ValueError):
            idents = {}
        wanted = {}
        for iid, ident in (idents.get("identities") or idents).items():
            fonts = (ident.get("fonts") or {}) if isinstance(ident, dict) else {}
            names = [re.sub(r"\s+(\d{3}|uppercase|italic|bold|regular)\b.*$", "", str(v).split("(")[0].split(";")[0].strip(), flags=re.I)
                     for k, v in fonts.items() if k in ("hero", "body", "numbers_font") and v]
            wanted[iid] = {n: (n.casefold() in installed) for n in names}
        loc["identity_fonts_installed"] = wanted
    out["provider_profiles_present"] = [d for d in PROFILE_DIRS if Path(d).expanduser().is_dir()]
    caches = {}
    for name, d in CACHE_DIRS.items():
        root = Path(d).expanduser()
        if root.is_dir():
            caches[name] = sorted(x.name for x in root.iterdir())[:40]
    loc["model_caches"] = caches
    if "fc-list" in loc["binaries"]:
        loc["installed_font_files"] = len(_run_all(["fc-list"]))
    out["notes"] = [
        "agent_tools: fill from your tool list (generators, MCP servers, media catalogs); a live catalog is the best price source",
        "credentials: environment names and CLI profile folders are hints; confirm access with the provider's own tool (for example its whoami or catalog call) before relying on it",
        "skills: fill from the skills you can load (hyperframes, a Manim skill, explainer-reel-skill ...)",
        "usage_windows: if the HyperFrames CLI is present, `npx hyperframes usage --json` reports allowance; record it or 'unknown'",
        "local models cost compute, not credits: ask the user what a local GPU run is worth",
    ]
    return out


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h"})
    if opt.get("help") or opt.get("h"):
        print(__doc__)
        return 0
    rep = probe()
    text = json.dumps(rep, indent=2)
    if opt.get("out"):
        p = Path(opt["out"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        eprint(f"[probe] wrote {p}")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
