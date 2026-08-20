# Market-Date Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-key the stock-trader pipeline, paper trading, and backtesting to market dates via a canonical daily-bar table, so exits, technicals, velocity, and signal outcomes are computed against real market history instead of pipeline-run snapshots.

**Architecture:** One new table (`price_bars`, PK `(ticker, date)`) becomes the time spine, gap-backfilled from yfinance on every run. A pure bar-walking exit engine (`src/trading/engine.py`) is shared by paper trading (replaying bars since each position's last evaluation) and the backtester. Signal outcomes are backfilled from bars at +5/+10/+30 trading days, closing the learning loop.

**Tech Stack:** Python 3.8+, SQLite3 (stdlib), yfinance + pandas (already in requirements.txt), pytest.

**Spec:** `docs/superpowers/plans/2026-08-19-market-date-spine-spec.md`

## Global Constraints

- Python 3.8 compatibility: use `typing.List/Dict/Optional`, no `dict |`, no builtin-generic annotations.
- No new dependencies. yfinance, pandas, numpy, pytest are already in `requirements.txt`.
- Working directory for all commands is the project root: `C:\Users\edk7c\ENGINEERING-PROJECTS\ACTIVE-PROJECTS\data-and-finance\stock-trader`.
- Test baseline before Task 1: `pytest` → **238 passed, 1 skipped**. Every commit must leave the full suite green (new tests added to that count).
- Never delete historical DB rows or downgrade recorded data — annotate/void with a status instead (workspace rule "Historical Preservation").
- `config/config.yaml` is gitignored (holds real keys). Commit only `config/config.example.yaml` changes; apply the same edits to the live file without committing it.
- Commit style: conventional commits (`feat:`, `fix:`, `chore:`), each message ending with the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- All dates in `price_bars` and the engine are ISO `YYYY-MM-DD` strings (sortable lexically). All "days held" counts are **calendar days**, matching existing `paper_trading.py` semantics.
- After the final task, rebuild the knowledge graph: `python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` (skip without failing if graphify is not installed).

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/utils/single_instance.py` | Create | Lock-file acquire/release for one pipeline at a time |
| `src/database/models.py` | Modify | `price_bars` DDL, column migrations, bar accessors, `pipeline_runs` ledger, `insert_signals` returns ids |
| `src/collectors/bars_backfill.py` | Create | Gap-aware daily-bar backfill from yfinance into `price_bars` |
| `src/metrics/technical.py` | Modify | `TechnicalAnalyzer` reads closes from `price_bars` |
| `src/trading/engine.py` | Create | Pure bar-walking exit engine (`walk_bars`, `ExitEvent`) |
| `src/trading/paper_trading.py` | Modify | Bar-replay position updates, one-open-per-ticker dedup, zero-share guard, `last_evaluated_date` |
| `src/analysis/outcomes.py` | Create | Backfill `signals` forward returns from bars |
| `src/analysis/backtester.py` | Modify | `simulate_trade` uses shared engine + `price_bars` |
| `src/database/queries.py` | Modify | `get_signal_edge_by_type()` |
| `src/reporters/dashboard_v2.py` | Modify | Signal-edge table section |
| `src/metrics/velocity.py` | Modify | Date-normalized 24h velocity + staleness |
| `main.py` | Modify | Lock, backfill step, bar-based updates, signal_id linkage, run ledger |
| `utils/revalidate_paper_trades.py` | Create | One-time: void duplicates/zero-share trades, re-close history against bars |
| `utils/register_daily_task.ps1` | Create | Windows Task Scheduler registration |
| `config/config.example.yaml` | Modify | Honest thresholds |
| Tests | Create/Modify | `tests/test_price_bars.py`, `tests/test_bars_backfill.py`, `tests/test_trade_engine.py`, `tests/test_outcomes.py`; extend `tests/test_paper_trading.py`, `tests/test_velocity.py`, `tests/test_technical_analyzer.py` |

---

### Task 1: Single-instance lock

Two pipeline instances ran concurrently on 2026-08-19 and duplicated every trade (spec F5/F8). Fix the front door first so nothing later in this plan is corrupted during rollout.

**Files:**
- Create: `src/utils/single_instance.py`
- Create: `tests/test_single_instance.py`
- Modify: `main.py` (inside `main()`, around the `run_pipeline` call)

**Interfaces:**
- Consumes: nothing.
- Produces: `acquire_lock(lock_path: str, stale_seconds: int = 7200) -> bool`, `release_lock(lock_path: str) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_single_instance.py
import os
from src.utils.single_instance import acquire_lock, release_lock


def test_acquire_creates_lock(tmp_path):
    lock = str(tmp_path / "pipeline.lock")
    assert acquire_lock(lock) is True
    assert os.path.exists(lock)
    release_lock(lock)
    assert not os.path.exists(lock)


def test_second_acquire_fails(tmp_path):
    lock = str(tmp_path / "pipeline.lock")
    assert acquire_lock(lock) is True
    assert acquire_lock(lock) is False
    release_lock(lock)


def test_stale_lock_is_broken(tmp_path):
    lock = str(tmp_path / "pipeline.lock")
    assert acquire_lock(lock) is True
    # Backdate the lock file beyond the stale window
    old = os.path.getmtime(lock) - 10_000
    os.utime(lock, (old, old))
    assert acquire_lock(lock, stale_seconds=7200) is True
    release_lock(lock)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_single_instance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.utils.single_instance'`

- [ ] **Step 3: Implement the lock module**

```python
# src/utils/single_instance.py
"""
@file single_instance.py
@brief Lock-file guard so only one pipeline instance runs at a time.
"""

import os
import time
import logging

logger = logging.getLogger(__name__)


def acquire_lock(lock_path: str, stale_seconds: int = 7200) -> bool:
    """
    @brief Atomically create a lock file. Returns False if a live lock exists.
    @details A lock older than stale_seconds is treated as a crashed run and broken.
    """
    if os.path.exists(lock_path):
        age = time.time() - os.path.getmtime(lock_path)
        if age < stale_seconds:
            return False
        logger.warning(f"Breaking stale pipeline lock ({age:.0f}s old): {lock_path}")
        try:
            os.remove(lock_path)
        except OSError:
            return False
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_lock(lock_path: str) -> None:
    """@brief Remove the lock file if present."""
    try:
        os.remove(lock_path)
    except OSError:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_single_instance.py -v`
Expected: 3 PASS

- [ ] **Step 5: Wire into main.py**

In `main.py`, add the import near the other `src.` imports:

```python
from src.utils.single_instance import acquire_lock, release_lock
```

In `main()`, wrap the `run_pipeline` call (currently `signals = run_pipeline(config, skip_email=args.skip_email)`):

```python
        lock_path = os.path.join(project_root, "data", "pipeline.lock")
        if not acquire_lock(lock_path):
            logger.error("Another pipeline instance is already running (data/pipeline.lock). Exiting.")
            sys.exit(2)
        try:
            signals = run_pipeline(config, skip_email=args.skip_email)
        finally:
            release_lock(lock_path)
        sys.exit(0)
```

- [ ] **Step 6: Verify full suite and the lock manually**

Run: `pytest`
Expected: 241 passed, 1 skipped (238 + 3 new).

Manual check: `python main.py --init-db` still works (init path is before the lock).

- [ ] **Step 7: Commit**

```bash
git add src/utils/single_instance.py tests/test_single_instance.py main.py
git commit -m "feat: single-instance lock prevents concurrent pipeline runs"
```

---

### Task 2: `price_bars` table and Database accessors

**Files:**
- Modify: `src/database/models.py` (schema in `initialize()` around line 165, new methods after `get_sentiment_history` around line 445)
- Create: `tests/test_price_bars.py`

**Interfaces:**
- Consumes: existing `Database.connect()` / `initialize()` pattern (models.py:32–57).
- Produces (used by Tasks 3–12):
  - `Database.insert_price_bars(bars: List[Dict[str, Any]]) -> int` — bars have keys `ticker, date, open, high, low, close, volume` (`date` = `'YYYY-MM-DD'`); upserts, returns count.
  - `Database.get_last_bar_date(ticker: str) -> Optional[str]`
  - `Database.get_close_history(ticker: str, days: int = 250) -> List[float]` — closes ascending by date, last `days` calendar days.
  - `Database.get_bars_since(ticker: str, start_date: str) -> List[Dict[str, Any]]` — bars with `date > start_date`, ascending; keys `date, open, high, low, close, volume`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_price_bars.py
import pytest
from src.database.models import Database

BARS = [
    {'ticker': 'TEST', 'date': '2026-08-10', 'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5, 'volume': 1000},
    {'ticker': 'TEST', 'date': '2026-08-11', 'open': 10.5, 'high': 12.0, 'low': 10.4, 'close': 11.8, 'volume': 1500},
    {'ticker': 'TEST', 'date': '2026-08-12', 'open': 11.8, 'high': 11.9, 'low': 10.9, 'close': 11.0, 'volume': 900},
]


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    d.initialize()
    yield d
    d.close()


def test_insert_and_read_back(db):
    assert db.insert_price_bars(BARS) == 3
    bars = db.get_bars_since('TEST', '2026-08-10')
    assert [b['date'] for b in bars] == ['2026-08-11', '2026-08-12']
    assert bars[0]['high'] == 12.0 and bars[0]['volume'] == 1500


def test_upsert_is_idempotent(db):
    db.insert_price_bars(BARS)
    db.insert_price_bars(BARS)  # same rows again
    assert len(db.get_bars_since('TEST', '2026-08-09')) == 3


def test_last_bar_date(db):
    assert db.get_last_bar_date('TEST') is None
    db.insert_price_bars(BARS)
    assert db.get_last_bar_date('TEST') == '2026-08-12'


def test_close_history_ascending(db):
    db.insert_price_bars(BARS)
    assert db.get_close_history('TEST', days=3650) == [10.5, 11.8, 11.0]
    assert db.get_close_history('OTHER') == []


def test_empty_insert(db):
    assert db.insert_price_bars([]) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_price_bars.py -v`
Expected: FAIL — `AttributeError: 'Database' object has no attribute 'insert_price_bars'`

- [ ] **Step 3: Add the schema to `Database.initialize()`**

In `src/database/models.py`, inside `initialize()`, immediately after the signals-table index creation (after `idx_signals_ticker_date`):

```python
        # Daily OHLCV bars - the market-date spine (see docs/superpowers/plans/2026-08-19-market-date-spine-spec.md)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_bars (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume INTEGER,
                source TEXT DEFAULT 'yfinance',
                PRIMARY KEY (ticker, date)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_bars_date ON price_bars(date)
        """)
```

- [ ] **Step 4: Add the accessor methods**

In `src/database/models.py`, after `get_sentiment_history` (~line 445):

```python
    def insert_price_bars(self, bars: List[Dict[str, Any]]) -> int:
        """
        @brief Upsert daily OHLCV bars into the market-date spine.
        @param bars Dicts with ticker, date ('YYYY-MM-DD'), open, high, low, close, volume
        @return Number of bars written
        """
        if not bars:
            return 0
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO price_bars (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(b['ticker'], b['date'], b.get('open'), b.get('high'),
               b.get('low'), b.get('close'), b.get('volume')) for b in bars])
        conn.commit()
        return len(bars)

    def get_last_bar_date(self, ticker: str) -> Optional[str]:
        """@brief Most recent bar date for a ticker, or None."""
        cursor = self.connect().cursor()
        cursor.execute("SELECT MAX(date) FROM price_bars WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_close_history(self, ticker: str, days: int = 250) -> List[float]:
        """@brief Closing prices ascending by date over the last `days` calendar days."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cursor = self.connect().cursor()
        cursor.execute("""
            SELECT close FROM price_bars
            WHERE ticker = ? AND date >= ? AND close IS NOT NULL
            ORDER BY date ASC
        """, (ticker, cutoff))
        return [row[0] for row in cursor.fetchall()]

    def get_bars_since(self, ticker: str, start_date: str) -> List[Dict[str, Any]]:
        """@brief Bars strictly after start_date ('YYYY-MM-DD'), ascending."""
        cursor = self.connect().cursor()
        cursor.execute("""
            SELECT date, open, high, low, close, volume FROM price_bars
            WHERE ticker = ? AND date > ?
            ORDER BY date ASC
        """, (ticker, start_date))
        return [{'date': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in cursor.fetchall()]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_price_bars.py tests/test_database_models.py -v`
Expected: all PASS (existing schema tests unaffected).

- [ ] **Step 6: Commit**

```bash
git add src/database/models.py tests/test_price_bars.py
git commit -m "feat: add price_bars market-date spine table and accessors"
```

---

### Task 3: Gap-aware bars backfill collector

**Files:**
- Create: `src/collectors/bars_backfill.py`
- Create: `tests/test_bars_backfill.py`

**Interfaces:**
- Consumes: `Database.insert_price_bars`, `Database.get_last_bar_date` (Task 2); `YFinanceCollector.collect_historical_prices(tickers, period) -> Dict[str, List[Dict]]` (yfinance_collector.py:169 — returns dicts already shaped `ticker/date/open/high/low/close/volume`, plus a `collected_at` key that `insert_price_bars` ignores).
- Produces (used by Task 4): `backfill_price_bars(db, collector, tickers: List[str], min_history_days: int = 180) -> Dict[str, int]` — per-ticker count of bars written.

- [ ] **Step 1: Write the failing tests**

Use a fake collector — no network in tests.

```python
# tests/test_bars_backfill.py
from datetime import datetime, timedelta
import pytest
from src.database.models import Database
from src.collectors.bars_backfill import backfill_price_bars, _period_for_gap


class FakeCollector:
    def __init__(self):
        self.calls = []

    def collect_historical_prices(self, tickers, period="1mo"):
        self.calls.append((tuple(tickers), period))
        out = {}
        for t in tickers:
            out[t] = [
                {'ticker': t, 'date': '2026-08-18', 'open': 1.0, 'high': 2.0,
                 'low': 0.9, 'close': 1.5, 'volume': 100, 'collected_at': datetime.now()},
                {'ticker': t, 'date': '2026-08-19', 'open': 1.5, 'high': 2.5,
                 'low': 1.4, 'close': 2.0, 'volume': 200, 'collected_at': datetime.now()},
            ]
        return out


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    d.initialize()
    yield d
    d.close()


def test_backfill_new_ticker_uses_long_period(db):
    fake = FakeCollector()
    written = backfill_price_bars(db, fake, ['NEW'], min_history_days=180)
    assert written == {'NEW': 2}
    assert fake.calls[0][1] == '1y'
    assert db.get_last_bar_date('NEW') == '2026-08-19'


def test_backfill_small_gap_uses_short_period(db):
    recent = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    db.insert_price_bars([{'ticker': 'OLD', 'date': recent,
                           'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1}])
    fake = FakeCollector()
    backfill_price_bars(db, fake, ['OLD'])
    assert fake.calls[0][1] == '5d'


def test_period_mapping():
    assert _period_for_gap(3) == '5d'
    assert _period_for_gap(20) == '1mo'
    assert _period_for_gap(80) == '3mo'
    assert _period_for_gap(150) == '6mo'
    assert _period_for_gap(400) == '1y'


def test_up_to_date_ticker_is_skipped(db):
    today = datetime.now().strftime('%Y-%m-%d')
    db.insert_price_bars([{'ticker': 'CUR', 'date': today,
                           'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1}])
    fake = FakeCollector()
    written = backfill_price_bars(db, fake, ['CUR'])
    assert written == {} and fake.calls == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bars_backfill.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the backfill module**

```python
# src/collectors/bars_backfill.py
"""
@file bars_backfill.py
@brief Gap-aware daily OHLCV backfill into the price_bars spine.
@details Groups tickers by how far behind they are and fetches the smallest
         yfinance period that covers each gap. Runs are gap-tolerant: skip a
         month, the next run fills every trading day missed.
"""

from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def _period_for_gap(gap_days: int) -> str:
    """@brief Smallest yfinance period string covering a gap of N calendar days."""
    if gap_days <= 5:
        return '5d'
    if gap_days <= 25:
        return '1mo'
    if gap_days <= 85:
        return '3mo'
    if gap_days <= 170:
        return '6mo'
    return '1y'


def backfill_price_bars(db, collector, tickers: List[str],
                        min_history_days: int = 180) -> Dict[str, int]:
    """
    @brief Fill price_bars up to today for every ticker, fetching only the gap.
    @param db Database instance (insert_price_bars / get_last_bar_date)
    @param collector Object with collect_historical_prices(tickers, period)
    @param tickers Tickers to bring current
    @param min_history_days History fetched for tickers with no bars at all
    @return Dict of ticker -> bars written (tickers already current are omitted)
    """
    today = datetime.now().strftime('%Y-%m-%d')
    by_period: Dict[str, List[str]] = {}

    for ticker in sorted(set(tickers)):
        last = db.get_last_bar_date(ticker)
        if last is None:
            period = _period_for_gap(min_history_days)
        elif last >= today:
            continue  # already current
        else:
            gap = (datetime.now() - datetime.strptime(last, '%Y-%m-%d')).days
            period = _period_for_gap(gap)
        by_period.setdefault(period, []).append(ticker)

    written: Dict[str, int] = {}
    for period, group in by_period.items():
        results = collector.collect_historical_prices(group, period=period)
        for ticker, bars in results.items():
            count = db.insert_price_bars(bars)
            if count:
                written[ticker] = count

    total = sum(written.values())
    logger.info(f"Backfilled {total} bars across {len(written)} tickers")
    return written
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bars_backfill.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/bars_backfill.py tests/test_bars_backfill.py
git commit -m "feat: gap-aware daily bar backfill from yfinance into price_bars"
```

---

### Task 4: Wire backfill into the pipeline

**Files:**
- Modify: `main.py` (inside `run_pipeline`, immediately after the Step 1b parallel-collection block, before "Update Paper Trading Positions")
- Modify: `src/database/models.py` (one new query method)

**Interfaces:**
- Consumes: `backfill_price_bars` (Task 3), `YFinanceCollector` (already imported conditionally in main.py).
- Produces: `Database.get_signal_and_trade_tickers() -> List[str]` — distinct tickers appearing in `signals` or `paper_trades` (used again by Task 10); a `bars` backfill step in every pipeline run.

- [ ] **Step 1: Add `get_signal_and_trade_tickers` to Database (with test)**

Append to `tests/test_price_bars.py`:

```python
def test_signal_and_trade_tickers(db):
    conn = db.connect()
    conn.execute("INSERT INTO signals (ticker, signal_type, conviction_score, created_at) "
                 "VALUES ('AAA', 'insider_cluster', 50, '2026-08-01')")
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL,
        entry_date DATETIME, entry_price REAL, shares INTEGER, conviction INTEGER,
        signal_types TEXT, position_size REAL, status TEXT DEFAULT 'open')""")
    conn.execute("INSERT INTO paper_trades (ticker, entry_date) VALUES ('BBB', '2026-08-01')")
    conn.commit()
    assert db.get_signal_and_trade_tickers() == ['AAA', 'BBB']
```

Run `pytest tests/test_price_bars.py -v` — new test FAILS. Then add to `src/database/models.py` (after `get_bars_since`):

```python
    def get_signal_and_trade_tickers(self) -> List[str]:
        """@brief Distinct tickers ever seen in signals or paper_trades (sorted)."""
        cursor = self.connect().cursor()
        tickers = set()
        cursor.execute("SELECT DISTINCT ticker FROM signals")
        tickers.update(row[0] for row in cursor.fetchall())
        try:
            cursor.execute("SELECT DISTINCT ticker FROM paper_trades")
            tickers.update(row[0] for row in cursor.fetchall())
        except Exception:
            pass  # paper_trades not created yet (paper trading disabled)
        return sorted(tickers)
```

Run `pytest tests/test_price_bars.py -v` — all PASS.

- [ ] **Step 2: Add the pipeline step in main.py**

Add the import at the top of `main.py` with the other collectors:

```python
from src.collectors.bars_backfill import backfill_price_bars
```

In `run_pipeline`, insert after the Step 1b `ThreadPoolExecutor` block closes (directly before the `# ========== Update Paper Trading Positions ==========` comment):

```python
        # ========== Step 1c: Backfill daily bars (the market-date spine) ==========
        logger.info("Step 1c: Backfilling daily price bars...")
        if YFINANCE_AVAILABLE:
            try:
                bar_tickers = set(tracked_tickers) | set(db.get_signal_and_trade_tickers())
                yf_bars = YFinanceCollector()
                written = backfill_price_bars(db, yf_bars, sorted(bar_tickers))
                yf_bars.close()
                logger.info(f"  [OK] Bars: {sum(written.values())} bars across {len(written)} tickers")
            except Exception as e:
                logger.error(f"  [ERROR] Bar backfill failed: {e}")
        else:
            logger.warning("  [WARN] yfinance not available - price_bars not updated")
```

- [ ] **Step 3: Run the full suite**

Run: `pytest`
Expected: all green — the 238-passed baseline plus every test added in Tasks 1–4, same skip count.

- [ ] **Step 4: Live smoke test**

Run: `python main.py --skip-email`
Expected in log: `Step 1c: Backfilling daily price bars...` then `[OK] Bars: <N> bars across <M> tickers` with N in the thousands on first run (~180 days × ~100 tickers). Verify:

```bash
python -c "import sqlite3; c=sqlite3.connect('data/sentiment.db'); print(c.execute('select count(*), count(distinct ticker), min(date), max(date) from price_bars').fetchone())"
```

Expected: tens of thousands of rows, min date ~6 months back, max date = last trading day.

- [ ] **Step 5: Commit**

```bash
git add main.py src/database/models.py tests/test_price_bars.py
git commit -m "feat: pipeline backfills price_bars every run (Step 1c)"
```

---

### Task 5: Technicals read from bars

**Files:**
- Modify: `src/metrics/technical.py` (`TechnicalAnalyzer.analyze_ticker`, ~line 218)
- Modify: `tests/test_technical_analyzer.py`

**Interfaces:**
- Consumes: `Database.get_close_history(ticker, days)` (Task 2).
- Produces: unchanged `analyze_ticker(ticker, days=250) -> Dict` contract — same result keys, now computed over real daily closes.

- [ ] **Step 1: Update the analyzer's data source**

In `TechnicalAnalyzer.analyze_ticker`, replace:

```python
        # Get price history
        price_history = self.db.get_price_history(ticker, days=days)

        if not price_history:
            return {}

        prices = [p['price'] for p in price_history if p.get('price') is not None and p['price'] > 0]
```

with:

```python
        # Get real daily closes from the market-date spine (price_bars)
        prices = [p for p in self.db.get_close_history(ticker, days=days) if p and p > 0]
```

- [ ] **Step 2: Fix the tests' mock**

`tests/test_technical_analyzer.py` uses a mock database exposing `get_price_history`. Update the mock to expose `get_close_history(ticker, days)` returning a plain `List[float]` (the same price values the old mock wrapped in dicts). Do not change any expected indicator values — the math is untouched; only the fetch changed.

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_technical_analyzer.py -v`
Expected: all PASS.

- [ ] **Step 4: Live sanity check**

```bash
python -c "
from src.database.models import Database
from src.metrics.technical import TechnicalAnalyzer
db = Database('data/sentiment.db'); db.initialize()
t = TechnicalAnalyzer(db)
r = t.analyze_ticker('NVDA')
print({k: r.get(k) for k in ('rsi_14','ma_20','ma_50','momentum_10d')})
db.close()"
```

Expected: real values — `rsi_14` between 0–100 computed from ~120+ actual daily closes, `ma_50` non-None (both were None/garbage on ≤11 snapshots).

- [ ] **Step 5: Commit**

```bash
git add src/metrics/technical.py tests/test_technical_analyzer.py
git commit -m "fix: technical analysis computes on real daily bars, not run snapshots"
```

---

### Task 6: Bar-walking exit engine

The heart of the redesign. Pure function, no I/O — heavily tested.

**Files:**
- Create: `src/trading/engine.py`
- Create: `tests/test_trade_engine.py`

**Interfaces:**
- Consumes: bar dicts shaped like `Database.get_bars_since` output (`date, open, high, low, close`).
- Produces (used by Tasks 7, 9, 12):

```python
@dataclass(frozen=True)
class ExitEvent:
    date: str        # 'YYYY-MM-DD' market date of the exit
    price: float     # fill price
    reason: str      # 'stop_loss' | 'take_profit' | 'time_limit'
    days_held: int   # calendar days from entry to exit

def walk_bars(entry_date: str, entry_price: float, stop_loss: float,
              target_price: float, hold_days: int,
              bars: Sequence[Dict[str, Any]]) -> Optional[ExitEvent]
```

Exit rules per bar, in date order, **skipping any bar with `date <= entry_date`** (intraday sequencing on the entry day is unknown):
1. `open <= stop_loss` → exit at the **open** (gap through the stop fills at the open, not the stop).
2. `open >= target_price` → exit at the **open**.
3. `low <= stop_loss` → exit at the stop price. (Stop checked before target: conservative when both hit in one bar.)
4. `high >= target_price` → exit at the target price.
5. `days_held >= hold_days` → exit at the close.
6. No trigger across all bars → return `None` (position stays open).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_trade_engine.py
from src.trading.engine import walk_bars, ExitEvent


def bar(date, o, h, l, c):
    return {'date': date, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 0}


# Entry: $10.00 on 2026-06-01; stop $9.00 (-10%), target $12.00 (+20%), hold 30d
ARGS = dict(entry_date='2026-06-01', entry_price=10.0, stop_loss=9.0,
            target_price=12.0, hold_days=30)


def test_no_exit_returns_none():
    bars = [bar('2026-06-02', 10.0, 10.5, 9.8, 10.2)]
    assert walk_bars(bars=bars, **ARGS) is None


def test_entry_day_bar_is_skipped():
    bars = [bar('2026-06-01', 10.0, 15.0, 5.0, 10.0)]  # wild entry-day bar
    assert walk_bars(bars=bars, **ARGS) is None


def test_intrabar_stop_fills_at_stop_price():
    bars = [bar('2026-06-02', 9.8, 10.0, 8.5, 9.5)]
    e = walk_bars(bars=bars, **ARGS)
    assert e == ExitEvent(date='2026-06-02', price=9.0, reason='stop_loss', days_held=1)


def test_gap_down_fills_at_open_not_stop():
    bars = [bar('2026-06-02', 7.0, 7.5, 6.8, 7.2)]  # opened far below the stop
    e = walk_bars(bars=bars, **ARGS)
    assert e.price == 7.0 and e.reason == 'stop_loss'


def test_intrabar_target_fills_at_target_price():
    bars = [bar('2026-06-02', 10.5, 12.5, 10.4, 12.1)]
    e = walk_bars(bars=bars, **ARGS)
    assert e.price == 12.0 and e.reason == 'take_profit'


def test_gap_up_fills_at_open():
    bars = [bar('2026-06-02', 13.0, 13.5, 12.8, 13.2)]
    e = walk_bars(bars=bars, **ARGS)
    assert e.price == 13.0 and e.reason == 'take_profit'


def test_stop_wins_when_both_hit_same_bar():
    bars = [bar('2026-06-02', 10.0, 12.5, 8.5, 11.0)]  # touched both
    e = walk_bars(bars=bars, **ARGS)
    assert e.reason == 'stop_loss'


def test_first_triggering_bar_wins():
    bars = [bar('2026-06-02', 10.0, 10.5, 9.9, 10.1),
            bar('2026-06-03', 10.1, 12.5, 10.0, 12.2),   # target here
            bar('2026-06-04', 12.2, 12.4, 8.0, 8.1)]     # stop later - never reached
    e = walk_bars(bars=bars, **ARGS)
    assert e.date == '2026-06-03' and e.reason == 'take_profit'


def test_time_limit_exits_at_close():
    bars = [bar('2026-06-15', 10.0, 10.5, 9.9, 10.1),
            bar('2026-07-02', 10.1, 10.6, 10.0, 10.4)]   # 31 calendar days after entry
    e = walk_bars(bars=bars, **ARGS)
    assert e == ExitEvent(date='2026-07-02', price=10.4, reason='time_limit', days_held=31)


def test_stop_beats_time_limit_on_same_bar():
    bars = [bar('2026-07-02', 9.5, 9.6, 8.8, 9.0)]
    e = walk_bars(bars=bars, **ARGS)
    assert e.reason == 'stop_loss' and e.price == 9.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_trade_engine.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the engine**

```python
# src/trading/engine.py
"""
@file engine.py
@brief Pure bar-walking exit engine shared by paper trading and the backtester.
@details Replays daily OHLCV bars in date order and returns the first exit a
         real resting order would have produced. No I/O - fully testable.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True)
class ExitEvent:
    """@brief The first exit a position's rules produce while walking bars."""
    date: str        # 'YYYY-MM-DD' market date of the exit
    price: float     # fill price
    reason: str      # 'stop_loss' | 'take_profit' | 'time_limit'
    days_held: int   # calendar days from entry to exit


def _days_between(entry_date: str, bar_date: str) -> int:
    d0 = datetime.strptime(entry_date[:10], '%Y-%m-%d')
    d1 = datetime.strptime(bar_date[:10], '%Y-%m-%d')
    return (d1 - d0).days


def walk_bars(entry_date: str, entry_price: float, stop_loss: float,
              target_price: float, hold_days: int,
              bars: Sequence[Dict[str, Any]]) -> Optional[ExitEvent]:
    """
    @brief Walk daily bars after entry_date and return the first exit, if any.
    @details Per bar: gap-open through stop/target fills at the open; an
             intrabar stop fills at the stop price (checked before the target -
             conservative when both hit); intrabar target fills at the target
             price; calendar hold_days exit fills at the close. The entry-day
             bar is skipped because intraday sequencing is unknown.
    """
    entry_day = entry_date[:10]
    for b in bars:
        bar_date = b['date'][:10]
        if bar_date <= entry_day:
            continue
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        if o is None or h is None or l is None or c is None:
            continue
        held = _days_between(entry_day, bar_date)

        if o <= stop_loss:
            return ExitEvent(bar_date, o, 'stop_loss', held)
        if o >= target_price:
            return ExitEvent(bar_date, o, 'take_profit', held)
        if l <= stop_loss:
            return ExitEvent(bar_date, stop_loss, 'stop_loss', held)
        if h >= target_price:
            return ExitEvent(bar_date, target_price, 'take_profit', held)
        if held >= hold_days:
            return ExitEvent(bar_date, c, 'time_limit', held)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_trade_engine.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add src/trading/engine.py tests/test_trade_engine.py
git commit -m "feat: pure bar-walking exit engine (walk_bars/ExitEvent)"
```

---

### Task 7: Paper trading replays bars through the engine

**Files:**
- Modify: `src/trading/paper_trading.py` (`_init_tables`, `update_positions` → `update_positions_from_bars`, `_get_historical_price`)
- Modify: `main.py` (the "Update Paper Trading Positions" block)
- Modify: `tests/test_paper_trading.py` (TestUpdatePositions class)

**Interfaces:**
- Consumes: `walk_bars`/`ExitEvent` (Task 6); `Database.get_bars_since` (Task 2).
- Produces: `PaperTradingManager.update_positions_from_bars(db, current_date: datetime) -> None` (replaces `update_positions(current_prices, current_date)` — the old method is deleted). Positions gain a `last_evaluated_date TEXT` column so replay resumes where it left off.

- [ ] **Step 1: Add the `last_evaluated_date` migration**

In `PaperTradingManager._init_tables`, after `conn.executescript(schema_sql)` and before `conn.commit()`:

```python
                cursor = conn.cursor()
                cols = [r[1] for r in cursor.execute("PRAGMA table_info(paper_trades)").fetchall()]
                if 'last_evaluated_date' not in cols:
                    cursor.execute("ALTER TABLE paper_trades ADD COLUMN last_evaluated_date TEXT")
```

- [ ] **Step 2: Write the failing tests**

Replace the body of `TestUpdatePositions` in `tests/test_paper_trading.py` with bar-based tests (keep the class's existing fixture pattern for constructing a manager over a tmp DB — reuse the same `config` dict used by neighboring test classes: position_size 1000, hold_days 30, stop −10, target +20, min_conviction 25):

```python
class TestUpdatePositionsFromBars:
    def _make(self, tmp_path):
        from src.database.models import Database
        db = Database(str(tmp_path / "t.db"))
        db.initialize()
        config = {'paper_trading': {'enabled': True, 'min_conviction': 25,
                                    'position_size': 1000, 'max_open_positions': 10,
                                    'hold_days': 30, 'stop_loss_pct': -10,
                                    'take_profit_pct': 20}}
        mgr = PaperTradingManager(db.db_path, config)
        return db, mgr

    def test_stop_fires_on_the_bar_that_crossed_it(self, tmp_path):
        from datetime import datetime
        db, mgr = self._make(tmp_path)
        mgr.create_paper_trade('XYZ', 10.0, 50, ['insider_cluster'],
                               datetime(2026, 6, 1, 12, 0))
        db.insert_price_bars([
            {'ticker': 'XYZ', 'date': '2026-06-02', 'open': 9.8, 'high': 9.9, 'low': 8.5, 'close': 8.8, 'volume': 1},
            {'ticker': 'XYZ', 'date': '2026-06-03', 'open': 8.8, 'high': 9.0, 'low': 8.0, 'close': 8.2, 'volume': 1},
        ])
        mgr.update_positions_from_bars(db, datetime(2026, 8, 19))
        import sqlite3, contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            row = conn.execute("SELECT status, exit_reason, exit_price, exit_date, days_held "
                               "FROM paper_trades WHERE ticker='XYZ'").fetchone()
        assert row[0] == 'closed' and row[1] == 'stop_loss'
        assert row[2] == 9.0                      # stop price, not the months-later snapshot
        assert row[3].startswith('2026-06-02')    # the bar that crossed it
        assert row[4] == 1

    def test_open_position_records_progress(self, tmp_path):
        from datetime import datetime
        db, mgr = self._make(tmp_path)
        mgr.create_paper_trade('ABC', 10.0, 50, ['insider_cluster'],
                               datetime(2026, 8, 10, 12, 0))
        db.insert_price_bars([
            {'ticker': 'ABC', 'date': '2026-08-11', 'open': 10.1, 'high': 10.5, 'low': 10.0, 'close': 10.4, 'volume': 1},
        ])
        mgr.update_positions_from_bars(db, datetime(2026, 8, 19))
        import sqlite3, contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            status, last_eval = conn.execute(
                "SELECT status, last_evaluated_date FROM paper_trades WHERE ticker='ABC'").fetchone()
            snap = conn.execute("SELECT current_price FROM paper_trade_snapshots").fetchone()
        assert status == 'open' and last_eval == '2026-08-11'
        assert snap[0] == 10.4

    def test_no_bars_leaves_position_untouched(self, tmp_path):
        from datetime import datetime
        db, mgr = self._make(tmp_path)
        mgr.create_paper_trade('QQQ', 10.0, 50, ['insider_cluster'],
                               datetime(2026, 8, 10, 12, 0))
        mgr.update_positions_from_bars(db, datetime(2026, 8, 19))
        import sqlite3, contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            status = conn.execute("SELECT status FROM paper_trades WHERE ticker='QQQ'").fetchone()[0]
        assert status == 'open'
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_paper_trading.py -v -k FromBars`
Expected: FAIL — no attribute `update_positions_from_bars`.

- [ ] **Step 4: Implement the replay method (and delete the old one)**

In `src/trading/paper_trading.py`, add the import at the top:

```python
from src.trading.engine import walk_bars
```

Replace the entire `update_positions` method with:

```python
    def update_positions_from_bars(self, db, current_date: datetime):
        """
        @brief Replay daily bars since each position's last evaluation and
               apply stop/target/time exits exactly where a resting order
               would have filled - regardless of pipeline run cadence.
        @param db Database instance exposing get_bars_since(ticker, start_date)
        @param current_date Now (used for logging only; exits use bar dates)
        """
        if not self.enabled:
            return

        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ticker, entry_date, entry_price, shares, stop_loss,
                       target_price, last_evaluated_date
                FROM paper_trades WHERE status = 'open'
            """)
            open_trades = cursor.fetchall()

            closed = 0
            for (trade_id, ticker, entry_date_str, entry_price, shares,
                 stop_loss, target_price, last_eval) in open_trades:
                entry_day = entry_date_str[:10]
                start = last_eval if last_eval and last_eval > entry_day else entry_day
                bars = db.get_bars_since(ticker, start)
                if not bars:
                    continue

                exit_event = walk_bars(entry_day, entry_price, stop_loss,
                                       target_price, self.hold_days, bars)
                if exit_event:
                    days_held = exit_event.days_held
                    self._close_position(cursor, trade_id, exit_event.price,
                                         datetime.strptime(exit_event.date, '%Y-%m-%d'),
                                         exit_event.reason, entry_price, shares, days_held)
                    closed += 1
                else:
                    last_bar = bars[-1]
                    unrealized_pnl = (last_bar['close'] - entry_price) * shares
                    unrealized_pct = ((last_bar['close'] - entry_price) / entry_price) * 100
                    cursor.execute("""
                        INSERT OR REPLACE INTO paper_trade_snapshots
                        (trade_id, snapshot_date, current_price, unrealized_pnl, unrealized_pct)
                        VALUES (?, ?, ?, ?, ?)
                    """, (trade_id, last_bar['date'], last_bar['close'],
                          unrealized_pnl, unrealized_pct))
                    cursor.execute("UPDATE paper_trades SET last_evaluated_date = ? WHERE id = ?",
                                   (last_bar['date'], trade_id))
            conn.commit()
        logger.info(f"Evaluated {len(open_trades)} open positions against bars "
                    f"({closed} closed)")
```

Also replace `_get_historical_price` (used by `backfill_from_signals`) to read bars:

```python
    def _get_historical_price(self, ticker: str, date: datetime) -> Optional[float]:
        """@brief Close of the first bar on/after the date (within 5 days)."""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT close FROM price_bars
                WHERE ticker = ? AND date >= ? AND date < ?
                ORDER BY date ASC LIMIT 1
            """, (ticker, date.strftime('%Y-%m-%d'),
                  (date + timedelta(days=5)).strftime('%Y-%m-%d')))
            result = cursor.fetchone()
        return result[0] if result else None
```

- [ ] **Step 5: Update main.py's call site**

In `run_pipeline`, replace the "Update Paper Trading Positions" block body:

```python
        if paper_trading.enabled:
            logger.info("Updating paper trading positions against daily bars...")
            try:
                paper_trading.update_positions_from_bars(db, datetime.now())
                logger.info("  [OK] Paper trading positions updated")
            except Exception as e:
                logger.error(f"  [ERROR] Paper trading update failed: {e}")
```

Also **move this block** so it runs *after* Step 1c (bar backfill) — it currently sits right after Step 1b; after Task 4 the backfill block is between them, so only verify the order is: Step 1b → Step 1c (bars) → paper-trading update. Delete the now-unused `current_prices = db.get_latest_prices()` line from the old block.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_paper_trading.py tests/test_trade_engine.py -v`
Expected: all PASS (old snapshot-based TestUpdatePositions tests replaced in Step 2).

Run: `pytest`
Expected: full suite green.

- [ ] **Step 7: Commit**

```bash
git add src/trading/paper_trading.py main.py tests/test_paper_trading.py
git commit -m "feat: paper trading replays daily bars through the shared exit engine"
```

---

### Task 8: Book hygiene — dedup, zero-share guard, signal linkage

**Files:**
- Modify: `src/trading/paper_trading.py` (`create_paper_trade`)
- Modify: `src/database/models.py` (`insert_signals` returns ids)
- Modify: `main.py` (paper-trade creation loop)
- Modify: `tests/test_paper_trading.py`, `tests/test_database_models.py`

**Interfaces:**
- Consumes: existing `create_paper_trade` (paper_trading.py:70) and `insert_signals` (models.py:352).
- Produces: `Database.insert_signals(signals) -> Dict[str, int]` (ticker → signal row id for this batch); `create_paper_trade` refuses a ticker that already has an **open** position and refuses `shares == 0`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_paper_trading.py`:

```python
class TestBookHygiene:
    def _mgr(self, tmp_path):
        from src.database.models import Database
        db = Database(str(tmp_path / "t.db"))
        db.initialize()
        config = {'paper_trading': {'enabled': True, 'min_conviction': 25,
                                    'position_size': 1000, 'max_open_positions': 10,
                                    'hold_days': 30, 'stop_loss_pct': -10,
                                    'take_profit_pct': 20}}
        return db, PaperTradingManager(db.db_path, config)

    def test_second_open_position_same_ticker_rejected(self, tmp_path):
        from datetime import datetime, timedelta
        db, mgr = self._mgr(tmp_path)
        t1 = mgr.create_paper_trade('DUP', 10.0, 50, ['insider_cluster'], datetime(2026, 8, 1))
        t2 = mgr.create_paper_trade('DUP', 10.5, 50, ['insider_cluster'],
                                    datetime(2026, 8, 1) + timedelta(minutes=5))
        assert t1 is not None and t2 is None

    def test_zero_share_trade_rejected(self, tmp_path):
        from datetime import datetime
        db, mgr = self._mgr(tmp_path)
        # conviction 25 -> $500 position; price $679 -> 0 shares (the VOO case)
        assert mgr.create_paper_trade('VOO', 679.46, 25, ['news_sentiment_bullish'],
                                      datetime(2026, 8, 1)) is None

    def test_signal_id_is_stored(self, tmp_path):
        from datetime import datetime
        db, mgr = self._mgr(tmp_path)
        tid = mgr.create_paper_trade('LNK', 10.0, 50, ['insider_cluster'],
                                     datetime(2026, 8, 1), signal_id=77)
        import sqlite3, contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            sid = conn.execute("SELECT signal_id FROM paper_trades WHERE id=?", (tid,)).fetchone()[0]
        assert sid == 77
```

Add to `tests/test_database_models.py`:

```python
def test_insert_signals_returns_ids(tmp_path):
    from datetime import datetime
    from src.database.models import Database
    from src.signals.generator import Signal
    db = Database(str(tmp_path / "t.db"))
    db.initialize()
    now = datetime(2026, 8, 19, 21, 30)
    sigs = [Signal(ticker='AAA', signal_type='insider_cluster', conviction_score=50,
                   price_at_signal=10.0, triggers=['insider_cluster'], notes='n', created_at=now)]
    ids = db.insert_signals(sigs)
    assert set(ids.keys()) == {'AAA'} and isinstance(ids['AAA'], int)
    db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_paper_trading.py -k Hygiene tests/test_database_models.py -k returns_ids -v`
Expected: FAIL (open-dup currently allowed; zero-share currently allowed; insert_signals returns None).

- [ ] **Step 3: Implement `create_paper_trade` guards**

In `create_paper_trade`, after the `_trade_exists` check and before the max-open-positions check, add:

```python
        # One open position per ticker - a second signal doesn't double the bet
        if self._has_open_position(ticker):
            logger.info(f"Open position already exists for {ticker}, skipping new trade")
            return None
```

After `shares = int(position_size / entry_price)`, add:

```python
        if shares == 0:
            logger.warning(f"Position size ${position_size:.2f} buys 0 shares of "
                           f"{ticker} @ ${entry_price:.2f}, skipping")
            return None
```

Add the helper next to `_trade_exists`:

```python
    def _has_open_position(self, ticker: str) -> bool:
        """@brief True if an open paper trade already exists for this ticker."""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM paper_trades WHERE ticker = ? AND status = 'open' LIMIT 1",
                           (ticker,))
            return cursor.fetchone() is not None
```

- [ ] **Step 4: Make `insert_signals` return ids**

In `src/database/models.py`, change `insert_signals` to collect ids after the loop (keep the existing INSERT unchanged) and update its signature/docstring:

```python
    def insert_signals(self, signals: List[Any]) -> Dict[str, int]:
        """
        @brief Insert generated signals
        @param signals List of Signal objects
        @return Dict mapping ticker -> signals.id for this batch (for trade linkage)
        """
        if not signals:
            return {}
```

…and after `conn.commit()`:

```python
        ids: Dict[str, int] = {}
        for signal in signals:
            row = cursor.execute(
                "SELECT id FROM signals WHERE ticker = ? AND created_at = ?",
                (signal.ticker, signal.created_at)).fetchone()
            if row:
                ids[signal.ticker] = row[0]
        logger.info(f"Inserted {len(signals)} signal records")
        return ids
```

(Delete the old trailing `logger.info` so it isn't duplicated.)

- [ ] **Step 5: Link signal ids in main.py**

In `run_pipeline` Step 3, capture the mapping:

```python
            signal_ids = {}
            if all_signals:
                signal_ids = db.insert_signals(all_signals)
                logger.info(f"  [OK] Inserted {len(all_signals)} signals into database")
```

In the "Create Paper Trades from Signals" loop, pass it through:

```python
                            trade_id = paper_trading.create_paper_trade(
                                ticker=signal.ticker,
                                entry_price=price_data['price'],
                                conviction=int(signal.conviction_score),
                                signal_types=signal.triggers,
                                entry_date=datetime.now(),
                                signal_id=signal_ids.get(signal.ticker)
                            )
```

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: green. If any pre-existing paper-trading test asserted that two same-ticker trades can coexist, update it to reflect the new one-open-per-ticker rule (that behavior is the bug this task fixes).

- [ ] **Step 7: Commit**

```bash
git add src/trading/paper_trading.py src/database/models.py main.py tests/test_paper_trading.py tests/test_database_models.py
git commit -m "fix: one open position per ticker, zero-share guard, signal_id linkage"
```

---

### Task 9: One-time book revalidation utility

Voids the 11 duplicates and the 0-share trade (annotate, never delete), and re-closes historical trades against real bars — the acceptance evidence that the engine works (UP: −42% recorded vs ~−10% by the rules).

**Files:**
- Create: `utils/revalidate_paper_trades.py`
- Create: `tests/test_revalidate.py`

**Interfaces:**
- Consumes: `walk_bars` (Task 6), `Database.get_bars_since` (Task 2), `paper_trades` rows.
- Produces: CLI `python utils/revalidate_paper_trades.py [--apply]`; statuses `void_duplicate` / `void_zero_shares`; re-closed trades keep their original exit in `notes` as JSON. Also exposes `find_duplicates(conn) -> List[int]` and `revalidate(db_path, apply: bool) -> List[Dict]` for tests.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_revalidate.py
import json
import sqlite3
import contextlib
from datetime import datetime
import pytest
from src.database.models import Database
from src.trading.paper_trading import PaperTradingManager
from utils.revalidate_paper_trades import revalidate


CONFIG = {'paper_trading': {'enabled': True, 'min_conviction': 25,
                            'position_size': 1000, 'max_open_positions': 10,
                            'hold_days': 30, 'stop_loss_pct': -10, 'take_profit_pct': 20}}


@pytest.fixture
def seeded(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.initialize()
    PaperTradingManager(db.db_path, CONFIG)  # creates paper_trades tables
    with contextlib.closing(sqlite3.connect(db.db_path)) as conn:
        # Two duplicates (same ticker, same entry day, minutes apart) + one zero-share
        rows = [
            ('DUP', '2026-06-01T10:00:00', 10.0, 100, 50, '["insider_cluster"]', 1000.0, 9.0, 12.0, 'closed'),
            ('DUP', '2026-06-01T10:05:00', 10.0, 100, 50, '["insider_cluster"]', 1000.0, 9.0, 12.0, 'closed'),
            ('ZRO', '2026-06-01T10:00:00', 700.0, 0, 25, '["news_sentiment_bullish"]', 0.0, 630.0, 840.0, 'closed'),
        ]
        for r in rows:
            conn.execute("""INSERT INTO paper_trades (ticker, entry_date, entry_price, shares,
                conviction, signal_types, position_size, stop_loss, target_price, status,
                exit_date, exit_price, exit_reason, return_pct, profit_loss, days_held)
                VALUES (?,?,?,?,?,?,?,?,?,?, '2026-08-19T00:00:00', 8.0, 'time_limit', -20.0, -200.0, 79)""", r)
        conn.commit()
    # Bars: stop (9.0) crossed on 2026-06-05
    db.insert_price_bars([
        {'ticker': 'DUP', 'date': '2026-06-02', 'open': 9.9, 'high': 10.1, 'low': 9.5, 'close': 9.6, 'volume': 1},
        {'ticker': 'DUP', 'date': '2026-06-05', 'open': 9.4, 'high': 9.5, 'low': 8.7, 'close': 8.8, 'volume': 1},
    ])
    yield db
    db.close()


def test_dry_run_changes_nothing(seeded):
    report = revalidate(seeded.db_path, apply=False)
    assert any(r['action'] == 'void_duplicate' for r in report)
    with contextlib.closing(sqlite3.connect(seeded.db_path)) as conn:
        statuses = [r[0] for r in conn.execute("SELECT status FROM paper_trades")]
    assert statuses == ['closed', 'closed', 'closed']


def test_apply_voids_and_recloses(seeded):
    revalidate(seeded.db_path, apply=True)
    with contextlib.closing(sqlite3.connect(seeded.db_path)) as conn:
        rows = list(conn.execute(
            "SELECT id, status, exit_reason, exit_price, notes FROM paper_trades ORDER BY id"))
    # Lowest id survives; duplicate + zero-share voided
    assert rows[0][1] == 'closed' and rows[1][1] == 'void_duplicate'
    assert rows[2][1] == 'void_zero_shares'
    # Survivor re-closed against bars: stop at 9.0 on 2026-06-05
    assert rows[0][2] == 'stop_loss' and rows[0][3] == 9.0
    original = json.loads(rows[0][4])['original_exit']
    assert original['exit_price'] == 8.0 and original['exit_reason'] == 'time_limit'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_revalidate.py -v`
Expected: FAIL — module not found. (If `utils/` lacks `__init__.py` and the import fails for that reason, add an empty `utils/__init__.py`.)

- [ ] **Step 3: Implement the utility**

```python
# utils/revalidate_paper_trades.py
"""
@file revalidate_paper_trades.py
@brief One-time paper-trade book repair: void duplicates and zero-share rows
       (annotated, never deleted), and re-close historical trades against real
       daily bars via the shared exit engine.
@usage python utils/revalidate_paper_trades.py           # dry run, prints report
       python utils/revalidate_paper_trades.py --apply   # writes changes
"""

import argparse
import contextlib
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.models import Database
from src.trading.engine import walk_bars

HOLD_DAYS = 30  # matches config paper_trading.hold_days


def find_duplicates(conn) -> List[int]:
    """@brief Ids to void: all but the lowest id per (ticker, entry day)."""
    rows = conn.execute("""
        SELECT id, ticker, substr(entry_date, 1, 10) AS day FROM paper_trades
        WHERE status IN ('open', 'closed') ORDER BY id
    """).fetchall()
    seen, dupes = set(), []
    for trade_id, ticker, day in rows:
        key = (ticker, day)
        if key in seen:
            dupes.append(trade_id)
        else:
            seen.add(key)
    return dupes


def revalidate(db_path: str, apply: bool) -> List[Dict]:
    db = Database(db_path)
    db.initialize()
    report: List[Dict] = []
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        for trade_id in find_duplicates(conn):
            report.append({'id': trade_id, 'action': 'void_duplicate'})
            if apply:
                conn.execute("UPDATE paper_trades SET status='void_duplicate', "
                             "notes=COALESCE(notes,'') || ' [voided: duplicate entry]' WHERE id=?",
                             (trade_id,))

        for (trade_id,) in conn.execute(
                "SELECT id FROM paper_trades WHERE shares = 0 AND status IN ('open','closed')"):
            report.append({'id': trade_id, 'action': 'void_zero_shares'})
            if apply:
                conn.execute("UPDATE paper_trades SET status='void_zero_shares', "
                             "notes=COALESCE(notes,'') || ' [voided: 0 shares]' WHERE id=?",
                             (trade_id,))
        if apply:
            conn.commit()

        # Re-close surviving closed trades against real bars
        for row in conn.execute("""
                SELECT id, ticker, entry_date, entry_price, shares, stop_loss,
                       target_price, exit_date, exit_price, exit_reason
                FROM paper_trades WHERE status='closed'""").fetchall():
            (trade_id, ticker, entry_date, entry_price, shares,
             stop_loss, target_price, old_date, old_price, old_reason) = row
            bars = db.get_bars_since(ticker, entry_date[:10])
            exit_event = walk_bars(entry_date[:10], entry_price, stop_loss,
                                   target_price, HOLD_DAYS, bars)
            if exit_event is None:
                continue
            delta = {'id': trade_id, 'ticker': ticker, 'action': 'reclose',
                     'old': {'exit_date': old_date, 'exit_price': old_price, 'exit_reason': old_reason},
                     'new': {'exit_date': exit_event.date, 'exit_price': exit_event.price,
                             'exit_reason': exit_event.reason}}
            report.append(delta)
            if apply:
                pnl = (exit_event.price - entry_price) * shares
                pct = ((exit_event.price - entry_price) / entry_price) * 100
                original = json.dumps({'original_exit': {
                    'exit_date': old_date, 'exit_price': old_price, 'exit_reason': old_reason}})
                conn.execute("""UPDATE paper_trades SET exit_date=?, exit_price=?, exit_reason=?,
                    profit_loss=?, return_pct=?, days_held=?, notes=? WHERE id=?""",
                    (exit_event.date, exit_event.price, exit_event.reason,
                     pnl, pct, exit_event.days_held, original, trade_id))
        if apply:
            conn.commit()
    db.close()
    return report


def main():
    parser = argparse.ArgumentParser(description='Repair the paper-trade book against real bars')
    parser.add_argument('--db', default='data/sentiment.db')
    parser.add_argument('--apply', action='store_true', help='Write changes (default: dry run)')
    args = parser.parse_args()
    report = revalidate(args.db, apply=args.apply)
    for entry in report:
        print(json.dumps(entry))
    print(f"\n{'APPLIED' if args.apply else 'DRY RUN'}: {len(report)} actions")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_revalidate.py -v`
Expected: 2 PASS

- [ ] **Step 5: Run against the live book — dry run first, review, then apply**

```bash
python utils/revalidate_paper_trades.py
```

Review the printed report. Expected: ~11 `void_duplicate` (SOFI ×2, GO ×2, CIA ×1, LUNR ×1, AM ×1, and the 4 duplicated 2026-08-19 entries), 1 `void_zero_shares` (VOO, id 15), and `reclose` deltas — trade 16 (UP) must show `old: -42.3% stop_loss` → `new: exit at 7.983 stop_loss` on a June date. If the report matches, run:

```bash
python utils/revalidate_paper_trades.py --apply
```

Then confirm the summary now reflects rule-true results:

```bash
python -c "
import sqlite3; c = sqlite3.connect('data/sentiment.db')
print(c.execute(\"select status, count(*), round(sum(profit_loss),2) from paper_trades group by status\").fetchall())"
```

- [ ] **Step 6: Commit**

```bash
git add utils/revalidate_paper_trades.py tests/test_revalidate.py
git commit -m "feat: revalidation utility - void duplicate/zero-share trades, re-close against bars"
```

---

### Task 10: Signal outcome backfill

**Files:**
- Create: `src/analysis/outcomes.py`
- Create: `tests/test_outcomes.py`
- Modify: `src/database/models.py` (`initialize()` — column migration)
- Modify: `main.py` (call after Step 1c)

**Interfaces:**
- Consumes: `price_bars`, `signals` (`price_at_signal`, `created_at`), `Database.connect()`.
- Produces: `update_signal_outcomes(db) -> int` (signals updated). New `signals` columns `fwd_return_5d REAL`, `fwd_return_10d REAL`, `fwd_return_30d REAL`. Convention: forward return at +N **trading days** (bar count), pct vs the baseline close (first bar on/after the signal date); `outcome_price/outcome_date/outcome_pct` mirror the 10-day point. Each horizon fills only once enough bars exist — partial fills allowed.

- [ ] **Step 1: Add the column migration**

In `src/database/models.py`, add a helper method to `Database`:

```python
    @staticmethod
    def _ensure_column(cursor, table: str, column: str, decl: str):
        """@brief Add a column if it doesn't exist (idempotent migration)."""
        cols = [r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
```

In `initialize()`, after the `price_bars` DDL:

```python
        # Forward-return outcome columns (learning loop)
        self._ensure_column(cursor, 'signals', 'fwd_return_5d', 'REAL')
        self._ensure_column(cursor, 'signals', 'fwd_return_10d', 'REAL')
        self._ensure_column(cursor, 'signals', 'fwd_return_30d', 'REAL')
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_outcomes.py
import sqlite3
import pytest
from src.database.models import Database
from src.analysis.outcomes import update_signal_outcomes


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "t.db"))
    d.initialize()
    yield d
    d.close()


def _seed_signal(db, ticker, created_at, price):
    db.connect().execute(
        "INSERT INTO signals (ticker, signal_type, conviction_score, price_at_signal, created_at) "
        "VALUES (?, 'insider_cluster', 50, ?, ?)", (ticker, price, created_at))
    db.connect().commit()


def _seed_bars(db, ticker, start_close, n):
    # n consecutive weekday-ish bars, close rising 1% per bar from start_close
    from datetime import date, timedelta
    bars, d = [], date(2026, 6, 1)
    close = start_close
    while len(bars) < n:
        if d.weekday() < 5:
            bars.append({'ticker': ticker, 'date': d.isoformat(), 'open': close,
                         'high': close * 1.01, 'low': close * 0.99,
                         'close': round(close, 4), 'volume': 1})
            close *= 1.01
        d += timedelta(days=1)
    db.insert_price_bars(bars)
    return bars


def test_full_horizons_filled(db):
    bars = _seed_bars(db, 'WIN', 100.0, 40)
    _seed_signal(db, 'WIN', bars[0]['date'] + ' 12:00:00', 100.0)
    assert update_signal_outcomes(db) == 1
    row = db.connect().execute(
        "SELECT fwd_return_5d, fwd_return_10d, fwd_return_30d, outcome_pct, outcome_date "
        "FROM signals").fetchone()
    # +5 trading days at 1%/bar compounding ~ +5.1%
    assert 4.5 < row[0] < 5.6 and 9.0 < row[1] < 11.5 and 33.0 < row[2] < 36.5
    assert row[3] == row[1]                       # outcome_pct mirrors the 10d point
    assert row[4] is not None


def test_partial_horizons_fill_incrementally(db):
    bars = _seed_bars(db, 'NEW', 100.0, 7)       # only 7 bars: 5d fills, 10d/30d don't
    _seed_signal(db, 'NEW', bars[0]['date'] + ' 12:00:00', 100.0)
    update_signal_outcomes(db)
    row = db.connect().execute(
        "SELECT fwd_return_5d, fwd_return_10d, fwd_return_30d FROM signals").fetchone()
    assert row[0] is not None and row[1] is None and row[2] is None


def test_no_bars_no_crash(db):
    _seed_signal(db, 'GHOST', '2026-06-01 12:00:00', 10.0)
    assert update_signal_outcomes(db) == 0


def test_completed_signals_skipped(db):
    bars = _seed_bars(db, 'DONE', 100.0, 40)
    _seed_signal(db, 'DONE', bars[0]['date'] + ' 12:00:00', 100.0)
    update_signal_outcomes(db)
    assert update_signal_outcomes(db) == 0        # nothing left to fill
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_outcomes.py -v`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement outcomes**

```python
# src/analysis/outcomes.py
"""
@file outcomes.py
@brief Backfill signal forward returns from the price_bars spine.
@details The learning loop: every signal gets +5/+10/+30 trading-day forward
         returns once bars exist, making per-trigger edge measurable.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

HORIZONS = ((5, 'fwd_return_5d'), (10, 'fwd_return_10d'), (30, 'fwd_return_30d'))


def update_signal_outcomes(db) -> int:
    """
    @brief Fill fwd_return_5d/10d/30d for signals missing them; mirror the
           10-day point into outcome_price/outcome_date/outcome_pct.
    @param db Database instance
    @return Number of signals that received at least one new value
    """
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, ticker, substr(created_at, 1, 10) AS day, price_at_signal,
               fwd_return_5d, fwd_return_10d, fwd_return_30d
        FROM signals
        WHERE fwd_return_30d IS NULL
    """)
    updated = 0
    for sig_id, ticker, day, price_at_signal, f5, f10, f30 in cursor.fetchall():
        existing = {'fwd_return_5d': f5, 'fwd_return_10d': f10, 'fwd_return_30d': f30}
        cursor2 = conn.cursor()
        cursor2.execute("""
            SELECT date, close FROM price_bars
            WHERE ticker = ? AND date >= ? AND close IS NOT NULL
            ORDER BY date ASC
        """, (ticker, day))
        bars = cursor2.fetchall()
        if not bars:
            continue

        baseline = price_at_signal if price_at_signal and price_at_signal > 0 else bars[0][1]
        if not baseline or baseline <= 0:
            continue

        sets, params = [], []
        ten_day: Optional[tuple] = None
        for n, column in HORIZONS:
            if existing[column] is not None:
                continue
            if len(bars) <= n:               # bars[0] is the signal day itself
                continue
            date_n, close_n = bars[n]
            ret = ((close_n - baseline) / baseline) * 100
            sets.append(f"{column} = ?")
            params.append(ret)
            if n == 10:
                ten_day = (close_n, date_n, ret)

        if not sets:
            continue
        if ten_day:
            sets.extend(["outcome_price = ?", "outcome_date = ?", "outcome_pct = ?"])
            params.extend(ten_day)
        params.append(sig_id)
        conn.execute(f"UPDATE signals SET {', '.join(sets)} WHERE id = ?", params)
        updated += 1

    conn.commit()
    if updated:
        logger.info(f"Backfilled forward returns for {updated} signals")
    return updated
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_outcomes.py -v`
Expected: 4 PASS

- [ ] **Step 6: Wire into the pipeline and backfill history**

In `main.py`, import `from src.analysis.outcomes import update_signal_outcomes` and add directly after the Step 1c backfill block:

```python
        # Backfill signal outcomes now that bars are current (learning loop)
        try:
            n = update_signal_outcomes(db)
            logger.info(f"  [OK] Signal outcomes updated for {n} signals")
        except Exception as e:
            logger.error(f"  [ERROR] Outcome backfill failed: {e}")
```

Then run it once against history: `python main.py --skip-email` and verify:

```bash
python -c "
import sqlite3; c = sqlite3.connect('data/sentiment.db')
print(c.execute('select count(*), sum(fwd_return_10d is not null) from signals').fetchone())"
```

Expected: most of the 76+ historical signals now carry a 10-day forward return (April/May signals fill all horizons; today's stay partially NULL until bars accrue).

- [ ] **Step 7: Commit**

```bash
git add src/analysis/outcomes.py tests/test_outcomes.py src/database/models.py main.py
git commit -m "feat: backfill signal forward returns from bars (learning loop)"
```

---

### Task 11: Per-trigger edge report in the dashboard

**Files:**
- Modify: `src/database/queries.py` (new method at the end of `DatabaseQueries`)
- Modify: `src/reporters/dashboard_v2.py`
- Modify: `tests/test_dashboard.py` (or extend a queries test in `tests/test_database_models.py`)

**Interfaces:**
- Consumes: `signals.fwd_return_*` (Task 10).
- Produces: `DatabaseQueries.get_signal_edge_by_type() -> List[Dict]` with keys `signal_type, n, avg_fwd_5d, avg_fwd_10d, avg_fwd_30d, hit_rate_10d` (hit rate = share of signals with positive 10-day return; rows ordered by `n` desc).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_database_models.py`:

```python
def test_signal_edge_by_type(tmp_path):
    import sqlite3
    from src.database.models import Database
    from src.database.queries import DatabaseQueries
    db = Database(str(tmp_path / "t.db"))
    db.initialize()
    conn = db.connect()
    rows = [('A', 'insider_cluster', 5.0, 2.0), ('B', 'insider_cluster', -1.0, -3.0),
            ('C', 'velocity_spike', 8.0, 12.0)]
    for i, (t, st, f10, f30) in enumerate(rows):
        conn.execute("INSERT INTO signals (ticker, signal_type, conviction_score, created_at, "
                     "fwd_return_10d, fwd_return_30d) VALUES (?, ?, 50, ?, ?, ?)",
                     (t, st, f'2026-06-0{i+1} 12:00:00', f10, f30))
    conn.commit()
    edge = DatabaseQueries(conn).get_signal_edge_by_type()
    ic = next(r for r in edge if r['signal_type'] == 'insider_cluster')
    assert ic['n'] == 2 and ic['avg_fwd_10d'] == 2.0 and ic['hit_rate_10d'] == 50.0
    db.close()
```

Run: `pytest tests/test_database_models.py -k edge -v` — FAIL.

- [ ] **Step 2: Implement the query**

Append to `DatabaseQueries` in `src/database/queries.py`:

```python
    def get_signal_edge_by_type(self) -> List[Dict[str, Any]]:
        """
        @brief Per-trigger-type edge: average forward returns and 10d hit rate.
        @return Rows ordered by sample size, only signals with a 10d outcome.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT signal_type,
                   COUNT(*)                                        AS n,
                   ROUND(AVG(fwd_return_5d), 2)                    AS avg_fwd_5d,
                   ROUND(AVG(fwd_return_10d), 2)                   AS avg_fwd_10d,
                   ROUND(AVG(fwd_return_30d), 2)                   AS avg_fwd_30d,
                   ROUND(AVG(CASE WHEN fwd_return_10d > 0 THEN 100.0 ELSE 0.0 END), 1)
                                                                   AS hit_rate_10d
            FROM signals
            WHERE fwd_return_10d IS NOT NULL
            GROUP BY signal_type
            ORDER BY n DESC
        """)
        return [{'signal_type': r[0], 'n': r[1], 'avg_fwd_5d': r[2],
                 'avg_fwd_10d': r[3], 'avg_fwd_30d': r[4], 'hit_rate_10d': r[5]}
                for r in cursor.fetchall()]
```

Run: `pytest tests/test_database_models.py -k edge -v` — PASS.

- [ ] **Step 3: Surface it in the dashboard**

`ModernDashboardGenerator.generate(...)` already receives `db`. Add a section method to `src/reporters/dashboard_v2.py`:

```python
    def _render_signal_edge_section(self, edge_rows):
        """@brief HTML table: which trigger types actually make money."""
        if not edge_rows:
            return ""
        rows_html = ""
        for r in edge_rows:
            color = "#2e7d32" if (r['avg_fwd_10d'] or 0) > 0 else "#c62828"
            rows_html += (
                f"<tr><td>{r['signal_type']}</td><td>{r['n']}</td>"
                f"<td>{r['avg_fwd_5d'] if r['avg_fwd_5d'] is not None else '–'}%</td>"
                f"<td style='color:{color};font-weight:600'>{r['avg_fwd_10d']}%</td>"
                f"<td>{r['avg_fwd_30d'] if r['avg_fwd_30d'] is not None else '–'}%</td>"
                f"<td>{r['hit_rate_10d']}%</td></tr>")
        return f"""
        <div class="card">
          <h2>Signal Edge by Trigger Type</h2>
          <p class="muted">Forward returns measured from price_bars. Judge trigger types here before trusting their conviction weights.</p>
          <table>
            <tr><th>Trigger</th><th>N</th><th>+5d avg</th><th>+10d avg</th><th>+30d avg</th><th>10d hit rate</th></tr>
            {rows_html}
          </table>
        </div>"""
```

Inside `generate(...)`, where `db` is available and other sections are assembled (locate with `grep -n "paper_trading_stats" src/reporters/dashboard_v2.py` and insert alongside the paper-trading section), compute and append:

```python
        edge_rows = []
        if db is not None:
            try:
                from src.database.queries import DatabaseQueries
                edge_rows = DatabaseQueries(db.connect()).get_signal_edge_by_type()
            except Exception as e:
                logger.warning(f"Signal edge section skipped: {e}")
```

…and concatenate `self._render_signal_edge_section(edge_rows)` into the HTML in the same way neighboring sections are concatenated (match the surrounding pattern exactly — this file assembles sections as f-string blocks).

- [ ] **Step 4: Verify**

Run: `pytest tests/test_dashboard.py -v` — existing dashboard tests still pass.
Run: `python main.py --skip-email` and open the newest `reports/dashboard_*.html` — the "Signal Edge by Trigger Type" table renders with real rows (insider_cluster, velocity_spike, news_sentiment_bullish from historical signals).

- [ ] **Step 5: Commit**

```bash
git add src/database/queries.py src/reporters/dashboard_v2.py tests/test_database_models.py
git commit -m "feat: per-trigger signal edge table in dashboard"
```

---

### Task 12: Backtester shares the engine and the spine

**Files:**
- Modify: `src/analysis/backtester.py` (`simulate_trade` ~line 141, `_store_historical_prices` ~line 384)
- Modify: `tests/test_backtester.py`

**Interfaces:**
- Consumes: `walk_bars`/`ExitEvent` (Task 6); `price_bars` table.
- Produces: unchanged `simulate_trade(...) -> Optional[BacktestTrade]` signature; exits now identical to paper trading's rules. `_store_historical_prices` writes to `price_bars` (INSERT OR REPLACE), not `prices`.

- [ ] **Step 1: Read the current implementation**

Read `src/analysis/backtester.py:141-275` fully before editing: `simulate_trade` currently fetches snapshot prices from the `prices` table and applies its own day-by-day exit logic. Note exactly which fields the `BacktestTrade` dataclass is constructed with at the end of the method — those stay.

- [ ] **Step 2: Replace the price-path and exit logic inside `simulate_trade`**

Add at the top of the file: `from src.trading.engine import walk_bars`.

Keep everything from the signature through the `stop_loss`/`target_price` calculation. Replace the price-fetch query and the exit-decision loop with:

```python
        # Fetch daily bars from the market-date spine
        entry_day = entry_date.strftime('%Y-%m-%d')
        end_day = (entry_date + timedelta(days=self.hold_days + 14)).strftime('%Y-%m-%d')
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, open, high, low, close FROM price_bars
                WHERE ticker = ? AND date > ? AND date <= ?
                ORDER BY date ASC
            """, (ticker, entry_day, end_day))
            bars = [{'date': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4]}
                    for r in cursor.fetchall()]

        if not bars:
            return None

        exit_event = walk_bars(entry_day, entry_price, stop_loss, target_price,
                               self.hold_days, bars)
        if exit_event is None:
            # Ran out of bars before any exit rule fired - force-close at the last bar
            last = bars[-1]
            days_held = (datetime.strptime(last['date'], '%Y-%m-%d')
                         - datetime.strptime(entry_day, '%Y-%m-%d')).days
            exit_date_str, exit_price, exit_reason = last['date'], last['close'], 'time_limit'
        else:
            days_held = exit_event.days_held
            exit_date_str, exit_price, exit_reason = exit_event.date, exit_event.price, exit_event.reason
```

Then map `exit_date_str` / `exit_price` / `exit_reason` / `days_held` into the existing `BacktestTrade(...)` construction, converting `exit_date_str` with `datetime.strptime(exit_date_str, '%Y-%m-%d')` if the dataclass expects a datetime (check Step 1's reading). Delete the now-dead snapshot-price fetching and per-day comparison code this replaced.

- [ ] **Step 3: Redirect `_store_historical_prices` to `price_bars`**

Replace its INSERT with:

```python
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            for index, row in hist.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO price_bars (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ticker, index.strftime('%Y-%m-%d'), float(row['Open']), float(row['High']),
                      float(row['Low']), float(row['Close']), int(row['Volume'])))
            conn.commit()
```

(Preserve the method's existing signature and any surrounding logging.)

- [ ] **Step 4: Update backtester tests**

`tests/test_backtester.py` classes `TestSimulateTrade` / `TestGetHistoricalPrice` seed the `prices` table for trade simulation — re-seed them via `Database.insert_price_bars` with bar dicts instead, and update expected exits to the engine's rules (intrabar stop fills at the stop price; gap-open fills at the open; entry-day bar skipped). Expected values follow the rules table in Task 6 — recompute each assertion by hand against the seeded bars; do not copy old expected values.

Run: `pytest tests/test_backtester.py -v` until green.

- [ ] **Step 5: Full suite + commit**

Run: `pytest` — green.

```bash
git add src/analysis/backtester.py tests/test_backtester.py
git commit -m "refactor: backtester simulates trades via shared engine over price_bars"
```

---

### Task 13: Date-normalized velocity + run ledger

**Files:**
- Modify: `src/metrics/velocity.py` (`VelocityCalculator.calculate_ticker_velocity`, the vel_24h block ~line 183)
- Modify: `src/database/models.py` (`pipeline_runs` DDL + two methods)
- Modify: `main.py` (`run_pipeline` start/end)
- Modify: `tests/test_velocity.py`; extend `tests/test_price_bars.py`

**Interfaces:**
- Consumes: `db.get_mention_history(ticker, days)` → `List[(datetime, int)]` (existing).
- Produces: vel_24h becomes a **per-day rate** between the two most recent distinct observation dates; the returned metrics dict gains `observation_gap_days` (int; not persisted — `insert_velocity` reads only its known keys). `Database.start_pipeline_run() -> int`, `Database.finish_pipeline_run(run_id: int, status: str, notes: Optional[str] = None)`.

- [ ] **Step 1: Write the failing velocity test**

Add to `tests/test_velocity.py` (follow the file's existing MockDatabase pattern — it already fabricates `get_mention_history` returns):

```python
def test_vel_24h_normalized_per_day():
    """A 3-day gap with +30% total change reads as +10%/day, not 0 and not +30."""
    from datetime import datetime, timedelta
    from src.metrics.velocity import VelocityCalculator

    class GapDB:
        def get_mention_history(self, ticker, days=7):
            now = datetime.now()
            return [(now - timedelta(days=3), 100), (now, 130)]
        def get_sentiment_history(self, ticker, days=7):
            return []
        def get_price_history(self, ticker, days=7):
            return []

    calc = VelocityCalculator(GapDB())
    result = calc.calculate_ticker_velocity('GAP')
    assert abs(result['mention_velocity_24h'] - 10.0) < 0.01
    assert result['observation_gap_days'] == 3
```

Run: `pytest tests/test_velocity.py -k normalized -v` — FAIL (current code returns 30.0 or 0.0 and no gap key).

- [ ] **Step 2: Replace the vel_24h block**

In `calculate_ticker_velocity`, replace the block from `vel_24h = 0.0` through the `if prev_mentions:` assignment with:

```python
            # Date-normalized 24h velocity: compare the two most recent distinct
            # observation days as a per-day rate, so irregular run cadence
            # degrades gracefully instead of reading zero.
            vel_24h = 0.0
            observation_gap_days = 0
            by_day = {}
            for ts, count in mention_history:
                by_day[ts.date()] = count  # last observation of each day wins
            days_seen = sorted(by_day)
            if len(days_seen) >= 2:
                observation_gap_days = max(1, (days_seen[-1] - days_seen[-2]).days)
                total_pct = mention_velocity_pct(by_day[days_seen[-1]], by_day[days_seen[-2]])
                vel_24h = total_pct / observation_gap_days
                if observation_gap_days > 3:
                    logger.warning(f"{ticker}: velocity computed over a "
                                   f"{observation_gap_days}-day gap - treat as stale")
```

Add `'observation_gap_days': observation_gap_days,` to the returned dict (and `'observation_gap_days': 0,` to the exception-path dict).

Run: `pytest tests/test_velocity.py -v` — all PASS (if an existing test asserted the old 24h-cutoff behavior, update it to the per-day-rate rule; that behavior is F1).

- [ ] **Step 3: Add the run ledger**

In `models.py` `initialize()` (after the outcome-column migrations):

```python
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT DEFAULT 'running',
                notes TEXT
            )
        """)
```

Methods (after `get_signal_and_trade_tickers`):

```python
    def start_pipeline_run(self) -> int:
        """@brief Record a pipeline run start; returns the run id."""
        cursor = self.connect().cursor()
        cursor.execute("INSERT INTO pipeline_runs (started_at) VALUES (?)",
                       (datetime.now().isoformat(),))
        self.connect().commit()
        return cursor.lastrowid

    def finish_pipeline_run(self, run_id: int, status: str, notes: Optional[str] = None):
        """@brief Close out a pipeline run record."""
        self.connect().execute(
            "UPDATE pipeline_runs SET finished_at = ?, status = ?, notes = ? WHERE id = ?",
            (datetime.now().isoformat(), status, notes, run_id))
        self.connect().commit()
```

Test (append to `tests/test_price_bars.py`):

```python
def test_pipeline_run_ledger(db):
    run_id = db.start_pipeline_run()
    db.finish_pipeline_run(run_id, 'ok', 'signals=4')
    row = db.connect().execute(
        "SELECT status, notes, finished_at FROM pipeline_runs WHERE id=?", (run_id,)).fetchone()
    assert row[0] == 'ok' and row[1] == 'signals=4' and row[2] is not None
```

- [ ] **Step 4: Wire the ledger into `run_pipeline`**

In `main.py` `run_pipeline`, after `db.initialize()`:

```python
    run_id = db.start_pipeline_run()
```

Change the `try:`/`finally:` at the end of `run_pipeline` to record status:

```python
        return signals
    except Exception as e:
        db.finish_pipeline_run(run_id, 'error', str(e)[:500])
        raise
    finally:
        if db.connect().execute("SELECT status FROM pipeline_runs WHERE id=?", (run_id,)).fetchone()[0] == 'running':
            db.finish_pipeline_run(run_id, 'ok', f"signals={len(signals) if 'signals' in dir() else 0}")
        db.close()
```

Simpler equivalent is acceptable: set a `run_status` variable and call `finish_pipeline_run` once in `finally` — implementer's choice, as long as both ok and error paths are recorded and `db.close()` still always runs.

- [ ] **Step 5: Full suite + commit**

Run: `pytest` — green.

```bash
git add src/metrics/velocity.py src/database/models.py main.py tests/test_velocity.py tests/test_price_bars.py
git commit -m "feat: date-normalized velocity and pipeline run ledger"
```

---

### Task 14: Recalibrate config, schedule daily runs, docs, close-out

**Files:**
- Modify: `config/config.example.yaml` (committed) and `config/config.yaml` (live, gitignored — same edits, not committed)
- Create: `utils/register_daily_task.ps1`
- Modify: `README.md`, `CLAUDE.md` (project-level)

- [ ] **Step 1: Restore honest thresholds**

In both config files, change under `thresholds:`:

```yaml
thresholds:
  velocity_spike:
    mention_vel_24h_min: 20        # per-day rate since Task 13
    composite_score_min: 40        # was 10
  insider_cluster:
    min_insiders: 2                # was 1
    lookback_days: 14              # was 30
    min_value_total: 100000        # was 10000
  minimum_conviction: 40           # was 15
```

Verify `paper_trading.min_conviction: 25` still holds (paper trading may run looser than reporting; leave it — the edge table will judge it).

- [ ] **Step 2: Task Scheduler registration script**

```powershell
# utils/register_daily_task.ps1
# Registers a daily 6:30 PM weekday run of the stock-trader pipeline.
# Run once from an elevated or user-level PowerShell:
#   pwsh -File utils/register_daily_task.ps1

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $python `
    -Argument "main.py --skip-email" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 6:30PM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "StockTrader-DailyPipeline" -Action $action `
    -Trigger $trigger -Settings $settings -Description "stock-trader daily signal pipeline" -Force
Write-Host "Registered task 'StockTrader-DailyPipeline' (weekdays 6:30 PM). Remove --skip-email in Task Scheduler if the email report is wanted."
```

Register it: `pwsh -File utils/register_daily_task.ps1`, then verify with `Get-ScheduledTask -TaskName StockTrader-DailyPipeline`.

- [ ] **Step 3: Update docs**

- `README.md`: add a "Market-date spine" paragraph — daily bars in `price_bars`, bar-replay paper trading, outcome tracking, the revalidation utility, and the scheduled task.
- Project `CLAUDE.md`: under Key Files add `src/trading/engine.py` (shared exit engine) and `src/collectors/bars_backfill.py`; under Conventions add "All time-series joins key on `price_bars.date` (market date), never `collected_at`"; **delete the malformed TODO block** (it duplicates the Tech Stack/Conventions lines as fake checkboxes) and replace with a TODO pointing at Phase 4 of the spec (empirical conviction re-weighting once ~50 outcomes per trigger type exist).

- [ ] **Step 4: Full verification pass**

```bash
pytest
python main.py --skip-email
```

Expected: full suite green; log shows lock acquired, Step 1c bars backfilled, outcomes updated, positions evaluated against bars, signals ≥ conviction 40 only, dashboard written with the edge table. Then run the graph rebuild:

```bash
python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

(Skip without failing if graphify isn't installed in this environment.)

- [ ] **Step 5: Commit**

```bash
git add config/config.example.yaml utils/register_daily_task.ps1 README.md CLAUDE.md
git commit -m "chore: honest thresholds, daily scheduled run, market-date-spine docs"
```

---

## Verification checklist (end state)

- [ ] `pytest` green; count strictly above the 238-passed baseline.
- [ ] `price_bars` holds ≥120 days of daily bars for every ticker in `signals`/`paper_trades`.
- [ ] `select count(*) from paper_trades where status='void_duplicate'` ≈ 11; zero open duplicate tickers.
- [ ] Trade 16 (UP) shows a June stop-loss exit near $7.98 with its original −42% exit preserved in `notes`.
- [ ] `select count(*) from signals where fwd_return_10d is not null` covers all signals older than ~2 weeks.
- [ ] Dashboard renders "Signal Edge by Trigger Type" with real rows.
- [ ] Two simultaneous `python main.py` invocations: the second exits with code 2 immediately.
- [ ] `Get-ScheduledTask StockTrader-DailyPipeline` exists.
