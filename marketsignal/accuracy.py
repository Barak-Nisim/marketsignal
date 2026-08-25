"""Aggregates claim_accuracy_check entries recorded across a ticker's
thesis_history into a running track record.

Deliberately reuses thesis_history.py's storage rather than adding a new
persistence store: each recorded thesis already carries its own
claim_accuracy_check verdicts (produced by the same AI call that generated
it, judging the *prior* thesis's claims), so walking the full history is
enough to build the summary. No AI call happens here -- this is a pure
aggregation over already-stored data.
"""

from __future__ import annotations

from marketsignal.models import AccuracySummary


def compute_accuracy_summary(thesis_history: list[dict]) -> AccuracySummary:
    held_up = 0
    did_not_hold_up = 0
    too_early = 0

    for entry in thesis_history:
        for check in entry["narrative"].get("claim_accuracy_check", []):
            if check["status"] == "Held up":
                held_up += 1
            elif check["status"] == "Did not hold up":
                did_not_hold_up += 1
            elif check["status"] == "Too early to tell":
                too_early += 1

    return AccuracySummary(
        held_up=held_up, did_not_hold_up=did_not_hold_up, too_early_to_tell=too_early
    )
