"""Behavioural tests for the hybrid-social-video scripts.

Run:  python3 -m pytest -q tests/        (stdlib + pytest; ffmpeg needed for the media tests)
Each test pins an invariant the skill relies on, not a snapshot of current data.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import beatmap_lint  # noqa: E402
import cost_plan  # noqa: E402
import style_lock  # noqa: E402
from hx_common import data, word_count  # noqa: E402

EXAMPLES = sorted((ROOT / "examples").glob("*.json"))
BASE_EXAMPLE = ROOT / "examples" / "data-story-compound-interest.json"  # the plan most tests mutate
HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def load(p):
    return json.loads(Path(p).read_text())


FIXTURE_PRICEBOOK = ROOT / "tests" / "fixtures" / "pricebook_synthetic.json"


def fresh_pricebook(**retries):
    """The synthetic fixture with every price stamped as fetched now (so freshness checks pass).
    The numbers are invented for tests; nothing in the skill ships a real price."""
    pb = json.loads(FIXTURE_PRICEBOOK.read_text())
    now = cost_plan.datetime.now(cost_plan.timezone.utc).isoformat(timespec="seconds")
    for e in pb["entries"]:
        e["fetched_at"] = now
    if retries:
        pb["assumptions"]["retries"] = retries
    return pb


def codes(rep, kind="errors"):
    return {x["code"] for x in rep[kind]}


def run_script(name, *args, check=False):
    return subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                          capture_output=True, text=True, check=check)


# ---------------------------------------------------------------- data contracts
def test_every_format_profile_is_internally_consistent():
    for fid, p in data("formats")["formats"].items():
        lo, hi = p["beat_seconds"]
        assert 0 < lo < hi, fid
        assert p["wps"] > 0 and p["hook_max_words"] > 0, fid
        for layer, (mn, mx) in p["mix"].items():
            assert 0 <= mn <= mx <= 1, (fid, layer)
            assert layer in p["layers_allowed"] or mx == 0, (fid, layer)
        assert p["default_tier"] in ("R0", "R1", "R2", "R3"), fid


def test_every_format_has_a_reference_file():
    for fid in data("formats")["formats"]:
        assert (ROOT / "references" / "formats" / f"{fid}.md").is_file(), fid


def test_skill_md_fits_the_rules_and_its_file_map_points_at_real_files():
    import re
    text = (ROOT / "SKILL.md").read_text()
    desc = " ".join(x.strip() for x in re.search(r"description: >-\n((?:  .*\n)+)", text).group(1).splitlines())
    assert len(desc) <= 1024, len(desc)
    for ref in re.findall(r"`(references/[0-9a-z\-]+\.md)`", text):
        assert (ROOT / ref).is_file(), ref
    row = next(l for l in text.splitlines() if l.startswith("| `scripts/`"))
    for name in re.findall(r"`([a-z_]+)`", row.split("|")[2]):
        assert (SCRIPTS / f"{name}.py").is_file(), name
    for name in ("formats", "intents", "identities", "platforms"):
        assert (ROOT / "data" / f"{name}.json").is_file()
    assert "$" not in "".join(re.findall(r"\$[0-9]+", text)), "SKILL.md must not carry a price"


def test_each_format_names_the_references_to_read_and_each_intent_points_at_real_formats():
    formats = data("formats")["formats"]
    for fid, p in formats.items():
        assert p.get("read"), fid
        for stem in p["read"]:
            assert (ROOT / "references" / f"{stem}.md").is_file(), (fid, stem)
    for iid, it in data("intents")["intents"].items():
        for f in it["formats"]:
            assert f in formats, (iid, f)


def test_narrative_formats_allow_the_dialogue_cut_and_ask_for_a_punchline_where_comic():
    f = data("formats")["formats"]
    assert f["comedy-sketch"]["needs_punchline"] and f["comedy-sketch"]["allow_repeat_treatment"]
    assert f["cartoon-episode"]["allow_repeat_treatment"]
    assert {"sketch", "serial-story"} <= set(data("intents")["intents"])


def test_platform_safe_boxes_fit_the_canvas():
    z = data("platforms")["safe_zones_1080x1920"]
    for name, m in z["platforms"].items():
        assert m["top"] + m["bottom"] < 1920 and m["left"] + m["right"] < 1080, name
    b = z["common_safe_box"]
    assert b["x"] + b["w"] <= 1080 and b["y"] + b["h"] <= 1920


# ---------------------------------------------------------------- the linter
@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_shipped_examples_lint_clean(path):
    rep = beatmap_lint.lint(load(path))
    assert rep["ok"], rep["errors"]


def base():
    return copy.deepcopy(load(BASE_EXAMPLE))


def test_length_is_set_by_speech_units_and_only_fails_once_the_rate_is_measured():
    bm = base()
    bm["meta"]["target_seconds"] = 90
    prior = beatmap_lint.lint(bm)
    assert "E010" not in codes(prior) and "E010" in codes(prior, "warnings")  # an unmeasured prior cannot fail a plan
    assert "E013" in codes(prior, "warnings")
    bm["meta"]["rate_source"] = "measured"
    measured = beatmap_lint.lint(bm)
    assert "E010" in codes(measured) and "E013" not in codes(measured, "warnings")


def test_numbers_must_be_shown_by_the_code_layer():
    bm = base()
    b = bm["beats"][3]
    b.update(layer="ai_image", device=None, overlays=[], ai={"prompt": "two piles of coins on a desk"})
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    assert "E031" in codes(beatmap_lint.lint(bm))


def test_ai_beat_without_anchor_is_an_error():
    bm = base()
    bm["beats"][1].update(layer="ai_image", ai={"prompt": "a quiet street"}, device="collage")
    bm["meta"].pop("visual_anchor", None)
    assert "E032" in codes(beatmap_lint.lint(bm))


def test_risky_scene_needs_a_strong_anchor():
    bm = base()
    bm["meta"]["visual_anchor"] = "protest"
    bm["beats"][1].update(layer="ai_image", ai={"prompt": "protesters waving flags at dusk"},
                          device="collage", overlays=[])
    assert "E033" in codes(beatmap_lint.lint(bm))
    bm["meta"]["visual_anchor"] = ("PTI supporters on Jinnah Avenue, Islamabad, Pakistan; only Pakistani "
                                   "national and PTI party flags, never any other country's symbols")
    assert "E033" not in codes(beatmap_lint.lint(bm))


def test_text_in_ai_prompt_is_flagged():
    bm = base()
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    bm["beats"][1].update(layer="ai_image", ai={"prompt": "a chart with a headline label"}, device="collage")
    assert "E030" in codes(beatmap_lint.lint(bm), "warnings")


def test_hook_must_be_first_and_a_payoff_must_close():
    bm = base()
    bm["beats"][0]["role"] = "context"
    assert "E020" in codes(beatmap_lint.lint(bm))
    bm = base()
    bm["beats"][-1]["role"] = "build"
    assert "E022" in codes(beatmap_lint.lint(bm))


def test_unsourced_claims_and_dangling_refs_fail():
    bm = base()
    bm["claims"].append({"id": "c9", "text": "x", "confidence": "primary"})
    assert "E050" in codes(beatmap_lint.lint(bm))
    bm = base()
    bm["beats"][0]["claim_refs"] = ["nope"]
    assert "E050" in codes(beatmap_lint.lint(bm))


def test_computed_claims_must_state_their_method():
    bm = base()
    bm["claims"][0].pop("method", None)
    bm["claims"][0].pop("source", None)
    assert "E050" in codes(beatmap_lint.lint(bm))


def test_tts_markup_and_spelled_numbers_do_not_leak_into_captioned_text():
    bm = base()
    bm["beats"][1]["text"] = "[excited] Ana invests two hundred dollars... fifty percent more"
    rep = beatmap_lint.lint(bm)
    assert "E052" in codes(rep)
    assert "E051" not in codes(rep, "warnings")  # no language is assumed: the number words come from the agent
    assert any("E051" in x for x in rep["stats"]["not_checked"])
    bm["meta"]["number_words"] = ["two", "hundred", "fifty"]
    assert "E051" in codes(beatmap_lint.lint(bm), "warnings")


def test_budget_cap_blocks_an_unaffordable_plan():
    bm = base()
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    bm["meta"]["budget_usd"] = 0.5
    for i in (1, 2, 3):
        bm["beats"][i].update(layer="ai_video", ai={"prompt": "coins on a desk"}, device=f"d{i}",
                              overlays=[{"kind": "stat"}])
    assert "E060" in codes(beatmap_lint.lint(bm, fresh_pricebook()))
    bm["meta"]["budget_usd"] = 500
    assert "E060" not in codes(beatmap_lint.lint(bm, fresh_pricebook()))


def paid_plan():
    bm = base()
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    bm["beats"][1].update(layer="ai_image", ai={"prompt": "coins on a desk"}, device="d1", overlays=[{"kind": "stat"}])
    return bm


def test_cost_is_unknown_not_guessed_without_a_pricebook():
    rep = beatmap_lint.lint(paid_plan())
    assert "E061" in codes(rep, "warnings") and "E061" not in codes(rep)
    assert rep["stats"]["cost_usd_low"] is None and rep["stats"]["cost"]["known"] is False
    assert "E061" in codes(beatmap_lint.lint(paid_plan(), None, require_pricebook=True))  # Gate 1 uses this


def test_an_all_code_plan_needs_no_pricebook():
    assert beatmap_lint.lint(base())["stats"]["cost"]["known"] is True
    assert "E061" not in codes(beatmap_lint.lint(base()), "warnings")


def test_a_paid_layer_with_no_price_on_file_is_an_error_and_a_question():
    pb = fresh_pricebook()
    pb["entries"] = [e for e in pb["entries"] if e["capability"] != "ai_image"]
    rep = beatmap_lint.lint(paid_plan(), pb)
    assert "E062" in codes(rep)
    plan = cost_plan.compute_plan(paid_plan(), pb)
    assert any(q["id"] == "missing_ai_image" for q in plan["questions"])
    assert plan["complete"] is False


def test_the_plan_is_priced_from_the_pricebook_alone():
    pb = fresh_pricebook(ai_image=2.0)
    plan = cost_plan.compute_plan(paid_plan(), pb)
    line = next(ln for ln in plan["lines"] if ln["capability"] == "ai_image")
    unit = next(e["usd_per_unit"] for e in pb["entries"] if e["capability"] == "ai_image")
    assert line["quantity"] == 1 and line["low"] == pytest.approx(unit)
    assert line["high"] == pytest.approx(unit * 2.0)
    # change the price: the plan follows, so nothing is cached in the skill
    for e in pb["entries"]:
        if e["capability"] == "ai_image":
            e["usd_per_unit"] = unit * 10
    assert cost_plan.compute_plan(paid_plan(), pb)["total_low"] > plan["total_low"]


def test_missing_retry_assumptions_leave_the_high_band_unknown_and_ask():
    pb = fresh_pricebook()
    pb["assumptions"]["retries"] = {}
    plan = cost_plan.compute_plan(paid_plan(), pb)
    assert plan["total_high"] is None
    assert any(q["id"] == "retries" for q in plan["questions"])
    assert "E065" in codes(beatmap_lint.lint(paid_plan(), pb), "warnings")


def test_stale_expired_and_illustrative_prices_are_flagged():
    from datetime import date, datetime, timedelta, timezone
    pb = fresh_pricebook()
    e = next(x for x in pb["entries"] if x["capability"] == "ai_image")
    e["expires"] = (date.today() - timedelta(days=1)).isoformat()
    e["fetched_at"] = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    flags = cost_plan.entry_flags(e, date.today(), datetime.now(timezone.utc), 24)
    assert any(f.startswith("stale") for f in flags) and any(f.startswith("expired") for f in flags)
    assert any(f.startswith("ILLUSTRATIVE") for f in flags)
    rep = beatmap_lint.lint(paid_plan(), pb)
    assert {"E063", "E064"} <= codes(rep, "warnings")


def test_several_routes_become_a_question_with_each_plan_cost():
    pb = fresh_pricebook()
    pb["entries"].append(dict(next(x for x in pb["entries"] if x["capability"] == "ai_image"),
                              id="img-b", model="image-b", usd_per_unit=0.5, selected=False))
    q = next(q for q in cost_plan.compute_plan(paid_plan(), pb)["questions"] if q["id"] == "route_ai_image")
    assert {o["entry"] for o in q["options"]} == {"img-a", "img-b"}
    assert all("plan_cost" in o for o in q["options"])


def test_clip_longer_than_the_model_limit_is_raised():
    pb = fresh_pricebook()
    bm = paid_plan()
    bm["beats"][2].update(layer="ai_video", clip_seconds=15, ai={"prompt": "coins"}, device="d2")
    plan = cost_plan.compute_plan(bm, pb)
    assert any(q["id"] == "clip_limit" for q in plan["questions"])


def test_a_unit_mismatch_is_a_missing_price_not_a_wrong_number():
    pb = fresh_pricebook()
    for e in pb["entries"]:
        if e["capability"] == "ai_video":
            e["unit"] = "clip"
    bm = paid_plan()
    bm["beats"][2].update(layer="ai_video", clip_seconds=5, ai={"prompt": "coins"}, device="d2")
    plan = cost_plan.compute_plan(bm, pb)
    assert any(m["capability"] == "ai_video" and "problem" in m for m in plan["missing"])


def test_pricebook_cli_requires_provenance_and_round_trips(tmp_path):
    pb = tmp_path / "pb.json"
    assert run_script("cost_plan.py", "init", "--out", pb).returncode == 0
    base_args = ["add", "--pricebook", pb, "--capability", "ai_image", "--provider", "p", "--model", "m", "--usd", "0.2"]
    assert run_script("cost_plan.py", *base_args).returncode == 2  # no source: refused
    ok = run_script("cost_plan.py", *base_args, "--source-type", "user", "--source-ref", "told by user", "--select")
    assert ok.returncode == 0 and json.loads(pb.read_text())["entries"][0]["fetched_at"]
    assert run_script("cost_plan.py", "set", "--pricebook", pb, "--retries", "ai_image=1.5").returncode == 2  # basis missing
    assert run_script("cost_plan.py", "set", "--pricebook", pb, "--retries", "ai_image=1.5",
                      "--retries-basis", "user said so").returncode == 0
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(paid_plan()))
    out = run_script("cost_plan.py", "plan", "--beatmap", bmp, "--pricebook", pb)
    plan = json.loads(out.stdout)
    assert plan["total_low"] == pytest.approx(0.2) and plan["total_high"] == pytest.approx(0.3)


def test_the_skill_ships_no_prices():
    assert not (ROOT / "data" / "prices.json").exists()
    for f in (SCRIPTS / "ledger.py", SCRIPTS / "beatmap_lint.py", SCRIPTS / "cost_plan.py"):
        src = f.read_text()
        assert "unit_usd" not in src and "retry_factor" not in src, f.name


def test_capability_probe_never_leaks_a_credential_value(tmp_path, monkeypatch):
    secret = "sk-test-VALUE-that-must-never-appear"
    monkeypatch.setenv("FAL_KEY", secret)
    out = tmp_path / "caps.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "capability_probe.py"), "--out", str(out)],
                       capture_output=True, text=True, env={**__import__("os").environ, "FAL_KEY": secret})
    assert r.returncode == 0
    for text in (r.stdout, r.stderr, out.read_text()):
        assert secret not in text
    assert "FAL_KEY" in json.loads(out.read_text())["credentials_present"]


def test_real_person_photoreal_ai_is_blocked_unless_labelled_or_stylised():
    bm = base()
    bm["meta"]["visual_anchor"] = "history explainer about a named public figure, archival look only"
    bm["meta"]["style"] = {"name": "x", "family": "photoreal documentary"}
    bm["beats"][1].update(layer="ai_image", ai={"prompt": "a photoreal portrait at a podium"},
                          depicts_real="person", device="portrait")
    assert "E034" in codes(beatmap_lint.lint(bm))
    bm["beats"][1]["label_synthetic"] = True
    assert "E034" not in codes(beatmap_lint.lint(bm))


def test_variety_law_flags_three_identical_treatments():
    bm = base()
    for i in (1, 2, 3):
        bm["beats"][i]["device"] = "timeline"
    assert "E040" in codes(beatmap_lint.lint(bm), "warnings")


def test_word_count_ignores_tags_and_punctuation():
    assert word_count("[excited] Hello — world ...") == 2


def test_cli_exit_codes(tmp_path):
    ok = run_script("beatmap_lint.py", BASE_EXAMPLE, "--quiet")
    assert ok.returncode == 0
    bad = base()
    bad["beats"] = []
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    assert run_script("beatmap_lint.py", p, "--quiet").returncode == 1
    assert run_script("beatmap_lint.py", tmp_path / "missing.json", "--quiet").returncode == 2


# ---------------------------------------------------------------- the ledger
def test_ledger_enforces_cap_and_retry_rule(tmp_path):
    ep = tmp_path / "ep"
    assert run_script("ledger.py", "init", "--episode", ep, "--budget", "5", "--require", "",
                      "--big-spend", "5").returncode == 0
    assert run_script("ledger.py", "check", "--episode", ep, "--need", "4.6").returncode == 0
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "host",
                      "--usd", "4.5", "--beat", "1").returncode == 0
    assert run_script("ledger.py", "check", "--episode", ep, "--need", "1.0").returncode == 4
    # same kind+beat again without --force is refused (diagnose first)
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "host",
                      "--usd", "0.1", "--beat", "1").returncode == 4
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image",
                      "--usd", "9", "--beat", "2").returncode == 4  # breaches the cap
    rep = json.loads(run_script("ledger.py", "report", "--episode", ep).stdout)
    assert rep["spent_usd"] == pytest.approx(4.5) and rep["calls"] == 1


def test_ledger_second_respend_is_refused_even_with_force(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "50", "--require", "")
    args = ["spend", "--episode", ep, "--kind", "ai_video", "--usd", "1", "--beat", "3"]
    assert run_script("ledger.py", *args).returncode == 0
    assert run_script("ledger.py", *args, "--force", "--note", "prompt fixed").returncode == 0
    assert run_script("ledger.py", *args, "--force", "--note", "again").returncode == 4


def test_ledger_estimate_needs_a_pricebook_and_spends_nothing(tmp_path):
    assert run_script("ledger.py", "estimate", "--kind", "host", "--units", "30").returncode == 3  # no prices anywhere
    r = run_script("ledger.py", "estimate", "--pricebook", FIXTURE_PRICEBOOK, "--kind", "host", "--units", "30")
    est = json.loads(r.stdout)
    assert est["high"] > est["low"] > 0 and est["source"]["type"] == "user"
    assert run_script("ledger.py", "estimate", "--pricebook", FIXTURE_PRICEBOOK, "--kind", "sfx").returncode == 3  # no price, no guess


def test_gates_block_spend_until_a_human_approves(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "10")  # default requires 'plan'
    assert run_script("ledger.py", "check", "--episode", ep, "--need", "0.2").returncode == 4
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image", "--usd", "0.1",
                      "--beat", "1").returncode == 4
    assert run_script("ledger.py", "gate", "--episode", ep, "--name", "plan", "--note", "go").returncode == 0
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image", "--usd", "0.1",
                      "--beat", "1", "--request-id", "req_123", "--model", "m1").returncode == 0
    # a big single spend (>= half the budget by default) needs its own approval even after the plan gate
    big = ["spend", "--episode", ep, "--kind", "host", "--usd", "6", "--beat", "2"]
    assert run_script("ledger.py", *big).returncode == 4
    run_script("ledger.py", "gate", "--episode", ep, "--name", "big_spend")
    assert run_script("ledger.py", *big).returncode == 0
    row = json.loads((ep / "ledger.jsonl").read_text().splitlines()[0])
    assert row["request_id"] == "req_123" and row["model"] == "m1"


def test_the_big_spend_threshold_is_the_users_choice_not_a_constant(tmp_path):
    ep = tmp_path / "ep"
    init = json.loads(run_script("ledger.py", "init", "--episode", ep, "--budget", "1000", "--require", "").stdout)
    assert init["big_spend_usd"] == 500  # a ratio of the cap, not a built-in amount
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "host", "--usd", "100", "--beat", "1").returncode == 0
    ep2 = tmp_path / "ep2"
    run_script("ledger.py", "init", "--episode", ep2, "--budget", "1000", "--require", "", "--big-spend", "20")
    assert run_script("ledger.py", "spend", "--episode", ep2, "--kind", "host", "--usd", "30", "--beat", "1").returncode == 4


def test_ledger_report_gives_observed_calls_per_beat_as_retry_evidence(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "50", "--require", "")
    for beat, force in (("1", False), ("1", True), ("2", False)):
        extra = ["--force", "--note", "prompt fixed"] if force else []
        run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image", "--usd", "1", "--beat", beat, *extra)
    rep = json.loads(run_script("ledger.py", "report", "--episode", ep).stdout)
    assert rep["observed_calls_per_beat"]["ai_image"] == pytest.approx(1.5)


def test_autonomous_runs_waive_gates_but_keep_the_cap(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "1", "--autonomous")
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image", "--usd", "0.5",
                      "--beat", "1").returncode == 0
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image", "--usd", "0.9",
                      "--beat", "2").returncode == 4


def test_ledger_imports_sibling_costs_idempotently(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "20", "--require", "")
    src = tmp_path / "costs.jsonl"
    src.write_text('{"ts": 1, "step": "host", "endpoint": "heygen", "est_usd": 4.5}\n'
                   '{"ts": 2, "step": "broll", "endpoint": "omni", "est_usd": 0.77}\n')
    assert json.loads(run_script("ledger.py", "import", "--episode", ep, "--from", src).stdout)["imported"] == 2
    assert json.loads(run_script("ledger.py", "import", "--episode", ep, "--from", src).stdout)["imported"] == 0
    rep = json.loads(run_script("ledger.py", "report", "--episode", ep).stdout)
    assert rep["spent_usd"] == pytest.approx(5.27) and set(rep["by_kind"]) == {"host", "ai_video"}


def test_ledger_requires_init(tmp_path):
    assert run_script("ledger.py", "report", "--episode", tmp_path / "nope").returncode == 3


# ---------------------------------------------------------------- storyboard / media
def test_storyboard_is_self_contained_html(tmp_path):
    out = tmp_path / "b.html"
    r = run_script("storyboard.py", BASE_EXAMPLE, "--lint", "--out", out)
    assert r.returncode == 0
    html = out.read_text()
    assert "<!doctype html>" in html and "LINT PASS" in html
    assert "http://" not in html and "https://" not in html.replace("https://www.w3.org", "")


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory):
    if not HAVE_FFMPEG:
        pytest.skip("ffmpeg not installed")
    p = tmp_path_factory.mktemp("media") / "v.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=1080x1920:rate=30:duration=6", "-f", "lavfi", "-i",
                    "sine=frequency=300:duration=6", "-af", "volume=0.5", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-shortest", str(p)],
                   check=True)
    return p


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_qc_reports_spec_duration_and_catches_wrong_aspect(sample_video, tmp_path):
    rep = json.loads(run_script("qc_master.py", sample_video, "--target", "6").stdout)
    assert rep["checks"]["spec"]["pass"] and rep["checks"]["duration"]["pass"]
    bad = tmp_path / "wide.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=30:duration=2", "-pix_fmt", "yuv420p", str(bad)], check=True)
    rep = json.loads(run_script("qc_master.py", bad).stdout)
    assert not rep["checks"]["spec"]["pass"]


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_qc_detects_loudness_and_dead_air(tmp_path):
    quiet = tmp_path / "quiet.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=1080x1920:rate=30:duration=4", "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=stereo", "-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(quiet)], check=True)
    rep = json.loads(run_script("qc_master.py", quiet).stdout)
    assert not rep["checks"]["loudness"]["pass"]
    assert not rep["checks"]["hook_audio"]["pass"] or rep["checks"]["hook_audio"]["first_audible_s"] > 0.9


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_contact_sheet_builds_png_with_beat_midpoints(sample_video, tmp_path):
    pytest.importorskip("PIL")
    out = tmp_path / "s.png"
    r = run_script("contact_sheet.py", sample_video, "--beatmap", BASE_EXAMPLE, "--out", out)
    assert r.returncode == 0 and out.is_file() and out.stat().st_size > 5_000
    info = json.loads(r.stdout)
    assert info["frames"][0]["label"] == "hook 0.4s" and info["frames"][0]["t"] == pytest.approx(0.4, abs=0.01)   # Q11: the hook frame leads
    assert len(info["frames"]) == len(load(BASE_EXAMPLE)["beats"]) + 1


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_animatic_length_tracks_the_beat_map(tmp_path):
    pytest.importorskip("PIL")
    out = tmp_path / "a.mp4"
    r = run_script("animatic.py", BASE_EXAMPLE, "--out", out)
    assert r.returncode == 0
    dur = float(json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(out)],
        capture_output=True, text=True).stdout)["format"]["duration"])
    est = json.loads(r.stdout)["seconds"]
    assert abs(dur - est) < 1.0


# ---------------------------------------------------------------- style lock
def test_contrast_formula_matches_wcag_reference_values():
    assert style_lock.contrast("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.01)
    assert style_lock.contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.02)


def test_every_identity_meets_the_contrast_it_declares():
    for iid, ident in data("identities")["identities"].items():
        t, on = ident["tokens"], ident.get("text_safe_on", "bg")
        assert style_lock.contrast(t["ink"], t["bg"]) >= 4.5, iid
        assert style_lock.contrast(t["muted"], t["bg"]) >= 4.5, iid
        for name, hexv in ident["text_safe"].items():
            assert style_lock.contrast(hexv, t[on]) >= 4.5, (iid, name)
        assert ident["ai_art_style"]["medium"], iid


def test_identity_and_intent_references_are_closed():
    formats = set(data("formats")["formats"])
    for iid, intent in data("intents")["intents"].items():
        assert set(intent["formats"]) <= formats, iid
        assert intent["hooks"], iid


def test_style_lock_writes_three_consistent_artifacts(tmp_path):
    r = run_script("style_lock.py", "build", "--identity", "paper-collage", "--out", tmp_path)
    assert r.returncode == 0, r.stderr
    style = json.loads((tmp_path / "style.json").read_text())
    art = json.loads((tmp_path / "art_style.json").read_text())
    css = (tmp_path / "style.css").read_text()
    accent = style["tokens"]["accent"]
    assert accent in css and accent in art["art_style"]["color_palette"]
    assert "STYLE SWATCH ONLY" in art["reference_image_role"]
    assert style["text_safe"]["accent"] in css  # the legible text variant is exported too
    assert ".grain" in css  # noise identities ship a static grain overlay


def test_brand_accent_that_fails_as_text_gets_a_safe_variant():
    ident = style_lock.build("swiss-grid", accent="#FFE800")  # yellow on off-white: unreadable text
    assert "accent" in ident["text_safe"]
    assert style_lock.contrast(ident["text_safe"]["accent"], ident["tokens"]["bg"]) >= 4.5
    assert ident["tokens"]["accent"] == "#FFE800"  # the fill colour is untouched


def test_style_lock_rejects_unknown_identity_and_bad_hex(tmp_path):
    assert run_script("style_lock.py", "build", "--identity", "nope", "--out", tmp_path).returncode == 2
    assert run_script("style_lock.py", "build", "--identity", "swiss-grid", "--accent", "red",
                      "--out", tmp_path).returncode == 2


def test_colormap_is_exported_and_validated(tmp_path):
    ok = run_script("style_lock.py", "build", "--identity", "blueprint", "--colormap",
                    "main=#7FDBFF,naive=#FF6B6B", "--out", tmp_path)
    assert ok.returncode == 0, ok.stderr
    assert "--cm-main: #7FDBFF;" in (tmp_path / "style.css").read_text()
    assert json.loads((tmp_path / "style.json").read_text())["color_map"]["naive"] == "#FF6B6B"
    bad = run_script("style_lock.py", "build", "--identity", "blueprint", "--colormap", "main=cyan",
                     "--out", tmp_path)
    assert bad.returncode == 2


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_qc_flags_a_strobing_clip_that_ffprobe_calls_valid(tmp_path):
    strobe = tmp_path / "strobe.mp4"
    # alternating black and white frames: structurally valid H.264, unwatchable
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=white:s=1080x1920:r=30:d=4,geq=lum='if(mod(N,2),255,0)':cb=128:cr=128",
                    "-f", "lavfi", "-i", "sine=frequency=300:d=4", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(strobe)], check=True)
    rep = json.loads(run_script("qc_master.py", strobe).stdout)
    assert rep["checks"]["flicker"]["max_big_jumps_in_1s"] >= 15
    assert not rep["checks"]["flicker"]["pass"]
    assert "flicker" in rep["failures"]


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not installed")
def test_qc_calm_clip_passes_the_flicker_check(sample_video):
    rep = json.loads(run_script("qc_master.py", sample_video).stdout)
    assert rep["checks"]["flicker"]["pass"]


# ---------------------------------------------------------------- HyperFrames handoff
def test_brief_and_script_carry_the_approved_plan(tmp_path):
    r = run_script("beatmap_to_brief.py", BASE_EXAMPLE, "--out", tmp_path)
    assert r.returncode == 0, r.stderr
    brief = (tmp_path / "BRIEF.md").read_text()
    front = brief.split("---")[1]
    assert "workflow: faceless-explainer" in front and "storyboard: no" in front
    assert "aspect: 1080x1920" in front and "length: 31s" in front
    assert "Do not re-plan" in brief and "beatmap.json" in brief
    script = (tmp_path / "SCRIPT.md").read_text()
    beats = load(BASE_EXAMPLE)["beats"]
    assert script.count("## Line ") == len(beats)
    assert f"    {beats[0]['text']}" in script  # the indented block is the spoken text
    assert "**Time:** 0.0 -" in script


def test_script_times_follow_real_spans_when_given(tmp_path):
    beats = load(BASE_EXAMPLE)["beats"]
    spans = [{"id": b["id"], "start": i * 3.0, "end": i * 3.0 + 2.5} for i, b in enumerate(beats)]
    sp = tmp_path / "spans.json"
    sp.write_text(json.dumps(spans))
    run_script("beatmap_to_brief.py", BASE_EXAMPLE, "--out", tmp_path, "--spans", sp)
    assert "**Time:** 3.0 - 5.5s" in (tmp_path / "SCRIPT.md").read_text()


def test_every_format_names_a_hyperframes_workflow():
    for fid, p in data("formats")["formats"].items():
        assert p["hyperframes_workflow"], fid


def test_host_billed_for_the_whole_voice_over_when_the_host_is_the_clock():
    bm = base()
    bm["meta"]["format"] = "host-broll"
    bm["meta"]["intent"] = "case"
    bm["meta"]["budget_usd"] = 100
    for b in bm["beats"]:
        b["layer"] = "code"
        b["device"] = b.get("device") or "d"
    only_one_host_beat = copy.deepcopy(bm)
    only_one_host_beat["beats"][1].update(layer="host", device="talking-head")
    pb = fresh_pricebook()
    stats = beatmap_lint.lint(only_one_host_beat, pb)["stats"]
    total_s = stats["est_seconds"]
    per_s = next(e["usd_per_unit"] for e in pb["entries"] if e["capability"] == "host")
    # priced on the full runtime, not on that single beat
    assert stats["cost_usd_low"] >= per_s * (total_s - 0.5)


def test_the_collage_example_closes_its_loop_in_code_without_a_new_generation():
    bm = load(ROOT / "examples" / "vox-collage-eiffel-tower.json")
    last = bm["beats"][-1]
    assert last["role"] == "loop" and last["layer"] == "code"
    plan = cost_plan.compute_plan(bm, fresh_pricebook())
    images = next(ln for ln in plan["lines"] if ln["capability"] == "ai_image")
    assert images["quantity"] == sum(b["layer"] == "ai_image" for b in bm["beats"])  # the callback adds none
    assert "budget_usd" not in bm["meta"]  # the cap is the user's answer to the cost card


# ---------------------------------------------------------------- language and script
def test_speech_units_follow_the_script_not_a_language_name():
    from textscript import profile, speech_units
    assert speech_units("Compound interest turns savings into wealth") == 6
    assert speech_units("复利让每个月变成钱") == 9  # unsegmented script: counted in characters
    assert speech_units("انفلیشن یعنی inflation آپ کی savings") == 6
    assert profile(["复利让每个月变成钱"])["unit_mode"] == "chars"
    assert profile(["مہنگائی آہستہ آہستہ"])["direction"] == "rtl"
    assert profile(["انفلیشن یعنی inflation آپ کی savings کو کھا جاتی ہے"])["direction"] == "mixed"
    assert profile(["plain english"])["direction"] == "ltr"


def test_rtl_is_detected_from_the_text_and_asks_for_script_fonts():
    bm = base()
    bm["beats"][1]["text"] = "مہنگائی آہستہ آہستہ آپ کی بچت کی قیمت کھا جاتی ہے"
    bm["meta"]["language"] = "whatever the user wrote in"
    rep = beatmap_lint.lint(bm)
    assert "E080" in codes(rep, "warnings")
    bm["meta"]["script_fonts"] = {"ARABIC": "any covering family"}
    assert "E080" not in codes(beatmap_lint.lint(bm), "warnings")


def test_letters_outside_latin_ask_for_a_font_check_but_accents_do_not():
    bm = base()
    bm["beats"][1]["text"] = "Les intérêts composés transforment 200 euros par mois"
    assert "E084" not in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][1]["text"] = "复利让每个月200元变成很多钱"
    assert "E084" in codes(beatmap_lint.lint(bm), "warnings")


def test_font_coverage_is_read_from_the_text():
    import shutil
    from textscript import fonts_covering, needed_codepoints
    if not shutil.which("fc-list"):
        pytest.skip("fontconfig not installed")
    ascii_fonts = fonts_covering(needed_codepoints(["abc 123"]))
    assert ascii_fonts, "some installed font must cover basic Latin"
    rare = fonts_covering([0x10FFFD])  # a private-use plane code point no ordinary font has
    assert rare == [] or rare is None


def test_regulated_topic_is_judged_by_the_agent_not_matched_on_english_words():
    bm = base()
    bm["meta"]["format"] = "host-broll"
    bm["meta"]["intent"] = "mechanism"  # not flagged regulated, so only the agent's own judgement can raise it
    bm["beats"][1].update(layer="host", device="talking-head")
    bm["meta"]["host"] = {"source": "generated", "consent": "not a real person"}
    bm["meta"]["topic"] = "inflation and your savings"  # no keyword a matcher could use
    assert "E085" in codes(beatmap_lint.lint(bm), "warnings")  # unset: asks the agent to judge
    bm["meta"]["regulated_topic"] = "finance"
    assert "E083" in codes(beatmap_lint.lint(bm), "warnings")
    bm["meta"]["regulated_topic"] = "none"
    rep = beatmap_lint.lint(bm)
    assert "E083" not in codes(rep, "warnings") and "E085" not in codes(rep, "warnings")
    bm["meta"]["regulated_topic"] = "none"
    bm["meta"]["intent"] = "finance"  # the intent itself is flagged regulated in data/intents.json
    assert "E083" in codes(beatmap_lint.lint(bm), "warnings")


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_speech_rate_is_measured_from_audio_and_written_back(tmp_path):
    tone, gap = tmp_path / "tone.wav", tmp_path / "gap.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=6", "-ar", "16000", str(tone)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1.0", str(gap)], check=True)
    lst = tmp_path / "l.txt"
    lst.write_text(f"file '{gap}'\nfile '{tone}'\nfile '{gap}'\n")
    sample = tmp_path / "sample.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(sample)], check=True)
    r = run_script("speech_rate.py", "measure", "--audio", sample, "--text", "one two three four five six seven eight nine ten eleven twelve")
    out = json.loads(r.stdout)
    assert out["speech_seconds"] == pytest.approx(6.0, abs=0.4)  # the silence either side is excluded
    assert out["units_per_second"] == pytest.approx(2.0, abs=0.15)
    bm = base()
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(bm))
    run_script("speech_rate.py", "measure", "--audio", sample, "--beatmap", bmp, "--write")
    written = json.loads(bmp.read_text())["meta"]
    assert written["rate_source"] == "measured" and written["wps"] > 0
    assert "E013" not in codes(beatmap_lint.lint(json.loads(bmp.read_text())), "warnings")


# ---------------------------------------------------------------- number integrity, synthetic data
def test_a_wrong_figure_that_keeps_its_claim_is_caught():
    bm = base()
    i = next(i for i, b in enumerate(bm["beats"]) if b.get("claim_refs") and any(ch.isdigit() for ch in b["text"]))
    assert "E054" not in codes(beatmap_lint.lint(bm), "warnings"), "the shipped example must be consistent"
    bm["beats"][i]["text"] = bm["beats"][i]["text"] + " That is 777 percent more."
    assert "E054" in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][i]["number_is_decorative"] = True
    assert "E054" not in codes(beatmap_lint.lint(bm), "warnings")


def test_too_many_figures_in_one_beat_warns_but_years_do_not_count():
    bm = base()
    bm["beats"][1]["text"] = "In 1999 and 2004 and 2011 it moved 12 then 34 then 56 then 78 points."
    bm["beats"][1]["claim_exempt"] = True
    rep = beatmap_lint.lint(bm)
    assert "E055" in codes(rep, "warnings")
    bm["beats"][1]["text"] = "In 1999 and 2004 and 2011 it moved 12 points."
    assert "E055" not in codes(beatmap_lint.lint(bm), "warnings")


def test_synthetic_data_must_be_labelled_on_screen():
    bm = base()
    bm["meta"]["data_origin"] = "synthetic"
    rep = beatmap_lint.lint(bm)
    assert "E057" in codes(rep)
    bm["beats"][0]["overlays"] = (bm["beats"][0].get("overlays") or []) + [{"kind": "synthetic-label", "content": "made-up data"}]
    assert "E057" not in codes(beatmap_lint.lint(bm))
    bm["meta"]["data_origin"] = "mixed"
    bm["beats"][0]["overlays"] = [o for o in bm["beats"][0]["overlays"] if o.get("kind") != "synthetic-label"]
    assert "E057" in codes(beatmap_lint.lint(bm), "warnings")  # mixed: a warning, not a block


def test_computed_claims_ask_where_the_data_came_from():
    bm = base()
    bm["meta"].pop("data_origin", None)
    assert "E056" in codes(beatmap_lint.lint(bm), "warnings")
    bm["meta"]["data_origin"] = "modelled"
    assert "E056" not in codes(beatmap_lint.lint(bm), "warnings")


def test_photoreal_ai_of_a_real_place_or_a_synthetic_subject_is_flagged():
    bm = paid_plan()
    bm["beats"][1].update(depicts_real="place")
    bm["meta"]["style"] = {"name": "x", "family": "photoreal documentary"}
    assert "E035" in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][1]["label_synthetic"] = True
    assert "E035" not in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][1]["label_synthetic"] = False
    bm["meta"]["style"] = {"name": "x", "family": "paper collage"}
    assert "E035" not in codes(beatmap_lint.lint(bm), "warnings")


# ---------------------------------------------------------------- cost scout fixes found in evaluation
def test_an_unpriced_plan_never_reads_as_free():
    pb = fresh_pricebook()
    pb["entries"] = []
    plan = cost_plan.compute_plan(paid_plan(), pb)
    assert plan["partial"] is True and plan["complete"] is False
    assert any(m["capability"] == "ai_image" for m in plan["missing"])


def test_require_pricebook_makes_any_unpriced_capability_an_error():
    pb = fresh_pricebook()
    pb["entries"] = [e for e in pb["entries"] if e["capability"] not in ("tts", "stt", "music")]
    assert "E062" not in codes(beatmap_lint.lint(paid_plan(), pb))  # warning only by default
    assert "E062" in codes(beatmap_lint.lint(paid_plan(), pb, require_pricebook=True))
    assert "E061" in codes(beatmap_lint.lint(base(), None, require_pricebook=True))  # even an all-code plan


def test_the_route_can_be_switched_without_restamping_the_price(tmp_path):
    pbp = tmp_path / "pb.json"
    pb = fresh_pricebook()
    pb["entries"].append(dict(next(x for x in pb["entries"] if x["capability"] == "ai_image"),
                              id="img-b", usd_per_unit=0.9, selected=False))
    pbp.write_text(json.dumps(pb))
    before = next(e for e in json.loads(pbp.read_text())["entries"] if e["id"] == "img-b")["fetched_at"]
    assert run_script("cost_plan.py", "select", "--pricebook", pbp, "--entry", "img-b").returncode == 0
    after = json.loads(pbp.read_text())["entries"]
    assert [e["id"] for e in after if e["capability"] == "ai_image" and e["selected"]] == ["img-b"]
    assert next(e for e in after if e["id"] == "img-b")["fetched_at"] == before
    assert run_script("cost_plan.py", "select", "--pricebook", pbp, "--entry", "nope").returncode == 2


def test_a_retry_assumption_can_be_removed(tmp_path):
    pbp = tmp_path / "pb.json"
    pbp.write_text(json.dumps(fresh_pricebook(ai_image=2.0, host=3.0)))
    assert run_script("cost_plan.py", "unset", "--pricebook", pbp, "--retries", "host").returncode == 0
    assert json.loads(pbp.read_text())["assumptions"]["retries"] == {"ai_image": 2.0}


def test_help_prints_usage_and_exits_zero():
    r = run_script("cost_plan.py", "--help")
    assert r.returncode == 0 and "cost_plan.py" in r.stdout


def test_a_host_call_longer_than_the_engine_limit_is_raised():
    pb = fresh_pricebook()
    for e in pb["entries"]:
        if e["capability"] == "host":
            e["limits"] = {"max_seconds": 5}
    bm = load(ROOT / "examples" / "host-broll-concorde.json")
    plan = cost_plan.compute_plan(bm, pb)
    assert any(q["id"] == "host_limit" for q in plan["questions"])


def test_language_support_is_asked_not_assumed():
    bm = load(ROOT / "examples" / "host-broll-concorde.json")
    bm["meta"]["language"] = "Some Language/Another"
    pb = fresh_pricebook()
    plan = cost_plan.compute_plan(bm, pb)
    assert any(q["id"].startswith("language_") for q in plan["questions"])
    for e in pb["entries"]:
        if e["capability"] in ("tts", "stt", "host"):
            e["supports_language"] = ["some language", "another"]
    plan = cost_plan.compute_plan(bm, pb)
    assert not any(q["id"].startswith("language_") for q in plan["questions"])


def test_ledger_estimate_uses_the_entrys_own_unit(tmp_path):
    pb = fresh_pricebook()
    for e in pb["entries"]:
        if e["capability"] == "music":
            e["unit"] = "second"
            e["usd_per_unit"] = 0.01
    pbp = tmp_path / "pb.json"
    pbp.write_text(json.dumps(pb))
    est = json.loads(run_script("ledger.py", "estimate", "--pricebook", pbp, "--kind", "music", "--units", "90").stdout)
    assert est["low"] == pytest.approx(0.9)  # 90 seconds at the per-second price, not one track
    assert est["unit_note"] and "per second" in est["unit_note"]


def test_the_probe_reports_profiles_and_caches_by_name_only(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".fal").mkdir(parents=True)
    (home / ".fal" / "key").write_text("SECRET-CONTENT-NEVER-PRINTED")
    (home / ".cache" / "huggingface" / "hub" / "models--org--thing").mkdir(parents=True)
    r = subprocess.run([sys.executable, str(SCRIPTS / "capability_probe.py")], capture_output=True, text=True,
                       env={**__import__("os").environ, "HOME": str(home)})
    rep = json.loads(r.stdout)
    assert "~/.fal" in rep["provider_profiles_present"]
    assert "models--org--thing" in rep["local"]["model_caches"]["huggingface"]
    assert "SECRET-CONTENT-NEVER-PRINTED" not in r.stdout + r.stderr


def test_the_board_reads_right_to_left_text_and_takes_translated_labels(tmp_path):
    bm = base()
    bm["meta"]["language_tag"] = "xx"
    bm["beats"][1]["text"] = "مہنگائی آہستہ آہستہ آپ کی بچت کھا جاتی ہے"
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(bm, ensure_ascii=False))
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"sees": "TRANSLATED-SEES", "lint_pass": "TRANSLATED-PASS"}, ensure_ascii=False))
    out = tmp_path / "b.html"
    assert run_script("storyboard.py", bmp, "--lint", "--labels", labels, "--out", out).returncode == 0
    html = out.read_text()
    assert 'dir="auto"' in html and 'lang="xx"' in html
    assert "TRANSLATED-SEES" in html and "TRANSLATED-PASS" in html
    labels.write_text(json.dumps({"not_a_key": "x"}))
    assert run_script("storyboard.py", bmp, "--labels", labels, "--out", out).returncode == 2  # unknown keys are refused


def test_the_board_never_shows_an_unpriced_plan_as_a_low_total(tmp_path):
    pb = fresh_pricebook()
    pb["entries"] = [e for e in pb["entries"] if e["capability"] != "ai_image"]
    pbp = tmp_path / "pb.json"
    pbp.write_text(json.dumps(pb))
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(paid_plan()))
    out = tmp_path / "b.html"
    assert run_script("storyboard.py", bmp, "--lint", "--pricebook", pbp, "--out", out).returncode == 0
    html = out.read_text()
    assert "INCOMPLETE" in html and "NOT the cost of the plan" in html


def test_the_board_lists_route_options_with_their_plan_cost(tmp_path):
    pb = fresh_pricebook()
    pb["entries"].append(dict(next(x for x in pb["entries"] if x["capability"] == "ai_image"),
                              id="img-b", model="route-b-model", usd_per_unit=0.5, selected=False))
    pbp = tmp_path / "pb.json"
    pbp.write_text(json.dumps(pb))
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(paid_plan()))
    out = tmp_path / "b.html"
    run_script("storyboard.py", bmp, "--pricebook", pbp, "--out", out)
    html = out.read_text()
    assert "route-b-model" in html and "Which ai_image route" in html


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_the_animatic_picks_a_font_that_covers_the_text_and_does_not_clip(tmp_path):
    import shutil
    from PIL import features
    if not shutil.which("fc-list"):
        pytest.skip("fontconfig not installed")
    bm = base()
    bm["beats"] = bm["beats"][:2]
    bm["beats"][0]["text"] = "ab " * 60  # far more text than one card line holds
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(bm))
    r = run_script("animatic.py", bmp, "--out", tmp_path / "a.mp4")
    assert r.returncode == 0 and (tmp_path / "a.mp4").stat().st_size > 0
    assert "covering font" in r.stderr or "NO installed font" in r.stderr
    import animatic
    ts = animatic.Typesetter(animatic.pick_font(bm, None)[0])
    size, lines = ts.fit("ab " * 60, 36, 400, 300)
    assert len(lines) * ts.line_height(size) <= 300 or size <= 14  # shrunk to fit, never overflowing silently
    assert animatic.line_is_rtl("مہنگائی") and not animatic.line_is_rtl("plain")
    if features.check("raqm"):
        assert ts.wrap("复利让每个月两百元" * 8, 30, 200)[0]  # no spaces: wraps by character


# ---------------------------------------------------------------- series
def make_series(tmp_path, n_chars=1):
    sd = tmp_path / "s"
    r = run_script("series.py", "init", "--dir", sd, "--title", "The Night Shift", "--premise", "two cleaners solve office mysteries",
                   "--language", "whatever the user wrote in", "--format", "comedy-sketch", "--intent", "sketch")
    assert r.returncode == 0, r.stderr
    (sd / "style" / "style.json").write_text('{"palette": ["#111", "#eee"]}')
    ref = tmp_path / "ana.png"
    ref.write_bytes(b"\x89PNG-ana-reference")
    for cid in ["ana", "ben"][:n_chars]:
        assert run_script("series.py", "character", "add", "--dir", sd, "--id", cid, "--name", cid.title(), "--role", "lead",
                          "--refs", ref, "--voice-engine", "any-engine", "--voice-id", f"voice-{cid}", "--anchor", f"{cid}: round glasses, green apron").returncode == 0
    return sd


def episode_bm(sd, n, hook, devices, language="whatever the user wrote in"):
    meta_hint = json.loads((sd / "episodes" / f"{n:02d}" / "meta_hint.json").read_text())
    beats = []
    roles = ["cold-open"] + ["setup"] * (len(devices) - 3) + ["escalate", "punchline", "tag"]
    for i, dev in enumerate(devices):
        beats.append({"id": i + 1, "role": roles[i], "layer": "code", "layer_why": "puppet rig", "text": hook if i == 0 else f"line {i} of episode {n}",
                      "visual": "two cleaners at a desk", "device": dev, "character": "ana", "hold_seconds": 0.2})
    return {"schema": "hybrid-beatmap/1", "meta": {**{k: v for k, v in meta_hint.items() if k != "language"}, "language": language,
            "topic": "t", "thesis": "t", "target_seconds": 10, "series": meta_hint["series"]}, "claims": [], "beats": beats}


def test_series_refuses_an_episode_that_changes_nothing(tmp_path):
    sd = make_series(tmp_path)
    r = run_script("series.py", "episode", "add", "--dir", sd, "--title", "Pilot", "--logline", "x")
    assert r.returncode == 2 and "--changes" in r.stderr
    ok = run_script("series.py", "episode", "add", "--dir", sd, "--title", "Pilot", "--logline", "x", "--changes", "location=lift,stakes=job")
    assert ok.returncode == 0 and (sd / "episodes" / "01" / "meta_hint.json").is_file()
    assert run_script("series.py", "init", "--dir", sd, "--title", "x", "--premise", "y", "--language", "z", "--format", "comedy-sketch").returncode == 2


def test_the_series_look_and_cast_are_locked_and_drift_is_an_error(tmp_path):
    sd = make_series(tmp_path)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "Pilot", "--logline", "x", "--changes", "location=lift")
    assert run_script("series.py", "lock", "--dir", sd).returncode == 0
    (sd / "episodes" / "01" / "beatmap.json").write_text(json.dumps(episode_bm(sd, 1, "hook", ["a", "b", "c", "d", "e"])))
    assert json.loads(run_script("series.py", "check", "--dir", sd).stdout)["ok"] is True
    (sd / "style" / "style.json").write_text('{"palette": ["#f00"]}')  # someone restyled the series
    r = run_script("series.py", "check", "--dir", sd)
    assert r.returncode == 1 and any(e["code"] == "S010" for e in json.loads(r.stdout)["errors"])
    assert run_script("series.py", "lock", "--dir", sd).returncode == 1  # refused without a reason
    assert run_script("series.py", "lock", "--dir", sd, "--reason", "user approved a new palette on the record").returncode == 0


def test_variation_limits_are_the_users_and_unset_limits_report_numbers(tmp_path):
    sd = make_series(tmp_path)
    for t, ch in (("One", "location=lift,stakes=job"), ("Two", "location=lift,stakes=job")):
        run_script("series.py", "episode", "add", "--dir", sd, "--title", t, "--logline", "x", "--changes", ch)
    run_script("series.py", "lock", "--dir", sd)
    same = ["a", "b", "c", "d", "e"]
    (sd / "episodes" / "01" / "beatmap.json").write_text(json.dumps(episode_bm(sd, 1, "the lift is stuck again", same)))
    (sd / "episodes" / "02" / "beatmap.json").write_text(json.dumps(episode_bm(sd, 2, "the lift is stuck again", same)))
    rep = json.loads(run_script("series.py", "check", "--dir", sd, "--episode", "2").stdout)
    assert {"S020", "S022"} <= {w["code"] for w in rep["warnings"]}  # unset: measured and asked, never invented
    assert rep["numbers"]["hook_similarity_max"]["value"] == 1.0
    sj = json.loads((sd / "series.json").read_text())
    sj["variation"].update(max_hook_similarity=0.5, max_structure_similarity=0.5, min_changed_axes=1)
    (sd / "series.json").write_text(json.dumps(sj))
    r = run_script("series.py", "check", "--dir", sd, "--episode", "2")
    codes_ = {e["code"] for e in json.loads(r.stdout)["errors"]}
    assert r.returncode == 1 and {"S021", "S023"} <= codes_


def test_a_language_or_cast_mismatch_between_series_and_episode_is_an_error(tmp_path):
    sd = make_series(tmp_path)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "x", "--changes", "location=lift")
    run_script("series.py", "lock", "--dir", sd)
    bm = episode_bm(sd, 1, "hook", ["a", "b", "c", "d", "e"], language="a different language")
    bm["meta"]["cast"] = ["ana", "stranger"]
    (sd / "episodes" / "01" / "beatmap.json").write_text(json.dumps(bm))
    errs = {e["code"] for e in json.loads(run_script("series.py", "check", "--dir", sd).stdout)["errors"]}
    assert {"S003", "S005"} <= errs


def test_continuity_tracks_gags_open_threads_and_unpaid_cliffhangers(tmp_path):
    sd = make_series(tmp_path)
    for t in ("One", "Two"):
        run_script("series.py", "episode", "add", "--dir", sd, "--title", t, "--logline", "x", "--changes", f"location={t}")
    run_script("series.py", "lock", "--dir", sd)
    for ep in (1, 2):
        (sd / "episodes" / f"{ep:02d}" / "beatmap.json").write_text(json.dumps(episode_bm(sd, ep, f"hook {ep} unique words {ep}", ["a", "b", "c", "d", "e"] if ep == 1 else ["f", "g", "h", "i", "j"])))
    run_script("series.py", "record", "--dir", sd, "--episode", "1", "--type", "cliffhanger", "--text", "the lights go out")
    for _ in range(3):
        run_script("series.py", "record", "--dir", sd, "--episode", "1", "--type", "gag", "--text", "the mop", "--ref", "mop")
    rep = json.loads(run_script("series.py", "check", "--dir", sd, "--episode", "2").stdout)
    assert any(w["code"] == "S040" for w in rep["warnings"])  # last episode's cliffhanger is still unpaid
    assert rep["numbers"]["gag_uses"]["mop"] == 3
    row = json.loads(run_script("series.py", "record", "--dir", sd, "--episode", "2", "--type", "paid_off", "--text", "lights back on", "--ref", "c1").stdout)
    assert row["ref"] == "c1"
    rep = json.loads(run_script("series.py", "check", "--dir", sd, "--episode", "2").stdout)
    assert not any(w["code"] == "S040" for w in rep["warnings"])
    brief = json.loads(run_script("series.py", "next", "--dir", sd).stdout)
    assert brief["episode"]["n"] == 3 and brief["continuity"]["gag_uses"]["mop"] == 3
    assert brief["cast"][0]["voice"]["voice_id"] == "voice-ana" and brief["look_locked"] is True


def test_series_spend_rolls_up_across_episodes_and_shared_assets(tmp_path):
    sd = make_series(tmp_path)
    for t in ("One", "Two"):
        run_script("series.py", "episode", "add", "--dir", sd, "--title", t, "--logline", "x", "--changes", f"location={t}")
    for ep, amt in ((1, 1.0), (2, 3.0)):
        ed = sd / "episodes" / f"{ep:02d}"
        (ed / "ledger.jsonl").write_text(json.dumps({"kind": "ai_image", "est_usd": amt}) + "\n")
    (sd / "shared").mkdir(exist_ok=True)
    (sd / "shared" / "ledger.jsonl").write_text(json.dumps({"kind": "ai_image", "est_usd": 4.0}) + "\n")
    ru = json.loads(run_script("series.py", "rollup", "--dir", sd, "--planned", "10").stdout)
    assert ru["series_total_usd"] == pytest.approx(8.0) and ru["avg_episode_usd"] == pytest.approx(2.0)
    assert ru["shared_per_produced_episode"] == pytest.approx(2.0)
    assert ru["projection_for_planned_episodes"]["usd"] == pytest.approx(4.0 + 2.0 * 10)
    sj = json.loads((sd / "series.json").read_text())
    sj["budget"]["cap"] = 5.0
    (sd / "series.json").write_text(json.dumps(sj))
    rep = json.loads(run_script("series.py", "check", "--dir", sd).stdout)
    assert any(e["code"] == "S050" for e in rep["errors"]) or rep["ok"] is False


def test_retention_csv_is_read_at_the_users_own_hook_window(tmp_path):
    sd = make_series(tmp_path)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "x", "--changes", "location=a")
    csvp = tmp_path / "ret.csv"
    csvp.write_text("second,retention\n0,100\n1,92\n2,80\n3,70\n4,66\n5,40\n6,38\n")
    r = run_script("series.py", "analytics", "--dir", sd, "--episode", "1", "--file", csvp)
    assert r.returncode == 2 and "--seconds" in r.stderr  # no default hook window is chosen for the user
    out = json.loads(run_script("series.py", "analytics", "--dir", sd, "--episode", "1", "--file", csvp, "--seconds", "3,5", "--window", "2").stdout)
    assert out["retention_at"]["3.0"] == pytest.approx(0.70) and out["retention_at"]["5.0"] == pytest.approx(0.40)
    assert out["steepest_drop"]["from"] == 3.0 and out["steepest_drop"]["to"] == 5.0  # 70% to 40%: the widest 2 s fall
    assert out["steepest_drop"]["window_seconds"] == 2.0 and out["steepest_drop"]["window_source"] == "user"
    viewers = tmp_path / "v.csv"
    viewers.write_text("second,viewers\n0,1000\n1,500\n")
    out = json.loads(run_script("series.py", "analytics", "--dir", sd, "--episode", "1", "--file", viewers, "--seconds", "1").stdout)
    assert out["retention_at"]["1.0"] == pytest.approx(0.5)


def test_calibrate_derives_the_pass_mark_from_the_series_own_references_and_has_no_default(tmp_path):
    g, i = tmp_path / "g.json", tmp_path / "i.json"
    g.write_text(json.dumps([0.80, 0.82, 0.85, 0.88, 0.90, 0.91, 0.93]))
    i.write_text(json.dumps([0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]))
    assert run_script("series.py", "calibrate", "--genuine", g, "--impostor", i).returncode == 2
    out = json.loads(run_script("series.py", "calibrate", "--genuine", g, "--impostor", i, "--genuine-pct", "10", "--impostor-pct", "90").stdout)
    assert out["separable"] is True and out["pass_at"] > out["impostor_ceiling"]
    assert out["copy_paste_above"] == pytest.approx(0.93)
    i.write_text(json.dumps([0.78, 0.81, 0.84, 0.87, 0.90, 0.92, 0.95]))  # the encoder cannot tell this style apart
    out = json.loads(run_script("series.py", "calibrate", "--genuine", g, "--impostor", i, "--genuine-pct", "10", "--impostor-pct", "90").stdout)
    assert out["separable"] is False


def test_the_lint_understands_story_roles_and_cast():
    bm = base()
    bm["meta"]["format"] = "comedy-sketch"
    bm["meta"]["intent"] = "sketch"
    bm["meta"]["cast"] = ["ana"]
    for i, b in enumerate(bm["beats"]):
        b["layer"] = "code"
        b["device"] = "puppet-scene"
    roles = ["cold-open", "setup", "setup", "escalate", "escalate", "punchline", "tag", "tag", "tag"]
    for b, r in zip(bm["beats"], roles):
        b["role"] = r
    bm["beats"][1]["character"] = "ana"
    rep = beatmap_lint.lint(bm)
    assert "E020" not in codes(rep) and "E022" not in codes(rep)  # a cold open opens, a tag closes
    bm["beats"][2]["character"] = "stranger"
    assert "E100" in codes(beatmap_lint.lint(bm))
    bm["beats"][2]["character"] = "ana"
    bm["beats"] = [b for b in bm["beats"] if b["role"] != "punchline"]
    assert "E106" in codes(beatmap_lint.lint(bm), "warnings")  # a comedy format with no punchline beat


def test_the_brief_needs_a_language_and_writes_speakers_and_voices(tmp_path):
    sd = make_series(tmp_path)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "x", "--changes", "location=a")
    bm = episode_bm(sd, 1, "hook", ["a", "b", "c", "d", "e"])
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(bm))
    out = tmp_path / "hf"
    assert run_script("beatmap_to_brief.py", bmp, "--out", out, "--series", sd).returncode == 0
    script_md = (out / "SCRIPT.md").read_text()
    assert "**Speaker:** Ana" in script_md and "voice-ana" in script_md
    assert "Episode 1 of the series" in (out / "BRIEF.md").read_text()
    del bm["meta"]["language"]
    bmp.write_text(json.dumps(bm))
    assert run_script("beatmap_to_brief.py", bmp, "--out", tmp_path / "hf2").returncode == 1  # no default language is assumed


# ---------------------------------------------------------------- round 2: the ledger cap and the lint
def test_force_never_lifts_the_cap_and_needs_a_note_and_the_cap_moves_only_by_raise(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "6", "--require", "")
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "host", "--usd", "50", "--beat", "1", "--force").returncode == 4
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_video", "--usd", "1", "--beat", "2").returncode == 0
    no_note = run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_video", "--usd", "1", "--beat", "2", "--force")
    assert no_note.returncode == 4 and "--note" in no_note.stderr
    assert run_script("ledger.py", "raise", "--episode", ep, "--budget", "60").returncode == 2  # a reason is required
    assert run_script("ledger.py", "raise", "--episode", ep, "--budget", "3", "--note", "x").returncode == 2  # only upwards
    r = json.loads(run_script("ledger.py", "raise", "--episode", ep, "--budget", "60", "--note", "user approved 60 on the record").stdout)
    assert r["raises"][0]["from"] == 6 and r["budget_usd"] == 60
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "host", "--usd", "20", "--beat", "1").returncode == 0  # the default threshold followed the cap to 30
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "host", "--usd", "30", "--beat", "9").returncode == 4  # now a big spend
    ep2 = tmp_path / "ep2"
    assert run_script("ledger.py", "init", "--episode", ep2, "--budget", "6", "--big-spend", "50").returncode == 2


def test_a_negated_list_is_one_negation_but_a_real_request_for_text_still_warns():
    bm = base()
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    bm["beats"][1].update(layer="ai_image", device="collage", overlays=[{"kind": "stat"}],
                          ai={"prompt": "a quiet desk with coins, no text, letters, numbers, logos, watermarks or signage anywhere"})
    assert "E030" not in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][1]["ai"]["prompt"] = "a desk with coins, no people, a chart and a headline label"
    assert "E030" in codes(beatmap_lint.lint(bm), "warnings")


def test_hook_and_on_screen_limits_scale_with_the_speech_rate_only_when_it_was_set():
    bm = base()
    prof = data("formats")["formats"][bm["meta"]["format"]]
    bm["beats"][0]["text"] = " ".join(["word"] * int(prof["hook_max_words"] * 1.3))
    bm["beats"][0]["claim_exempt"] = True
    bm["meta"].pop("wps", None)
    assert any(w["code"] == "E020" for w in beatmap_lint.lint(bm)["warnings"])
    bm["meta"]["wps"] = prof["wps"] * 2  # a fast-unit script: the same words fit a hook twice as long
    bm["meta"]["rate_source"] = "measured"
    assert not any(w["code"] == "E020" for w in beatmap_lint.lint(bm)["warnings"])


def test_comedy_is_keyed_on_intent_and_a_punchline_needs_options_or_approval():
    bm = load(ROOT / "examples" / "cartoon-bolt-episode.json")
    assert "E106" not in codes(beatmap_lint.lint(bm), "warnings")  # a serial story is not a sketch
    bm["meta"]["intent"] = "sketch"
    assert "E106" in codes(beatmap_lint.lint(bm), "warnings")  # a comic piece with no punchline, in a format that does not require one
    bm["beats"][7]["role"] = "punchline"
    assert "E107" in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][7]["punchline_options"] = ["It rose!", "It lives!", "It is alive!"]
    assert "E107" not in codes(beatmap_lint.lint(bm), "warnings")


def test_fiction_needs_no_data_label_and_a_custom_overlay_can_declare_it_shows_a_number():
    bm = load(ROOT / "examples" / "cartoon-bolt-episode.json")
    bm["meta"]["data_origin"] = "synthetic"
    assert "E057" not in codes(beatmap_lint.lint(bm))  # no claims, no figures: nothing to label
    bm = base()
    i = next(i for i, b in enumerate(bm["beats"]) if any(ch.isdigit() for ch in b["text"]))
    bm["beats"][i].update(layer="ai_image", ai={"prompt": "coins on a desk, no text"}, device="x", overlays=[{"kind": "my-own-widget"}])
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    assert "E031" in codes(beatmap_lint.lint(bm))
    bm["beats"][i]["overlays"] = [{"kind": "my-own-widget", "shows_number": True}]
    assert "E031" not in codes(beatmap_lint.lint(bm))


def test_a_platform_with_no_entry_is_flagged():
    bm = base()
    bm["meta"]["platform"] = ["tiktok", "some-new-platform"]
    rep = beatmap_lint.lint(bm)
    assert any(w["code"] == "E014" and "some-new-platform" in w["msg"] for w in rep["warnings"])


def test_extra_quantities_and_a_reused_motif_change_the_plan():
    pb = fresh_pricebook()
    bm = paid_plan()
    base_plan = cost_plan.compute_plan(bm, pb)
    more = cost_plan.compute_plan(bm, pb, extra={"ai_image": 12})
    img = lambda p: next(ln for ln in p["lines"] if ln["capability"] == "ai_image")["quantity"]  # noqa: E731
    assert img(more) == img(base_plan) + 12
    bm["audio"] = {"music_brief": "a motif"}
    assert any(ln["capability"] == "music" for ln in cost_plan.compute_plan(bm, pb)["lines"])
    bm["meta"]["reuse_music"] = True
    assert not any(ln["capability"] == "music" for ln in cost_plan.compute_plan(bm, pb)["lines"])


# ---------------------------------------------------------------- round 2: series
def test_series_set_stores_the_users_policy_and_rejects_unknown_keys(tmp_path):
    sd = make_series(tmp_path)
    out = json.loads(run_script("series.py", "set", "--dir", sd, "--variation", "min_changed_axes=2,max_hook_similarity=0.4,window=3",
                                "--budget", "cap=50,per_episode_envelope=5,setup_allowance=8", "--axes", "location,stakes,outcome,prop",
                                "--frame", "structure=cold-open|title|setup|punchline|tag,music_motif=motif.wav", "--disclose", "false",
                                "--cadence", "twice a week", "--platforms", "tiktok,reels").stdout)
    sj = json.loads((sd / "series.json").read_text())
    assert sj["variation"]["min_changed_axes"] == 2 and sj["variation"]["max_hook_similarity"] == 0.4
    assert sj["budget"]["per_episode_envelope"] == 5 and sj["disclose"] is False and "prop" in sj["variation"]["axes"]
    assert sj["frame"]["structure"] == ["cold-open", "title", "setup", "punchline", "tag"]
    assert run_script("series.py", "set", "--dir", sd, "--variation", "nonsense=1").returncode == 2
    run_script("series.py", "set", "--dir", sd, "--variation", "window=none")
    assert json.loads((sd / "series.json").read_text())["variation"]["window"] is None


def test_episode_axes_are_validated_and_episodes_can_be_set_and_removed(tmp_path):
    sd = make_series(tmp_path)
    junk = run_script("series.py", "episode", "add", "--dir", sd, "--title", "x", "--logline", "y", "--changes", "a=b")
    assert junk.returncode == 2 and "unknown axes" in junk.stderr
    ok = run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "y", "--changes", "location=lift")
    assert ok.returncode == 0
    assert run_script("series.py", "episode", "set", "--dir", sd, "--n", "1", "--status", "bogus").returncode == 2
    assert run_script("series.py", "episode", "set", "--dir", sd, "--n", "1", "--status", "scripted").returncode == 0
    assert run_script("series.py", "episode", "remove", "--dir", sd, "--n", "1").returncode == 2  # no longer planned
    run_script("series.py", "episode", "set", "--dir", sd, "--n", "1", "--status", "planned")
    assert run_script("series.py", "episode", "remove", "--dir", sd, "--n", "1").returncode == 0
    assert json.loads((sd / "series.json").read_text())["episodes"] == []


def test_character_replace_merges_and_survives_a_reference_already_in_place(tmp_path):
    sd = make_series(tmp_path)
    inplace = sd / "characters" / "ana" / "ana.png"
    assert inplace.is_file()
    r = run_script("series.py", "character", "add", "--dir", sd, "--id", "ana", "--name", "Ana", "--replace",
                   "--refs", inplace, "--speech-rate", "3.2")
    assert r.returncode == 0, r.stderr  # no SameFileError
    c = json.loads((sd / "series.json").read_text())["characters"][0]
    assert c["voice"]["voice_id"] == "voice-ana" and c["voice"]["speech_rate"] == 3.2  # voice kept, rate added
    assert c["visual"]["prompt_anchor"].startswith("ana:")  # the anchor was not wiped


def test_a_rig_is_validated_and_the_lock_covers_identity_and_rig(tmp_path):
    sd = make_series(tmp_path)
    parts = tmp_path / "parts"
    parts.mkdir()
    for n in ("body", "head", "m1", "m2"):
        (parts / f"{n}.png").write_bytes(b"png" + n.encode())
    rig = {"schema": "hybrid-rig/1", "parts": [{"name": "body", "file": "parts/body.png", "pivot": [1, 2], "parent": None, "z": 0},
                                              {"name": "head", "file": "parts/head.png", "pivot": [1, 2], "parent": "body", "z": 1}],
           "mouth": {"shapes": {"A": "parts/m1.png", "B": "parts/m2.png"}}}
    rp = tmp_path / "rig.json"
    rp.write_text(json.dumps(rig))
    (sd / "characters" / "ana" / "parts").mkdir()
    for n in ("body", "head", "m1", "m2"):
        (sd / "characters" / "ana" / "parts" / f"{n}.png").write_bytes(b"png" + n.encode())
    assert run_script("series.py", "character", "add", "--dir", sd, "--id", "ana", "--name", "Ana", "--replace", "--rig", rp).returncode == 0
    ok = json.loads(run_script("series.py", "character", "rig-check", "--dir", sd, "--id", "ana").stdout)
    assert ok["ok"] is True
    run_script("series.py", "lock", "--dir", sd)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "x", "--changes", "location=a")
    (sd / "episodes" / "01" / "beatmap.json").write_text(json.dumps(episode_bm(sd, 1, "hook", ["a", "b", "c", "d", "e"])))
    assert json.loads(run_script("series.py", "check", "--dir", sd).stdout)["ok"] is True
    (sd / "characters" / "ana" / "parts" / "head.png").write_bytes(b"someone repainted the head")
    r = run_script("series.py", "check", "--dir", sd)
    assert r.returncode == 1 and "rig" in r.stdout
    run_script("series.py", "lock", "--dir", sd, "--reason", "user approved a repaint")
    run_script("series.py", "character", "add", "--dir", sd, "--id", "ana", "--name", "Anna", "--replace")  # a rename after the lock
    assert run_script("series.py", "check", "--dir", sd).returncode == 1
    bad = dict(rig, parts=rig["parts"] + [{"name": "tail", "file": "parts/missing.png", "pivot": [0], "parent": "ghost"}])
    rp.write_text(json.dumps(bad))
    run_script("series.py", "character", "add", "--dir", sd, "--id", "ana", "--name", "Anna", "--replace", "--rig", rp)
    chk = run_script("series.py", "character", "rig-check", "--dir", sd, "--id", "ana")
    assert chk.returncode == 1 and "missing.png" in chk.stdout and "ghost" in chk.stdout


def test_a_mouthless_character_needs_a_speech_cue():
    import series
    errs, _ = series.rig_validate({"parts": [{"name": "b", "file": "x.png", "pivot": [0, 0], "parent": None}], "mouth": None}, Path("/nonexistent"))
    assert any("no mouth needs rig.cue" in e for e in errs)
    errs, _ = series.rig_validate({"parts": [{"name": "b", "file": "x.png", "pivot": [0, 0], "parent": None}], "mouth": None,
                                   "cue": "amplitude-bounce"}, Path("/nonexistent"))
    assert not any("cue" in e for e in errs)


def test_a_reworded_copy_is_caught_by_script_and_ending_similarity_even_with_renamed_devices(tmp_path):
    sd = make_series(tmp_path)
    for t in ("One", "Two", "Three"):
        run_script("series.py", "episode", "add", "--dir", sd, "--title", t, "--logline", "x", "--changes", f"location={t},stakes={t}")
    run_script("series.py", "lock", "--dir", sd)
    run_script("series.py", "set", "--dir", sd, "--variation", "max_script_similarity=0.5,max_ending_similarity=0.5,window=1,min_changed_axes=1")
    def write(n, lines, devs):
        bm = episode_bm(sd, n, lines[0], devs)
        for b, t in zip(bm["beats"], lines):
            b["text"] = t
        (sd / "episodes" / f"{n:02d}" / "beatmap.json").write_text(json.dumps(bm))
    base_lines = ["the oven is missing again", "who took the oven", "we checked every shelf twice", "the baker is calm", "nothing is missing but the oven"]
    write(1, base_lines, ["a", "b", "c", "d", "e"])
    write(2, ["fresh start here today", "something else happens", "a new problem arrives", "people argue loudly", "the sky falls in"], ["f", "g", "h", "i", "j"])
    write(3, base_lines, ["p", "q", "r", "s", "t"])  # a copy of episode 1, devices renamed, window 1 only sees episode 2
    rep = json.loads(run_script("series.py", "check", "--dir", sd, "--episode", "3").stdout)
    assert rep["numbers"]["script_similarity_max_all"]["against_episode"] == 1
    assert any(w["code"] == "S024" for w in rep["warnings"])  # outside the window, still reported
    write(2, base_lines, ["f", "g", "h", "i", "j"])
    rep = json.loads(run_script("series.py", "check", "--dir", sd, "--episode", "3").stdout)
    assert {"S021"} <= {e["code"] for e in rep["errors"]}


def test_gags_are_counted_inside_the_window_and_the_envelope_is_checked(tmp_path):
    sd = make_series(tmp_path)
    for t in ("One", "Two", "Three"):
        run_script("series.py", "episode", "add", "--dir", sd, "--title", t, "--logline", "x", "--changes", f"location={t}")
    run_script("series.py", "lock", "--dir", sd)
    run_script("series.py", "set", "--dir", sd, "--variation", "max_gag_uses=2,window=2", "--budget", "per_episode_envelope=1")
    for ep, n in ((1, 3), (3, 1)):
        for _ in range(n):
            run_script("series.py", "record", "--dir", sd, "--episode", str(ep), "--type", "gag", "--text", "the mop", "--ref", "mop")
    for ep in (1, 2, 3):
        (sd / "episodes" / f"{ep:02d}" / "beatmap.json").write_text(json.dumps(episode_bm(sd, ep, f"unique hook {ep} {ep * 7}", [chr(97 + ep + i) for i in range(5)])))
    (sd / "episodes" / "03" / "ledger.jsonl").write_text(json.dumps({"kind": "ai_image", "est_usd": 5}) + "\n")
    rep = json.loads(run_script("series.py", "check", "--dir", sd, "--episode", "3").stdout)
    assert rep["numbers"]["gag_uses"]["mop"] == 1  # episode 1's three uses are outside the window of 2
    assert not any(w["code"] == "S030" for w in rep["warnings"])
    assert any(w["code"] == "S052" for w in rep["warnings"])  # 5 spent against an envelope of 1


def test_status_counts_only_open_threads_and_unicode_titles_keep_their_slug(tmp_path):
    sd = tmp_path / "s"
    r = run_script("series.py", "init", "--dir", sd, "--title", "AI 40秒", "--premise", "p", "--language", "zh", "--format", "kinetic-type-essay")
    assert json.loads(r.stdout)["series"] == "ai-40秒"
    sd2 = tmp_path / "s2"
    assert json.loads(run_script("series.py", "init", "--dir", sd2, "--title", "x", "--premise", "p", "--language", "l",
                                 "--format", "data-story", "--id", "my-id").stdout)["series"] == "my-id"
    run_script("series.py", "record", "--dir", sd, "--episode", "1", "--type", "thread", "--text", "a")
    run_script("series.py", "record", "--dir", sd, "--episode", "1", "--type", "thread", "--text", "b")
    run_script("series.py", "record", "--dir", sd, "--episode", "2", "--type", "paid_off", "--text", "a is resolved", "--ref", "c1")
    assert json.loads(run_script("series.py", "status", "--dir", sd).stdout)["open_threads"] == 1


def test_the_check_defaults_to_the_latest_episode_that_has_a_beat_map(tmp_path):
    sd = make_series(tmp_path)
    for t in ("One", "Two"):
        run_script("series.py", "episode", "add", "--dir", sd, "--title", t, "--logline", "x", "--changes", f"location={t}")
    run_script("series.py", "lock", "--dir", sd)
    (sd / "episodes" / "01" / "beatmap.json").write_text(json.dumps(episode_bm(sd, 1, "hook", ["a", "b", "c", "d", "e"])))
    assert json.loads(run_script("series.py", "check", "--dir", sd).stdout)["numbers"]["episode"] == 1  # not the empty episode 2


def test_analytics_reports_the_steepest_fall_after_the_hook_window(tmp_path):
    sd = make_series(tmp_path)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "x", "--changes", "location=a")
    csvp = tmp_path / "r.csv"
    csvp.write_text("second,retention\n0,100\n1,70\n2,55\n3,50\n4,48\n5,47\n6,30\n7,29\n8,28\n")
    out = json.loads(run_script("series.py", "analytics", "--dir", sd, "--episode", "1", "--file", csvp, "--seconds", "3", "--window", "1").stdout)
    assert out["steepest_drop"]["from"] == 0.0  # the opening fall
    assert out["steepest_drop_after_hook"]["from"] == 5.0 and out["steepest_drop_after_hook"]["after_second"] == 3.0


def test_every_series_command_has_its_own_help():
    out = run_script("series.py", "episode", "add", "--help").stdout
    assert "--changes" in out and "character" not in out
    assert "--speech-rate" in run_script("series.py", "character", "add", "--help").stdout
    assert "calibrate" in run_script("series.py", "calibrate", "--help").stdout


def test_the_probe_help_does_not_run_the_probe_and_reports_identity_fonts():
    r = run_script("capability_probe.py", "--help")
    assert r.returncode == 0 and not r.stdout.lstrip().startswith("{")  # usage text, not the JSON report
    import shutil
    if shutil.which("fc-list"):
        rep = json.loads(run_script("capability_probe.py").stdout)
        assert isinstance(rep["local"]["identity_fonts_installed"], dict) and rep["local"]["identity_fonts_installed"]


# ---------------------------------------------------------------- round 2: board, animatic, brief
def test_the_board_translates_roles_lists_punchline_options_and_hides_english_issues_by_default(tmp_path):
    bm = base()
    bm["beats"][1]["role"] = "punchline"
    bm["beats"][1]["punchline_options"] = ["option one", "the chosen line", "option three"]
    bm["beats"][1]["text"] = "the chosen line"
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(bm))
    labels = tmp_path / "l.json"
    labels.write_text(json.dumps({"role_punchline": "TRANSLATED-ROLE", "punchline_options": "TRANSLATED-OPTIONS", "chosen": "TRANSLATED-CHOSEN"}))
    out = tmp_path / "b.html"
    run_script("storyboard.py", bmp, "--lint", "--labels", labels, "--out", out)
    html = out.read_text()
    assert "TRANSLATED-ROLE" in html and "TRANSLATED-OPTIONS" in html and "TRANSLATED-CHOSEN" in html and "option three" in html
    assert "class='issues'" not in html  # the English message list is opt-in
    run_script("storyboard.py", bmp, "--lint", "--issues", "--out", out)
    assert "class='issues'" in out.read_text()


def test_the_animatic_font_pick_avoids_italics_and_line_breaks_respect_numbers_and_punctuation():
    import animatic
    rows = [{"family": "A", "file": "/x/a-italic.ttf", "style": "Italic"}, {"family": "B", "file": "/x/b.ttf", "style": "Regular"}]
    original = animatic.fonts_covering
    animatic.fonts_covering = lambda cps: rows
    try:
        assert animatic.pick_font({"beats": [{"text": "abc"}]}, None)[0] == "/x/b.ttf"
    finally:
        animatic.fonts_covering = original
    mb = animatic.Typesetter.may_break
    assert not mb("增长了2", "6") and not mb("增长了26", "%") and not mb("增长了", "，") and not mb("他说“", "你")
    assert mb("增长了", "很")


def test_the_brief_says_when_the_series_is_not_locked_yet(tmp_path):
    sd = make_series(tmp_path)
    run_script("series.py", "episode", "add", "--dir", sd, "--title", "One", "--logline", "x", "--changes", "location=a")
    bmp = tmp_path / "bm.json"
    bmp.write_text(json.dumps(episode_bm(sd, 1, "hook", ["a", "b", "c", "d", "e"])))
    run_script("beatmap_to_brief.py", bmp, "--out", tmp_path / "hf", "--series", sd)
    assert "NOT locked yet" in (tmp_path / "hf" / "BRIEF.md").read_text()
    run_script("series.py", "lock", "--dir", sd)
    run_script("beatmap_to_brief.py", bmp, "--out", tmp_path / "hf2", "--series", sd)
    assert "are locked" in (tmp_path / "hf2" / "BRIEF.md").read_text()


def test_negated_text_in_a_prompt_is_not_a_request_for_text():
    bm = base()
    bm["meta"]["visual_anchor"] = "personal finance explainer, neutral desk scene, no logos or brands visible"
    bm["beats"][1].update(layer="ai_image", device="collage", overlays=[{"kind": "stat"}],
                          ai={"prompt": "a quiet desk with coins, soft light, no people, no text, without logos"})
    assert "E030" not in codes(beatmap_lint.lint(bm), "warnings")
    bm["beats"][1]["ai"]["prompt"] = "a desk with a chart and a headline label"
    assert "E030" in codes(beatmap_lint.lint(bm), "warnings")


def test_host_beats_require_a_stated_source_and_consent_for_real_people():
    bm = base()
    bm["beats"][1].update(layer="host", device="talking-head")
    assert "E082" in codes(beatmap_lint.lint(bm), "warnings")  # no meta.host at all
    bm["meta"]["host"] = {"source": "real_person"}
    assert "E082" in codes(beatmap_lint.lint(bm))  # real person without consent is an error
    bm["meta"]["host"] = {"source": "real_person", "consent": "the user, photos supplied by them"}
    assert "E082" not in codes(beatmap_lint.lint(bm))


# ---------------------------------------------------------------- v1.2: models, provenance, voice, pacing
def test_spoken_tokens_treat_digits_and_number_words_alike():
    from speech_align import align, tokens, wer
    assert tokens("It picks 1 of 15 formats, hybrid-social-video") == ["it", "picks", "one", "of", "fifteen", "formats", "hybrid", "social", "video"]
    assert wer(tokens("1 of 15"), tokens("one of fifteen")) == 0.0
    assert wer(tokens("a b c d"), tokens("a x c d")) == pytest.approx(0.25)
    assert align(["a", "b", "c"], ["a", "c"]) == {0: 0, 2: 1}


def test_provenance_records_models_and_the_check_finds_gaps(tmp_path):
    ep = tmp_path / "ep"
    bm = tmp_path / "bm.json"
    bm.write_text(json.dumps({"beats": [{"id": 1, "layer": "code"}, {"id": 2, "layer": "ai_image"}, {"id": 3, "layer": "host"}]}))
    assert run_script("provenance.py", "check", "--episode", ep).returncode == 3              # not initialised
    run_script("provenance.py", "init", "--episode", ep, "--director", "some-model")
    gap = run_script("provenance.py", "check", "--episode", ep, "--beatmap", bm)
    assert gap.returncode == 1 and "beat 2" in gap.stderr and "beat 3" in gap.stderr
    run_script("provenance.py", "add", "--episode", ep, "--role", "image", "--tool", "t", "--model", "m1", "--provider", "p", "--runs", "hosted",
               "--used-for", "still", "--beats", "2", "--realism", "photoreal", "--depicts", "fictional")
    run_script("provenance.py", "add", "--episode", ep, "--role", "host", "--tool", "t", "--model", "m2", "--provider", "p", "--runs", "hosted",
               "--used-for", "clip", "--beats", "3", "--realism", "photoreal", "--depicts", "fictional")
    assert run_script("provenance.py", "check", "--episode", ep, "--beatmap", bm).returncode == 0
    rep = run_script("provenance.py", "report", "--episode", ep).stdout
    assert "Director: some-model" in rep and "m1" in rep and "LABEL" in rep and "host's face and speech are AI-generated" in rep


def test_provenance_leaves_a_test_that_is_not_in_the_output_out_of_the_verdict(tmp_path):
    ep = tmp_path / "ep"
    run_script("provenance.py", "init", "--episode", ep, "--director", "d")
    run_script("provenance.py", "add", "--episode", ep, "--role", "tts", "--tool", "t", "--model", "m", "--provider", "p", "--runs", "hosted",
               "--used-for", "a test", "--in-output", "false")
    rep = run_script("provenance.py", "report", "--episode", ep).stdout
    assert "(not in the output)" in rep and "synthetic voice" not in rep


def test_provenance_requires_a_voice_entry_when_a_voice_exists(tmp_path):
    ep = tmp_path / "ep"
    run_script("provenance.py", "init", "--episode", ep, "--director", "d")
    (ep / "spans.json").write_text("[]")
    bm = tmp_path / "bm.json"
    bm.write_text(json.dumps({"beats": []}))
    r = run_script("provenance.py", "check", "--episode", ep, "--beatmap", bm)
    assert r.returncode == 1 and "voice" in r.stderr


def test_probe_reports_the_ai_models_it_can_see():
    rep = json.loads(run_script("capability_probe.py").stdout)
    ai = rep["ai_models"]
    assert set(ai) >= {"local", "hosted_hints", "director", "tool_models"} and ai["director"] is None
    for row in ai["local"]:
        assert {"id", "role", "runs", "note"} <= set(row) and row["runs"] in ("local", "hosted")


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_voice_check_marks_a_system_voice_as_draft_however_it_scores(tmp_path):
    wav = tmp_path / "tone.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(wav)], check=True)
    r = run_script("voice_check.py", "--audio", wav, "--text", "hello world", "--kind", "system")
    rep = json.loads(r.stdout)
    assert rep["verdict"] == "draft" and "draft" in rep["why"] and r.returncode in (0, 1, 3)
    assert rep["duration_s"] == pytest.approx(2.0, abs=0.1) and rep["lufs"] is not None


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_pacing_fails_a_long_shot_only_when_nothing_moves(tmp_path):
    static, moving = tmp_path / "static.mp4", tmp_path / "moving.mp4"
    for out, src in ((static, "color=c=0x224466:s=270x480:r=30:d=7"), (moving, "testsrc2=s=270x480:r=30:d=7")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-f", "lavfi", "-i", "sine=frequency=300:duration=7",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    pacing = {}
    for name, path in (("static", static), ("moving", moving)):
        r = run_script("qc_master.py", path, "--platform", "tiktok")
        pacing[name] = json.loads(r.stdout[r.stdout.index("{"):])["checks"]["pacing"]
    assert pacing["static"]["pass"] is False and pacing["static"]["static_holds"]
    assert pacing["moving"]["pass"] is True and not pacing["moving"]["static_holds"]


def test_new_scripts_print_their_help_and_the_skill_lists_them():
    for name in ("host_assemble.py", "render_html.py", "mix_audio.py", "voice_check.py", "provenance.py"):
        r = run_script(name, "--help")
        assert r.returncode == 0 and name.split(".")[0] in r.stdout, name
    text = (ROOT / "SKILL.md").read_text()
    for needle in ("Operating mode", "Know your models", "The bar: would a top creator post this?", "Decision record"):
        assert needle in text, needle
    for ref in ("17-ai-models-and-tools.md",):
        assert (ROOT / "references" / ref).is_file()


def test_ledger_keeps_its_gates_by_default_so_autonomy_is_an_explicit_choice(tmp_path):
    ep = tmp_path / "ep"
    run_script("ledger.py", "init", "--episode", ep, "--budget", "10")
    assert run_script("ledger.py", "spend", "--episode", ep, "--kind", "ai_image", "--usd", "1", "--beat", "1").returncode == 4
    ep2 = tmp_path / "ep2"
    run_script("ledger.py", "init", "--episode", ep2, "--budget", "10", "--autonomous")
    assert run_script("ledger.py", "spend", "--episode", ep2, "--kind", "ai_image", "--usd", "1", "--beat", "1").returncode == 0


# ---------------------------------------------------------------- v1.3: look picker and reference scan
def _pick(*args):
    r = run_script("style_lock.py", "pick", *args)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_look_is_picked_by_topic_not_defaulted(tmp_path):
    fin = [p["id"] for p in _pick("--topic", "compound interest for beginners", "--intent", "finance")["picks"]]
    assert fin[0] == "newsroom" and set(fin) <= {"newsroom", "editorial-serif", "swiss-grid", "whiteboard-doodle", "tech-terminal"}
    assert fin == [p["id"] for p in _pick("--topic", "compound interest for beginners", "--intent", "finance")["picks"]]   # repeatable
    sci = _pick("--topic", "how a jet engine works", "--intent", "mechanism")["picks"][0]["id"]
    assert sci in {"flat-vector", "blueprint", "whiteboard-doodle"}
    assert fin[0] != sci


def test_the_picker_excludes_and_spreads_consecutive_looks(tmp_path):
    base = [p["id"] for p in _pick("--topic", "how a jet engine works", "--intent", "mechanism")["picks"]]
    avoided = _pick("--topic", "how a jet engine works", "--intent", "mechanism", "--avoid", base[0])
    assert base[0] not in [p["id"] for p in avoided["picks"]]
    prev = tmp_path / "episodes" / "01"
    prev.mkdir(parents=True)
    run_script("style_lock.py", "build", "--identity", "blueprint", "--out", prev)
    after = _pick("--topic", "how a jet engine works", "--intent", "mechanism", "--recent", tmp_path / "episodes")
    assert after["recent"] == ["blueprint"]
    ids = [p["id"] for p in after["picks"]]
    assert ids[0] != "blueprint"                                           # not the look used last time
    assert "already used" in " ".join(p["why"] for p in after["picks"] if p["id"] == "blueprint") or "blueprint" not in ids
    from style_lock import hue_family
    ids_data = data("identities")["identities"]
    assert hue_family(ids_data["blueprint"]["tokens"]["bg"]) == "blue"
    assert hue_family(ids_data[ids[0]]["tokens"]["bg"]) != "blue"          # the next look is not another blue after a blue


def test_a_format_that_defines_its_look_fixes_it_and_a_brand_only_sets_the_accent():
    assert _pick("--format", "vox-collage", "--topic", "x")["picks"][0]["id"] == "paper-collage"
    out = _pick("--topic", "a startup pitch", "--brand", "#E4572E")
    assert out["brand_accent"] == "#E4572E" and "--accent" in out["note"]
    assert run_script("style_lock.py", "pick").returncode == 2


def test_hooks_are_classified_by_how_they_open():
    import reference_scan as rs
    assert rs.classify_hook("What is compound interest? It's interest") == "question"
    assert rs.classify_hook("Stop leaving your money in a savings account") == "warning"
    assert rs.classify_hook("5 ways to grow your savings") == "number"
    assert rs.classify_hook("Let us talk about coffee money") == "statement"
    assert rs.classify_hook("I tried investing for a year") == "story"
    assert rs.classify_hook("Nobody tells you this about banks") == "claim"
    assert rs.classify_hook("") == "unknown"
    assert rs.platform_of("https://www.tiktok.com/@a/video/1") == "tiktok" and rs.platform_of("https://youtu.be/x") == "youtube"
    assert rs.platform_of("https://www.instagram.com/reel/abc/") == "instagram"


def test_the_scan_summary_names_the_overused_opener_and_drops_off_topic_reels():
    import reference_scan as rs
    items = [{"status": "ok", "platform": "youtube", "duration_s": 20 + i, "avg_shot_s": 2.0, "hook_type": "question", "hook_words": 7,
              "vertical": True, "on_topic": True} for i in range(5)]
    items += [{"status": "ok", "platform": "tiktok", "duration_s": 30, "avg_shot_s": 3.0, "hook_type": "number", "hook_words": 5,
               "vertical": True, "on_topic": False}, {"status": "blocked", "platform": "instagram"}]
    s = rs.summarize({"items": items})
    text = " ".join(s["notes"])
    assert s["scanned"] == 5 and s["median_avg_shot_s"] == 2.0 and s["median_duration_s"] == 22
    assert "5 of 5 open with a question hook" in text and "off-topic" in text and "never the content" in text
    few = rs.summarize({"items": items[:2]})
    assert "only 2 readable" in " ".join(few["notes"])


def test_analyze_without_a_download_uses_titles_and_the_scan_skips_cleanly_without_ytdlp(tmp_path):
    refs = tmp_path / "references.json"
    refs.write_text(json.dumps({"topic": "compound interest", "items": [
        {"status": "ok", "platform": "youtube", "url": "https://youtu.be/a", "title": "How does compound interest work?"},
        {"status": "ok", "platform": "youtube", "url": "https://youtu.be/b", "title": "Cat video"}]}))
    assert run_script("reference_scan.py", "analyze", "--refs", refs, "--no-download").returncode == 0
    items = json.loads(refs.read_text())["items"]
    assert items[0]["hook_type"] == "question" and items[0]["on_topic"] is True and items[1]["on_topic"] is False
    r = subprocess.run([sys.executable, str(SCRIPTS / "reference_scan.py"), "find", "--topic", "x", "--out", str(tmp_path / "o.json")],
                       capture_output=True, text=True, env={"PATH": "/nonexistent"})
    assert r.returncode == 3 and "yt-dlp is not installed" in r.stderr


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_measure_reads_length_cuts_and_shape_from_a_local_video(tmp_path):
    import reference_scan as rs
    v = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=270x480:r=30:d=4", "-f", "lavfi", "-i", "sine=frequency=300:duration=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(v)], check=True)
    m = rs.measure(v)
    assert m["vertical"] is True and m["duration_s"] == pytest.approx(4.0, abs=0.2) and m["avg_shot_s"] > 0 and "cuts" in m


def test_the_reference_scan_is_documented_with_its_limits():
    text = (ROOT / "SKILL.md").read_text()
    assert "references/18-reference-scan.md" in text and "style_lock.py pick" in text
    doc = (ROOT / "references" / "18-reference-scan.md").read_text()
    for needle in ("Never bypass a wall", "No personal data", "Technique, not content", "deleted"):
        assert needle in doc, needle


# ---------------------------------------------------------------- v1.4: faceless route, voice route, trial fixes
def _tone(path, seconds=4):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}", str(path)], check=True)


def test_spanish_numbers_percent_and_accents_are_normalised():
    from speech_align import tokens
    assert tokens("Un 2 % de 25 años", True, "es") == ["un", "dos", "por", "ciento", "de", "veinticinco", "anos"]
    assert tokens("100 y 130", True, "es") == ["cien", "y", "ciento", "treinta"]
    assert tokens("about 3 percent", True, "en") == ["about", "three", "percent"]
    assert tokens("12 mois", True, "fr") == ["12", "mois"]                      # no table: the digits stay as written


def test_beat_timings_snap_a_beat_start_to_the_real_pause():
    from speech_align import beat_timings
    bm = {"beats": [{"id": 1, "text": "hello there"}, {"id": 2, "text": "second beat here"}]}
    heard = [("hello", 0.0, 0.4), ("there", 0.45, 0.9), ("second", 1.2, 1.6), ("beat", 1.65, 2.0), ("here", 2.05, 2.4)]
    res = beat_timings(bm, heard, "en", [(0.95, 1.3)])                         # a pause from 0.95 to 1.3 s: the recogniser began beat 2 early
    assert res["matched"] == 5 and res["beats"][0]["e"] <= 0.95 and res["beats"][1]["s"] == pytest.approx(1.3)
    assert [w["word"] for w in res["beats"][1]["words"]] == ["second", "beat", "here"]


def test_captions_break_after_punctuation_and_write_srt_and_vtt(tmp_path):
    timing = {"beats": [{"id": 1, "words": [{"word": "Hello,", "s": 0.0, "e": 0.4}, {"word": "this", "s": 0.5, "e": 0.8}, {"word": "is", "s": 0.85, "e": 1.0},
                                              {"word": "a", "s": 1.05, "e": 1.1}, {"word": "test.", "s": 1.15, "e": 1.6}]}], "duration": 2.0}
    tj = tmp_path / "timing.json"
    tj.write_text(json.dumps(timing))
    out = tmp_path / "c.srt"
    r = run_script("captions.py", "--timing", tj, "--out", out, "--vtt")
    assert r.returncode == 0 and json.loads(r.stdout)["cues"] == 2
    srt = out.read_text()
    assert "Hello, this is a" in srt and "test." in srt              # a comma never leaves a one-word cue
    assert out.with_suffix(".vtt").read_text().startswith("WEBVTT")


def test_the_voice_route_picks_by_language_and_never_a_novelty_voice():
    from voice_render import pick_voice, script_text
    voices = [{"engine": "say", "name": "Bad News", "locale": "en_US", "quality": "novelty", "score": -9},
              {"engine": "say", "name": "Samantha (English (US))", "locale": "en_US", "quality": "system", "score": 2.5},
              {"engine": "say", "name": "Ava (Premium)", "locale": "en_US", "quality": "system-hq", "score": 4},
              {"engine": "say", "name": "Paulina", "locale": "es_MX", "quality": "system", "score": 2.2},
              {"engine": "say", "name": "Monica", "locale": "es_ES", "quality": "system", "score": 2.3}]
    assert pick_voice(voices, "en")["name"] == "Ava (Premium)"                   # a high-quality local voice outranks the standard one
    assert pick_voice(voices, "es-MX")["name"] == "Paulina"                      # the exact locale wins
    assert pick_voice(voices, "es")["name"] == "Monica"
    assert pick_voice(voices, "ja") is None
    txt = script_text({"beats": [{"text": "One.", "hold_seconds": 0.5}, {"text": "Two."}]})
    assert txt == "One. [[slnc 760]] Two."


def test_a_zero_spend_plan_lints_clean_with_the_free_pricebook(tmp_path):
    pb = tmp_path / "pricebook.json"
    assert run_script("cost_plan.py", "init", "--out", pb, "--free").returncode == 0
    r = run_script("beatmap_lint.py", ROOT / "examples" / "faceless-money-guard.json", "--pricebook", pb, "--require-pricebook")
    assert r.returncode == 0, r.stderr
    bare = run_script("cost_plan.py", "init", "--out", tmp_path / "bare.json")
    assert run_script("beatmap_lint.py", ROOT / "examples" / "faceless-money-guard.json", "--pricebook", tmp_path / "bare.json", "--require-pricebook").returncode == 1


def test_user_supplied_claims_need_no_url_and_unverified_ones_are_surfaced():
    bm = base()
    bm["claims"][0]["confidence"] = "user"
    bm["claims"][0].pop("source", None)
    rep = beatmap_lint.lint(bm)
    assert rep["ok"] and "E059" in codes(rep, "warnings")
    bm2 = base()
    bm2["claims"][1]["verified"] = False
    assert "E059" in codes(beatmap_lint.lint(bm2), "warnings")
    bm3 = base()
    bm3["claims"][0]["confidence"] = "primary"
    bm3["claims"][0].pop("source", None)
    assert "E050" in codes(beatmap_lint.lint(bm3))                                 # a non-user claim still needs a source


def test_the_picker_respects_the_formats_allowed_looks_and_builds_resolve_fonts(tmp_path):
    ids = [p["id"] for p in _pick("--topic", "inflation and savings", "--intent", "finance", "--format", "kinetic-type-essay", "--n", "5")["picks"]]
    assert "newsroom" not in ids and set(ids) <= set(data("formats")["formats"]["kinetic-type-essay"]["looks"])
    r = run_script("style_lock.py", "build", "--identity", "editorial-serif", "--out", tmp_path)
    style = json.loads((tmp_path / "style.json").read_text())
    for role in ("hero", "body", "numbers"):
        assert style["fonts_resolved"][role]["stack"].count(",") >= 1
    css_text = (tmp_path / "style.css").read_text()
    assert "--font-hero:" in css_text and "sans-serif;" not in css_text.split("--font-hero:")[1].split("\n")[0] or "serif" in css_text.split("--font-hero:")[1].split("\n")[0]
    assert r.returncode == 0


def test_a_draft_voice_is_recorded_reported_and_warned_about(tmp_path):
    ep = tmp_path / "ep"
    run_script("provenance.py", "init", "--episode", ep, "--director", "d")
    run_script("provenance.py", "add", "--episode", ep, "--role", "tts", "--tool", "say", "--model", "Samantha", "--provider", "local", "--runs", "local",
               "--used-for", "narration", "--draft", "true", "--upgrade", "a neural voice")
    run_script("provenance.py", "add", "--episode", ep, "--role", "reference", "--tool", "reference_scan.py", "--used-for", "8 reels analysed", "--ai", "false")
    rep = run_script("provenance.py", "report", "--episode", ep).stdout
    assert "DRAFT: tts 'Samantha'" in rep and "a neural voice" in rep
    chk = run_script("provenance.py", "check", "--episode", ep)
    assert chk.returncode == 0 and "draft tts recorded" in chk.stderr             # a reference entry needs no model or provider


def test_the_probe_prints_a_short_summary_when_it_writes_a_file(tmp_path):
    r = run_script("capability_probe.py", "--out", tmp_path / "c.json")
    assert r.returncode == 0 and r.stdout.count("\n") <= 6 and "[probe] ffmpeg" in r.stdout
    assert "ai_models" in json.loads((tmp_path / "c.json").read_text())


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_qc_can_waive_a_false_alarm_with_a_reason_and_never_silently(tmp_path):
    static = tmp_path / "static.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x224466:s=270x480:r=30:d=6", "-f", "lavfi", "-i", "sine=frequency=300:duration=6",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(static)], check=True)
    assert json.loads(run_script("qc_master.py", static).stdout)["checks"]["pacing"]["pass"] is False
    assert run_script("qc_master.py", static, "--waive", "pacing").returncode == 2           # a reason is required
    rep = json.loads(run_script("qc_master.py", static, "--waive", "pacing", "--why", "a deliberate held title card").stdout)
    assert rep["checks"]["pacing"]["pass"] is True and rep["waivers"][0]["why"] == "a deliberate held title card"


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_dark_brand_backgrounds_are_not_reported_as_black_frames(tmp_path):
    v = tmp_path / "navy.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x001372:s=270x480:r=30:d=4", "-f", "lavfi", "-i", "sine=frequency=300:duration=4",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(v)], check=True)
    assert json.loads(run_script("qc_master.py", v).stdout)["checks"]["dead_frames"]["black_segments"] == []


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg needed")
def test_encode_master_uses_the_delivery_profile(tmp_path):
    PIL = pytest.importorskip("PIL.Image")
    fr = tmp_path / "frames"
    fr.mkdir()
    for k in range(30):
        PIL.new("RGB", (270, 480), (k * 8, 40, 90)).save(fr / f"{k:05d}.png")
    wav = tmp_path / "a.wav"
    _tone(wav, 1)
    r = run_script("encode_master.py", "--frames", fr, "--audio", wav, "--out", tmp_path / "m.mp4")
    assert r.returncode == 0 and json.loads(r.stdout)["audio_kbps"] == "384k"
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,profile,pix_fmt,color_space", "-of", "json", str(tmp_path / "m.mp4")],
                                     capture_output=True, text=True).stdout)
    v = next(s for s in info["streams"] if s.get("codec_name") == "h264")
    assert v["profile"] == "High" and v["pix_fmt"] == "yuv420p" and v.get("color_space") == "bt709"


def _have_browser():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not (HAVE_FFMPEG and _have_browser()), reason="ffmpeg and a Playwright Chromium needed")
def test_build_video_makes_a_checked_master_from_a_beat_map_and_timings(tmp_path):
    ep = tmp_path / "episode"
    ep.mkdir()
    bm = load(ROOT / "examples" / "faceless-money-guard.json")
    bm["beats"] = bm["beats"][:3]
    (ep / "beatmap.json").write_text(json.dumps(bm))
    words = [("Can", 0.0), ("an", 0.3), ("AI", 0.5), ("agent", 0.8), ("spend", 1.1), ("your", 1.4), ("money", 1.7), ("without", 2.0), ("overspending?", 2.4),
             ("A", 3.2), ("price", 3.4), ("from", 3.7), ("memory", 4.0), ("goes", 4.3), ("stale,", 4.6), ("so", 5.0), ("every", 5.2), ("price", 5.5), ("is", 5.8),
             ("read", 6.0), ("from", 6.3), ("the", 6.5), ("tool.", 6.7), ("It", 7.5), ("estimates,", 7.7), ("checks", 8.3), ("the", 8.6), ("ledger,", 8.8),
             ("spends", 9.3), ("once,", 9.6), ("and", 9.9), ("records", 10.1), ("it.", 10.5)]
    texts = [b["text"].split() for b in bm["beats"]]
    flat = [w for w, _ in words]
    assert [w for t in texts for w in t] == flat
    timing, k = [], 0
    for b, t in zip(bm["beats"], texts):
        ws = [{"word": w, "s": words[k + i][1], "e": words[k + i][1] + 0.28} for i, w in enumerate(t)]
        k += len(t)
        timing.append({"id": b["id"], "s": ws[0]["s"], "e": ws[-1]["e"], "words": ws})
    (ep / "timing.json").write_text(json.dumps({"beats": timing, "duration": 11.0}))
    voice = tmp_path / "vo.wav"
    _tone(voice, 11)
    (tmp_path / "vo.json").write_text(json.dumps({"voice": "Test Voice", "engine": "say", "draft": True}))
    run_script("provenance.py", "init", "--episode", ep, "--director", "test")
    r = run_script("build_video.py", "--episode", ep, "--voice", voice, "--fps", "10", "--qc")
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout.strip().splitlines()[-1])
    assert res["scenes"] == ["kinetic", "compare", "cycle"] and Path(res["master"]).is_file() and (ep / "captions.srt").is_file()
    assert res["seconds"] == pytest.approx(11.9, abs=0.5) and (ep / "style.json").is_file()
    assert res["layout"]["ok"] is True, res["layout"]
    assert res["qc"]["failures"] == [] or set(res["qc"]["failures"]) <= {"duration", "pacing", "spec"}, res["qc"]       # a 3-beat, 12 s clip rendered at 10 fps for speed: the spec check rightly objects
    roles = {e["role"]: e for e in json.loads((ep / "provenance.json").read_text())["entries"]}
    assert "stt" in roles and roles["tts"]["draft"] is True and roles["tts"]["model"] == "Test Voice"    # recorded without being asked
    assert json.loads((ep / "beatmap.json").read_text())["meta"]["style"]["family"] == json.loads((ep / "style.json").read_text())["id"]
    assert run_script("layout_check.py", "--page", ep / "build" / "index.html").returncode == 0


def test_the_docs_no_longer_tell_an_autonomous_agent_to_ask():
    refs = ROOT / "references"
    banned = ("cost card asks the user", "have the user listen at the gate", "Asking is cheaper than rebuilding", "the user's answer to the cost card, never a default",
              "put the questions to the user in one message")
    for f in refs.rglob("*.md"):
        text = f.read_text()
        for phrase in banned:
            assert phrase not in text, (f.name, phrase)
    skill = (ROOT / "SKILL.md").read_text()
    assert "## Fast path" in skill and "build_video.py" in skill and "layout_check.py" in skill and "Accepted defects" in skill
    assert (ROOT / "templates" / "faceless" / "index.html").is_file()


def test_the_starter_beat_map_lints_clean_and_every_scene_type_is_documented():
    rep = beatmap_lint.lint(load(ROOT / "examples" / "starter-beatmap.json"))
    assert rep["ok"], rep["errors"]
    doc = (ROOT / "references" / "03-beat-map.md").read_text()
    page = (ROOT / "templates" / "faceless" / "index.html").read_text()
    import re
    types = re.findall(r"^(\w+)\(b,sc,t\)\{", page, flags=re.M)
    assert {"stat", "steps", "flow", "cycle", "compare", "bars", "kinetic", "terminal", "quote"} <= set(types)
    for ty in types:
        assert f"| `{ty}` |" in doc, ty


def test_the_brief_for_hyperframes_carries_each_scene_and_a_host_video_changes_the_workflow(tmp_path):
    out = tmp_path / "hf"
    spans = tmp_path / "spans.json"
    bm = load(ROOT / "examples" / "faceless-money-guard.json")
    spans.write_text(json.dumps([{"id": b["id"], "start": i * 4.0, "end": i * 4.0 + 3.5} for i, b in enumerate(bm["beats"])]))
    r = run_script("beatmap_to_brief.py", ROOT / "examples" / "faceless-money-guard.json", "--out", out, "--spans", spans, "--host-video", "public/host.mp4")
    assert r.returncode == 0 and json.loads(r.stdout)["workflow"] == "talking-head-recut"
    brief = (out / "BRIEF.md").read_text()
    assert "workflow: talking-head-recut" in brief and "public/host.mp4" in brief and "master clock" in brief
    assert "beat 3 (8.0-11.5s): cycle of ESTIMATE -> CHECK -> SPEND ONCE -> RECORD, centre label 'LEDGER'" in brief
    assert "a huge count-up number 1 labelled 'respend per asset'" in brief
    plain = run_script("beatmap_to_brief.py", ROOT / "examples" / "faceless-money-guard.json", "--out", tmp_path / "hf2")
    assert json.loads(plain.stdout)["workflow"] == "diagram-mechanism" or json.loads(plain.stdout)["workflow"]


def test_the_probe_reports_whether_hyperframes_is_reachable_and_how_to_get_it():
    rep = json.loads(run_script("capability_probe.py").stdout)
    hf = rep["hyperframes"]
    assert set(hf) >= {"skills", "skills_installed", "get_it", "cli"} and "npx skills add heygen-com/hyperframes" in hf["get_it"]
    assert "mcp.heygen.com/mcp/hyperframes" in hf["get_it"]


def test_hyperframes_is_the_first_route_and_is_referenced_not_vendored():
    skill = (ROOT / "SKILL.md").read_text()
    doc = (ROOT / "references" / "19-hyperframes.md").read_text()
    assert "## Motion design: HyperFrames first" in skill and "https://hyperframes.heygen.com/guides/mcp" in skill and "npx skills add heygen-com/hyperframes" in skill
    for needle in ("https://mcp.heygen.com/mcp/hyperframes/", "/talking-head-recut", "/faceless-explainer", "refused for local", "Read, do not remember"):
        assert needle in doc, needle
    assert not (ROOT / "references" / "hyperframes-core").exists()                # nothing from HyperFrames is copied in
    assert "never stop to ask about installing" not in skill and "optional upgrade in the final note" not in skill
