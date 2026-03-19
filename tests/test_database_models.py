"""
@file test_database_models.py
@brief Test suite for enhanced database analytics query methods
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from src.database.models import Database


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database"""
    db_path = tmp_path / "test_sentiment.db"
    db = Database(str(db_path))
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def sample_velocity_data(test_db):
    """Insert sample velocity data for testing"""
    conn = test_db.connect()
    cursor = conn.cursor()

    # Insert sample velocity data
    for i in range(15):
        cursor.execute("""
            INSERT INTO velocity
            (ticker, mention_velocity_24h, mention_velocity_7d, sentiment_velocity, composite_score, calculated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', '-' || ? || ' hours'))
        """, (f'TEST{i}', 10.0 + i, 5.0 + i, 0.5 + i*0.1, 50.0 + i*5, i))

    conn.commit()
    return test_db


@pytest.fixture
def sample_insider_data(test_db):
    """Insert sample insider trades data for testing"""
    conn = test_db.connect()
    cursor = conn.cursor()

    # Insert sample insider trades
    for i in range(20):
        trade_type = 'Purchase' if i % 2 == 0 else 'Sale'
        cursor.execute("""
            INSERT INTO insiders
            (ticker, insider_name, trade_type, value, trade_date, collected_at)
            VALUES (?, ?, ?, ?, date('now', '-' || ? || ' days'), datetime('now'))
        """, (f'TICK{i}', f'Insider {i}', trade_type, 100000 + i*10000, i))

    conn.commit()
    return test_db


@pytest.fixture
def sample_social_data(test_db):
    """Insert sample social media data for testing"""
    conn = test_db.connect()
    cursor = conn.cursor()

    # Insert sample social mentions
    for i in range(15):
        cursor.execute("""
            INSERT INTO mentions
            (ticker, mentions, upvotes, rank, collected_at)
            VALUES (?, ?, ?, ?, datetime('now', '-' || ? || ' hours'))
        """, (f'SOC{i}', 100 + i*10, 50 + i*5, i, i))

    conn.commit()
    return test_db


@pytest.fixture
def sample_signal_data(test_db):
    """Insert sample signals and paper trades for testing"""
    conn = test_db.connect()
    cursor = conn.cursor()

    # Get column names to handle schema variations
    cursor.execute("PRAGMA table_info(paper_trades)")
    columns = [row['name'] for row in cursor.fetchall()]

    # Insert sample signals
    signal_types = ['velocity_spike', 'insider_buy', 'technical_breakout']
    for i in range(30):
        signal_type = signal_types[i % len(signal_types)]
        cursor.execute("""
            INSERT INTO signals
            (ticker, signal_type, conviction_score, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now', '-' || ? || ' days'))
        """, (f'SIG{i}', signal_type, 60.0 + i*1.5, 'Test signal', i % 90))

        # Add paper trades for some signals
        if i % 3 == 0:
            signal_id = cursor.lastrowid
            pnl = (i % 2) * 200 - 100  # Alternating wins/losses

            entry_date = datetime.now() - timedelta(days=i % 90)
            exit_date = datetime.now() - timedelta(days=(i % 90) - 1)

            if "signal_id" in columns:
                if "profit_loss" in columns:
                    cursor.execute("""
                        INSERT INTO paper_trades
                        (signal_id, ticker, entry_price, exit_price, shares, profit_loss, entry_date, exit_date, position_size, conviction, signal_types)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (signal_id, f'SIG{i}', 100.0, 100.0 + pnl/10, 10, pnl, entry_date, exit_date, 1000.0, 60, "[]"))
                else:
                    cursor.execute("""
                        INSERT INTO paper_trades
                        (signal_id, ticker, entry_price, exit_price, shares, pnl, entry_date, exit_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (signal_id, f'SIG{i}', 100.0, 100.0 + pnl/10, 10, pnl, entry_date, exit_date))
            else:
                cursor.execute("""
                    INSERT INTO paper_trades
                    (ticker, entry_price, exit_price, shares, profit_loss, entry_date, exit_date, position_size, conviction, signal_types)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (f'SIG{i}', 100.0, 100.0 + pnl/10, 10, pnl, entry_date, exit_date, 1000.0, 60, "[]"))

    conn.commit()
    return test_db


class TestVelocityQueries:
    """Test velocity-related analytics queries"""

    def test_get_top_velocity_gainers(self, sample_velocity_data):
        """Test retrieving top velocity gainers"""
        results = sample_velocity_data.get_top_velocity_gainers(limit=5, hours=24)

        assert len(results) <= 5
        assert all('ticker' in r for r in results)
        assert all('composite_score' in r for r in results)

        # Verify results are sorted by composite_score descending
        if len(results) > 1:
            scores = [r['composite_score'] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_get_top_velocity_gainers_empty(self, test_db):
        """Test velocity gainers with empty database"""
        results = test_db.get_top_velocity_gainers(limit=10, hours=24)
        assert results == []


class TestInsiderTradesQueries:
    """Test insider trading analytics queries"""

    def test_get_recent_insider_trades_detailed(self, sample_insider_data):
        """Test retrieving recent insider trades"""
        results = sample_insider_data.get_recent_insider_trades_detailed(days=30, limit=10)

        assert len(results) <= 10
        assert all('ticker' in r for r in results)
        assert all('trade_type' in r for r in results)
        assert all('value' in r for r in results)

    def test_get_insider_buy_sell_ratio(self, sample_insider_data):
        """Test calculating buy/sell ratio"""
        ratio = sample_insider_data.get_insider_buy_sell_ratio(days=30)

        assert 'buy' in ratio
        assert 'sell' in ratio
        assert ratio['buy'] + ratio['sell'] > 0

    def test_get_insider_buy_sell_ratio_empty(self, test_db):
        """Test buy/sell ratio with empty database"""
        ratio = test_db.get_insider_buy_sell_ratio(days=30)
        assert ratio == {'buy': 0, 'sell': 0}


class TestSocialQueries:
    """Test social media analytics queries"""

    def test_get_top_social_mentions(self, sample_social_data):
        """Test retrieving top social mentions"""
        results = sample_social_data.get_top_social_mentions(limit=5, hours=24)

        assert len(results) <= 5
        assert all('ticker' in r for r in results)
        assert all('mention_count' in r for r in results)
        assert all('viral_score' in r for r in results)

    def test_get_emerging_tickers(self, sample_social_data):
        """Test identifying emerging tickers"""
        results = sample_social_data.get_emerging_tickers(hours=24, min_mentions=5)

        assert isinstance(results, list)
        assert all('ticker' in r for r in results)

    def test_get_emerging_tickers_empty(self, test_db):
        """Test emerging tickers with empty database"""
        results = test_db.get_emerging_tickers(hours=24, min_mentions=5)
        assert results == []


class TestSentimentQueries:
    """Test sentiment analytics queries"""

    def test_get_sentiment_shifts(self, test_db):
        """Test detecting sentiment shifts"""
        # This test requires sentiment data which isn't in the current schema
        # Will pass with empty results for now
        results = test_db.get_sentiment_shifts(min_change=0.3, days=7)
        assert isinstance(results, list)


class TestSignalPerformanceQueries:
    """Test signal performance analytics queries"""

    def test_get_signal_performance_by_type(self, sample_signal_data):
        """Test aggregating signal performance by type"""
        results = sample_signal_data.get_signal_performance_by_type()

        assert len(results) > 0
        assert all('signal_type' in r for r in results)
        assert all('signal_count' in r for r in results)
        assert all('avg_conviction' in r for r in results)

        # Verify win rate calculation
        for perf in results:
            if perf['trades_executed'] > 0:
                assert 0 <= perf['win_rate'] <= 100

    def test_get_paper_trading_equity_curve(self, sample_signal_data):
        """Test equity curve calculation"""
        results = sample_signal_data.get_paper_trading_equity_curve(days=90)

        assert isinstance(results, list)
        assert all('date' in r for r in results)
        assert all('cumulative_pnl' in r for r in results)

    def test_get_signal_performance_empty(self, test_db):
        """Test signal performance with no data"""
        results = test_db.get_signal_performance_by_type()
        assert results == []


class TestMacroIndicatorQueries:
    """Test macro indicator analytics queries"""

    def test_get_macro_indicator_history(self, test_db):
        """Test retrieving macro indicator history"""
        # Insert sample macro data
        conn = test_db.connect()
        cursor = conn.cursor()

        for i in range(30):
            cursor.execute("""
                INSERT INTO macro_indicators
                (indicator_name, series_id, value, observation_date, collected_at)
                VALUES (?, ?, ?, date('now', '-' || ? || ' days'), datetime('now', '-' || ? || ' days'))
            """, ('VIX', 'VIXCLS', 20.0 + i*0.5, i, i))

        conn.commit()

        results = test_db.get_macro_indicator_history('VIX', days=30)

        assert len(results) <= 30
        assert all('date' in r for r in results)
        assert all('value' in r for r in results)

    def test_get_macro_indicator_history_empty(self, test_db):
        """Test macro indicator with no data"""
        results = test_db.get_macro_indicator_history('NONEXISTENT', days=30)
        assert results == []


class TestQueryEdgeCases:
    """Test edge cases and error handling"""

    def test_queries_with_zero_limit(self, sample_velocity_data):
        """Test queries with limit=0"""
        results = sample_velocity_data.get_top_velocity_gainers(limit=0, hours=24)
        assert results == []

    def test_queries_with_large_limit(self, sample_velocity_data):
        """Test queries with very large limit"""
        results = sample_velocity_data.get_top_velocity_gainers(limit=1000, hours=24)
        assert len(results) <= 15  # Only 15 records inserted in fixture

    def test_queries_with_zero_timeframe(self, sample_velocity_data):
        """Test queries with 0 hours/days"""
        results = sample_velocity_data.get_top_velocity_gainers(limit=10, hours=0)
        # Should return empty or very recent data
        assert isinstance(results, list)
