"""
@file queries.py
@brief Database query helper functions
@details Provides convenient functions for retrieving data from the database
"""

import sqlite3
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DatabaseQueries:
    """
    @class DatabaseQueries
    @brief Helper class for database queries
    @details Provides methods to retrieve data for analysis and signal generation
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        @brief Initialize with database connection
        @param conn SQLite connection object
        """
        self.conn = conn

    def get_tracked_tickers(self, days: int = 7) -> List[str]:
        """
        @brief Get list of tickers that have been tracked recently
        @param days Number of days to look back
        @return List of unique ticker symbols
        """
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT ticker FROM mentions
            WHERE collected_at >= ?
            ORDER BY ticker
        """, (cutoff,))

        return [row[0] for row in cursor.fetchall()]

    def get_mention_history(self, ticker: str, days: int = 7) -> List[Tuple[datetime, int]]:
        """
        @brief Get mention count history for a ticker
        @param ticker Stock ticker symbol
        @param days Number of days to retrieve
        @return List of (timestamp, mention_count) tuples
        """
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT collected_at, mentions
            FROM mentions
            WHERE ticker = ? AND collected_at >= ?
            ORDER BY collected_at ASC
        """, (ticker, cutoff))

        rows = cursor.fetchall()
        return [(datetime.fromisoformat(row[0]), row[1]) for row in rows]

    def get_latest_mentions(self, ticker: str) -> Dict[str, Any]:
        """
        @brief Get most recent mention data for a ticker
        @param ticker Stock ticker symbol
        @return Dictionary with mention data or empty dict if not found
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT ticker, mentions, upvotes, rank, mentions_24h_ago, collected_at
            FROM mentions
            WHERE ticker = ?
            ORDER BY collected_at DESC
            LIMIT 1
        """, (ticker,))

        row = cursor.fetchone()
        if row:
            return {
                'ticker': row[0],
                'mentions': row[1],
                'upvotes': row[2],
                'rank': row[3],
                'mentions_24h_ago': row[4],
                'collected_at': row[5]
            }
        return {}

    def get_recent_insiders(self, days: int = 14) -> Dict[str, List[Dict[str, Any]]]:
        """
        @brief Get recent insider trades grouped by ticker
        @param days Number of days to look back
        @return Dictionary mapping ticker to list of insider trade dicts
        """
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT ticker, insider_name, insider_title, trade_type, trade_date,
                   shares, price, value, ownership_change_pct, is_cluster_buy
            FROM insiders
            WHERE trade_date >= ?
            ORDER BY trade_date DESC
        """, (cutoff,))

        # Group by ticker
        result: Dict[str, List[Dict[str, Any]]] = {}
        for row in cursor.fetchall():
            ticker = row[0]
            if ticker not in result:
                result[ticker] = []

            result[ticker].append({
                'insider_name': row[1],
                'insider_title': row[2],
                'trade_type': row[3],
                'trade_date': datetime.fromisoformat(row[4]) if row[4] else None,
                'shares': row[5],
                'price': row[6],
                'value': row[7],
                'ownership_change_pct': row[8],
                'is_cluster_buy': bool(row[9])
            })

        return result

    def get_latest_prices(self) -> Dict[str, Dict[str, Any]]:
        """
        @brief Get most recent price data for all tracked tickers
        @return Dictionary mapping ticker to latest price data
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT p1.ticker, p1.price, p1.change_pct, p1.news_sentiment,
                   p1.bullish_pct, p1.bearish_pct, p1.collected_at
            FROM prices p1
            INNER JOIN (
                SELECT ticker, MAX(collected_at) as max_time
                FROM prices
                GROUP BY ticker
            ) p2 ON p1.ticker = p2.ticker AND p1.collected_at = p2.max_time
        """)

        result = {}
        for row in cursor.fetchall():
            result[row[0]] = {
                'price': row[1],
                'change_pct': row[2],
                'news_sentiment': row[3],
                'bullish_pct': row[4],
                'bearish_pct': row[5],
                'collected_at': row[6]
            }

        return result

    def get_price_history(self, ticker: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        @brief Get price history for a ticker
        @param ticker Stock ticker symbol
        @param days Number of days to retrieve
        @return List of price data dictionaries
        """
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT collected_at, price, change_pct, news_sentiment,
                   bullish_pct, bearish_pct
            FROM prices
            WHERE ticker = ? AND collected_at >= ?
            ORDER BY collected_at ASC
        """, (ticker, cutoff))

        result = []
        for row in cursor.fetchall():
            result.append({
                'collected_at': datetime.fromisoformat(row[0]),
                'price': row[1],
                'change_pct': row[2],
                'news_sentiment': row[3],
                'bullish_pct': row[4],
                'bearish_pct': row[5]
            })

        return result

    def get_sentiment_history(self, ticker: str, days: int = 7) -> List[float]:
        """
        @brief Get sentiment score history for velocity calculations
        @param ticker Stock ticker symbol
        @param days Number of days to retrieve
        @return List of sentiment scores in chronological order
        """
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT news_sentiment
            FROM prices
            WHERE ticker = ? AND collected_at >= ? AND news_sentiment IS NOT NULL
            ORDER BY collected_at ASC
        """, (ticker, cutoff))

        return [row[0] for row in cursor.fetchall()]

    def get_top_velocity_tickers(self, limit: int = 50) -> List[str]:
        """
        @brief Get tickers with highest recent velocity scores
        @param limit Maximum number of tickers to return
        @return List of ticker symbols ordered by composite score
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT v1.ticker
            FROM velocity v1
            INNER JOIN (
                SELECT ticker, MAX(calculated_at) as max_time
                FROM velocity
                GROUP BY ticker
            ) v2 ON v1.ticker = v2.ticker AND v1.calculated_at = v2.max_time
            ORDER BY v1.composite_score DESC
            LIMIT ?
        """, (limit,))

        return [row[0] for row in cursor.fetchall()]

    def get_signal_history(self, ticker: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """
        @brief Get historical signals for tracking outcomes
        @param ticker Optional ticker to filter by
        @param days Number of days to look back
        @return List of signal dictionaries
        """
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        if ticker:
            cursor.execute("""
                SELECT ticker, signal_type, conviction_score, price_at_signal,
                       triggers, notes, created_at, outcome_price, outcome_pct
                FROM signals
                WHERE ticker = ? AND created_at >= ?
                ORDER BY created_at DESC
            """, (ticker, cutoff))
        else:
            cursor.execute("""
                SELECT ticker, signal_type, conviction_score, price_at_signal,
                       triggers, notes, created_at, outcome_price, outcome_pct
                FROM signals
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (cutoff,))

        result = []
        for row in cursor.fetchall():
            result.append({
                'ticker': row[0],
                'signal_type': row[1],
                'conviction_score': row[2],
                'price_at_signal': row[3],
                'triggers': row[4].split(',') if row[4] else [],
                'notes': row[5],
                'created_at': datetime.fromisoformat(row[6]),
                'outcome_price': row[7],
                'outcome_pct': row[8]
            })

        return result
