# Enhancement Roadmap

MarketSignal v1 is stable and, unlike the other two portfolio projects, is meant for actual regular use: real yfinance data, deterministic scoring, AI thesis, and local history/what-changed tracking are all working and tested. This document is the parking lot for what could come next, ranked by effort, not by priority. Nothing here is committed to.

Effort tags: **Minor** (an evening), **Moderate** (a focused day or two), **Major** (a real feature, spans multiple files/decisions).

## Data & scoring

1. **[Moderate]** Web-search-grounded recent news in the AI thesis ([issue #8](https://github.com/Barak-Nisim/marketsignal/issues/8)) -- deferred from v1 because combining Claude's `web_search` tool with strict structured output is an unverified technical unknown; worth a focused spike.
2. **[Major]** Sector-relative scoring: compare a ticker's P/E, margins, etc. against its own sector/industry average instead of fixed absolute thresholds.
3. **[Moderate]** Support an alternate data provider as a fallback, since `yfinance` is an unofficial wrapper and can break when Yahoo changes something upstream.
4. **[Shipped]** ~~A historical trend chart rendering overall score over time from the local history file.~~ Shipped as a sparkline on the report page (signal score over time; the raw price chart is a separate item, see #14).
5. **[Minor]** Make the scoring thresholds configurable (a YAML/JSON override) instead of hardcoded in `scoring.py`.
6. **[Moderate]** Add forward-looking valuation signals (forward P/E, consensus EPS estimates) alongside the current trailing-metric-only valuation category.
7. **[Minor]** Add a dividend yield / payout ratio signal, useful for income-focused tickers that the current five categories don't address well.

## Personal-use workflow

8. **[Shipped]** ~~Watchlist support (multiple tickers per run)~~ Shipped as named, saved portfolios (`/portfolios`) rather than a one-off multi-ticker research run -- see #40 below for the fuller writeup. A single research run is still single-ticker by design; a portfolio is the multi-ticker surface.
9. **[Moderate]** A digest mode: run against a saved watchlist on a schedule and produce one summary of everything that changed.
10. **[Minor]** CSV/JSON export of a report for tracking in a spreadsheet.
11. **[Moderate]** Side-by-side comparison view for two tickers.
12. **[Minor]** A small script/cron helper to run research against a watchlist automatically and just log to history, without opening the browser.

## Web UI / UX

13. **[Minor]** Ticker autocomplete/typeahead on the research form.
14. **[Shipped]** ~~A sparkline *price* chart on the report page.~~ Shipped with a 5D/1M/1Y/All range toggle: one daily-history fetch per research run, sliced into four windows and pre-rendered server-side, so switching ranges is instant with no extra request. No intraday "1 Day" option -- deliberately left out since it needs a separate, less reliable fetch. See `price_trend.py`.
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

29. **[Shipped]** ~~Portfolio-level aggregation: sum signal scores across a list of holdings for one portfolio-level readout instead of ticker-by-ticker only.~~ Shipped -- see #40.
30. **[Major]** Read-only brokerage integration (e.g. via Plaid) to auto-populate a watchlist from actual holdings, instead of typing tickers in by hand.

## Shipped since this list was written (2026-08-25)

Not originally on this list, added as they were built:

31. **[Shipped]** Investment thesis builder: the AI thesis restructured from one free-form paragraph into bull_case / bear_case / catalysts / risk_factors (each with a `based_on` evidence tag) / what_would_change_my_mind. See `ai/narrator.py` and `ai/prompts.py`.
32. **[Shipped]** Outcome tracking: each history snapshot now records price at signal time; the report shows how past signals actually performed (1wk+ / 1mo+ / 3mo+) against the current price. See `outcomes.py`.
33. **[Shipped]** Favorites list with per-ticker trend on `/app` (a lighter-weight version of #8's watchlist idea, not the full digest-mode version).
34. **[Shipped]** Evidence & Provenance: catalysts and risk factors are each tagged `Fact` / `Inference` / `Opinion` in the structured output, rendered as colored badges on the report. Also fixed `report/markdown.py`, which had gone stale against the bull/bear schema and was silently dropping the thesis from CLI output. See `ai/narrator.py`.
35. **[Shipped]** Thesis tracking over time: each AI thesis is now persisted to `~/.marketsignal/thesis_history/<TICKER>.json`, and the next research run shows what was added or dropped (catalysts, risk factors, invalidation conditions, confidence) versus the prior thesis. The diff is a deterministic set comparison over the structured fields, not a re-narrated prose comparison -- narrating "revenue outlook strengthened" in words would need its own AI call, which was deliberately left out to keep this addition free. See `thesis_history.py`.
36. **[Shipped]** "What would change my mind" invalidation checking: each research run now passes the prior thesis's invalidation conditions (via `thesis_history.previous_invalidation_conditions`) into the same AI call as extra context, so the model classifies each one Triggered / Not triggered / Unclear against today's data, no separate AI call and no live/scheduled monitor. See the `invalidation_check` field in `ai/narrator.py` and the "Invalidation check" section on the report page.
37. **[Shipped]** Investment Journal: a persisted, user-authored note attached to a ticker, kept separate from the AI-generated thesis. Add a note via `marketsignal journal add <TICKER> <note>` or the form on the report page; entries show up on later research runs for that ticker. See `journal.py`.
39. **[Shipped]** Historical accountability: catalyst and risk-factor claims from the prior thesis are checked against current data in the same AI call (via `thesis_history.previous_claims`), classified Held up / Did not hold up / Too early to tell, and aggregated into a running "Track record" (e.g. "3 of 4 judged fundamental claims held up") built by walking `thesis_history` -- no new persistence store. Deliberately scoped to the fundamental metric each claim was grounded in, never to price direction, so it can't function as a covert Buy/Sell signal. Won't show a meaningful track record until enough research runs have accumulated over time. See `accuracy.py` and the `claim_accuracy_check` field in `ai/narrator.py`.
41. **[Shipped]** Portfolio performance tracking: `portfolio_performance.py` answers "which holdings actually gained or lost over a window, and did the portfolio move up or down" -- best/worst movers, an up/down/flat count, and a total value series -- as pure arithmetic over price histories the caller already fetched, the same posture as `portfolio_review.py`, so it stays deterministic and testable against synthetic series. Period windows (1M/3M/6M/YTD/1Y/All) reuse `price_trend.py`'s calendar-days-back logic, so the report page's price chart and this table can never disagree about what "1Y" means. Every holding is deliberately valued at a fixed 100 shares: MarketSignal never asks for share counts or cost basis, so a fixed notional keeps holdings comparable and is honest that the total means "what 100 shares of each would have done", not a real P&L -- per-position weighting is a future enhancement, not an oversight. A holding with fewer than two closes in the window is named in `excluded_tickers` and left out of the totals rather than counted as flat, since no window is not the same as no movement. Surfaced as the `portfolio performance` CLI subcommand and a Performance section on the `/portfolios/{slug}/review` page, whose period toggle is plain server-rendered links with no JS.
42. **[Shipped]** Learn encyclopedia and tooltip deep-links: a `Concept` registry in `education.py` gives every category and metric an anchor, a small hand-drawn SVG diagram, and one or two outside references, reusing the `CATEGORY_GLOSSARY` / `METRIC_GLOSSARY` text verbatim so the glossaries stay the single source of truth and the page can never drift from the tooltips. Diagrams are four parametric builders (compare-bars, kept-bar, trend line, range marker) drawn with CSS custom properties so they follow the app's light/dark theme, rather than shipping two sets of images. The `/learn` page renders the 0-4 scale, a jump-link contents, then a section per category with its metrics nested in scoring order; `test_education.py` checks the registry against a real `ScoreResult`, so a metric added to `scoring.py` without a Concept fails a test instead of rendering a blank section. The report's existing info tooltips now carry a "Learn more" link into the matching anchor via `education.concept_anchor()`, which returns `None` for a key with no entry so nothing broken is linked. This is an extension of the education glossary and report-page `info_tip` tooltip foundation shipped immediately before it, which was likewise never a roadmap item and so isn't listed above on its own. Still deliberately concept-only: it explains what a metric means, never what a specific ticker's number implies, and it doesn't repeat `scoring.py`'s numeric thresholds -- those stay in `docs/scoring_methodology.md`.

## Bigger bets (real architecture decisions, plan formally before building)

The 2026-08-25 conversation with Barak reframed MarketSignal from "an AI stock research app" to "a system that maintains and challenges an investment thesis over time" (five layers: Thesis Engine, Multi-Agent Debate, Evidence/Provenance, Historical Accountability, Portfolio Intelligence). Reviewed and sequenced the same day. Sequence 1 (items 34-37), Historical Accountability (39), and Portfolio Intelligence (40) are now shipped.

40. **[Shipped]** ~~Portfolio Intelligence: multi-ticker concentration/exposure analysis.~~ Shipped as named, saved portfolios (`portfolios.py`, `/portfolios`): a deterministic aggregate of the same five signals across a set of holdings (averaged, missing categories excluded rather than zeroed) plus a sector-concentration count. Scoped down from the original idea in a formal plan, confirmed with Barak first: no AI-narrated portfolio thesis, no numeric growth-rate projection (would be real forecasting, conflicts with the standing "signals and reasoning, not a prediction" stance), and no pairwise correlation/covariance between holdings -- that last one is real quant work and the natural next step if this gets real use. Also no portfolio-level score history yet (each holding still gets its own history via `record_and_diff`, but the portfolio's own aggregate score isn't trended over time) -- explicitly deferred, not forgotten.

**Still parked:**

38. **[Major]** Multi-agent debate: specialized agents (bull, bear, and possibly others) argue a ticker independently before a synthesis step reconciles them, instead of one model call producing both cases directly. Real cost implications (multiple Opus calls per research run instead of one -- a scoped bull/bear-only version at 3 calls was considered and explicitly deferred rather than built now) and a real prerequisite: a News/Catalyst agent needs grounded current data, which is #1 above, an "unverified technical unknown" -- solve that first. Do not add a "Fundamentals Agent"; fundamentals stay in the deterministic scoring engine, which already does that job without hallucination risk.

**Considered and rejected:** an "Ask MarketSignal" free-form chat box (from the vision's own company-page mockup) was cut -- it reopens the hallucination/trust surface that Evidence & Provenance (34) is meant to close, and conflicts with the vision's own stated principle that "the AI should support the product, not be the product."
