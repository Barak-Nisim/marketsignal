"""Plain-language explanations of what MarketSignal's categories and
metrics mean, for someone who has never read a balance sheet before.

Single source of truth for both the inline tooltips on the report pages
and the standalone /learn page, so the two can never drift apart or say
different things about the same metric.

Deliberately does not repeat the exact numeric thresholds from
scoring.py -- those already live in docs/scoring_methodology.md,
hand-maintained, and duplicating them here would just be a second place
to go stale. This module explains the concept and the general direction
("lower is usually better here"), not the precise cutoff.

Explains concepts, never interprets a specific ticker's numbers toward a
conclusion -- that would edge back toward the Buy/Sell advice this tool
deliberately never gives.
"""

from __future__ import annotations

CATEGORY_GLOSSARY: dict[str, str] = {
    "valuation": (
        "How expensive the stock is relative to the business behind it -- "
        "earnings, book value, sales. A high score means you're paying "
        "relatively little for what the company actually produces; it "
        "doesn't mean the company is good or bad, just whether the price "
        "looks reasonable next to its fundamentals."
    ),
    "growth": (
        "How much bigger the company's revenue and profit got over the "
        "last year. Growth is what usually justifies paying a higher "
        "price today for a business that expects to be worth more later."
    ),
    "profitability": (
        "How efficiently the company turns revenue into actual profit. "
        "Two companies can sell the same amount and end up with very "
        "different results depending on how much it costs them to do it."
    ),
    "financial_health": (
        "How much debt the company is carrying and whether it has enough "
        "short-term cash and assets to cover its near-term bills. A "
        "financially strong company can survive a bad year; a weak one "
        "may not have that cushion."
    ),
    "momentum": (
        "How the stock's price has actually been moving recently, and "
        "where it sits relative to its own highs and lows over the past "
        "year. This is about market behavior, not the business itself --  "
        "a great company can still have weak momentum, and vice versa."
    ),
}

METRIC_GLOSSARY: dict[str, str] = {
    "trailing_pe": (
        "Price-to-earnings compares what you'd pay for the stock to how "
        "much profit the company actually makes per share. Lower "
        "generally means you're paying less for each dollar of profit, "
        "but very low can also mean the market expects trouble ahead."
    ),
    "price_to_book": (
        "Compares the stock price to the company's net assets (what it "
        "would theoretically be worth if it sold everything and paid off "
        "its debts). Lower can mean a bargain, or it can mean the market "
        "doubts those assets are worth what the books say."
    ),
    "price_to_sales": (
        "Compares the stock price to how much revenue the company brings "
        "in, useful for companies that aren't profitable yet. Lower "
        "generally means you're paying less per dollar of sales."
    ),
    "peg_ratio": (
        "Price-to-earnings adjusted for how fast the company is growing. "
        "A stock can look expensive on P/E alone but reasonable once you "
        "account for fast growth -- this metric tries to capture that."
    ),
    "revenue_growth": (
        "How much more the company sold this year compared to last year. "
        "Higher is generally better -- it's the most direct sign a "
        "business is actually expanding."
    ),
    "earnings_growth": (
        "How much more profit the company made this year compared to "
        "last year. A company can grow revenue while earnings shrink (or "
        "vice versa), which is why both are tracked separately."
    ),
    "gross_margin": (
        "The share of each sales dollar left after covering the direct "
        "cost of making the product or delivering the service. Higher "
        "means more room to cover everything else (marketing, R&D, "
        "overhead) and still turn a profit."
    ),
    "operating_margin": (
        "The share of each sales dollar left after covering the ordinary "
        "cost of running the business, not just making the product. "
        "Higher means the core business itself is efficient."
    ),
    "return_on_equity": (
        "How much profit the company generates for every dollar "
        "shareholders have invested in it. Higher generally means "
        "management is putting shareholders' money to more effective use."
    ),
    "debt_to_equity": (
        "How much the company has borrowed compared to what shareholders "
        "have put in. Lower generally means less risk from debt "
        "payments if business slows down, though some debt is normal "
        "and even healthy for most companies."
    ),
    "current_ratio": (
        "Whether the company has enough cash and short-term assets to "
        "cover its bills due within the next year. Higher generally "
        "means a healthier short-term cushion; too high can just mean "
        "cash sitting idle instead of being put to work."
    ),
    "price_change_12mo": (
        "How much the stock price has moved over the last year. This "
        "reflects market sentiment and momentum, not the underlying "
        "business -- a stock can rise or fall for reasons that have "
        "nothing to do with the company's actual performance."
    ),
    "price_change_3mo": (
        "How much the stock price has moved over the last three months -- "
        "a shorter, noisier window than the 12-month version, more "
        "sensitive to recent news and short-term sentiment."
    ),
    "pct_of_52wk_range": (
        "Where the current price sits between its lowest and highest "
        "point over the past year. Near the top can mean strength (or "
        "that it's gotten expensive); near the bottom can mean a "
        "bargain (or that something is genuinely wrong)."
    ),
}

SCORE_SCALE_EXPLANATION = (
    "Every metric and category is scored 0 to 4, labeled Weak, Below "
    "Average, Average, Above Average, or Strong. These labels describe "
    "how a metric compares to fixed, documented thresholds -- not a "
    "prediction of what the stock will do next, and never a signal to "
    "buy or sell. A 'Weak' valuation score means the stock looks "
    "expensive by the numbers, nothing more; what you do with that is "
    "your call."
)


def get_category_explanation(category_id: str) -> str | None:
    return CATEGORY_GLOSSARY.get(category_id)


def get_metric_explanation(metric_key: str) -> str | None:
    return METRIC_GLOSSARY.get(metric_key)
