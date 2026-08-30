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

## Examples

Every call and a representative (redacted) result. Values below are illustrative.

```python
ws.me()
# {'name': 'Jane Doe', 'email': 'jane@example.com',
#  'identity_id': 'identity-XXXX', 'ownership_type': 'primary',
#  'scope': 'read write', 'client_id': '4da5...', 'token_expired': False,
#  'token_expires': '2026-08-30T14:12:46+00:00'}

ws.quote("AAPL")
# {'symbol': 'AAPL', 'name': 'Apple Inc', 'exchange': 'NASDAQ',
#  'security_id': 'sec-s-...', 'market_status': 'CLOSED',
#  'price': '319.9', 'bid': '320.02', 'ask': '320.15',
#  'open': '317.08', 'high': '322.37', 'low': '315.45', 'close': '319.7',
#  'prev_close': '319.7', 'volume': '28569783', 'change_pct': 0.06, 'currency': 'USD'}

ws.security("AAPL")
# {'symbol': 'AAPL', 'name': 'Apple Inc', 'security_id': 'sec-s-...',
#  'marketCap': '4665765.74', 'peRatio': '36.65', 'eps': '8.72',
#  'yield': '0.0033', 'high52Week': '344.57', 'low52Week': '225.95', ...}

ws.security_info("AAPL")
# {'symbol': 'AAPL', 'exchange': 'NASDAQ', 'dividend_frequency': 'QUARTERLY',
#  'allowed_order_subtypes': ['MARKET', 'FRACTIONAL', 'LIMIT', 'STOP', ...],
#  'mer': None, 'margin_rate': '0.3', 'beta': '1.0774', 'marketCap': '4665765.74', ...}

ws.security_dividend("AAPL")
# {'yield': '0.0033', 'frequency': 'QUARTERLY',
#  'ex_dividend_date': None, 'record_date': None, 'payable_date': None}

ws.historical_quotes("AAPL", "1m")
# [{'price': '333.43', 'sessionPrice': None, 'timestamp': '2026-07-30T00:00:00.000Z', 'currency': 'USD'},
#  ... 32 daily points ...]

ws.accounts()
# [{'id': 'tfsa-XXXX', 'type': 'SELF_DIRECTED_TFSA', 'nickname': None,
#   'currency': 'CAD', 'status': 'open', 'value': '33576.54'},
#  {'id': 'ca-cash-XXXX', 'type': 'CASH', 'nickname': 'Spending',
#   'currency': 'CAD', 'status': 'open', 'value': '5178.99'}, ...]

ws.positions()
# [{'symbol': 'VFV', 'name': 'Vanguard S&P 500 ...', 'quantity': '3.89',
#   'direction': 'BUY', 'book_value': '718.96', 'market_value': '742.44',
#   'unrealized_pnl': '23.48', 'pct_of_account': '0.06', 'currency': 'CAD'}, ...]

ws.net_worth()
# {'net_value': '51076.05', 'net_deposits': '50658.42',
#  'return_amount': '417.67', 'return_rate': '0.0082', 'currency': 'CAD'}

ws.realized_returns()
# {'total': '1430.08', 'currency': 'CAD',
#  'by_security': [{'symbol': 'QQQU', 'amount': '1498.39'},
#                  {'symbol': 'MSFT', 'amount': '149.51'}, ...]}

ws.dividends()
# {'total': '234.58', 'currency': 'CAD',
#  'by_security': [{'symbol': 'QYLD', 'amount': '50.94'},
#                  {'symbol': 'SDIV', 'amount': '35.06'}, ...]}

ws.portfolio_history(days=90)
# [{'date': '2026-06-01', 'value': '239.62'}, ...,
#  {'date': '2026-08-29', 'value': '51067.24'}]   # 90 daily points

ws.activities(5)
# [{'occurredAt': '2026-08-25T...', 'type': 'CREDIT_CARD', 'subType': 'PAYMENT',
#   'amount': '1619.16', 'amountSign': 'positive', 'currency': 'CAD',
#   'assetSymbol': None, 'assetQuantity': None, 'status': 'COMPLETED'}, ...]

ws.credit_card()
# {'id': 'ca-credit-card-XXXX', 'creditLimit': 3000,
#  'balance': {'current': '862.36', 'outstanding': '1074.30',
#              'availableCreditLimit': '1925.70', 'pending': '211.94'},
#  'currentCards': [{'cardNumber': '************1234', 'cardStatus': 'open',
#                    'nameOnCard': 'JANE DOE', 'isLocked': False}]}

ws.identity_id      # 'identity-XXXX'
ws.token_claims     # {'sub': 'identity-XXXX', 'scope': 'read write', 'exp': 1788099166, ...}
```

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
