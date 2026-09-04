# MarketSignal

[![CI](https://github.com/Barak-Nisim/marketsignal/actions/workflows/ci.yml/badge.svg)](https://github.com/Barak-Nisim/marketsignal/actions/workflows/ci.yml)

AI-assisted investment research for US stocks and ETFs. Pulls real financial data from Yahoo Finance, scores it deterministically across five categories (Valuation, Growth, Profitability, Financial Health, Momentum), tracks what changed since your last look, and, optionally, has Claude write a reasoned thesis. No Buy/Sell button, by design: it shows the signals and the reasoning, and you draw the conclusion.

The scoring engine is deterministic, unit-tested, and has zero dependency on any AI service. The AI layer is a separate, optional piece bolted on top of it, same split as [RiskLens](https://github.com/Barak-Nisim/risklens). See [`docs/architecture.md`](docs/architecture.md) for why it's split that way, and [`docs/scoring_methodology.md`](docs/scoring_methodology.md) for the full threshold table.

**Not financial advice.** This shows deterministic signals from public market data and, optionally, AI-written reasoning about them. It doesn't know your portfolio, risk tolerance, or time horizon.

## Quickstart

```bash
pip install -e ".[dev]"

# Real data, no API key needed
marketsignal research AAPL --no-ai
```

Sample output (excerpt, from a real run against live data):

```
# MarketSignal Research Brief: Apple Inc. (AAPL)

**Sector:** Technology / Consumer Electronics
**As of:** 2026-08-24
**Overall Signal:** 2.68 / 4.0 (Above Average)

## Category Scores

| Category | Score | Signal |
|---|---|---|
| Valuation | 0.75 | Weak |
| Growth | 3.50 | Strong |
| Profitability | 3.67 | Strong |
| Financial Health | 2.50 | Above Average |
| Momentum | 3.00 | Above Average |
...
```

### With AI narration

Copy `.env.example` to `.env`, add an `ANTHROPIC_API_KEY`, then drop `--no-ai`:

```bash
marketsignal research AAPL
```

This adds a reasoned thesis, a confidence level, and key risk factors to the report, synthesized from the same scored signals above (the AI narrates them, it doesn't recompute them, and it never says Buy/Hold/Sell).

### What changed since last time

Every run is saved to `~/.marketsignal/history/<TICKER>.json` (outside the repo -- real personal research, never committed). Research the same ticker again later and the report shows exactly what moved.

## Web UI

```bash
marketsignal serve
```

Opens a small product site at `http://127.0.0.1:8000`:

- `/` -- a landing page explaining what MarketSignal does
- `/how-it-works` -- a walkthrough of the actual scoring methodology
- `/app` -- the live demo: enter a real ticker, get a real report against live market data
- `/portfolios` -- named, saved portfolios: aggregate signals and price performance across holdings
- `/learn` -- a plain-language encyclopedia of every category and metric behind the scores

## Development

```bash
pytest      # 35 tests, all mocked at the yfinance and AI boundaries -- no network calls, no cost
ruff check .
```

## Status

Core scoring engine, CLI, history/what-changed tracking, AI thesis, and web UI are all working end to end against real market data. See [`docs/enhancements.md`](docs/enhancements.md) for what's next, and [open issues](https://github.com/Barak-Nisim/marketsignal/issues) for the tracked roadmap.

## License

MIT
