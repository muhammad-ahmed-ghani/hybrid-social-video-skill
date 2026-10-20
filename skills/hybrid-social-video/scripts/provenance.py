#!/usr/bin/env python3
"""provenance.py - which AI models and tools made what, recorded at the moment of use.

    python3 provenance.py init   --episode ep --director "<the model you run as>"
    python3 provenance.py add    --episode ep --role image --tool <tool> --model <id> --provider <vendor> --runs hosted \\
                                 --used-for "host portrait" [--beats 1,2] [--request-id ID] [--asset path] \\
                                 [--data-sent "text prompt"] [--realism photoreal|stylised|none] [--depicts fictional|real|none] \\
                                 [--licence "..."] [--ai false] [--in-output false] [--note "..."]
    python3 provenance.py report --episode ep [--json]       # the AI-use statement and the disclosure verdict
    python3 provenance.py check  --episode ep [--beatmap beatmap.json]   # exit 1 on a gap

Roles: script, code, image, video, host, tts, stt, music, sfx, captions, human-voice, other. An entry says what ran
(tool, model id, provider, local or hosted), what it was used for, which beats, the request id, what data left the
machine, how realistic the output is and whether it depicts a real person. `--in-output false` records a test or an asset that is not in the delivered video (it is listed but
leaves the disclosure verdict). `--ai false` records a non-AI tool or a
human contribution (a real recording) so the statement is complete both ways. The director (the model that wrote the
plan, script and code) is recorded once at init, and a speech recogniser used only for timings counts as an AI model.
The file is episode/provenance.json. `check` fails when a generated layer in the beat map has no entry, when a voice
exists with no entry, or when an entry is missing its model, provider or purpose. `report` prints a statement for the
final note and a disclosure verdict derived from the entries, never from memory.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402

ROLES = {"script", "code", "image", "video", "host", "tts", "stt", "music", "sfx", "captions", "human-voice", "other"}
LAYER_ROLES = {"ai_image": {"image"}, "ai_video": {"video", "host"}, "host": {"host", "video"}}
VOICE_ROLES = {"tts", "host", "human-voice"}


def _path(ep: str) -> Path:
    return Path(ep) / "provenance.json"


def _load(ep: str) -> dict:
    p = _path(ep)
    if not p.is_file():
        raise FileNotFoundError(f"{p} is missing: run `provenance.py init --episode {ep} --director <model>` first")
    return json.loads(p.read_text(encoding="utf-8"))


def _truthy(v) -> bool:
    return str(v).lower() not in ("false", "0", "no")


def verdict(entries: list[dict]) -> list[str]:
    """Plain-language disclosure verdict from the entries (rules in references/08-governance.md)."""
    out: list[str] = []
    ai = [e for e in entries if e.get("ai", True) and e.get("in_output", True)]
    person = [e for e in ai if e.get("role") in ("host", "video", "image") and e.get("realism") == "photoreal"
              and e.get("depicts") in ("fictional", "real", None, "")]
    if any(e.get("depicts") == "real" for e in person):
        out.append("REQUIRED: photoreal AI of a real person or event. Do not present it as footage; use the platform AI label and an on-screen label.")
    elif person:
        out.append("LABEL: photoreal AI-generated people or scenes appear (a fictional presenter). Turn on the platform's AI-content label and say so in the description.")
    synth_voice = [e for e in ai if e.get("role") == "tts"]
    if any(e.get("role") == "host" for e in ai):
        out.append("NOTE: the host's face and speech are AI-generated; say so in the description (the platform label covers the face, the line covers the voice).")
    if synth_voice:
        out.append("NOTE: the narration is a synthetic voice; say so in the description. Platforms rarely require a label for a clearly non-deceptive synthetic narrator.")
    if not out and ai:
        out.append("NONE REQUIRED: AI was used only for non-realistic or assistive work (script, code, timing, stylised graphics). Still list the models.")
    if not ai:
        out.append("NONE: no AI models recorded.")
    return out


def statement(data: dict) -> str:
    lines = [f"Director: {data.get('director') or 'not recorded'} (wrote the plan, script and code)."]
    rows = data.get("entries", [])
    if rows:
        lines.append("")
        lines.append("| Role | Model | Tool | Provider | Runs | Used for | Beats |")
        lines.append("|---|---|---|---|---|---|---|")
        for e in rows:
            tag = ("" if e.get("ai", True) else " (not AI)") + ("" if e.get("in_output", True) else " (not in the output)")
            lines.append(f"| {e.get('role')}{tag} | {e.get('model') or '-'} | {e.get('tool') or '-'} | {e.get('provider') or '-'} | "
                         f"{e.get('runs') or '-'} | {e.get('used_for') or '-'} | {','.join(map(str, e.get('beats', []))) or '-'} |")
    lines.append("")
    lines += [f"Disclosure: {v}" for v in verdict(rows)]
    sent = sorted({e["data_sent"] for e in rows if e.get("data_sent") and e.get("runs") == "hosted"})
    if sent:
        lines.append("Data sent to hosted providers: " + "; ".join(sent) + ".")
    return "\n".join(lines)


def check(data: dict, beatmap: dict | None, ep: str) -> list[str]:
    problems: list[str] = []
    if not data.get("director"):
        problems.append("no director model recorded (provenance.py init --director ...)")
    rows = data.get("entries", [])
    for i, e in enumerate(rows):
        miss = [k for k in ("role", "model", "provider", "runs", "used_for") if not e.get(k)]
        if e.get("role") == "human-voice" or e.get("ai") is False:
            miss = [k for k in miss if k not in ("model", "provider", "runs")]
        if miss:
            problems.append(f"entry {i + 1} ({e.get('role', '?')}) lacks {', '.join(miss)}")
        if e.get("role") not in ROLES:
            problems.append(f"entry {i + 1} has an unknown role {e.get('role')!r}")
    if beatmap:
        for b in beatmap.get("beats", []):
            roles = LAYER_ROLES.get(b.get("layer"))
            if not roles:
                continue
            covered = any(e.get("role") in roles and (not e.get("beats") or b["id"] in e["beats"]) for e in rows)
            if not covered:
                problems.append(f"beat {b['id']} uses layer {b['layer']} but no {'/'.join(sorted(roles))} entry covers it")
        if (Path(ep) / "spans.json").is_file() or beatmap.get("audio", {}).get("voice"):
            if not any(e.get("role") in VOICE_ROLES for e in rows):
                problems.append("a voice exists but no tts, host or human-voice entry records where it came from")
    return problems


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"json", "help", "h"})
    if opt.get("help") or opt.get("h"):
        print(__doc__)
        return 0
    if not pos:
        eprint(__doc__)
        return 2
    cmd, ep = pos[0], opt.get("episode")
    if not ep:
        eprint("--episode DIR is required")
        return 2
    if cmd == "init":
        p = _path(ep)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if opt.get("director") not in (None, True):
                data["director"] = opt["director"]
        else:
            data = {"schema": "hybrid-provenance/1", "director": None if opt.get("director") in (None, True) else opt["director"],
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "entries": []}
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(json.dumps({"provenance": str(p), "director": data["director"], "entries": len(data["entries"])}))
        return 0
    try:
        data = _load(ep)
    except FileNotFoundError as exc:
        eprint(str(exc))
        return 3
    if cmd == "add":
        role = opt.get("role")
        if role not in ROLES:
            eprint(f"--role must be one of {sorted(ROLES)}")
            return 2
        e = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "role": role, "ai": _truthy(opt.get("ai", True))}
        for k_opt, k in (("tool", "tool"), ("model", "model"), ("provider", "provider"), ("runs", "runs"), ("used-for", "used_for"),
                         ("request-id", "request_id"), ("asset", "asset"), ("data-sent", "data_sent"), ("realism", "realism"),
                         ("depicts", "depicts"), ("licence", "licence"), ("note", "note")):
            if opt.get(k_opt) not in (None, True):
                e[k] = opt[k_opt]
        if opt.get("in-output") not in (None, True):
            e["in_output"] = _truthy(opt["in-output"])
        if opt.get("beats") not in (None, True):
            e["beats"] = [int(x) for x in str(opt["beats"]).split(",") if x.strip()]
        data["entries"].append(e)
        _path(ep).write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(json.dumps({"added": role, "model": e.get("model"), "entries": len(data["entries"])}))
        return 0
    if cmd == "report":
        if opt.get("json"):
            print(json.dumps({**data, "verdict": verdict(data.get("entries", []))}, indent=2, ensure_ascii=False))
        else:
            print(statement(data))
        return 0
    if cmd == "check":
        bm = None
        if opt.get("beatmap") not in (None, True):
            bm = json.loads(Path(opt["beatmap"]).read_text(encoding="utf-8"))
        problems = check(data, bm, ep)
        print(json.dumps({"ok": not problems, "problems": problems, "entries": len(data.get("entries", []))}))
        for p in problems:
            eprint(f"[provenance] {p}")
        return 1 if problems else 0
    eprint(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
