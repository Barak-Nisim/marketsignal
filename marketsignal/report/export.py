"""CSV and JSON export of a ScoreResult, for tracking outside the app.

Both formats export the deterministic score data only -- ticker, overall
score/tier, category scores, and (for JSON) every metric plus any sector
comparison -- never the AI-generated thesis prose, which doesn't have a
natural row-and-column shape and isn't what "tracking in a spreadsheet"
is asking for. CSV is one row per research run, meant to be appended to
over time; JSON is the fuller structured dump for programmatic use.
"""

from __future__ import annotations

import csv
import io
import json

from marketsignal.models import ScoreResult
from marketsignal.sector_benchmarks import SectorComparison

CSV_FIELDS = [
    "ticker",
    "company_name",
    "sector",
    "industry",
    "as_of",
    "overall_score",
    "tier",
    "valuation_score",
    "growth_score",
    "profitability_score",
    "financial_health_score",
    "momentum_score",
]


def _round_or_blank(value: float | None) -> float | str:
    return "" if value is None else round(value, 2)


def render_csv(result: ScoreResult) -> str:
    """One CSV row (with a header) summarizing the result at the category
    level -- ticker, overall score/tier, and each category's score."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()

    f = result.financials
    row = {
        "ticker": f.ticker,
        "company_name": f.company_name,
        "sector": f.sector or "",
        "industry": f.industry or "",
        "as_of": f.as_of,
        "overall_score": _round_or_blank(result.overall_score),
        "tier": result.tier,
    }
    for category in result.category_scores:
        row[f"{category.id}_score"] = _round_or_blank(category.score)

    writer.writerow(row)
    return buf.getvalue()


def render_json(
    result: ScoreResult, sector_comparisons: tuple[SectorComparison, ...] = ()
) -> str:
    """The full deterministic result as JSON: every category, every metric
    within it, and any sector-relative valuation comparisons."""
    f = result.financials
    payload = {
        "ticker": f.ticker,
        "company_name": f.company_name,
        "sector": f.sector,
        "industry": f.industry,
        "as_of": f.as_of,
        "overall_score": result.overall_score,
        "tier": result.tier,
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "score": category.score,
                "metrics": [
                    {
                        "key": metric.key,
                        "label": metric.label,
                        "value": metric.value,
                        "score": metric.score,
                    }
                    for metric in category.metric_scores
                ],
            }
            for category in result.category_scores
        ],
        "sector_comparisons": [
            {
                "metric_key": c.metric_key,
                "metric_label": c.metric_label,
                "ticker_value": c.ticker_value,
                "sector": c.sector,
                "sector_median": c.sector_median,
                "label": c.label,
            }
            for c in sector_comparisons
        ],
    }
    return json.dumps(payload, indent=2)
