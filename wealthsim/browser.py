"""Browser-assisted login for passkey/2FA accounts.

Opens your real Chrome to the Wealthsimple login page; you complete the passkey
(Windows Hello / phone). We capture the token the browser earns from the first
post-login GraphQL request, optionally cache it, and return an authed Client.

Requires: pip install playwright   (uses your installed Chrome via channel="chrome").
"""

from __future__ import annotations

import json
from typing import Optional

from curl_cffi import requests as _cffi

from .client import GRAPHQL_URL, Session, WSError


def login_via_browser(
    cache_path: Optional[str] = ".env",
    timeout_sec: int = 180,
) -> Session:
    """Interactive passkey login. Returns an authed :class:`Session` (a.k.a. Client).

    If ``cache_path`` is set, the captured tokens are written there as JSON for reuse.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise WSError("playwright not installed. Run: pip install playwright") from exc

    captured: dict[str, str] = {}

    def is_user_graphql(req) -> bool:
        return GRAPHQL_URL in req.url and req.headers.get(
            "authorization", ""
        ).lower().startswith("bearer ")

    def on_request(req) -> None:
        if is_user_graphql(req) and "access_token" not in captured:
            captured["access_token"] = req.headers["authorization"][7:]
            dev = req.headers.get("x-ws-device-id")
            if dev:
                captured["device_id"] = dev

    def on_response(resp) -> None:
        if resp.url.endswith("/token") and resp.request.method == "POST":
            try:
                body = resp.json()
            except Exception:
                return
            if "refresh_token" in body:
                captured["refresh_token"] = body["refresh_token"]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        page = browser.new_page()
        page.on("request", on_request)
        page.on("response", on_response)
        page.goto("https://my.wealthsimple.com/app/login")
        print(">>> Log in with your passkey in the browser window...")
        try:
            page.wait_for_event("request", predicate=is_user_graphql, timeout=timeout_sec * 1000)
        except Exception:
            pass
        browser.close()

    if "access_token" not in captured:
        raise WSError("No token captured — did login complete in the browser?")

    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(captured, f, indent=2)

    return Session(
        _cffi.Session(),
        access_token=captured["access_token"],
        device_id=captured.get("device_id", ""),
    )


def load_cached(cache_path: str = ".env") -> Session:
    """Build a Client from previously cached tokens. Raises if the file is missing."""
    with open(cache_path) as f:
        tok = json.load(f)
    return Session(
        _cffi.Session(),
        access_token=tok["access_token"],
        device_id=tok.get("device_id", ""),
    )
