#!/usr/bin/env python3
"""ledger.py - spend ledger + hard budget cap for one episode directory.

Every paid generation call is a one-way door (no cancel, no refund). This keeps
an append-only ledger so the agent can answer "what have I spent and what is
left" in one command, and refuses spends that would breach the cap.

    python3 ledger.py init     --episode ep --budget N [--big-spend N] [--require plan,look] [--autonomous]
    python3 ledger.py gate     --episode ep --name plan --note "user said go"   # records a human approval
    python3 ledger.py estimate --pricebook ep/pricebook.json --kind ai_video --units 5 [--n 3]  # spends nothing
    python3 ledger.py check    --episode ep --need 4.60              # exit 0 ok | 4 would breach
    python3 ledger.py spend    --episode ep --kind host --usd 4.50 --beat 3 --note "heygen 30s"
    python3 ledger.py raise    --episode ep --budget N --note "what the user approved"   # the only way past the cap
    python3 ledger.py report   --episode ep                          # totals by kind + retries
    python3 ledger.py import   --episode ep --from other/costs.jsonl # fold in explainer-reel-skill spend

Ledger file: <episode>/ledger.jsonl (one JSON object per line; `est_usd` key is
compatible with explainer-reel-skill's costs.jsonl). Budget: <episode>/budget.json.
Retry rule: at most ONE respend per (kind, beat) and only for a content defect;
a second spend on the same pair needs --force and a --note saying why. --force waives the retry
rule and nothing else: it never lets a spend past the cap. The cap moves only with `raise`, which
records the new amount, the old one and the user's reason, because exceeding it is the user's call.
Gates: `init --require plan,look` names the human approvals that must exist before
any spend (default: plan). `gate --name X` records one. `check` and `spend` refuse
(exit 4) until every required gate is approved. `--autonomous` at init waives the
gates for unattended runs and is recorded. A single spend at or above the big-spend
threshold also needs a `big_spend` approval. The threshold is whatever the user chose at
init (--big-spend); when none was chosen it is half the budget, a ratio and not a constant.
No amount is built into this script, and `estimate` prices from the episode pricebook only
(cost_plan.py), refusing when the price is unknown. The guard lives HERE, in the script
that records the call, because a cap written only in prose is an honour system.
Persist the provider's request id with `spend --request-id ID` the moment a job is
submitted, and resume polling by id instead of resubmitting a paid call. `report` also
prints the observed calls per beat for each kind: the evidence for the retry multipliers the
cost scout asks the user to confirm on the next episode.

Exit codes: 0 ok | 2 usage | 3 not initialised or no price on file | 4 budget breach / retry refusal.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cost_plan import UNITS, load_pricebook, selected  # noqa: E402
from hx_common import eprint, parse_args  # noqa: E402


def _paths(ep: str) -> tuple[Path, Path]:
    d = Path(ep)
    return d / "budget.json", d / "ledger.jsonl"


def _load_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def estimate(pricebook: dict, kind: str, units: float = 1.0, n: int = 1) -> dict:
    """Price `units` of `kind` from the episode pricebook. Raises KeyError when there is no price."""
    if kind not in UNITS:
        raise KeyError(f"unknown kind '{kind}'; one of {sorted(UNITS)}")
    e = selected(pricebook, kind)
    if e is None:
        raise KeyError(f"no price on file for '{kind}': ask the cost scout (references/14-cost-scout.md); a missing price is never guessed")
    # units are counted in the ENTRY's own billing unit (per second, per image, per clip ...); the
    # price is never converted behind your back. A unit that differs from the plan's is reported.
    low = float(e["usd_per_unit"]) * float(units) * n
    retry = (pricebook.get("assumptions", {}).get("retries") or {}).get(kind)
    return {"kind": kind, "unit": e.get("unit"), "units": units, "n": n, "entry": e.get("id"),
            "provider": e.get("provider"), "model": e.get("model"), "low": round(low, 4),
            "high": None if retry is None else round(low * float(retry), 4),
            "source": e.get("source"), "fetched_at": e.get("fetched_at"),
            "unit_note": None if e.get("unit") == UNITS[kind] else
            f"entry is priced per {e.get('unit')}, the plan counts per {UNITS[kind]}: convert before using this figure"}


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"force", "autonomous"})
    if not pos:
        eprint(__doc__)
        return 2
    cmd = pos[0]
    if cmd == "estimate":
        pbp = opt.get("pricebook")
        if not pbp or not Path(pbp).is_file():
            eprint("--pricebook FILE is required: this script holds no prices (cost_plan.py init)")
            return 3
        try:
            est = estimate(load_pricebook(pbp), opt.get("kind", ""), float(opt.get("units", 1)), int(opt.get("n", 1)))
        except KeyError as exc:
            eprint(str(exc).strip("'\""))
            return 3
        print(json.dumps(est))
        return 0
    ep = opt.get("episode")
    if not ep:
        eprint("--episode DIR is required")
        return 2
    bpath, lpath = _paths(ep)

    if cmd == "init":
        Path(ep).mkdir(parents=True, exist_ok=True)
        budget = float(opt.get("budget", 0) or 0)
        if budget <= 0:
            eprint("--budget USD (>0) is required")
            return 2
        require = [g for g in str(opt.get("require", "plan")).split(",") if g]
        big = float(opt["big-spend"]) if opt.get("big-spend") not in (None, True) else budget / 2
        if big > budget:
            eprint(f"--big-spend {big} is above the budget {budget}: a threshold the cap can never reach would disable the spend card")
            return 2
        bpath.write_text(json.dumps({"budget_usd": budget, "big_spend_usd": big, "big_spend_set": opt.get("big-spend") not in (None, True),
                                     "created": int(time.time()),
                                     "require": require, "autonomous": bool(opt.get("autonomous"))}))
        lpath.touch()
        print(json.dumps({"budget_usd": budget, "big_spend_usd": big, "ledger": str(lpath), "require": require,
                          "autonomous": bool(opt.get("autonomous"))}))
        return 0

    if not bpath.is_file():
        eprint(f"not initialised: run `ledger.py init --episode {ep} --budget N` first")
        return 3
    cfg = json.loads(bpath.read_text())
    budget = cfg["budget_usd"]
    gpath = Path(ep) / "gates.json"
    gates = json.loads(gpath.read_text()) if gpath.is_file() else {}
    rows = _load_ledger(lpath)
    spent = round(sum(float(r.get("est_usd", 0)) for r in rows), 4)
    remaining = round(budget - spent, 4)

    if cmd == "gate":
        name = opt.get("name")
        if not name:
            eprint("--name is required")
            return 2
        gates[name] = {"ts": int(time.time()), "note": opt.get("note", "")}
        gpath.write_text(json.dumps(gates, indent=2))
        print(json.dumps({"approved": name, "gates": sorted(gates)}))
        return 0

    def _gate_block(amount: float) -> str:
        if cfg.get("autonomous"):
            return ""
        missing = [g for g in cfg.get("require", []) if g not in gates]
        if missing:
            return f"required approval(s) missing: {', '.join(missing)}. Present the plan and wait for the user, then `ledger.py gate --name <gate>`."
        big = float(cfg.get("big_spend_usd", budget / 2))
        if amount >= big and "big_spend" not in gates:
            return (f"a {amount:.2f} call reaches the {big:.2f} big-spend threshold the user set: show the spend card "
                    "and record `ledger.py gate --name big_spend`.")
        return ""

    if cmd == "check":
        need = float(opt.get("need", 0))
        blocked = _gate_block(need)
        ok = need <= remaining + 1e-9 and not blocked
        print(json.dumps({"ok": ok, "need": need, "remaining": remaining,
                          "spent": spent, "budget": budget, "blocked": blocked or None}))
        if blocked:
            eprint(f"[ledger] BLOCKED: {blocked}")
            return 4
        if not ok:
            eprint(f"[ledger] BLOCKED: need ${need:.2f} but only ${remaining:.2f} left of ${budget:.2f}. "
                   "Cut scope (fewer AI clips / shorter host) or ask the user to raise the cap.")
            return 4
        return 0

    if cmd == "spend":
        usd = float(opt.get("usd", -1))
        kind = opt.get("kind", "")
        if usd < 0 or not kind:
            eprint("--kind and --usd are required")
            return 2
        blocked = _gate_block(usd)
        if blocked:
            eprint(f"[ledger] REFUSED: {blocked}")
            return 4
        beat = opt.get("beat", "-")
        prior = [r for r in rows if r.get("kind") == kind and str(r.get("beat")) == str(beat)
                 and beat != "-"]
        if prior and not opt.get("force"):
            eprint(f"[ledger] REFUSED: {kind} for beat {beat} was already generated "
                   f"({len(prior)}x). One respend is allowed only for a content defect: "
                   "diagnose and change the prompt first, then re-run with --force --note '<why>'.")
            return 4
        if len(prior) >= 2:
            eprint(f"[ledger] REFUSED: {kind}/beat {beat} already respent once. Stop and report.")
            return 4
        if usd > remaining + 1e-9:
            eprint(f"[ledger] REFUSED: ${usd:.2f} exceeds remaining ${remaining:.2f}. --force does not lift the cap; "
                   "ask the user, and if they agree record it with `ledger.py raise`.")
            return 4
        if opt.get("force") and not opt.get("note"):
            eprint("[ledger] REFUSED: --force needs --note saying what changed in the prompt or why the respend is justified.")
            return 4
        row = {"ts": int(time.time()), "kind": kind, "beat": beat, "est_usd": round(usd, 4),
               "note": opt.get("note", "")}
        for k_opt, k_row in (("request-id", "request_id"), ("model", "model")):
            if opt.get(k_opt):
                row[k_row] = opt[k_opt]
        with open(lpath, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        print(json.dumps({"recorded": row, "remaining": round(remaining - usd, 4)}))
        return 0

    if cmd == "raise":
        new = float(opt.get("budget", 0) or 0)
        if new <= budget or not opt.get("note"):
            eprint("--budget must be higher than the current cap and --note must say what the user approved")
            return 2
        cfg.setdefault("raises", []).append({"ts": int(time.time()), "from": budget, "to": new, "note": opt["note"]})
        cfg["budget_usd"] = new
        if not cfg.get("big_spend_set"):  # a default (half the cap) follows the cap; one the user chose stays
            cfg["big_spend_usd"] = new / 2
        bpath.write_text(json.dumps(cfg))
        print(json.dumps({"budget_usd": new, "raises": cfg["raises"]}))
        return 0

    if cmd == "import":
        src = Path(opt.get("from", ""))
        if not src.is_file():
            eprint("--from FILE (a costs.jsonl) is required")
            return 2
        kind_of = {"tts": "tts", "portrait": "ai_image", "still": "ai_image", "host": "host",
                   "broll": "ai_video", "stt": "stt", "music": "music", "sfx": "sfx"}
        have_ts = {(r.get("ts"), r.get("note")) for r in rows}
        added = 0
        with open(lpath, "a", encoding="utf-8") as fh:
            for r in _load_ledger(src):
                step = str(r.get("step", "other"))
                row = {"ts": r.get("ts", int(time.time())), "kind": kind_of.get(step, step),
                       "beat": r.get("beat", "-"), "est_usd": round(float(r.get("est_usd", 0)), 4),
                       "note": f"imported:{step}:{r.get('endpoint', '')}"}
                if (row["ts"], row["note"]) in have_ts:
                    continue  # idempotent: re-running the import never double counts
                fh.write(json.dumps(row) + "\n")
                added += 1
        print(json.dumps({"imported": added}))
        return 0

    if cmd == "report":
        by_kind: dict[str, float] = defaultdict(float)
        respend = 0
        seen = set()
        for r in rows:
            by_kind[r.get("kind", "?")] += float(r.get("est_usd", 0))
            key = (r.get("kind"), str(r.get("beat")))
            if r.get("beat") not in (None, "-") and key in seen:
                respend += 1
            seen.add(key)
        per_beat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for r in rows:
            if r.get("beat") not in (None, "-"):
                per_beat[r.get("kind", "?")][str(r["beat"])] += 1
        observed = {k: round(sum(v.values()) / len(v), 2) for k, v in per_beat.items()}
        rep = {"budget_usd": budget, "spent_usd": spent, "remaining_usd": remaining,
               "by_kind": {k: round(v, 3) for k, v in by_kind.items()},
               "calls": len(rows), "respends": respend,
               "observed_calls_per_beat": observed}
        print(json.dumps(rep, indent=2))
        eprint(f"[ledger] spent ${spent:.2f} of ${budget:.2f} (${remaining:.2f} left) over "
               f"{len(rows)} calls, {respend} respend(s)")
        return 0

    eprint(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
