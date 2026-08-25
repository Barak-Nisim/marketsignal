# Enhancement Roadmap

MarketSignal v1 is stable and, unlike the other two portfolio projects, is meant for actual regular use: real yfinance data, deterministic scoring, AI thesis, and local history/what-changed tracking are all working and tested. This document is the parking lot for what could come next, ranked by effort, not by priority. Nothing here is committed to.

Effort tags: **Minor** (an evening), **Moderate** (a focused day or two), **Major** (a real feature, spans multiple files/decisions).

## Data & scoring

1. **[Moderate]** Web-search-grounded recent news in the AI thesis ([issue #8](https://github.com/Barak-Nisim/marketsignal/issues/8)) -- deferred from v1 because combining Claude's `web_search` tool with strict structured output is an unverified technical unknown; worth a focused spike.
2. **[Major]** Sector-relative scoring: compare a ticker's P/E, margins, etc. against its own sector/industry average instead of fixed absolute thresholds.
3. **[Moderate]** Support an alternate data provider as a fallback, since `yfinance` is an unofficial wrapper and can break when Yahoo changes something upstream.
4. **[Shipped]** ~~A historical trend chart rendering overall score over time from the local history file.~~ Shipped as a sparkline on the report page (signal score over time, not raw price -- a price chart specifically is still open, see the Web UI section).
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
14. **[Moderate]** A sparkline *price* chart on the report page (the shipped sparkline is signal score over time, not the raw price; currently price is still only 3/6/12-month deltas as numbers).
15. **[Minor]** Mobile polish pass on the report's metric-detail tables.
16. **[Shipped]** ~~Manual dark/light theme toggle.~~ Shipped.
17. **[Minor]** Print-friendly stylesheet for the report page.
18. **[Shipped]** ~~A "recently researched" list on `/app` pulling from local history.~~ Shipped, plus a favorites list with per-ticker trend went further than originally scoped here.

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

## Shipped since this list was written (2026-08-25)

Not originally on this list, added as they were built:

31. **[Shipped]** Investment thesis builder: the AI thesis restructured from one free-form paragraph into bull_case / bear_case / catalysts / risk_factors (each with a `based_on` evidence tag) / what_would_change_my_mind. See `ai/narrator.py` and `ai/prompts.py`.
32. **[Shipped]** Outcome tracking: each history snapshot now records price at signal time; the report shows how past signals actually performed (1wk+ / 1mo+ / 3mo+) against the current price. See `outcomes.py`.
33. **[Shipped]** Favorites list with per-ticker trend on `/app` (a lighter-weight version of #8's watchlist idea, not the full digest-mode version).
34. **[Shipped]** Evidence & Provenance: catalysts and risk factors are each tagged `Fact` / `Inference` / `Opinion` in the structured output, rendered as colored badges on the report. Also fixed `report/markdown.py`, which had gone stale against the bull/bear schema and was silently dropping the thesis from CLI output. See `ai/narrator.py`.
35. **[Shipped]** Thesis tracking over time: each AI thesis is now persisted to `~/.marketsignal/thesis_history/<TICKER>.json`, and the next research run shows what was added or dropped (catalysts, risk factors, invalidation conditions, confidence) versus the prior thesis. The diff is a deterministic set comparison over the structured fields, not a re-narrated prose comparison -- narrating "revenue outlook strengthened" in words would need its own AI call, which was deliberately left out to keep this addition free. See `thesis_history.py`.

## Bigger bets (real architecture decisions, plan formally before building)

The 2026-08-25 conversation with Barak reframed MarketSignal from "an AI stock research app" to "a system that maintains and challenges an investment thesis over time" (five layers: Thesis Engine, Multi-Agent Debate, Evidence/Provenance, Historical Accountability, Portfolio Intelligence). Reviewed and sequenced the same day. Agreed direction below; items are numbered in build order, not list order.

**Sequence 1 -- next up, cheap, no new infra:**

36. **[Moderate]** "What would change my mind" invalidation checking: on the next manual research run for a ticker (not a live/scheduled monitor -- consistent with the standing no-live-deploy decision), check the current data against the invalidation conditions stored from the prior thesis (now available via `thesis_history.py`, shipped as #35) and flag which ones tripped.
37. **[Minor]** Investment Journal: a persisted, user-authored note attached to a ticker (your own reasoning, not AI-generated), surfaced on later visits alongside how the thesis has since moved.

**Sequence 2 -- larger, needs a prerequisite or an explicit go-ahead first:**

38. **[Major]** Multi-agent debate: specialized agents (bull, bear, and possibly others) argue a ticker independently before a synthesis step reconciles them, instead of one model call producing both cases directly. Real cost implications (multiple Opus calls per research run instead of one -- a scoped bull/bear-only version at 3 calls was considered and explicitly deferred rather than built now) and a real prerequisite: a News/Catalyst agent needs grounded current data, which is #1 above, an "unverified technical unknown" -- solve that first. Do not add a "Fundamentals Agent"; fundamentals stay in the deterministic scoring engine, which already does that job without hallucination risk.
39. **[Major]** Historical accountability: track whether past *fundamental* claims held up (margins expanded, revenue accelerated) over time. Deliberately scoped to fundamental-claim accuracy only, never price-direction accuracy -- tracking whether the stock went up would be a covert Buy/Sell signal, which conflicts with the standing no-Buy/Sell-advice decision. Needs real elapsed time after shipping before it has anything to show.
40. **[Major]** Portfolio Intelligence: multi-ticker concentration/correlation/exposure analysis. Real value but a genuinely new UI surface (multi-ticker input) and new data surface (pairwise historical price series). Don't start this until the single-ticker thesis engine (34-37) is settled -- no point building portfolio-level insight on a thesis model still in flux.

**Considered and rejected:** an "Ask MarketSignal" free-form chat box (from the vision's own company-page mockup) was cut -- it reopens the hallucination/trust surface that Evidence & Provenance (34) is meant to close, and conflicts with the vision's own stated principle that "the AI should support the product, not be the product."
