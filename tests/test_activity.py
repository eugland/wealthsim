"""Structural tests for activity-feed methods. No network."""

from __future__ import annotations

from typing import Any

from wealthsim.client import Session


def test_corporate_action_activities_shape(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    canned = {
        "corporateActionChildActivities": {
            "nodes": [
                {"occurredAt": "2026-08-01T00:00:00Z", "type": "CORPORATE_ACTION",
                 "subType": "SPLIT", "amount": "0", "amountSign": "positive",
                 "currency": "USD", "assetSymbol": "NVDA", "assetQuantity": "10",
                 "status": "COMPLETED"}
            ]
        }
    }
    monkeypatch.setattr(s, "_graphql", lambda *a: canned)
    out = s.corporate_action_activities("act-canon-1")
    assert len(out) == 1 and out[0]["assetSymbol"] == "NVDA"


def test_corporate_action_activities_empty(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    monkeypatch.setattr(s, "_graphql", lambda *a: {"corporateActionChildActivities": None})
    assert s.corporate_action_activities("nope") == []
