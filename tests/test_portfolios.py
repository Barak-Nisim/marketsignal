from marketsignal.portfolios import (
    delete_portfolio,
    get_portfolio,
    list_portfolios,
    save_portfolio,
    slugify,
)


def test_slugify_normalizes_name():
    assert slugify("Growth Picks") == "growth-picks"
    assert slugify("  Core / Holdings!! ") == "core-holdings"
    assert slugify("") == "portfolio"


def test_save_and_get_portfolio_normalizes_tickers(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    saved = save_portfolio("Growth Picks", ["aapl", "MSFT", "aapl", " amzn "])

    assert saved.name == "Growth Picks"
    assert saved.tickers == ("AAPL", "MSFT", "AMZN")  # deduped, uppercased, order preserved

    loaded = get_portfolio("Growth Picks")
    assert loaded == saved


def test_get_portfolio_returns_none_for_unknown_name(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    assert get_portfolio("Nope") is None


def test_save_portfolio_upserts(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    save_portfolio("Growth Picks", ["AAPL"])
    save_portfolio("Growth Picks", ["AAPL", "NVDA"])

    assert get_portfolio("Growth Picks").tickers == ("AAPL", "NVDA")
    assert len(list_portfolios()) == 1


def test_list_portfolios_returns_all_saved(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    save_portfolio("Growth Picks", ["AAPL"])
    save_portfolio("Core Holdings", ["KO", "JNJ"])

    names = {p.name for p in list_portfolios()}
    assert names == {"Growth Picks", "Core Holdings"}


def test_delete_portfolio_removes_it(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))
    save_portfolio("Growth Picks", ["AAPL"])

    delete_portfolio("Growth Picks")

    assert get_portfolio("Growth Picks") is None
    assert list_portfolios() == []


def test_delete_portfolio_is_a_no_op_for_unknown_name(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    delete_portfolio("Nope")  # should not raise


def test_portfolios_are_isolated_from_real_user_home(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_PORTFOLIOS_DIR", str(tmp_path))

    save_portfolio("Growth Picks", ["AAPL"])

    assert (tmp_path / "growth-picks.json").exists()
