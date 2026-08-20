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
- `tests/` — Test modules covering all subsystems (273+ tests)
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

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
