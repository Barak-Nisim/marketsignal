# Scoring Methodology

MarketSignal scores a ticker's signal strength across five categories on a 0-4 scale, then rolls that up into an overall score. This document is the full threshold table; the implementation is in `marketsignal/scoring.py` and is unit-tested in `tests/test_scoring.py`.

## The signal scale

| Score | Meaning |
|---|---|
| 0 | Weak |
| 1 | Below Average |
| 2 | Average |
| 3 | Above Average |
| 4 | Strong |

**A missing metric is excluded, not penalized.** ETFs in particular usually have no income-statement data at all (margins, growth, ROE), since they aren't operating companies. A missing metric is left out of its category's average; if every metric in a category is unavailable, the category itself is excluded from the overall score. This is a deliberate difference from RiskLens, where an unanswered security question genuinely does mean "no evidence of control." A missing P/E ratio doesn't mean a company is doing poorly, it usually just means the ratio doesn't apply.

## Rolling scores up

Category score = simple average of its available metric scores. Overall score = simple average of the available category scores. No hidden weighting beyond what's listed below; this is deliberately simpler than RiskLens's weighted rollup, since there are fewer metrics per category here and the point is to stay recomputable by hand.

## Thresholds by category

**Valuation** (lower is a stronger signal, except where noted):

| Metric | Strong (4) | Above Avg (3) | Average (2) | Below Avg (1) | Weak (0) |
|---|---|---|---|---|---|
| Trailing P/E* | < 10 | < 15 | < 25 | < 40 | ≥ 40 |
| Price / Book | < 1 | < 3 | < 5 | < 8 | ≥ 8 |
| Price / Sales | < 1 | < 3 | < 6 | < 10 | ≥ 10 |
| PEG Ratio* | < 1 | < 1.5 | < 2 | < 3 | ≥ 3 |

\* Excluded (not scored 0) when negative -- a negative P/E from negative earnings isn't "expensive," it's a different situation entirely.

**Growth** (higher is a stronger signal; fractions, e.g. 0.20 = 20%):

| Metric | Strong (4) | Above Avg (3) | Average (2) | Below Avg (1) | Weak (0) |
|---|---|---|---|---|---|
| Revenue Growth (YoY) | ≥ 0.20 | ≥ 0.10 | ≥ 0.05 | ≥ 0 | < 0 |
| Earnings Growth (YoY) | ≥ 0.20 | ≥ 0.10 | ≥ 0.05 | ≥ 0 | < 0 |

**Profitability** (higher is a stronger signal):

| Metric | Strong (4) | Above Avg (3) | Average (2) | Below Avg (1) | Weak (0) |
|---|---|---|---|---|---|
| Gross Margin | ≥ 0.50 | ≥ 0.35 | ≥ 0.20 | ≥ 0.05 | < 0.05 |
| Operating Margin | ≥ 0.25 | ≥ 0.15 | ≥ 0.05 | ≥ 0 | < 0 |
| Return on Equity | ≥ 0.25 | ≥ 0.15 | ≥ 0.08 | ≥ 0 | < 0 |

**Financial Health**:

| Metric | Strong (4) | Above Avg (3) | Average (2) | Below Avg (1) | Weak (0) |
|---|---|---|---|---|---|
| Debt / Equity* | < 50 | < 100 | < 150 | < 250 | ≥ 250 |
| Current Ratio | ≥ 2 | ≥ 1.5 | ≥ 1 | ≥ 0.75 | < 0.75 |

\* Reported on the same scale Yahoo Finance uses (roughly percentage-like, e.g. 100 ≈ 1.0x debt-to-equity), not a raw fraction.

**Momentum** (higher / closer to the 52-week high is a stronger signal):

| Metric | Strong (4) | Above Avg (3) | Average (2) | Below Avg (1) | Weak (0) |
|---|---|---|---|---|---|
| 12-Month Price Change | ≥ 0.30 | ≥ 0.15 | ≥ 0 | ≥ -0.15 | < -0.15 |
| 3-Month Price Change | ≥ 0.15 | ≥ 0.05 | ≥ -0.05 | ≥ -0.15 | < -0.15 |
| Position in 52-Week Range | ≥ 0.80 | ≥ 0.60 | ≥ 0.40 | ≥ 0.20 | < 0.20 |

"Position in 52-Week Range" is `(current_price - 52wk_low) / (52wk_high - 52wk_low)`, so 1.0 means trading at the 52-week high and 0.0 means trading at the 52-week low.

## What the AI layer does and doesn't do

The AI narrator (`ai/narrator.py`) receives the fully-computed `ScoreResult` (and the `WhatChanged` diff, if one exists) as structured JSON and is explicitly instructed to write a reasoned thesis, a confidence level, and risk factors, not to recompute or second-guess the scores, and not to issue a Buy, Hold, or Sell recommendation. If a threshold above seems wrong for a given ticker, the fix is in this table, not in the AI layer.

**This is not financial advice.** MarketSignal shows deterministic signals computed from public market data and, optionally, AI-written reasoning about them. It does not know your portfolio, risk tolerance, or time horizon, and it does not recommend buying or selling anything.
