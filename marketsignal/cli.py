"""MarketSignal CLI: marketsignal research <TICKER> [options]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from marketsignal.accuracy import compute_accuracy_summary
from marketsignal.data.yfinance_source import TickerNotFoundError, fetch_raw_financials
from marketsignal.favorites import add_favorite, list_favorites, remove_favorite
from marketsignal.history import load_history, record_and_diff
from marketsignal.journal import add_journal_entry, load_journal
from marketsignal.outcomes import compute_outcomes
from marketsignal.portfolio_review import build_portfolio_review
from marketsignal.portfolios import (
    delete_portfolio,
    get_portfolio,
    list_portfolios,
    save_portfolio,
)
from marketsignal.report.markdown import render
from marketsignal.scoring import score_financials, tier_for_score
from marketsignal.thesis_history import (
    load_thesis_history,
    previous_claims,
    previous_invalidation_conditions,
    record_thesis_and_diff,
)


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

    journal = subparsers.add_parser("journal", help="Manage your own notes on a ticker")
    journal_action = journal.add_subparsers(dest="journal_action", required=True)
    journal_add = journal_action.add_parser("add", help="Add a note to a ticker's journal")
    journal_add.add_argument("ticker")
    journal_add.add_argument("note")
    journal_list = journal_action.add_parser("list", help="List a ticker's journal entries")
    journal_list.add_argument("ticker")

    portfolio = subparsers.add_parser("portfolio", help="Manage and review saved portfolios")
    portfolio_action = portfolio.add_subparsers(dest="portfolio_action", required=True)
    portfolio_create = portfolio_action.add_parser("create", help="Create or replace a portfolio")
    portfolio_create.add_argument("name")
    portfolio_create.add_argument("tickers", nargs="+", help="One or more ticker symbols")
    portfolio_action.add_parser("list", help="List saved portfolios")
    portfolio_review = portfolio_action.add_parser("review", help="Review a saved portfolio")
    portfolio_review.add_argument("name")
    portfolio_delete = portfolio_action.add_parser("delete", help="Delete a saved portfolio")
    portfolio_delete.add_argument("name")

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
    thesis_delta = None
    accuracy_summary = None
    if not args.no_ai:
        from marketsignal.ai.narrator import generate_narrative

        prior_conditions = previous_invalidation_conditions(financials.ticker)
        prior_claims = previous_claims(financials.ticker)
        ai_narrative = generate_narrative(result, what_changed, prior_conditions, prior_claims)
        thesis_delta = record_thesis_and_diff(financials.ticker, financials.as_of, ai_narrative)
        accuracy_summary = compute_accuracy_summary(load_thesis_history(financials.ticker))

    report = render(result, what_changed=what_changed, ai_narrative=ai_narrative)

    if accuracy_summary and accuracy_summary.judged:
        pct = accuracy_summary.accuracy_pct
        report += (
            f"\n\n## Track record\n\n{accuracy_summary.held_up} of {accuracy_summary.judged} "
            f"judged fundamental claims held up ({pct * 100:.0f}%)"
        )
        if accuracy_summary.too_early_to_tell:
            report += f", {accuracy_summary.too_early_to_tell} too early to tell"
        report += ".\n"

    if thesis_delta:
        report += f"\n\n## What changed in the thesis since {thesis_delta.previous_as_of}\n\n"
        if thesis_delta.confidence_before != thesis_delta.confidence_after:
            report += (
                f"Confidence: {thesis_delta.confidence_before} -> "
                f"{thesis_delta.confidence_after}\n\n"
            )
        for label, added, removed in (
            ("Catalysts", thesis_delta.catalysts_added, thesis_delta.catalysts_removed),
            ("Risk factors", thesis_delta.risks_added, thesis_delta.risks_removed),
            (
                "What would change this view",
                thesis_delta.invalidation_added,
                thesis_delta.invalidation_removed,
            ),
        ):
            if not added and not removed:
                continue
            report += f"**{label}:**\n"
            for item in added:
                report += f"- (new) {item}\n"
            for item in removed:
                report += f"- (dropped) {item}\n"
            report += "\n"

    outcomes = compute_outcomes(load_history(financials.ticker), financials.current_price)
    if outcomes:
        report += "\n\n## How past signals performed\n\n"
        report += "| Signal date | Signal was | Since then | Price move |\n"
        report += "|---|---|---|---|\n"
        for o in outcomes:
            if o.overall_score is not None:
                score_text = f"{o.overall_score:.2f} ({o.tier_at_signal})"
            else:
                score_text = "n/a"
            report += (
                f"| {o.as_of} | {score_text} | {o.horizon_label} ({o.days_elapsed}d) "
                f"| {o.pct_change * 100:+.1f}% |\n"
            )

    journal_entries = load_journal(financials.ticker)
    if journal_entries:
        report += "\n\n## Your journal\n\n"
        for entry in journal_entries:
            report += f"- **{entry.written_at}:** {entry.note}\n"

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


def _run_journal(args: argparse.Namespace) -> int:
    if args.journal_action == "add":
        entry = add_journal_entry(args.ticker, args.note)
        print(f"Added journal entry for {entry.ticker} ({entry.written_at}).", file=sys.stderr)
    elif args.journal_action == "list":
        entries = load_journal(args.ticker)
        if not entries:
            print(f"No journal entries for {args.ticker.upper()} yet.", file=sys.stderr)
        else:
            for entry in entries:
                print(f"{entry.written_at}: {entry.note}")

    return 0


def _run_portfolio(args: argparse.Namespace) -> int:
    if args.portfolio_action == "create":
        portfolio = save_portfolio(args.name, args.tickers)
        print(
            f"Saved portfolio '{portfolio.name}' with {len(portfolio.tickers)} "
            f"ticker(s): {', '.join(portfolio.tickers)}",
            file=sys.stderr,
        )
    elif args.portfolio_action == "list":
        portfolios = list_portfolios()
        if not portfolios:
            print("No portfolios yet.", file=sys.stderr)
        else:
            for p in portfolios:
                print(f"{p.name}: {', '.join(p.tickers)}")
    elif args.portfolio_action == "delete":
        delete_portfolio(args.name)
        print(f"Deleted portfolio '{args.name}'.", file=sys.stderr)
    elif args.portfolio_action == "review":
        return _run_portfolio_review(args.name)

    return 0


def _run_portfolio_review(name: str) -> int:
    portfolio = get_portfolio(name)
    if portfolio is None:
        print(f"No portfolio named '{name}'.", file=sys.stderr)
        return 1

    results = []
    failed_tickers = []
    for ticker in portfolio.tickers:
        try:
            financials = fetch_raw_financials(ticker)
        except TickerNotFoundError:
            failed_tickers.append(ticker)
            continue
        result = score_financials(financials)
        record_and_diff(result)
        results.append(result)

    review = build_portfolio_review(portfolio.name, results, failed_tickers)

    print(f"# {review.portfolio_name}\n")
    if review.failed_tickers:
        print(f"Could not fetch data for: {', '.join(review.failed_tickers)}\n")

    if review.overall_score is not None:
        print(f"Portfolio signal: {review.overall_score:.2f} / 4.0 ({review.tier})\n")
    else:
        print("No tickers could be scored yet.\n")

    for category_id, avg in review.category_averages.items():
        label = category_id.replace("_", " ").title()
        if avg is not None:
            print(f"{label}: {avg:.2f} ({tier_for_score(avg)})")
        else:
            print(f"{label}: n/a")

    if review.sector_counts:
        print("\nSector concentration:")
        total = len(review.holdings)
        for sector, count in review.sector_counts.items():
            print(f"- {sector}: {count} ({count / total * 100:.0f}%)")

    if review.holdings:
        print("\nHoldings:")
        for h in review.holdings:
            if h.overall_score is not None:
                score_text = f"{h.overall_score:.2f} ({h.tier})"
            else:
                score_text = "n/a"
            print(f"- {h.financials.ticker} ({h.financials.company_name}): {score_text}")

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
    if args.command == "journal":
        return _run_journal(args)
    if args.command == "portfolio":
        return _run_portfolio(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
