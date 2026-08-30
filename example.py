"""Run the quote path against a real account.

Credentials come from env vars / interactive prompt so they never get hard-coded.
Run it yourself:  python example.py   (or in Claude Code:  ! python example.py)

    set WS_EMAIL=you@example.com
    set WS_PASSWORD=...
    python example.py
"""

import getpass
import os

from wealthsim import OTPRequired, login

email = os.environ.get("WS_EMAIL") or input("Wealthsimple email: ")
password = os.environ.get("WS_PASSWORD") or getpass.getpass("Password: ")

try:
    ws = login(email, password)
except OTPRequired:
    code = input("2FA code: ")
    ws = login(email, password, otp=code)

print(ws.quote("AAPL"))
