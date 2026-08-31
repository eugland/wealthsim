"""MCP server exposing wealthsim's read-only methods as tools for Claude.

Run:  wealthsim-mcp            (after `pip install "wealthsim[mcp]"`)
  or: python -m wealthsim.mcp_server

Auth reuses the cached token (OS keyring, then .env). If none is cached, tools return
an error asking you to run `python browser_auth.py` once. Read-only by design — there is
no order-placement tool.

Register with Claude Desktop (claude_desktop_config.json) or Claude Code (.mcp.json):

    {
      "mcpServers": {
        "wealthsim": { "command": "wealthsim-mcp" }
      }
    }
"""

from __future__ import annotations

from typing import Any, Optional

from .client import Session, WSError

try:  # mcp SDK v1 exposed FastMCP; v2 renamed it to MCPServer. Support both.
    from mcp.server.fastmcp import FastMCP as _Server  # type: ignore
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer as _Server  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "The MCP SDK is required. Install it with:  pip install \"wealthsim[mcp]\""
        ) from exc

mcp = _Server("wealthsim")

_session: Optional[Session] = None


def _ws() -> Session:
    """Lazily build (and cache) an authed Session from cached tokens."""
    global _session
    if _session is None:
        from .browser import load_cached

        try:
            _session = load_cached()
        except FileNotFoundError as exc:
            raise WSError(
                "No cached Wealthsimple token. Run `python browser_auth.py` once to log in."
            ) from exc
    return _session


# --- market data (public) -----------------------------------------------------------
@mcp.tool()
def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search securities by symbol or name. Returns symbol, name, exchange, security_id."""
    return _ws().search(query, limit=limit)


@mcp.tool()
def quote(symbol: str) -> dict[str, Any]:
    """Latest quote for a ticker: price, bid/ask, OHLC, volume, change %, market status."""
    return _ws().quote(symbol)


@mcp.tool()
def security(symbol: str) -> dict[str, Any]:
    """Core fundamentals: market cap, P/E, EPS, yield, 52-week range."""
    return _ws().security(symbol)


@mcp.tool()
def security_info(symbol: str) -> dict[str, Any]:
    """Full security data: fundamentals plus beta, margin rate, MER, allowed order subtypes."""
    return _ws().security_info(symbol)


@mcp.tool()
def security_dividend(symbol: str) -> dict[str, Any]:
    """Dividend details: yield, frequency, ex-dividend / record / payable dates."""
    return _ws().security_dividend(symbol)


@mcp.tool()
def historical_quotes(symbol: str, timerange: str = "1m") -> list[dict[str, Any]]:
    """Daily price history. timerange one of: 1d, 1w, 1m, 3m, 1y, 5y."""
    return _ws().historical_quotes(symbol, timerange)


# --- accounts & portfolio (personal) ------------------------------------------------
@mcp.tool()
def accounts() -> list[dict[str, Any]]:
    """All accounts: id, type, nickname, currency, status, value."""
    return _ws().accounts()


@mcp.tool()
def account_balances(account_id: str) -> dict[str, Any]:
    """Per-security balances for one account: {symbol_or_cash_code: quantity}."""
    return _ws().account_balances(account_id)


@mcp.tool()
def positions(currency: str = "CAD") -> list[dict[str, Any]]:
    """Holdings across accounts: symbol, quantity, book/market value, unrealized P&L."""
    return _ws().positions(currency=currency)


@mcp.tool()
def account_unrealized_pnl(account_id: str, currency: str = "CAD") -> dict[str, Any]:
    """Combined unrealized P&L for one account: amount, rate, currency."""
    return _ws().account_unrealized_pnl(account_id, currency=currency)


@mcp.tool()
def net_worth(currency: str = "CAD") -> dict[str, Any]:
    """Combined net worth: value, net deposits, simple return (amount + rate)."""
    return _ws().net_worth(currency=currency)


@mcp.tool()
def realized_returns(currency: str = "CAD") -> dict[str, Any]:
    """Total realized P&L plus per-security breakdown."""
    return _ws().realized_returns(currency=currency)


@mcp.tool()
def dividends(currency: str = "CAD") -> dict[str, Any]:
    """Total dividend income plus per-security breakdown."""
    return _ws().dividends(currency=currency)


@mcp.tool()
def portfolio_history(days: int = 90, currency: str = "CAD") -> list[dict[str, Any]]:
    """Daily net-worth series for the last `days` (for charting)."""
    return _ws().portfolio_history(days=days, currency=currency)


@mcp.tool()
def account_history(account_id: str, days: int = 90, currency: str = "CAD") -> list[dict[str, Any]]:
    """Daily value series for one account over the last `days`."""
    return _ws().account_history(account_id, days=days, currency=currency)


@mcp.tool()
def activities(limit: int = 10) -> list[dict[str, Any]]:
    """Recent activity feed: deposits, trades, dividends, card, interest."""
    return _ws().activities(limit=limit)


@mcp.tool()
def me() -> dict[str, Any]:
    """Profile + session: name, email, identity id, token scope and expiry."""
    return _ws().me()


def main() -> None:
    """Console-script entry point: run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
