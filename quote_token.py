"""Quote a symbol using a browser-grabbed access token (for passkey accounts).

Token + device id are read from env vars or an interactive prompt, so they never
get hard-coded or pasted anywhere shared. Run it yourself:

    python quote_token.py                # prompts for both
    # or set them first:
    $env:WS_TOKEN="eyJhbGci..."          # value AFTER "Bearer ", no "Bearer " prefix
    $env:WS_DEVICE_ID="226d18b3-...."    # the x-ws-device-id header value
    python quote_token.py AAPL

Token format: the raw JWT from the `authorization: Bearer <THIS>` header.
Do NOT include the word "Bearer". Device id: the `x-ws-device-id` header value.
"""

import os
import sys

from curl_cffi import requests

from wealthsim import Session

token = os.environ.get("WS_TOKEN") or input("Bearer access token: ").strip()
device_id = os.environ.get("WS_DEVICE_ID") or input("x-ws-device-id: ").strip()
symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

# sanitize a copy/pasted header value: surrounding quotes, an "authorization:"
# label, and/or a leading "Bearer " — keep only the raw JWT.
token = token.strip().strip('"').strip("'").strip()
if ":" in token.split(".")[0]:  # e.g. "authorization: Bearer eyJ..."
    token = token.split(":", 1)[1].strip()
if token.lower().startswith("bearer "):
    token = token[7:].strip()
token = token.strip().strip('"').strip("'").strip()
device_id = device_id.strip().strip('"').strip("'").strip()

ws = Session(requests.Session(), access_token=token, device_id=device_id)
print(ws.quote(symbol))
