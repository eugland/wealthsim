"""Browser-assisted login for passkey accounts.

Opens your real Chrome to the Wealthsimple login page. YOU log in with your passkey
(Windows Hello / phone). The script watches the network, captures the access token
(and refresh token if seen), saves them to .env, then quotes a symbol.

    pip install playwright
    python -m playwright install chromium   # or rely on channel="chrome" below
    python browser_auth.py AAPL

Nothing is typed by the script — it only reads the tokens the browser already obtained.
"""

import json
import sys

from playwright.sync_api import sync_playwright

from wealthsim import Session
from curl_cffi import requests as cffi_requests

symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
captured: dict[str, str] = {}


def _is_user_graphql(req) -> bool:
    # Only /graphql carries the real user token, and only after login succeeds.
    # (WS sends an anonymous Bearer on pre-login bootstrap calls — ignore those.)
    return "/graphql" in req.url and req.headers.get("authorization", "").lower().startswith(
        "bearer "
    )


def on_request(req):
    if _is_user_graphql(req) and "access_token" not in captured:
        captured["access_token"] = req.headers["authorization"][7:]
        dev = req.headers.get("x-ws-device-id")
        if dev:
            captured["device_id"] = dev
        print("captured user access token from a graphql request.")


def on_response(resp):
    if resp.url.endswith("/token") and resp.request.method == "POST":
        try:
            body = resp.json()
        except Exception:
            return
        if "refresh_token" in body:
            captured["refresh_token"] = body["refresh_token"]
            captured.setdefault("access_token", body.get("access_token", ""))
            print("captured refresh token from token response.")


with sync_playwright() as p:
    # channel="chrome" uses your installed Chrome so the OS passkey prompt works.
    browser = p.chromium.launch(channel="chrome", headless=False)
    page = browser.new_page()
    page.on("request", on_request)
    page.on("response", on_response)
    page.goto("https://my.wealthsimple.com/app/login")

    print("\n>>> Log in with your passkey in the browser window.")
    print(">>> Waiting for a token... (up to 3 min)\n")
    try:
        page.wait_for_event("request", predicate=_is_user_graphql, timeout=180_000)
    except Exception:
        pass
    browser.close()

if "access_token" not in captured:
    print("No token captured. Did login complete?")
    sys.exit(1)

# Persist whatever we got (access + refresh if present) for reuse.
with open(".env", "w") as f:
    json.dump(captured, f, indent=2)
print("saved tokens to .env")

ws = Session(
    cffi_requests.Session(),
    access_token=captured["access_token"],
    device_id=captured.get("device_id", ""),
)
print(ws.quote(symbol))
