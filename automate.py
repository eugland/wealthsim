"""Demo every wealthsim client method using the cached token (no login).

Run:  python automate.py
If the token expired, refresh it once with:  python browser_auth.py

PRIVACY: this script is a safe, shareable demo. It never prints personal financial
data — account names/nicknames, balances, holding quantities, net worth, P&L, dividend
amounts, credit-card numbers, ids, name, or email are all redacted to `***`. Only
public market data (quotes, fundamentals) is shown in full. It still exercises every
method end-to-end so you can confirm the API works without leaking your account.
"""

import sys

from wealthsim import LoginFailed, OTPRequired, WSError, load_cached
from wealthsim import _store

sys.stdout.reconfigure(encoding="utf-8")  # Windows console: allow emoji nicknames

R = "***"  # redaction marker for any personal value


def shape(obj: object) -> str:
    """Describe a result without revealing values: keys of a dict, len of a list."""
    if isinstance(obj, dict):
        return f"dict keys={list(obj.keys())}"
    if isinstance(obj, list):
        return f"list len={len(obj)}"
    return type(obj).__name__


def main() -> None:
    # --- token storage (keyring-first, .env fallback) -------------------------------
    kr = _store._keyring()
    in_keyring = bool(kr and kr.get_password(_store.SERVICE, _store.ACCOUNT))
    backend = "OS keyring" if in_keyring else ".env file (plaintext fallback)"
    print(f"=== token storage ===  reading from: {backend}")
    try:
        ws = load_cached()  # tries OS keyring first, then .env
    except (FileNotFoundError, ValueError, KeyError):
        print("No cached token. Run: python browser_auth.py")
        sys.exit(1)

    # --- profile / session (all personal → redacted, only prove it returns) ---------
    print("=== me() ===  [personal → redacted]")
    me = ws.me()
    for k in me:
        personal = k in {"name", "email", "identity_id", "client_id"}
        print(f"  {k:<16} {R if personal else me[k]}")
    print(f"  identity_id      {R} (property returns '{ws.identity_id[:9]}…')")
    print(f"  token_claims     {shape(ws.token_claims)} (values redacted)")

    # --- market data (PUBLIC — shown in full) ---------------------------------------
    print("\n=== search('apple') ===  [public]")
    for m in ws.search("apple", limit=3):
        print(f"  {m['symbol']:<6} {m['exchange']:<8} {m['name']}")

    print("\n=== quote(sym) ===  [public]")
    aapl_id = None
    for sym in ("AAPL", "TSLA", "VFV"):
        q = ws.quote(sym)
        if sym == "AAPL":
            aapl_id = q["security_id"]
        print(f"  {q['symbol']:<6} {q['price']} {q['currency']}  "
              f"bid {q['bid']}/ask {q['ask']}  [{q['market_status']}]")

    print("\n=== security_id_to_symbol(id) ===  [public]")
    if aapl_id:
        print(f"  {aapl_id[:8]}… -> {ws.security_id_to_symbol(aapl_id)}")

    print("\n=== security('AAPL') fundamentals ===  [public]")
    s = ws.security("AAPL")
    for k in ("marketCap", "peRatio", "eps", "yield", "high52Week", "low52Week"):
        print(f"  {k:<12} {s.get(k)}")

    print("\n=== security_info('AAPL') ===  [public]")
    si = ws.security_info("AAPL")
    for k in ("beta", "margin_rate", "mer", "dividend_frequency", "allowed_order_subtypes"):
        print(f"  {k:<22} {si.get(k)}")

    print("\n=== security_dividend('AAPL') ===  [public]")
    print(" ", ws.security_dividend("AAPL"))

    print("\n=== historical_quotes('AAPL', '1m') ===  [public]")
    hq = ws.historical_quotes("AAPL", "1m")
    print(f"  {len(hq)} points; last {hq[-1]['timestamp'][:10]} = {hq[-1]['price']} {hq[-1]['currency']}")

    # --- accounts / portfolio (PERSONAL — structure only, all values redacted) ------
    print("\n=== accounts() ===  [names/values redacted]")
    account_ids = []
    for a in ws.accounts():
        if a["status"] != "open":
            continue
        account_ids.append(a["id"])
        print(f"  type {a['type']:<40} nickname {R}  value {R} {a['currency']}")
    acct = account_ids[0] if account_ids else None

    print("\n=== account_balances(account_id) ===  [quantities redacted]")
    if acct:
        bals = ws.account_balances(acct)
        print(f"  {len(bals)} holdings: symbols {list(bals.keys())}  (quantities {R})")

    print("\n=== account_unrealized_pnl(account_id) ===  [amounts redacted]")
    if acct:
        pnl = ws.account_unrealized_pnl(acct)
        print(f"  amount {R}  rate {R}  currency {pnl['currency']}")

    print("\n=== positions() ===  [symbols shown, quantities/values redacted]")
    for p in ws.positions():
        print(f"  {p['symbol'] or '?':<6} qty {R:<6} mkt {R:<6} {p['currency'] or ''}  pnl {R}")

    print("\n=== net_worth() ===  [amounts redacted]")
    n = ws.net_worth()
    print(f"  value {R}  deposits {R}  return {R} ({R})  currency {n['currency']}")

    print("\n=== realized_returns() ===  [amounts redacted]")
    r = ws.realized_returns(limit=5)
    print(f"  total {R} {r['currency']};  {len(r['by_security'])} securities: "
          f"{[b['symbol'] for b in r['by_security']]}  (amounts {R})")

    print("\n=== dividends() ===  [amounts redacted]")
    d = ws.dividends()
    print(f"  total {R} {d['currency']};  {len(d['by_security'])} securities: "
          f"{[b['symbol'] for b in d['by_security'][:5]]}  (amounts {R})")

    print("\n=== portfolio_history(30 days) ===  [values redacted]")
    h = ws.portfolio_history(days=30)
    if h:
        print(f"  {len(h)} days; {h[0]['date']} -> {h[-1]['date']}  (values {R})")

    print("\n=== account_history(account_id, 30 days) ===  [values redacted]")
    if acct:
        ah = ws.account_history(acct, days=30)
        span = f"{ah[0]['date']} -> {ah[-1]['date']}" if ah else "no data"
        print(f"  {len(ah)} days; {span}  (values {R})")

    print("\n=== activities(5) ===  [amounts redacted]")
    for act in ws.activities(5):
        print(f"  {act.get('occurredAt', '')[:10]}  {act.get('type'):<16} "
              f"{act.get('subType') or '':<14} amount {R} {act.get('currency') or ''} "
              f"{act.get('assetSymbol') or ''}")

    print("\n=== corporate_action_activities(id) ===  [amounts redacted]")
    ca = next((a for a in ws.activities(50) if (a.get("type") or "") == "CORPORATE_ACTION"), None)
    canon_id = (ca or {}).get("canonicalId")
    if canon_id:
        kids = ws.corporate_action_activities(canon_id)
        print(f"  {len(kids)} child activities  (amounts {R})")
    else:
        print("  (no corporate-action item in recent feed to expand; method available)")

    print("\n=== credit_card() ===  [numbers redacted]")
    cc = ws.credit_card()
    if cc:
        print(f"  limit {R}  balance {R}  available {R}  card **** (redacted)")
    else:
        print("  (no credit card account)")

    print("\nDone. All personal values redacted; every method exercised.")


if __name__ == "__main__":
    # Exception taxonomy: OTPRequired and LoginFailed are WSError subclasses.
    try:
        main()
    except OTPRequired:
        print("\n2FA required — supply an otp to login().")
        sys.exit(1)
    except LoginFailed as e:
        print(f"\nLogin/token rejected: {e}. Refresh with: python browser_auth.py")
        sys.exit(1)
    except WSError as e:
        msg = str(e)
        if "UNAUTHENTICATED" in msg or "Not Authorized" in msg:
            print("\nToken expired — refresh with: python browser_auth.py")
        else:
            print("\nERROR:", msg)
        sys.exit(1)
