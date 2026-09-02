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

from dataclasses import dataclass

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


# ===========================================================================
# Encyclopedia -- the structured entries behind the /learn page and the
# tooltips' "Learn more" links. Every Concept reuses the plain-language text
# above verbatim (the glossaries stay the single source of truth) and adds
# an anchor, a small hand-drawn SVG diagram, and a couple of outside
# references. Diagrams are drawn with CSS custom properties (var(--accent)
# etc.) so they follow the app's light/dark theme; the hex fallbacks only
# matter if an <svg> is rendered outside the app stylesheet.
# ===========================================================================


@dataclass(frozen=True)
class Reference:
    title: str
    url: str


@dataclass(frozen=True)
class Concept:
    key: str
    title: str
    kind: str  # "category" or "metric"
    explanation: str
    anchor: str
    diagram: str  # an inline <svg> string
    references: tuple[Reference, ...]


_INK = "var(--text, #1f2933)"
_MUTED = "var(--muted, #7b8794)"
_ACCENT = "var(--accent, #22e584)"
_DOWN = "var(--down, #e5484d)"
_FRAME = "var(--border, #d2d6dc)"


def _svg(body: str, *, w: int = 260, h: int = 132) -> str:
    return (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'class="learn-diagram" xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )


def _label(x: float, y: float, text: str, *, anchor: str = "middle") -> str:
    return (
        f'<text x="{x:.0f}" y="{y:.0f}" fill="{_MUTED}" font-size="11" '
        f'text-anchor="{anchor}" font-family="sans-serif">{text}</text>'
    )


def _compare_bars(left: str, left_frac: float, right: str, right_frac: float, *, look: str) -> str:
    """Two vertical bars whose heights show the two sides of a ratio; the
    side named by `look` ("left"/"right") is drawn in the accent colour as
    the one to read."""
    base, span, w, lx, rx = 98, 76, 46, 62, 152
    lh, rh = left_frac * span, right_frac * span
    lc = _ACCENT if look == "left" else _MUTED
    rc = _ACCENT if look == "right" else _MUTED
    return _svg(
        f'<line x1="42" y1="{base}" x2="230" y2="{base}" stroke="{_FRAME}" stroke-width="1.5"/>'
        f'<rect x="{lx}" y="{base - lh:.1f}" width="{w}" height="{lh:.1f}" rx="3" fill="{lc}"/>'
        f'<rect x="{rx}" y="{base - rh:.1f}" width="{w}" height="{rh:.1f}" rx="3" fill="{rc}"/>'
        f"{_label(lx + w / 2, base + 16, left)}{_label(rx + w / 2, base + 16, right)}"
    )


def _kept_bar(kept_frac: float, kept: str, rest: str) -> str:
    """One horizontal bar split into a kept (accent) portion and the rest
    (muted) -- for margins, "the slice of a sales dollar left over"."""
    x, y, total, h = 20, 52, 220, 26
    kw = kept_frac * total
    rw = total - kw
    return _svg(
        f'<rect x="{x}" y="{y}" width="{kw:.1f}" height="{h}" fill="{_ACCENT}" rx="3"/>'
        f'<rect x="{x + kw:.1f}" y="{y}" width="{rw:.1f}" height="{h}" fill="{_MUTED}" rx="3"/>'
        f'<rect x="{x}" y="{y}" width="{total}" height="{h}" fill="none" stroke="{_FRAME}" rx="3"/>'
        f"{_label(x + kw / 2, y + h + 16, kept)}"
        f"{_label(x + kw + rw / 2, y + h + 16, rest)}"
    )


def _trend(rising: bool = True) -> str:
    """A price/'change over time' line inside a frame."""
    colour = _ACCENT if rising else _DOWN
    pts = "30,86 80,70 120,78 170,44 226,26" if rising else "30,30 80,48 120,40 170,74 226,92"
    tip = "226,26" if rising else "226,92"
    tx, ty = (int(v) for v in tip.split(","))
    return _svg(
        f'<rect x="18" y="14" width="224" height="86" fill="none" stroke="{_FRAME}" rx="4"/>'
        f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{tx}" cy="{ty}" r="3.5" fill="{colour}"/>'
        f"{_label(130, 122, 'time')}"
    )


def _range_marker(frac: float) -> str:
    """A 52-week low-to-high track with a marker showing where price sits."""
    x, y, total = 30, 60, 200
    mx = x + frac * total
    return _svg(
        f'<line x1="{x}" y1="{y}" x2="{x + total}" y2="{y}" stroke="{_FRAME}" stroke-width="3"/>'
        f'<line x1="{x}" y1="{y - 8}" x2="{x}" y2="{y + 8}" stroke="{_MUTED}" stroke-width="2"/>'
        f'<line x1="{x + total}" y1="{y - 8}" x2="{x + total}" y2="{y + 8}" '
        f'stroke="{_MUTED}" stroke-width="2"/>'
        f'<circle cx="{mx:.1f}" cy="{y}" r="6" fill="{_ACCENT}"/>'
        f"{_label(x, y + 24, '52wk low')}{_label(x + total, y + 24, '52wk high')}"
    )


def _ref(title: str, url: str) -> Reference:
    return Reference(title=title, url=url)


_INVESTOR_GOV = _ref(
    "SEC / investor.gov: investing basics",
    "https://www.investor.gov/introduction-investing/investing-basics",
)

# Ordered for display: each category followed by its own metrics, in the
# same order score_financials() builds them. test_education.py checks this
# against a real ScoreResult so it cannot silently drift.
_CATEGORY_METRICS: dict[str, tuple[str, ...]] = {
    "valuation": ("trailing_pe", "price_to_book", "price_to_sales", "peg_ratio"),
    "growth": ("revenue_growth", "earnings_growth"),
    "profitability": ("gross_margin", "operating_margin", "return_on_equity"),
    "financial_health": ("debt_to_equity", "current_ratio"),
    "momentum": ("price_change_12mo", "price_change_3mo", "pct_of_52wk_range"),
}

_CATEGORY_TITLES = {
    "valuation": "Valuation",
    "growth": "Growth",
    "profitability": "Profitability",
    "financial_health": "Financial Health",
    "momentum": "Momentum",
}

_METRIC_TITLES = {
    "trailing_pe": "Trailing P/E",
    "price_to_book": "Price / Book",
    "price_to_sales": "Price / Sales",
    "peg_ratio": "PEG Ratio",
    "revenue_growth": "Revenue Growth (YoY)",
    "earnings_growth": "Earnings Growth (YoY)",
    "gross_margin": "Gross Margin",
    "operating_margin": "Operating Margin",
    "return_on_equity": "Return on Equity",
    "debt_to_equity": "Debt / Equity",
    "current_ratio": "Current Ratio",
    "price_change_12mo": "12-Month Price Change",
    "price_change_3mo": "3-Month Price Change",
    "pct_of_52wk_range": "Position in 52-Week Range",
}

_DIAGRAMS: dict[str, str] = {
    "valuation": _compare_bars("Price", 0.85, "Fundamentals", 0.5, look="right"),
    "growth": _trend(rising=True),
    "profitability": _kept_bar(0.22, "Profit", "Costs"),
    "financial_health": _compare_bars("Assets", 0.75, "Debt", 0.45, look="left"),
    "momentum": _trend(rising=True),
    "trailing_pe": _compare_bars("Price", 0.8, "Earnings", 0.35, look="right"),
    "price_to_book": _compare_bars("Price", 0.8, "Book value", 0.45, look="right"),
    "price_to_sales": _compare_bars("Price", 0.8, "Revenue", 0.55, look="right"),
    "peg_ratio": _compare_bars("P/E ratio", 0.7, "Growth rate", 0.55, look="right"),
    "revenue_growth": _trend(rising=True),
    "earnings_growth": _trend(rising=True),
    "gross_margin": _kept_bar(0.45, "Gross profit", "Cost of goods"),
    "operating_margin": _kept_bar(0.25, "Operating profit", "Operating costs"),
    "return_on_equity": _compare_bars("Annual profit", 0.3, "Equity", 0.85, look="left"),
    "debt_to_equity": _compare_bars("Debt", 0.55, "Equity", 0.8, look="right"),
    "current_ratio": _compare_bars("Current assets", 0.78, "Near-term bills", 0.5, look="left"),
    "price_change_12mo": _trend(rising=True),
    "price_change_3mo": _trend(rising=True),
    "pct_of_52wk_range": _range_marker(0.7),
}

_REFERENCES: dict[str, tuple[Reference, ...]] = {
    "valuation": (
        _ref("Investopedia: Valuation", "https://www.investopedia.com/terms/v/valuation.asp"),
        _INVESTOR_GOV,
    ),
    "growth": (
        _ref("Investopedia: Growth Rates", "https://www.investopedia.com/terms/g/growthrates.asp"),
        _INVESTOR_GOV,
    ),
    "profitability": (
        _ref(
            "Investopedia: Profitability Ratios",
            "https://www.investopedia.com/terms/p/profitabilityratios.asp",
        ),
    ),
    "financial_health": (
        _ref(
            "Investopedia: Liquidity Ratios",
            "https://www.investopedia.com/terms/l/liquidityratios.asp",
        ),
        _ref(
            "Investopedia: Leverage Ratio",
            "https://www.investopedia.com/terms/l/leverageratio.asp",
        ),
    ),
    "momentum": (
        _ref("Investopedia: Momentum", "https://www.investopedia.com/terms/m/momentum.asp"),
    ),
    "trailing_pe": (
        _ref(
            "Investopedia: P/E Ratio",
            "https://www.investopedia.com/terms/p/price-earningsratio.asp",
        ),
    ),
    "price_to_book": (
        _ref(
            "Investopedia: Price-to-Book Ratio",
            "https://www.investopedia.com/terms/p/price-to-bookratio.asp",
        ),
    ),
    "price_to_sales": (
        _ref(
            "Investopedia: Price-to-Sales Ratio",
            "https://www.investopedia.com/terms/p/price-to-salesratio.asp",
        ),
    ),
    "peg_ratio": (
        _ref("Investopedia: PEG Ratio", "https://www.investopedia.com/terms/p/pegratio.asp"),
    ),
    "revenue_growth": (
        _ref("Investopedia: Revenue", "https://www.investopedia.com/terms/r/revenue.asp"),
    ),
    "earnings_growth": (
        _ref(
            "Investopedia: Earnings Per Share",
            "https://www.investopedia.com/terms/e/eps.asp",
        ),
    ),
    "gross_margin": (
        _ref(
            "Investopedia: Gross Margin",
            "https://www.investopedia.com/terms/g/grossmargin.asp",
        ),
    ),
    "operating_margin": (
        _ref(
            "Investopedia: Operating Margin",
            "https://www.investopedia.com/terms/o/operatingmargin.asp",
        ),
    ),
    "return_on_equity": (
        _ref(
            "Investopedia: Return on Equity",
            "https://www.investopedia.com/terms/r/returnonequity.asp",
        ),
    ),
    "debt_to_equity": (
        _ref(
            "Investopedia: Debt-to-Equity Ratio",
            "https://www.investopedia.com/terms/d/debtequityratio.asp",
        ),
    ),
    "current_ratio": (
        _ref(
            "Investopedia: Current Ratio",
            "https://www.investopedia.com/terms/c/currentratio.asp",
        ),
    ),
    "price_change_12mo": (
        _ref("Investopedia: Total Return", "https://www.investopedia.com/terms/t/totalreturn.asp"),
    ),
    "price_change_3mo": (
        _ref("Investopedia: Momentum", "https://www.investopedia.com/terms/m/momentum.asp"),
    ),
    "pct_of_52wk_range": (
        _ref(
            "Investopedia: 52-Week High/Low",
            "https://www.investopedia.com/terms/1/52-week-high-low.asp",
        ),
    ),
}


def _anchor(key: str) -> str:
    return "learn-" + key.replace("_", "-")


def _build_concepts() -> dict[str, Concept]:
    concepts: dict[str, Concept] = {}
    for category_id, metric_keys in _CATEGORY_METRICS.items():
        concepts[category_id] = Concept(
            key=category_id,
            title=_CATEGORY_TITLES[category_id],
            kind="category",
            explanation=CATEGORY_GLOSSARY[category_id],
            anchor=_anchor(category_id),
            diagram=_DIAGRAMS[category_id],
            references=_REFERENCES[category_id],
        )
        for metric_key in metric_keys:
            concepts[metric_key] = Concept(
                key=metric_key,
                title=_METRIC_TITLES[metric_key],
                kind="metric",
                explanation=METRIC_GLOSSARY[metric_key],
                anchor=_anchor(metric_key),
                diagram=_DIAGRAMS[metric_key],
                references=_REFERENCES[metric_key],
            )
    return concepts


CONCEPTS: dict[str, Concept] = _build_concepts()


def get_concept(key: str) -> Concept | None:
    return CONCEPTS.get(key)


def learn_sections() -> list[dict]:
    """The /learn page's structure: each category concept with its own
    metric concepts nested, in scoring order."""
    return [
        {
            "category": CONCEPTS[category_id],
            "metrics": [CONCEPTS[m] for m in metric_keys],
        }
        for category_id, metric_keys in _CATEGORY_METRICS.items()
    ]
