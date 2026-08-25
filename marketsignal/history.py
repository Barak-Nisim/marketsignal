"""Persists research snapshots between runs and computes what changed.

Snapshots live at ~/.marketsignal/history/<TICKER>.json by default (an
append-only JSON array, one entry per run) -- outside the repo entirely,
since this is real personal research data, not sample data (see models.py
and the repo's .gitignore for why). The location is overridable via
MARKETSIGNAL_HISTORY_DIR, which the test suite uses so tests never touch a
real user's home directory.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from marketsignal.models import ScoreResult, Snapshot, WhatChanged


def _history_dir() -> Path:
    override = os.environ.get("MARKETSIGNAL_HISTORY_DIR")
    base = Path(override) if override else Path.home() / ".marketsignal" / "history"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _history_path(ticker: str) -> Path:
    return _history_dir() / f"{ticker.upper()}.json"


def _snapshot_from_result(result: ScoreResult) -> Snapshot:
    return Snapshot(
        ticker=result.financials.ticker,
        as_of=result.financials.as_of,
        overall_score=result.overall_score,
        category_scores={c.id: c.score for c in result.category_scores},
    )


def load_history(ticker: str) -> list[Snapshot]:
    path = _history_path(ticker)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Snapshot(**entry) for entry in raw]


def _save_history(ticker: str, snapshots: list[Snapshot]) -> None:
    path = _history_path(ticker)
    path.write_text(json.dumps([asdict(s) for s in snapshots], indent=2), encoding="utf-8")


def compute_what_changed(previous: Snapshot, current: Snapshot) -> WhatChanged:
    overall_delta = (
        current.overall_score - previous.overall_score
        if current.overall_score is not None and previous.overall_score is not None
        else None
    )

    category_deltas = {}
    for category_id, current_score in current.category_scores.items():
        previous_score = previous.category_scores.get(category_id)
        if current_score is not None and previous_score is not None:
            category_deltas[category_id] = current_score - previous_score
        else:
            category_deltas[category_id] = None

    return WhatChanged(
        previous_as_of=previous.as_of,
        overall_score_delta=overall_delta,
        category_deltas=category_deltas,
    )


def list_recent_tickers(limit: int = 6) -> list[Snapshot]:
    """Returns the latest snapshot for each researched ticker, most
    recently modified first. Used for the "recently researched" list on
    the web UI's /app page."""
    paths = sorted(
        _history_dir().glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    recent = []
    for path in paths[:limit]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw:
            recent.append(Snapshot(**raw[-1]))
    return recent


def record_and_diff(result: ScoreResult) -> WhatChanged | None:
    """Appends the current result to that ticker's history and returns a
    diff against the immediately prior run, or None if this is the first
    recorded run for this ticker."""
    ticker = result.financials.ticker
    history = load_history(ticker)
    current_snapshot = _snapshot_from_result(result)

    what_changed = compute_what_changed(history[-1], current_snapshot) if history else None

    history.append(current_snapshot)
    _save_history(ticker, history)

    return what_changed
