import datetime as dt
from dataclasses import replace
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


def test_landing_page_has_a_working_research_form():
    response = client.get("/")

    assert response.status_code == 200
    assert "MarketSignal" in response.text
    assert "What company do you want to research?" in response.text
    assert 'action="/research"' in response.text
    assert 'name="ticker"' in response.text
    assert "AAPL" in response.text and "NVDA" in response.text
    assert 'name="use_ai"' not in response.text  # AI toggle is /app-only, not on the landing page


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


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_shows_outcome_tracking_for_old_signals(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    old_financials = replace(FAKE_FINANCIALS, as_of="2020-01-01", current_price=100)
    mock_fetch.return_value = old_financials
    client.post("/research", data={"ticker": "AAPL"})  # records an old, cheap snapshot

    mock_fetch.return_value = FAKE_FINANCIALS
    response = client.post("/research", data={"ticker": "AAPL"})

    assert response.status_code == 200
    assert "How past signals performed" in response.text
    assert "2020-01-01" in response.text
    assert "+50.0%" in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_omits_outcome_tracking_on_first_run(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    todays_financials = replace(FAKE_FINANCIALS, as_of=dt.date.today().isoformat())
    mock_fetch.return_value = todays_financials

    response = client.post("/research", data={"ticker": "AAPL"})

    assert response.status_code == 200
    assert "How past signals performed" not in response.text


@patch("marketsignal.ai.narrator.generate_narrative")
@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_shows_thesis_delta_on_second_ai_run(
    mock_fetch, mock_narrate, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path / "thesis"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_fetch.return_value = FAKE_FINANCIALS

    def _narrative(catalyst):
        return {
            "bull_case": "Strong growth.",
            "bear_case": "Rich valuation.",
            "confidence": "Medium",
            "key_evidence": ["Valuation"],
            "catalysts": [{"catalyst": catalyst, "claim_type": "Fact", "based_on": "Growth"}],
            "risk_factors": [
                {"factor": "High P/E", "claim_type": "Fact", "based_on": "Valuation"}
            ],
            "what_would_change_my_mind": ["If revenue growth turns negative"],
        }

    mock_narrate.return_value = _narrative("Earnings report")
    client.post("/research", data={"ticker": "AAPL", "use_ai": "1"})

    mock_narrate.return_value = _narrative("Product launch")
    response = client.post("/research", data={"ticker": "AAPL", "use_ai": "1"})

    assert response.status_code == 200
    assert "What changed in the thesis since 2026-01-01" in response.text
    assert "Product launch" in response.text
    assert "Earnings report" in response.text
    assert "thesis-delta-added" in response.text
    assert "thesis-delta-removed" in response.text


@patch("marketsignal.ai.narrator.generate_narrative")
@patch("marketsignal.web.app.fetch_raw_financials")
def test_research_shows_claim_accuracy_and_track_record(
    mock_fetch, mock_narrate, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path / "thesis"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
    mock_fetch.return_value = FAKE_FINANCIALS

    first_narrative = {
        "bull_case": "Strong growth.",
        "bear_case": "Rich valuation.",
        "confidence": "Medium",
        "key_evidence": ["Valuation"],
        "catalysts": [],
        "risk_factors": [
            {"factor": "High P/E", "claim_type": "Fact", "based_on": "Valuation"}
        ],
        "what_would_change_my_mind": [],
    }
    second_narrative = {
        **first_narrative,
        "claim_accuracy_check": [
            {"claim": "High P/E", "status": "Held up", "explanation": "P/E is still elevated."}
        ],
    }

    mock_narrate.return_value = first_narrative
    client.post("/research", data={"ticker": "AAPL", "use_ai": "1"})

    mock_narrate.return_value = second_narrative
    response = client.post("/research", data={"ticker": "AAPL", "use_ai": "1"})

    assert response.status_code == 200
    assert "Track record" in response.text
    assert "1 of 1 judged fundamental claims" in response.text
    assert "claim-status-held-up" in response.text
    assert "P/E is still elevated." in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_journal_add_then_shows_on_report(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path / "journal"))
    mock_fetch.return_value = FAKE_FINANCIALS

    add_response = client.post(
        "/journal/add",
        data={"ticker": "aapl", "note": "Watching for Q2 guidance."},
        follow_redirects=False,
    )
    assert add_response.status_code == 303
    assert add_response.headers["location"] == "/app?ticker=AAPL"

    response = client.post("/research", data={"ticker": "AAPL"})

    assert response.status_code == 200
    assert "Watching for Q2 guidance." in response.text


@patch("marketsignal.web.app.fetch_raw_financials")
def test_journal_ignores_blank_note(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path / "journal"))
    mock_fetch.return_value = FAKE_FINANCIALS

    client.post("/journal/add", data={"ticker": "AAPL", "note": "   "}, follow_redirects=False)
    response = client.post("/research", data={"ticker": "AAPL"})

    assert "No notes yet" in response.text
