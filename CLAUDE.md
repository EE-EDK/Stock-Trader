# CLAUDE.md — Stock Trading Signals System

## Overview
Multi-source stock trading signal generator using 100% free APIs. Combines social momentum (ApeWisdom), insider trades (OpenInsider), technical analysis (Finnhub, Alpha Vantage, YFinance), macro indicators (FRED), and sentiment analysis (VADER) into scored trading signals.

## Tech Stack
- Python 3.8+, SQLite, Flask (dashboard server)
- PyQt5 (GUI), PyInstaller (distribution)
- pandas, numpy, yfinance, reportlab

## Key Files
- `main.py` — Entry point, orchestrates the full pipeline (single-instance locked)
- `src/` — Core modules (collectors, signals, backtester, paper trading)
- `src/trading/engine.py` — Shared bar-walking exit engine (paper trading + backtester)
- `src/collectors/bars_backfill.py` — Gap-aware daily OHLCV backfill into `price_bars`
- `src/analysis/outcomes.py` — Signal forward-return backfill (+5/+10/+30 trading days)
- `docs/memory/LEDGER.md` — project memory: what has been tried, what works, what does not (read at session start)
- `docs/memory/memory.py` — append-only memory CLI (`add` / `list` / `supersede`)
- `tests/` — Test modules covering all subsystems (295 tests, `pytest --collect-only -q`, 2026-08-27)
- `web/` — HTML dashboard generation
- `utils/backtest.py` — Backtesting utilities
- `utils/revalidate_paper_trades.py` — One-time book repair (void dupes, re-close vs bars)
- `utils/register_daily_task.ps1` — Windows Task Scheduler registration (weekday runs)
- `config/config.yaml` — API keys and runtime configuration (gitignored)
- `data/sentiment.db` — SQLite database (gitignored)

## Build & Run
```bash
# Install dependencies
pip install -r requirements.txt

# Run signal generation
python main.py

# Run tests
pytest

# Build standalone executable
pyinstaller main.spec
```

## Conventions
- All API keys go in `config/config.yaml` or `.env` — never hardcode
- SQLite for persistence, never flat files for time-series data
- **All time-series joins key on `price_bars.date` (market date), never `collected_at`** — the
  `prices` table is a run-time snapshot only; indicators, exits, and outcomes read `price_bars`
- Trade exit logic lives only in `src/trading/engine.py` — paper trading and the backtester share it
- Rate limiting is mandatory for all API collectors
- Tests use pytest with fixtures

## TODO
- [ ] Phase 4 of the market-date-spine plan (`docs/superpowers/plans/2026-08-19-market-date-spine-spec.md`):
      re-weight conviction scoring empirically once ~50 outcomes per trigger type accumulate in the
      signal edge table (dashboard "Signal Edge by Trigger Type")
- [ ] **Trade page (actionable order tickets).** Make the system usable for real trades: a page
      (dashboard section or standalone) that turns each confirmed signal/paper trade into a concrete
      order ticket — ticker, action (buy), share count and dollar size (conviction-sized, scaled to a
      configurable real-money account size rather than the $1000 paper base), suggested order type
      (limit at/near signal price vs market), and the exact stop-loss and take-profit prices to place
      with the broker so real exits mirror the engine's rules. Flow: review open paper trades →
      mark one "taking this live" → get the ticket; record the real fill back against the same
      signal_id so real results, paper results, and backtest results stay comparable in one lineage.
      Prerequisite for sizing confidence: the per-trigger edge table (Phase 4) should have enough
      samples to trust before real money follows it.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current

## Claude Cowork Sessions (remote-device bridge from KunzPrime)

Operational facts specific to reaching this repo through the Claude Cowork
device bridge (`mcp__remote-devices__*` tools). Not relevant to Grok/Cursor/
local CLI sessions, which work the filesystem directly — keep this section
out of `AGENTS.md`, which is agent-agnostic.

### Mount path
The connected folder does not mount at a directory literally named
`stock-trader`. Use:
- `$HOME/mnt/ACTIVE-PROJECTS--data-and-finance--stock-trader` — the real working tree
- `$HOME/mnt/modules--data-and-finance--stock-trader` — the submodule's real `.git` directory (see below)

A third folder named plain `stock-trader` sometimes also appears under
`$HOME/mnt/` — it is a stale, empty leftover mount from an earlier session.
Run `ls -la $HOME/mnt/` and confirm before trusting a path; do not assume the
shortest or most obvious name is correct.

### Git (submodule quirk)
This repo is a git submodule. Its `.git` file points to
`../../../.git/modules/data-and-finance/stock-trader`, a relative path that
does not resolve across the device-mount boundary — plain `git status` /
`git log` fail with `fatal: not a git repository`. Set both env vars first:

```bash
export GIT_DIR="$HOME/mnt/modules--data-and-finance--stock-trader"
export GIT_WORK_TREE="$HOME/mnt/ACTIVE-PROJECTS--data-and-finance--stock-trader"
cd "$GIT_WORK_TREE"
```

### Phantom "modified" files after a remount
A freshly remounted folder often shows dozens of files as modified in
`git status --short` with zero real changes underneath — CRLF/mtime noise
from the mount layer, not real edits. Never report this as a finding
without checking first:

```bash
git diff --stat -b -- . ':!docs/memory'   # whitespace-ignored; empty output = phantom noise
```

### SQLite reads over the device mount
Writes to `data/sentiment.db` over the mount are unreliable (`disk I/O
error`) — this is why `guard.py` enforces `env:device_mount +
tool:sqlite_write`. Reads are usually fine but occasionally fail the same
way. Use the read-only, lock-free URI form for any read-only query:

```python
sqlite3.connect('file:data/sentiment.db?mode=ro&immutable=1', uri=True)
```

### Running Python via `device_bash`
Multi-line Python passed as `python3 -c "..."` through `device_bash`'s
`bash -c` wrapper breaks on embedded quotes/backslashes. Write the script to
a file first:

```bash
cat > /tmp/script.py <<'PYEOF'
...
PYEOF
python3 /tmp/script.py
```

Use a single-quoted heredoc delimiter — required if the script references
`$HOME`, since that also blocks shell expansion; substitute the resolved
value in afterward with `sed -i` if the script needs it.

### `fwd_return_5d` / `fwd_return_10d` / `fwd_return_30d` units
Already stored in percentage-point units (e.g. `2.82` means +2.82%). Do not
multiply by 100.

### Automated/scheduled checks — do not re-propose
A weekly Claude Cowork scheduled task for this project was built, then
abandoned by explicit user decision on 2026-09-18 (ledger #48). It failed
on: device-binding silently lost between runs with no way to re-bind from a
cloud session, no way to retrieve a finished run's report content
(`list_triggers` exposes only success/duration, not what was found), and
the scheduled session self-rewriting its own future prompt without being
asked. Do not suggest recreating a scheduled task for this project unless
the user raises it first. Stock-trader status checks happen manually,
in-conversation, on request.

## Status Check Report Template

Use this exact structure whenever asked for a stock-trader status check,
review, or "should I buy anything"-type question (only the Bottom Line
prose changes check to check):

```
**Guard status:** action:live_trade — <BLOCKED by #N / CLEAR>. Open advisories: <#N summary, or none>.

**Edge by signal type** (vs. <prior check date>)

| type | n | independent dates | avg fwd 10d | hit rate | Δ |
|---|---|---|---|---|---|
| ... |

**Pipeline:** run range checked, status, any anomalies.

**Paper book:** open/closed/void counts, cap status if relevant.

**Account (<masked acct>):** cash, positions, orders since <date>.

**Git:** ahead/behind origin; working-tree status (run the phantom-diff check above before reporting a dirty tree).

**Bottom line:** one or two sentences — trade or no trade, and why.
```

Log a ledger entry only for a new decision, fix, or failure — not for
routine incremental movement in the edge numbers (fold small deltas into
whichever future entry actually needs one).
