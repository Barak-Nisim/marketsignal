"""Shared pytest fixtures for the test suite.

fetch_price_history makes a real yfinance call and is invoked on every
/research POST to build the report's price-trend chart, so it's mocked to
return [] here by default rather than requiring every existing /research
test to mock it individually. Tests that want to exercise real
price-trend rendering explicitly re-patch it with data, which layers on
top of (and for their duration overrides) this default.
"""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _no_price_history_by_default():
    with patch("marketsignal.web.app.fetch_price_history", return_value=[]):
        yield
