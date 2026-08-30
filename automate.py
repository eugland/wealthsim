"""Demo every wealthsim client method using the cached .env token (no login).

Run:  python automate.py
If the token expired, refresh it once with:  python browser_auth.py
"""

import sys

from wealthsim import WSError, load_cached

sys.stdout.reconfigure(encoding="utf-8")  # Windows console: allow emoji nicknames


def main() -> None:
    try:
        ws = load_cached(".env")
    except (FileNotFoundError, ValueError, KeyError):
        print("No cached token in .env. Run: python browser_auth.py")
        sys.exit(1)

    print("=== me() ===")
    for k, v in ws.me().items():
        print(f"  {k:<16} {v}")

    print("\n=== quote(sym) ===")
    for sym in ("AAPL", "TSLA", "VFV"):
        q = ws.quote(sym)
        print(f"  {q['symbol']:<6} {q['price']} {q['currency']}  "
              f"bid {q['bid']}/ask {q['ask']}  [{q['market_status']}]")

    print("\n=== security('AAPL') fundamentals ===")
    s = ws.security("AAPL")
    for k in ("marketCap", "peRatio", "eps", "yield", "high52Week", "low52Week"):
        print(f"  {k:<12} {s.get(k)}")

    print("\n=== historical_quotes('AAPL', '1m') ===")
    hq = ws.historical_quotes("AAPL", "1m")
    print(f"  {len(hq)} points; last: {hq[-1]['timestamp'][:10]} = {hq[-1]['price']} {hq[-1]['currency']}")

    print("\n=== accounts() (open only) ===")
    for a in ws.accounts():
        if a["status"] != "open":
            continue
        nick = a.get("nickname") or "-"
        print(f"  {a['type']:<40} {nick:<14} {a['value'] or '0':>18} {a['currency']}")

    print("\n=== positions() ===")
    for p in ws.positions():
        print(f"  {p['symbol'] or '?':<6} qty {str(p['quantity']):<12} "
              f"mkt {p['market_value'] or '0':>16} {p['currency'] or ''}  pnl {p['unrealized_pnl'] or '0'}")

    print("\n=== activities(5) ===")
    for act in ws.activities(5):
        print(f"  {act.get('occurredAt', '')[:10]}  {act.get('type'):<16} "
              f"{act.get('subType') or '':<14} "
              f"{act.get('amountSign') or ''}{act.get('amount') or ''} {act.get('currency') or ''} "
              f"{act.get('assetSymbol') or ''}")

    print("\n=== net_worth() ===")
    n = ws.net_worth()
    print(f"  value {n['net_value']} {n['currency']}  deposits {n['net_deposits']}  "
          f"return {n['return_amount']} ({n['return_rate']})")

    print("\n=== realized_returns() top 5 ===")
    r = ws.realized_returns(limit=5)
    print(f"  total {r['total']} {r['currency']}")
    for b in r["by_security"]:
        print(f"    {b['symbol'] or '?':<10} {b['amount']}")

    print("\n=== dividends() top 5 ===")
    d = ws.dividends()
    print(f"  total {d['total']} {d['currency']}")
    for b in d["by_security"][:5]:
        print(f"    {b['symbol'] or '?':<10} {b['amount']}")

    print("\n=== security_info('AAPL') ===")
    si = ws.security_info("AAPL")
    for k in ("beta", "margin_rate", "mer", "dividend_frequency", "allowed_order_subtypes"):
        print(f"  {k:<22} {si.get(k)}")

    print("\n=== security_dividend('AAPL') ===")
    print(" ", ws.security_dividend("AAPL"))

    print("\n=== portfolio_history(30 days) ===")
    h = ws.portfolio_history(days=30)
    print(f"  {len(h)} days; {h[0]['date']}={h[0]['value'][:8]} -> {h[-1]['date']}={h[-1]['value'][:8]}")

    print("\n=== credit_card() ===")
    cc = ws.credit_card()
    if cc:
        print(f"  limit {cc['creditLimit']}  balance {cc['balance']['current']}  "
              f"available {cc['balance']['availableCreditLimit']}")
    else:
        print("  (no credit card account)")


if __name__ == "__main__":
    try:
        main()
    except WSError as e:
        msg = str(e)
        if "UNAUTHENTICATED" in msg or "Not Authorized" in msg:
            print("\nToken expired — refresh with: python browser_auth.py")
        else:
            print("\nERROR:", msg)
        sys.exit(1)
