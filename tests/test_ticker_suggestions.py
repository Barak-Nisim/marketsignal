from marketsignal.favorites import add_favorite
from marketsignal.ticker_suggestions import COMMON_TICKERS, build_ticker_suggestions


def test_common_tickers_are_unique_and_labeled():
    symbols = [symbol for symbol, _ in COMMON_TICKERS]

    assert len(symbols) == len(set(symbols))
    assert all(symbol.isupper() and label for symbol, label in COMMON_TICKERS)


def test_suggestions_fall_back_to_the_curated_list_with_no_personal_history(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))

    suggestions = build_ticker_suggestions()

    assert len(suggestions) == len(COMMON_TICKERS)
    assert suggestions[0].symbol == COMMON_TICKERS[0][0]


def test_favorites_come_first_and_are_not_duplicated_by_the_curated_list(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_HISTORY_DIR", str(tmp_path / "history"))
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path / "favorites"))
    add_favorite("aapl")  # already in COMMON_TICKERS
    add_favorite("PLTR")  # not in COMMON_TICKERS

    suggestions = build_ticker_suggestions()
    symbols = [s.symbol for s in suggestions]

    assert symbols[:2] == ["AAPL", "PLTR"]
    assert symbols.count("AAPL") == 1
    assert suggestions[0].label == "Favorite"  # not relabeled by the curated entry
    assert len(suggestions) == len(COMMON_TICKERS) + 1  # only PLTR is new
