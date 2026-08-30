"""Save a browser-grabbed access token to .env (no login needed).

Copy the token from your already-logged-in browser:
  DevTools -> Network -> any `graphql` request -> Headers -> Request Headers
  -> `authorization: Bearer <TOKEN>`  (copy the part after "Bearer")

Then run:  python set_token.py
Paste the token at the prompt (quotes / "Bearer" prefix are stripped automatically).
"""

import json
import os

token = os.environ.get("WS_TOKEN") or input("Bearer access token: ")
device_id = os.environ.get("WS_DEVICE_ID") or input("x-ws-device-id: ").strip()

token = token.strip().strip('"').strip("'").strip()
if token.lower().startswith("bearer "):
    token = token[7:].strip()

with open(".env", "w") as f:
    json.dump({"access_token": token, "device_id": device_id}, f, indent=2)

print("saved .env — now run: python run_env.py positions")
