from marketsignal.models import RawFinancials
from marketsignal.report.markdown import render
from marketsignal.scoring import score_financials


def _sample_result():
    financials = RawFinancials(
        ticker="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        as_of="2026-01-01",
        current_price=150,
        fifty_two_week_low=120,
        fifty_two_week_high=160,
        price_change_3mo=0.10,
        price_change_6mo=0.15,
        price_change_12mo=0.25,
        trailing_pe=28,
        price_to_book=45,
        price_to_sales=7.5,
        peg_ratio=2.1,
        revenue_growth=0.08,
        earnings_growth=0.12,
        gross_margin=0.44,
        operating_margin=0.30,
        return_on_equity=1.50,
        debt_to_equity=180,
        current_ratio=1.0,
    )
    return score_financials(financials)


def test_render_contains_key_sections():
    report = render(_sample_result())

    assert "MarketSignal Research Brief: Apple Inc. (AAPL)" in report
    assert "## Category Scores" in report
    assert "## Metric Detail" in report
    assert "Valuation" in report
    assert "## Thesis" not in report  # no AI narrative passed


def test_render_formats_percentages_and_ratios_differently():
    report = render(_sample_result())

    assert "8.0%" in report  # revenue_growth 0.08 -> percentage
    assert "28.00" in report  # trailing_pe -> plain ratio


def test_render_includes_what_changed_section():
    from marketsignal.models import WhatChanged

    what_changed = WhatChanged(
        previous_as_of="2025-12-01",
        overall_score_delta=0.3,
        category_deltas={"valuation": -0.5, "growth": 0.2},
    )

    report = render(_sample_result(), what_changed=what_changed)

    assert "What changed since 2025-12-01" in report
    assert "+0.30" in report
    assert "-0.50" in report


def test_render_includes_ai_thesis_when_provided():
    ai_narrative = {
        "thesis": "Growth is steady but valuation looks stretched relative to peers.",
        "confidence": "Medium",
        "risk_factors": ["Elevated valuation multiples", "Slowing revenue growth"],
    }

    report = render(_sample_result(), ai_narrative=ai_narrative)

    assert "## Thesis" in report
    assert "Medium" in report
    assert "Elevated valuation multiples" in report
