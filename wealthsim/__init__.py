"""wealthsim — tiny standalone Wealthsimple client. Login + one thing: quote a symbol.

Unofficial. Wealthsimple has no public API; this talks to their private GraphQL
backend. Use at your own risk (their ToS forbids automated access; worst case is an
account lock). Read-only scope only.

    from wealthsim import login
    ws = login("you@example.com", "password", otp="123456")
    print(ws.quote("AAPL"))
"""

from __future__ import annotations

from .client import OTPRequired, Session, WSError, from_refresh_token, login

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
]
__version__ = "0.1.0"
