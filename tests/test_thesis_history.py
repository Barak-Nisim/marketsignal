from marketsignal.thesis_history import (
    build_thesis_delta,
    load_thesis_history,
    previous_claims,
    previous_invalidation_conditions,
    record_thesis_and_diff,
)


def _narrative(confidence="Medium", catalysts=None, risks=None, invalidation=None):
    return {
        "bull_case": "Bull case text.",
        "bear_case": "Bear case text.",
        "confidence": confidence,
        "key_evidence": ["Valuation"],
        "catalysts": [
            {"catalyst": c, "claim_type": "Fact", "based_on": "Growth"}
            for c in (catalysts or ["Next earnings report"])
        ],
        "risk_factors": [
            {"factor": r, "claim_type": "Fact", "based_on": "Valuation"}
            for r in (risks or ["Elevated multiples"])
        ],
        "what_would_change_my_mind": invalidation or ["If revenue growth turns negative"],
    }


def test_record_thesis_and_diff_first_run_returns_none_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))

    delta = record_thesis_and_diff("AAPL", "2026-01-01", _narrative())

    assert delta is None
    history = load_thesis_history("AAPL")
    assert len(history) == 1
    assert history[0]["as_of"] == "2026-01-01"


def test_record_thesis_and_diff_second_run_returns_diff(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))
    record_thesis_and_diff(
        "AAPL", "2026-01-01", _narrative(catalysts=["Earnings report"], risks=["High P/E"])
    )

    delta = record_thesis_and_diff(
        "AAPL",
        "2026-02-01",
        _narrative(catalysts=["New product launch"], risks=["High P/E"]),
    )

    assert delta is not None
    assert delta.previous_as_of == "2026-01-01"
    assert delta.catalysts_added == ("New product launch",)
    assert delta.catalysts_removed == ("Earnings report",)
    assert delta.risks_added == ()
    assert delta.risks_removed == ()

    history = load_thesis_history("AAPL")
    assert len(history) == 2


def test_build_thesis_delta_reports_confidence_change():
    previous = {"as_of": "2026-01-01", "narrative": _narrative(confidence="Low")}
    current = _narrative(confidence="High")

    delta = build_thesis_delta(previous, current)

    assert delta.confidence_before == "Low"
    assert delta.confidence_after == "High"


def test_build_thesis_delta_tracks_invalidation_conditions():
    previous = {
        "as_of": "2026-01-01",
        "narrative": _narrative(invalidation=["If margins compress"]),
    }
    current = _narrative(invalidation=["If margins compress", "If guidance is cut"])

    delta = build_thesis_delta(previous, current)

    assert delta.invalidation_added == ("If guidance is cut",)
    assert delta.invalidation_removed == ()


def test_load_thesis_history_returns_empty_list_for_unknown_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))

    assert load_thesis_history("NOPE") == []


def test_thesis_history_is_isolated_from_real_user_home(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))
    record_thesis_and_diff("MSFT", "2026-01-01", _narrative())

    assert (tmp_path / "MSFT.json").exists()


def test_previous_invalidation_conditions_empty_for_unknown_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))

    assert previous_invalidation_conditions("NOPE") == []


def test_previous_invalidation_conditions_returns_most_recent_thesis(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))
    record_thesis_and_diff("AAPL", "2026-01-01", _narrative(invalidation=["Condition A"]))
    record_thesis_and_diff("AAPL", "2026-02-01", _narrative(invalidation=["Condition B"]))

    assert previous_invalidation_conditions("AAPL") == ["Condition B"]


def test_previous_claims_empty_for_unknown_ticker(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))

    assert previous_claims("NOPE") == []


def test_previous_claims_flattens_catalysts_and_risk_factors(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETSIGNAL_THESIS_HISTORY_DIR", str(tmp_path))
    record_thesis_and_diff(
        "AAPL",
        "2026-01-01",
        _narrative(catalysts=["Earnings report"], risks=["High P/E"]),
    )

    claims = previous_claims("AAPL")

    assert {"claim": "Earnings report", "based_on": "Growth", "source": "catalyst"} in claims
    assert {"claim": "High P/E", "based_on": "Valuation", "source": "risk_factor"} in claims
    assert len(claims) == 2
