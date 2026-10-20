"""ui_labels.py - every interface string the board and the animatic print, in one place.

The skill talks to the user in the language they write in, so these strings are overridable:
translate the values into that language and pass the file with `--labels labels.json` to
storyboard.py and animatic.py. Keys you leave out keep the English default below. Scripts'
messages to the agent (lint codes, errors) stay as they are: they are working notes, not the
user's interface.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {
    "lint_pass": "LINT PASS", "lint_fail": "LINT FAIL", "errors": "errors", "warnings": "warnings",
    "cost": "cost", "sees": "Sees", "why": "Why", "device": "device", "overlays": "overlays",
    "on_screen": "on-screen", "units": "speech units", "beat": "beat", "budget": "budget",
    "not_set": "not set", "unknown": "unknown", "claims": "Claims and sources", "claim": "claim",
    "confidence": "confidence", "source": "source", "date": "date", "method": "method", "id": "id",
    "cost_card": "Cost card", "low": "Low", "high": "high", "incomplete": "INCOMPLETE",
    "incomplete_note": "only what has a price so far; this is NOT the cost of the plan",
    "missing_price": "no price", "what": "what", "quantity": "quantity", "route": "route",
    "per_unit": "per unit", "options": "Options", "questions": "Questions for you",
    "notes": "Notes", "ai_label_on": "AI label: on", "ai_label_off": "AI label: off",
    "retries_assumed": "retries assumed", "cost_unknown_no_pricebook": "Cost: unknown. No pricebook has been built for this episode.",
    "sees_caps": "SEES", "text_caps": "TEXT", "punchline_options": "Punchline options", "chosen": "chosen",
    "role_hook": "hook", "role_context": "context", "role_build": "build", "role_turn": "turn", "role_reveal": "reveal",
    "role_payoff": "payoff", "role_loop": "loop", "role_cold-open": "cold open", "role_title": "title", "role_recap": "recap",
    "role_setup": "setup", "role_escalate": "escalate", "role_punchline": "punchline", "role_tag": "tag",
    "role_cliffhanger": "cliffhanger",
    "layer_code": "CODE", "layer_ai_image": "AI IMAGE", "layer_ai_video": "AI VIDEO", "layer_stock": "STOCK",
    "layer_capture": "CAPTURE", "layer_host": "HOST", "layer_real": "REAL FOOTAGE",
}


def load(path: str | None = None) -> dict:
    labels = dict(DEFAULTS)
    if path:
        extra = json.loads(Path(path).read_text(encoding="utf-8"))
        unknown = sorted(set(extra) - set(DEFAULTS))
        if unknown:
            raise KeyError(f"unknown label keys: {unknown}")
        labels.update({k: str(v) for k, v in extra.items()})
    return labels
