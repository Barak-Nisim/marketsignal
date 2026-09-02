from marketsignal.education import (
    CATEGORY_GLOSSARY,
    METRIC_GLOSSARY,
    SCORE_SCALE_EXPLANATION,
    get_category_explanation,
    get_metric_explanation,
)
from marketsignal.models import RawFinancials
from marketsignal.scoring import score_financials


def _real_result():
    # every field populated so every metric in scoring.py actually gets
    # constructed, not skipped as unavailable
    financials = RawFinancials(
        ticker="TEST",
        company_name="Test Co",
        sector="Technology",
        industry="Software",
        as_of="2026-01-01",
        current_price=150,
        fifty_two_week_low=100,
        fifty_two_week_high=200,
        price_change_3mo=0.10,
        price_change_12mo=0.20,
        trailing_pe=15,
        price_to_book=3,
        price_to_sales=4,
        peg_ratio=1.2,
        revenue_growth=0.15,
        earnings_growth=0.10,
        gross_margin=0.4,
        operating_margin=0.2,
        return_on_equity=0.2,
        debt_to_equity=80,
        current_ratio=1.5,
    )
    return score_financials(financials)


def test_every_real_category_has_a_glossary_entry():
    result = _real_result()

    for category in result.category_scores:
        assert category.id in CATEGORY_GLOSSARY, f"missing glossary entry for {category.id}"


def test_every_real_metric_has_a_glossary_entry():
    result = _real_result()

    for category in result.category_scores:
        for metric in category.metric_scores:
            assert metric.key in METRIC_GLOSSARY, f"missing glossary entry for {metric.key}"


def test_glossary_has_no_stale_entries_beyond_real_categories_and_metrics():
    result = _real_result()

    real_category_ids = {c.id for c in result.category_scores}
    real_metric_keys = {m.key for c in result.category_scores for m in c.metric_scores}

    assert set(CATEGORY_GLOSSARY.keys()) == real_category_ids
    assert set(METRIC_GLOSSARY.keys()) == real_metric_keys


def test_get_category_explanation_returns_text_for_known_id():
    assert get_category_explanation("valuation") == CATEGORY_GLOSSARY["valuation"]


def test_get_category_explanation_returns_none_for_unknown_id():
    assert get_category_explanation("nope") is None


def test_get_metric_explanation_returns_text_for_known_key():
    assert get_metric_explanation("trailing_pe") == METRIC_GLOSSARY["trailing_pe"]


def test_get_metric_explanation_returns_none_for_unknown_key():
    assert get_metric_explanation("nope") is None


def test_score_scale_explanation_is_non_empty_and_mentions_the_scale():
    assert SCORE_SCALE_EXPLANATION
    assert "0" in SCORE_SCALE_EXPLANATION
    assert "4" in SCORE_SCALE_EXPLANATION


def test_no_glossary_text_uses_em_dash():
    all_text = list(CATEGORY_GLOSSARY.values()) + list(METRIC_GLOSSARY.values())
    all_text.append(SCORE_SCALE_EXPLANATION)

    for text in all_text:
        assert "—" not in text
