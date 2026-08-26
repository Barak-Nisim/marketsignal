"""Fetches raw financial data for a ticker from Yahoo Finance via yfinance.

Isolated in its own module so every other part of MarketSignal (scoring,
CLI, web) can be tested without ever hitting the network -- tests mock
fetch_raw_financials() directly rather than mocking yfinance internals.
"""

from __future__ import annotations

import datetime as dt

import yfinance as yf

from marketsignal.models import PricePoint, RawFinancials


class TickerNotFoundError(Exception):
    def __init__(self, ticker: str):
        super().__init__(f"Could not find market data for ticker '{ticker}'.")
        self.ticker = ticker


def _price_change(history, months_ago: int) -> float | None:
    if history is None or history.empty:
        return None
    last_date = history.index[-1]
    current_price = float(history.loc[last_date, "Close"])
    if current_price == 0:
        return None
    target_date = last_date - dt.timedelta(days=months_ago * 30)
    eligible = history.index[history.index <= target_date]
    if len(eligible) == 0:
        return None
    past_price = float(history.loc[eligible[-1], "Close"])
    if past_price == 0:
        return None
    return (current_price - past_price) / past_price


def fetch_price_history(ticker: str) -> list[PricePoint]:
    """Daily closing prices for the ticker's full available history, oldest
    first. Returns [] on any fetch failure or if the ticker has no price
    history -- this feeds an optional chart, not a required field, so a
    miss here should never break the rest of a research run."""
    ticker = ticker.strip().upper()
    try:
        history = yf.Ticker(ticker).history(period="max")
    except Exception:  # noqa: BLE001 -- same "any failure -> no data" posture as fetch_raw_financials
        return []

    if history is None or history.empty:
        return []

    return [
        PricePoint(date=index.strftime("%Y-%m-%d"), close=float(row["Close"]))
        for index, row in history.iterrows()
    ]


def fetch_raw_financials(ticker: str) -> RawFinancials:
    ticker = ticker.strip().upper()
    yf_ticker = yf.Ticker(ticker)

    try:
        info = yf_ticker.info
    except Exception as exc:  # noqa: BLE001 -- any fetch failure maps to one clear error
        raise TickerNotFoundError(ticker) from exc

    company_name = info.get("longName") or info.get("shortName")
    if not company_name or info.get("regularMarketPrice") is None:
        raise TickerNotFoundError(ticker)

    history = yf_ticker.history(period="1y")

    return RawFinancials(
        ticker=ticker,
        company_name=company_name,
        sector=info.get("sector"),
        industry=info.get("industry"),
        as_of=dt.date.today().isoformat(),
        current_price=info.get("regularMarketPrice"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        price_change_3mo=_price_change(history, 3),
        price_change_6mo=_price_change(history, 6),
        price_change_12mo=_price_change(history, 12),
        trailing_pe=info.get("trailingPE"),
        price_to_book=info.get("priceToBook"),
        price_to_sales=info.get("priceToSalesTrailing12Months"),
        peg_ratio=info.get("pegRatio") or info.get("trailingPegRatio"),
        revenue_growth=info.get("revenueGrowth"),
        earnings_growth=info.get("earningsGrowth"),
        gross_margin=info.get("grossMargins"),
        operating_margin=info.get("operatingMargins"),
        return_on_equity=info.get("returnOnEquity"),
        debt_to_equity=info.get("debtToEquity"),
        current_ratio=info.get("currentRatio"),
    )
