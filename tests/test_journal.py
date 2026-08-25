from marketsignal.journal import add_journal_entry, load_journal


def test_load_journal_returns_empty_list_for_unknown_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path))

    assert load_journal("NOPE") == []


def test_add_journal_entry_persists_and_defaults_written_at(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path))

    entry = add_journal_entry("aapl", "Watching for Q2 guidance.")

    assert entry.ticker == "AAPL"
    assert entry.written_at  # defaulted to today, non-empty
    entries = load_journal("AAPL")
    assert len(entries) == 1
    assert entries[0].note == "Watching for Q2 guidance."


def test_add_journal_entry_accepts_explicit_written_at(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path))

    add_journal_entry("AAPL", "First note.", written_at="2026-01-01")
    add_journal_entry("AAPL", "Second note.", written_at="2026-02-01")

    entries = load_journal("AAPL")
    assert [e.written_at for e in entries] == ["2026-01-01", "2026-02-01"]
    assert [e.note for e in entries] == ["First note.", "Second note."]


def test_journal_is_isolated_from_real_user_home(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_JOURNAL_DIR", str(tmp_path))

    add_journal_entry("MSFT", "Test note.")

    assert (tmp_path / "MSFT.json").exists()
