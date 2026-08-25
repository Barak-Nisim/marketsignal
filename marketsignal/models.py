"""Data model for MarketSignal: raw financials, computed scores, and history.

RawFinancials fields are almost all Optional -- not every ticker publishes
every metric. ETFs in particular usually lack income-statement-based fields
(margins, growth, ROE) entirely, since they aren't operating companies. The
scoring engine in scoring.py treats a missing metric as "not applicable" and
excludes it from its category's weighted average, rather than penalizing it
the way an unanswered RiskLens question is penalized -- a missing P/E ratio
doesn't mean a company is doing poorly, it usually just means the metric
doesn't apply.
"""

from __future__ import annotations

from dataclasses import dataclass

SIGNAL_LEVELS = {
    0: "Weak",
    1: "Below Average",
    2: "Average",
    3: "Above Average",
    4: "Strong",
}


@dataclass(frozen=True)
class RawFinancials:
    ticker: str
    company_name: str
    sector: str | None
    industry: str | None
    as_of: str

    current_price: float | None = None
    fifty_two_week_low: float | None = None
    fifty_two_week_high: float | None = None
    price_change_3mo: float | None = None  # fraction, e.g. 0.05 = +5%
    price_change_6mo: float | None = None
    price_change_12mo: float | None = None

    trailing_pe: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    peg_ratio: float | None = None

    revenue_growth: float | None = None
    earnings_growth: float | None = None

    gross_margin: float | None = None
    operating_margin: float | None = None
    return_on_equity: float | None = None

    debt_to_equity: float | None = None
    current_ratio: float | None = None


@dataclass(frozen=True)
class MetricScore:
    key: str
    label: str
    value: float | None
    score: int | None  # None if the underlying value was unavailable


@dataclass(frozen=True)
class CategoryScore:
    id: str
    name: str
    score: float | None  # None if every metric in the category was unavailable
    metric_scores: tuple[MetricScore, ...]


@dataclass(frozen=True)
class ScoreResult:
    financials: RawFinancials
    overall_score: float | None
    tier: str
    category_scores: tuple[CategoryScore, ...]


@dataclass(frozen=True)
class Snapshot:
    """What gets persisted to ~/.marketsignal/history/<TICKER>.json between runs."""

    ticker: str
    as_of: str
    overall_score: float | None
    category_scores: dict[str, float | None]
    price: float | None = None  # current_price at snapshot time, for outcome tracking later


@dataclass(frozen=True)
class WhatChanged:
    previous_as_of: str
    overall_score_delta: float | None
    category_deltas: dict[str, float | None]


@dataclass(frozen=True)
class JournalEntry:
    """A user-authored note attached to a ticker, persisted separately from
    the AI-generated thesis -- your own reasoning, not narrated output."""

    ticker: str
    note: str
    written_at: str


@dataclass(frozen=True)
class AccuracySummary:
    """A running tally of how past catalyst/risk-factor claims have held up
    against later data, built from claim_accuracy_check entries recorded in
    thesis_history over time. Scoped to fundamental-claim accuracy only --
    never price-direction accuracy, which would function as a covert
    Buy/Sell signal."""

    held_up: int
    did_not_hold_up: int
    too_early_to_tell: int

    @property
    def judged(self) -> int:
        return self.held_up + self.did_not_hold_up

    @property
    def accuracy_pct(self) -> float | None:
        return (self.held_up / self.judged) if self.judged else None


@dataclass(frozen=True)
class ThesisDelta:
    """A deterministic diff between two AI-generated theses for the same
    ticker: what was added or dropped, not a re-narrated comparison. No AI
    call is involved in producing this -- it's a set comparison over the
    structured catalysts/risk_factors/what_would_change_my_mind fields
    already in the narrator's output."""

    previous_as_of: str
    confidence_before: str
    confidence_after: str
    catalysts_added: tuple[str, ...]
    catalysts_removed: tuple[str, ...]
    risks_added: tuple[str, ...]
    risks_removed: tuple[str, ...]
    invalidation_added: tuple[str, ...]
    invalidation_removed: tuple[str, ...]
