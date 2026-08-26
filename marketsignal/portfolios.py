"""Persists named lists of tickers for portfolio review.

Mirrors favorites.py/journal.py's storage pattern: one JSON file per
portfolio at ~/.marketsignal/portfolios/<slug>.json by default, outside
the repo entirely, overridable via MARKETSIGNAL_PORTFOLIOS_DIR -- a
separate env var and default subdirectory from the other three stores
(history, favorites, journal, thesis_history) so they never collide in
tests or in production.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from pathlib import Path

from marketsignal.models import Portfolio


def _portfolios_dir() -> Path:
    override = os.environ.get("MARKETSIGNAL_PORTFOLIOS_DIR")
    base = Path(override) if override else Path.home() / ".marketsignal" / "portfolios"
    base.mkdir(parents=True, exist_ok=True)
    return base


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "portfolio"


def _portfolio_path_for_slug(slug: str) -> Path:
    return _portfolios_dir() / f"{slug}.json"


def _portfolio_path(name: str) -> Path:
    return _portfolio_path_for_slug(slugify(name))


def _load(path: Path) -> Portfolio | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Portfolio(name=raw["name"], tickers=tuple(raw["tickers"]))


def list_portfolios() -> list[Portfolio]:
    portfolios = []
    for path in sorted(_portfolios_dir().glob("*.json")):
        portfolio = _load(path)
        if portfolio:
            portfolios.append(portfolio)
    return portfolios


def get_portfolio(name: str) -> Portfolio | None:
    return _load(_portfolio_path(name))


def get_portfolio_by_slug(slug: str) -> Portfolio | None:
    """Looks up a portfolio directly by its URL slug, without needing the
    human-readable name -- used by web routes, where only the slug (from
    the URL path) is available."""
    return _load(_portfolio_path_for_slug(slug))


def save_portfolio(name: str, tickers: list[str]) -> Portfolio:
    seen: set[str] = set()
    normalized: list[str] = []
    for ticker in tickers:
        upper = ticker.strip().upper()
        if upper and upper not in seen:
            seen.add(upper)
            normalized.append(upper)

    portfolio = Portfolio(name=name.strip(), tickers=tuple(normalized))
    _portfolio_path(name).write_text(json.dumps(asdict(portfolio), indent=2), encoding="utf-8")
    return portfolio


def delete_portfolio(name: str) -> None:
    delete_portfolio_by_slug(slugify(name))


def delete_portfolio_by_slug(slug: str) -> None:
    path = _portfolio_path_for_slug(slug)
    if path.exists():
        path.unlink()
