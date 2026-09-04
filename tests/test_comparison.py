from marketsignal.comparison import build_comparison
from marketsignal.models import RawFinancials
from marketsignal.scoring import score_financials


def _result(ticker: str, **overrides) -> None:
    defaults = dict(
        ticker=ticker,
        company_name=f"{ticker} Inc.",
        sector="Technology",
        industry="Software",
        as_of="2026-01-01",
        current_price=100,
        trailing_pe=20,
        revenue_growth=0.10,
        gross_margin=0.40,
        debt_to_equity=50,
        current_ratio=1.5,
    )
    defaults.update(overrides)
    return score_financials(RawFinancials(**defaults))


def test_higher_overall_score_is_the_leader():
    strong = _result("AAA", revenue_growth=0.30, earnings_growth=0.30)
    weak = _result("BBB", revenue_growth=0.0, earnings_growth=0.0)

    comparison = build_comparison(strong, weak)

    assert comparison.overall_leader == "a"
    assert comparison.overall_score_a > comparison.overall_score_b


def test_tied_scores_have_no_leader():
    a = _result("AAA")
    b = _result("BBB")

    comparison = build_comparison(a, b)

    assert comparison.overall_leader is None
    assert all(c.leader is None for c in comparison.categories)


def test_categories_line_up_by_id_in_scoring_order():
    a = _result("AAA")
    b = _result("BBB")

    comparison = build_comparison(a, b)

    assert [c.category_id for c in comparison.categories] == [
        cat.id for cat in a.category_scores
    ]


def test_a_category_missing_on_one_side_still_gets_a_leader():
    # ETF-shaped financials: growth/profitability/financial_health metrics
    # all unavailable, so those categories score None on the "b" side.
    has_data = _result("AAA")
    etf = score_financials(
        RawFinancials(
            ticker="ETF", company_name="Some ETF", sector=None, industry=None, as_of="2026-01-01"
        )
    )

    comparison = build_comparison(has_data, etf)

    growth = next(c for c in comparison.categories if c.category_id == "growth")
    assert growth.score_b is None
    assert growth.leader == "a"


def test_ticker_and_company_identifiers_are_preserved():
    a = _result("AAA")
    b = _result("BBB")

    comparison = build_comparison(a, b)

    assert comparison.ticker_a == "AAA"
    assert comparison.ticker_b == "BBB"
    assert comparison.company_name_a == "AAA Inc."
