"""Persists AI-generated theses between runs and computes what changed in
the narrative itself, not just the score.

Entries live at ~/.marketsignal/thesis_history/<TICKER>.json by default (an
append-only JSON array of {"as_of": ..., "narrative": {...}}), outside the
repo entirely -- same reasoning as history.py. The location is overridable
via MARKETSIGNAL_THESIS_HISTORY_DIR, a separate env var and a separate
default subdirectory from MARKETSIGNAL_HISTORY_DIR so the two stores never
collide in tests or in production.

The diff in build_thesis_delta is a deterministic set comparison over the
narrator's structured fields (catalysts, risk factors, invalidation
conditions, confidence) -- no AI call. Bull/bear case prose isn't diffed;
comparing free text for meaning would need its own model call, which is a
larger, separate bet (see docs/enhancements.md).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from marketsignal.models import ThesisDelta


def _thesis_history_dir() -> Path:
    override = os.environ.get("MARKETSIGNAL_THESIS_HISTORY_DIR")
    base = Path(override) if override else Path.home() / ".marketsignal" / "thesis_history"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _thesis_path(ticker: str) -> Path:
    return _thesis_history_dir() / f"{ticker.upper()}.json"


def load_thesis_history(ticker: str) -> list[dict]:
    path = _thesis_path(ticker)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def previous_invalidation_conditions(ticker: str) -> list[str]:
    """The most recently recorded thesis's what_would_change_my_mind list for
    this ticker, or [] if there's no prior thesis. Fetched before generating
    a new narrative so the AI call can check whether those conditions have
    since come true against the current data, in the same request -- no
    separate monitoring process, no extra API call."""
    history = load_thesis_history(ticker)
    if not history:
        return []
    return history[-1]["narrative"].get("what_would_change_my_mind", [])


def previous_claims(ticker: str) -> list[dict]:
    """The most recently recorded thesis's catalysts and risk factors for
    this ticker, flattened into {claim, based_on, source} dicts, or [] if
    there's no prior thesis. Fetched before generating a new narrative, same
    reasoning as previous_invalidation_conditions -- checked in the same AI
    call, no separate process."""
    history = load_thesis_history(ticker)
    if not history:
        return []
    narrative = history[-1]["narrative"]
    claims = [
        {"claim": c["catalyst"], "based_on": c["based_on"], "source": "catalyst"}
        for c in narrative.get("catalysts", [])
    ]
    claims += [
        {"claim": r["factor"], "based_on": r["based_on"], "source": "risk_factor"}
        for r in narrative.get("risk_factors", [])
    ]
    return claims


def _save_thesis_history(ticker: str, entries: list[dict]) -> None:
    path = _thesis_path(ticker)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def build_thesis_delta(previous: dict, current: dict) -> ThesisDelta:
    previous_narrative = previous["narrative"]

    def _texts(narrative: dict, key: str, field: str) -> set[str]:
        return {item[field] for item in narrative.get(key, [])}

    previous_catalysts = _texts(previous_narrative, "catalysts", "catalyst")
    current_catalysts = _texts(current, "catalysts", "catalyst")
    previous_risks = _texts(previous_narrative, "risk_factors", "factor")
    current_risks = _texts(current, "risk_factors", "factor")
    previous_invalidation = set(previous_narrative.get("what_would_change_my_mind", []))
    current_invalidation = set(current.get("what_would_change_my_mind", []))

    return ThesisDelta(
        previous_as_of=previous["as_of"],
        confidence_before=previous_narrative.get("confidence", "n/a"),
        confidence_after=current.get("confidence", "n/a"),
        catalysts_added=tuple(current_catalysts - previous_catalysts),
        catalysts_removed=tuple(previous_catalysts - current_catalysts),
        risks_added=tuple(current_risks - previous_risks),
        risks_removed=tuple(previous_risks - current_risks),
        invalidation_added=tuple(current_invalidation - previous_invalidation),
        invalidation_removed=tuple(previous_invalidation - current_invalidation),
    )


def record_thesis_and_diff(ticker: str, as_of: str, narrative: dict) -> ThesisDelta | None:
    """Appends the current thesis to that ticker's history and returns a
    diff against the immediately prior recorded thesis, or None if this is
    the first thesis ever recorded for this ticker."""
    history = load_thesis_history(ticker)

    delta = build_thesis_delta(history[-1], narrative) if history else None

    history.append({"as_of": as_of, "narrative": narrative})
    _save_thesis_history(ticker, history)

    return delta
