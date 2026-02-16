# Pipeline Verification Report

**Purpose:** Confirm all `src` modules are connected and that data is pulled, calculated, and acted on correctly. No broken paths.

---

## 1. Data flow overview

```
[Collectors] --> db.insert_* --> [DB]
                                      \
[DB] --> get_tracked_tickers, get_* --> [VelocityCalculator, TechnicalAnalyzer]
                                                      \
[velocity_data, technical_data, insider_data, price_data, sentiment_data]
    --> [SignalGenerator.generate_signals] --> all_signals --> db.insert_signals
    --> filter_by_conviction --> signals
            --> [PaperTradingManager] (create_paper_trade, update_positions)
            --> [EmailReporter] (optional)
            --> [DashboardGenerator (dashboard_v2)] --> HTML report
```

---

## 2. Collectors → DB (data pulled and stored)

| Collector | main.py usage | DB method | Status |
|-----------|----------------|-----------|--------|
| **ApeWisdom** | `collect_apewisdom(config)` → mentions | `db.insert_mentions(mentions)` | OK – dict keys: ticker, mentions, upvotes, rank, mentions_24h_ago, rank_24h_ago, collected_at, source |
| **OpenInsider** | `collect_openinsider(config)` → trades | `db.insert_insiders(trades)` | OK – dict keys match insert_insiders |
| **Finnhub** | `FinnhubCollector().combine_price_and_sentiment(tracked_tickers)` → prices | `db.insert_prices(prices)` | OK – uses get_tracked_tickers(days=7) for ticker list |
| **YFinance** | `collect_yfinance(tracked_tickers)` → yfinance_data | Not inserted (in-memory for sentiment/velocity) | OK – passed to VADER and signal context |
| **Alpha Vantage** | `collect_alphavantage(config, top_tickers)` → alpha_sentiment | Not inserted (in-memory) | OK – merged into sentiment_data for signals |
| **VADER** | `collect_vader(top_tickers, yfinance_data, config)` → vader_sentiment | Not inserted (in-memory) | OK – merged into sentiment_data for signals |
| **FRED** | `collect_fred(config)` → indicators, assessment | `db.insert_macro_indicators()`, `db.insert_market_assessment()` | OK – assessment has risk_level, risk_score, conditions, warnings, recommendations |

---

## 3. DB → metrics (data read and calculated)

| Consumer | DB methods used | Output |
|----------|------------------|--------|
| **VelocityCalculator(db)** | `get_mention_history(ticker, 7)`, `get_sentiment_history(ticker, 7)`, `get_price_history(ticker, 7)` | velocity_data: {ticker: {mention_velocity_24h, mention_velocity_7d, sentiment_velocity, volume_price_divergence, composite_score}} |
| **TechnicalAnalyzer(db)** | `get_price_history(ticker, days)` | technical_data: {ticker: {rsi, macd, ...}} |
| **SignalGenerator** | N/A (receives data from main) | all_signals → filtered signals |

Velocity and technical use `queries.py` via `models.py` (get_mention_history, get_price_history, get_sentiment_history). Schema matches: mentions.mentions, prices.price, etc.

---

## 4. Metrics + DB → signals

| Input | Source | Passed to SignalGenerator.generate_signals |
|-------|--------|--------------------------------------------|
| velocity_data | VelocityCalculator | Yes |
| insider_data | `db.get_recent_insiders(days=14)` | Yes |
| price_data | `db.get_latest_prices()` | Yes |
| technical_data | TechnicalAnalyzer | Yes |
| sentiment_data | alpha_sentiment + vader_sentiment merge | Yes |

Signals inserted with `db.insert_signals(all_signals)`. Signal dataclass has: ticker, signal_type, conviction_score, price_at_signal, triggers, notes, created_at – matches insert_signals columns.

---

## 5. Signals → paper trading and reporting

| Consumer | Input | Connection |
|----------|--------|------------|
| **PaperTradingManager** | db_path (str), config; update_positions(get_latest_prices()) | main uses `PaperTradingManager(db_path, config)`. update_positions expects Dict[ticker, price_data]; main passes `db.get_latest_prices()` (ticker → {price, ...}). Paper trading extracts `price_data['price']` – OK. |
| **EmailReporter** | config['email'], signals, velocity_data, report options | main passes report_section.get('max_signals', 10), etc. – OK. |
| **DashboardGenerator (dashboard_v2)** | signals, velocity_data, technical_data, sentiment_data, paper_trading_stats, macro_indicators, market_assessment, db | main passes all; generate() signature includes db. – OK. |

---

## 6. File and schema paths

| Asset | Referenced by | Status |
|-------|----------------|--------|
| `src/database/queries.py` | models.py (get_tracked_tickers, get_recent_insiders, get_latest_prices, get_mention_history, get_price_history, get_sentiment_history) | OK – exists and used |
| `src/database/macro_schema.sql` | models.py initialize() | OK – exists |
| `src/database/paper_trading_schema.sql` | models.py initialize(), paper_trading._init_tables() | OK – paper_trading uses Path; main runs with cwd=project_root so relative path works |
| `src/reporters/dashboard_v2.py` | main.py (ModernDashboardGenerator) | OK – only dashboard used in pipeline |
| `src/reporters/dashboard.py` | test_runtime.py (was wrong – fixed to dashboard_v2) | Legacy; not used by pipeline |
| `src/reporters/charts.py` | Not used by main.py | Standalone; no broken path |

---

## 7. Fixes applied during verification

1. **utils/test_runtime.py**
   - Dashboard test now uses `src.reporters.dashboard_v2.ModernDashboardGenerator` (same as main.py).
   - Dashboard generate signature check includes `db` parameter.
   - PaperTradingManager test: first argument changed from Database instance to `db_path` string; config uses `{'paper_trading': {'enabled': False}}`.
   - Backtester test: first argument changed from Database instance to `db_path` string; config uses `{'backtesting': {'initial_capital': 10000}}`.

---

## 8. Summary

- **Collectors:** All 7 used collectors (ApeWisdom, OpenInsider, Finnhub, YFinance, Alpha Vantage, VADER, FRED) are called from main.py; their outputs are either written to the DB or passed in-memory as intended.
- **DB:** All insert and query methods used by main exist in models.py and (where used) queries.py; schema and dict shapes match.
- **Metrics:** VelocityCalculator and TechnicalAnalyzer receive the DB instance and call the correct query methods; their outputs are passed into the signal generator.
- **Signals:** SignalGenerator receives velocity, insiders, prices, technical, and sentiment data; signals are written to the DB and filtered for reporting and paper trading.
- **Paper trading / Email / Dashboard:** Constructors and method calls match main.py; dashboard used in production is dashboard_v2; paper trading correctly uses price from `get_latest_prices()`.
- **Paths:** No broken imports or missing schema files; test_runtime now validates the same dashboard and constructor contracts as the pipeline.

**Conclusion:** The pipeline is wired end-to-end. Data is pulled by collectors, stored or passed in-memory, read by metrics and signal generator, and acted on by paper trading, email, and dashboard. The only corrections needed were in the runtime test script so it matches the actual pipeline (dashboard_v2 and correct constructor arguments).
