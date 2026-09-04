import datetime as dt
import json
from dataclasses import replace
from unittest.mock import patch

from marketsignal.cli import main
from marketsignal.data.yfinance_source import TickerNotFoundError
from marketsignal.models import PricePoint, RawFinancials


def _price_series(start_price: float, end_price: float, days: int = 300) -> list[PricePoint]:
    """Daily closes moving linearly from start to end, oldest first, ending today.
    Kept under a year so the default 1Y window keeps both exact endpoints."""
    end = dt.date.today()
    return [
        PricePoint(
            date=(end - dt.timedelta(days=days - 1 - i)).isoformat(),
            close=start_price + (end_price - start_price) * i / (days - 1),
        )
        for i in range(days)
    ]

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

OLD_FINANCIALS = replace(FAKE_FINANCIALS, as_of="2020-01-01", current_price=100)

FAKE_MSFT = replace(
    FAKE_FINANCIALS,
    ticker="MSFT",
    company_name="Microsoft Corporation",
    trailing_pe=32,
    revenue_growth=0.15,
)


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_no_ai_prints_report(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.return_value = FAKE_FINANCIALS

    exit_code = main(["research", "AAPL", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "MarketSignal Research Brief: Apple Inc. (AAPL)" in captured.out
    mock_fetch.assert_called_once_with("AAPL")


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_csv_format_prints_a_data_row_without_fetching_ai(
    mock_fetch, capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.return_value = FAKE_FINANCIALS

    # --format csv is given with no --no-ai; the AI narrator must still never
    # be reached, or this test would need ANTHROPIC_API_KEY / a narrator mock.
    exit_code = main(["research", "AAPL", "--format", "csv"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ticker,company_name" in captured.out
    assert "AAPL,Apple Inc.,Technology" in captured.out


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_json_format_writes_to_output_file(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.return_value = FAKE_FINANCIALS
    output_path = tmp_path / "report.json"

    exit_code = main(["research", "AAPL", "--format", "json", "--output", str(output_path)])

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ticker"] == "AAPL"
    assert payload["sector_comparisons"]  # Technology sector, trailing_pe present


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_writes_to_output_file(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.return_value = FAKE_FINANCIALS
    output_path = tmp_path / "report.md"

    exit_code = main(["research", "AAPL", "--no-ai", "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.exists()
    assert "MarketSignal Research Brief" in output_path.read_text(encoding="utf-8")


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_handles_unknown_ticker_cleanly(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.side_effect = TickerNotFoundError("BOGUS")

    exit_code = main(["research", "BOGUS", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "BOGUS" in captured.err


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_records_history_between_runs(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.return_value = FAKE_FINANCIALS

    main(["research", "AAPL", "--no-ai"])
    second_run_output = tmp_path / "second.md"
    main(["research", "AAPL", "--no-ai", "--output", str(second_run_output)])

    # second run should have a prior snapshot to diff against
    assert "What changed since 2026-01-01" in second_run_output.read_text(encoding="utf-8")


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_shows_outcome_tracking_for_old_signals(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.return_value = OLD_FINANCIALS
    main(["research", "AAPL", "--no-ai"])  # records an old, cheap snapshot

    mock_fetch.return_value = FAKE_FINANCIALS
    exit_code = main(["research", "AAPL", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "How past signals performed" in captured.out
    assert "2020-01-01" in captured.out
    assert "+50.0%" in captured.out  # (150 - 100) / 100


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_omits_outcome_tracking_on_first_run(mock_fetch, capsys, monkeypatch, tmp_path):
    import datetime as dt

    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    # a realistic "just researched right now" snapshot, unlike FAKE_FINANCIALS'
    # hardcoded past as_of, so it's correctly too recent to show an outcome
    todays_financials = replace(FAKE_FINANCIALS, as_of=dt.date.today().isoformat())
    mock_fetch.return_value = todays_financials

    exit_code = main(["research", "AAPL", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "How past signals performed" not in captured.out


@patch("marketsignal.ai.narrator.generate_narrative")
@patch("marketsignal.cli.fetch_raw_financials")
def test_research_shows_thesis_delta_on_second_ai_run(
    mock_fetch, mock_narrate, capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path / "thesis"))
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
    main(["research", "AAPL"])

    mock_narrate.return_value = _narrative("Product launch")
    exit_code = main(["research", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "What changed in the thesis since 2026-01-01" in captured.out
    assert "(new) Product launch" in captured.out
    assert "(dropped) Earnings report" in captured.out


@patch("marketsignal.ai.narrator.generate_narrative")
@patch("marketsignal.cli.fetch_raw_financials")
def test_research_shows_claim_accuracy_and_track_record(
    mock_fetch, mock_narrate, capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path / "thesis"))
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
    main(["research", "AAPL"])

    mock_narrate.return_value = second_narrative
    exit_code = main(["research", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "## Track record" in captured.out
    assert "1 of 1 judged fundamental claims held up (100%)" in captured.out
    assert "### Claim accuracy check" in captured.out
    assert "**Held up** -- High P/E" in captured.out


@patch("marketsignal.cli.fetch_raw_financials")
def test_compare_prints_a_side_by_side_table(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.side_effect = [FAKE_FINANCIALS, FAKE_MSFT]

    exit_code = main(["compare", "AAPL", "MSFT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# Comparing AAPL vs. MSFT" in captured.out
    assert "AAPL (Apple Inc.)" in captured.out
    assert "MSFT (Microsoft Corporation)" in captured.out
    assert "## By category" in captured.out
    mock_fetch.assert_any_call("AAPL")
    mock_fetch.assert_any_call("MSFT")


@patch("marketsignal.cli.fetch_raw_financials")
def test_compare_writes_to_output_file(mock_fetch, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.side_effect = [FAKE_FINANCIALS, FAKE_MSFT]
    output_path = tmp_path / "compare.md"

    exit_code = main(["compare", "AAPL", "MSFT", "--output", str(output_path)])

    assert exit_code == 0
    assert "Comparing AAPL vs. MSFT" in output_path.read_text(encoding="utf-8")


@patch("marketsignal.cli.fetch_raw_financials")
def test_compare_stops_cleanly_when_the_first_ticker_is_unknown(
    mock_fetch, capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path))
    mock_fetch.side_effect = TickerNotFoundError("BOGUS")

    exit_code = main(["compare", "BOGUS", "MSFT"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Could not find market data for ticker 'BOGUS'" in captured.err
    mock_fetch.assert_called_once_with("BOGUS")  # never reaches the second ticker


def test_favorites_list_when_empty(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    exit_code = main(["favorites", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No favorites yet." in captured.err


def test_favorites_add_and_list(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    main(["favorites", "add", "aapl"])
    exit_code = main(["favorites", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AAPL" in captured.out


def test_favorites_remove(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))
    main(["favorites", "add", "AAPL"])

    main(["favorites", "remove", "AAPL"])
    exit_code = main(["favorites", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No favorites yet." in captured.err


def test_journal_list_when_empty(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path))

    exit_code = main(["journal", "list", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No journal entries for AAPL yet." in captured.err


def test_journal_add_and_list(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path))

    main(["journal", "add", "aapl", "Watching for Q2 guidance."])
    exit_code = main(["journal", "list", "AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Watching for Q2 guidance." in captured.out


@patch("marketsignal.cli.fetch_raw_financials")
def test_research_shows_journal_entries(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path / "journal"))
    mock_fetch.return_value = FAKE_FINANCIALS
    main(["journal", "add", "AAPL", "Watching for Q2 guidance."])

    exit_code = main(["research", "AAPL", "--no-ai"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "## Your journal" in captured.out
    assert "Watching for Q2 guidance." in captured.out


FAKE_MSFT = RawFinancials(
    ticker="MSFT",
    company_name="Microsoft Corporation",
    sector="Technology",
    industry="Software",
    as_of="2026-01-01",
    current_price=400,
    trailing_pe=30,
    revenue_growth=0.15,
)


def test_portfolio_list_when_empty(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    exit_code = main(["portfolio", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No portfolios yet." in captured.err


def test_portfolio_create_and_list(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    main(["portfolio", "create", "Growth Picks", "aapl", "msft"])
    exit_code = main(["portfolio", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Growth Picks: AAPL, MSFT" in captured.out


def test_portfolio_delete(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))
    main(["portfolio", "create", "Growth Picks", "AAPL"])

    main(["portfolio", "delete", "Growth Picks"])
    exit_code = main(["portfolio", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No portfolios yet." in captured.err


@patch("marketsignal.cli.fetch_raw_financials")
def test_portfolio_review_prints_aggregate_and_holdings(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path / "portfolios"))
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    main(["portfolio", "create", "Growth Picks", "AAPL", "MSFT"])
    mock_fetch.side_effect = [FAKE_FINANCIALS, FAKE_MSFT]

    exit_code = main(["portfolio", "review", "Growth Picks"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# Growth Picks" in captured.out
    assert "Portfolio signal:" in captured.out
    assert "Technology: 2 (100%)" in captured.out
    assert "AAPL (Apple Inc.)" in captured.out
    assert "MSFT (Microsoft Corporation)" in captured.out


@patch("marketsignal.cli.fetch_raw_financials")
def test_portfolio_review_handles_one_bad_ticker(mock_fetch, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path / "portfolios"))
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    main(["portfolio", "create", "Mixed", "AAPL", "BOGUS"])
    mock_fetch.side_effect = [FAKE_FINANCIALS, TickerNotFoundError("BOGUS")]

    exit_code = main(["portfolio", "review", "Mixed"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Could not fetch data for: BOGUS" in captured.out
    assert "AAPL (Apple Inc.)" in captured.out


def test_portfolio_review_unknown_name_returns_error(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    exit_code = main(["portfolio", "review", "Nope"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No portfolio named 'Nope'." in captured.err


@patch("marketsignal.cli.fetch_price_history")
def test_portfolio_performance_prints_totals_and_holdings(
    mock_history, capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))
    main(["portfolio", "create", "Movers", "AAPL", "MSFT"])
    mock_history.side_effect = [
        _price_series(100.0, 150.0),  # AAPL up 50%
        _price_series(200.0, 180.0),  # MSFT down 10%
    ]

    exit_code = main(["portfolio", "performance", "Movers", "--period", "1Y"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# Movers -- 1Y performance" in captured.out
    assert "Every holding valued at 100 shares." in captured.out
    assert "Portfolio value:" in captured.out
    assert "1 up, 1 down, 0 flat" in captured.out
    assert "AAPL: 100.00 -> 150.00 (+50.0%)" in captured.out
    assert "MSFT: 200.00 -> 180.00 (-10.0%)" in captured.out
    # sorted best to worst
    assert captured.out.index("AAPL:") < captured.out.index("MSFT:")


@patch("marketsignal.cli.fetch_price_history")
def test_portfolio_performance_excludes_ticker_with_no_history(
    mock_history, capsys, monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))
    main(["portfolio", "create", "Partial", "AAPL", "BOGUS"])
    mock_history.side_effect = [_price_series(100.0, 120.0), []]

    exit_code = main(["portfolio", "performance", "Partial"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AAPL: 100.00 -> 120.00" in captured.out
    assert "Excluded (too little price history in the window): BOGUS" in captured.out


def test_portfolio_performance_unknown_name_returns_error(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    exit_code = main(["portfolio", "performance", "Nope"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No portfolio named 'Nope'." in captured.err
