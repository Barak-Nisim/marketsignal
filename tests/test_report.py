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


def test_render_includes_sector_comparison_under_valuation():
    report = render(_sample_result())

    assert "vs. Technology sector median" in report
    assert "Price / Book: 45.00 vs. 8.00 -- More expensive than sector" in report
    assert "Trailing P/E: 28.00 vs. 28.00 -- In line with sector" in report


def test_render_omits_sector_comparison_when_sector_is_unknown():
    from dataclasses import replace

    result = score_financials(replace(_sample_result().financials, sector=None))
    report = render(result)

    assert "vs." not in report


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
        "bull_case": "Growth is steady and margins are healthy.",
        "bear_case": "Valuation looks stretched relative to peers.",
        "confidence": "Medium",
        "key_evidence": ["Valuation", "Growth"],
        "catalysts": [
            {
                "catalyst": "Next earnings report",
                "claim_type": "Fact",
                "based_on": "Growth",
            }
        ],
        "risk_factors": [
            {
                "factor": "Elevated valuation multiples",
                "claim_type": "Fact",
                "based_on": "Valuation",
            },
            {
                "factor": "Slowing revenue growth",
                "claim_type": "Inference",
                "based_on": "Growth",
            },
        ],
        "what_would_change_my_mind": ["If revenue growth turns negative"],
        "invalidation_check": [
            {
                "condition": "If revenue growth turns negative",
                "status": "Not triggered",
                "explanation": "Revenue growth is still 8% year over year.",
            }
        ],
        "claim_accuracy_check": [
            {
                "claim": "Elevated valuation multiples",
                "status": "Held up",
                "explanation": "Trailing P/E is still elevated.",
            }
        ],
    }

    report = render(_sample_result(), ai_narrative=ai_narrative)

    assert "## Thesis" in report
    assert "Medium" in report
    assert "Growth is steady and margins are healthy." in report
    assert "Valuation looks stretched relative to peers." in report
    assert "Elevated valuation multiples [Fact, based on Valuation]" in report
    assert "Slowing revenue growth [Inference, based on Growth]" in report
    assert "Next earnings report [Fact, based on Growth]" in report
    assert "If revenue growth turns negative" in report
    assert "**Not triggered** -- If revenue growth turns negative" in report
    assert "Revenue growth is still 8% year over year." in report
    assert "**Held up** -- Elevated valuation multiples" in report
    assert "Trailing P/E is still elevated." in report
