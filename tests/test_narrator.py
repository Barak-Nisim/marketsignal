"""Tests for the AI narrator. The Claude API is always mocked here -- these
tests never make a network call and never require ANTHROPIC_API_KEY.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from marketsignal.ai.narrator import generate_narrative
from marketsignal.models import RawFinancials, WhatChanged
from marketsignal.scoring import score_financials

FAKE_NARRATIVE = {
    "thesis": "Growth and profitability are strong, but valuation looks stretched.",
    "confidence": "Medium",
    "risk_factors": ["Elevated valuation multiples", "Slowing revenue growth"],
}


def _sample_result():
    financials = RawFinancials(
        ticker="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        as_of="2026-01-01",
        trailing_pe=28,
        revenue_growth=0.08,
        gross_margin=0.44,
    )
    return score_financials(financials)


def _mock_client_with_response(payload: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps(payload))]
    )
    mock_client.messages.create.return_value = mock_response
    return mock_client


@patch("marketsignal.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_parses_mocked_response(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    narrative = generate_narrative(_sample_result())

    assert narrative == FAKE_NARRATIVE
    mock_anthropic.return_value.messages.create.assert_called_once()


@patch("marketsignal.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_uses_structured_output_schema(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    generate_narrative(_sample_result())

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "confidence" in kwargs["output_config"]["format"]["schema"]["required"]


@patch("marketsignal.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_includes_what_changed_in_prompt(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)
    what_changed = WhatChanged(
        previous_as_of="2025-12-01", overall_score_delta=0.5, category_deltas={"growth": 0.5}
    )

    generate_narrative(_sample_result(), what_changed)

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    user_message = kwargs["messages"][0]["content"]
    assert "2025-12-01" in user_message
