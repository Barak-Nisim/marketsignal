import datetime as dt

from marketsignal.models import Snapshot
from marketsignal.outcomes import compute_outcomes


def _snapshot(as_of: str, price: float | None, overall_score: float | None = 2.5) -> Snapshot:
    return Snapshot(
        ticker="AAPL", as_of=as_of, overall_score=overall_score, category_scores={}, price=price
    )


def test_no_outcomes_without_a_current_price():
    history = [_snapshot("2026-01-01", 100.0)]

    assert compute_outcomes(history, current_price=None) == []


def test_no_outcomes_for_a_snapshot_missing_a_price():
    history = [_snapshot("2026-01-01", None)]
    today = dt.date(2026, 3, 1)

    assert compute_outcomes(history, current_price=150.0, today=today) == []


def test_snapshot_less_than_a_week_old_is_excluded():
    history = [_snapshot("2026-02-28", 100.0)]
    today = dt.date(2026, 3, 1)  # 1 day elapsed

    assert compute_outcomes(history, current_price=110.0, today=today) == []


def test_snapshot_exactly_one_week_old_is_included():
    history = [_snapshot("2026-02-22", 100.0)]
    today = dt.date(2026, 3, 1)  # 7 days elapsed

    outcomes = compute_outcomes(history, current_price=110.0, today=today)

    assert len(outcomes) == 1
    assert outcomes[0].horizon_label == "1 week+"
    assert outcomes[0].days_elapsed == 7


def test_pct_change_is_computed_correctly():
    history = [_snapshot("2026-01-01", 100.0)]
    today = dt.date(2026, 2, 1)  # 31 days elapsed

    outcomes = compute_outcomes(history, current_price=120.0, today=today)

    assert outcomes[0].pct_change == 0.2
    assert outcomes[0].price_then == 100.0
    assert outcomes[0].price_now == 120.0
    assert outcomes[0].horizon_label == "1 month+"


def test_horizon_labels_scale_with_elapsed_time():
    history = [_snapshot("2025-01-01", 100.0)]
    today = dt.date(2026, 1, 1)  # 365 days elapsed

    outcomes = compute_outcomes(history, current_price=110.0, today=today)

    assert outcomes[0].horizon_label == "3 months+"


def test_tier_at_signal_reflects_the_score_at_that_time():
    from marketsignal.scoring import tier_for_score

    history = [_snapshot("2026-01-01", 100.0, overall_score=3.5)]
    today = dt.date(2026, 2, 1)

    outcomes = compute_outcomes(history, current_price=110.0, today=today)

    assert outcomes[0].tier_at_signal == tier_for_score(3.5)


def test_tier_at_signal_is_na_when_score_was_missing():
    history = [_snapshot("2026-01-01", 100.0, overall_score=None)]
    today = dt.date(2026, 2, 1)

    outcomes = compute_outcomes(history, current_price=110.0, today=today)

    assert outcomes[0].tier_at_signal == "n/a"


def test_results_are_capped_to_the_limit_most_recent():
    history = [_snapshot(f"2026-01-{day:02d}", 100.0) for day in range(1, 10)]
    today = dt.date(2026, 3, 1)

    outcomes = compute_outcomes(history, current_price=110.0, today=today, limit=3)

    assert len(outcomes) == 3
    assert outcomes[-1].as_of == "2026-01-09"  # most recent snapshot kept last


def test_snapshots_missing_as_of_are_skipped():
    history = [_snapshot("", 100.0)]
    today = dt.date(2026, 3, 1)

    assert compute_outcomes(history, current_price=110.0, today=today) == []
