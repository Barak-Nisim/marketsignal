"""FastAPI web UI for MarketSignal.

Thin wrapper around the same data/scoring/history/report modules the CLI
uses -- no scoring or narration logic lives here. Run locally with
`marketsignal serve`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from marketsignal.accuracy import compute_accuracy_summary
from marketsignal.charts import sparkline_svg
from marketsignal.comparison import build_comparison
from marketsignal.data.yfinance_source import (
    DataUnavailableError,
    TickerNotFoundError,
    fetch_price_history,
    fetch_raw_financials,
)
from marketsignal.education import (
    SCORE_SCALE_EXPLANATION,
    concept_anchor,
    get_category_explanation,
    get_metric_explanation,
    learn_sections,
)
from marketsignal.favorites import add_favorite, is_favorite, list_favorites, remove_favorite
from marketsignal.history import list_recent_tickers, load_history, record_and_diff
from marketsignal.journal import add_journal_entry, load_journal
from marketsignal.models import SIGNAL_LEVELS
from marketsignal.outcomes import compute_outcomes
from marketsignal.portfolio_performance import (
    PERIOD_LABELS,
    SHARES_PER_HOLDING,
    build_portfolio_performance,
)
from marketsignal.portfolio_review import build_portfolio_review
from marketsignal.portfolios import (
    delete_portfolio_by_slug,
    get_portfolio_by_slug,
    list_portfolios,
    save_portfolio,
    slugify,
)
from marketsignal.price_trend import build_price_ranges
from marketsignal.report.export import render_csv, render_json
from marketsignal.report.markdown import format_value
from marketsignal.scoring import score_financials, signal_bucket, tier_for_score
from marketsignal.sector_benchmarks import build_valuation_sector_view
from marketsignal.thesis_history import (
    load_thesis_history,
    previous_claims,
    previous_invalidation_conditions,
    record_thesis_and_diff,
)

WEB_DIR = Path(__file__).parent
TREND_WINDOW = 10  # most recent research runs shown in a trend sparkline

app = FastAPI(title="MarketSignal")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
templates.env.filters["slugify"] = slugify
# Plain-language glossary lookups for the inline info tooltips (see education.py).
# Registered as globals so any template can call them; they return None when a
# category/metric has no entry, and the templates skip the tooltip in that case.
templates.env.globals["category_explanation"] = get_category_explanation
templates.env.globals["metric_explanation"] = get_metric_explanation
templates.env.globals["score_scale_explanation"] = SCORE_SCALE_EXPLANATION
# Anchor for the tooltip's "Learn more" deep-link into /learn; None if no entry.
templates.env.globals["concept_anchor"] = concept_anchor
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


def _ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _favorite_summaries() -> list[dict]:
    summaries = []
    for ticker in list_favorites():
        recent = load_history(ticker)[-TREND_WINDOW:]
        latest = recent[-1] if recent else None
        summaries.append(
            {
                "ticker": ticker,
                "latest_score": latest.overall_score if latest else None,
                "latest_tier": (
                    tier_for_score(latest.overall_score)
                    if latest and latest.overall_score is not None
                    else None
                ),
                "sparkline": sparkline_svg([s.overall_score for s in recent]),
                "has_history": bool(recent),
            }
        )
    return summaries


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {})


@app.get("/how-it-works", response_class=HTMLResponse)
def how_it_works(request: Request):
    return templates.TemplateResponse(request, "how_it_works.html", {})


@app.get("/learn", response_class=HTMLResponse)
def learn(request: Request):
    return templates.TemplateResponse(
        request,
        "learn.html",
        {
            "sections": learn_sections(),
            "score_scale_explanation": SCORE_SCALE_EXPLANATION,
        },
    )


@app.get("/compare", response_class=HTMLResponse)
def compare_form(request: Request):
    return templates.TemplateResponse(request, "compare.html", {"comparison": None, "error": None})


@app.post("/compare", response_class=HTMLResponse)
def compare_run(request: Request, ticker_a: str = Form(...), ticker_b: str = Form(...)):
    results = []
    for ticker in (ticker_a, ticker_b):
        try:
            results.append(score_financials(fetch_raw_financials(ticker)))
        except (TickerNotFoundError, DataUnavailableError) as exc:
            return templates.TemplateResponse(
                request,
                "compare.html",
                {
                    "comparison": None,
                    "error": str(exc),
                    "ticker_a": ticker_a,
                    "ticker_b": ticker_b,
                },
            )

    return templates.TemplateResponse(
        request,
        "compare.html",
        {
            "comparison": build_comparison(*results),
            "error": None,
            "tier_for_score": tier_for_score,
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
        },
    )


@app.get("/app", response_class=HTMLResponse)
def app_form(request: Request, ticker: str = "AAPL"):
    return templates.TemplateResponse(
        request,
        "app_form.html",
        {
            "ticker": ticker,
            "ai_available": _ai_available(),
            "error": None,
            "recent": list_recent_tickers(),
            "favorites": _favorite_summaries(),
        },
    )


@app.post("/favorites/add")
def favorites_add(ticker: str = Form(...)):
    add_favorite(ticker)
    return RedirectResponse(url="/app", status_code=303)


@app.post("/favorites/remove")
def favorites_remove(ticker: str = Form(...)):
    remove_favorite(ticker)
    return RedirectResponse(url="/app", status_code=303)


@app.post("/journal/add")
def journal_add(ticker: str = Form(...), note: str = Form(...)):
    if note.strip():
        add_journal_entry(ticker, note.strip())
    return RedirectResponse(url=f"/app?ticker={ticker.upper()}", status_code=303)


@app.post("/research", response_class=HTMLResponse)
def research(request: Request, ticker: str = Form(...), use_ai: str | None = Form(None)):
    try:
        financials = fetch_raw_financials(ticker)
    except (TickerNotFoundError, DataUnavailableError) as exc:
        return templates.TemplateResponse(
            request,
            "app_form.html",
            {"ticker": ticker, "ai_available": _ai_available(), "error": str(exc)},
        )

    result = score_financials(financials)
    what_changed = record_and_diff(result)

    ai_narrative = None
    thesis_delta = None
    accuracy_summary = None
    if use_ai and _ai_available():
        from marketsignal.ai.narrator import generate_narrative

        prior_conditions = previous_invalidation_conditions(financials.ticker)
        prior_claims = previous_claims(financials.ticker)
        ai_narrative = generate_narrative(result, what_changed, prior_conditions, prior_claims)
        thesis_delta = record_thesis_and_diff(financials.ticker, financials.as_of, ai_narrative)
        accuracy_summary = compute_accuracy_summary(load_thesis_history(financials.ticker))

    full_history = load_history(financials.ticker)
    trend = full_history[-TREND_WINDOW:]
    outcomes = compute_outcomes(full_history, financials.current_price)
    price_ranges = build_price_ranges(fetch_price_history(financials.ticker))
    sector_comparisons = build_valuation_sector_view(financials)

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "result": result,
            "what_changed": what_changed,
            "ai_narrative": ai_narrative,
            "thesis_delta": thesis_delta,
            "accuracy_summary": accuracy_summary,
            "tier_for_score": tier_for_score,
            "format_value": format_value,
            "signal_levels": SIGNAL_LEVELS,
            "is_favorite": is_favorite(financials.ticker),
            "trend_sparkline": sparkline_svg([s.overall_score for s in trend]),
            "trend_count": len(trend),
            "outcomes": outcomes,
            "journal_entries": load_journal(financials.ticker),
            "price_ranges": price_ranges,
            "sector_comparisons": sector_comparisons,
        },
    )


@app.get("/export/{ticker}")
def export_report(ticker: str, format: str = "csv"):
    """Downloads the deterministic score data for a ticker as CSV or JSON --
    no AI thesis is fetched, since neither export format has a natural place
    for prose. Re-fetches and re-scores rather than reusing a cached report,
    same as every other route here."""
    try:
        financials = fetch_raw_financials(ticker)
    except (TickerNotFoundError, DataUnavailableError):
        return RedirectResponse(url=f"/app?ticker={ticker.upper()}", status_code=303)

    result = score_financials(financials)

    if format == "json":
        body = render_json(result, build_valuation_sector_view(financials))
        media_type = "application/json"
    else:
        body = render_csv(result)
        media_type = "text/csv"

    extension = "json" if format == "json" else "csv"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{financials.ticker}.{extension}"'},
    )


@app.get("/portfolios", response_class=HTMLResponse)
def portfolios_list(request: Request):
    return templates.TemplateResponse(
        request,
        "portfolios.html",
        {"portfolios": list_portfolios()},
    )


@app.post("/portfolios/save")
def portfolios_save(name: str = Form(...), tickers: str = Form("")):
    parsed = [t for t in re.split(r"[,\s]+", tickers.strip()) if t]
    portfolio = save_portfolio(name, parsed)
    return RedirectResponse(url=f"/portfolios/{slugify(portfolio.name)}/review", status_code=303)


@app.post("/portfolios/{slug}/delete")
def portfolios_delete(slug: str):
    delete_portfolio_by_slug(slug)
    return RedirectResponse(url="/portfolios", status_code=303)


@app.get("/portfolios/{slug}/review", response_class=HTMLResponse)
def portfolio_review_page(request: Request, slug: str, period: str = "1Y"):
    portfolio = get_portfolio_by_slug(slug)
    if portfolio is None:
        return RedirectResponse(url="/portfolios", status_code=303)

    results = []
    failed_tickers = []
    for ticker in portfolio.tickers:
        try:
            financials = fetch_raw_financials(ticker)
        except (TickerNotFoundError, DataUnavailableError):
            failed_tickers.append(ticker)
            continue
        result = score_financials(financials)
        record_and_diff(result)
        results.append(result)

    review = build_portfolio_review(portfolio.name, results, failed_tickers)

    price_histories = {ticker: fetch_price_history(ticker) for ticker in portfolio.tickers}
    performance = build_portfolio_performance(portfolio, price_histories, period)
    value_sparkline = sparkline_svg([p.value for p in performance.value_series])

    return templates.TemplateResponse(
        request,
        "portfolio_review.html",
        {
            "portfolio": portfolio,
            "review": review,
            "tier_for_score": tier_for_score,
            "signal_bucket": signal_bucket,
            "performance": performance,
            "period_labels": PERIOD_LABELS,
            "shares_per_holding": SHARES_PER_HOLDING,
            "value_sparkline": value_sparkline,
        },
    )
