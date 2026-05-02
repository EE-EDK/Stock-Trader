# CLAUDE.md — Stock Trading Signals System

## Overview
Multi-source stock trading signal generator using 100% free APIs. Combines social momentum (ApeWisdom), insider trades (OpenInsider), technical analysis (Finnhub, Alpha Vantage, YFinance), macro indicators (FRED), and sentiment analysis (VADER) into scored trading signals.

## Tech Stack
- Python 3.8+, SQLite, Flask (dashboard server)
- PyQt5 (GUI), PyInstaller (distribution)
- pandas, numpy, yfinance, reportlab

## Key Files
- `main.py` — Entry point, orchestrates the full pipeline
- `src/` — Core modules (collectors, signals, backtester, paper trading)
- `tests/` — 8 test modules covering all subsystems
- `web/` — HTML dashboard generation
- `utils/backtest.py` — Backtesting utilities
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
- Rate limiting is mandatory for all API collectors
- Tests use pytest with fixtures

## TODO
- [ ] Python 3.8+, SQLite, Flask (dashboard server)
- [ ] PyQt5 (GUI), PyInstaller (distribution)
- [ ] pandas, numpy, yfinance, reportlab
- [ ] All API keys go in `config/config.yaml` or `.env` — never hardcode
- [ ] SQLite for persistence, never flat files for time-series data
- [ ] Rate limiting is mandatory for all API collectors
- [ ] Tests use pytest with fixtures

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
