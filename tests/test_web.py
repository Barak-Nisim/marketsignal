from unittest.mock import patch

from fastapi.testclient import TestClient

from marketsignal.data.yfinance_source import TickerNotFoundError
from marketsignal.models import RawFinancials
from marketsignal.web.app import app

client = TestClient(app)

FAKE_FINANCIALS = RawFinancials(
    ticker="AAPL",
    company_name="Apple Inc.",
    sector="Technology",
    industry="Consumer Electronics",
    as_of="2026-01-01",
    current_price=150,
    fifty_two_week_low=120,
    fifty_two_week_high=160,
    trailing_pe=28,
    revenue_growth=0.08,
)


def test_landing_page_shows_marketing_content():
    response = client.get("/")

    assert response.status_code == 200
    assert "MarketSignal" in response.text
    assert "Try the live demo" in response.text
    assert 'name="ticker"' not in response.text


def test_how_it_works_page_explains_methodology():
    response = client.get("/how-it-works")

    assert response.status_code == 200
    assert "How MarketSignal works" in response.text


def test_app_form_shows_ticker_input(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))

    response = client.get("/app")

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="ticker"' in response.text


def test_app_form_shows_no_recent_tickers_when_history_is_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))

    response = client.get("/app")

    assert "Recently researched" not in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_app_form_lists_recently_researched_tickers_after_a_run(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.return_value = FAKE_FINANCIALS

    client.post("/research", data={"ticker": "AAPL"})
    response = client.get("/app")

    assert "Recently researched" in response.text
    assert "/app?ticker=AAPL" in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_renders_report(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.return_value = FAKE_FINANCIALS

    response = client.post("/research", data={"ticker": "AAPL"})

    assert response.status_code == 200
    assert "Apple Inc. (AAPL)" in response.text
    assert "Category scores" in response.text
    assert "Thesis" not in response.text  # no AI requested


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_with_unknown_ticker_shows_error(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.side_effect = TickerNotFoundError("BOGUS")

    response = client.post("/research", data={"ticker": "BOGUS"})

    assert response.status_code == 200
    assert "Could not find market data" in response.text
    assert "<form" in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_ai_checkbox_ignored_without_api_key(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    mock_fetch.return_value = FAKE_FINANCIALS

    response = client.post("/research", data={"ticker": "AAPL", "use_ai": "1"})

    assert response.status_code == 200
    assert "Thesis" not in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_shows_what_changed_on_second_run(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.return_value = FAKE_FINANCIALS

    client.post("/research", data={"ticker": "AAPL"})
    response = client.post("/research", data={"ticker": "AAPL"})

    assert "What changed since 2026-01-01" in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_shows_a_trend_sparkline_on_second_run(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.return_value = FAKE_FINANCIALS

    first = client.post("/research", data={"ticker": "AAPL"})
    second = client.post("/research", data={"ticker": "AAPL"})

    assert "<svg" not in first.text or "sparkline" not in first.text  # only 1 point yet
    assert "sparkline" in second.text
    assert "Signal trend" in second.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_favorite_toggle_appears_on_report_and_adds_ticker(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.return_value = FAKE_FINANCIALS

    response = client.post("/research", data={"ticker": "AAPL"})
    assert "Add to favorites" in response.text
    assert "Remove from favorites" not in response.text

    client.post("/favorites/add", data={"ticker": "AAPL"}, follow_redirects=False)
    response = client.post("/research", data={"ticker": "AAPL"})

    assert "Remove from favorites" in response.text


def test_favorites_add_and_remove_via_web(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))

    add_response = client.post(
        "/favorites/add", data={"ticker": "aapl"}, follow_redirects=False
    )
    assert add_response.status_code == 303
    assert add_response.headers["location"] == "/app"

    app_response = client.get("/app")
    assert "Favorites" in app_response.text
    assert "AAPL" in app_response.text
    assert "Not researched yet" in app_response.text

    client.post("/favorites/remove", data={"ticker": "AAPL"}, follow_redirects=False)
    app_response = client.get("/app")

    assert "favorites-panel" not in app_response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_favorite_with_history_shows_tier_and_sparkline_on_app_page(
    mock_fetch, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    mock_fetch.return_value = FAKE_FINANCIALS

    client.post("/research", data={"ticker": "AAPL"})
    client.post("/research", data={"ticker": "AAPL"})
    client.post("/favorites/add", data={"ticker": "AAPL"}, follow_redirects=False)

    response = client.get("/app")

    assert "Not researched yet" not in response.text
    assert "sparkline" in response.text
