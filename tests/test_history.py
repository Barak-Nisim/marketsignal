from marketsignal.history import compute_what_changed, load_history, record_and_diff
from marketsignal.models import (
    CategoryScore,
    RawFinancials,
    ScoreResult,
    Snapshot,
)


def _make_result(ticker: str, as_of: str, overall: float, valuation: float, growth: float | None):
    financials = RawFinancials(
        ticker=ticker, company_name="Test Co", sector="Technology", industry="Software", as_of=as_of
    )
    categories = (
        CategoryScore("valuation", "Valuation", valuation, ()),
        CategoryScore("growth", "Growth", growth, ()),
    )
    return ScoreResult(
        financials=financials, overall_score=overall, tier="Average", category_scores=categories
    )


def test_compute_what_changed_reports_deltas():
    previous = Snapshot(
        ticker="TEST", as_of="2026-01-01", overall_score=2.0,
        category_scores={"valuation": 2.0, "growth": 1.0},
    )
    current = Snapshot(
        ticker="TEST", as_of="2026-02-01", overall_score=2.5,
        category_scores={"valuation": 3.0, "growth": 1.0},
    )

    changed = compute_what_changed(previous, current)

    assert changed.previous_as_of == "2026-01-01"
    assert changed.overall_score_delta == 0.5
    assert changed.category_deltas["valuation"] == 1.0
    assert changed.category_deltas["growth"] == 0.0


def test_compute_what_changed_handles_missing_scores():
    previous = Snapshot(
        ticker="TEST", as_of="2026-01-01", overall_score=None, category_scores={"growth": None}
    )
    current = Snapshot(
        ticker="TEST", as_of="2026-02-01", overall_score=2.0, category_scores={"growth": 3.0}
    )

    changed = compute_what_changed(previous, current)

    assert changed.overall_score_delta is None  # previous was None
    assert changed.category_deltas["growth"] is None  # previous was None


def test_record_and_diff_first_run_returns_none_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    result = _make_result("AAPL", "2026-01-01", overall=2.0, valuation=2.0, growth=1.0)

    what_changed = record_and_diff(result)

    assert what_changed is None
    history = load_history("AAPL")
    assert len(history) == 1
    assert history[0].overall_score == 2.0


def test_record_and_diff_second_run_returns_diff(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    first = _make_result("AAPL", "2026-01-01", overall=2.0, valuation=2.0, growth=1.0)
    second = _make_result("AAPL", "2026-02-01", overall=3.0, valuation=3.0, growth=2.0)

    record_and_diff(first)
    what_changed = record_and_diff(second)

    assert what_changed is not None
    assert what_changed.previous_as_of == "2026-01-01"
    assert what_changed.overall_score_delta == 1.0
    assert what_changed.category_deltas["valuation"] == 1.0
    assert what_changed.category_deltas["growth"] == 1.0

    history = load_history("AAPL")
    assert len(history) == 2


def test_load_history_returns_empty_list_for_unknown_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))

    assert load_history("NOPE") == []


def test_history_is_isolated_from_real_user_home(monkeypatch, tmp_path):
    # defense-in-depth check: confirm the env var override actually redirects
    # storage away from the real ~/.marketsignal, so tests can never write
    # into a real user's home directory
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    record_and_diff(_make_result("MSFT", "2026-01-01", overall=1.0, valuation=1.0, growth=1.0))

    assert (tmp_path / "MSFT.json").exists()
