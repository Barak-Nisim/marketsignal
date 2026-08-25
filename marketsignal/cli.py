"""MarketSignal CLI: marketsignal research <TICKER> [options]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from marketsignal.data.yfinance_source import TickerNotFoundError, fetch_raw_financials
from marketsignal.favorites import add_favorite, list_favorites, remove_favorite
from marketsignal.history import record_and_diff
from marketsignal.report.markdown import render
from marketsignal.scoring import score_financials


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marketsignal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser("research", help="Research a US stock or ETF ticker")
    research.add_argument("ticker", help="Ticker symbol, e.g. AAPL")
    research.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip the AI thesis and render the deterministic report only",
    )
    research.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Write the report to a file instead of stdout",
    )

    serve = subparsers.add_parser("serve", help="Run the MarketSignal web UI locally")
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8001, help="Bind port (default: 8001)")
    serve.add_argument("--reload", action="store_true", help="Auto-reload on code changes")

    favorites = subparsers.add_parser("favorites", help="Manage the favorited ticker list")
    favorites_action = favorites.add_subparsers(dest="favorites_action", required=True)
    favorites_action.add_parser("list", help="List favorited tickers")
    add_parser = favorites_action.add_parser("add", help="Add a ticker to favorites")
    add_parser.add_argument("ticker")
    remove_parser = favorites_action.add_parser("remove", help="Remove a ticker from favorites")
    remove_parser.add_argument("ticker")

    return parser


def _run_research(args: argparse.Namespace) -> int:
    try:
        financials = fetch_raw_financials(args.ticker)
    except TickerNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    result = score_financials(financials)
    what_changed = record_and_diff(result)

    ai_narrative = None
    if not args.no_ai:
        from marketsignal.ai.narrator import generate_narrative

        ai_narrative = generate_narrative(result, what_changed)

    report = render(result, what_changed=what_changed, ai_narrative=ai_narrative)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    return 0


def _run_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("marketsignal.web.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def _run_favorites(args: argparse.Namespace) -> int:
    if args.favorites_action == "list":
        favorites = list_favorites()
        if not favorites:
            print("No favorites yet.", file=sys.stderr)
        else:
            for ticker in favorites:
                print(ticker)
    elif args.favorites_action == "add":
        add_favorite(args.ticker)
        print(f"Added {args.ticker.upper()} to favorites.", file=sys.stderr)
    elif args.favorites_action == "remove":
        remove_favorite(args.ticker)
        print(f"Removed {args.ticker.upper()} from favorites.", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "research":
        return _run_research(args)
    if args.command == "serve":
        return _run_serve(args)
    if args.command == "favorites":
        return _run_favorites(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
