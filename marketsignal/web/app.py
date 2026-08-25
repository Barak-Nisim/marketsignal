"""FastAPI web UI for MarketSignal.

Thin wrapper around the same data/scoring/history/report modules the CLI
uses -- no scoring or narration logic lives here. Run locally with
`marketsignal serve`.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from marketsignal.charts import sparkline_svg
from marketsignal.data.yfinance_source import TickerNotFoundError, fetch_raw_financials
from marketsignal.favorites import add_favorite, is_favorite, list_favorites, remove_favorite
from marketsignal.history import list_recent_tickers, load_history, record_and_diff
from marketsignal.models import SIGNAL_LEVELS
from marketsignal.report.markdown import format_value
from marketsignal.scoring import score_financials, tier_for_score

WEB_DIR = Path(__file__).parent
TREND_WINDOW = 10  # most recent research runs shown in a trend sparkline

app = FastAPI(title="MarketSignal")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
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


@app.post("/research", response_class=HTMLResponse)
def research(request: Request, ticker: str = Form(...), use_ai: str | None = Form(None)):
    try:
        financials = fetch_raw_financials(ticker)
    except TickerNotFoundError as exc:
        return templates.TemplateResponse(
            request,
            "app_form.html",
            {"ticker": ticker, "ai_available": _ai_available(), "error": str(exc)},
        )

    result = score_financials(financials)
    what_changed = record_and_diff(result)

    ai_narrative = None
    if use_ai and _ai_available():
        from marketsignal.ai.narrator import generate_narrative

        ai_narrative = generate_narrative(result, what_changed)

    trend = load_history(financials.ticker)[-TREND_WINDOW:]

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "result": result,
            "what_changed": what_changed,
            "ai_narrative": ai_narrative,
            "tier_for_score": tier_for_score,
            "format_value": format_value,
            "signal_levels": SIGNAL_LEVELS,
            "is_favorite": is_favorite(financials.ticker),
            "trend_sparkline": sparkline_svg([s.overall_score for s in trend]),
            "trend_count": len(trend),
        },
    )
