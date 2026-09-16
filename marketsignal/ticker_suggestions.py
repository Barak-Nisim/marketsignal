"""Builds the ticker suggestion list behind the research form's autocomplete.

Feeds a plain HTML5 `<datalist>` on the /app research form -- no JS, no
typeahead library, and no ticker-lookup API call. The browser does the
matching itself, so this is a static server-rendered list rather than a
live search: a ticker that isn't here can still be typed in and researched
exactly as before, which is why the curated set below doesn't try to be
exhaustive.

Ordering is the whole point of the module. The user's own favorites come
first, then tickers they've actually researched recently (both already
persisted by favorites.py and history.py), and only then the curated
common-ticker set -- so real personal usage surfaces above a generic list
of large caps. Browsers render datalist options in document order, so the
order here is the order the user sees.
"""

from __future__ import annotations

from dataclasses import dataclass

from marketsignal.favorites import list_favorites
from marketsignal.history import list_recent_tickers

# A deliberately partial set of widely-held US large caps and index/sector
# ETFs -- enough that a first-time user with no history sees useful
# suggestions, without pretending to be a complete symbol directory. The
# label is what the browser shows next to the symbol in the dropdown.
COMMON_TICKERS: tuple[tuple[str, str], ...] = (
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("NVDA", "NVIDIA Corporation"),
    ("GOOGL", "Alphabet Inc."),
    ("AMZN", "Amazon.com Inc."),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("AVGO", "Broadcom Inc."),
    ("BRK-B", "Berkshire Hathaway Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("V", "Visa Inc."),
    ("MA", "Mastercard Inc."),
    ("UNH", "UnitedHealth Group Inc."),
    ("XOM", "Exxon Mobil Corporation"),
    ("CVX", "Chevron Corporation"),
    ("JNJ", "Johnson & Johnson"),
    ("LLY", "Eli Lilly and Company"),
    ("PFE", "Pfizer Inc."),
    ("MRK", "Merck & Co. Inc."),
    ("ABBV", "AbbVie Inc."),
    ("PG", "Procter & Gamble Company"),
    ("KO", "Coca-Cola Company"),
    ("PEP", "PepsiCo Inc."),
    ("COST", "Costco Wholesale Corporation"),
    ("WMT", "Walmart Inc."),
    ("HD", "Home Depot Inc."),
    ("MCD", "McDonald's Corporation"),
    ("NKE", "Nike Inc."),
    ("DIS", "Walt Disney Company"),
    ("NFLX", "Netflix Inc."),
    ("CRM", "Salesforce Inc."),
    ("ORCL", "Oracle Corporation"),
    ("ADBE", "Adobe Inc."),
    ("AMD", "Advanced Micro Devices Inc."),
    ("INTC", "Intel Corporation"),
    ("QCOM", "Qualcomm Inc."),
    ("TXN", "Texas Instruments Inc."),
    ("CSCO", "Cisco Systems Inc."),
    ("IBM", "International Business Machines"),
    ("BAC", "Bank of America Corporation"),
    ("WFC", "Wells Fargo & Company"),
    ("GS", "Goldman Sachs Group Inc."),
    ("MS", "Morgan Stanley"),
    ("BA", "Boeing Company"),
    ("CAT", "Caterpillar Inc."),
    ("GE", "General Electric Company"),
    ("HON", "Honeywell International Inc."),
    ("UPS", "United Parcel Service Inc."),
    ("T", "AT&T Inc."),
    ("VZ", "Verizon Communications Inc."),
    ("UBER", "Uber Technologies Inc."),
    ("PYPL", "PayPal Holdings Inc."),
    ("SBUX", "Starbucks Corporation"),
    ("SPY", "SPDR S&P 500 ETF Trust"),
    ("VOO", "Vanguard S&P 500 ETF"),
    ("VTI", "Vanguard Total Stock Market ETF"),
    ("QQQ", "Invesco QQQ Trust"),
    ("IWM", "iShares Russell 2000 ETF"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF"),
    ("VEA", "Vanguard FTSE Developed Markets ETF"),
    ("VWO", "Vanguard FTSE Emerging Markets ETF"),
    ("AGG", "iShares Core U.S. Aggregate Bond ETF"),
    ("BND", "Vanguard Total Bond Market ETF"),
    ("SCHD", "Schwab U.S. Dividend Equity ETF"),
    ("XLK", "Technology Select Sector SPDR Fund"),
    ("XLF", "Financial Select Sector SPDR Fund"),
    ("XLE", "Energy Select Sector SPDR Fund"),
    ("GLD", "SPDR Gold Shares"),
)


@dataclass(frozen=True)
class TickerSuggestion:
    symbol: str
    label: str


def build_ticker_suggestions(recent_limit: int = 12) -> list[TickerSuggestion]:
    """Returns favorites, then recently researched tickers, then the curated
    common set, deduplicated by symbol with the first (most personal)
    occurrence winning so a favorited ticker keeps its "Favorite" label
    rather than being relabeled by a later source."""
    suggestions: list[TickerSuggestion] = []
    seen: set[str] = set()

    def _add(symbol: str, label: str) -> None:
        symbol = symbol.upper()
        if symbol not in seen:
            seen.add(symbol)
            suggestions.append(TickerSuggestion(symbol=symbol, label=label))

    for ticker in list_favorites():
        _add(ticker, "Favorite")

    for snapshot in list_recent_tickers(limit=recent_limit):
        _add(snapshot.ticker, "Recently researched")

    for symbol, name in COMMON_TICKERS:
        _add(symbol, name)

    return suggestions
