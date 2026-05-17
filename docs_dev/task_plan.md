# Task: Stock Trader Scraper — Full Remediation

## Goal
Fix all 28 issues identified by the 5-agent audit. Fixes must be surgical, preserve existing behavior where correct, and each phase must pass `pytest` before moving to the next.

## Phases

### Phase 1: Signal Accuracy (CRITICAL — data corruption / incorrect signals)
- [x] **1.1** VADER/AlphaVantage normalization mismatch
  - [x] 1.1a Normalize VADER output to 0-1 scale
  - [x] 1.1b Unify key names: added `bullish_pct/bearish_pct`
  - [x] 1.1c Add `sentiment_score` + `sentiment_label` via `_signal_label()`
- [x] **1.2** Stray conviction += 10 removed
- [x] **1.3** OpenInsider `_parse_date` returns None; rows with None trade_date skipped
- [x] **1.4** None guards applied across yfinance (30+ fields), generator, technical, velocity
- [x] **1.5** Triggers stored as JSON; backfill has CSV fallback for legacy data
- [x] **1.P** pytest: 238 passed, 1 skipped, 0 failures

### Phase 2: Broken Features (HIGH — silent data loss / dead features)
- [x] **2.1** Golden cross / death cross wired into analyze_ticker with len>=200 guard
- [x] **2.2** Default lookback increased from 30 to 250 days
- [x] **2.3** Dashboard unpacks nested paper stats; performance section renders paper trading card
- [x] **2.4** Fallback schema now includes market_assessments + fixed date NOT NULL
- [x] **2.5** Header-row detection for OpenInsider columns with hardcoded fallback
  - - Acceptance: Column mapping derived from headers when available
- [ ] **2.6** Alpha Vantage rate-limit response not detected
  - [ ] 2.6a Check for `"Note"` and `"Information"` keys in API response
  - [ ] 2.6b Log warning and return empty on rate limit hit
  - - Files: `src/collectors/alphavantage.py:65-70`
  - - Acceptance: Rate limit logged as warning, not silently swallowed
- [ ] **2.7** ApeWisdom error vs empty indistinguishable
  - [ ] 2.7a Return `None` on error, `[]` on legitimate empty
  - [ ] 2.7b Update `collect_apewisdom` in main.py to check for `None`
  - - Files: `src/collectors/apewisdom.py:71-76`, `main.py:126-134`
  - - Acceptance: Pipeline log distinguishes API error from zero results
- [x] **2.6** Alpha Vantage rate-limit response detected and logged
- [x] **2.7** ApeWisdom returns None on error, [] on empty; main.py distinguishes
- [x] **2.P** pytest: 238 passed, 1 skipped, 0 failures

### Phase 3: Hardening (MEDIUM — robustness / data quality)
- [x] **3.1** UNIQUE constraints on mentions/prices/velocity/signals + INSERT OR IGNORE
- [x] **3.2** None guards on all format specifiers in dashboard_v2.py and email.py
- [x] **3.3** HTML escaping via `html.escape()` on all external-sourced text in both reporters
- [x] **3.4** try/finally on db.close() in main.py run_pipeline
- [x] **3.5** Deep merge of user thresholds over defaults via copy.deepcopy + nested update
- [x] **3.6** OHLC fields (high, low, open, prev_close) added to get_latest_prices and get_price_history
- [x] **3.7** Conviction rebalanced: theoretical max ~150 pre-cap, better spread among top signals
- [x] **3.8** Composite score returns 0.0 for data-starved tickers (all inputs < 0.01)
- [x] **3.9** signal_id param added to create_paper_trade (optional, defaults to None)
- [x] **3.10** Sentiment shifts: fixed window subquery + added GROUP BY v.ticker
- [x] **3.P** pytest: 238 passed, 1 skipped, 0 failures

### Phase 4: Cleanup (LOW — dead code, minor issues)
- [x] **4.1** Deleted dead `dashboard.py` (v1)
- [x] **4.2** Deleted orphaned `charts.py`; removed `include_charts` param from email.py + main.py
- [x] **4.3** Email report: added 5 enriched data params + _generate_enriched_summary() method
- [x] **4.4** RSI: switched from Cutler (SMA) to Wilder (EMA) smoothing
- [x] **4.5** FRED: CPI inflation (15pts) and USD/EUR (10pts) now in risk assessment
- [x] **4.6** yfinance `_parse_earnings_date`: uses `datetime.fromtimestamp(ts, tz=timezone.utc)`
- [x] **4.7** Removed redundant `pnl` column from paper_trading_schema.sql
- [x] **4.P** pytest: 238 passed, 1 skipped, 0 failures

## Decisions
| Decision | Rationale | Date |
|----------|-----------|------|
| Fix in 4 phases, pytest gate between each | Ensures no regressions compound | 2026-05-17 |
| Use parallel agents for independent file groups | Speed; each agent touches non-overlapping files | 2026-05-17 |
| JSON for triggers storage (not fix CSV parser) | JSON is the standard for list serialization | 2026-05-17 |
| Deep merge thresholds (not shallow copy) | Partial user config must preserve nested defaults | 2026-05-17 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
