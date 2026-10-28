"""Tests for the person-aware effects: tracking helpers, the compositor's depth rules, every effect on a synthetic frame, plans and word cues, assets, and a tiny render.

Nothing here downloads anything or needs a real person: the matte is a drawn ellipse and the fonts fall back to the system's.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
cv2 = pytest.importorskip("cv2")
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fx_assets  # noqa: E402
import fx_core  # noqa: E402
import fx_registry  # noqa: E402
import person_fx  # noqa: E402
import person_track  # noqa: E402
from fx_registry import EFFECTS, Fx  # noqa: E402

HAVE_FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    """No downloads: assets resolve to nothing, so fonts fall back to the system's and the matte to a drawn one."""
    monkeypatch.setenv("SER_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(fx_assets, "ensure", lambda name, quiet=True: None)


def make_ctx(w=540, h=960):
    img = np.tile(np.linspace(0.25, 0.6, h, dtype=np.float32)[:, None, None], (1, w, 3)).copy()
    face = (w * 0.5, h * 0.27, w * 0.2, w * 0.26)
    m = person_track.ParamMatte()((img * 255).astype(np.uint8), face)
    top, shoulder = person_track.matte_geometry(m, face)
    return fx_core.Ctx(w, h, 30.0, 0.0, img, m.astype(np.float32), (*face, top, shoulder))


def cards():
    return [Image.new("RGB", (270, 480), (40 + 30 * i, 80, 120)) for i in range(4)]


# ---------------------------------------------------------------------------------------------------------------- registry and docs

def test_catalog_files_are_current():
    assert (ROOT / "data" / "effects.json").read_text(encoding="utf-8") == fx_registry.dump_catalog()
    doc = (ROOT / "references" / "20-person-aware-effects.md").read_text(encoding="utf-8")
    block = doc.split("<!-- effects:start -->\n")[1].split("\n<!-- effects:end -->")[0]
    assert block.strip() == person_fx.catalog_markdown().strip(), "run: person_fx.py catalog --doc and paste it between the markers"


def test_every_effect_is_described():
    for name, e in EFFECTS.items():
        assert e.desc and e.family in ("type", "light", "camera", "cards", "ui", "data", "glass", "frame"), name
        assert e.seconds[0] < e.seconds[1], name


# ------------------------------------------------------------------------------------------------------------ every effect, one frame

@pytest.mark.parametrize("name", sorted(EFFECTS))
def test_effect_renders_and_keeps_the_head_clear(name):
    spec = EFFECTS[name]
    e = Fx({"fx": name, "start": 0.0, "end": 3.0})
    e.cards = cards()
    worst = 0.0
    for lt in (0.35, 1.5, 2.7):
        c = make_ctx()
        c.lt = lt
        c.t = lt
        spec.fn(c, e)
        assert c.img.shape == (960, 540, 3) and np.isfinite(c.img).all(), f"{name} at {lt}s"
        assert 0.0 <= float(c.img.min()) and float(c.img.max()) <= 1.001, f"{name} left the 0..1 range"
        worst = max(worst, c.cover)
    assert spec.cover_ok or worst <= 0.06, f"{name} covers {worst:.0%} of the head"


# ------------------------------------------------------------------------------------------------------------------- the compositor

def test_depth_rules():
    c = make_ctx()
    white = np.ones((c.H, c.W, 4), np.float32)
    inside = (int(c.fy), int(c.fx))
    outside = (int(c.H * 0.12), 4)
    assert c.m[inside] > 0.9 and c.m[outside] < 0.1
    base = c.img.copy()
    fx_core.comp(c, white, 0, 0, 1.0, "behind")
    assert np.allclose(c.img[inside], base[inside], atol=1e-3), "a 'behind' layer must not draw over the person"
    assert np.allclose(c.img[outside], 1.0, atol=1e-3), "a 'behind' layer must draw where there is no person"
    c = make_ctx()
    fx_core.comp(c, white, 0, 0, 1.0, "guard")
    assert not np.allclose(c.img[inside], 1.0, atol=1e-2), "a 'guard' layer must not cover the head"
    c = make_ctx()
    fx_core.comp(c, white, 0, 0, 1.0, "front")
    assert c.cover > 0.9, "a full-frame front layer covers the head and the audit must see it"


def test_glass_bends_and_protects():
    c = make_ctx()
    before = c.img.copy()
    fx_core.glass(c, (60, 570, 480, 780), None, "front")
    assert not np.allclose(c.img, before), "glass must change the pixels under it"
    assert np.allclose(c.img[:100], before[:100]), "glass must not touch pixels outside its box"
    c = make_ctx()
    before = c.img.copy()
    box = (c.fx - 100, c.fy - 120, c.fx + 100, c.fy + 120)
    fx_core.glass(c, box, None, "guard")
    hx, hy = int(c.hx), int(c.hy)
    assert np.allclose(c.img[hy, hx], before[hy, hx], atol=1e-3), "guarded glass must leave the head alone"


def test_camera_keeps_the_face_where_it_says():
    c = make_ctx()
    fx_core.face_cam(c, 1.6, 0.4)
    assert abs(c.fy - c.H * 0.4) < c.H * 0.03
    assert c.cam[0] == pytest.approx(1.6, rel=0.01)
    c = make_ctx()
    fx_core.camera(c, 9.0, c.fx, c.fy)
    assert c.cam[0] <= 2.0 + 1e-6, "zoom is capped at 2x"


def test_text_and_easing_helpers():
    assert fx_core.count_text("197K", 1.0) == "197K" and fx_core.count_text("$4,200", 0.0).startswith("$0")
    assert fx_core.typed("hello", 0.5) in ("hel", "he")
    assert fx_core.ease_back(1.0) == pytest.approx(1.0) and fx_core.ease_out(0) == 0
    im = fx_core.fit_text("A VERY LONG HEADLINE THAT MUST SHRINK", 300, "display", 400)
    assert im.width <= 300 + 2 * (int(400 * 0.2) + 4) and im.mode == "RGBA"
    assert fx_core.rgb("#ffcc00") == (255, 204, 0) and fx_core.rgb("fc0") == (255, 204, 0) and fx_core.rgb(None, (1, 2, 3)) == (1, 2, 3)
    pts = [(0, 0), (10, 0), (10, 10)]
    part = fx_core.path_part(pts, 0.75)
    assert part[-1] == pytest.approx((10, 5)), "a stroke drawn 75% of the way ends at 75% of its length"


# -------------------------------------------------------------------------------------------------------------------- tracking bits

def test_smoothing_has_no_lag_and_fills_gaps():
    n = 60
    x = np.array([[0.0 if i < 30 else 10.0, 1.0, 1.0, 1.0, 1.0, 1.0] for i in range(n)])
    x[40:45, 0] = np.nan
    out = person_track.smooth_rows(x, 30.0)
    assert np.isfinite(out).all()
    half = int(np.argmax(out[:, 0] > 5.0))
    assert abs(half - 30) <= 1, "the two-pass filter must cross the midpoint where the step is, not later"


def test_param_matte_is_a_person_shape():
    c = make_ctx()
    assert c.m.max() == pytest.approx(1.0, abs=0.01) and c.m[: int(c.top * 0.5)].max() < 0.05
    assert c.top < c.fy < c.chin < c.shoulder + 1


# ------------------------------------------------------------------------------------------------------------------------ assets

def test_assets_refuse_a_wrong_file(tmp_path, monkeypatch):
    monkeypatch.undo()
    monkeypatch.setenv("SER_CACHE", str(tmp_path))
    spec = fx_assets.catalog()["yunet"]
    p = tmp_path / spec["file"]
    p.parent.mkdir(parents=True)
    p.write_bytes(b"not the model")
    assert fx_assets.verified("yunet") is None and not p.exists(), "a file with the wrong size or hash must be refused and removed"
    assert fx_assets.main(["path", "nope"]) == 2


def test_assets_catalog_is_pinned():
    for name, spec in fx_assets.catalog().items():
        assert len(spec["sha256"]) == 64 and spec["bytes"] > 1000 and spec["url"].startswith("https://") and spec["licence"], name


# --------------------------------------------------------------------------------------------------------------- plans and word cues

WORDS = [{"t": t, "s": 0.5 * i, "e": 0.5 * i + 0.4} for i, t in enumerate("making a reel stop asking one ai tool to do everything great videos mix 4 layers".split())]


def test_word_cue_lands_on_the_word():
    plan, issues = person_fx.resolve_plan([{"fx": "word-behind", "on": "do everything", "text": "X", "dur": 2.0}], WORDS, 20.0)
    assert not issues and plan[0]["start"] == pytest.approx(4.5 - 0.15) and plan[0]["end"] == pytest.approx(plan[0]["start"] + 2.0)
    plan, issues = person_fx.resolve_plan([{"fx": "stamp", "on": "stop asking", "until": "everything"}], WORDS, 20.0)
    assert plan[0]["end"] > plan[0]["start"] + 3.0


def test_plan_problems_are_reported():
    _, issues = person_fx.resolve_plan([{"fx": "wordbehind", "start": 1}], WORDS, 20.0)
    assert issues and "word-behind" in issues[0]["msg"]
    _, issues = person_fx.resolve_plan([{"fx": "stamp", "on": "never said"}], WORDS, 20.0)
    assert issues and "not heard" in issues[0]["msg"]
    _, issues = person_fx.resolve_plan([{"fx": "stamp", "on": "a reel"}], None, 20.0)
    assert issues and "word times" in issues[0]["msg"]
    _, issues = person_fx.resolve_plan([{"fx": "punch-in", "start": 1, "end": 3}, {"fx": "slow-push", "start": 2, "end": 6}], WORDS, 20.0)
    assert any("both move the camera" in i["msg"] for i in issues)
    plan, issues = person_fx.resolve_plan([{"fx": "stamp", "start": 18, "end": 25}], WORDS, 20.0)
    assert plan[0]["end"] == 20.0 and issues[0]["level"] == "warn"
    plan, _ = person_fx.resolve_plan([{"fx": "glitter-spotlight", "start": 1, "end": 3}], WORDS, 20.0)
    assert plan[0]["fx"] == "spotlight" and plan[0]["look"] == "sparkle"


def test_numbers_must_come_from_the_beat_map():
    bm = {"claims": [{"id": "c1", "text": "Median reel reach is 197K"}], "beats": [{"id": 1, "text": "Four layers", "overlays": [{"kind": "stat", "content": "15 formats"}]}]}
    ok = [{"fx": "big-number", "text": "197K", "start": 1, "end": 3}, {"fx": "big-number", "text": "15", "start": 4, "end": 6}]
    assert not person_fx.number_lint(ok, bm)
    bad = person_fx.number_lint([{"fx": "big-number", "text": "98%", "start": 1, "end": 3}], bm)
    assert bad and "98" in bad[0]["msg"] and bad[0]["level"] == "error"
    assert not person_fx.number_lint([{"fx": "big-number", "text": "98%", "decorative": True, "start": 1, "end": 3}], bm)


def test_plan_from_beatmap(tmp_path):
    import fx_plan_from_beatmap
    bm = {"beats": [{"id": 1, "layer": "host", "text": "Four layers", "overlays": [{"kind": "count-up", "content": "4 layers"}]},
                    {"id": 2, "layer": "code", "text": "x", "overlays": [{"kind": "stat", "content": "9"}]},
                    {"id": 3, "layer": "host", "text": "Open it", "overlays": [{"kind": "stat", "content": "github.com/x/y"}, {"kind": "mystery", "content": "?"}]}]}
    (tmp_path / "bm.json").write_text(json.dumps(bm))
    (tmp_path / "spans.json").write_text(json.dumps([{"id": 1, "start": 0, "end": 3}, {"id": 2, "start": 3, "end": 6}, {"id": 3, "start": 6, "end": 9}]))
    assert fx_plan_from_beatmap.main([str(tmp_path / "bm.json"), "--spans", str(tmp_path / "spans.json"), "--out", str(tmp_path / "plan.json")]) == 0
    plan = json.loads((tmp_path / "plan.json").read_text())["effects"]
    assert [p["fx"] for p in plan] == ["big-number", "quote-card"], "host beats only; a stat with no figure becomes a card; an unknown kind is skipped"
    assert plan[0]["text"] == "4" and plan[0]["label"] == "layers" and 0 <= plan[0]["start"] < plan[0]["end"] <= 3.3
    resolved, issues = person_fx.resolve_plan(plan, None, 9.0)
    assert not [i for i in issues if i["level"] == "error"] and len(resolved) == 2


def test_example_plan_resolves():
    plan, _ = person_fx.load_plan(ROOT / "examples" / "person-fx" / "plan.json")
    words = [{"t": t, "s": 0.4 * i, "e": 0.4 * i + 0.3} for i, t in enumerate(("stop asking everything 4 layers never wrong prices every beat how do you use it describe the reel " * 3).split())]
    resolved, issues = person_fx.resolve_plan(plan, words, 60.0)
    assert len(resolved) == len(plan) and not [i for i in issues if i["level"] == "error"]


# ----------------------------------------------------------------------------------------------------------------------- end to end

@pytest.mark.skipif(not HAVE_FFMPEG, reason="needs ffmpeg")
def test_tiny_render_keeps_audio_and_length(tmp_path):
    src = tmp_path / "in.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=180x320:rate=15:duration=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src)], check=True)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"effects": [{"fx": "grade", "start": 0.2, "end": 1.2, "kind": "bw"}, {"fx": "stamp", "start": 1.0, "end": 1.9, "text": "OK"}]}))
    out = tmp_path / "out.mp4"
    assert person_fx.main(["render", str(plan), str(src), str(out), "--width", "180"]) == 0
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(out)], capture_output=True, text=True).stdout)
    kinds = {s["codec_type"] for s in probe["streams"]}
    assert kinds == {"video", "audio"} and abs(float(probe["format"]["duration"]) - 2.0) < 0.2
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert (v["width"], v["height"]) == (180, 320)
    log = json.loads(out.with_suffix(".fx.json").read_text())
    assert [e["fx"] for e in log["effects"]] == ["grade", "stamp"] and log["schema"] == "hybrid-fxlog/1"
    # the frames outside every window are byte-for-byte the source decode: the effect touched only its window
    a = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vf", "select=eq(n\\,0)", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-vf", "select=eq(n\\,0)", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    assert len(a) == len(b) and np.abs(np.frombuffer(a, np.uint8).astype(int) - np.frombuffer(b, np.uint8).astype(int)).mean() < 3.0
