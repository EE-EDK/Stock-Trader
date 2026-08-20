"""
@file test_paper_trading.py
@brief Unit tests for paper trading system
@details Tests for PaperTradingManager and all paper trading functionality
"""

import pytest
import sqlite3
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
import tempfile
import os

from src.trading.paper_trading import PaperTradingManager


class TestPaperTradingInit:
    """Test cases for PaperTradingManager initialization"""

    def test_init_enabled(self):
        """Test initialization with paper trading enabled"""
        config = {
            'paper_trading': {
                'enabled': True,
                'min_conviction': 60,
                'position_size': 1000,
                'max_open_positions': 10,
                'hold_days': 30,
                'stop_loss_pct': -10,
                'take_profit_pct': 20
            }
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name

        try:
            manager = PaperTradingManager(db_path, config)

            assert manager.enabled is True
            assert manager.min_conviction == 60
            assert manager.base_position_size == 1000
            assert manager.max_open_positions == 10
            assert manager.hold_days == 30
            assert manager.stop_loss_pct == -10
            assert manager.take_profit_pct == 20
        finally:
            os.unlink(db_path)

    def test_init_disabled(self):
        """Test initialization with paper trading disabled"""
        config = {
            'paper_trading': {
                'enabled': False
            }
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name

        try:
            manager = PaperTradingManager(db_path, config)
            assert manager.enabled is False
        finally:
            os.unlink(db_path)

    def test_init_defaults(self):
        """Test initialization with default values"""
        config = {
            'paper_trading': {
                'enabled': True
            }
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name

        try:
            manager = PaperTradingManager(db_path, config)

            # Check defaults
            assert manager.min_conviction == 60
            assert manager.base_position_size == 1000
            assert manager.max_open_positions == 10
            assert manager.hold_days == 30
            assert manager.stop_loss_pct == -10
            assert manager.take_profit_pct == 20
        finally:
            os.unlink(db_path)

    def test_tables_created(self):
        """Test that database tables are created on init"""
        config = {
            'paper_trading': {
                'enabled': True
            }
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
            db_path = tmp.name

        try:
            # Create schema file
            os.makedirs('src/database', exist_ok=True)
            if not os.path.exists('src/database/paper_trading_schema.sql'):
                with open('src/database/paper_trading_schema.sql', 'w') as f:
                    f.write("""
                        CREATE TABLE IF NOT EXISTS paper_trades (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ticker TEXT NOT NULL,
                            entry_date DATETIME NOT NULL,
                            entry_price REAL NOT NULL,
                            shares INTEGER NOT NULL,
                            conviction INTEGER NOT NULL,
                            signal_types TEXT NOT NULL,
                            position_size REAL NOT NULL,
                            stop_loss REAL,
                            target_price REAL,
                            signal_id INTEGER,
                            exit_date DATETIME,
                            exit_price REAL,
                            exit_reason TEXT,
                            return_pct REAL,
                            profit_loss REAL,
                            days_held INTEGER,
                            status TEXT DEFAULT 'open',
                            notes TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(ticker, entry_date)
                        );

                        CREATE TABLE IF NOT EXISTS paper_trade_snapshots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            trade_id INTEGER NOT NULL,
                            snapshot_date DATETIME NOT NULL,
                            current_price REAL NOT NULL,
                            unrealized_pnl REAL,
                            unrealized_pct REAL,
                            FOREIGN KEY (trade_id) REFERENCES paper_trades(id),
                            UNIQUE(trade_id, snapshot_date)
                        );
                    """)

            manager = PaperTradingManager(db_path, config)

            # Check tables exist
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            assert 'paper_trades' in tables
            assert 'paper_trade_snapshots' in tables
        finally:
            os.unlink(db_path)


class TestPositionSizeCalculation:
    """Test cases for conviction-weighted position sizing"""

    def setup_method(self):
        """Setup test manager"""
        config = {
            'paper_trading': {
                'enabled': True,
                'position_size': 1000
            }
        }

        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name
        self.tmp_file.close()
        self.manager = PaperTradingManager(self.db_path, config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_conviction_50(self):
        """Test position size at conviction 50 (minimum)"""
        size = self.manager.calculate_position_size(50)
        assert size == 1000  # 1.0x base

    def test_conviction_60(self):
        """Test position size at conviction 60"""
        size = self.manager.calculate_position_size(60)
        assert size == 1200  # 1.2x base

    def test_conviction_75(self):
        """Test position size at conviction 75"""
        size = self.manager.calculate_position_size(75)
        assert size == 1500  # 1.5x base

    def test_conviction_100(self):
        """Test position size at conviction 100 (maximum)"""
        size = self.manager.calculate_position_size(100)
        assert size == 2000  # 2.0x base

    def test_linear_scaling(self):
        """Test that scaling is linear"""
        size_60 = self.manager.calculate_position_size(60)
        size_70 = self.manager.calculate_position_size(70)
        size_80 = self.manager.calculate_position_size(80)

        # Differences should be equal (linear)
        diff1 = size_70 - size_60
        diff2 = size_80 - size_70
        assert abs(diff1 - diff2) < 0.01


class TestCreatePaperTrade:
    """Test cases for creating paper trades"""

    def setup_method(self):
        """Setup test manager"""
        config = {
            'paper_trading': {
                'enabled': True,
                'min_conviction': 60,
                'position_size': 1000,
                'max_open_positions': 10,
                'stop_loss_pct': -10,
                'take_profit_pct': 20
            }
        }

        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name
        self.tmp_file.close()

        # Create schema manually for tests
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                entry_date DATETIME NOT NULL,
                entry_price REAL NOT NULL,
                shares INTEGER NOT NULL,
                conviction INTEGER NOT NULL,
                signal_types TEXT NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                target_price REAL,
                signal_id INTEGER,
                exit_date DATETIME,
                exit_price REAL,
                exit_reason TEXT,
                return_pct REAL,
                profit_loss REAL,
                days_held INTEGER,
                status TEXT DEFAULT 'open',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, entry_date)
            );

            CREATE TABLE IF NOT EXISTS paper_trade_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                snapshot_date DATETIME NOT NULL,
                current_price REAL NOT NULL,
                unrealized_pnl REAL,
                unrealized_pct REAL,
                FOREIGN KEY (trade_id) REFERENCES paper_trades(id),
                UNIQUE(trade_id, snapshot_date)
            );
        """)
        conn.commit()
        conn.close()

        self.manager = PaperTradingManager(self.db_path, config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_create_trade_success(self):
        """Test successful trade creation"""
        entry_date = datetime.now()
        trade_id = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=150.0,
            conviction=80,
            signal_types=['velocity_spike', 'insider_buy'],
            entry_date=entry_date
        )

        assert trade_id is not None

        # Verify trade in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM paper_trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[1] == 'AAPL'  # ticker
        assert row[3] == 150.0  # entry_price
        assert row[5] == 80  # conviction

    def test_create_trade_calculates_shares(self):
        """Test that shares are calculated correctly"""
        trade_id = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=150.0,
            conviction=75,  # 1.5x base = $1500
            signal_types=['velocity_spike'],
            entry_date=datetime.now()
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT shares, position_size FROM paper_trades WHERE id = ?", (trade_id,))
        shares, position_size = cursor.fetchone()
        conn.close()

        # Position size should be $1500 (1.5x $1000)
        # Shares should be 10 ($1500 / $150)
        assert shares == 10
        assert abs(position_size - 1500.0) < 0.01

    def test_create_trade_calculates_exit_prices(self):
        """Test that stop loss and target prices are calculated"""
        trade_id = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=100.0,
            conviction=60,
            signal_types=['velocity_spike'],
            entry_date=datetime.now()
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stop_loss, target_price FROM paper_trades WHERE id = ?", (trade_id,))
        stop_loss, target_price = cursor.fetchone()
        conn.close()

        # Stop loss: 100 * (1 + (-10/100)) = 90
        # Target: 100 * (1 + (20/100)) = 120
        assert abs(stop_loss - 90.0) < 0.01
        assert abs(target_price - 120.0) < 0.01

    def test_create_trade_idempotent(self):
        """Test that duplicate trades are skipped (idempotent)"""
        entry_date = datetime.now()

        # Create first trade
        trade_id_1 = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=150.0,
            conviction=80,
            signal_types=['velocity_spike'],
            entry_date=entry_date
        )

        # Try to create duplicate
        trade_id_2 = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=150.0,
            conviction=80,
            signal_types=['velocity_spike'],
            entry_date=entry_date
        )

        assert trade_id_1 is not None
        assert trade_id_2 is None  # Should be skipped

        # Verify only one trade in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM paper_trades WHERE ticker = 'AAPL'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_create_trade_respects_max_positions(self):
        """Test that max open positions limit is enforced"""
        # Create 10 positions (the max)
        for i in range(10):
            self.manager.create_paper_trade(
                ticker=f'TICK{i}',
                entry_price=100.0,
                conviction=80,
                signal_types=['test'],
                entry_date=datetime.now() + timedelta(seconds=i)
            )

        # Try to create 11th position
        trade_id = self.manager.create_paper_trade(
            ticker='TICK11',
            entry_price=100.0,
            conviction=80,
            signal_types=['test'],
            entry_date=datetime.now() + timedelta(seconds=11)
        )

        assert trade_id is None  # Should be rejected

    def test_create_trade_disabled(self):
        """Test that trades are not created when disabled"""
        config = {'paper_trading': {'enabled': False}}
        manager = PaperTradingManager(self.db_path, config)

        trade_id = manager.create_paper_trade(
            ticker='AAPL',
            entry_price=150.0,
            conviction=80,
            signal_types=['test'],
            entry_date=datetime.now()
        )

        assert trade_id is None


class TestUpdatePositionsFromBars:
    """Test cases for bar-replay position updates via the shared exit engine"""

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
        db, mgr = self._make(tmp_path)
        mgr.create_paper_trade('XYZ', 10.0, 50, ['insider_cluster'],
                               datetime(2026, 6, 1, 12, 0))
        db.insert_price_bars([
            {'ticker': 'XYZ', 'date': '2026-06-02', 'open': 9.8, 'high': 9.9, 'low': 8.5, 'close': 8.8, 'volume': 1},
            {'ticker': 'XYZ', 'date': '2026-06-03', 'open': 8.8, 'high': 9.0, 'low': 8.0, 'close': 8.2, 'volume': 1},
        ])
        mgr.update_positions_from_bars(db, datetime(2026, 8, 19))
        import contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            row = conn.execute("SELECT status, exit_reason, exit_price, exit_date, days_held "
                               "FROM paper_trades WHERE ticker='XYZ'").fetchone()
        assert row[0] == 'closed' and row[1] == 'stop_loss'
        assert row[2] == 9.0                      # stop price, not the months-later snapshot
        assert row[3].startswith('2026-06-02')    # the bar that crossed it
        assert row[4] == 1
        db.close()

    def test_open_position_records_progress(self, tmp_path):
        db, mgr = self._make(tmp_path)
        mgr.create_paper_trade('ABC', 10.0, 50, ['insider_cluster'],
                               datetime(2026, 8, 10, 12, 0))
        db.insert_price_bars([
            {'ticker': 'ABC', 'date': '2026-08-11', 'open': 10.1, 'high': 10.5, 'low': 10.0, 'close': 10.4, 'volume': 1},
        ])
        mgr.update_positions_from_bars(db, datetime(2026, 8, 19))
        import contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            status, last_eval = conn.execute(
                "SELECT status, last_evaluated_date FROM paper_trades WHERE ticker='ABC'").fetchone()
            snap = conn.execute("SELECT current_price FROM paper_trade_snapshots").fetchone()
        assert status == 'open' and last_eval == '2026-08-11'
        assert snap[0] == 10.4
        db.close()

    def test_no_bars_leaves_position_untouched(self, tmp_path):
        db, mgr = self._make(tmp_path)
        mgr.create_paper_trade('QQQ', 10.0, 50, ['insider_cluster'],
                               datetime(2026, 8, 10, 12, 0))
        mgr.update_positions_from_bars(db, datetime(2026, 8, 19))
        import contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            status = conn.execute("SELECT status FROM paper_trades WHERE ticker='QQQ'").fetchone()[0]
        assert status == 'open'
        db.close()

    def test_update_disabled(self, tmp_path):
        db, _ = self._make(tmp_path)
        config = {'paper_trading': {'enabled': False}}
        manager = PaperTradingManager(db.db_path, config)
        # Should not raise error
        manager.update_positions_from_bars(db, datetime.now())
        db.close()


class TestBackfillFromSignals:
    """Test cases for backfilling trades from historical signals"""

    def setup_method(self):
        """Setup test manager and database"""
        config = {
            'paper_trading': {
                'enabled': True,
                'min_conviction': 60
            }
        }

        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name
        self.tmp_file.close()

        # Create schema
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                entry_date DATETIME NOT NULL,
                entry_price REAL NOT NULL,
                shares INTEGER NOT NULL,
                conviction INTEGER NOT NULL,
                signal_types TEXT NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                target_price REAL,
                signal_id INTEGER,
                exit_date DATETIME,
                exit_price REAL,
                exit_reason TEXT,
                return_pct REAL,
                profit_loss REAL,
                days_held INTEGER,
                status TEXT DEFAULT 'open',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, entry_date)
            );

            CREATE TABLE IF NOT EXISTS signals (
                ticker TEXT,
                conviction_score REAL,
                triggers TEXT,
                created_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS price_bars (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume INTEGER,
                source TEXT DEFAULT 'yfinance',
                PRIMARY KEY (ticker, date)
            );
        """)
        conn.commit()
        conn.close()

        self.manager = PaperTradingManager(self.db_path, config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_backfill_creates_trades(self):
        """Test that backfill creates trades from signals"""
        # Add test signal
        signal_date = datetime.now() - timedelta(days=10)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (ticker, conviction_score, triggers, created_at)
            VALUES (?, ?, ?, ?)
        """, ('AAPL', 80, json.dumps(['velocity_spike']), signal_date.isoformat()))

        cursor.execute("""
            INSERT INTO price_bars (ticker, date, close)
            VALUES (?, ?, ?)
        """, ('AAPL', signal_date.strftime('%Y-%m-%d'), 150.0))

        conn.commit()
        conn.close()

        # Run backfill
        self.manager.backfill_from_signals(days=30)

        # Check trade was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM paper_trades WHERE ticker = 'AAPL'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_backfill_respects_conviction_threshold(self):
        """Test that backfill only creates trades above conviction threshold"""
        # Add signals with different convictions
        signal_date = datetime.now() - timedelta(days=10)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Below threshold (50 < 60)
        cursor.execute("""
            INSERT INTO signals (ticker, conviction_score, triggers, created_at)
            VALUES (?, ?, ?, ?)
        """, ('LOW', 50, json.dumps(['test']), signal_date.isoformat()))

        # Above threshold (80 > 60)
        cursor.execute("""
            INSERT INTO signals (ticker, conviction_score, triggers, created_at)
            VALUES (?, ?, ?, ?)
        """, ('HIGH', 80, json.dumps(['test']), signal_date.isoformat()))

        # Add prices
        cursor.execute("INSERT INTO price_bars (ticker, date, close) VALUES (?, ?, ?)", ('LOW', signal_date.strftime('%Y-%m-%d'), 100.0))
        cursor.execute("INSERT INTO price_bars (ticker, date, close) VALUES (?, ?, ?)", ('HIGH', signal_date.strftime('%Y-%m-%d'), 100.0))

        conn.commit()
        conn.close()

        # Run backfill
        self.manager.backfill_from_signals(days=30)

        # Check only HIGH was created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM paper_trades")
        tickers = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert 'HIGH' in tickers
        assert 'LOW' not in tickers

    def test_backfill_idempotent(self):
        """Test that backfill can be run multiple times safely"""
        # Add test signal
        signal_date = datetime.now() - timedelta(days=10)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signals (ticker, conviction_score, triggers, created_at)
            VALUES (?, ?, ?, ?)
        """, ('AAPL', 80, json.dumps(['test']), signal_date.isoformat()))

        cursor.execute("""
            INSERT INTO price_bars (ticker, date, close)
            VALUES (?, ?, ?)
        """, ('AAPL', signal_date.strftime('%Y-%m-%d'), 150.0))

        conn.commit()
        conn.close()

        # Run backfill twice
        self.manager.backfill_from_signals(days=30)
        self.manager.backfill_from_signals(days=30)

        # Should only have one trade
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM paper_trades WHERE ticker = 'AAPL'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1


class TestPerformanceSummary:
    """Test cases for performance summary methods"""

    def setup_method(self):
        """Setup test manager with sample trades"""
        config = {
            'paper_trading': {
                'enabled': True
            }
        }

        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name
        self.tmp_file.close()

        # Create schema
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                entry_date DATETIME NOT NULL,
                entry_price REAL NOT NULL,
                shares INTEGER NOT NULL,
                conviction INTEGER NOT NULL,
                signal_types TEXT NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                target_price REAL,
                signal_id INTEGER,
                exit_date DATETIME,
                exit_price REAL,
                exit_reason TEXT,
                return_pct REAL,
                profit_loss REAL,
                days_held INTEGER,
                status TEXT DEFAULT 'open',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, entry_date)
            );

            CREATE TABLE IF NOT EXISTS paper_trade_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,
                snapshot_date DATETIME NOT NULL,
                current_price REAL NOT NULL,
                unrealized_pnl REAL,
                unrealized_pct REAL,
                FOREIGN KEY (trade_id) REFERENCES paper_trades(id),
                UNIQUE(trade_id, snapshot_date)
            );
        """)
        conn.commit()
        conn.close()

        self.manager = PaperTradingManager(self.db_path, config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_performance_summary_structure(self):
        """Test that performance summary has correct structure"""
        summary = self.manager.get_performance_summary()

        assert 'closed_trades' in summary
        assert 'open_positions' in summary

        assert 'count' in summary['closed_trades']
        assert 'win_rate' in summary['closed_trades']
        assert 'avg_return_pct' in summary['closed_trades']
        assert 'total_pnl' in summary['closed_trades']

        assert 'count' in summary['open_positions']
        assert 'total_deployed' in summary['open_positions']

    def test_performance_summary_with_closed_trades(self):
        """Test performance summary with closed trades"""
        # Add closed trades manually
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Winning trade
        cursor.execute("""
            INSERT INTO paper_trades
            (ticker, entry_date, entry_price, shares, conviction, signal_types,
             position_size, exit_price, profit_loss, return_pct, days_held, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('AAPL', datetime.now().isoformat(), 100.0, 10, 80, '[]',
              1000.0, 120.0, 200.0, 20.0, 10, 'closed'))

        # Losing trade
        cursor.execute("""
            INSERT INTO paper_trades
            (ticker, entry_date, entry_price, shares, conviction, signal_types,
             position_size, exit_price, profit_loss, return_pct, days_held, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('TSLA', datetime.now().isoformat(), 200.0, 5, 80, '[]',
              1000.0, 180.0, -100.0, -10.0, 15, 'closed'))

        conn.commit()
        conn.close()

        summary = self.manager.get_performance_summary()

        assert summary['closed_trades']['count'] == 2
        assert summary['closed_trades']['win_rate'] == 50.0  # 1 out of 2
        assert summary['closed_trades']['total_pnl'] == 100.0  # 200 - 100

    def test_get_open_positions(self):
        """Test getting open positions"""
        # Create a trade
        trade_id = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=100.0,
            conviction=80,
            signal_types=['test'],
            entry_date=datetime.now()
        )

        positions = self.manager.get_open_positions()

        assert len(positions) == 1
        assert positions[0]['ticker'] == 'AAPL'
        assert positions[0]['entry_price'] == 100.0

    def test_get_recent_closes(self):
        """Test getting recently closed positions"""
        # Add a recently closed trade
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        exit_date = datetime.now() - timedelta(days=2)
        cursor.execute("""
            INSERT INTO paper_trades
            (ticker, entry_date, entry_price, shares, conviction, signal_types,
             position_size, exit_date, exit_price, profit_loss, return_pct,
             days_held, exit_reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('AAPL', (datetime.now() - timedelta(days=12)).isoformat(), 100.0, 10, 80, '[]',
              1000.0, exit_date.isoformat(), 120.0, 200.0, 20.0, 10, 'take_profit', 'closed'))

        conn.commit()
        conn.close()

        recent = self.manager.get_recent_closes(days=7)

        assert len(recent) == 1
        assert recent[0]['ticker'] == 'AAPL'
        assert recent[0]['exit_reason'] == 'take_profit'
        assert recent[0]['profit_loss'] == 200.0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Setup test manager"""
        config = {
            'paper_trading': {
                'enabled': True
            }
        }

        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name
        self.tmp_file.close()

        # Create minimal schema
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                entry_date DATETIME,
                entry_price REAL,
                shares INTEGER,
                conviction INTEGER,
                signal_types TEXT,
                position_size REAL,
                stop_loss REAL,
                target_price REAL,
                signal_id INTEGER,
                status TEXT DEFAULT 'open'
            );
        """)
        conn.commit()
        conn.close()

        self.manager = PaperTradingManager(self.db_path, config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_zero_entry_price(self):
        """Test handling of zero entry price"""
        # Should handle gracefully or raise appropriate error
        try:
            trade_id = self.manager.create_paper_trade(
                ticker='INVALID',
                entry_price=0.0,
                conviction=80,
                signal_types=['test'],
                entry_date=datetime.now()
            )
            # If it succeeds, shares should be 0 or None
            if trade_id:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT shares FROM paper_trades WHERE id = ?", (trade_id,))
                shares = cursor.fetchone()[0]
                conn.close()
                # Shares should be very large or handled specially
                assert shares is not None
        except Exception:
            # It's OK to raise an error for invalid price
            pass

    def test_negative_conviction(self):
        """Test handling of negative conviction"""
        # Should still calculate position size (though unusual)
        size = self.manager.calculate_position_size(-10)
        assert size >= 0  # Should not return negative size

    def test_very_high_conviction(self):
        """Test handling of conviction > 100"""
        size = self.manager.calculate_position_size(150)
        # Should still work, just give a very high multiplier
        assert size > self.manager.base_position_size * 2

    def test_empty_signal_types(self):
        """Test creating trade with empty signal types list"""
        trade_id = self.manager.create_paper_trade(
            ticker='AAPL',
            entry_price=100.0,
            conviction=80,
            signal_types=[],
            entry_date=datetime.now()
        )

        assert trade_id is not None


class TestBookHygiene:
    """One open position per ticker, zero-share guard, signal_id linkage"""

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
        db, mgr = self._mgr(tmp_path)
        t1 = mgr.create_paper_trade('DUP', 10.0, 50, ['insider_cluster'], datetime(2026, 8, 1))
        t2 = mgr.create_paper_trade('DUP', 10.5, 50, ['insider_cluster'],
                                    datetime(2026, 8, 1) + timedelta(minutes=5))
        assert t1 is not None and t2 is None
        db.close()

    def test_zero_share_trade_rejected(self, tmp_path):
        db, mgr = self._mgr(tmp_path)
        # conviction 25 -> $500 position; price $679 -> 0 shares (the VOO case)
        assert mgr.create_paper_trade('VOO', 679.46, 25, ['news_sentiment_bullish'],
                                      datetime(2026, 8, 1)) is None
        db.close()

    def test_signal_id_is_stored(self, tmp_path):
        db, mgr = self._mgr(tmp_path)
        tid = mgr.create_paper_trade('LNK', 10.0, 50, ['insider_cluster'],
                                     datetime(2026, 8, 1), signal_id=77)
        import contextlib
        with contextlib.closing(sqlite3.connect(mgr.db_path)) as conn:
            sid = conn.execute("SELECT signal_id FROM paper_trades WHERE id=?", (tid,)).fetchone()[0]
        assert sid == 77
        db.close()
