from marketsignal.accuracy import compute_accuracy_summary


def _entry(checks):
    return {"as_of": "2026-01-01", "narrative": {"claim_accuracy_check": checks}}


def test_compute_accuracy_summary_empty_history():
    summary = compute_accuracy_summary([])

    assert summary.held_up == 0
    assert summary.did_not_hold_up == 0
    assert summary.too_early_to_tell == 0
    assert summary.judged == 0
    assert summary.accuracy_pct is None


def test_compute_accuracy_summary_counts_statuses_across_entries():
    history = [
        _entry(
            [
                {"claim": "A", "status": "Held up", "explanation": "x"},
                {"claim": "B", "status": "Did not hold up", "explanation": "x"},
            ]
        ),
        _entry(
            [
                {"claim": "C", "status": "Held up", "explanation": "x"},
                {"claim": "D", "status": "Too early to tell", "explanation": "x"},
            ]
        ),
    ]

    summary = compute_accuracy_summary(history)

    assert summary.held_up == 2
    assert summary.did_not_hold_up == 1
    assert summary.too_early_to_tell == 1
    assert summary.judged == 3
    assert summary.accuracy_pct == 2 / 3


def test_compute_accuracy_summary_ignores_entries_without_claim_checks():
    history = [{"as_of": "2026-01-01", "narrative": {}}]

    summary = compute_accuracy_summary(history)

    assert summary.judged == 0
    assert summary.accuracy_pct is None
