"""Persists a small list of favorited tickers for quick access and trend
tracking on the /app page.

Mirrors history.py's storage pattern: ~/.marketsignal/favorites.json by
default, outside the repo entirely, overridable via
MARKETSIGNAL_FAVORITES_DIR so tests never touch a real user's home
directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _favorites_dir() -> Path:
    override = os.environ.get("MARKETSIGNAL_FAVORITES_DIR")
    base = Path(override) if override else Path.home() / ".marketsignal"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _favorites_path() -> Path:
    return _favorites_dir() / "favorites.json"


def list_favorites() -> list[str]:
    path = _favorites_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_favorites(tickers: list[str]) -> None:
    _favorites_path().write_text(json.dumps(tickers, indent=2), encoding="utf-8")


def add_favorite(ticker: str) -> list[str]:
    ticker = ticker.upper()
    favorites = list_favorites()
    if ticker not in favorites:
        favorites.append(ticker)
        _save_favorites(favorites)
    return favorites


def remove_favorite(ticker: str) -> list[str]:
    ticker = ticker.upper()
    favorites = [t for t in list_favorites() if t != ticker]
    _save_favorites(favorites)
    return favorites


def is_favorite(ticker: str) -> bool:
    return ticker.upper() in list_favorites()
