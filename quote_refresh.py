"""Quote a symbol using a browser-grabbed REFRESH token (mints fresh access tokens).

Values read from prompt/env so they never get hard-coded or pasted anywhere shared:

    python quote_refresh.py AAPL

Refresh token: the `refresh_token` value from the OAuth response in DevTools
(Network -> the `token` request -> Response), the long JWT.
Device id: the `x-ws-device-id` request header value.
"""

import os
import sys

from wealthsim import WSError, from_refresh_token


def clean(v: str) -> str:
    v = v.strip().strip('"').strip("'").strip()
    if v.lower().startswith("bearer "):
        v = v[7:].strip()
    return v


refresh = clean(os.environ.get("WS_REFRESH") or input("Refresh token: "))
device_id = clean(os.environ.get("WS_DEVICE_ID") or input("x-ws-device-id: "))
symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

try:
    ws = from_refresh_token(refresh, device_id=device_id)
    print(ws.quote(symbol))
except WSError as e:
    print("ERROR:", e)
