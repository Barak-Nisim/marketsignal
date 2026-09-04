from dataclasses import replace

from marketsignal.models import RawFinancials
from marketsignal.sector_benchmarks import (
    SECTOR_VALUATION_BENCHMARKS,
    VALUATION_METRIC_KEYS,
    build_valuation_sector_view,
)

BASE = RawFinancials(
    ticker="TEST",
    company_name="Test Co",
    sector="Technology",
    industry="Software",
    as_of="2026-01-01",
    current_price=100,
    trailing_pe=28.0,  # exactly at the Technology median
    price_to_book=45.0,  # far above the Technology median
    price_to_sales=6.0,  # exactly at the Technology median
    peg_ratio=1.0,  # far below the Technology median
)


def _by_key(comparisons, key):
    return next(c for c in comparisons if c.metric_key == key)


def test_metric_at_the_sector_median_is_in_line():
    comparisons = build_valuation_sector_view(BASE)

    assert _by_key(comparisons, "trailing_pe").label == "In line with sector"
    assert _by_key(comparisons, "price_to_sales").label == "In line with sector"


def test_metric_well_above_median_is_more_expensive():
    assert _by_key(build_valuation_sector_view(BASE), "price_to_book").label == (
        "More expensive than sector"
    )


def test_metric_well_below_median_is_cheaper():
    assert _by_key(build_valuation_sector_view(BASE), "peg_ratio").label == "Cheaper than sector"


def test_missing_metric_value_is_skipped_not_guessed():
    financials = replace(BASE, peg_ratio=None)

    comparisons = build_valuation_sector_view(financials)

    assert all(c.metric_key != "peg_ratio" for c in comparisons)
    assert len(comparisons) == 3


def test_ticker_with_no_sector_gets_no_comparisons():
    financials = replace(BASE, sector=None)

    assert build_valuation_sector_view(financials) == ()


def test_ticker_with_an_unrecognized_sector_gets_no_comparisons():
    financials = replace(BASE, sector="Not A Real Sector")

    assert build_valuation_sector_view(financials) == ()


def test_every_benchmark_sector_has_all_four_valuation_metrics():
    for sector, metrics in SECTOR_VALUATION_BENCHMARKS.items():
        for key in VALUATION_METRIC_KEYS:
            assert key in metrics, f"{sector} is missing a benchmark for {key}"
            assert metrics[key] > 0
