"""Structural tests for per-account history. No network."""

from __future__ import annotations

from typing import Any

from wealthsim.client import Session


def test_account_history_shape(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    canned = {
        "account": {
            "financials": {
                "historicalDaily": {
                    "edges": [
                        {"node": {"date": "2026-08-01", "netLiquidationValueV2": {"amount": "100.0"}}},
                        {"node": {"date": "2026-08-02", "netLiquidationValueV2": {"amount": "101.5"}}},
                    ]
                }
            }
        }
    }
    monkeypatch.setattr(s, "_graphql", lambda *a: canned)
    assert s.account_history("tfsa-x", days=30) == [
        {"date": "2026-08-01", "value": "100.0"},
        {"date": "2026-08-02", "value": "101.5"},
    ]


def test_account_history_missing_raises(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    monkeypatch.setattr(s, "_graphql", lambda *a: {"account": None})
    try:
        s.account_history("nope")
    except Exception as exc:
        assert "No account found" in str(exc)
    else:
        raise AssertionError("expected WSError")
