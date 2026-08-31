"""Structural tests for account/balance methods. No network: _graphql dispatched by op."""

from __future__ import annotations

from typing import Any

from wealthsim.client import Session


def test_account_balances_resolves_symbols(monkeypatch: Any) -> None:
    s = Session.__new__(Session)

    def fake_graphql(operation: str, query: str, variables: dict[str, Any]) -> Any:
        if operation == "FetchAccountsWithBalance":
            return {
                "accounts": [
                    {
                        "custodianAccounts": [
                            {"financials": {"balance": [
                                {"securityId": "sec-c-cad", "quantity": "100.50"},
                                {"securityId": "sec-s-aapl", "quantity": "3"},
                            ]}}
                        ]
                    }
                ]
            }
        if operation == "FetchSecuritySymbol":
            return {"security": {"stock": {"symbol": "AAPL"}}}
        raise AssertionError(operation)

    monkeypatch.setattr(s, "_graphql", fake_graphql)
    assert s.account_balances("tfsa-x") == {"sec-c-cad": "100.50", "AAPL": "3"}


def test_account_balances_missing_raises(monkeypatch: Any) -> None:
    s = Session.__new__(Session)
    monkeypatch.setattr(s, "_graphql", lambda *a: {"accounts": []})
    try:
        s.account_balances("nope")
    except Exception as exc:
        assert "No account found" in str(exc)
    else:
        raise AssertionError("expected WSError")
