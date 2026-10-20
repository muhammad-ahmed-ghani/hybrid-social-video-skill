#!/usr/bin/env python3
"""cost_plan.py - price a beat map from LIVE prices, never from numbers baked into the skill.

Prices, model lineups, billing units and promotions differ per environment and change
weekly, so this skill ships none. A cost scout (references/14-cost-scout.md) discovers what
THIS environment can run and what it costs, and records each price in an episode pricebook
with its source and timestamp. This script computes the plan's cost from that pricebook and
emits the questions a human must answer. An unknown price is an answer: it is reported as
missing and never guessed.

    cost_plan.py init  --out episode/pricebook.json
    cost_plan.py add   --pricebook P --capability ai_video --provider <p> --model <m> --unit second \\
                       --usd 0.10 --source-type api --source-ref <url-or-tool> [--qualifier 720p] \\
                       [--expires 2026-10-31] [--limits max_seconds=10,concurrency=1] [--select] \\
                       [--confidence live|reported|user] [--supports-language "<language as written in meta.language>"]
    cost_plan.py set   --pricebook P --retries ai_image=<x>,ai_video=<x>,host=<x> --retries-basis <why>
    cost_plan.py unset --pricebook P --retries ai_image,host        # remove an assumption you no longer stand behind
    cost_plan.py select --pricebook P --entry <id>                  # choose the route; prices and timestamps untouched
    cost_plan.py check --pricebook P [--max-age-hours 24]      # stale, expired, expiring, illustrative
    cost_plan.py plan  --beatmap B --pricebook P [--bakeoff N] [--extra ai_image=12,tts=0.3] [--max-age-hours 24]
    cost_plan.py --help

Source types: api (a provider's pricing endpoint), tool_catalog (a catalog the agent's own tools
expose), web (an official pricing page), user (the person told us), ledger (our own past spend),
local (an engine on this machine: price 0 credits, compute only).

Capabilities and their billing units: ai_image=image, ai_video=second, host=second,
tts=1k_chars, stt=minute, music=track, sfx=call. `--extra cap=qty,...` adds quantities the beat map does not list: a series' cast sheets and backgrounds, a
theme track, a bake-off. `meta.reuse_music: true` (a fixed series motif) counts no music track.

Retry multipliers (only for ai_image, ai_video
and host, where a rejected take is paid for) are ASSUMPTIONS, not data: set them from the
project's own ledger history or from the user (--retries-basis), and they are shown on the cost
card for confirmation.

Exit: 0 ok | 2 usage | 3 pricebook missing or unreadable.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, est_beat_seconds, load_json, parse_args  # noqa: E402

UNITS = {"ai_image": "image", "ai_video": "second", "host": "second", "tts": "1k_chars",
         "stt": "minute", "music": "track", "sfx": "call"}
SOURCE_TYPES = ("api", "tool_catalog", "web", "user", "ledger", "local")
CONFIDENCE = ("live", "reported", "user", "illustrative")
# capabilities where a rejected generation is paid for and the cap must cover it; the others
# (speech, transcription, music, effects) are priced once unless the pricebook says otherwise
RETRY_CAPS = ("ai_image", "ai_video", "host")


def new_pricebook() -> dict:
    return {"schema": "hybrid-pricebook/1", "currency": "USD",
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "assumptions": {"retries": {}, "retries_basis": None},
            "entries": []}


def load_pricebook(path: str | Path) -> dict:
    pb = load_json(path)
    pb.setdefault("entries", [])
    pb.setdefault("assumptions", {"retries": {}, "retries_basis": None})
    return pb


def selected(pb: dict, capability: str) -> dict | None:
    cands = [e for e in pb["entries"] if e.get("capability") == capability]
    pick = [e for e in cands if e.get("selected")]
    return pick[0] if pick else (cands[0] if len(cands) == 1 else None)


def _age_hours(entry: dict, now: datetime) -> float | None:
    try:
        t = datetime.fromisoformat(str(entry["fetched_at"]).replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (now - t).total_seconds() / 3600
    except (KeyError, ValueError):
        return None


def entry_flags(entry: dict, today: date, now: datetime, max_age_h: float) -> list[str]:
    flags = []
    age = _age_hours(entry, now)
    if age is None:
        flags.append("no fetched_at timestamp")
    elif age > max_age_h:
        flags.append(f"stale: fetched {age:.0f} h ago")
    exp = entry.get("expires")
    if exp:
        try:
            d = date.fromisoformat(str(exp))
            if d < today:
                flags.append(f"expired promotion or price ({exp})")
            elif d <= today + timedelta(days=14):
                flags.append(f"price changes on {exp}")
        except ValueError:
            flags.append("unreadable expires date")
    if entry.get("confidence") == "illustrative":
        flags.append("ILLUSTRATIVE price, not a real quote")
    if entry.get("confidence") == "reported":
        flags.append("confidence 'reported': read through a summary or a secondary source, not from the source's own price field; confirm before a large spend")
    return flags


_beat_seconds = est_beat_seconds


def quantities(bm: dict, bakeoff: int = 0, extra: dict | None = None) -> dict[str, dict]:
    """What the plan consumes, derived from the beat map. No prices here."""
    meta, beats = bm.get("meta", {}), bm.get("beats", [])
    fmt = data("formats")["formats"].get(meta.get("format"), {})
    wps = float(meta.get("wps") or fmt.get("wps", 2.5))
    secs = [_beat_seconds(b, wps) for b in beats]
    total_s = sum(secs)
    fixed = 0.0
    q: dict[str, dict] = {k: {"quantity": 0.0, "unit": u, "note": ""} for k, u in UNITS.items()}
    for b, s in zip(beats, secs):
        if isinstance(b.get("est_cost_usd"), (int, float)):
            fixed += float(b["est_cost_usd"])  # a cost the user or scout fixed for this beat
            continue
        layer = b.get("layer")
        if layer == "ai_image":
            q["ai_image"]["quantity"] += 1
        elif layer == "ai_video":
            q["ai_image"]["quantity"] += 1  # the approved still the clip starts from
            q["ai_video"]["quantity"] += float(b.get("clip_seconds") or math.ceil(max(s, 1.0)))
        elif layer == "host":
            q["host"]["quantity"] += s
    if fmt.get("host_covers_full_vo") and q["host"]["quantity"] > 0:
        q["host"]["quantity"] = total_s
        q["host"]["note"] = "the avatar call covers the whole voice-over (the host is the clock)"
    q["ai_image"]["quantity"] += bakeoff + int(meta.get("extra_stills", 0) or 0)
    if bakeoff:
        q["ai_image"]["note"] = f"includes {bakeoff} style bake-off stills"
    chars = sum(len((b.get("tts_text") or b.get("text") or "")) for b in beats)
    q["tts"]["quantity"] = chars / 1000.0
    if str(meta.get("alignment", "stt")).lower() not in ("engine", "none", "forced"):
        q["stt"]["quantity"] = total_s / 60.0
    if (bm.get("audio") or {}).get("music_brief") and not meta.get("reuse_music"):
        q["music"]["quantity"] = float(meta.get("music_tracks", 1))
    for cap, qty in (extra or {}).items():
        if cap in q:
            q[cap]["quantity"] += float(qty)
            q[cap]["note"] = (q[cap]["note"] + "; " if q[cap]["note"] else "") + f"includes {qty:g} extra"
    q["sfx"]["quantity"] = float(sum(len(b.get("sfx") or []) for b in beats))
    return {"quantities": {k: v for k, v in q.items() if v["quantity"] > 0}, "fixed_usd": fixed,
            "total_seconds": total_s}


SPEECH_CAPS = ("tts", "stt", "host")


def languages_of(text: str) -> list[str]:
    """The languages named in meta.language as the user wrote them. 'Urdu/English' names two."""
    import re
    return [p.strip() for p in re.split(r"[/,+&;]", str(text or "")) if p.strip()]


def unsupported_languages(entry: dict, wanted: list[str]) -> list[str]:
    have = {str(x).strip().casefold() for x in entry.get("supports_language") or []}
    return [w for w in wanted if w.casefold() not in have]


def compute_plan(bm: dict, pb: dict, bakeoff: int = 0, max_age_h: float = 24.0,
                 today: date | None = None, now: datetime | None = None, extra: dict | None = None) -> dict:
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    qd = quantities(bm, bakeoff, extra)
    retries = pb.get("assumptions", {}).get("retries") or {}
    lines, missing, questions = [], [], []
    low = high = qd["fixed_usd"]
    high_known = True
    for cap, info in qd["quantities"].items():
        e = selected(pb, cap)
        if cap == "sfx" and e is None:
            questions.append({"id": "sfx_source", "ask": "Sound effects are not priced. Use a free library, or price a generator?",
                              "why": f"{int(info['quantity'])} effect cues are in the beat map."})
            continue
        if e is None:
            cands = [x for x in pb["entries"] if x.get("capability") == cap]
            missing.append({"capability": cap, "needed": round(info["quantity"], 2), "unit": info["unit"],
                            "candidates": [x.get("id") for x in cands]})
            continue
        qty = info["quantity"]
        if e.get("unit") != info["unit"]:
            missing.append({"capability": cap, "needed": round(qty, 2), "unit": info["unit"],
                            "problem": f"selected entry '{e.get('id')}' is priced per {e.get('unit')}, plan needs per {info['unit']}"})
            continue
        usd = float(e["usd_per_unit"])
        sub_low = qty * usd
        rf = retries.get(cap, 1.0 if cap not in RETRY_CAPS else None)
        sub_high = qty * usd * float(rf) if rf is not None else None
        low += sub_low
        if sub_high is None:
            high_known = False
        else:
            high += sub_high
        flags = entry_flags(e, today, now, max_age_h)
        mx = (e.get("limits") or {}).get("max_seconds")
        if cap == "ai_video" and mx:
            over = [b["id"] for b in bm["beats"] if b.get("layer") == "ai_video"
                    and float(b.get("clip_seconds") or 0) > float(mx)]
            if over:
                flags.append(f"clip longer than the model's {mx} s limit on beats {over}")
                questions.append({"id": "clip_limit", "ask": f"Beats {over} need clips longer than {mx} s. Split them, shorten, or pick another model?",
                                  "why": "the selected video model cannot generate that length in one call"})
        if cap == "host" and mx:
            fmt_p = data("formats")["formats"].get(bm.get("meta", {}).get("format"), {})
            hs = [_beat_seconds(b, float(bm["meta"].get("wps", 2.5))) for b in bm["beats"] if b.get("layer") == "host"]
            longest = qd["total_seconds"] if fmt_p.get("host_covers_full_vo") else max(hs or [0.0])
            if longest > float(mx):
                flags.append(f"host call of {longest:.0f} s exceeds the engine's {mx} s limit")
                questions.append({"id": "host_limit", "ask": f"The avatar call needs {longest:.0f} s but '{e.get('id')}' allows {mx} s. Split the voice-over into segments, shorten it, or pick another engine?",
                                  "why": "the selected host engine cannot generate that length in one call"})
        wanted = languages_of(bm.get("meta", {}).get("language"))
        if cap in SPEECH_CAPS and wanted:
            lacking = unsupported_languages(e, wanted)
            if lacking:
                flags.append("language support unconfirmed: " + ", ".join(lacking))
                questions.append({"id": f"language_{e.get('id')}", "ask": f"Does '{e.get('id')}' support {', '.join(lacking)}? The pricebook has no record. "
                                  "Check the tool's own catalog, or play a short sample in that language and listen.",
                                  "why": "support for a language is read from the tool, never assumed; a native listen is the final test"})
        conc = (e.get("limits") or {}).get("concurrency")
        lines.append({"capability": cap, "quantity": round(qty, 2), "unit": info["unit"],
                      "entry": e.get("id"), "provider": e.get("provider"), "model": e.get("model"),
                      "qualifier": e.get("qualifier"), "usd_per_unit": usd, "source": e.get("source"),
                      "fetched_at": e.get("fetched_at"), "low": round(sub_low, 4),
                      "high": None if sub_high is None else round(sub_high, 4),
                      "note": info.get("note", ""), "concurrency": conc, "flags": flags})
        alts = [x for x in pb["entries"] if x.get("capability") == cap and x.get("unit") == info["unit"]]
        if len(alts) > 1:
            questions.append({
                "id": f"route_{cap}", "ask": f"Which {cap} route should I use?", "why": "several are available in this environment",
                "options": [{"entry": x.get("id"), "provider": x.get("provider"), "model": x.get("model"),
                             "plan_cost": round(qty * float(x["usd_per_unit"]), 4),
                             "selected": x is e} for x in alts]})
        for f in flags:
            if f.startswith(("stale", "expired", "price changes", "ILLUSTRATIVE", "confidence 'reported'", "no fetched_at", "language support")):
                questions.append({"id": f"price_{e.get('id')}", "ask": f"Price for '{e.get('id')}' ({f}). Refresh it, or accept it?",
                                  "why": "a spend decision rests on this number"})
    for m in missing:
        questions.append({"id": f"missing_{m['capability']}", "ask": f"No price is on file for {m['capability']} "
                          f"({m['needed']} {m['unit']} needed). Authorise a lookup, supply the price, or change the plan?",
                          "why": "unknown prices are never guessed"})
    no_retry = [ln["capability"] for ln in lines if ln["capability"] in RETRY_CAPS and ln["high"] is None]
    if no_retry:
        questions.append({"id": "retries", "ask": f"How many paid takes per item should the cap assume for {', '.join(no_retry)}?",
                          "why": "rejected generations are paid for and no multiplier is on file, so the high band is unknown. "
                                 "Offer the project's own ledger history (ledger.py report) when it exists."})
    budget = bm.get("meta", {}).get("budget_usd")
    if budget is None:
        opts = [{"label": "low estimate", "usd": round(low, 2)}]
        if high_known:
            opts.append({"label": "high estimate", "usd": round(high, 2)})
        questions.append({"id": "budget", "ask": "What is the spend cap?", "options": opts, "why": "the ledger refuses spends beyond it"})
    questions.append({"id": "big_spend", "ask": "At what single-call amount should I stop and show a spend card?",
                      "why": "default proposal: half the cap (a ratio, not a constant)"})
    downgrade = None
    vid = [b for b in bm.get("beats", []) if b.get("layer") == "ai_video" and not isinstance(b.get("est_cost_usd"), (int, float))]
    img_e, vid_e = selected(pb, "ai_image"), selected(pb, "ai_video")
    if vid and img_e and vid_e:
        saved = sum(float(b.get("clip_seconds") or math.ceil(max(_beat_seconds(b, float(bm["meta"].get("wps", 2.5))), 1.0)))
                    for b in vid) * float(vid_e["usd_per_unit"])
        downgrade = {"option": "turn every AI clip into its still with parallax and grain in code",
                     "saves_low_usd": round(saved, 4), "beats": [b["id"] for b in vid]}
    return {"currency": pb.get("currency", "USD"), "total_seconds": round(qd["total_seconds"], 1),
            "lines": lines, "missing": missing, "fixed_usd": qd["fixed_usd"],
            "total_low": round(low, 4), "total_high": round(high, 4) if high_known else None,
            "complete": not missing, "partial": bool(missing), "high_known": high_known,
            "retries_assumed": retries, "retries_basis": pb.get("assumptions", {}).get("retries_basis"),
            "downgrade": downgrade, "questions": questions}


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"select", "help", "h"})
    if opt.get("help") or opt.get("h"):
        print(__doc__)
        return 0
    if not pos:
        eprint(__doc__)
        return 2
    cmd = pos[0]
    if cmd == "init":
        out = Path(opt.get("out", "pricebook.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(new_pricebook(), indent=2))
        print(str(out))
        return 0
    pbp = opt.get("pricebook")
    if not pbp or not Path(pbp).is_file():
        eprint("--pricebook FILE is required (create one with `init`)")
        return 3
    pb = load_pricebook(pbp)
    if cmd == "add":
        cap = opt.get("capability", "")
        if cap not in UNITS:
            eprint(f"--capability must be one of {sorted(UNITS)}")
            return 2
        unit = opt.get("unit", UNITS[cap])
        try:
            usd = float(opt["usd"])
        except (KeyError, ValueError):
            eprint("--usd NUMBER is required: the price as quoted by the source, per --unit")
            return 2
        stype = opt.get("source-type", "")
        if stype not in SOURCE_TYPES or not opt.get("source-ref"):
            eprint(f"--source-type {SOURCE_TYPES} and --source-ref are required: every price needs provenance")
            return 2
        limits = {}
        for kv in str(opt.get("limits", "")).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                limits[k.strip()] = float(v) if v.replace(".", "", 1).isdigit() else v
        entry = {"id": opt.get("id") or f"{cap}-{len([e for e in pb['entries'] if e['capability'] == cap]) + 1}",
                 "capability": cap, "provider": opt.get("provider", ""), "model": opt.get("model", ""),
                 "qualifier": opt.get("qualifier"), "unit": unit, "usd_per_unit": usd,
                 "source": {"type": stype, "ref": opt["source-ref"]},
                 "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "expires": opt.get("expires"), "confidence": opt.get("confidence", "live"),
                 "limits": limits, "selected": bool(opt.get("select")), "notes": opt.get("notes", ""),
                 "supports_language": [x.strip() for x in str(opt.get("supports-language", "")).split(",") if x.strip()]}
        if entry["confidence"] not in CONFIDENCE:
            eprint(f"--confidence must be one of {CONFIDENCE}")
            return 2
        if entry["selected"]:
            for e in pb["entries"]:
                if e["capability"] == cap:
                    e["selected"] = False
        pb["entries"] = [e for e in pb["entries"] if e["id"] != entry["id"]] + [entry]
        Path(pbp).write_text(json.dumps(pb, indent=2))
        print(json.dumps(entry))
        return 0
    if cmd == "set":
        retries = {}
        for kv in str(opt.get("retries", "")).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                retries[k.strip()] = float(v)
        if not retries or not opt.get("retries-basis"):
            eprint("--retries cap=multiplier,... and --retries-basis <why: ledger history, user, scout estimate> are required")
            return 2
        pb["assumptions"]["retries"].update(retries)
        pb["assumptions"]["retries_basis"] = opt["retries-basis"]
        Path(pbp).write_text(json.dumps(pb, indent=2))
        print(json.dumps(pb["assumptions"]))
        return 0
    if cmd == "unset":
        caps = [c.strip() for c in str(opt.get("retries", "")).split(",") if c.strip()]
        if not caps:
            eprint("--retries cap,cap is required: the assumptions to remove")
            return 2
        for c in caps:
            pb["assumptions"]["retries"].pop(c, None)
        if not pb["assumptions"]["retries"]:
            pb["assumptions"]["retries_basis"] = None
        Path(pbp).write_text(json.dumps(pb, indent=2))
        print(json.dumps(pb["assumptions"]))
        return 0
    if cmd == "select":
        pick = next((e for e in pb["entries"] if e.get("id") == opt.get("entry")), None)
        if pick is None:
            eprint(f"--entry must be one of {[e.get('id') for e in pb['entries']]}")
            return 2
        for e in pb["entries"]:
            if e["capability"] == pick["capability"]:
                e["selected"] = e is pick
        Path(pbp).write_text(json.dumps(pb, indent=2))
        print(json.dumps({"selected": pick["id"], "capability": pick["capability"]}))
        return 0
    now, today = datetime.now(timezone.utc), date.today()
    max_age = float(opt.get("max-age-hours", 24))
    if cmd == "check":
        report = [{"id": e.get("id"), "capability": e.get("capability"), "flags": entry_flags(e, today, now, max_age)}
                  for e in pb["entries"]]
        print(json.dumps(report, indent=2))
        for r in report:
            for f in r["flags"]:
                eprint(f"  {r['id']}: {f}")
        return 0
    if cmd == "plan":
        try:
            bm = load_json(opt["beatmap"])
        except (KeyError, OSError, json.JSONDecodeError) as exc:
            eprint(f"--beatmap FILE unreadable: {exc}")
            return 2
        extra = {}
        for kv in str(opt.get("extra", "")).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                if k.strip() not in UNITS:
                    eprint(f"--extra capability must be one of {sorted(UNITS)}")
                    return 2
                extra[k.strip()] = float(v)
        plan = compute_plan(bm, pb, int(opt.get("bakeoff", 0)), max_age, extra=extra)
        print(json.dumps(plan, indent=2))
        for ln in plan["lines"]:
            eprint(f"  {ln['capability']:9s} {ln['quantity']:>7} {ln['unit']:8s} x {ln['usd_per_unit']:<8} "
                   f"= {ln['low']:.3f}  ({ln['provider']} {ln['model']}, {ln['source']['type']})")
        for m in plan["missing"]:
            eprint(f"  MISSING PRICE: {m}")
        hi = "unknown (no retry assumptions)" if plan["total_high"] is None else f"{plan['total_high']:.2f}"
        if plan["partial"]:
            eprint(f"[cost] INCOMPLETE: {plan['total_low']:.2f} is only what has a price so far "
                   f"(missing: {', '.join(m['capability'] for m in plan['missing'])}); this is NOT the cost of the plan | "
                   f"{len(plan['questions'])} question(s) for the human")
        else:
            eprint(f"[cost] low {plan['total_low']:.2f} | high {hi} {plan['currency']} | "
                   f"{len(plan['questions'])} question(s) for the human")
        return 0
    eprint(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
