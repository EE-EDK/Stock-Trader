"""
@file test_backtester.py
@brief Unit tests for backtesting module
@details Tests for Backtester class and all backtesting functionality
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from src.analysis.backtester import Backtester, BacktestTrade, BacktestResults


class TestBacktesterInit:
    """Test cases for backtester initialization"""

    def test_init_with_config(self):
        """Test initialization with full config"""
        config = {
            'backtesting': {
                'initial_capital': 20000,
                'position_size': 2000,
                'max_positions': 5,
                'stop_loss_pct': -15,
                'take_profit_pct': 25,
                'hold_days': 45,
                'min_conviction': 70,
                'conviction_weighted': True
            }
        }

        backtester = Backtester(db_path="test.db", config=config)

        assert backtester.initial_capital == 20000
        assert backtester.position_size == 2000
        assert backtester.max_positions == 5
        assert backtester.stop_loss_pct == -15
        assert backtester.take_profit_pct == 25
        assert backtester.hold_days == 45
        assert backtester.min_conviction == 70
        assert backtester.use_conviction_weighted is True

    def test_init_with_defaults(self):
        """Test initialization with default values"""
        config = {}
        backtester = Backtester(db_path="test.db", config=config)

        # Should use defaults
        assert backtester.initial_capital == 10000
        assert backtester.position_size == 1000
        assert backtester.max_positions == 10
        assert backtester.stop_loss_pct == -10
        assert backtester.take_profit_pct == 20
        assert backtester.hold_days == 30
        assert backtester.min_conviction == 60


class TestPositionSizing:
    """Test cases for position sizing calculations"""

    def setup_method(self):
        """Setup test backtester"""
        self.config = {'backtesting': {'conviction_weighted': True, 'position_size': 1000}}
        self.backtester = Backtester(db_path="test.db", config=self.config)

    def test_conviction_50(self):
        """Test position size at conviction 50 (minimum)"""
        size = self.backtester.calculate_position_size(50)
        assert size == 1000  # 1.0x base

    def test_conviction_75(self):
        """Test position size at conviction 75"""
        size = self.backtester.calculate_position_size(75)
        assert size == 1500  # 1.5x base

    def test_conviction_100(self):
        """Test position size at conviction 100 (maximum)"""
        size = self.backtester.calculate_position_size(100)
        assert size == 2000  # 2.0x base

    def test_fixed_sizing(self):
        """Test fixed position sizing when conviction weighting disabled"""
        config = {'backtesting': {'conviction_weighted': False, 'position_size': 1000}}
        backtester = Backtester(db_path="test.db", config=config)

        # All convictions should return same size
        assert backtester.calculate_position_size(50) == 1000
        assert backtester.calculate_position_size(75) == 1000
        assert backtester.calculate_position_size(100) == 1000


class TestGetHistoricalPrice:
    """Test cases for retrieving historical prices"""

    def setup_method(self):
        """Setup test database and backtester"""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name

        # Create test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE prices (
                ticker TEXT,
                price REAL,
                collected_at DATETIME
            )
        """)

        # Insert test prices
        test_date = datetime(2025, 1, 15)
        cursor.execute("INSERT INTO prices VALUES (?, ?, ?)",
                      ('AAPL', 150.0, test_date))
        cursor.execute("INSERT INTO prices VALUES (?, ?, ?)",
                      ('AAPL', 155.0, test_date + timedelta(days=1)))

        conn.commit()
        conn.close()

        self.config = {}
        self.backtester = Backtester(db_path=self.db_path, config=self.config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_get_price_exact_date(self):
        """Test getting price on exact date"""
        test_date = datetime(2025, 1, 15)
        price = self.backtester.get_historical_price('AAPL', test_date)

        assert price == 150.0

    def test_get_price_with_offset(self):
        """Test getting price with offset days"""
        test_date = datetime(2025, 1, 15)
        price = self.backtester.get_historical_price('AAPL', test_date, offset_days=1)

        assert price == 155.0

    def test_get_price_not_found(self):
        """Test getting price when not in database"""
        test_date = datetime(2025, 1, 1)  # No data for this date
        price = self.backtester.get_historical_price('AAPL', test_date)

        assert price is None

    def test_get_price_different_ticker(self):
        """Test getting price for ticker not in database"""
        test_date = datetime(2025, 1, 15)
        price = self.backtester.get_historical_price('TSLA', test_date)

        assert price is None


class TestSimulateTrade:
    """Test cases for trade simulation"""

    def setup_method(self):
        """Setup test database and backtester"""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name

        # Create test database with price history
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE prices (
                ticker TEXT,
                price REAL,
                collected_at DATETIME
            )
        """)

        # Insert price series for testing
        base_date = datetime(2025, 1, 1)
        prices = [100, 105, 110, 115, 120, 125, 130, 135, 140, 145]  # Uptrend
        for i, price in enumerate(prices):
            cursor.execute("INSERT INTO prices VALUES (?, ?, ?)",
                          ('AAPL', price, base_date + timedelta(days=i)))

        conn.commit()
        conn.close()

        self.config = {
            'backtesting': {
                'position_size': 1000,
                'stop_loss_pct': -10,
                'take_profit_pct': 20,
                'hold_days': 30
            }
        }
        self.backtester = Backtester(db_path=self.db_path, config=self.config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_simulate_take_profit(self):
        """Test trade that hits take profit"""
        entry_date = datetime(2025, 1, 1)
        entry_price = 100.0  # Target price = 120 (+20%)

        trade = self.backtester.simulate_trade(
            ticker='AAPL',
            entry_date=entry_date,
            entry_price=entry_price,
            conviction=80,
            signal_types=['test']
        )

        assert trade is not None
        assert trade.exit_reason == 'take_profit'
        assert trade.return_pct > 0
        assert trade.profit_loss > 0

    def test_simulate_invalid_entry_price(self):
        """Test trade with invalid entry price"""
        entry_date = datetime(2025, 1, 1)

        # Zero price
        trade = self.backtester.simulate_trade(
            ticker='AAPL',
            entry_date=entry_date,
            entry_price=0.0,
            conviction=80,
            signal_types=['test']
        )
        assert trade is None

        # Negative price
        trade = self.backtester.simulate_trade(
            ticker='AAPL',
            entry_date=entry_date,
            entry_price=-10.0,
            conviction=80,
            signal_types=['test']
        )
        assert trade is None

        # None price
        trade = self.backtester.simulate_trade(
            ticker='AAPL',
            entry_date=entry_date,
            entry_price=None,
            conviction=80,
            signal_types=['test']
        )
        assert trade is None

    def test_simulate_zero_shares(self):
        """Test trade with very high entry price (results in 0 shares)"""
        entry_date = datetime(2025, 1, 1)

        trade = self.backtester.simulate_trade(
            ticker='AAPL',
            entry_date=entry_date,
            entry_price=10000.0,  # Way too expensive for $1000 position
            conviction=80,
            signal_types=['test']
        )

        assert trade is None


class TestGetHistoricalSignals:
    """Test cases for retrieving historical signals"""

    def setup_method(self):
        """Setup test database"""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name

        # Create test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE signals (
                ticker TEXT,
                conviction_score REAL,
                triggers TEXT,
                price_at_signal REAL,
                created_at DATETIME
            )
        """)

        # Insert test signals
        base_date = datetime(2025, 1, 1)
        signals = [
            ('AAPL', 80, '["velocity_spike"]', 150.0, base_date),
            ('TSLA', 65, '["insider_buy"]', 200.0, base_date + timedelta(days=1)),
            ('MSFT', 90, '["multi_signal"]', 300.0, base_date + timedelta(days=2)),
            ('AMD', 45, '["weak_signal"]', 100.0, base_date + timedelta(days=3)),  # Low conviction
        ]

        for signal in signals:
            cursor.execute("INSERT INTO signals VALUES (?, ?, ?, ?, ?)", signal)

        conn.commit()
        conn.close()

        self.config = {'backtesting': {'min_conviction': 60}}
        self.backtester = Backtester(db_path=self.db_path, config=self.config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_get_signals_in_range(self):
        """Test getting signals within date range"""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 10)

        signals = self.backtester.get_historical_signals(start_date, end_date)

        # Should get 3 signals (AAPL, TSLA, MSFT) - AMD filtered by low conviction
        assert len(signals) == 3
        assert all(s['conviction'] >= 60 for s in signals)

    def test_get_signals_respects_conviction_filter(self):
        """Test that signals are filtered by min conviction"""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 10)

        signals = self.backtester.get_historical_signals(start_date, end_date)

        # AMD has conviction 45 < 60, should be filtered out
        tickers = [s['ticker'] for s in signals]
        assert 'AMD' not in tickers
        assert 'AAPL' in tickers
        assert 'MSFT' in tickers

    def test_get_signals_empty_range(self):
        """Test getting signals when none exist in range"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)

        signals = self.backtester.get_historical_signals(start_date, end_date)

        assert len(signals) == 0


class TestMetricCalculations:
    """Test cases for metric calculations"""

    def setup_method(self):
        """Setup test backtester"""
        self.config = {}
        self.backtester = Backtester(db_path="test.db", config=self.config)

    def test_sharpe_ratio_positive(self):
        """Test Sharpe ratio calculation with positive returns"""
        returns = [0.05, 0.03, -0.02, 0.04, 0.06]  # Mix of positive and negative

        sharpe = self.backtester.calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)
        # Sharpe should be positive for overall positive returns

    def test_sharpe_ratio_zero_std(self):
        """Test Sharpe ratio with zero standard deviation"""
        returns = [0.05, 0.05, 0.05]  # All same returns

        sharpe = self.backtester.calculate_sharpe_ratio(returns)

        assert sharpe == 0.0

    def test_sharpe_ratio_empty(self):
        """Test Sharpe ratio with empty returns"""
        sharpe = self.backtester.calculate_sharpe_ratio([])

        assert sharpe == 0.0

    def test_max_drawdown_decline(self):
        """Test max drawdown calculation with declining equity"""
        equity_curve = [10000, 9500, 9000, 8500, 8000]  # -20% drawdown

        max_dd = self.backtester.calculate_max_drawdown(equity_curve)

        assert max_dd == 20.0

    def test_max_drawdown_recovery(self):
        """Test max drawdown with recovery"""
        equity_curve = [10000, 8000, 9000, 11000]  # Drops 20% then recovers

        max_dd = self.backtester.calculate_max_drawdown(equity_curve)

        assert max_dd == 20.0  # Max drawdown during period

    def test_max_drawdown_no_decline(self):
        """Test max drawdown with only gains"""
        equity_curve = [10000, 11000, 12000, 13000]

        max_dd = self.backtester.calculate_max_drawdown(equity_curve)

        assert max_dd == 0.0

    def test_max_drawdown_empty(self):
        """Test max drawdown with empty equity curve"""
        max_dd = self.backtester.calculate_max_drawdown([])

        assert max_dd == 0.0


class TestRunBacktest:
    """Test cases for complete backtest execution"""

    def setup_method(self):
        """Setup comprehensive test database"""
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.tmp_file.name

        # Create full test database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Signals table
        cursor.execute("""
            CREATE TABLE signals (
                ticker TEXT,
                conviction_score REAL,
                triggers TEXT,
                price_at_signal REAL,
                created_at DATETIME
            )
        """)

        # Prices table
        cursor.execute("""
            CREATE TABLE prices (
                ticker TEXT,
                price REAL,
                collected_at DATETIME
            )
        """)

        # Insert test data
        base_date = datetime(2025, 1, 1)

        # Signal for AAPL
        cursor.execute("INSERT INTO signals VALUES (?, ?, ?, ?, ?)",
                      ('AAPL', 80, '["test"]', 100.0, base_date))

        # Price series for AAPL (goes up 25% over 10 days - hits take profit)
        for i in range(15):
            price = 100 + (i * 2)  # 100, 102, 104... 128
            cursor.execute("INSERT INTO prices VALUES (?, ?, ?)",
                          ('AAPL', price, base_date + timedelta(days=i)))

        # SPY for benchmark
        cursor.execute("INSERT INTO prices VALUES (?, ?, ?)",
                      ('SPY', 400.0, base_date))
        cursor.execute("INSERT INTO prices VALUES (?, ?, ?)",
                      ('SPY', 420.0, base_date + timedelta(days=30)))

        conn.commit()
        conn.close()

        self.config = {
            'backtesting': {
                'initial_capital': 10000,
                'position_size': 1000,
                'min_conviction': 60,
                'stop_loss_pct': -10,
                'take_profit_pct': 20,
                'hold_days': 30
            }
        }
        self.backtester = Backtester(db_path=self.db_path, config=self.config)

    def teardown_method(self):
        """Cleanup"""
        os.unlink(self.db_path)

    def test_run_backtest_success(self):
        """Test complete backtest execution"""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)

        results = self.backtester.run_backtest(start_date, end_date)

        assert isinstance(results, BacktestResults)
        assert results.total_trades == 1
        assert results.start_date == start_date
        assert results.end_date == end_date

    def test_run_backtest_no_signals(self):
        """Test backtest with no signals in range"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        results = self.backtester.run_backtest(start_date, end_date)

        assert results.total_trades == 0
        assert results.total_return_pct == 0.0


class TestGenerateReport:
    """Test cases for report generation"""

    def setup_method(self):
        """Setup test backtester"""
        self.config = {'backtesting': {'initial_capital': 10000}}
        self.backtester = Backtester(db_path="test.db", config=self.config)

    def test_generate_report_with_trades(self):
        """Test report generation with actual trades"""
        # Create sample results
        trade1 = BacktestTrade(
            ticker='AAPL',
            entry_date=datetime(2025, 1, 1),
            entry_price=100.0,
            exit_date=datetime(2025, 1, 15),
            exit_price=120.0,
            shares=10,
            conviction=80,
            signal_types=['test'],
            exit_reason='take_profit',
            profit_loss=200.0,
            return_pct=20.0,
            days_held=14
        )

        results = BacktestResults(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            total_trades=1,
            winning_trades=1,
            losing_trades=0,
            win_rate=100.0,
            total_return_pct=2.0,
            total_profit_loss=200.0,
            avg_return_pct=20.0,
            avg_win_pct=20.0,
            avg_loss_pct=0.0,
            best_trade_pct=20.0,
            worst_trade_pct=20.0,
            avg_days_held=14.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=1.5,
            trades=[trade1],
            benchmark_return_pct=5.0,
            alpha=-3.0
        )

        report = self.backtester.generate_report(results)

        assert isinstance(report, str)
        assert 'BACKTEST RESULTS' in report
        assert 'Total Trades:        1' in report
        assert 'Win Rate' in report or 'Winning Trades' in report

    def test_generate_report_empty(self):
        """Test report generation with no trades"""
        results = BacktestResults(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_return_pct=0.0,
            total_profit_loss=0.0,
            avg_return_pct=0.0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            best_trade_pct=0.0,
            worst_trade_pct=0.0,
            avg_days_held=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            trades=[],
            benchmark_return_pct=0.0,
            alpha=0.0
        )

        report = self.backtester.generate_report(results)

        assert isinstance(report, str)
        assert 'Total Trades:        0' in report
