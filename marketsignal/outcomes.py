"""Tracks how past MarketSignal signals actually performed.

Compares each history snapshot's recorded price at signal time against the
ticker's current price from this run. No new network calls -- reuses the
current_price already fetched by fetch_raw_financials for this run, so
"1 week / 1 month / 3 months" are labeled by how much time has actually
elapsed since the snapshot (a snapshot 40 days old is labeled "1 month+",
not resolved against the exact price on day 30), which is an honest,
simple approximation rather than a second historical-price fetch per
snapshot.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from marketsignal.models import Snapshot
from marketsignal.scoring import tier_for_score

# (minimum days elapsed, label), checked in order -- first match wins
HORIZONS = (
    (90, "3 months+"),
    (30, "1 month+"),
    (7, "1 week+"),
)

MIN_DAYS_TO_SHOW = 7


@dataclass(frozen=True)
class Outcome:
    as_of: str
    overall_score: float | None
    tier_at_signal: str
    price_then: float
    price_now: float
    pct_change: float
    days_elapsed: int
    horizon_label: str


def _horizon_label(days_elapsed: int) -> str:
    for threshold, label in HORIZONS:
        if days_elapsed >= threshold:
            return label
    return "1 week+"


def compute_outcomes(
    history: list[Snapshot],
    current_price: float | None,
    today: dt.date | None = None,
    limit: int = 5,
) -> list[Outcome]:
    if not current_price:
        return []
    today = today or dt.date.today()

    outcomes = []
    for snap in history:
        if not snap.price or not snap.as_of:
            continue
        try:
            as_of_date = dt.date.fromisoformat(snap.as_of)
        except ValueError:
            continue

        days_elapsed = (today - as_of_date).days
        if days_elapsed < MIN_DAYS_TO_SHOW:
            continue

        outcomes.append(
            Outcome(
                as_of=snap.as_of,
                overall_score=snap.overall_score,
                tier_at_signal=(
                    tier_for_score(snap.overall_score) if snap.overall_score is not None else "n/a"
                ),
                price_then=snap.price,
                price_now=current_price,
                pct_change=(current_price - snap.price) / snap.price,
                days_elapsed=days_elapsed,
                horizon_label=_horizon_label(days_elapsed),
            )
        )

    return outcomes[-limit:]
