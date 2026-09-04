"""Fetches raw financial data for a ticker from Yahoo Finance via yfinance.

Isolated in its own module so every other part of MarketSignal (scoring,
CLI, web) can be tested without ever hitting the network -- tests mock
fetch_raw_financials() directly rather than mocking yfinance internals.
"""

from __future__ import annotations

import datetime as dt
import time

import requests
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from marketsignal.models import PricePoint, RawFinancials


class TickerNotFoundError(Exception):
    """The ticker genuinely doesn't exist (or Yahoo has no data for it) --
    retrying wouldn't help."""

    def __init__(self, ticker: str):
        super().__init__(f"Could not find market data for ticker '{ticker}'.")
        self.ticker = ticker


class DataUnavailableError(Exception):
    """A real ticker, but the data source was temporarily unreachable even
    after retrying -- a rate limit or network blip, not a missing ticker.
    Distinct from TickerNotFoundError so callers (and their error messages)
    don't tell a user their ticker doesn't exist when it's Yahoo that's
    having a moment; retrying again shortly is the right next step."""

    def __init__(self, ticker: str):
        super().__init__(
            f"Market data for '{ticker}' is temporarily unavailable (Yahoo Finance "
            "may be rate-limiting or briefly unreachable). Try again shortly."
        )
        self.ticker = ticker


# Errors judged transient -- worth a retry with backoff rather than an
# immediate failure. YFRateLimitError is yfinance's own signal for "you're
# being rate-limited"; the requests.exceptions are generic network blips.
# Anything else (a malformed ticker, YFTickerMissingError, ...) is not
# retried -- retrying a genuinely bad ticker just wastes three round trips
# to reach the same answer.
_TRANSIENT_ERRORS = (
    YFRateLimitError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def _with_retry(fetch, *, attempts: int = 3, base_delay: float = 1.0, sleep=None):
    """Calls fetch() up to `attempts` times, retrying only on _TRANSIENT_ERRORS
    with exponential backoff (base_delay, base_delay*2, ...). Any other
    exception propagates immediately on the first try. Re-raises the last
    transient error once attempts are exhausted.

    `sleep` defaults to time.sleep looked up at call time, not bound as a
    default argument value, so tests that patch time.sleep on this module
    (rather than passing sleep= explicitly) actually take effect."""
    sleep = sleep or time.sleep
    for attempt in range(attempts):
        try:
            return fetch()
        except _TRANSIENT_ERRORS:
            if attempt == attempts - 1:
                raise
            sleep(base_delay * (2**attempt))


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
    first. Returns [] on any fetch failure (after retrying a transient one)
    or if the ticker has no price history -- this feeds an optional chart,
    not a required field, so a miss here should never break the rest of a
    research run."""
    ticker = ticker.strip().upper()
    try:
        history = _with_retry(lambda: yf.Ticker(ticker).history(period="max"))
    except Exception:  # noqa: BLE001 -- same "any failure -> no data" posture as before
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
        info = _with_retry(lambda: yf_ticker.info)
    except _TRANSIENT_ERRORS as exc:
        raise DataUnavailableError(ticker) from exc
    except Exception as exc:  # noqa: BLE001 -- anything else means no usable data for this ticker
        raise TickerNotFoundError(ticker) from exc

    company_name = info.get("longName") or info.get("shortName")
    if not company_name or info.get("regularMarketPrice") is None:
        raise TickerNotFoundError(ticker)

    try:
        history = _with_retry(lambda: yf_ticker.history(period="1y"))
    except Exception:  # noqa: BLE001 -- price-change fields are optional; same "any
        # failure -> no data" posture as fetch_price_history. A Yahoo hiccup here
        # (rate limiting is common) must not 500 an otherwise-complete research run.
        history = None

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
