"""FastAPI web UI for MarketSignal.

Thin wrapper around the same data/scoring/history/report modules the CLI
uses -- no scoring or narration logic lives here. Run locally with
`marketsignal serve`.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from marketsignal.data.yfinance_source import TickerNotFoundError, fetch_raw_financials
from marketsignal.history import list_recent_tickers, record_and_diff
from marketsignal.models import SIGNAL_LEVELS
from marketsignal.report.markdown import format_value
from marketsignal.scoring import score_financials, tier_for_score

WEB_DIR = Path(__file__).parent

app = FastAPI(title="MarketSignal")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


def _ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


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
        },
    )


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
        },
    )
