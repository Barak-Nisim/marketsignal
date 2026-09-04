from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests
from yfinance.exceptions import YFRateLimitError

from marketsignal.data.yfinance_source import (
    DataUnavailableError,
    TickerNotFoundError,
    _with_retry,
    fetch_price_history,
    fetch_raw_financials,
)

FAKE_INFO = {
    "longName": "Test Company Inc.",
    "sector": "Technology",
    "industry": "Software",
    "regularMarketPrice": 150.0,
    "fiftyTwoWeekLow": 100.0,
    "fiftyTwoWeekHigh": 160.0,
    "trailingPE": 22.5,
    "priceToBook": 5.0,
    "priceToSalesTrailing12Months": 4.0,
    "pegRatio": 1.2,
    "revenueGrowth": 0.15,
    "earningsGrowth": 0.12,
    "grossMargins": 0.45,
    "operatingMargins": 0.20,
    "returnOnEquity": 0.18,
    "debtToEquity": 60.0,
    "currentRatio": 1.8,
}


def _fake_history(days=365, start_price=100.0, end_price=150.0):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="D")
    prices = [start_price + (end_price - start_price) * i / (days - 1) for i in range(days)]
    return pd.DataFrame({"Close": prices}, index=dates)


def test_with_retry_uses_exponential_backoff_and_succeeds_within_attempts():
    sleeps = []
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise YFRateLimitError()
        return "ok"

    result = _with_retry(flaky, attempts=3, base_delay=1.0, sleep=sleeps.append)

    assert result == "ok"
    assert sleeps == [1.0, 2.0]  # exponential: base_delay * 2**attempt


def test_with_retry_reraises_the_transient_error_once_attempts_are_exhausted():
    def always_rate_limited():
        raise YFRateLimitError()

    with pytest.raises(YFRateLimitError):
        _with_retry(always_rate_limited, attempts=2, base_delay=0, sleep=lambda s: None)


def test_with_retry_never_retries_a_non_transient_error():
    calls = {"n": 0}

    def not_transient():
        calls["n"] += 1
        raise ValueError("this ticker just doesn't exist")

    with pytest.raises(ValueError):
        _with_retry(not_transient, attempts=5, sleep=lambda s: None)

    assert calls["n"] == 1  # no retries wasted on a non-transient failure


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_maps_info_fields(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = FAKE_INFO
    mock_ticker.history.return_value = _fake_history()
    mock_ticker_cls.return_value = mock_ticker

    financials = fetch_raw_financials("test")

    assert financials.ticker == "TEST"  # normalized to uppercase
    assert financials.company_name == "Test Company Inc."
    assert financials.sector == "Technology"
    assert financials.trailing_pe == 22.5
    assert financials.debt_to_equity == 60.0
    assert financials.price_change_12mo is not None
    assert financials.price_change_12mo > 0  # price rose over the fake history


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_raises_for_unknown_ticker(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {}  # yfinance returns a near-empty dict for bad tickers
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(TickerNotFoundError):
        fetch_raw_financials("BOGUS")


class _RaisingTicker:
    """A minimal stub whose .info raises, without mutating MagicMock's
    shared class the way patching a property on a MagicMock instance
    would."""

    @property
    def info(self):
        raise RuntimeError("boom")


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_raises_when_yfinance_errors(mock_ticker_cls):
    mock_ticker_cls.return_value = _RaisingTicker()

    with pytest.raises(TickerNotFoundError):
        fetch_raw_financials("AAPL")


class _FlakyInfoTicker:
    """`.info` raises each exception in `side_effects` in order, then
    returns FAKE_INFO on every access after that. Tracks how many times
    `.info` was actually accessed, so a test can prove retries happened
    (or didn't)."""

    def __init__(self, side_effects):
        self._side_effects = list(side_effects)
        self.info_call_count = 0

    @property
    def info(self):
        self.info_call_count += 1
        if self._side_effects:
            raise self._side_effects.pop(0)
        return FAKE_INFO

    def history(self, *args, **kwargs):
        return _fake_history()


@patch("marketsignal.data.yfinance_source.time.sleep")
@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_retries_a_rate_limit_then_succeeds(mock_ticker_cls, mock_sleep):
    ticker = _FlakyInfoTicker([YFRateLimitError(), YFRateLimitError()])
    mock_ticker_cls.return_value = ticker

    financials = fetch_raw_financials("AAPL")

    assert financials.company_name == "Test Company Inc."
    assert ticker.info_call_count == 3
    assert mock_sleep.call_count == 2


@patch("marketsignal.data.yfinance_source.time.sleep")
@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_raises_data_unavailable_after_exhausting_retries(
    mock_ticker_cls, mock_sleep
):
    ticker = _FlakyInfoTicker([YFRateLimitError()] * 5)  # more than the retry budget
    mock_ticker_cls.return_value = ticker

    with pytest.raises(DataUnavailableError):
        fetch_raw_financials("AAPL")

    assert ticker.info_call_count == 3  # the default attempt budget, not 5


@patch("marketsignal.data.yfinance_source.time.sleep")
@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_does_not_retry_a_definitively_missing_ticker(
    mock_ticker_cls, mock_sleep
):
    ticker = _FlakyInfoTicker([RuntimeError("no such ticker")])
    mock_ticker_cls.return_value = ticker

    with pytest.raises(TickerNotFoundError):
        fetch_raw_financials("BOGUS")

    assert ticker.info_call_count == 1  # failed fast, no retries wasted
    mock_sleep.assert_not_called()


class _InfoOkHistoryRaisesTicker:
    """`.info` succeeds but `.history()` fails -- the shape of a partial Yahoo
    outage / rate limit. The research run should still complete."""

    info = FAKE_INFO

    def history(self, *args, **kwargs):
        raise RuntimeError("YFRateLimitError: Too Many Requests. Rate limited.")


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_survives_history_fetch_failure(mock_ticker_cls):
    mock_ticker_cls.return_value = _InfoOkHistoryRaisesTicker()

    financials = fetch_raw_financials("AAPL")

    # core info-derived fields still populated
    assert financials.company_name == "Test Company Inc."
    assert financials.trailing_pe == 22.5
    # price-change fields degrade to None instead of raising
    assert financials.price_change_3mo is None
    assert financials.price_change_6mo is None
    assert financials.price_change_12mo is None


def test_price_change_handles_empty_history():
    from marketsignal.data.yfinance_source import _price_change

    assert _price_change(pd.DataFrame(), 3) is None
    assert _price_change(None, 3) is None


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_price_history_maps_daily_closes(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _fake_history(days=10, start_price=100.0, end_price=110.0)
    mock_ticker_cls.return_value = mock_ticker

    history = fetch_price_history("test")

    mock_ticker.history.assert_called_once_with(period="max")
    assert len(history) == 10
    assert history[0].close == 100.0
    assert history[-1].close == 110.0
    assert history[0].date < history[-1].date  # oldest first


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_price_history_returns_empty_list_for_empty_response(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker

    assert fetch_price_history("BOGUS") == []


class _RaisingHistoryTicker:
    """Mirrors _RaisingTicker above but raises from .history() instead of
    .info, for testing fetch_price_history's independent error path."""

    def history(self, *args, **kwargs):
        raise RuntimeError("boom")


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_price_history_returns_empty_list_when_yfinance_errors(mock_ticker_cls):
    mock_ticker_cls.return_value = _RaisingHistoryTicker()

    assert fetch_price_history("AAPL") == []


class _FlakyHistoryTicker:
    def __init__(self, side_effects):
        self._side_effects = list(side_effects)
        self.call_count = 0

    def history(self, *args, **kwargs):
        self.call_count += 1
        if self._side_effects:
            raise self._side_effects.pop(0)
        return _fake_history(days=5, start_price=10.0, end_price=12.0)


@patch("marketsignal.data.yfinance_source.time.sleep")
@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_price_history_retries_a_transient_network_error_then_succeeds(
    mock_ticker_cls, mock_sleep
):
    ticker = _FlakyHistoryTicker([requests.exceptions.ConnectionError()])
    mock_ticker_cls.return_value = ticker

    history = fetch_price_history("AAPL")

    assert len(history) == 5
    assert ticker.call_count == 2
    mock_sleep.assert_called_once()


@patch("marketsignal.data.yfinance_source.time.sleep")
@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_price_history_gives_up_after_exhausting_retries(mock_ticker_cls, mock_sleep):
    ticker = _FlakyHistoryTicker([requests.exceptions.Timeout()] * 5)
    mock_ticker_cls.return_value = ticker

    assert fetch_price_history("AAPL") == []
    assert ticker.call_count == 3  # the default attempt budget, not 5
