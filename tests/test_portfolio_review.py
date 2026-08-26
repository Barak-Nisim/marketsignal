from marketsignal.models import RawFinancials, ScoreResult
from marketsignal.portfolio_review import build_portfolio_review
from marketsignal.scoring import score_financials


def _result(ticker: str, sector: str | None, **overrides) -> ScoreResult:
    defaults = {
        "ticker": ticker,
        "company_name": f"{ticker} Inc.",
        "sector": sector,
        "industry": "Test Industry",
        "as_of": "2026-01-01",
        "current_price": 150,
        "fifty_two_week_low": 100,
        "fifty_two_week_high": 200,
        "price_change_3mo": 0.10,
        "price_change_12mo": 0.20,
        "trailing_pe": 15,
        "revenue_growth": 0.20,
        "earnings_growth": 0.15,
        "gross_margin": 0.5,
        "operating_margin": 0.25,
        "return_on_equity": 0.30,
        "debt_to_equity": 40,
        "current_ratio": 1.5,
    }
    defaults.update(overrides)
    return score_financials(RawFinancials(**defaults))


def test_build_portfolio_review_empty_holdings_returns_no_score():
    review = build_portfolio_review("Empty", [], failed_tickers=[])

    assert review.overall_score is None
    assert review.tier is None
    assert review.category_averages == {}
    assert review.holdings == ()


def test_build_portfolio_review_averages_overall_score():
    holdings = [_result("AAPL", "Technology"), _result("KO", "Consumer Staples")]

    review = build_portfolio_review("Test", holdings, failed_tickers=[])

    expected = (holdings[0].overall_score + holdings[1].overall_score) / 2
    assert review.overall_score == expected
    assert review.tier is not None


def test_build_portfolio_review_category_averages_exclude_missing():
    # AAPL has every metric; an ETF-shaped holding has no profitability
    # data at all (no gross_margin/operating_margin/return_on_equity) --
    # its missing profitability score must not drag the average down or
    # get treated as a zero.
    full = _result("AAPL", "Technology")
    etf = _result(
        "VTI",
        None,
        gross_margin=None,
        operating_margin=None,
        return_on_equity=None,
        revenue_growth=None,
        earnings_growth=None,
    )

    review = build_portfolio_review("Test", [full, etf], failed_tickers=[])

    full_profitability = next(c.score for c in full.category_scores if c.id == "profitability")
    # ETF's missing profitability is excluded, not zeroed, from the average
    assert review.category_averages["profitability"] == full_profitability


def test_build_portfolio_review_category_averages_preserve_canonical_order():
    holdings = [_result("AAPL", "Technology")]

    review = build_portfolio_review("Test", holdings, failed_tickers=[])

    assert list(review.category_averages.keys()) == [
        "valuation",
        "growth",
        "profitability",
        "financial_health",
        "momentum",
    ]


def test_build_portfolio_review_sector_counts_unknown_bucket():
    holdings = [
        _result("AAPL", "Technology"),
        _result("MSFT", "Technology"),
        _result("VTI", None),
    ]

    review = build_portfolio_review("Test", holdings, failed_tickers=[])

    assert review.sector_counts == {"Technology": 2, "Unknown": 1}


def test_build_portfolio_review_carries_failed_tickers():
    review = build_portfolio_review(
        "Test", [_result("AAPL", "Technology")], failed_tickers=["BOGUS"]
    )

    assert review.failed_tickers == ("BOGUS",)
