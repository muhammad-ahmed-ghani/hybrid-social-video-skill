#!/usr/bin/env python3
"""series.py - the memory and the governor of a SERIES: comedy, cartoon, a recurring tech explainer.

A series is more than a list of videos. It has a frame that never changes (look, cast, voices, music
motif, recurring segments), a payload that must change every episode, a continuity memory (what is
established, which gags are spent, which threads are open) and one budget across all episodes. This
script keeps that state on disk so a fresh agent can continue the series from the folder alone, and
checks the set of episodes, not one episode at a time.

    series.py init      --dir S --title T --premise P --language L --format F [--id slug] [--language-tag xx]
                        [--intent I] [--audience A] [--cadence C] [--platforms tiktok,reels]
    series.py set       --dir S [--variation min_changed_axes=2,max_hook_similarity=0.4,...] [--axes location,stakes,outcome]
                        [--budget cap=N,per_episode_envelope=N,setup_allowance=N] [--frame structure=a|b|c,title_sting=...,music_motif=...]
                        [--disclose true|false] [--cadence C] [--platforms a,b] [--language-tag xx] [--intent I]
    series.py character add --dir S --id ana --name Ana --role R [--description D] [--refs a.png,b.png] [--anchor "prompt anchor"]
                        [--voice-engine E --voice-id V --voice-notes N --speech-rate X] [--rig rig.json] [--replace]
    series.py character rig-check --dir S --id ana
    series.py lock      --dir S [--reason "why the look is allowed to change"]
    series.py episode add --dir S --title T --logline L --changes "location=docks,stakes=job,outcome=wins"
    series.py episode set --dir S --n N --status planned|scripted|approved|produced|published
    series.py episode remove --dir S --n N                  # only a planned episode with no beatmap
    series.py record    --dir S --episode N --type fact|gag|thread|cliffhanger|callback|paid_off|state --text T [--ref ID] [--due N]
    series.py next      --dir S                      # the brief for the next episode: bible, cast, memory, constraints
    series.py check     --dir S [--episode N]        # cross-episode checks; thresholds come from series.json variation
    series.py rollup    --dir S [--planned N]        # spend across episodes and shared assets
    series.py analytics --dir S --episode N --file retention.csv --seconds 3,5 [--window W]
    series.py lesson    --dir S --episode N --text "what the numbers taught"
    series.py status    --dir S
    series.py calibrate --genuine g.json --impostor i.json --genuine-pct P --impostor-pct Q

Nothing here carries a limit of its own. How different two episodes must be, how often a gag may
return, how many episodes to compare and the budget are the user's answers, stored in series.json
under `variation` and `budget` (set them with `series.py set`). When a limit is not set the check
reports the measured number and asks for the decision instead of inventing a threshold. The
similarity numbers are a floor, not a verdict: a reworded copy can slip under them, so the declared
changes and a human read of the loglines are the real check. Limits apply inside the window, and the
check also warns when an episode outside the window is a copy. A series is allowed to repeat its frame; it
is not allowed to repeat its situation with the same outcome, so every episode must declare what
changes (`--changes`), and an episode with no declared change is refused.

Exit: 0 ok | 1 check found errors | 2 usage | 3 not initialised.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import data, eprint, load_json, parse_args  # noqa: E402
from textscript import profile as text_profile  # noqa: E402

SCHEMA = "hybrid-series/1"
CONTINUITY_TYPES = ("fact", "gag", "thread", "cliffhanger", "callback", "paid_off", "state")


# ------------------------------------------------------------------ storage
def _paths(d: str | Path) -> dict[str, Path]:
    d = Path(d)
    return {"dir": d, "series": d / "series.json", "continuity": d / "continuity.jsonl",
            "episodes": d / "episodes", "characters": d / "characters", "style": d / "style",
            "shared_ledger": d / "shared" / "ledger.jsonl"}


def load_series(d: str | Path) -> dict:
    p = _paths(d)["series"]
    if not p.is_file():
        raise FileNotFoundError(f"{p} not found: run `series.py init` first")
    return json.loads(p.read_text(encoding="utf-8"))


def save_series(d: str | Path, s: dict) -> None:
    _paths(d)["series"].write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_continuity(d: str | Path) -> list[dict]:
    p = _paths(d)["continuity"]
    rows = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def episode_dir(d: str | Path, n: int) -> Path:
    return _paths(d)["episodes"] / f"{n:02d}"


def episode_beatmap(d: str | Path, n: int) -> dict | None:
    p = episode_dir(d, n) / "beatmap.json"
    return load_json(p) if p.is_file() else None


# ------------------------------------------------------------------ locks
def current_hashes(d: str | Path, s: dict) -> dict:
    """Hashes of every file that defines the look and the cast: style files and character references."""
    p = _paths(d)
    style = {str(f.relative_to(p["dir"])): sha256(f) for f in sorted(p["style"].rglob("*")) if f.is_file()} if p["style"].is_dir() else {}
    chars = {}
    for c in s.get("characters", []):
        files = {}
        for ref in (c.get("visual") or {}).get("reference_files", []):
            fp = p["dir"] / ref["path"]
            if fp.is_file():
                files[ref["path"]] = sha256(fp)
        rig = (c.get("visual") or {}).get("rig")
        rig_hash = {}
        if rig and (p["dir"] / rig).is_file():
            rp = p["dir"] / rig
            rig_hash[rig] = sha256(rp)
            try:
                for part in json.loads(rp.read_text()).get("parts", []):
                    pf = rp.parent / part.get("file", "")
                    if pf.is_file():
                        rig_hash[str(pf.relative_to(p["dir"]))] = sha256(pf)
            except (OSError, ValueError):
                pass
        chars[c["id"]] = {"refs": files, "voice": c.get("voice"), "prompt_anchor": (c.get("visual") or {}).get("prompt_anchor"),
                          "identity": [c.get("name"), c.get("role"), c.get("description")], "rig": rig_hash}
    return {"style": style, "characters": chars}


def lock_drift(d: str | Path, s: dict) -> list[str]:
    lock = s.get("locks")
    if not lock:
        return ["the look and the cast are not locked yet: run `series.py lock` after the user approves the series look"]
    now = current_hashes(d, s)
    out = []
    for name, h in lock["hashes"]["style"].items():
        if now["style"].get(name) != h:
            out.append(f"style file changed or missing since the lock: {name}")
    for name in set(now["style"]) - set(lock["hashes"]["style"]):
        out.append(f"style file added since the lock: {name}")
    for cid, info in lock["hashes"]["characters"].items():
        cur = now["characters"].get(cid)
        if cur is None:
            out.append(f"character removed since the lock: {cid}")
            continue
        if cur["refs"] != info["refs"]:
            out.append(f"character '{cid}' reference images changed since the lock")
        if cur["voice"] != info["voice"]:
            out.append(f"character '{cid}' voice changed since the lock")
        if cur["prompt_anchor"] != info["prompt_anchor"]:
            out.append(f"character '{cid}' prompt anchor changed since the lock")
        if cur.get("identity") != info.get("identity"):
            out.append(f"character '{cid}' name, role or description changed since the lock")
        if cur.get("rig") != info.get("rig"):
            out.append(f"character '{cid}' rig or one of its part files changed since the lock")
    for cid in set(now["characters"]) - set(lock["hashes"]["characters"]):
        out.append(f"character added since the lock: {cid} (cast changes need a new lock with a reason)")
    return out


# ------------------------------------------------------------------ similarity
def _tokens(text: str) -> set[str]:
    prof = text_profile([text])
    low = text.casefold()
    if prof["unit_mode"] in ("chars", "mixed"):
        chars = [c for c in low if c.isalnum()]
        return {a + b for a, b in zip(chars, chars[1:])} or set(chars)
    return set(re.findall(r"\w+", low, re.UNICODE))


def text_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def structure_signature(bm: dict) -> list[tuple]:
    return [(b.get("layer"), b.get("device")) for b in bm.get("beats", [])]


def structure_similarity(a: dict, b: dict) -> float:
    sa, sb = structure_signature(a), structure_signature(b)
    return difflib.SequenceMatcher(None, sa, sb).ratio() if sa and sb else 0.0


def hook_text(bm: dict) -> str:
    return (bm.get("beats") or [{}])[0].get("text", "")


def script_text(bm: dict) -> str:
    return " ".join(b.get("text", "") for b in bm.get("beats", []))


def ending_text(bm: dict) -> str:
    return (bm.get("beats") or [{}])[-1].get("text", "")


def parse_kv(text: str) -> dict:
    """'a=1,b=x,c=none' -> {'a': 1, 'b': 'x', 'c': None}. Numbers become numbers; none and null become None."""
    out = {}
    for kv in str(text or "").split(","):
        if "=" not in kv:
            continue
        k, v = (x.strip() for x in kv.split("=", 1))
        if v.lower() in ("none", "null", ""):
            out[k] = None
        else:
            try:
                out[k] = int(v)
            except ValueError:
                try:
                    out[k] = float(v)
                except ValueError:
                    out[k] = v
    return out


RIG_CUES = ("amplitude-bounce", "blink", "none")


def rig_validate(rig: dict, base: Path) -> tuple[list[str], list[str]]:
    """Checks a character rig file (schema hybrid-rig/1). A rig is authored once per character; nothing automates it."""
    errors: list[str] = []
    warnings: list[str] = []
    parts = rig.get("parts")
    if not isinstance(parts, list) or not parts:
        return ["rig.parts must be a non-empty list"], warnings
    names = [pt.get("name") for pt in parts]
    if len(set(names)) != len(names) or not all(names):
        errors.append("every part needs a unique name")
    by = {pt.get("name"): pt for pt in parts}
    for pt in parts:
        nm = pt.get("name")
        if not (base / str(pt.get("file", ""))).is_file():
            errors.append(f"part '{nm}': file '{pt.get('file')}' not found next to the rig")
        piv = pt.get("pivot")
        if not (isinstance(piv, list) and len(piv) == 2 and all(isinstance(v, (int, float)) for v in piv)):
            errors.append(f"part '{nm}': pivot must be [x, y]")
        if pt.get("parent") is not None and pt.get("parent") not in by:
            errors.append(f"part '{nm}': parent '{pt.get('parent')}' is not a part")
    for pt in parts:
        seen: set = set()
        cur = pt.get("name")
        while cur is not None and cur in by:
            if cur in seen:
                errors.append(f"the parent chain of '{pt.get('name')}' loops")
                break
            seen.add(cur)
            cur = by[cur].get("parent")
    mouth = rig.get("mouth")
    if mouth:
        shapes = mouth.get("shapes") or {}
        if not shapes:
            errors.append("rig.mouth needs shapes: {cue: file}")
        for k, f in shapes.items():
            if not (base / str(f)).is_file():
                errors.append(f"mouth shape '{k}': file '{f}' not found")
        if len(shapes) == 1:
            warnings.append("a mouth with a single shape cannot show speech")
    elif rig.get("cue") not in RIG_CUES:
        errors.append("a character with no mouth needs rig.cue: amplitude-bounce, blink or none (how speech shows)")
    return errors, warnings


# ------------------------------------------------------------------ spend
def _ledger_total(path: Path) -> tuple[float, dict]:
    total, by_kind = 0.0, {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            v = float(r.get("est_usd", 0) or 0)
            total += v
            by_kind[r.get("kind", "?")] = by_kind.get(r.get("kind", "?"), 0.0) + v
    return round(total, 4), {k: round(v, 4) for k, v in by_kind.items()}


def rollup(d: str | Path, planned: int | None = None) -> dict:
    s = load_series(d)
    p = _paths(d)
    per_ep, produced = {}, 0
    for ep in s.get("episodes", []):
        t, by = _ledger_total(episode_dir(d, ep["n"]) / "ledger.jsonl")
        per_ep[ep["n"]] = {"total": t, "by_kind": by, "status": ep.get("status")}
        if t > 0 or ep.get("status") in ("produced", "published"):
            produced += 1
    shared, shared_by = _ledger_total(p["shared_ledger"])
    ep_sum = round(sum(v["total"] for v in per_ep.values()), 4)
    avg = round(ep_sum / produced, 4) if produced else None
    out = {"episodes": per_ep, "episodes_produced": produced, "episodes_total_usd": ep_sum,
           "shared_assets_usd": shared, "shared_by_kind": shared_by, "series_total_usd": round(ep_sum + shared, 4),
           "avg_episode_usd": avg,
           "shared_per_produced_episode": round(shared / produced, 4) if produced else None}
    cap = (s.get("budget") or {}).get("cap")
    if cap is not None:
        out["cap"] = cap
        out["remaining"] = round(float(cap) - out["series_total_usd"], 4)
    if planned and avg is not None:
        out["projection_for_planned_episodes"] = {
            "planned": planned, "note": "average of produced episodes x remaining, plus shared assets so far; an estimate, not a quote",
            "usd": round(shared + avg * planned, 4)}
    return out


# ------------------------------------------------------------------ analytics
def parse_retention(path: str | Path) -> list[tuple[float, float]]:
    """(second, retention fraction) from a CSV with `second` and `retention` (0-1 or 0-100) or `viewers`."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().lower(): v for k, v in r.items() if k}
            try:
                sec = float(r["second"])
                val = float(r["retention"]) if "retention" in r else float(r["viewers"])
            except (KeyError, ValueError):
                continue
            rows.append((sec, val))
    if not rows:
        raise ValueError("no usable rows: the CSV needs a `second` column and a `retention` or `viewers` column")
    rows.sort()
    if "retention" not in open(path, encoding="utf-8").readline().lower():
        first = rows[0][1] or 1.0
        rows = [(s, v / first) for s, v in rows]
    elif max(v for _, v in rows) > 1.5:
        rows = [(s, v / 100.0) for s, v in rows]
    return rows


def analyse_retention(rows: list[tuple[float, float]], seconds: list[float], window: float | None) -> dict:
    def at(t: float) -> float:
        return min(rows, key=lambda r: abs(r[0] - t))[1]
    out = {"retention_at": {str(t): round(at(t), 4) for t in seconds},
           "mean_retention": round(sum(v for _, v in rows) / len(rows), 4),
           "last_second": rows[-1][0], "samples": len(rows)}
    best = (0.0, None)
    w = window or (rows[1][0] - rows[0][0] if len(rows) > 1 else 1.0)
    for i, (t0, v0) in enumerate(rows):
        j = max((k for k, (t1, _) in enumerate(rows) if t1 <= t0 + w + 1e-9), default=i)
        drop = v0 - rows[j][1]
        if drop > best[0]:
            best = (drop, (t0, rows[j][0]))
    if best[1]:
        out["steepest_drop"] = {"from": best[1][0], "to": best[1][1], "drop": round(best[0], 4),
                                "window_seconds": w, "window_source": "user" if window else "sample spacing"}
    # the opening seconds always fall fastest; the drop that teaches something comes after the user's hook window
    after = max(seconds) if seconds else 0.0
    late = (0.0, None)
    for i, (t0, v0) in enumerate(rows):
        if t0 < after:
            continue
        j = max((k for k, (t1, _) in enumerate(rows) if t1 <= t0 + w + 1e-9), default=i)
        drop = v0 - rows[j][1]
        if drop > late[0]:
            late = (drop, (t0, rows[j][0]))
    if late[1]:
        out["steepest_drop_after_hook"] = {"from": late[1][0], "to": late[1][1], "drop": round(late[0], 4),
                                           "after_second": after, "window_seconds": w}
    return out


# ------------------------------------------------------------------ consistency pass mark
def percentile(values: list[float], q: float) -> float:
    """q-th percentile (0 to 100) by linear interpolation."""
    v = sorted(values)
    if not v:
        raise ValueError("no values")
    k = (len(v) - 1) * q / 100.0
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def calibrate(genuine: list[float], impostor: list[float], genuine_pct: float, impostor_pct: float) -> dict:
    """A pass mark for 'is this the same character' from the series' own references. The percentiles are
    the user's choice; nothing here picks them. `separable` False means the encoder cannot tell this style apart."""
    pass_at = percentile(genuine, genuine_pct)
    ceiling = percentile(impostor, impostor_pct)
    return {"pass_at": round(pass_at, 4), "impostor_ceiling": round(ceiling, 4), "separable": pass_at > ceiling,
            "copy_paste_above": round(max(genuine), 4), "genuine_n": len(genuine), "impostor_n": len(impostor),
            "genuine_pct": genuine_pct, "impostor_pct": impostor_pct,
            "reading": ("a frame passes when its similarity to the canonical sheet is at least pass_at and not above "
                        "copy_paste_above; if separable is false, change the encoder or use a human judge")}


# ------------------------------------------------------------------ the checks
def check(d: str | Path, n: int | None = None) -> dict:
    s = load_series(d)
    errors: list[dict] = []
    warnings: list[dict] = []
    eps = s.get("episodes", [])
    if not eps:
        return {"ok": True, "errors": [], "warnings": [{"msg": "no episodes yet"}], "numbers": {}}
    if n is None:  # the latest episode that has a beat map, else the latest
        with_bm = [e["n"] for e in eps if episode_beatmap(d, e["n"]) is not None]
        n = max(with_bm) if with_bm else max(e["n"] for e in eps)
    cur = next((e for e in eps if e["n"] == n), None)
    if cur is None:
        return {"ok": False, "errors": [{"msg": f"episode {n} is not in the series"}], "warnings": [], "numbers": {}}
    var = s.get("variation") or {}
    numbers: dict = {"episode": n}

    for msg in lock_drift(d, s):
        (warnings if msg.startswith("the look and the cast are not locked") else errors).append({"code": "S010", "msg": msg})

    axes = set(var.get("axes") or [])
    for e in eps:
        bad = sorted(set((e.get("changes") or {})) - axes) if axes else []
        if bad:
            errors.append({"code": "S007", "msg": f"episode {e['n']} declares axes that are not in variation.axes: {bad} "
                           "(add a real axis with `series.py set --axes`, or fix the episode)"})

    bm = episode_beatmap(d, n)
    if bm is None:
        warnings.append({"code": "S001", "msg": f"episode {n} has no beatmap.json yet; the content checks were skipped"})
    else:
        meta = bm.get("meta", {})
        ser = meta.get("series") or {}
        if ser.get("id") != s["id"] or ser.get("episode") != n:
            errors.append({"code": "S002", "msg": f"meta.series must be {{id: '{s['id']}', episode: {n}}}"})
        if meta.get("language") != s.get("language"):
            errors.append({"code": "S003", "msg": f"language '{meta.get('language')}' differs from the series' '{s.get('language')}'"})
        if meta.get("format") != s.get("format"):
            warnings.append({"code": "S004", "msg": f"format '{meta.get('format')}' differs from the series' '{s.get('format')}'"})
        known = {c["id"] for c in s.get("characters", [])}
        for cid in set(meta.get("cast") or []) - known:
            errors.append({"code": "S005", "msg": f"character '{cid}' is not in the series cast"})
        ids = {e["n"] for e in eps}
        for b in bm.get("beats", []):
            cb = b.get("callback_to")
            if isinstance(cb, dict) and (cb.get("episode", 0) >= n or cb.get("episode") not in ids):
                errors.append({"code": "S006", "msg": f"beat {b.get('id')} calls back to episode {cb.get('episode')}, which is not an earlier episode"})

        # variation: limits apply inside the window; every earlier episode is still measured
        window = int(var["window"]) if var.get("window") else None
        earlier_all = [e for e in eps if e["n"] < n]
        in_window = earlier_all[-window:] if window else earlier_all
        win_ids = {e["n"] for e in in_window}
        measures = {"hook": [], "treatment": [], "script": [], "ending": []}
        changed: list[tuple[int, int]] = []
        for e in earlier_all:
            pbm = episode_beatmap(d, e["n"])
            if pbm:
                measures["hook"].append((text_similarity(hook_text(bm), hook_text(pbm)), e["n"]))
                measures["treatment"].append((structure_similarity(bm, pbm), e["n"]))
                measures["script"].append((text_similarity(script_text(bm), script_text(pbm)), e["n"]))
                measures["ending"].append((text_similarity(ending_text(bm), ending_text(pbm)), e["n"]))
            if e["n"] in win_ids:
                diffs = [k for k, v in (cur.get("changes") or {}).items() if (e.get("changes") or {}).get(k) != v]
                changed.append((len(diffs), e["n"]))
        keys = {"hook": "max_hook_similarity", "treatment": "max_structure_similarity",
                "script": "max_script_similarity", "ending": "max_ending_similarity"}
        for label, vals in measures.items():
            if not vals:
                continue
            worst_all = max(vals)
            numbers[f"{label}_similarity_max_all"] = {"value": round(worst_all[0], 3), "against_episode": worst_all[1]}
            inside = [v for v in vals if v[1] in win_ids]
            limit = var.get(keys[label])
            if inside:
                worst = max(inside)
                numbers[f"{label}_similarity_max"] = {"value": round(worst[0], 3), "against_episode": worst[1]}
                if limit is None:
                    warnings.append({"code": "S020", "msg": f"no limit is set for {label} similarity ({keys[label]}); measured {worst[0]:.2f} against "
                                     f"episode {worst[1]}. Ask the user how alike two episodes may be, then `series.py set --variation {keys[label]}=...`"})
                elif worst[0] > float(limit):
                    errors.append({"code": "S021", "msg": f"the {label} is {worst[0]:.2f} like episode {worst[1]} (limit {limit}): "
                                   "a series may repeat its frame, not its situation"})
            if limit is not None:
                for sim, en in vals:
                    if en not in win_ids and sim > float(limit):
                        warnings.append({"code": "S024", "msg": f"episode {en}, outside the window, is {sim:.2f} like this one in {label} (limit {limit}): "
                                         "a copy of an older episode"})
        if changed:
            least = min(changed)
            numbers["axes_changed_min"] = {"value": least[0], "against_episode": least[1]}
            need = var.get("min_changed_axes")
            if need is None:
                warnings.append({"code": "S022", "msg": f"min_changed_axes is not set; this episode changes at least {least[0]} declared axes "
                                 "against every episode in the window. Ask the user how many must change"})
            elif least[0] < int(need):
                errors.append({"code": "S023", "msg": f"only {least[0]} declared axes differ from episode {least[1]} (need {need}): "
                               "the same situation with the same outcome is the pattern platforms demote"})

    rows = read_continuity(d)
    window = int(var["window"]) if var.get("window") else None
    lo = n - window + 1 if window else 0
    gags: dict[str, int] = {}
    for r in rows:
        if r.get("type") == "gag" and lo <= int(r.get("episode", 0)) <= n:
            k = r.get("ref") or r.get("text", "")[:40]
            gags[k] = gags.get(k, 0) + 1
    numbers["gag_uses"] = gags
    numbers["gag_count_scope"] = f"episodes {max(lo, 1)} to {n}" if window else "all episodes"
    lim = var.get("max_gag_uses")
    for g, c in gags.items():
        if lim is not None and c > int(lim):
            warnings.append({"code": "S030", "msg": f"the gag '{g}' has been used {c} times in {numbers['gag_count_scope']} (limit {lim})"})
    if gags and lim is None:
        warnings.append({"code": "S031", "msg": "max_gag_uses is not set: ask the user how often a running gag may return"})
    paid = {r.get("ref") for r in rows if r.get("type") == "paid_off"}
    for r in rows:
        if r.get("type") in ("thread", "cliffhanger") and r.get("id") not in paid:
            due = r.get("due_episode")
            if r.get("type") == "cliffhanger" and r.get("episode", 0) == n - 1:
                warnings.append({"code": "S040", "msg": f"the cliffhanger from episode {r['episode']} ({r.get('text', '')[:60]}) is not paid off"})
            elif due is not None and n >= int(due):
                warnings.append({"code": "S041", "msg": f"the thread '{r.get('text', '')[:60]}' was due by episode {due} and is still open"})

    bud = s.get("budget") or {}
    cap = bud.get("cap")
    if cap is not None:
        ru = rollup(d)
        numbers["spend"] = {"series_total_usd": ru["series_total_usd"], "cap": cap}
        if ru["series_total_usd"] > float(cap):
            errors.append({"code": "S050", "msg": f"the series has spent {ru['series_total_usd']} of a {cap} cap"})
    elif any(_ledger_total(episode_dir(d, e["n"]) / "ledger.jsonl")[0] > 0 for e in eps):
        warnings.append({"code": "S051", "msg": "the series has spend but no series budget cap: ask the user for one"})
    env = bud.get("per_episode_envelope")
    if env is not None:
        t, _ = _ledger_total(episode_dir(d, n) / "ledger.jsonl")
        numbers["episode_spend"] = {"episode_usd": t, "envelope": env}
        if t > float(env):
            warnings.append({"code": "S052", "msg": f"episode {n} has spent {t} against its envelope of {env}"})
    return {"ok": not errors, "errors": errors, "warnings": warnings, "numbers": numbers}


# ------------------------------------------------------------------ the brief for the next episode
def next_brief(d: str | Path) -> dict:
    s = load_series(d)
    eps = s.get("episodes", [])
    # the next episode is the first one planned that has no beat map yet; otherwise a new number
    planned = next((e for e in eps if e.get("status") == "planned" and episode_beatmap(d, e["n"]) is None), None)
    n = planned["n"] if planned else (max((e["n"] for e in eps), default=0) + 1)
    var = s.get("variation") or {}
    window = int(var["window"]) if var.get("window") else 3
    recent = []
    for e in [x for x in eps if x["n"] < n][-window:]:
        bm = episode_beatmap(d, e["n"])
        recent.append({"n": e["n"], "title": e.get("title"), "changes": e.get("changes"),
                       "hook": hook_text(bm) if bm else None,
                       "treatment": [f"{l}/{dv}" for l, dv in structure_signature(bm)] if bm else None,
                       "analytics": (load_json(episode_dir(d, e["n"]) / "analytics.json")
                                     if (episode_dir(d, e["n"]) / "analytics.json").is_file() else None)})
    rows = read_continuity(d)
    paid = {r.get("ref") for r in rows if r.get("type") == "paid_off"}
    gags: dict[str, int] = {}
    for r in rows:
        if r.get("type") == "gag":
            k = r.get("ref") or r.get("text", "")[:40]
            gags[k] = gags.get(k, 0) + 1
    ru = rollup(d)
    constraints = [
        f"Declare what changes in this episode on the declared axes {var.get('axes')} and keep the frame unchanged.",
        "Do not repeat a situation from a recent episode with the same outcome.",
        "Characters look and sound exactly as their passports say; compare every generated frame with the canonical sheet, never with the previous episode.",
        "Use only facts recorded in the continuity memory, or add new ones with `series.py record`.",
    ]
    for key in ("min_changed_axes", "max_hook_similarity", "max_structure_similarity", "max_script_similarity",
                "max_ending_similarity", "max_gag_uses", "window"):
        if var.get(key) is None:
            constraints.append(f"The user has not set variation.{key}: ask for it at the series gate before the episode is judged.")
    return {
        "series": {k: s.get(k) for k in ("id", "title", "premise", "language", "language_tag", "format", "intent", "audience", "platforms", "cadence", "disclose")},
        "episode": {"n": n, "planned": planned},
        "frame": s.get("frame"), "variation": var,
        "cast": [{"id": c["id"], "name": c.get("name"), "role": c.get("role"), "description": c.get("description"),
                  "prompt_anchor": (c.get("visual") or {}).get("prompt_anchor"),
                  "reference_files": [r["path"] for r in (c.get("visual") or {}).get("reference_files", [])],
                  "voice": c.get("voice")} for c in s.get("characters", [])],
        "look_locked": not lock_drift(d, s), "lock_drift": lock_drift(d, s),
        "continuity": {
            "open_threads": [r for r in rows if r.get("type") in ("thread", "cliffhanger") and r.get("id") not in paid],
            "gag_uses": gags,
            "callbacks_available": [r for r in rows if r.get("type") == "callback"],
            "recent_facts": [r for r in rows if r.get("type") in ("fact", "state")][-12:]},
        "recent_episodes": recent,
        "lessons": s.get("lessons", [])[-5:],
        "budget": {"cap": (s.get("budget") or {}).get("cap"), "per_episode_envelope": (s.get("budget") or {}).get("per_episode_envelope"),
                   "setup_allowance": (s.get("budget") or {}).get("setup_allowance"),
                   "spent": ru["series_total_usd"], "remaining": ru.get("remaining"),
                   "avg_episode_usd": ru["avg_episode_usd"], "shared_assets_usd": ru["shared_assets_usd"]},
        "pricebook": str(_paths(d)["dir"] / "pricebook.json"),
        "constraints": constraints,
    }


# ------------------------------------------------------------------ commands
HELP = {
    "init": "series.py init --dir S --title T --premise P --language L --format F [--id slug] [--language-tag xx] [--intent I] [--audience A] [--cadence C] [--platforms a,b]",
    "set": "series.py set --dir S [--variation key=value,...] [--axes a,b,c] [--budget cap=N,per_episode_envelope=N,setup_allowance=N] [--frame structure=a|b|c,title_sting=...,music_motif=...,recurring_segments=a|b] [--disclose true|false] [--cadence C] [--platforms a,b] [--language-tag xx] [--intent I]. Variation keys: min_changed_axes, max_hook_similarity, max_structure_similarity, max_script_similarity, max_ending_similarity, max_gag_uses, window. These are the user's answers; 'none' unsets one.",
    "character add": "series.py character add --dir S --id ID --name N [--role R] [--description D] [--refs a.png,b.png] [--anchor TEXT] [--voice-engine E --voice-id V --voice-notes N --speech-rate X] [--rig rig.json] [--replace]. With --replace only the fields you pass change.",
    "character rig-check": "series.py character rig-check --dir S --id ID: validates characters/ID/rig.json (parts, pivots, parents, mouth shapes or a no-mouth cue).",
    "lock": "series.py lock --dir S [--reason TEXT]: pins style files, references, voice, anchor, identity and rig. Changing any of them afterwards needs a new lock with the reason the user gave.",
    "episode add": "series.py episode add --dir S --title T --logline L --changes axis=value,axis=value: every axis must be in variation.axes; at least one change is required.",
    "episode set": "series.py episode set --dir S --n N --status planned|scripted|approved|produced|published",
    "episode remove": "series.py episode remove --dir S --n N: only a planned episode with no beatmap.json.",
    "record": "series.py record --dir S --episode N --type fact|gag|thread|cliffhanger|callback|paid_off|state --text T [--ref ID] [--due N]",
    "next": "series.py next --dir S: the brief for the next episode.",
    "check": "series.py check --dir S [--episode N]: default is the latest episode that has a beatmap.json.",
    "rollup": "series.py rollup --dir S [--planned N]",
    "analytics": "series.py analytics --dir S --episode N --file retention.csv --seconds 3,5 [--window W]: seconds are the user's own hook window.",
    "lesson": "series.py lesson --dir S --episode N --text TEXT",
    "status": "series.py status --dir S",
    "calibrate": "series.py calibrate --genuine g.json --impostor i.json --genuine-pct P --impostor-pct Q (both percentiles are the user's choice)",
}
STATUSES = ("planned", "scripted", "approved", "produced", "published")


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"replace", "help", "h"})
    if opt.get("help") or opt.get("h"):
        key = " ".join(pos[:2]) if pos[:2] and " ".join(pos[:2]) in HELP else (pos[0] if pos and pos[0] in HELP else None)
        print(HELP[key] if key else __doc__)
        return 0
    if not pos:
        eprint(__doc__)
        return 2
    cmd = pos[0]
    if cmd == "calibrate":
        need = [k for k in ("genuine", "impostor", "genuine-pct", "impostor-pct") if opt.get(k) in (None, True)]
        if need:
            eprint("missing: " + ", ".join("--" + k for k in need) + "  (the percentiles are the user's choice; there is no default)")
            return 2
        try:
            g, i = load_json(opt["genuine"]), load_json(opt["impostor"])
            print(json.dumps(calibrate([float(x) for x in g], [float(x) for x in i], float(opt["genuine-pct"]), float(opt["impostor-pct"])), indent=2))
        except (OSError, ValueError, TypeError) as exc:
            eprint(f"calibrate: {exc}")
            return 2
        return 0
    d = opt.get("dir")
    if not d:
        eprint("--dir DIR is required")
        return 2
    P = _paths(d)

    if cmd == "init":
        if P["series"].is_file():
            eprint(f"{P['series']} exists: a series is initialised once")
            return 2
        need = [k for k in ("title", "premise", "language", "format") if not opt.get(k)]
        if need:
            eprint("missing: " + ", ".join("--" + k for k in need) + "  (language: the one the user writes in, unless they chose another)")
            return 2
        if opt["format"] not in data("formats")["formats"]:
            eprint("--format must be one of " + ", ".join(sorted(data("formats")["formats"])))
            return 2
        for k in ("dir", "episodes", "characters", "style"):
            P[k].mkdir(parents=True, exist_ok=True)
        (P["dir"] / "shared").mkdir(exist_ok=True)
        slug = str(opt.get("id") or re.sub(r"[^\w]+", "-", str(opt["title"]).lower(), flags=re.UNICODE).strip("-") or "series")
        s = {"schema": SCHEMA, "id": slug, "title": opt["title"], "premise": opt["premise"], "language": opt["language"],
             "language_tag": opt.get("language-tag"), "format": opt["format"], "intent": opt.get("intent"),
             "audience": opt.get("audience"), "platforms": [x for x in str(opt.get("platforms", "")).split(",") if x],
             "cadence": opt.get("cadence"),
             "frame": {"structure": [], "recurring_segments": [], "title_sting": None, "music_motif": None, "style_ref": "style/style.json"},
             "variation": {"axes": ["location", "stakes", "outcome"], "min_changed_axes": None, "max_hook_similarity": None,
                           "max_structure_similarity": None, "max_script_similarity": None, "max_ending_similarity": None,
                           "max_gag_uses": None, "window": None},
             "characters": [], "locks": None, "budget": {"cap": None, "per_episode_envelope": None, "setup_allowance": None},
             "disclose": None, "episodes": [], "lessons": [], "created": int(time.time())}
        save_series(d, s)
        P["continuity"].touch()
        print(json.dumps({"series": slug, "dir": str(P["dir"]), "next": "add characters, build the look, get the series gate approved, then `series.py lock`"}))
        return 0

    try:
        s = load_series(d)
    except FileNotFoundError as exc:
        eprint(str(exc))
        return 3

    if cmd == "set":
        changed = {}
        if opt.get("variation"):
            vk = parse_kv(opt["variation"])
            allowed = {"min_changed_axes", "max_hook_similarity", "max_structure_similarity", "max_script_similarity",
                       "max_ending_similarity", "max_gag_uses", "window"}
            bad = sorted(set(vk) - allowed)
            if bad:
                eprint(f"unknown variation keys {bad}; use {sorted(allowed)}")
                return 2
            s["variation"].update(vk)
            changed["variation"] = vk
        if opt.get("axes"):
            s["variation"]["axes"] = [a.strip() for a in str(opt["axes"]).split(",") if a.strip()]
            changed["axes"] = s["variation"]["axes"]
        if opt.get("budget"):
            bk = parse_kv(opt["budget"])
            bad = sorted(set(bk) - {"cap", "per_episode_envelope", "setup_allowance"})
            if bad:
                eprint(f"unknown budget keys {bad}; use cap, per_episode_envelope, setup_allowance")
                return 2
            s["budget"].update(bk)
            changed["budget"] = bk
        if opt.get("frame"):
            raw = {}  # list values (structure, recurring_segments) are written with | between items
            for kv in str(opt["frame"]).split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    raw[k.strip()] = [x for x in v.split("|") if x] if k.strip() in ("structure", "recurring_segments") else v.strip()
            s["frame"].update(raw)
            changed["frame"] = raw
        for k_opt, k_s in (("cadence", "cadence"), ("language-tag", "language_tag"), ("intent", "intent")):
            if opt.get(k_opt) not in (None, True):
                s[k_s] = opt[k_opt]
                changed[k_s] = opt[k_opt]
        if opt.get("platforms"):
            s["platforms"] = [x for x in str(opt["platforms"]).split(",") if x]
            changed["platforms"] = s["platforms"]
        if opt.get("disclose") not in (None, True):
            s["disclose"] = str(opt["disclose"]).lower() in ("true", "yes", "1", "on")
            changed["disclose"] = s["disclose"]
        if not changed:
            eprint(HELP["set"])
            return 2
        save_series(d, s)
        print(json.dumps(changed, ensure_ascii=False))
        return 0

    if cmd == "character" and len(pos) > 1 and pos[1] == "rig-check":
        c = next((x for x in s["characters"] if x["id"] == opt.get("id")), None)
        rig = (c or {}).get("visual", {}).get("rig")
        if not c or not rig or not (P["dir"] / rig).is_file():
            eprint("that character has no rig: add one with `character add --id ID --rig rig.json --replace`")
            return 2
        rp = P["dir"] / rig
        try:
            errs, warns = rig_validate(json.loads(rp.read_text()), rp.parent)
        except ValueError as exc:
            errs, warns = [f"rig.json is not valid JSON: {exc}"], []
        print(json.dumps({"ok": not errs, "errors": errs, "warnings": warns}, indent=2))
        return 0 if not errs else 1

    if cmd == "character" and len(pos) > 1 and pos[1] == "add":
        cid = opt.get("id")
        if not cid or not opt.get("name"):
            eprint("--id and --name are required")
            return 2
        existing = next((c for c in s["characters"] if c["id"] == cid), None)
        if existing and not opt.get("replace"):
            eprint(f"character '{cid}' exists: pass --replace to change it (only the fields you pass change; re-lock afterwards)")
            return 2
        entry = json.loads(json.dumps(existing)) if existing else {"id": cid, "visual": {"reference_files": [], "prompt_anchor": None}, "voice": None}
        entry["name"] = opt["name"]
        for k_opt, k in (("role", "role"), ("description", "description")):
            if opt.get(k_opt) not in (None, True):
                entry[k] = opt[k_opt]
        entry.setdefault("role", None)
        entry.setdefault("description", None)
        refs = []
        for src in [x for x in str(opt.get("refs", "")).split(",") if x]:
            sp = Path(src)
            if not sp.is_file():
                eprint(f"reference image not found: {src}")
                return 2
            dst = P["characters"] / cid / sp.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if sp.resolve() != dst.resolve():
                shutil.copyfile(sp, dst)
            refs.append({"path": str(dst.relative_to(P["dir"])), "sha256": sha256(dst)})
        if refs:
            entry["visual"]["reference_files"] = refs
        if opt.get("anchor") not in (None, True):
            entry["visual"]["prompt_anchor"] = opt["anchor"]
        voice = dict(entry.get("voice") or {})
        for k, o in (("engine", "voice-engine"), ("voice_id", "voice-id"), ("notes", "voice-notes")):
            if opt.get(o) not in (None, True):
                voice[k] = opt[o]
        if opt.get("speech-rate") not in (None, True):
            voice["speech_rate"] = float(opt["speech-rate"])
        entry["voice"] = voice or None
        if opt.get("rig") not in (None, True):
            rs = Path(opt["rig"])
            if not rs.is_file():
                eprint(f"rig file not found: {opt['rig']}")
                return 2
            rd = P["characters"] / cid / "rig.json"
            rd.parent.mkdir(parents=True, exist_ok=True)
            if rs.resolve() != rd.resolve():
                shutil.copyfile(rs, rd)
            entry["visual"]["rig"] = str(rd.relative_to(P["dir"]))
        s["characters"] = [c for c in s["characters"] if c["id"] != cid] + [entry]
        save_series(d, s)
        print(json.dumps(entry, ensure_ascii=False))
        return 0

    if cmd == "lock":
        drift = [m for m in lock_drift(d, s) if not m.startswith("the look and the cast are not locked")]
        if s.get("locks") and drift and not opt.get("reason"):
            eprint("the look or the cast changed since the lock:\n  " + "\n  ".join(drift) +
                   "\nA changed look is a decision for the user: pass --reason with what they approved.")
            return 1
        s["locks"] = {"locked_at": int(time.time()), "reason": opt.get("reason"), "hashes": current_hashes(d, s)}
        save_series(d, s)
        print(json.dumps({"locked": True, "style_files": len(s["locks"]["hashes"]["style"]),
                          "characters": list(s["locks"]["hashes"]["characters"])}))
        return 0

    if cmd == "episode" and len(pos) > 1 and pos[1] == "add":
        changes = {}
        for kv in str(opt.get("changes", "")).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                changes[k.strip()] = v.strip()
        if not opt.get("title") or not opt.get("logline"):
            eprint("--title and --logline are required")
            return 2
        axes = set((s.get("variation") or {}).get("axes") or [])
        bad = sorted(set(changes) - axes) if axes else []
        if bad:
            eprint(f"unknown axes {bad}: a change must be on one of the series' declared axes {sorted(axes)}. "
                   "Add a real axis with `series.py set --axes`, or fix the name.")
            return 2
        if not changes:
            eprint("--changes is required: say what is different in this episode (for example location=docks,stakes=job,outcome=wins). "
                   "An episode that changes nothing is the template pattern platforms demote.")
            return 2
        n = max((e["n"] for e in s["episodes"]), default=0) + 1
        ep = {"n": n, "title": opt["title"], "logline": opt["logline"], "changes": changes, "status": "planned"}
        s["episodes"].append(ep)
        save_series(d, s)
        ed = episode_dir(d, n)
        ed.mkdir(parents=True, exist_ok=True)
        hint = {"series": {"id": s["id"], "episode": n, "title": opt["title"]}, "language": s["language"],
                "format": s["format"], "intent": s.get("intent"), "cast": [c["id"] for c in s["characters"]]}
        (ed / "meta_hint.json").write_text(json.dumps(hint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"episode": ep, "dir": str(ed), "meta_hint": str(ed / "meta_hint.json")}, ensure_ascii=False))
        return 0

    if cmd == "episode" and len(pos) > 1 and pos[1] in ("set", "remove"):
        n = int(opt["n"]) if opt.get("n") not in (None, True) else None
        ep = next((e for e in s["episodes"] if e["n"] == n), None)
        if ep is None:
            eprint("--n must be an episode number in this series")
            return 2
        if pos[1] == "set":
            if opt.get("status") not in STATUSES:
                eprint(f"--status must be one of {STATUSES}")
                return 2
            ep["status"] = opt["status"]
            save_series(d, s)
            print(json.dumps(ep, ensure_ascii=False))
            return 0
        if ep.get("status") != "planned" or episode_beatmap(d, n) is not None:
            eprint("only a planned episode with no beatmap.json can be removed: it has work attached, so change its status instead")
            return 2
        s["episodes"] = [e for e in s["episodes"] if e["n"] != n]
        save_series(d, s)
        shutil.rmtree(episode_dir(d, n), ignore_errors=True)
        print(json.dumps({"removed": n}))
        return 0

    if cmd == "record":
        typ = opt.get("type")
        if typ not in CONTINUITY_TYPES or not opt.get("text") or not opt.get("episode"):
            eprint(f"--episode, --type ({'|'.join(CONTINUITY_TYPES)}) and --text are required")
            return 2
        rows = read_continuity(d)
        row = {"id": f"c{len(rows) + 1}", "ts": int(time.time()), "episode": int(opt["episode"]), "type": typ, "text": opt["text"]}
        for k_opt, k_row in (("ref", "ref"), ("due", "due_episode")):
            if opt.get(k_opt):
                row[k_row] = int(opt[k_opt]) if k_row == "due_episode" else opt[k_opt]
        with open(P["continuity"], "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps(row, ensure_ascii=False))
        return 0

    if cmd == "next":
        print(json.dumps(next_brief(d), indent=2, ensure_ascii=False))
        return 0

    if cmd == "check":
        rep = check(d, int(opt["episode"]) if opt.get("episode") else None)
        print(json.dumps(rep, indent=2, ensure_ascii=False))
        for e in rep["errors"]:
            eprint(f"  ERROR {e.get('code', '')}: {e['msg']}")
        for w in rep["warnings"]:
            eprint(f"  warn  {w.get('code', '')}: {w['msg']}")
        eprint("[series] " + ("PASS" if rep["ok"] else "FAIL"))
        return 0 if rep["ok"] else 1

    if cmd == "rollup":
        print(json.dumps(rollup(d, int(opt["planned"]) if opt.get("planned") else None), indent=2))
        return 0

    if cmd == "analytics":
        if not opt.get("episode") or not opt.get("file") or not opt.get("seconds"):
            eprint("--episode, --file and --seconds are required: the user's own hook window decides which seconds to read, "
                   "this script does not pick one")
            return 2
        try:
            rows = parse_retention(opt["file"])
        except (OSError, ValueError) as exc:
            eprint(str(exc))
            return 2
        res = analyse_retention(rows, [float(x) for x in str(opt["seconds"]).split(",") if x],
                                float(opt["window"]) if opt.get("window") else None)
        ed = episode_dir(d, int(opt["episode"]))
        ed.mkdir(parents=True, exist_ok=True)
        (ed / "analytics.json").write_text(json.dumps(res, indent=2) + "\n")
        print(json.dumps(res, indent=2))
        return 0

    if cmd == "lesson":
        if not opt.get("text"):
            eprint("--text is required")
            return 2
        s["lessons"].append({"ts": int(time.time()), "episode": int(opt["episode"]) if opt.get("episode") else None, "text": opt["text"]})
        save_series(d, s)
        print(json.dumps(s["lessons"][-1], ensure_ascii=False))
        return 0

    if cmd == "status":
        ru = rollup(d)
        print(json.dumps({"series": s["id"], "language": s["language"], "format": s["format"],
                          "characters": [c["id"] for c in s["characters"]], "locked": bool(s.get("locks")),
                          "episodes": [{k: e.get(k) for k in ("n", "title", "status")} for e in s["episodes"]],
                          "spend": {k: ru.get(k) for k in ("series_total_usd", "shared_assets_usd", "avg_episode_usd", "cap", "remaining")},
                          "open_threads": len([r for r in read_continuity(d)
                                               if r.get("type") in ("thread", "cliffhanger")
                                               and r.get("id") not in {x.get("ref") for x in read_continuity(d) if x.get("type") == "paid_off"}])},
                         indent=2, ensure_ascii=False))
        return 0

    eprint(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
