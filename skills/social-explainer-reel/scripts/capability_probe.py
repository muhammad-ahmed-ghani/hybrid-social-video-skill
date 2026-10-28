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

It also writes `ai_models`: what on this machine is an AI model or a synthetic-voice route (local speech models, TTS
modules and binaries, cached model weights, hosted gateways hinted by credential names), with a role, local or hosted,
and a note such as "DRAFT quality" for system voices. The agent fills `ai_models.director` and `ai_models.tool_models`.

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
            "fal", "piper", "whisper", "espeak-ng", "say", "rhubarb", "fc-list", "pdftotext"]
MODULES = ["PIL", "manim", "fal_client", "playwright", "numpy", "cv2", "torch", "transformers",
           "onnxruntime", "edge_tts", "TTS", "kokoro", "piper", "whisper", "faster_whisper",
           "pydub", "fontTools", "h5py"]
# What the AI-looking things on a machine are, so the agent knows what it is working with. Detection only.
AI_MODULES = {
    "faster_whisper": ("stt", "local", "speech-to-text, Whisper family"), "whisper": ("stt", "local", "speech-to-text, Whisper family"),
    "TTS": ("tts", "local", "Coqui text-to-speech"), "kokoro": ("tts", "local", "Kokoro neural text-to-speech"),
    "piper": ("tts", "local", "Piper small neural text-to-speech"),
    "edge_tts": ("tts", "hosted", "unofficial web endpoint: can be blocked (HTTP 403), no published price or terms"),
    "fal_client": ("gateway", "hosted", "fal.ai client: image, video, voice and music models, read ids from its catalog"),
    "torch": ("runtime", "local", "model runtime"), "transformers": ("runtime", "local", "model runtime"),
    "onnxruntime": ("runtime", "local", "model runtime"),
}
AI_BINARIES = {
    "say": ("tts", "local", "macOS system voices: DRAFT quality, never the final voice when anything better is reachable"),
    "espeak-ng": ("tts", "local", "formant synthesiser: DRAFT quality"),
    "piper": ("tts", "local", "Piper small neural text-to-speech"),
    "whisper": ("stt", "local", "Whisper CLI"), "fal": ("gateway", "hosted", "fal CLI"),
}
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


HF_SKILLS = ["hyperframes", "hyperframes-core", "hyperframes-creative", "hyperframes-animation", "hyperframes-cli", "faceless-explainer", "talking-head-recut",
             "general-video", "embedded-captions", "motion-graphics", "media-use"]


def _hyperframes() -> dict:
    """Is HyperFrames reachable? Its skills (listed by folder name in the usual agent skill folders), its CLI, and how to get it."""
    homes = [Path("~/.claude/skills"), Path("~/.agents/skills"), Path("~/.codex/skills"), Path(".claude/skills"), Path(".agents/skills")]
    found = sorted({n for h in homes for n in HF_SKILLS if (h.expanduser() / n / "SKILL.md").is_file()})
    return {"skills": found, "skills_installed": bool(found),
            "get_it": "npx skills add heygen-com/hyperframes (agents with a filesystem: Claude Code, Cursor, Codex); the hosted MCP "
                      "(https://mcp.heygen.com/mcp/hyperframes/, guide: https://hyperframes.heygen.com/guides/mcp) is for chat clients and "
                      "refuses compose and render from CLI agents. Read references/19-hyperframes.md"}


def _person_fx() -> dict:
    """Can person-aware effects (person_fx.py) run here, and how good would the matte be? Local facts only; never downloads."""
    have = {m: importlib.util.find_spec(m) is not None for m in ("numpy", "cv2", "PIL", "onnxruntime")}
    cached: dict = {}
    try:
        import fx_assets
        cached = {n: bool(fx_assets.verified(n)) for n in ("modnet", "yunet")}
        cached["fonts"] = sum(1 for n, sp in fx_assets.catalog().items() if sp["kind"] == "font" and fx_assets.verified(n))
    except Exception:
        pass
    ready = have["numpy"] and have["cv2"] and have["PIL"]
    matte = "modnet (cached)" if have["onnxruntime"] and cached.get("modnet") else ("modnet (will download once, 26 MB)" if have["onnxruntime"] else "grabcut (rough; pip install onnxruntime for the real matte)")
    return {"ready": ready, "modules": have, "assets_cached": cached, "matte": matte,
            "get_it": "pip install numpy opencv-python pillow onnxruntime  (then person_fx.py fetches the models and fonts it needs on first use; references/20-person-aware-effects.md)"}


def _voice_routes() -> dict:
    """Offline voice routes: the best local voice per language and any high-quality (Premium, Enhanced, Siri) voices."""
    try:
        from voice_render import list_voices
        voices = list_voices()
    except Exception:
        return {"engine": None, "voices": 0}
    if not voices:
        return {"engine": None, "voices": 0}
    best: dict[str, str] = {}
    for v in sorted((x for x in voices if x["quality"] != "novelty"), key=lambda x: x["score"]):
        best[v["locale"].split("_")[0]] = f"{v['name']} [{v['locale']}]"
    return {"engine": voices[0]["engine"], "voices": len(voices), "offline": True,
            "high_quality": [v["name"] for v in voices if v["quality"] == "system-hq"], "best_by_language": best,
            "note": "system voices are DRAFT quality unless listed in high_quality; Premium and Enhanced voices can be added in "
                    "System Settings > Accessibility > Spoken Content > System Voice > Manage Voices (free, offline)"}


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
    ai: list[dict] = []
    for m in loc["modules"]:
        if m in AI_MODULES:
            role, runs, note = AI_MODULES[m]
            ai.append({"id": m, "kind": "python module", "role": role, "runs": runs, "offline": runs == "local", "note": note})
    for b in loc["binaries"]:
        if b in AI_BINARIES:
            role, runs, note = AI_BINARIES[b]
            ai.append({"id": b, "kind": "binary", "role": role, "runs": runs, "offline": runs == "local", "note": note})
    for name, folders in caches.items():
        for f in folders:
            if f.startswith("models--"):
                ai.append({"id": f[len("models--"):].replace("--", "/"), "kind": f"{name} cache", "role": "model", "runs": "local", "offline": True,
                           "note": "cached weights: confirm what it does before relying on it"})
    out["hyperframes"] = _hyperframes()
    out["hyperframes"]["cli"] = loc.get("hyperframes_cli")
    out["person_fx"] = _person_fx()
    out["ai_models"] = {"local": ai, "hosted_hints": sorted(set(out["credentials_present"].values())),
                        "director": None, "tool_models": [], "voice_routes": _voice_routes()}
    if "fc-list" in loc["binaries"]:
        loc["installed_font_files"] = len(_run_all(["fc-list"]))
    out["notes"] = [
        "ai_models.director: write the model you run as (from your own context, never a guess); ai_models.tool_models: every model your image, video, voice and music tools expose, with ids read from the tool",
        "the agent's own MCP servers can be deferred or still connecting: search for them (ToolSearch) before concluding a layer is missing",
        "agent_tools: fill from your tool list (generators, MCP servers, media catalogs); a live catalog is the best price source",
        "credentials: environment names and CLI profile folders are hints; confirm access with the provider's own tool (for example its whoami or catalog call) before relying on it",
        "skills: fill from the skills you can load (hyperframes, a Manim skill, explainer-reel-skill ...)",
        "usage_windows: if the HyperFrames CLI is present, `npx hyperframes usage --json` reports allowance; record it or 'unknown'",
        "local models cost compute, not credits: ask the user what a local GPU run is worth",
    ]
    return out


def main(argv: list[str]) -> int:
    _, opt = parse_args(argv, flags={"help", "h", "json"})
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
        if not opt.get("json"):
            loc, ai = rep["local"], rep["ai_models"]
            vr = ai["voice_routes"]
            print(f"[probe] ffmpeg {'yes' if 'ffmpeg' in loc['binaries'] else 'NO'} | playwright {'yes' if 'playwright' in loc['modules'] else 'no'} | "
                  f"yt-dlp {'yes' if 'yt-dlp' in loc['binaries'] else 'no'} | "
                  f"{loc['cpu_count']} cpus, {loc['free_disk_gb']} GB free")
            hf = rep["hyperframes"]
            print(f"[probe] HyperFrames: skills {', '.join(hf['skills'][:4]) + (' ...' if len(hf['skills']) > 4 else '') if hf['skills'] else 'NOT installed'}"
                  f" | cli {hf['cli'] or 'no'}" + ("" if hf["skills_installed"] else " | get it: npx skills add heygen-com/hyperframes (references/19-hyperframes.md)"))
            pf = rep["person_fx"]
            print(f"[probe] person-aware effects: {'ready' if pf['ready'] else 'NOT ready (' + pf['get_it'] + ')'} | matte: {pf['matte']}")
            print(f"[probe] voices: {vr.get('engine') or 'none'} ({vr.get('voices', 0)}); high-quality local: {', '.join(vr.get('high_quality') or []) or 'none'}; "
                  f"best by language: " + "; ".join(f"{k}: {(vr.get('best_by_language') or {})[k]}" for k in ("en", "es", "fr", "de", "pt", "it", "ar", "hi", "ur", "ja", "zh", "ko") if k in (vr.get("best_by_language") or {})))
            print("[probe] AI models here: " + ", ".join(f"{m['id']} ({m['role']}, {'offline' if m['offline'] else 'online'})" for m in ai["local"] if m["role"] != "runtime") + "; "
                  f"hosted hints: {', '.join(ai['hosted_hints']) or 'none'}; provider profiles: {', '.join(rep['provider_profiles_present']) or 'none'}")
            print(f"[probe] full detail: {p} (use --json to print it all)")
            return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
