"""Structural tests for positions/holdings methods. No network."""

from __future__ import annotations

from typing import Any

from wealthsim.client import Session


def test_account_unrealized_pnl_shape(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    canned = {
        "account": {
            "financials": {
                "currentCombined": {
                    "unrealizedPnL": {"amount": "123.45", "rate": "0.021", "currency": "CAD"}
                }
            }
        }
    }
    monkeypatch.setattr(s, "_graphql", lambda *a: canned)
    assert s.account_unrealized_pnl("tfsa-x") == {
        "amount": "123.45",
        "rate": "0.021",
        "currency": "CAD",
    }


def test_account_unrealized_pnl_missing_raises(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    monkeypatch.setattr(s, "_graphql", lambda *a: {"account": None})
    try:
        s.account_unrealized_pnl("nope")
    except Exception as exc:
        assert "No account found" in str(exc)
    else:
        raise AssertionError("expected WSError")
