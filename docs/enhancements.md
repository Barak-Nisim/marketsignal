# Enhancement Roadmap

MarketSignal v1 is stable and, unlike the other two portfolio projects, is meant for actual regular use: real yfinance data, deterministic scoring, AI thesis, and local history/what-changed tracking are all working and tested. This document is the parking lot for what could come next, ranked by effort, not by priority. Nothing here is committed to.

Effort tags: **Minor** (an evening), **Moderate** (a focused day or two), **Major** (a real feature, spans multiple files/decisions).

## Data & scoring

1. **[Moderate]** Web-search-grounded recent news in the AI thesis ([issue #8](https://github.com/Barak-Nisim/marketsignal/issues/8)) -- deferred from v1 because combining Claude's `web_search` tool with strict structured output is an unverified technical unknown; worth a focused spike.
2. **[Major]** Sector-relative scoring: compare a ticker's P/E, margins, etc. against its own sector/industry average instead of fixed absolute thresholds.
3. **[Moderate]** Support an alternate data provider as a fallback, since `yfinance` is an unofficial wrapper and can break when Yahoo changes something upstream.
4. **[Moderate]** A historical trend chart rendering overall score over time from the local history file, not just the single-run delta.
5. **[Minor]** Make the scoring thresholds configurable (a YAML/JSON override) instead of hardcoded in `scoring.py`.
6. **[Moderate]** Add forward-looking valuation signals (forward P/E, consensus EPS estimates) alongside the current trailing-metric-only valuation category.
7. **[Minor]** Add a dividend yield / payout ratio signal, useful for income-focused tickers that the current five categories don't address well.

## Personal-use workflow

8. **[Major]** Watchlist support (multiple tickers per run) ([issue #9](https://github.com/Barak-Nisim/marketsignal/issues/9)) -- v1 is single-ticker by explicit scope decision; this is the most likely thing to actually get requested once v1 has been used for a while.
9. **[Moderate]** A digest mode: run against a saved watchlist on a schedule and produce one summary of everything that changed.
10. **[Minor]** CSV/JSON export of a report for tracking in a spreadsheet.
11. **[Moderate]** Side-by-side comparison view for two tickers.
12. **[Minor]** A small script/cron helper to run research against a watchlist automatically and just log to history, without opening the browser.

## Web UI / UX

13. **[Minor]** Ticker autocomplete/typeahead on the research form.
14. **[Moderate]** A sparkline price chart on the report page (currently only 3/6/12-month deltas as numbers, no visual).
15. **[Minor]** Mobile polish pass on the report's metric-detail tables.
16. **[Minor]** Manual dark/light theme toggle; currently OS-preference only.
17. **[Minor]** Print-friendly stylesheet for the report page.
18. **[Minor]** A "recently researched" list on `/app` pulling from local history, so returning tickers are one click away.

## AI layer

19. **[Moderate]** Stream the thesis token-by-token instead of waiting for the full response.
20. **[Minor]** A thesis-depth toggle (quick take vs. a longer deep-dive).
21. **[Minor]** Cache AI narratives for repeated same-day requests on the same ticker to avoid redundant spend.

## Engineering & quality

22. **[Minor]** Structured logging for the web app (local-only, no external telemetry).
23. **[Minor]** Basic rate limiting / request caps on the web form, relevant only if this is ever made public.
24. **[Moderate]** Dockerfile as an alternative to `pip install` for local setup.
25. **[Minor]** Add `mypy` or `pyright` to CI alongside the existing `ruff` lint step.
26. **[Moderate]** Snapshot/golden-file tests for the rendered report, to catch template regressions substring tests might miss.
27. **[Moderate]** Retry/backoff handling for transient yfinance failures. Right now any fetch error, including a temporary network blip, is reported as "ticker not found," which is misleading for a real transient failure.
28. **[Minor]** Split "ticker genuinely doesn't exist" from "data source temporarily unavailable" into two distinct error types, once #27 is in place, so the CLI/web error messages are accurate.

## Integrations

29. **[Major]** Portfolio-level aggregation: sum signal scores across a list of holdings for one portfolio-level readout instead of ticker-by-ticker only.
30. **[Major]** Read-only brokerage integration (e.g. via Plaid) to auto-populate a watchlist from actual holdings, instead of typing tickers in by hand.
