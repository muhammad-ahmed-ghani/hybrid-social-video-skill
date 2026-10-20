#!/usr/bin/env python3
"""beatmap_lint.py - the free gate between the script and the first paid call.

    python3 beatmap_lint.py beatmap.json            # human summary on stderr, JSON on stdout
    python3 beatmap_lint.py beatmap.json --strict   # warnings also fail (exit 1)
    python3 beatmap_lint.py beatmap.json --quiet    # JSON only
    python3 beatmap_lint.py beatmap.json --pricebook episode/pricebook.json [--require-pricebook] [--bakeoff N]

Validates a hybrid beat map (schema: references/03-beat-map.md) against the
format profile in data/formats.json and the craft rules that cost real money
to learn: numbers belong to the code layer, AI beats need an anchor, every
fact needs a source, duration is set by WORDS, never fix it in audio.

Cost is never read from a file shipped with the skill. With --pricebook (the per-episode
file the cost scout fills, references/14-cost-scout.md) the plan is priced from live,
sourced prices by cost_plan.compute_plan. Without one, cost is reported as UNKNOWN
(warning E061). Under --require-pricebook, which Gate 1 uses, a missing pricebook and ANY unpriced
capability (voice, transcription, music as well as the paid layers) are errors. A local engine is
priced 0 with source type local, so an all-local plan passes with a pricebook that says so.

Exit codes: 0 clean (warnings allowed) | 1 errors (or warnings under --strict)
            2 unreadable input / usage.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unicodedata  # noqa: E402

from cost_plan import compute_plan, load_pricebook  # noqa: E402
from hx_common import (AI_LAYERS, CLOSING_ROLES, LAYERS, OPENING_ROLES, ROLES, TIERS, data,  # noqa: E402
                       eprint, est_beat_seconds, load_json, parse_args, word_count)
from textscript import beatmap_texts, is_unsegmented, needs_font_check  # noqa: E402
from textscript import profile as text_profile  # noqa: E402

_est_beat_seconds = est_beat_seconds
PAID_LAYERS = ("ai_image", "ai_video", "host")

RISKY_SCENES = re.compile(
    r"\b(flags?|banners?|crowds?|protest\w*|rall(?:y|ies)|march\w*|soldiers?|army|"
    r"troops?|police|uniforms?|insignia|emblems?|mob|riot\w*|election\w*|parliament|"
    r"demonstrat\w*)\b", re.I)
TEXT_IN_PROMPT = re.compile(
    r"\b(text|label(?:s|led)?|caption|title card|headline|sign(?:age)?|logo|"
    r"infographic|chart|graph|diagram|screenshot|ui|interface|dashboard|"
    r"equation|formula)\b", re.I)
# stat-bearing numbers: 12%, $9.6B, 3.5 hours, 2003, 1,200, 25-150 Hz
NUMBER_RE = re.compile(r"(?:[$€£]\s?)?\d[\d,]*(?:\.\d+)?\s?(?:%|[kKmMbB]\b|x\b)?")
STYLISED = ("collage", "illustration", "vector", "paper", "flat", "cartoon", "stylized", "stylised")
NUMBER_OVERLAYS = {"stat", "count-up", "countup", "bar-chart", "line-chart", "chart",
                   "comparison", "ranking", "scale", "number", "counter", "map-data",
                   "table", "timeline", "equation", "data"}
# a negation covers its whole list: "no text, letters, numbers, logos or signage" is one negation
NEGATED = re.compile(r"\b(?:no|without|free of|never|avoid)\b(?:\s+[\w'-]+){1,3}"
                     r"(?:\s*(?:,|\bor\b|\band\b)\s*(?:no\s+)?[\w'-]+(?:\s+[\w'-]+){0,2})*", re.I)
ZONE_RISK = {"bottom", "lower", "right_rail", "top_bar"}  # UI-covered on vertical platforms


class Report:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def err(self, code: str, msg: str, beat=None, fix: str = "") -> None:
        self.errors.append({"code": code, "beat": beat, "msg": msg, "fix": fix})

    def warn(self, code: str, msg: str, beat=None, fix: str = "") -> None:
        self.warnings.append({"code": code, "beat": beat, "msg": msg, "fix": fix})


def _overlay_kinds(beat: dict) -> set[str]:
    out = set()
    for ov in beat.get("overlays") or []:
        if isinstance(ov, dict):
            out.add(str(ov.get("kind", "")).lower())
        else:
            out.add(str(ov).lower())
    if beat.get("device"):
        out.add(str(beat["device"]).lower())
    return out


def _spelled_number(text: str, words: list[str]) -> bool:
    """True if `text` contains one of the number words the agent supplied for this language."""
    low = text.casefold()
    tokens = set(re.findall(r"\w+", low, re.UNICODE))
    for w in words:
        w = w.casefold().strip()
        if not w:
            continue
        if any(is_unsegmented(c) for c in w) or " " in w:
            if w in low:
                return True
        elif w in tokens:
            return True
    return False


def _number_tokens(text: str) -> list[tuple[str, bool]]:
    """Digit strings in a text, Unicode digits folded to ASCII. Each is (digits, has_magnitude_suffix)."""
    folded = "".join(str(unicodedata.digit(c)) if c.isdigit() and not c.isascii() else c for c in text)
    out = []
    for m in re.finditer(r"\d+(?:[.,\u066b\u066c]\d+)*(\s?[kKmMbB]\b)?", folded):
        out.append((re.sub(r"\D", "", m.group(0)), bool(m.group(1))))
    return out


def _stylised(ai: dict, meta: dict) -> bool:
    style = (ai.get("style") or meta.get("style", {}).get("family", "") or "").lower()
    return any(k in style for k in STYLISED)


def _is_year(raw_tokens: list[str], digits: str, rng: list) -> bool:
    """A four-digit figure in the range, written bare (no separator, currency or unit), is a year."""
    return len(digits) == 4 and rng[0] <= int(digits) <= rng[1] and any(
        r.strip() == digits for r in raw_tokens)


def lint(bm: dict, pricebook: dict | None = None, require_pricebook: bool = False, bakeoff: int = 0) -> dict:
    rep = Report()
    formats = data("formats")["formats"]
    platforms = data("platforms")

    meta = bm.get("meta") or {}
    beats = bm.get("beats") or []
    claims = {c.get("id"): c for c in (bm.get("claims") or []) if isinstance(c, dict)}

    # ---- schema ---------------------------------------------------------
    for k in ("topic", "thesis", "format", "target_seconds", "language"):
        if not meta.get(k):
            rep.err("E001", f"meta.{k} is required", fix=f"add meta.{k}")
    if not beats:
        rep.err("E001", "beats[] is empty")
        return _finish(rep, {}, bm)

    fmt_id = meta.get("format")
    prof = formats.get(fmt_id)
    if fmt_id and not prof:
        rep.err("E002", f"unknown format '{fmt_id}'",
                fix="use one of: " + ", ".join(sorted(formats)))
    prof = prof or next(iter(formats.values()))
    tier = meta.get("tier", prof.get("default_tier", "R1"))
    if tier not in TIERS:
        rep.err("E002", f"tier '{tier}' invalid", fix="one of " + "/".join(TIERS))

    intents = data("intents")["intents"]
    intent = meta.get("intent")
    if not intent:
        rep.warn("E005", "meta.intent missing: pick the story skeleton first",
                 fix="one of: " + ", ".join(sorted(intents)))
    elif intent not in intents:
        rep.err("E005", f"unknown intent '{intent}'", fix="one of: " + ", ".join(sorted(intents)))
    elif fmt_id in formats and fmt_id not in intents[intent]["formats"]:
        rep.warn("E005", f"format '{fmt_id}' is unusual for intent '{intent}'",
                 fix="usual formats: " + ", ".join(intents[intent]["formats"]))
    if intent in intents and intents[intent].get("misconception"):
        if not any(b.get("misconception") for b in beats) and not meta.get("misconception_note"):
            rep.warn("E006", f"intent '{intent}' works best with a 'what you probably think' beat",
                     fix="mark that beat with misconception: true, or set meta.misconception_note")

    known_platforms = {k.casefold() for k in platforms.get("platforms", {})}
    for pid in meta.get("platform") or []:
        if str(pid).casefold() not in known_platforms:
            rep.warn("E014", f"no spec on file for platform '{pid}': the common safe box is used, so ask for its safe zones",
                     fix="add the platform to data/platforms.json once its zones and limits are read from its own pages")
    target = float(meta.get("target_seconds") or 0)
    wps = float(meta.get("wps") or prof.get("wps", 2.5))
    rate_source = meta.get("rate_source") or "prior"
    measured = rate_source in ("measured", "engine", "user")
    dur_err = rep.err if measured else rep.warn  # a duration built on an unmeasured prior cannot fail the plan
    # limits are counted in speech units; a script that packs more units into a second (characters, say)
    # gets proportionally more units. Scaled only when the rate was set or measured, never guessed.
    unit_scale = (wps / float(prof.get("wps", wps))) if meta.get("wps") else 1.0
    texts = beatmap_texts(bm)
    tprof = text_profile(texts)
    number_words = [str(w) for w in (meta.get("number_words") or [])]
    not_checked: list[str] = []
    if not number_words:
        not_checked.append("E051 spelled-out numbers: set meta.number_words to this language's number words, or check by eye")
    ids = [b.get("id") for b in beats]
    if len(set(ids)) != len(ids):
        rep.err("E001", "beat ids must be unique and stable (asset filenames key off them)")

    # ---- per-beat -------------------------------------------------------
    secs = []
    total_words = 0
    layer_time: Counter = Counter()
    ai_calls = 0
    lo_b, hi_b = prof.get("beat_seconds", [1.2, 6.0])
    ai_present = False
    for i, b in enumerate(beats):
        bid = b.get("id", i)
        layer = b.get("layer")
        if layer not in LAYERS:
            rep.err("E003", f"layer '{layer}' invalid", bid, "one of " + ", ".join(LAYERS))
            continue
        if layer not in prof.get("layers_allowed", LAYERS):
            rep.warn("E004", f"layer '{layer}' is unusual for format '{fmt_id}'", bid,
                     "check the format file or change the layer")
        if b.get("role") not in ROLES:
            rep.err("E003", f"role '{b.get('role')}' invalid", bid, "one of " + ", ".join(ROLES))
        text = b.get("text", "")
        n = word_count(text)
        total_words += n
        s = _est_beat_seconds(b, wps)
        secs.append(s)
        layer_time[layer] += s
        if not b.get("visual"):
            rep.err("E091", "beat has no `visual` (what the viewer SEES)", bid)
        if not b.get("layer_why"):
            rep.warn("E092", "no `layer_why`: justify the layer in one clause", bid,
                     "e.g. 'numbers must be exact' / 'cannot be filmed'")
        if n == 0 and not b.get("hold_seconds") and not b.get("est_seconds"):
            rep.err("E093", "beat has no spoken text and no hold: it would be a silent gap",
                    bid, "write the narration on this beat or set hold_seconds")
        if s and not (lo_b <= s <= hi_b) and not b.get("allow_long"):
            (dur_err if s > hi_b * 1.6 or s < lo_b * 0.5 else rep.warn)(
                "E011", f"~{s:.1f}s is outside the {fmt_id} beat band {lo_b}-{hi_b}s", bid,
                "split the beat" if s > hi_b else "merge with a neighbour")

        # performance markup / caps leaking into captioned text
        if re.search(r"\[[^\]]{1,24}\]", text):
            rep.err("E052", "bracket tag in `text` (would be captioned)", bid,
                    "move performance markup to `tts_text`")
        caps = [w for w in re.findall(r"\b[A-Z]{4,}\b", text)
                if w not in set(meta.get("acronyms", []))]
        if caps:
            rep.warn("E053", f"ALL-CAPS words in `text`: {caps[:3]}", bid,
                     "emphasis CAPS belong in `tts_text`; list real acronyms in meta.acronyms")
        if number_words and _spelled_number(text, number_words):
            rep.warn("E051", "spelled-out number in `text`; the transcriber returns digits, "
                     "so captions desync", bid, "write digits in `text`, spell them in `tts_text`")

        # numbers belong to the code layer
        kinds = _overlay_kinds(b)
        has_number = bool(NUMBER_RE.search(text)) and not b.get("number_is_decorative")
        declared = any(isinstance(o, dict) and o.get("shows_number") for o in b.get("overlays") or [])
        number_shown = layer == "code" or declared or bool(kinds & NUMBER_OVERLAYS) or layer in (
            "capture", "real") and bool(b.get("shows_source_number"))
        if has_number and not number_shown:
            rep.err("E031", "narration states a number but no code-layer element shows it",
                    bid, "add an overlay (count-up/chart/stat) or move the beat to layer 'code'")

        # AI-layer rules
        if layer in AI_LAYERS:
            ai_present = True
            ai = b.get("ai") or {}
            if not ai.get("prompt"):
                rep.err("E032", "AI beat has no ai.prompt", bid)
            else:
                if TEXT_IN_PROMPT.search(NEGATED.sub(" ", ai["prompt"])) and not ai.get("text_ok"):
                    rep.warn("E030", "AI prompt asks for text/charts/UI; models garble them", bid,
                             "show that element in the code layer instead")
                if RISKY_SCENES.search(ai["prompt"]):
                    anchor = (meta.get("visual_anchor") or "").lower()
                    if len(anchor.split()) < 8:
                        rep.err("E033", "risky scene (flags/crowds/uniforms) with a weak "
                                "visual_anchor: wrong-country symbols will be hallucinated", bid,
                                "write a 15+ word visual_anchor naming the real place, people "
                                "and the ONLY symbols allowed")
            if b.get("on_screen_text") and not b.get("overlays"):
                rep.warn("E030", "on_screen_text on an AI-layer base with no code overlay: render text as an overlay", bid)
            if layer == "ai_video":
                ai_calls += 1
            ai_calls += 1 if layer == "ai_image" else 0
            real = b.get("depicts_real")
            if real in ("person", "event") and not b.get("label_synthetic"):
                if not _stylised(ai, meta):
                    rep.err("E034", f"photoreal AI imagery of a real {real} presented as footage", bid,
                            "use a clearly stylised look, real archival/stock, or label it synthetic")
            elif not b.get("label_synthetic") and not _stylised(ai, meta) and (
                    real == "place" or meta.get("data_origin") == "synthetic"):
                what = "a real place" if real == "place" else "a made-up subject in a synthetic-data story"
                rep.warn("E035", f"photoreal AI imagery of {what} can pass for footage", bid,
                         "use a stylised look, real or stock footage, or label it synthetic")

        # on-screen text discipline
        ost = b.get("on_screen_text") or []
        if isinstance(ost, str):
            ost = [ost]
        words_on_screen = sum(word_count(str(t)) for t in ost)
        if words_on_screen > prof.get("max_on_screen_words", 7) * unit_scale:
            rep.warn("E070", f"{words_on_screen} on-screen words; viewers read OR listen", bid,
                     "cut to <=5 words and let narration carry the sentence")
        zone = b.get("zone")
        if zone and zone in ZONE_RISK:
            rep.warn("E071", f"zone '{zone}' collides with platform UI (caption/CTA/rail)", bid,
                     "keep key graphics in the safe region: " +
                     json.dumps(platforms["safe_zones_1080x1920"]["common_safe_box"]))

        # claims
        refs = b.get("claim_refs") or []
        if has_number and not refs and not b.get("claim_exempt"):
            rep.warn("E050", "number without claim_refs (no source on file)", bid,
                     "add a claims[] entry with source + date")
        for r in refs:
            if r not in claims:
                rep.err("E050", f"claim_ref '{r}' not defined in claims[]", bid)
        if refs and not b.get("number_is_decorative") and not b.get("claim_exempt"):
            known_digits = {d for r in refs if r in claims
                            for d, _ in _number_tokens(" ".join(str(claims[r].get(k, "")) for k in ("text", "method", "value")))}
            for digits, suffixed in _number_tokens(text):
                if not (digits in known_digits or (suffixed and any(k.startswith(digits) for k in known_digits))):
                    rep.warn("E054", f"the number {digits} in `text` does not appear in the claims this beat cites "
                             f"({', '.join(refs)}; numbers found there: {', '.join(sorted(known_digits)) or 'none'}): a wrong figure would pass unnoticed", bid,
                             "fix the figure, fix the claim, or cite the claim that holds it")
                    break
        nr = data("formats").get("number_rules", {})
        if nr and not b.get("number_is_decorative"):
            raw = re.findall(r"[$\u20ac\u00a3]?\s?\d[\d,.]*\s?(?:%|[kKmMbB]\b|x\b)?", text)
            rng = nr.get("year_like_range", [1000, 2999])
            stat = {d for d, _ in _number_tokens(text) if not _is_year(raw, d, rng)}
            if len(stat) > nr.get("max_distinct_per_beat", 3):
                rep.warn("E055", f"{len(stat)} distinct figures in one beat (limit {nr.get('max_distinct_per_beat', 3)}): "
                         "a viewer holds a few at a time", bid, "split the beat or keep the figures that carry the point")

    # ---- global duration ------------------------------------------------
    est = sum(secs)
    if target:
        ratio = est / target
        if ratio > 1.35 or ratio < 0.65:
            dur_err("E010", f"{total_words} speech units ~ {est:.0f}s vs target {target:.0f}s "
                    f"({ratio:.2f}x)", fix=f"speech units are the only length knob: aim ~{round(target*wps)} units")
        elif ratio > 1.15 or ratio < 0.85:
            rep.warn("E010", f"~{est:.0f}s vs target {target:.0f}s ({ratio:.2f}x)",
                     fix=f"aim ~{round(target*wps)} speech units")
    if not measured and total_words:
        rep.warn("E013", f"duration is estimated from a format prior of {wps} speech units per second "
                 f"(counted in {tprof['unit_mode']}); real speech varies with the language, the voice and the text",
                 fix="render a short sample in the chosen voice, then: python3 scripts/speech_rate.py measure "
                     "--audio sample.wav --beatmap beatmap.json --write")
    lmin, lmax = prof.get("length_seconds", [15, 90])
    if target and not (lmin <= target <= lmax):
        rep.warn("E012", f"target {target:.0f}s outside the {fmt_id} band {lmin}-{lmax}s")

    # ---- structure ------------------------------------------------------
    first, last = beats[0], beats[-1]
    if first.get("role") not in OPENING_ROLES:
        rep.err("E020", "beat 0 must be role 'hook' (or 'cold-open' for a story)")
    hw = word_count(first.get("text", ""))
    hmax = prof.get("hook_max_words", 12) * unit_scale
    if hw > hmax * 1.6:
        rep.err("E020", f"hook is {hw} words; the scroll decision happens in ~2-3 s", first.get("id"),
                f"tighten to <= {hmax:.0f} speech units")
    elif hw > hmax:
        rep.warn("E020", f"hook is {hw} words (format band <= {hmax})", first.get("id"))
    if not first.get("mute_proof"):
        rep.warn("E021", "hook not marked mute_proof: it must work with sound off",
                 first.get("id"), "give the hook a visual device + <=5 on-screen words")
    if last.get("role") not in CLOSING_ROLES:
        rep.err("E022", "last beat must be role 'payoff', 'loop', 'tag' or 'cliffhanger' (close the hook's loop)",
                last.get("id"))
    roles = [b.get("role") for b in beats]
    if not any(r in CLOSING_ROLES for r in roles):
        rep.err("E022", "no payoff, loop, tag or cliffhanger beat anywhere")

    # ---- narrative and series ---------------------------------------------
    cast = meta.get("cast")
    ser = meta.get("series")
    if ser is not None and not (isinstance(ser, dict) and ser.get("id") and isinstance(ser.get("episode"), int)):
        rep.err("E103", "meta.series must be {id, episode} with an integer episode",
                fix="series.py episode add writes it for you")
    for b in beats:
        who = b.get("character")
        if who and cast is not None and who not in cast:
            rep.err("E100", f"character '{who}' is not in meta.cast", b.get("id"), "add it to the series cast or fix the id")
        elif who and cast is None:
            rep.warn("E101", "a beat names a character but meta.cast is not set", b.get("id"),
                     "meta.cast = the character ids in this episode")
        cb = b.get("callback_to")
        if cb is not None and not (isinstance(cb, dict) and isinstance(cb.get("episode"), int)):
            rep.warn("E102", "callback_to must be {episode: int, beat: id}", b.get("id"))
    pmax = prof.get("punchline_max_seconds")
    if "punchline" in roles or "setup" in roles:
        if "setup" in roles and "punchline" in roles and roles.index("setup") > roles.index("punchline"):
            rep.warn("E104", "a setup comes after the first punchline: the joke has to be planted before it pays off")
        if pmax:
            for b in beats:
                spoken = _est_beat_seconds({**b, "hold_seconds": 0}, wps)
                if b.get("role") == "punchline" and spoken > pmax:
                    rep.warn("E105", f"the punchline takes ~{spoken:.1f}s to say (house limit {pmax}s): "
                             "a long punchline is explained, not landed", b.get("id"),
                             "cut distracting specifics, put the key word last, leave the gap in hold_seconds")
    if (prof.get("needs_punchline") or intent == "sketch") and "punchline" not in roles:
        rep.warn("E106", "a comic piece has no punchline beat" + (f" ({fmt_id} format)" if prof.get("needs_punchline") else " (intent sketch)"),
                 fix="mark the beat where the joke lands role 'punchline'")
    if intent == "sketch" or "punchline" in roles:
        for b in beats:
            if b.get("role") == "punchline" and not b.get("punchline_options") and not b.get("punchline_approved"):
                rep.warn("E107", "a punchline with no recorded options and no approval: the human picks or rewrites every punchline "
                         "(the punchline pass)", b.get("id"),
                         "list three options in punchline_options and set punchline_approved when the user chose")

    # ---- variety / mix --------------------------------------------------
    run_len = 1
    for i in range(1, len(beats)):
        sig = (beats[i].get("layer"), beats[i].get("device"))
        prev = (beats[i - 1].get("layer"), beats[i - 1].get("device"))
        run_len = run_len + 1 if sig == prev else 1
        if run_len == 3 and not prof.get("allow_repeat_treatment"):
            rep.warn("E040", "3 consecutive beats with the same layer+device",
                     beats[i].get("id"), "vary the device or layer (variety law)")
    tot = sum(layer_time.values()) or 1.0
    mix = {k: round(v / tot, 3) for k, v in layer_time.items()}
    for layer, (mn, mx) in (prof.get("mix") or {}).items():
        share = mix.get(layer, 0.0)
        if share < mn - 1e-9:
            rep.warn("E041", f"{layer} share {share:.0%} < format minimum {mn:.0%}",
                     fix=f"'{fmt_id}' relies on the {layer} layer")
        if share > mx + 1e-9:
            rep.warn("E041", f"{layer} share {share:.0%} > format maximum {mx:.0%}",
                     fix=f"too much {layer} for '{fmt_id}'")

    # ---- claims ledger --------------------------------------------------
    inferred = 0
    for cid, c in claims.items():
        conf = c.get("confidence")
        if conf not in ("primary", "secondary", "inference", "computed", "user"):
            rep.err("E050", f"claim {cid}: confidence must be primary|secondary|inference|computed|user "
                            "(user = text the user supplied, cited as such, no URL needed)")
        if conf == "computed":
            if not (c.get("method") or c.get("source")):
                rep.err("E050", f"claim {cid} is 'computed' but states no method/assumptions",
                        fix="add method: the formula and every assumption (rate, period, fees)")
        elif conf not in ("inference", "user") and not c.get("source"):
            rep.err("E050", f"claim {cid} has no source", fix="add a real URL, mark inference, or confidence \"user\" for text the user supplied")
        if c.get("verified") is False or conf == "user":
            rep.warn("E059", f"claim {cid} is {'supplied by the user' if conf == 'user' else 'cited but not verified'}: "
                     "check it against a source before publishing when one is reachable", fix="open the source and set verified: true, or leave the note in meta.notes")
        if conf == "inference":
            inferred += 1
        if conf in ("primary", "secondary") and not c.get("date"):
            rep.warn("E050", f"claim {cid} has no source date (facts go stale)")
    if claims and inferred / len(claims) > 0.3:
        rep.warn("E050", f"{inferred}/{len(claims)} claims are inference: hedge them in the script")

    # ---- anchor / disclosure / language / budget ------------------------
    if ai_present and len((meta.get("visual_anchor") or "").split()) < 5:
        rep.err("E032", "meta.visual_anchor missing (required whenever an AI layer is used)",
                fix="one line: the real subject, place, and the ONLY symbols allowed")
    if ai_present and "disclose" not in meta:
        rep.warn("E081", "AI layers present but meta.disclose not set",
                 fix="set meta.disclose true/false and say why (see references/08-governance.md)")
    script_fonts = meta.get("script_fonts") or ({"rtl": meta["rtl_font"]} if meta.get("rtl_font") else {})
    if tprof["direction"] in ("rtl", "mixed") and not script_fonts:
        rep.warn("E080", f"the text is {tprof['direction']} ({tprof['dominant_script']}): set meta.script_fonts, "
                 "mirror layouts and isolate opposite-direction runs (references/12-localization.md)",
                 fix="python3 scripts/textscript.py beatmap.json lists fonts that cover every character")
    elif needs_font_check(texts) and not script_fonts and not meta.get("fonts_checked"):
        rep.warn("E084", "the text has letters outside Latin: the identity fonts cannot be assumed to cover them",
                 fix="python3 scripts/textscript.py beatmap.json lists covering fonts; record the choice in meta.script_fonts")
    if any(b.get("layer") == "host" for b in beats):
        host = meta.get("host") or {}
        src = host.get("source")
        if src not in ("generated", "real_person", "twin"):
            rep.warn("E082", "a host beat exists but meta.host.source is not set",
                     fix="meta.host = {source: generated|real_person|twin, consent: ...}")
        elif src in ("real_person", "twin") and not host.get("consent"):
            rep.err("E082", "a real person or digital twin as host needs meta.host.consent",
                    fix="state that the person is the user or has consented; refuse celebrity or third-party photos")
        regulated = meta.get("regulated_topic")
        by_intent = bool(intents.get(intent, {}).get("regulated"))
        if src == "generated":
            if "regulated_topic" not in meta and not by_intent:
                rep.warn("E085", "an AI host is set but meta.regulated_topic is not: judge whether the topic is health, "
                         "legal, finance or politics, in whatever language the video is in",
                         fix='meta.regulated_topic: "health" | "legal" | "finance" | "politics" | "none"')
            elif by_intent or str(regulated or "none").lower() not in ("none", "false", ""):
                rep.warn("E083", "an AI-generated persona giving advice on a regulated topic is not monetisable on YouTube",
                         fix="offer the user the alternatives in references/08-governance.md (voice-over, a real presenter, "
                             "or a labelled persona with a not-advice line) and record the choice in meta.notes")
    computed = any(c.get("confidence") == "computed" for c in claims.values())
    origin = meta.get("data_origin")
    if (computed or origin) and origin not in ("real", "synthetic", "mixed", "modelled"):
        rep.warn("E056", "claims are computed from data but meta.data_origin is not set",
                 fix='meta.data_origin: "real" (a dataset) | "synthetic" (made up) | "mixed" | "modelled" (computed from stated assumptions)')
    shows_figures = bool(claims) or any(NUMBER_RE.search(b.get("text", "")) for b in beats)
    if origin in ("synthetic", "mixed") and shows_figures:
        labelled = any(str(ov.get("kind", "")).lower() in ("synthetic-label", "disclaimer")
                       for b in beats for ov in (b.get("overlays") or []) if isinstance(ov, dict))
        if not labelled:
            (rep.err if origin == "synthetic" else rep.warn)(
                "E057", f"the data is {origin} but no beat carries a visible label (overlay kind 'synthetic-label' or 'disclaimer')",
                fix="add the label on the hook beat so the viewer sees it before any figure")
        if origin == "synthetic" and any(c.get("confidence") in ("primary", "secondary") for c in claims.values()):
            rep.warn("E058", "synthetic data with claims marked primary or secondary: a made-up figure has no source",
                     fix="mark those claims 'computed' and state the generation method")
    cost = _cost_block(rep, bm, beats, meta, pricebook, require_pricebook, bakeoff)
    return _finish(rep, {
        "format": fmt_id, "tier": tier, "beats": len(beats), "words": total_words,
        "est_seconds": round(est, 1), "target_seconds": target, "wps": wps,
        "layer_mix_by_time": mix, "ai_calls": ai_calls,
        "cost_usd_low": cost["low"], "cost_usd_high": cost["high"], "cost": cost,
        "rate_source": rate_source, "unit_mode": tprof["unit_mode"], "direction": tprof["direction"],
        "dominant_script": tprof["dominant_script"], "not_checked": not_checked,
    }, bm)


def _cost_block(rep: Report, bm: dict, beats: list, meta: dict, pricebook: dict | None,
                require: bool, bakeoff: int = 0) -> dict:
    """Price the plan from the episode pricebook, or say the cost is unknown. Never guesses."""
    paid = [b for b in beats if b.get("layer") in PAID_LAYERS]
    out = {"known": False, "low": None, "high": None, "missing": [], "questions": 0, "source": None, "note": None}
    if pricebook is None:
        if paid or require:
            msg = ("cost unknown: no pricebook for this episode. Run the cost scout "
                   "(references/14-cost-scout.md), then lint with --pricebook")
            (rep.err if require else rep.warn)(
                "E061", msg, fix="cost_plan.py init, then fill it from live sources")
        else:
            out.update(known=True, low=0.0, high=0.0, source="no paid layers",
                       note="no generation layers; voice, music and transcription routes are not priced")
        return out
    plan = compute_plan(bm, pricebook, bakeoff)
    out.update(known=plan["complete"], low=plan["total_low"], high=plan["total_high"],
               missing=[m["capability"] for m in plan["missing"]], questions=len(plan["questions"]),
               source="pricebook")
    for m in plan["missing"]:
        blocking = m["capability"] in PAID_LAYERS or require
        what = m.get("problem") or f"{m['needed']} {m['unit']} needed"
        (rep.err if blocking else rep.warn)(
            "E062", f"no usable price on file for {m['capability']} ({what})",
            fix="the cost scout adds it from a live source or the user supplies it; "
                "a local engine is a price of 0 with source type local")
    if any(f.startswith("ILLUSTRATIVE") for ln in plan["lines"] for f in ln["flags"]):
        rep.warn("E063", "an ILLUSTRATIVE price is in use: this is a rehearsal, not a quote",
                 fix="replace it with a live price")
    stale = [f"{ln['capability']}: {f}" for ln in plan["lines"] for f in ln["flags"]
             if f.startswith(("stale", "expired", "price changes", "no fetched_at"))]
    if stale:
        rep.warn("E064", "price freshness: " + "; ".join(stale),
                 fix="`cost_plan.py check`, then refresh the flagged entries")
    if plan["total_high"] is None and plan["lines"]:
        rep.warn("E065", "no retry assumptions set: the high estimate is unknown, so the cap cannot "
                 "cover rejected generations",
                 fix="cost_plan.py set --retries ... --retries-basis ... (ledger history or the user)")
    budget = meta.get("budget_usd")
    if budget is not None and out["low"] is not None:
        b = float(budget)
        if out["low"] > b:
            rep.err("E060", f"estimated cost {out['low']:.2f} (low) exceeds budget {b}",
                    fix="cut AI clips or host seconds, or raise the cap with the user")
        elif out["high"] is not None and out["high"] > b:
            rep.err("E060", f"estimated cost {out['low']:.2f}-{out['high']:.2f} exceeds budget {b}",
                    fix="cut AI clips or host seconds, or raise the cap with the user")
        elif out["high"] is not None and out["high"] > 0.85 * b:
            rep.warn("E060", f"high estimate {out['high']:.2f} is over 85% of budget {b}")
    return out


def _fmt_cost(c: dict) -> str:
    if c.get("note"):
        return c["note"]
    if c["low"] is None:
        return "UNKNOWN (no pricebook)"
    hi = "?" if c["high"] is None else f"{c['high']:.2f}"
    miss = "" if c["known"] else " (incomplete: missing " + ", ".join(c["missing"]) + ")"
    return f"{c['low']:.2f}-{hi}{miss}"


def _finish(rep: Report, stats: dict, bm: dict) -> dict:
    return {"ok": not rep.errors, "errors": rep.errors, "warnings": rep.warnings, "stats": stats}


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"strict", "quiet", "require-pricebook"})
    if not pos:
        eprint(__doc__)
        return 2
    try:
        bm = load_json(pos[0])
    except (OSError, json.JSONDecodeError) as exc:
        eprint(f"cannot read {pos[0]}: {exc}")
        return 2
    pb = None
    if opt.get("pricebook"):
        try:
            pb = load_pricebook(opt["pricebook"])
        except (OSError, json.JSONDecodeError) as exc:
            eprint(f"cannot read pricebook {opt['pricebook']}: {exc}")
            return 2
    rep = lint(bm, pb, bool(opt.get("require-pricebook")), int(opt.get("bakeoff", 0) or 0))
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    if not opt.get("quiet"):
        s = rep["stats"]
        if s:
            mix = ", ".join(f"{k} {v:.0%}" for k, v in sorted(s["layer_mix_by_time"].items()))
            eprint(f"[lint] {s['format']} {s['tier']} | {s['beats']} beats | {s['words']} words "
                   f"~ {s['est_seconds']}s (target {s['target_seconds']}s) | mix: {mix} | "
                   f"cost {_fmt_cost(s['cost'])}")
        for e in rep["errors"]:
            eprint(f"  ERROR {e['code']} beat={e['beat']}: {e['msg']}" +
                   (f"\n        fix: {e['fix']}" if e["fix"] else ""))
        for w in rep["warnings"]:
            eprint(f"  warn  {w['code']} beat={w['beat']}: {w['msg']}" +
                   (f"\n        fix: {w['fix']}" if w["fix"] else ""))
        eprint("[lint] " + ("PASS" if rep["ok"] and not (opt.get("strict") and rep["warnings"])
                            else "FAIL"))
    if rep["errors"] or (opt.get("strict") and rep["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
