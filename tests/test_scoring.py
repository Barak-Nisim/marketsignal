from marketsignal.models import RawFinancials
from marketsignal.scoring import score_financials, tier_for_score


def _base_financials(**overrides) -> RawFinancials:
    defaults = dict(
        ticker="TEST",
        company_name="Test Co",
        sector="Technology",
        industry="Software",
        as_of="2026-01-01",
    )
    defaults.update(overrides)
    return RawFinancials(**defaults)


def test_strong_financials_score_near_top():
    financials = _base_financials(
        current_price=100,
        fifty_two_week_low=70,
        fifty_two_week_high=105,
        price_change_3mo=0.20,
        price_change_6mo=0.30,
        price_change_12mo=0.40,
        trailing_pe=8,
        price_to_book=0.8,
        price_to_sales=0.9,
        peg_ratio=0.7,
        revenue_growth=0.25,
        earnings_growth=0.25,
        gross_margin=0.60,
        operating_margin=0.30,
        return_on_equity=0.30,
        debt_to_equity=20,
        current_ratio=2.5,
    )

    result = score_financials(financials)

    assert result.overall_score is not None
    assert result.overall_score >= 3.5
    assert result.tier in ("Above Average", "Strong")


def test_weak_financials_score_near_bottom():
    financials = _base_financials(
        current_price=10,
        fifty_two_week_low=9,
        fifty_two_week_high=50,
        price_change_3mo=-0.30,
        price_change_6mo=-0.40,
        price_change_12mo=-0.50,
        trailing_pe=80,
        price_to_book=15,
        price_to_sales=20,
        peg_ratio=5,
        revenue_growth=-0.10,
        earnings_growth=-0.20,
        gross_margin=0.02,
        operating_margin=-0.10,
        return_on_equity=-0.10,
        debt_to_equity=400,
        current_ratio=0.5,
    )

    result = score_financials(financials)

    assert result.overall_score is not None
    assert result.overall_score <= 0.5
    assert result.tier == "Weak"


def test_etf_like_ticker_excludes_categories_with_no_data():
    # ETFs typically have no income-statement data (growth, profitability) --
    # those categories should be excluded from the overall score entirely,
    # not penalized as zero.
    financials = _base_financials(
        current_price=450,
        fifty_two_week_low=400,
        fifty_two_week_high=460,
        price_change_3mo=0.05,
        price_change_6mo=0.08,
        price_change_12mo=0.15,
        trailing_pe=None,
        price_to_book=None,
        price_to_sales=None,
        peg_ratio=None,
        revenue_growth=None,
        earnings_growth=None,
        gross_margin=None,
        operating_margin=None,
        return_on_equity=None,
        debt_to_equity=None,
        current_ratio=None,
    )

    result = score_financials(financials)

    categories_by_id = {c.id: c for c in result.category_scores}
    assert categories_by_id["valuation"].score is None
    assert categories_by_id["growth"].score is None
    assert categories_by_id["profitability"].score is None
    assert categories_by_id["financial_health"].score is None
    assert categories_by_id["momentum"].score is not None
    # overall score should be computed only from momentum, the one
    # available category
    assert result.overall_score == categories_by_id["momentum"].score


def test_all_data_missing_yields_none_overall_and_unknown_tier():
    financials = _base_financials()

    result = score_financials(financials)

    assert result.overall_score is None
    assert result.tier == "Unknown"
    assert all(c.score is None for c in result.category_scores)


def test_negative_pe_is_excluded_not_scored_as_expensive():
    financials = _base_financials(trailing_pe=-15)

    result = score_financials(financials)

    valuation = next(c for c in result.category_scores if c.id == "valuation")
    pe_metric = next(m for m in valuation.metric_scores if m.key == "trailing_pe")
    assert pe_metric.score is None
    assert pe_metric.value == -15  # raw value is still reported for transparency


def test_pct_of_52wk_range_handles_missing_or_invalid_bounds():
    # high == low (or missing) -> can't compute a meaningful position
    financials = _base_financials(
        current_price=100, fifty_two_week_low=100, fifty_two_week_high=100
    )
    result = score_financials(financials)
    momentum = next(c for c in result.category_scores if c.id == "momentum")
    range_metric = next(m for m in momentum.metric_scores if m.key == "pct_of_52wk_range")
    assert range_metric.value is None
    assert range_metric.score is None


def test_tier_for_score_boundaries():
    assert tier_for_score(0.0) == "Weak"
    assert tier_for_score(0.79) == "Weak"
    assert tier_for_score(0.8) == "Below Average"
    assert tier_for_score(1.6) == "Average"
    assert tier_for_score(2.4) == "Above Average"
    assert tier_for_score(3.2) == "Strong"
    assert tier_for_score(4.0) == "Strong"
