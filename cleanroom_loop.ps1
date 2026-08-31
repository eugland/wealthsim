# cleanroom_loop.ps1 — drive headless Claude Code to clean-room-reimplement
# ws-trade's PUBLIC API surface into wealthsim, one area per iteration.
#
# CLEAN-ROOM RULES (enforced in the prompt, but you own the outcome):
#   * Read ws-trade only to learn its PUBLIC surface: method names, params,
#     return-dict shapes, observed behavior. DO NOT copy its source code,
#     comments, or internal structure. Reimplement from scratch.
#   * Every new file keeps wealthsim's own MIT header and style.
#   * Read-only endpoints only (project boundary — no order placement).
#
# Usage:  pwsh ./cleanroom_loop.ps1
# Stop:   Ctrl-C, or `touch STOP` in this dir.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- 1. the areas to work through, one per iteration ---------------------
$areas = @(
    "market data (quotes, security fundamentals, dividends, historical prices)",
    "accounts + balances",
    "positions / holdings + unrealized P&L",
    "net worth, realized returns, dividends received",
    "portfolio history time series",
    "activity / transaction feed",
    "profile, identity, token claims / session introspection",
    "error handling + exception taxonomy"
)

# where ws-trade lives (the library you are mirroring the surface of)
$target = "C:\Users\eugen\dev\wslite\reference\ws-trade"   # <-- adjust
$log    = Join-Path $PSScriptRoot "cleanroom_progress.md"
if (-not (Test-Path $log)) { "# clean-room progress`n" | Out-File $log -Encoding utf8 }

# --- 2. loop -------------------------------------------------------------
$i = 0
foreach ($area in $areas) {
    if (Test-Path (Join-Path $PSScriptRoot "STOP")) { Write-Host "STOP file found, halting."; break }
    $i++
    Write-Host "`n=== [$i/$($areas.Count)] $area ===" -ForegroundColor Cyan

    $prompt = @"
You are extending the local Python package 'wealthsim' (cwd).

TASK: clean-room reimplement the **$area** functionality that the reference
library at '$target' exposes.

CLEAN-ROOM RULES — MANDATORY:
1. Inspect '$target' ONLY to learn its PUBLIC API surface for this area:
   public method names, their parameters/defaults, and the SHAPE of what they
   return. Note observed behavior.
2. DO NOT copy its source code, comments, private helpers, or file structure.
   Reimplement every method from scratch against Wealthsimple's own API, in
   wealthsim's existing style (plain-dict returns, one GraphQL call per method
   where possible, fully typed).
3. READ-ONLY endpoints only. No order placement — that is a hard project boundary.
4. If a method already exists in wealthsim, skip it; only add what's missing for
   THIS area.

STEPS:
- Read wealthsim/client.py and wealthsim/__init__.py to match conventions.
- Enumerate the target's public methods for this area (list them to me).
- Implement the missing ones in wealthsim/client.py, exported via __init__ if
  they are top-level.
- Add or extend a test in tests/ that at least imports and type-checks the new
  surface (no live network in tests — mock or structural only).
- Run:  python -m mypy wealthsim  &&  python -m pytest -q
  Fix anything you broke.
- Append ONE bullet to cleanroom_progress.md: what you added for '$area'.

Keep changes surgical and scoped to this area only.
"@

    claude -p $prompt `
        --permission-mode acceptEdits `
        --allowedTools "Read,Edit,Write,Grep,Glob,Bash" `
        2>&1 | Tee-Object -FilePath $log -Append

    "`n---`n" | Out-File $log -Append -Encoding utf8
}
Write-Host "`nDone. Review with: git -C `"$PSScriptRoot`" diff" -ForegroundColor Green
