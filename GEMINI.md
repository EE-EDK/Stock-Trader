# Stock Trading Signals — Project Mandates

This document extends the root `ENGINEERING-PROJECTS/GEMINI.md` for this project.

## Project-Specific Mandates

- **Free APIs Only:** All data sources must be zero-cost. No paid subscriptions or premium API tiers.
- **Rate Limiting:** Every API collector must implement rate limiting per provider specs. Never exceed documented limits.
- **Data Integrity:** All financial data must flow through SQLite — no CSV or flat-file storage for time-series data.
- **No Invented Signals:** Trading signals must be derived from real API data. Never fabricate or interpolate market data.
- **Secrets Management:** API keys in `config/config.yaml` or `.env` only. These files are gitignored. Never commit credentials.

## Validation
- Run `pytest` before any commit touching signal logic or collectors.
- Backtester results must be reproducible given the same database state.

## Domain Rules
- VADER sentiment analysis runs locally (offline) — no external NLP API dependencies.
- Paper trading mode must be used for all testing — never connect to live brokers.
- Dashboard HTML reports are generated artifacts (gitignored via `*.html` pattern, except `web/templates/`).

## TODO
- [ ] Run `pytest` before any commit touching signal logic or collectors.
- [ ] Backtester results must be reproducible given the same database state.
- [ ] VADER sentiment analysis runs locally (offline) — no external NLP API dependencies.
- [ ] Paper trading mode must be used for all testing — never connect to live brokers.
- [ ] Dashboard HTML reports are generated artifacts (gitignored via `*.html` pattern, except `web/templates/`).
