# Progress Log

## 2026-05-17

### Session Start
- 5-agent audit completed: collectors, signal generator, database, dashboard, tests
- 28 issues identified across 4 severity tiers
- All 239 existing tests pass as baseline
- Plan created in `task_plan.md`

### Phase 1: Signal Accuracy (CRITICAL) — COMPLETE
- 4 parallel agents on non-overlapping file groups
- VADER normalization: 0-100→0-1 scale, unified keys (`bullish_pct`, `sentiment_score`, `sentiment_label`)
- Stray `conviction += 10` removed from generator.py
- OpenInsider `_parse_date` returns None on failure; rows with None trade_date skipped
- None guards applied across 30+ fields in yfinance, generator, technical, velocity
- Triggers: CSV→JSON storage with backward-compatible CSV fallback in backfill
- pytest gate: 238 passed, 1 skipped

### Phase 2: Broken Features (HIGH) — COMPLETE
- 3 parallel agents
- Golden cross / death cross wired into analyze_ticker with len>=200 guard
- Default lookback increased from 30→250 days (enables SMA-50, cross detection)
- Dashboard v2 unpacks nested paper trading stats correctly
- Fallback macro schema now includes market_assessments table + fixed date NOT NULL
- OpenInsider: dynamic header-row column detection with hardcoded fallback
- Alpha Vantage: rate-limit JSON response detected and logged
- ApeWisdom: returns None on error vs [] on empty; main.py distinguishes
- pytest gate: 238 passed, 1 skipped

### Phase 3: Hardening (MEDIUM) — COMPLETE
- 3 parallel agents
- UNIQUE constraints on mentions/prices/velocity/signals + INSERT OR IGNORE
- None guards on all format specifiers in dashboard_v2.py and email.py
- HTML escaping via html.escape() on all external-sourced text in both reporters
- try/finally on db.close() in main.py
- Deep merge of user thresholds over defaults
- OHLC fields added to get_latest_prices and get_price_history queries
- Conviction rebalanced: reduced weights, better spread among top signals
- Composite score returns 0.0 for data-starved tickers
- signal_id param added to create_paper_trade
- Sentiment shifts: fixed window subquery + GROUP BY
- pytest gate: 238 passed, 1 skipped

### Phase 4: Cleanup (LOW) — COMPLETE
- 2 parallel agents
- Deleted dead dashboard.py (v1) and orphaned charts.py
- Removed include_charts dead param from email.py and main.py
- Email report: 5 enriched data params + _generate_enriched_summary()
- RSI: Cutler (SMA) → Wilder (EMA) smoothing
- FRED: CPI inflation (15pts) and USD/EUR (10pts) added to risk assessment
- yfinance _parse_earnings_date: UTC timezone
- Removed redundant pnl column from paper_trading_schema.sql
- pytest gate: 238 passed, 1 skipped

### Final State
- All 28 issues resolved
- 238 tests passing, 1 skipped (Finnhub live integration, API key gated)
- 12 parallel agent dispatches across 4 phases
- Files modified: ~20 source files
- Files deleted: 2 (dead code)
