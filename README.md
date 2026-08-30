# wealthsim

**Unofficial Python client for Wealthsimple** — quotes, accounts, positions, activity. Read-only.

> Not affiliated with or endorsed by Wealthsimple. Uses the private GraphQL API behind the web app. Automated access may violate Wealthsimple's terms — use at your own risk. No order placement, by design.

```python
from wealthsim import login_via_browser, load_cached

ws = login_via_browser()          # opens Chrome; you complete the passkey / 2FA
# next runs: ws = load_cached()   # reuse the cached token, no re-login

ws.quote("AAPL")                  # {'symbol': 'AAPL', 'price': '319.9', 'bid': ..., ...}
ws.accounts()                     # every account + balance
ws.positions()                    # holdings: qty, market value, unrealized P&L
ws.activities(10)                 # recent feed items
ws.security("AAPL")               # fundamentals: P/E, market cap, yield, 52wk range
ws.historical_quotes("AAPL", "1m")# daily price history
ws.identity_id                    # your identity id (decoded from the token)
```

```bash
pip install curl_cffi playwright
```

## Auth

Wealthsimple has no public API and (for passkey/2FA accounts) can't be logged into headlessly.
`login_via_browser()` opens your real Chrome, **you** complete the passkey, and it captures the
access token from the first post-login request — then caches it to `.env` for reuse.

- `curl_cffi` (Chrome impersonation) is required — WS is behind Cloudflare TLS fingerprinting.
- Access tokens expire (~1h); rerun `login_via_browser()` to refresh.
- **`.env` holds a live account token in plaintext — never commit it.**

## API reference

All methods are read-only and return plain dicts/lists. Create a client with
`login_via_browser()` (interactive passkey) or `load_cached()` (reuse `.env`).

### Profile & session
| Method | Returns |
|---|---|
| `me()` | name, email, identity id, ownership, token scope, token expiry |
| `identity_id` | your `identity-...` id (decoded from the JWT) |
| `token_claims` | raw decoded JWT claims (sub, scope, client_id, iat, exp) |

### Market data
| Method | Returns |
|---|---|
| `quote(symbol)` | price, bid/ask, OHLC, close, prev close, volume, `change_pct`, market status |
| `security(symbol)` | core fundamentals (market cap, P/E, EPS, yield, 52wk range) |
| `security_info(symbol)` | full: + beta, margin rate, MER, allowed order subtypes, revenue, shares |
| `security_dividend(symbol)` | yield, frequency, ex-div / record / payable dates |
| `historical_quotes(symbol, timerange="1m")` | price series; `timerange` ∈ `1d 1w 1m 3m 1y 5y` |

### Accounts & portfolio
| Method | Returns |
|---|---|
| `accounts()` | every account: id, type, nickname, currency, status, value |
| `positions(currency="CAD")` | holdings: symbol, quantity, book/market value, unrealized P&L |
| `net_worth(currency="CAD")` | combined value, net deposits, simple return (amount + rate) |
| `realized_returns(currency="CAD")` | total realized P&L + per-security breakdown |
| `dividends(currency="CAD")` | total dividend income + per-security breakdown |
| `portfolio_history(days=90, currency="CAD")` | daily net-worth series for charting |
| `activities(limit=10)` | recent feed items (deposits, trades, card, interest, dividends) |
| `credit_card()` | credit-card limit, balances, cards (or `None`) |

All methods raise `WSError` on failure (`UNAUTHENTICATED` → token expired, re-login).

## CLI

```bash
python run_env.py quote AAPL
python run_env.py accounts
python run_env.py positions
python run_env.py activities 10
python run_env.py security TSLA
python run_env.py history AAPL 3m
python automate.py            # full end-to-end: login -> quote -> accounts -> activity
```

## Prior art

Endpoint shapes referenced from [`ws-api`](https://github.com/gboudreau/ws-api-python) (Guillaume Boudreau). This is a clean, focused reimplementation of the read-only path.

## License

MIT
