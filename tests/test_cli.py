from dataclasses import replace
from unittest.mock import patch

from marketsignal.cli import main
from marketsignal.data.yfinance_source import TickerNotFoundError
from marketsignal.models import RawFinancials

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
