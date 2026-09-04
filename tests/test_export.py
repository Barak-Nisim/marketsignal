import csv
import io
import json

from marketsignal.models import RawFinancials
from marketsignal.report.export import render_csv, render_json
from marketsignal.scoring import score_financials
from marketsignal.sector_benchmarks import build_valuation_sector_view


def _sample_result():
    financials = RawFinancials(
        ticker="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        as_of="2026-01-01",
        current_price=150,
        trailing_pe=28,
        price_to_book=45,
        revenue_growth=0.08,
        gross_margin=0.44,
        debt_to_equity=180,
        current_ratio=1.0,
    )
    return score_financials(financials), financials


def test_render_csv_has_a_header_and_one_row():
    result, _financials = _sample_result()

    body = render_csv(result)
    rows = list(csv.DictReader(io.StringIO(body)))

    assert len(rows) == 1
    row = rows[0]
    assert row["ticker"] == "AAPL"
    assert row["company_name"] == "Apple Inc."
    assert row["sector"] == "Technology"
    assert row["tier"] == result.tier
    assert row["valuation_score"] != ""


def test_render_csv_blanks_a_missing_category_score():
    financials = RawFinancials(
        ticker="ETF", company_name="Some ETF", sector=None, industry=None, as_of="2026-01-01"
    )
    result = score_financials(financials)

    row = next(csv.DictReader(io.StringIO(render_csv(result))))

    # ETFs have no fundamentals data, so every category is unscored
    assert row["valuation_score"] == ""
    assert row["overall_score"] == ""


def test_render_json_round_trips_categories_and_metrics():
    result, _financials = _sample_result()

    payload = json.loads(render_json(result))

    assert payload["ticker"] == "AAPL"
    assert payload["tier"] == result.tier
    category_ids = [c["id"] for c in payload["categories"]]
    assert category_ids == [c.id for c in result.category_scores]

    valuation = next(c for c in payload["categories"] if c["id"] == "valuation")
    metric_keys = [m["key"] for m in valuation["metrics"]]
    assert "trailing_pe" in metric_keys


def test_render_json_includes_sector_comparisons_when_given():
    result, financials = _sample_result()
    comparisons = build_valuation_sector_view(financials)

    payload = json.loads(render_json(result, comparisons))

    assert payload["sector_comparisons"]
    assert payload["sector_comparisons"][0]["sector"] == "Technology"


def test_render_json_sector_comparisons_default_to_empty():
    result, _financials = _sample_result()

    payload = json.loads(render_json(result))

    assert payload["sector_comparisons"] == []
