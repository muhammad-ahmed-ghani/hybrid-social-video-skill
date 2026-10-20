#!/usr/bin/env python3
"""storyboard.py - render a beat map as ONE self-contained HTML board for Gate 1.

    python3 storyboard.py beatmap.json --out beatmap.html [--lint] [--issues] [--pricebook P] [--bakeoff N]
                          [--labels labels.json]

The human approving the plan should not read JSON. This produces a single page (no external
assets): a timeline bar coloured by layer, one card per beat (narration, what is seen, layer and
why, overlays, sources), the claim list with how each was derived, the layer mix, the lint verdict,
the notes and the AI-label decision. With a pricebook it adds the cost card: every line with its
source and age, the routes on offer with what each would cost for this plan, the missing prices
and the questions only the human can answer. Without one the cost shows as unknown. A plan with a
missing price is labelled INCOMPLETE, never shown as a low total.

The page reads in the language of the text: narration and notes carry dir="auto", so right-to-left
lines render in the right order, and `meta.language_tag` (a BCP 47 tag, optional) sets the page's
lang. Interface strings and role names come from ui_labels.py; translate them into the user's language
and pass `--labels`. The lint verdict and counts always show; the list of lint messages is in English
(they are working notes for you), so it appears only with --issues. Put what matters in your own
message to the user, in their language. A punchline's options, when recorded, are listed on its card. Open it in a browser, or publish it as an Artifact when one is available.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui_labels  # noqa: E402
from beatmap_lint import lint  # noqa: E402
from cost_plan import compute_plan, load_pricebook  # noqa: E402
from hx_common import eprint, load_json, parse_args, word_count  # noqa: E402
from hx_common import est_beat_seconds as _est_beat_seconds  # noqa: E402

COLORS = {"code": "#4f8cff", "ai_image": "#b366ff", "ai_video": "#ff5fa2", "stock": "#35c48b",
          "capture": "#f5a524", "host": "#ff7a45", "real": "#13b5c8"}


def e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def cost_text(c: dict | None, L: dict) -> str:
    if c and c.get("note"):
        return c["note"]
    if not c or c.get("low") is None:
        return L["unknown"]
    hi = "?" if c.get("high") is None else c["high"]
    base = f"{c['low']}–{hi}"
    return base if c.get("known", True) else f"{L['incomplete']} ({L['incomplete_note']})"


def cost_card(plan: dict | None, L: dict) -> str:
    if not plan:
        return f'<p class="dim">{e(L["cost_unknown_no_pricebook"])}</p>'
    rows = "".join(
        f'<tr><td>{e(ln["capability"])}</td><td>{e(ln["quantity"])} {e(ln["unit"])}</td>'
        f'<td>{e(ln["provider"])} {e(ln["model"])} {e(ln.get("qualifier") or "")}</td>'
        f'<td>{e(ln["usd_per_unit"])}</td><td>{e(ln["low"])}</td><td>{e("?" if ln["high"] is None else ln["high"])}</td>'
        f'<td>{e(ln["source"]["type"])}, {e((ln.get("fetched_at") or "")[:16])}'
        f'{"<br>" + e("; ".join(ln["flags"])) if ln["flags"] else ""}</td></tr>' for ln in plan["lines"])
    miss = "".join(f'<li class="err">{e(L["missing_price"])}: {e(m["capability"])} ({e(m["needed"])} {e(m["unit"])})</li>'
                   for m in plan["missing"])

    def question(q: dict) -> str:
        opts = "".join(
            f'<li>{e(o.get("label") or o.get("entry"))}'
            f'{" · " + e(o["provider"]) + " " + e(o["model"]) if o.get("provider") else ""}'
            f'{" · " + e(o["plan_cost"]) if o.get("plan_cost") is not None else ""}'
            f'{" · " + e(o["usd"]) if o.get("usd") is not None else ""}'
            f'{" ✓" if o.get("selected") else ""}</li>' for o in q.get("options", []))
        return (f'<li><b>{e(q["ask"])}</b> <span class="dim">{e(q.get("why", ""))}</span>'
                f'{"<ul>" + opts + "</ul>" if opts else ""}</li>')

    qs = "".join(question(q) for q in plan["questions"])
    hi = L["unknown"] if plan["total_high"] is None else plan["total_high"]
    if plan["partial"]:
        head = (f'<p class="verdict bad">{e(L["incomplete"])}: {e(plan["total_low"])} {e(plan["currency"])} '
                f'{e(L["incomplete_note"])}</p>')
    else:
        head = f'<p>{e(L["low"])} {e(plan["total_low"])} · {e(L["high"])} {e(hi)} {e(plan["currency"])}</p>'
    retries = ""
    if plan["retries_assumed"]:
        retries = f'<p class="dim">{e(L["retries_assumed"])}: {e(plan["retries_assumed"])} ({e(plan["retries_basis"])})</p>'
    return (f'<h2>{e(L["cost_card"])}</h2>{head}{retries}'
            f'<div class="scroll"><table><tr><th>{e(L["what"])}</th><th>{e(L["quantity"])}</th><th>{e(L["route"])}</th>'
            f'<th>{e(L["per_unit"])}</th><th>{e(L["low"])}</th><th>{e(L["high"])}</th><th>{e(L["source"])}</th></tr>{rows}</table></div>'
            f'<ul class="issues">{miss}</ul><h3>{e(L["questions"])}</h3><ol>{qs}</ol>')


def build(bm: dict, with_lint: bool, pricebook: dict | None = None, labels: dict | None = None,
          bakeoff: int = 0, issues: bool = False) -> str:
    L = labels or ui_labels.load()
    meta, beats = bm.get("meta", {}), bm.get("beats", [])
    wps = float(meta.get("wps", 2.5))
    secs = [_est_beat_seconds(b, wps) for b in beats]
    rep = lint(bm, pricebook, False, bakeoff) if with_lint else None
    plan = compute_plan(bm, pricebook, bakeoff) if pricebook else None
    claims = {c.get("id"): c for c in bm.get("claims", [])}

    def lay_label(k: str) -> str:
        return L.get(f"layer_{k}", k)

    bar = "".join(
        f'<div class="seg" style="flex:{s:.3f};background:{COLORS.get(b.get("layer"), "#888")}" '
        f'title="{e(L["beat"])} {e(b.get("id"))} · {s:.1f}s"></div>' for b, s in zip(beats, secs))

    cards, t = [], 0.0
    for b, s in zip(beats, secs):
        lay = b.get("layer", "?")
        ov = ", ".join(str(o.get("kind") if isinstance(o, dict) else o) for o in b.get("overlays", []) or [])
        srcs = "".join(
            f'<li>{e(claims.get(r, {}).get("source_name") or r)} <span class="dim">'
            f'{e(claims.get(r, {}).get("date", ""))}</span></li>' for r in b.get("claim_refs", []) or [])
        who = f' <span class="dim">· {e(b.get("character"))}</span>' if b.get("character") else ""
        opts = b.get("punchline_options") or []
        opt_html = ""
        if opts:
            items = "".join(f'<li{" class=\"pick\"" if str(o).strip() == str(b.get("text", "")).strip() else ""}>{e(o)}'
                            f'{" · " + e(L["chosen"]) if str(o).strip() == str(b.get("text", "")).strip() else ""}</li>' for o in opts)
            opt_html = f'<p class="dim" dir="auto"><b>{e(L["punchline_options"])}:</b></p><ol class="opts" dir="auto">{items}</ol>'
        role_label = L.get(f"role_{b.get('role')}", b.get("role"))
        cards.append(f"""
<section class="card" style="border-inline-start:6px solid {COLORS.get(lay, '#888')}">
  <header><b>#{e(b.get('id'))}</b> <span class="role">{e(role_label)}</span>
    <span class="chip" style="background:{COLORS.get(lay, '#888')}">{e(lay_label(lay))}</span>
    <span class="dim">{t:4.1f}s → {t + s:4.1f}s · {word_count(b.get('text', ''))} {e(L['units'])}</span>{who}</header>
  <p class="say" dir="auto">“{e(b.get('text'))}”</p>
  <p dir="auto"><b>{e(L['sees'])}:</b> {e(b.get('visual'))}</p>
  <p class="dim" dir="auto"><b>{e(L['why'])} {e(lay_label(lay))}:</b> {e(b.get('layer_why'))}
     {('· ' + e(L['device']) + ': ' + e(b.get('device'))) if b.get('device') else ''}
     {('· ' + e(L['overlays']) + ': ' + e(ov)) if ov else ''}
     {('· ' + e(L['on_screen']) + ': ' + e(' / '.join(map(str, b.get('on_screen_text') or [])))) if b.get('on_screen_text') else ''}</p>
  {opt_html}
  {('<ul class="src">' + srcs + '</ul>') if srcs else ''}
</section>""")
        t += s

    mix = (rep or {}).get("stats", {}).get("layer_mix_by_time", {})
    mixbar = "".join(f'<span class="chip" style="background:{COLORS.get(k, "#888")}">{e(lay_label(k))} {v:.0%}</span>'
                     for k, v in sorted(mix.items(), key=lambda kv: -kv[1]))
    verdict = ""
    if rep:
        st = rep["stats"]
        verdict = (f'<div class="verdict {"ok" if rep["ok"] else "bad"}">'
                   f'{e(L["lint_pass"] if rep["ok"] else L["lint_fail"])} · {len(rep["errors"])} {e(L["errors"])} · '
                   f'{len(rep["warnings"])} {e(L["warnings"])} · {e(L["cost"])} {e(cost_text(st.get("cost"), L))}'
                   f' · ~{st.get("est_seconds", 0)}s / {st.get("target_seconds", 0)}s</div>')
        listed = "".join(f'<li class="{k}">{e(i["code"])} {e(L["beat"])} {e(i["beat"])}: {e(i["msg"])}</li>'
                         for k, lst in (("err", rep["errors"]), ("warn", rep["warnings"])) for i in lst)
        if listed and issues:
            verdict += f"<ul class='issues'>{listed}</ul>"

    claim_rows = "".join(
        f'<tr><td>{e(c.get("id"))}</td><td dir="auto">{e(c.get("text"))}</td><td>{e(c.get("confidence"))}</td>'
        f'<td dir="auto">{e(c.get("source_name") or c.get("source"))}</td><td>{e(c.get("date"))}</td>'
        f'<td dir="auto">{e(c.get("method"))}</td></tr>' for c in bm.get("claims", []))
    label_chip = (f'<span class="chip" style="background:#6b7280">{e(L["ai_label_on"] if meta.get("disclose") else L["ai_label_off"])}</span>'
                  if "disclose" in meta else "")
    notes = f'<h2>{e(L["notes"])}</h2><p dir="auto">{e(meta.get("notes"))}</p>' if meta.get("notes") else ""
    lang_attr = f' lang="{e(meta["language_tag"])}"' if meta.get("language_tag") else ""

    return f"""<!doctype html><html{lang_attr}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(meta.get('topic'))}</title><style>
:root{{--bg:#f6f7f9;--fg:#15181e;--card:#fff;--dim:#6b7280;--line:#e5e7eb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#101216;--fg:#eceff4;--card:#181b21;--dim:#9aa3b2;--line:#2a2f39}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;overflow-wrap:anywhere}}
main{{max-width:880px;margin:0 auto;padding:20px 16px 60px}}
h1{{font-size:22px;margin:0 0 4px}} .dim{{color:var(--dim)}}
.timeline{{display:flex;height:16px;border-radius:8px;overflow:hidden;margin:14px 0;gap:2px}}
.seg{{min-width:4px}} .card{{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:10px 14px;margin:10px 0}} .card header{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.chip{{color:#fff;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:600;margin-inline-end:4px;display:inline-block}}
.role{{text-transform:uppercase;font-size:12px;letter-spacing:.06em;color:var(--dim)}}
.say{{font-size:17px;margin:6px 0}} .card p{{margin:4px 0}} .src{{margin:4px 0;padding-inline-start:18px;font-size:13px}}
.verdict{{padding:10px 14px;border-radius:10px;font-weight:600;margin:10px 0}}
.verdict.ok{{background:#e8f8ef;color:#0b6b3a}} .verdict.bad{{background:#fdecec;color:#a11d1d}}
.issues{{font-size:13px;padding-inline-start:18px}} .issues .err{{color:#c62828}} .issues .warn{{color:#a86400}}
.opts .pick{{font-weight:600}} .scroll{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{border-bottom:1px solid var(--line);
padding:5px 6px;text-align:start;vertical-align:top;min-width:64px}} ol,ul{{padding-inline-start:20px}}
</style></head><body><main>
<h1 dir="auto">{e(meta.get('topic'))}</h1>
<div class="dim" dir="auto">{e(meta.get('thesis'))}</div>
<p class="dim">{e(meta.get('format'))} · {e(meta.get('tier'))} · {e(meta.get('language'))} ·
{e(meta.get('target_seconds'))}s · {e(L['budget'])} {e(meta.get('budget_usd', L['not_set']))} {label_chip}</p>
{verdict}
<div class="timeline">{bar}</div><div>{mixbar}</div>
{''.join(cards)}
{cost_card(plan, L)}
<h2>{e(L['claims'])}</h2><div class="scroll"><table><tr><th>{e(L['id'])}</th><th>{e(L['claim'])}</th><th>{e(L['confidence'])}</th><th>{e(L['source'])}</th><th>{e(L['date'])}</th><th>{e(L['method'])}</th></tr>{claim_rows}</table></div>
{notes}
</main></body></html>"""


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"lint", "issues"})
    if not pos:
        eprint(__doc__)
        return 2
    bm = load_json(pos[0])
    out = Path(opt.get("out") or Path(pos[0]).with_suffix(".html"))
    pb = load_pricebook(opt["pricebook"]) if opt.get("pricebook") else None
    try:
        labels = ui_labels.load(opt.get("labels"))
    except (OSError, ValueError, KeyError) as exc:
        eprint(f"--labels: {exc}")
        return 2
    out.write_text(build(bm, bool(opt.get("lint")), pb, labels, int(opt.get("bakeoff", 0) or 0), bool(opt.get("issues"))), encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
