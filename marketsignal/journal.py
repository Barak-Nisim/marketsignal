"""Persists user-authored notes attached to a ticker -- your own reasoning
about a thesis, not AI-generated. Deliberately kept separate from
thesis_history.py, which stores the AI's output, not yours.

Entries live at ~/.marketsignal/journal/<TICKER>.json by default (an
append-only JSON array), outside the repo entirely -- same reasoning as
history.py and thesis_history.py. The location is overridable via
MARKETSIGNAL_JOURNAL_DIR, a separate env var and default subdirectory from
the other two stores so they never collide in tests or in production.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import asdict
from pathlib import Path

from marketsignal.models import JournalEntry


def _journal_dir() -> Path:
    override = os.environ.get("MARKETSIGNAL_JOURNAL_DIR")
    base = Path(override) if override else Path.home() / ".marketsignal" / "journal"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _journal_path(ticker: str) -> Path:
    return _journal_dir() / f"{ticker.upper()}.json"


def load_journal(ticker: str) -> list[JournalEntry]:
    path = _journal_path(ticker)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [JournalEntry(**entry) for entry in raw]


def add_journal_entry(ticker: str, note: str, written_at: str | None = None) -> JournalEntry:
    entries = load_journal(ticker)
    entry = JournalEntry(
        ticker=ticker.upper(),
        note=note,
        written_at=written_at or dt.date.today().isoformat(),
    )
    entries.append(entry)
    path = _journal_path(ticker)
    path.write_text(json.dumps([asdict(e) for e in entries], indent=2), encoding="utf-8")
    return entry
