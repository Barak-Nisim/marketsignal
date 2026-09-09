"""Caches AI narratives so re-running research for the same ticker again
later the same day, against effectively unchanged inputs, doesn't
re-spend tokens on a response that would come back identical.

Keyed by ticker plus a hash of everything that actually feeds the
narrative call (the score result's `as_of`/scores and the prior
thesis-history context) -- there's no separate TTL to reason about, since
any real change to those inputs is itself a cache miss.

Lives at ~/.marketsignal/narrative_cache/ by default, outside the repo,
overridable via MARKETSIGNAL_NARRATIVE_CACHE_DIR for test isolation
(mirrors history.py/favorites.py's storage pattern).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from marketsignal.models import ScoreResult


def _cache_dir() -> Path:
    override = os.environ.get("MARKETSIGNAL_NARRATIVE_CACHE_DIR")
    base = Path(override) if override else Path.home() / ".marketsignal" / "narrative_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _cache_path(ticker: str) -> Path:
    return _cache_dir() / f"{ticker.upper()}.json"


def _input_key(
    result: ScoreResult,
    previous_invalidation_conditions: list[str] | None,
    previous_claims: list[dict] | None,
) -> str:
    # Deliberately excludes `what_changed`: within a same-day repeat run it's
    # derived from the same history and comes out identical anyway, and a
    # later call on a day the score data has moved will already miss here on
    # `as_of`/`overall_score`/`category_scores` before that would matter.
    payload = {
        "as_of": result.financials.as_of,
        "overall_score": result.overall_score,
        "tier": result.tier,
        "category_scores": {c.id: c.score for c in result.category_scores},
        "previous_invalidation_conditions": previous_invalidation_conditions or [],
        "previous_claims": previous_claims or [],
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get_cached_narrative(
    result: ScoreResult,
    previous_invalidation_conditions: list[str] | None,
    previous_claims: list[dict] | None,
) -> dict | None:
    path = _cache_path(result.financials.ticker)
    if not path.exists():
        return None
    cached = json.loads(path.read_text(encoding="utf-8"))
    if cached.get("input_key") != _input_key(
        result, previous_invalidation_conditions, previous_claims
    ):
        return None
    return cached["narrative"]


def store_narrative(
    result: ScoreResult,
    previous_invalidation_conditions: list[str] | None,
    previous_claims: list[dict] | None,
    narrative: dict,
) -> None:
    payload = {
        "input_key": _input_key(result, previous_invalidation_conditions, previous_claims),
        "narrative": narrative,
    }
    _cache_path(result.financials.ticker).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
