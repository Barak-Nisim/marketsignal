from marketsignal.favorites import add_favorite, is_favorite, list_favorites, remove_favorite


def test_list_favorites_is_empty_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    assert list_favorites() == []


def test_add_favorite_persists_and_uppercases_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    add_favorite("aapl")

    assert list_favorites() == ["AAPL"]
    assert (tmp_path / "favorites.json").exists()


def test_add_favorite_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    add_favorite("AAPL")
    add_favorite("AAPL")

    assert list_favorites() == ["AAPL"]


def test_add_multiple_favorites_preserves_order(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    add_favorite("AAPL")
    add_favorite("MSFT")

    assert list_favorites() == ["AAPL", "MSFT"]


def test_remove_favorite(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))
    add_favorite("AAPL")
    add_favorite("MSFT")

    remove_favorite("aapl")

    assert list_favorites() == ["MSFT"]


def test_remove_favorite_not_in_list_is_a_no_op(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))
    add_favorite("AAPL")

    remove_favorite("MSFT")

    assert list_favorites() == ["AAPL"]


def test_is_favorite(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))
    add_favorite("AAPL")

    assert is_favorite("aapl") is True
    assert is_favorite("MSFT") is False


def test_favorites_storage_is_isolated_from_real_user_home(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_FAVORITES_DIR", str(tmp_path))

    add_favorite("AAPL")

    assert (tmp_path / "favorites.json").exists()
