"""
@file models.py
@brief Database models and schema for sentiment velocity tracker
@details Defines SQLite database schema and provides Database class for initialization and operations
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """
    @class Database
    @brief Main database interface for sentiment velocity tracker
    @details Handles SQLite database initialization, connection management, and data insertion
    """

    def __init__(self, db_path: str = "data/sentiment.db"):
        """
        @brief Initialize database connection
        @param db_path Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        @brief Create or get database connection
        @return SQLite connection object
        """
        if self.conn is None:
            # Ensure parent directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        return self.conn

    def close(self):
        """
        @brief Close database connection
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    def initialize(self):
        """
        @brief Initialize database schema
        @details Creates all required tables and indexes if they don't exist
        """
        conn = self.connect()
        cursor = conn.cursor()

        # Social mentions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                mentions INTEGER NOT NULL,
                upvotes INTEGER,
                rank INTEGER,
                mentions_24h_ago INTEGER,
                rank_24h_ago INTEGER,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'apewisdom'
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_ticker_time
            ON mentions(ticker, collected_at)
        """)

        # Insider trading table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insiders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                insider_name TEXT,
                insider_title TEXT,
                trade_type TEXT,
                trade_date DATE,
                filing_date DATE,
                shares INTEGER,
                price REAL,
                value REAL,
                ownership_change_pct REAL,
                is_cluster_buy BOOLEAN DEFAULT 0,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_insiders_ticker_date
            ON insiders(ticker, trade_date)
        """)

        # Price and sentiment table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                price REAL,
                change_pct REAL,
                high REAL,
                low REAL,
                open REAL,
                prev_close REAL,
                news_sentiment REAL,
                bullish_pct REAL,
                bearish_pct REAL,
                buzz_score REAL,
                articles_week INTEGER,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_ticker_time
            ON prices(ticker, collected_at)
        """)

        # Velocity metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS velocity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                mention_velocity_24h REAL,
                mention_velocity_7d REAL,
                sentiment_velocity REAL,
                volume_price_divergence REAL,
                composite_score REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_velocity_ticker_time
            ON velocity(ticker, calculated_at)
        """)

        # Signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                signal_type TEXT,
                conviction_score REAL,
                price_at_signal REAL,
                triggers TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                outcome_price REAL,
                outcome_date DATE,
                outcome_pct REAL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_ticker_date
            ON signals(ticker, created_at)
        """)

        # Macro indicators table (Phase 2)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS macro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id TEXT NOT NULL,
                value REAL,
                observation_date DATE,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_macro_series_date
            ON macro(series_id, observation_date)
        """)

        conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def insert_mentions(self, mentions: List[Dict[str, Any]]):
        """
        @brief Insert social mention data
        @param mentions List of mention dictionaries from collectors
        """
        if not mentions:
            return

        conn = self.connect()
        cursor = conn.cursor()

        for mention in mentions:
            cursor.execute("""
                INSERT INTO mentions (ticker, mentions, upvotes, rank, mentions_24h_ago,
                                     rank_24h_ago, collected_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mention.get('ticker'),
                mention.get('mentions'),
                mention.get('upvotes'),
                mention.get('rank'),
                mention.get('mentions_24h_ago'),
                mention.get('rank_24h_ago'),
                mention.get('collected_at', datetime.now()),
                mention.get('source', 'apewisdom')
            ))

        conn.commit()
        logger.info(f"Inserted {len(mentions)} mention records")

    def insert_insiders(self, insiders: List[Dict[str, Any]]):
        """
        @brief Insert insider trading data
        @param insiders List of insider trade dictionaries
        """
        if not insiders:
            return

        conn = self.connect()
        cursor = conn.cursor()

        for insider in insiders:
            cursor.execute("""
                INSERT INTO insiders (ticker, insider_name, insider_title, trade_type,
                                     trade_date, filing_date, shares, price, value,
                                     ownership_change_pct, is_cluster_buy, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                insider.get('ticker'),
                insider.get('insider_name'),
                insider.get('insider_title'),
                insider.get('trade_type'),
                insider.get('trade_date'),
                insider.get('filing_date'),
                insider.get('shares'),
                insider.get('price'),
                insider.get('value'),
                insider.get('ownership_change_pct'),
                insider.get('is_cluster_buy', False),
                insider.get('collected_at', datetime.now())
            ))

        conn.commit()
        logger.info(f"Inserted {len(insiders)} insider trade records")

    def insert_prices(self, prices: List[Dict[str, Any]]):
        """
        @brief Insert price and sentiment data
        @param prices List of price/sentiment dictionaries
        """
        if not prices:
            return

        conn = self.connect()
        cursor = conn.cursor()

        for price in prices:
            cursor.execute("""
                INSERT INTO prices (ticker, price, change_pct, high, low, open, prev_close,
                                   news_sentiment, bullish_pct, bearish_pct, buzz_score,
                                   articles_week, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                price.get('ticker'),
                price.get('price'),
                price.get('change_pct'),
                price.get('high'),
                price.get('low'),
                price.get('open'),
                price.get('prev_close'),
                price.get('news_sentiment'),
                price.get('bullish_pct'),
                price.get('bearish_pct'),
                price.get('buzz_score'),
                price.get('articles_week'),
                price.get('collected_at', datetime.now())
            ))

        conn.commit()
        logger.info(f"Inserted {len(prices)} price records")

    def insert_velocity(self, velocity_data: Dict[str, Dict[str, float]]):
        """
        @brief Insert velocity metrics
        @param velocity_data Dictionary mapping ticker to velocity metrics
        """
        if not velocity_data:
            return

        conn = self.connect()
        cursor = conn.cursor()

        for ticker, metrics in velocity_data.items():
            cursor.execute("""
                INSERT INTO velocity (ticker, mention_velocity_24h, mention_velocity_7d,
                                     sentiment_velocity, volume_price_divergence,
                                     composite_score, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                metrics.get('mention_velocity_24h'),
                metrics.get('mention_velocity_7d'),
                metrics.get('sentiment_velocity'),
                metrics.get('volume_price_divergence'),
                metrics.get('composite_score'),
                datetime.now()
            ))

        conn.commit()
        logger.info(f"Inserted {len(velocity_data)} velocity records")

    def insert_signals(self, signals: List[Any]):
        """
        @brief Insert generated signals
        @param signals List of Signal objects
        """
        if not signals:
            return

        conn = self.connect()
        cursor = conn.cursor()

        for signal in signals:
            cursor.execute("""
                INSERT INTO signals (ticker, signal_type, conviction_score, price_at_signal,
                                    triggers, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.ticker,
                signal.signal_type,
                signal.conviction_score,
                signal.price_at_signal,
                ','.join(signal.triggers),
                signal.notes,
                signal.created_at
            ))

        conn.commit()
        logger.info(f"Inserted {len(signals)} signal records")

    def get_tracked_tickers(self, days: int = 7) -> List[str]:
        """
        @brief Get list of tickers tracked recently
        @param days Number of days to look back
        @return List of unique ticker symbols
        """
        from src.database.queries import DatabaseQueries
        queries = DatabaseQueries(self.connect())
        return queries.get_tracked_tickers(days)

    def get_recent_insiders(self, days: int = 14) -> Dict[str, List[Dict[str, Any]]]:
        """
        @brief Get recent insider trades
        @param days Number of days to look back
        @return Dictionary mapping ticker to list of trades
        """
        from src.database.queries import DatabaseQueries
        queries = DatabaseQueries(self.connect())
        return queries.get_recent_insiders(days)

    def get_latest_prices(self) -> Dict[str, Dict[str, Any]]:
        """
        @brief Get latest price data for all tickers
        @return Dictionary mapping ticker to price data
        """
        from src.database.queries import DatabaseQueries
        queries = DatabaseQueries(self.connect())
        return queries.get_latest_prices()

    def get_mention_history(self, ticker: str, days: int = 7) -> List[tuple]:
        """
        @brief Get mention history for a ticker
        @param ticker Stock ticker symbol
        @param days Number of days to retrieve
        @return List of (timestamp, mentions) tuples
        """
        from src.database.queries import DatabaseQueries
        queries = DatabaseQueries(self.connect())
        return queries.get_mention_history(ticker, days)

    def get_price_history(self, ticker: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        @brief Get price history for a ticker
        @param ticker Stock ticker symbol
        @param days Number of days to retrieve
        @return List of price dictionaries
        """
        from src.database.queries import DatabaseQueries
        queries = DatabaseQueries(self.connect())
        return queries.get_price_history(ticker, days)

    def get_sentiment_history(self, ticker: str, days: int = 7) -> List[float]:
        """
        @brief Get sentiment history for a ticker
        @param ticker Stock ticker symbol
        @param days Number of days to retrieve
        @return List of sentiment scores
        """
        from src.database.queries import DatabaseQueries
        queries = DatabaseQueries(self.connect())
        return queries.get_sentiment_history(ticker, days)
