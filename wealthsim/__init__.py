"""wealthsim — tiny standalone Wealthsimple client. Login + one thing: quote a symbol.

Unofficial. Wealthsimple has no public API; this talks to their private GraphQL
backend. Use at your own risk (their ToS forbids automated access; worst case is an
account lock). Read-only scope only.

    from wealthsim import login
    ws = login("you@example.com", "password", otp="123456")
    print(ws.quote("AAPL"))

DISCLAIMER
==========
Provided "AS IS", without warranty of any kind. NOT affiliated with, authorized by,
or endorsed by Wealthsimple Technologies Inc. NOT financial, investment, tax, or legal
advice. Data comes from an undocumented private API and may be wrong, stale, or
unavailable — always verify in the official app before acting. To the maximum extent
permitted by law, the authors are NOT liable for any loss (financial or otherwise)
arising from use of this software. Automated access may violate Wealthsimple's Terms
of Service; complying with those terms is your responsibility. See README "Disclaimer".
"""

from __future__ import annotations

from .client import LoginFailed, OTPRequired, Session, WSError, from_refresh_token, login

# Session is the client; expose a friendlier alias.
Client = Session


def __getattr__(name: str):  # lazy: keep playwright import optional
    if name in ("login_via_browser", "load_cached"):
        from . import browser

        return getattr(browser, name)
    raise AttributeError(name)


__all__ = [
    "Client",
    "Session",
    "login",
    "from_refresh_token",
    "login_via_browser",
    "load_cached",
    "WSError",
    "OTPRequired",
    "LoginFailed",
]
__version__ = "0.3.0"
