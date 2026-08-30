"""wealthsim CLI — run against the token saved in .env.

    python run_env.py quote AAPL
    python run_env.py accounts
    python run_env.py activities 10
    python run_env.py whoami

Reloads the .env token each run. Re-run browser_auth.py when it expires.
"""

import json
import sys

from curl_cffi import requests

from wealthsim import Session, WSError

sys.stdout.reconfigure(encoding="utf-8")  # Windows console: allow emoji nicknames

def make_session() -> Session:
    with open(".env") as f:
        tok = json.load(f)
    return Session(
        requests.Session(),
        access_token=tok["access_token"],
        device_id=tok.get("device_id", ""),
    )


def cmd_quote(ws: Session, args: list[str]) -> None:
    symbol = args[0] if args else "AAPL"
    q = ws.quote(symbol)
    print(f"{q['symbol']} ({q['name']}, {q['exchange']})")
    print(f"  price {q['price']} {q['currency']}   bid {q['bid']} / ask {q['ask']}   [{q['market_status']}]")


def cmd_accounts(ws: Session, args: list[str]) -> None:
    for a in ws.accounts():
        nick = a.get("nickname") or "-"
        print(f"  {a['type']:<40} {nick:<16} {a['value'] or '0':>18} {a['currency']}  [{a['status']}]")


def cmd_activities(ws: Session, args: list[str]) -> None:
    limit = int(args[0]) if args else 10
    for act in ws.activities(limit):
        print(f"  {act.get('occurredAt', '')[:10]}  {act.get('type'):<18} "
              f"{act.get('subType') or '':<16} {act.get('amountSign') or ''}{act.get('amount') or ''} "
              f"{act.get('currency') or ''}  {act.get('assetSymbol') or ''}")


def cmd_whoami(ws: Session, args: list[str]) -> None:
    for k, v in ws.me().items():
        print(f"  {k:<16} {v}")


def cmd_positions(ws: Session, args: list[str]) -> None:
    for p in ws.positions():
        print(f"  {p['symbol'] or '?':<8} qty {p['quantity']:<12} "
              f"mkt {p['market_value'] or '0':>14} {p['currency'] or ''}  "
              f"pnl {p['unrealized_pnl'] or '0'}")


def cmd_security(ws: Session, args: list[str]) -> None:
    s = ws.security(args[0] if args else "AAPL")
    print(f"{s['symbol']} ({s['name']})")
    for k in ("marketCap", "peRatio", "eps", "yield", "high52Week", "low52Week", "dailyVolume"):
        print(f"  {k:<12} {s.get(k)}")


def cmd_history(ws: Session, args: list[str]) -> None:
    sym = args[0] if args else "AAPL"
    rng = args[1] if len(args) > 1 else "1m"
    quotes = ws.historical_quotes(sym, rng)
    print(f"{sym} {rng}: {len(quotes)} points")
    for h in (quotes[:3] + ["..."] + quotes[-3:] if len(quotes) > 6 else quotes):
        if h == "...":
            print("  ...")
        else:
            print(f"  {h.get('timestamp', '')[:10]}  {h.get('price')} {h.get('currency')}")


def cmd_networth(ws: Session, args: list[str]) -> None:
    n = ws.net_worth()
    print(f"  net value   {n['net_value']} {n['currency']}")
    print(f"  deposits    {n['net_deposits']}")
    print(f"  return      {n['return_amount']} ({n['return_rate']})")


def cmd_returns(ws: Session, args: list[str]) -> None:
    r = ws.realized_returns(limit=int(args[0]) if args else 15)
    print(f"  total realized: {r['total']} {r['currency']}")
    for b in r["by_security"]:
        print(f"    {b['symbol'] or '?':<10} {b['amount']}")


def cmd_dividends(ws: Session, args: list[str]) -> None:
    d = ws.dividends()
    print(f"  total dividends: {d['total']} {d['currency']}")
    for b in d["by_security"][:15]:
        print(f"    {b['symbol'] or '?':<10} {b['amount']}")


def cmd_secinfo(ws: Session, args: list[str]) -> None:
    s = ws.security_info(args[0] if args else "AAPL")
    for k, v in s.items():
        if k != "description":
            print(f"  {k:<22} {v}")


def cmd_secdiv(ws: Session, args: list[str]) -> None:
    print(" ", ws.security_dividend(args[0] if args else "AAPL"))


def cmd_portfolio(ws: Session, args: list[str]) -> None:
    days = int(args[0]) if args else 90
    h = ws.portfolio_history(days=days)
    print(f"  {len(h)} days; {h[0]['date']}={h[0]['value'][:8]} -> {h[-1]['date']}={h[-1]['value'][:8]}")


def cmd_creditcard(ws: Session, args: list[str]) -> None:
    print(" ", ws.credit_card())


COMMANDS = {
    "quote": cmd_quote,
    "accounts": cmd_accounts,
    "activities": cmd_activities,
    "positions": cmd_positions,
    "security": cmd_security,
    "secinfo": cmd_secinfo,
    "secdiv": cmd_secdiv,
    "history": cmd_history,
    "networth": cmd_networth,
    "returns": cmd_returns,
    "dividends": cmd_dividends,
    "portfolio": cmd_portfolio,
    "creditcard": cmd_creditcard,
    "whoami": cmd_whoami,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("usage: python run_env.py {" + "|".join(COMMANDS) + "} [args]")
        sys.exit(1)
    cmd, rest = sys.argv[1], sys.argv[2:]
    try:
        COMMANDS[cmd](make_session(), rest)
    except WSError as e:
        msg = str(e)
        if "UNAUTHENTICATED" in msg or "Not Authorized" in msg:
            print("ERROR: token expired — rerun:  python browser_auth.py")
        else:
            print("ERROR:", msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
