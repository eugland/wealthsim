"""Minimal Wealthsimple GraphQL client: bootstrap -> login (+TOTP) -> quote(symbol).

Endpoints and query shapes are the public/undocumented ones used by the web app,
same as the community `ws-api` library. This is a clean, from-scratch, single-file
reimplementation of only the login + quote path.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from curl_cffi import requests  # required: WS is behind Cloudflare TLS fingerprinting

OAUTH_TOKEN_URL = "https://api.production.wealthsimple.com/v1/oauth/v2/token"
GRAPHQL_URL = "https://my.wealthsimple.com/graphql"
LOGIN_PAGE_URL = "https://my.wealthsimple.com/app/login"
GRAPHQL_VERSION = "12"
SCOPE_READ_ONLY = "invest.read trade.read tax.read"
IMPERSONATE = "chrome"  # curl_cffi browser fingerprint to pass Cloudflare

_SEARCH_QUERY = (
    "query FetchSecuritySearchResult($query: String!) {"
    "  securitySearch(input: {query: $query}) {"
    "    results { id buyable status stock { symbol name primaryExchange }"
    "      quoteV2 { currency price"
    "        ... on EquityQuote { marketStatus last bid ask open high low close"
    "          mid volume: vol referenceClose } } } } }"
)

_ACCOUNTS_QUERY = (
    "query FetchAccounts($identityId: ID!, $pageSize: Int = 25, $cursor: String) {"
    "  identity(id: $identityId) {"
    "    id accounts(filter: {}, first: $pageSize, after: $cursor) {"
    "      edges { node {"
    "        id nickname unifiedAccountType currency status"
    "        financials { currentCombined {"
    "          netLiquidationValueV2 { amount currency } } } } } } } }"
)

_ACTIVITIES_QUERY = (
    "query FetchActivityFeedItems($first: Int, $accountScope: AccountScope = OWN) {"
    "  activityFeedItems(first: $first, accountScope: $accountScope) {"
    "    edges { node {"
    "      occurredAt type subType amount amountSign currency"
    "      assetSymbol assetQuantity status } } } }"
)

_POSITIONS_QUERY = (
    "query FetchIdentityPositions($identityId: ID!, $currency: Currency!, $first: Int) {"
    "  identity(id: $identityId) {"
    "    id financials(filter: {}) {"
    "      current(currency: $currency) {"
    "        positions(first: $first, aggregated: true) {"
    "          edges { node {"
    "            quantity positionDirection percentageOfAccount"
    "            bookValue { amount currency }"
    "            totalValue(currencyOverride: null) { amount currency }"
    "            unrealizedReturns(since: null) { amount currency }"
    "            security { id stock { symbol name primaryExchange } } } } } } } } }"
)

_SECURITY_QUERY = (
    "query FetchSecurityMarketData($id: ID!) {"
    "  security(id: $id) {"
    "    id stock { symbol name primaryExchange }"
    "    fundamentals {"
    "      marketCap peRatio eps yield high52Week low52Week"
    "      avgVolume dailyVolume sharesOutstanding currency } } }"
)

_HIST_QUERY = (
    "query FetchChartBarQuotes($id: ID!, $period: ChartPeriod) {"
    "  security(id: $id) {"
    "    id chartBarQuotes(period: $period) {"
    "      price sessionPrice timestamp currency } } }"
)

# Friendly range -> WS ChartPeriod enum.
_CHART_PERIODS = {
    "1d": "ONE_DAY",
    "1w": "ONE_WEEK",
    "1m": "ONE_MONTH",
    "3m": "THREE_MONTHS",
    "1y": "ONE_YEAR",
    "5y": "FIVE_YEARS",
}

_NETWORTH_QUERY = (
    "query FetchIdentityCurrentFinancials($identityId: ID!, $currency: Currency!) {"
    "  identity(id: $identityId) {"
    "    id financials(filter: {}) {"
    "      current(currency: $currency) {"
    "        netLiquidationValueV2 { amount currency }"
    "        netDeposits: netDepositsV2 { amount currency }"
    "        simpleReturns(referenceDate: null) { amount { amount } rate } } } } }"
)

_REALIZED_QUERY = (
    "query FetchIdentityRealizedReturns($identityId: ID!, $currency: Currency!, $first: Int) {"
    "  identity(id: $identityId) {"
    "    id financials(filter: {}) {"
    "      realizedReturns(currency: $currency) {"
    "        totalValue { amount currency }"
    "        securityBreakdown(first: $first) { edges { node {"
    "          security { stock { symbol name } }"
    "          totalValue { amount currency } } } } } } } }"
)

_DIVIDENDS_QUERY = (
    "query FetchDividendsV2($identityId: ID!, $currency: Currency!) {"
    "  identity(id: $identityId) {"
    "    id financials(filter: {}) {"
    "      dividendsV2(currency: $currency) {"
    "        totalValue { amount currency }"
    "        issuingSecurityBreakdown {"
    "          security { stock { symbol name } }"
    "          totalValue { amount currency } } } } } }"
)

_SEC_DIVIDEND_QUERY = (
    "query FetchSecurityDividendDetails($securityId: ID!) {"
    "  security(id: $securityId) {"
    "    id currency fundamentals { yield }"
    "    events { exDividendDate payableDate recordDate }"
    "    stock { dividendFrequency } } }"
)

_PORTFOLIO_HISTORY_QUERY = (
    "query FetchIdentityHistoricalFinancials("
    "$identityId: ID!, $currency: Currency!, $startDate: Date, $first: Int) {"
    "  identity(id: $identityId) {"
    "    id financials(filter: {}) {"
    "      historicalDaily(currency: $currency, startDate: $startDate, first: $first) {"
    "        edges { node { date netLiquidationValueV2 { amount currency } } } } } } }"
)

_SEC_INFO_QUERY = (
    "query FetchSecurityMarketData($id: ID!) {"
    "  security(id: $id) {"
    "    id allowedOrderSubtypes managementExpenseRatio"
    "    marginRates { clientMarginRate }"
    "    fundamentals {"
    "      marketCap peRatio eps yield high52Week low52Week beta"
    "      avgVolume dailyVolume sharesOutstanding companyRevenue"
    "      description currency }"
    "    stock { symbol name primaryExchange dividendFrequency } } }"
)

_PROFILE_QUERY = (
    "query FetchProfile($id: ID!) {"
    "  identity(id: $id) {"
    "    id accounts(first: 1) { edges { node { accountOwners {"
    "      name email identityId ownershipType } } } } } }"
)

_CREDIT_CARD_QUERY = (
    "query FetchCreditCardAccount($id: ID!) {"
    "  creditCardAccount(id: $id) {"
    "    id creditLimit"
    "    balance { current outstanding availableCreditLimit pending }"
    "    currentCards { cardNumber cardStatus nameOnCard isLocked } } }"
)


class WSError(Exception):
    """Any failure talking to Wealthsimple (bootstrap, login, OTP, GraphQL)."""


class OTPRequired(WSError):
    """2FA code required — call login() again with otp=."""


class Session:
    """An authenticated Wealthsimple session. Create via :func:`login`."""

    def __init__(self, http: requests.Session, access_token: str, device_id: str) -> None:
        self._http = http
        self._access_token = access_token
        self._device_id = device_id
        self._session_id = str(uuid.uuid4())
        self._identity_id: Optional[str] = None

    @property
    def identity_id(self) -> str:
        """The `identity-...` id, decoded from the access token's JWT claims."""
        if self._identity_id is None:
            try:
                payload_b64 = self._access_token.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            except Exception as exc:
                raise WSError(f"Couldn't decode identity from token: {exc}") from exc
            ident = next(
                (v for v in claims.values() if isinstance(v, str) and v.startswith("identity-")),
                None,
            )
            if not ident:
                raise WSError("No identity id found in token claims.")
            self._identity_id = ident
        return self._identity_id

    def _graphql(self, operation: str, query: str, variables: dict[str, Any]) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "x-ws-profile": "trade",
            "x-ws-api-version": GRAPHQL_VERSION,
            "x-ws-locale": "en-CA",
            "x-ws-device-id": self._device_id,
            "x-ws-session-id": self._session_id,
            "x-platform-os": "web",
        }
        body = {"operationName": operation, "query": query, "variables": variables}
        try:
            resp = self._http.post(
                GRAPHQL_URL, json=body, headers=headers, impersonate=IMPERSONATE
            )
        except Exception as exc:  # curl_cffi network errors
            raise WSError(f"GraphQL request failed: {exc}") from exc
        payload = resp.json()
        if "data" not in payload or payload["data"] is None:
            raise WSError(f"GraphQL error for {operation}: {payload.get('errors', payload)}")
        return payload["data"]

    def quote(self, symbol: str) -> dict[str, Any]:
        """Look up ``symbol`` and return its latest daily price.

        Returns a dict: symbol, name, exchange, security_id, market_status,
        last_price, currency, as_of. Raises WSError if the symbol isn't found.
        """
        data = self._graphql("FetchSecuritySearchResult", _SEARCH_QUERY, {"query": symbol})
        results = data["securitySearch"]["results"]
        match = next(
            (r for r in results if r["stock"]["symbol"].upper() == symbol.upper()),
            results[0] if results else None,
        )
        if match is None:
            raise WSError(f"No security found for {symbol!r}")

        q = match.get("quoteV2") or {}
        price = q.get("price") or q.get("last")
        prev = q.get("referenceClose")
        change = None
        if price is not None and prev not in (None, "0"):
            try:
                change = round((float(price) - float(prev)) / float(prev) * 100, 2)
            except (TypeError, ValueError, ZeroDivisionError):
                change = None
        return {
            "symbol": match["stock"]["symbol"],
            "name": match["stock"]["name"],
            "exchange": match["stock"]["primaryExchange"],
            "security_id": match["id"],
            "market_status": q.get("marketStatus"),
            "price": price,
            "bid": q.get("bid"),
            "ask": q.get("ask"),
            "open": q.get("open"),
            "high": q.get("high"),
            "low": q.get("low"),
            "close": q.get("close"),
            "prev_close": prev,
            "volume": q.get("volume"),
            "change_pct": change,
            "currency": q.get("currency"),
        }

    def accounts(self) -> list[dict[str, Any]]:
        """List your accounts: id, type, nickname, currency, status, value."""
        data = self._graphql(
            "FetchAccounts", _ACCOUNTS_QUERY, {"identityId": self.identity_id}
        )
        out = []
        for edge in data["identity"]["accounts"]["edges"]:
            n = edge["node"]
            nlv = (((n.get("financials") or {}).get("currentCombined")) or {}).get(
                "netLiquidationValueV2"
            ) or {}
            out.append(
                {
                    "id": n["id"],
                    "type": n["unifiedAccountType"],
                    "nickname": n.get("nickname"),
                    "currency": n["currency"],
                    "status": n["status"],
                    "value": nlv.get("amount"),
                }
            )
        return out

    def activities(self, limit: int = 10) -> list[dict[str, Any]]:
        """Recent activity feed items (deposits, trades, etc.), newest first."""
        data = self._graphql("FetchActivityFeedItems", _ACTIVITIES_QUERY, {"first": limit})
        return [e["node"] for e in data["activityFeedItems"]["edges"]]

    def positions(self, currency: str = "CAD", limit: int = 50) -> list[dict[str, Any]]:
        """Your aggregated holdings: symbol, quantity, book/market value, unrealized P&L."""
        data = self._graphql(
            "FetchIdentityPositions",
            _POSITIONS_QUERY,
            {"identityId": self.identity_id, "currency": currency, "first": limit},
        )
        edges = data["identity"]["financials"]["current"]["positions"]["edges"]
        out = []
        for e in edges:
            n = e["node"]
            stock = (n["security"].get("stock") or {})
            out.append(
                {
                    "symbol": stock.get("symbol"),
                    "name": stock.get("name"),
                    "quantity": n.get("quantity"),
                    "direction": n.get("positionDirection"),
                    "book_value": (n.get("bookValue") or {}).get("amount"),
                    "market_value": (n.get("totalValue") or {}).get("amount"),
                    "unrealized_pnl": (n.get("unrealizedReturns") or {}).get("amount"),
                    "pct_of_account": n.get("percentageOfAccount"),
                    "currency": (n.get("totalValue") or {}).get("currency"),
                }
            )
        return out

    def security(self, symbol: str) -> dict[str, Any]:
        """Fundamentals for ``symbol``: market cap, P/E, EPS, yield, 52wk range, volume."""
        sec_id = self._resolve_security_id(symbol)
        data = self._graphql("FetchSecurityMarketData", _SECURITY_QUERY, {"id": sec_id})
        sec = data["security"]
        return {
            "symbol": (sec.get("stock") or {}).get("symbol"),
            "name": (sec.get("stock") or {}).get("name"),
            "security_id": sec_id,
            **(sec.get("fundamentals") or {}),
        }

    def historical_quotes(self, symbol: str, timerange: str = "1m") -> list[dict[str, Any]]:
        """Price history. ``timerange``: 1d, 1w, 1m, 3m, 1y, 5y."""
        period = _CHART_PERIODS.get(timerange.lower())
        if period is None:
            raise WSError(f"timerange must be one of {sorted(_CHART_PERIODS)}")
        sec_id = self._resolve_security_id(symbol)
        data = self._graphql(
            "FetchChartBarQuotes", _HIST_QUERY, {"id": sec_id, "period": period}
        )
        return data["security"]["chartBarQuotes"]

    @property
    def token_claims(self) -> dict[str, Any]:
        """Decoded access-token JWT claims (sub, scope, client_id, iat, exp)."""
        payload_b64 = self._access_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))

    def me(self) -> dict[str, Any]:
        """Your profile: name, email, identity id, plus token scope and expiry."""
        data = self._graphql("FetchProfile", _PROFILE_QUERY, {"id": self.identity_id})
        owners = data["identity"]["accounts"]["edges"][0]["node"]["accountOwners"]
        owner = next(
            (o for o in owners if o.get("identityId") == self.identity_id),
            owners[0] if owners else {},
        )
        claims = self.token_claims
        exp = claims.get("exp")
        return {
            "name": owner.get("name"),
            "email": owner.get("email"),
            "identity_id": self.identity_id,
            "ownership_type": owner.get("ownershipType"),
            "scope": claims.get("scope"),
            "client_id": claims.get("client_id"),
            "token_expires": (
                datetime.fromtimestamp(exp, timezone.utc).isoformat() if exp else None
            ),
            "token_expired": bool(exp and exp < datetime.now(timezone.utc).timestamp()),
        }

    def net_worth(self, currency: str = "CAD") -> dict[str, Any]:
        """Combined value across all accounts + simple return (amount and rate)."""
        data = self._graphql(
            "FetchIdentityCurrentFinancials",
            _NETWORTH_QUERY,
            {"identityId": self.identity_id, "currency": currency},
        )
        cur = data["identity"]["financials"]["current"]
        sr = cur.get("simpleReturns") or {}
        return {
            "net_value": (cur.get("netLiquidationValueV2") or {}).get("amount"),
            "net_deposits": (cur.get("netDeposits") or {}).get("amount"),
            "return_amount": ((sr.get("amount") or {}).get("amount")),
            "return_rate": sr.get("rate"),
            "currency": currency,
        }

    def realized_returns(self, currency: str = "CAD", limit: int = 25) -> dict[str, Any]:
        """Total realized P&L + per-security breakdown."""
        data = self._graphql(
            "FetchIdentityRealizedReturns",
            _REALIZED_QUERY,
            {"identityId": self.identity_id, "currency": currency, "first": limit},
        )
        rr = data["identity"]["financials"]["realizedReturns"]
        return {
            "total": (rr.get("totalValue") or {}).get("amount"),
            "currency": currency,
            "by_security": [
                {
                    "symbol": (e["node"]["security"].get("stock") or {}).get("symbol"),
                    "amount": (e["node"].get("totalValue") or {}).get("amount"),
                }
                for e in rr["securityBreakdown"]["edges"]
            ],
        }

    def dividends(self, currency: str = "CAD") -> dict[str, Any]:
        """Total dividend income + per-security breakdown."""
        data = self._graphql(
            "FetchDividendsV2",
            _DIVIDENDS_QUERY,
            {"identityId": self.identity_id, "currency": currency},
        )
        dv = data["identity"]["financials"]["dividendsV2"]
        return {
            "total": (dv.get("totalValue") or {}).get("amount"),
            "currency": currency,
            "by_security": [
                {
                    "symbol": (b["security"].get("stock") or {}).get("symbol"),
                    "amount": (b.get("totalValue") or {}).get("amount"),
                }
                for b in (dv.get("issuingSecurityBreakdown") or [])
            ],
        }

    def security_dividend(self, symbol: str) -> dict[str, Any]:
        """Dividend details for ``symbol``: yield, frequency, ex-div/record/payable dates."""
        sec_id = self._resolve_security_id(symbol)
        data = self._graphql("FetchSecurityDividendDetails", _SEC_DIVIDEND_QUERY, {"securityId": sec_id})
        sec = data["security"]
        ev = sec.get("events") or {}
        return {
            "yield": (sec.get("fundamentals") or {}).get("yield"),
            "frequency": (sec.get("stock") or {}).get("dividendFrequency"),
            "ex_dividend_date": ev.get("exDividendDate"),
            "record_date": ev.get("recordDate"),
            "payable_date": ev.get("payableDate"),
        }

    def portfolio_history(
        self, days: int = 90, currency: str = "CAD"
    ) -> list[dict[str, Any]]:
        """Daily net-worth series for the last ``days`` (for charting account value)."""
        start = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        data = self._graphql(
            "FetchIdentityHistoricalFinancials",
            _PORTFOLIO_HISTORY_QUERY,
            {"identityId": self.identity_id, "currency": currency, "startDate": start, "first": days + 5},
        )
        edges = data["identity"]["financials"]["historicalDaily"]["edges"]
        return [
            {"date": e["node"]["date"], "value": (e["node"].get("netLiquidationValueV2") or {}).get("amount")}
            for e in edges
        ]

    def security_info(self, symbol: str) -> dict[str, Any]:
        """Full security data: fundamentals, margin rate, MER, order subtypes, exchange."""
        sec_id = self._resolve_security_id(symbol)
        data = self._graphql("FetchSecurityMarketData", _SEC_INFO_QUERY, {"id": sec_id})
        sec = data["security"]
        return {
            "symbol": (sec.get("stock") or {}).get("symbol"),
            "name": (sec.get("stock") or {}).get("name"),
            "exchange": (sec.get("stock") or {}).get("primaryExchange"),
            "dividend_frequency": (sec.get("stock") or {}).get("dividendFrequency"),
            "allowed_order_subtypes": sec.get("allowedOrderSubtypes"),
            "mer": sec.get("managementExpenseRatio"),
            "margin_rate": (sec.get("marginRates") or {}).get("clientMarginRate"),
            **(sec.get("fundamentals") or {}),
        }

    def credit_card(self) -> Optional[dict[str, Any]]:
        """Credit-card account: limit, balances, cards. None if you have no card account."""
        card_acct = next(
            (a for a in self.accounts() if a["type"] == "CREDIT_CARD"), None
        )
        if card_acct is None:
            return None
        data = self._graphql("FetchCreditCardAccount", _CREDIT_CARD_QUERY, {"id": card_acct["id"]})
        return data["creditCardAccount"]

    def _resolve_security_id(self, symbol: str) -> str:
        """Search ``symbol`` and return the best-matching WS security id."""
        data = self._graphql("FetchSecuritySearchResult", _SEARCH_QUERY, {"query": symbol})
        results = data["securitySearch"]["results"]
        match = next(
            (r for r in results if r["stock"]["symbol"].upper() == symbol.upper()),
            results[0] if results else None,
        )
        if match is None:
            raise WSError(f"No security found for {symbol!r}")
        return match["id"]


def _bootstrap(http: requests.Session) -> tuple[str, str]:
    """Fetch device id (wssdi cookie) and production client_id from the login page."""
    try:
        resp = http.get(LOGIN_PAGE_URL, impersonate=IMPERSONATE)
    except Exception as exc:
        raise WSError(f"Bootstrap request failed: {exc}") from exc

    device_id = resp.cookies.get("wssdi")
    if not device_id:
        m = re.search(r"wssdi=([a-f0-9-]+)", "; ".join(f"{k}={v}" for k, v in resp.cookies.items()))
        device_id = m.group(1) if m else None
    if not device_id:
        raise WSError("Couldn't find wssdi (device id) on login page.")

    m = re.search(r'<script[^>]+src="([^"]+/app-[a-f0-9]+\.js)"', resp.text, re.IGNORECASE)
    if not m:
        raise WSError("Couldn't find app JS bundle URL on login page.")
    js = http.get(m.group(1), impersonate=IMPERSONATE)
    m = re.search(r'"production"[^}]*clientId:"([a-f0-9]+)"', js.text, re.IGNORECASE)
    if not m:
        raise WSError("Couldn't find production clientId in app JS.")
    return device_id, m.group(1)


def from_refresh_token(
    refresh_token: str,
    device_id: Optional[str] = None,
    client_id: Optional[str] = None,
) -> Session:
    """Exchange a refresh token for a fresh access token and return a Session.

    Best path for passkey/2FA accounts: grab the refresh token once from the browser,
    then this mints new access tokens without any login or OTP. ``device_id`` and
    ``client_id`` are bootstrapped from the login page if not supplied.
    """
    http = requests.Session()
    if not device_id or not client_id:
        boot_device, boot_client = _bootstrap(http)
        device_id = device_id or boot_device
        client_id = client_id or boot_client

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    headers = {
        "Content-Type": "application/json",
        "x-wealthsimple-client": "@wealthsimple/wealthsimple",
        "x-ws-profile": "invest",
        "x-ws-device-id": device_id,
    }
    try:
        resp = http.post(OAUTH_TOKEN_URL, json=data, headers=headers, impersonate=IMPERSONATE)
    except Exception as exc:
        raise WSError(f"Refresh request failed: {exc}") from exc
    payload = resp.json()
    if "access_token" not in payload:
        raise WSError(f"Refresh failed: {payload.get('error_description', payload)}")
    return Session(http, payload["access_token"], device_id)


def login(
    email: str,
    password: str,
    otp: Optional[str] = None,
    scope: str = SCOPE_READ_ONLY,
) -> Session:
    """Log in and return an authenticated :class:`Session`.

    On first call without ``otp`` for a 2FA account, raises :class:`OTPRequired`;
    call again passing the TOTP code as ``otp``.
    """
    http = requests.Session()
    device_id, client_id = _bootstrap(http)

    data = {
        "grant_type": "password",
        "username": email,
        "password": password,
        "skip_provision": "true",
        "scope": scope,
        "client_id": client_id,
        "otp_claim": None,
    }
    headers = {
        "Content-Type": "application/json",
        "x-wealthsimple-client": "@wealthsimple/wealthsimple",
        "x-ws-profile": "undefined",
        "x-ws-device-id": device_id,
    }
    if otp:
        headers["x-wealthsimple-otp"] = f"{otp};remember=true"

    try:
        resp = http.post(OAUTH_TOKEN_URL, json=data, headers=headers, impersonate=IMPERSONATE)
    except Exception as exc:
        raise WSError(f"Login request failed: {exc}") from exc
    payload = resp.json()

    if payload.get("error") == "invalid_grant" and otp is None:
        raise OTPRequired("2FA code required — call login() again with otp=<code>.")
    if "error" in payload or "access_token" not in payload:
        raise WSError(f"Login failed: {payload.get('error_description', payload)}")

    return Session(http, payload["access_token"], device_id)
