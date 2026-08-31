# clean-room progress

Mirroring the public API surface of ws-api-python (gboudreau) into wealthsim,
one area per iteration. Public surface only — no source copied. Read-only endpoints.

- [x] **(1) market data** — added `search(query, limit=10)` (public security search →
  list of symbol/name/exchange/security_id/buyable/status) and `security_id_to_symbol(id)`
  (reverse ticker lookup, new `_SEC_SYMBOL_QUERY`). Existing already covered ws-api's
  `get_security_market_data` (`security`/`security_info`), `get_security_dividend_details`
  (`security_dividend`), `get_security_historical_quotes`/`get_security_chart_quotes`
  (`historical_quotes`). Tests: tests/test_market_data.py (3, structural/mock). pytest green.
  NOTE: 5 pre-existing mypy errors (IMPERSONATE literal type, lines ~542-634) unrelated to
  this area — left untouched.
- [x] **(2) accounts + balances** — added `account_balances(account_id)` → `{symbol_or_cash_code:
  quantity}` (new `_ACCOUNT_BALANCES_QUERY`, resolves non-cash ids via `security_id_to_symbol`),
  mirroring ws-api `get_account_balances`. ws-api `get_accounts` already covered by `accounts()`;
  `get_account_historical_financials` deferred to area 5 (portfolio history). Tests:
  tests/test_accounts.py (2, structural). pytest 5/5 green. mypy: only the 5 pre-existing
  IMPERSONATE errors remain.
- [x] **(3) positions / holdings** — added `account_unrealized_pnl(account_id, currency="CAD")`
  → `{amount, rate, currency}` (new `_ACCOUNT_UNREALIZED_PNL_QUERY`), mirroring ws-api
  `get_account_unrealized_pnl`. ws-api `get_identity_positions` already covered by `positions()`.
  Tests: tests/test_positions.py (2, structural). pytest 7/7. New code type-clean.
- [x] **(4) net worth / realized returns / dividends** — already fully covered: ws-api
  `get_identity_current_financials`→`net_worth()`, `get_identity_realized_returns`→`realized_returns()`,
  `get_dividends`→`dividends()`. No methods missing. NOT added: the target's optional
  `account_ids`/`start_date` filter params — they require declaring new GraphQL variables on the
  working query strings against an unverifiable live schema, risking breakage of endpoints that
  currently work. Deferred as an enhancement rather than guessed. No code change; pytest 7/7.
- [x] **(5) portfolio history** — added `account_history(account_id, days=90, currency="CAD")`
  → daily `[{date, value}]` for one account (new `_ACCOUNT_HISTORY_QUERY`), mirroring ws-api
  `get_account_historical_financials`. ws-api `get_identity_historical_financials` already covered
  by `portfolio_history()`. Tests: tests/test_history.py (2). pytest 9/9. New code type-clean.
- [x] **(6) activity feed** — added `corporate_action_activities(activity_canonical_id)` →
  list of activity nodes (new `_CORP_ACTION_QUERY`, reuses the known activity-node field set),
  mirroring ws-api `get_corporate_action_child_activities`. ws-api `get_activities` already
  covered by `activities()`. NOT added: `get_transfer_details`, `get_etf_details`,
  `get_statement_transactions` — each selects fields on types (accountTransfer / fundsTransfer /
  monthlyStatement) whose schema I can't verify; guessing selection sets would ship broken
  queries. Deferred. Tests: tests/test_activity.py (2). pytest 11/11. New code type-clean.
- [x] **(7) profile / identity / session** — already covered: ws-api `login`→`login()`,
  `from_token`→`from_refresh_token()`, and the who-am-I/scope/expiry/identity surface of
  `get_token_info` is served offline by `me()` + `token_claims` + `identity_id` (JWT-decoded).
  NOT added: a live-fetch `token_info()` hitting the REST `/token/info` endpoint — unverifiable
  path + response shape, and functionally redundant with existing accessors. Deferred. No code
  change; pytest 11/11.
- [x] **(8) error taxonomy** — added `LoginFailed(WSError)` (raised now at both auth-failure
  sites: `login` and `from_refresh_token`, carrying the raw payload) and gave `WSError` an
  optional `response` attribute — parity with ws-api `WSApiException`/`LoginFailedException`.
  Exported `LoginFailed` from the package. `OTPRequired` already mirrored `OTPRequiredException`;
  Curl/Unexpected/ManualLoginRequired fold into `WSError` by design (flatter taxonomy).
  Tests: tests/test_errors.py (4). pytest 15/15. New code type-clean.

## Summary — all 8 areas complete
Added, clean-room (public surface only, no source copied), read-only:
`search`, `security_id_to_symbol`, `account_balances`, `account_unrealized_pnl`,
`account_history`, `corporate_action_activities`, plus `LoginFailed` + `WSError.response`.
Already-covered areas: net worth/realized/dividends (4), profile/session (7).
Deferred (unverifiable GraphQL schema / redundant): `account_ids`/`start_date` filters on
financials methods; `get_transfer_details` / `get_etf_details` / `get_statement_transactions`;
live-fetch `token_info()`. 15 structural tests, all green. Pre-existing mypy IMPERSONATE
literal errors (×5) untouched — unrelated to this work.
