"""Structural tests for market-data methods. No network: _graphql is monkeypatched."""

from __future__ import annotations

from typing import Any

from wealthsim.client import Session


def _session(monkeypatch: Any, canned: dict[str, Any]) -> Session:
    s = Session.__new__(Session)  # bypass __init__ (no real http/token needed)

    def fake_graphql(operation: str, query: str, variables: dict[str, Any]) -> Any:
        return canned

    monkeypatch.setattr(s, "_graphql", fake_graphql)
    return s


def test_search_shape(monkeypatch: Any) -> None:
    canned = {
        "securitySearch": {
            "results": [
                {
                    "id": "sec-s-1",
                    "buyable": True,
                    "status": "active",
                    "stock": {"symbol": "AAPL", "name": "Apple Inc", "primaryExchange": "NASDAQ"},
                }
            ]
        }
    }
    s = _session(monkeypatch, canned)
    out = s.search("AAPL")
    assert out == [
        {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "exchange": "NASDAQ",
            "security_id": "sec-s-1",
            "buyable": True,
            "status": "active",
        }
    ]


def test_search_respects_limit(monkeypatch: Any) -> None:
    results = [
        {"id": f"sec-{i}", "buyable": True, "status": "active",
         "stock": {"symbol": f"S{i}", "name": "x", "primaryExchange": "NYSE"}}
        for i in range(5)
    ]
    s = _session(monkeypatch, {"securitySearch": {"results": results}})
    assert len(s.search("x", limit=2)) == 2


def test_security_id_to_symbol(monkeypatch: Any) -> None:
    canned = {"security": {"id": "sec-s-1", "stock": {"symbol": "TSLA", "name": "Tesla", "primaryExchange": "NASDAQ"}}}
    s = _session(monkeypatch, canned)
    assert s.security_id_to_symbol("sec-s-1") == "TSLA"
