"""
@file models.py
@brief Database models and schema for sentiment velocity tracker
@details Defines SQLite database schema and provides Database class for initialization and operations
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

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

        # Macro indicators tables (Phase 2 - enhanced)
        macro_schema_path = Path(__file__).parent / "macro_schema.sql"
        if macro_schema_path.exists():
            with open(macro_schema_path, 'r') as f:
                macro_schema = f.read()
                cursor.executescript(macro_schema)
        else:
            # Fallback to basic schema if file doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS macro_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator_name TEXT NOT NULL,
                    series_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    observation_date DATE NOT NULL,
                    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(indicator_name, observation_date)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_macro_indicator_date
                ON macro_indicators(indicator_name, observation_date DESC)
            """)

        # Paper trading tables (Phase 2)
        paper_trading_schema_path = Path(__file__).parent / "paper_trading_schema.sql"
        if paper_trading_schema_path.exists():
            with open(paper_trading_schema_path, 'r') as f:
                paper_schema = f.read()
                cursor.executescript(paper_schema)


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

    def insert_macro_indicators(self, indicators: Dict[str, Dict[str, Any]]):
        """
        @brief Insert macro economic indicators
        @param indicators Dictionary of indicator_name -> indicator data
        """
        if not indicators:
            return

        conn = self.connect()
        cursor = conn.cursor()

        for indicator_name, data in indicators.items():
            cursor.execute("""
                INSERT OR REPLACE INTO macro_indicators
                (indicator_name, series_id, value, observation_date, collected_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                indicator_name,
                data.get('series_id'),
                data.get('value'),
                data.get('date'),
                data.get('collected_at', datetime.now())
            ))

        conn.commit()
        logger.info(f"Inserted {len(indicators)} macro indicators")

    def insert_market_assessment(self, assessment: Dict[str, Any], assessment_date: str = None):
        """
        @brief Insert market risk assessment
        @param assessment Dictionary with risk_level, risk_score, conditions, etc.
        @param assessment_date Date of assessment (default: today)
        """
        if not assessment:
            return

        import json
        conn = self.connect()
        cursor = conn.cursor()

        if assessment_date is None:
            assessment_date = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT OR REPLACE INTO market_assessments
            (assessment_date, risk_level, risk_score, conditions, warnings, recommendations)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            assessment_date,
            assessment.get('risk_level'),
            assessment.get('risk_score'),
            json.dumps(assessment.get('conditions', [])),
            json.dumps(assessment.get('warnings', [])),
            json.dumps(assessment.get('recommendations', []))
        ))

        conn.commit()
        logger.info(f"Inserted market assessment: {assessment.get('risk_level')} risk")

    def get_latest_macro_indicators(self) -> Dict[str, Dict[str, Any]]:
        """
        @brief Get latest values for all macro indicators
        @return Dictionary of indicator_name -> latest data
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT indicator_name, series_id, value, observation_date
            FROM macro_indicators
            WHERE (indicator_name, observation_date) IN (
                SELECT indicator_name, MAX(observation_date)
                FROM macro_indicators
                GROUP BY indicator_name
            )
        """)

        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                'indicator_name': row[0],
                'series_id': row[1],
                'value': row[2],
                'date': row[3]
            }

        return results

    def get_latest_market_assessment(self) -> Optional[Dict[str, Any]]:
        """
        @brief Get most recent market risk assessment
        @return Dictionary with assessment data, or None if no assessment exists
        """
        import json
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT assessment_date, risk_level, risk_score, conditions, warnings, recommendations
            FROM market_assessments
            ORDER BY assessment_date DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'assessment_date': row[0],
            'risk_level': row[1],
            'risk_score': row[2],
            'conditions': json.loads(row[3]) if row[3] else [],
            'warnings': json.loads(row[4]) if row[4] else [],
            'recommendations': json.loads(row[5]) if row[5] else []
        }

    def get_top_velocity_gainers(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """Get top velocity gainers in the last N hours"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ticker, mention_velocity_24h, mention_velocity_7d,
                   sentiment_velocity, composite_score, calculated_at
            FROM velocity
            WHERE calculated_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY composite_score DESC
            LIMIT ?
        """, (hours, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'ticker': row[0],
                'mention_velocity_24h': row[1],
                'mention_velocity_7d': row[2],
                'sentiment_velocity': row[3],
                'composite_score': row[4],
                'calculated_at': row[5]
            })
        return results

    def get_recent_insider_trades_detailed(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent insider trades with full details"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ticker, insider_name, trade_type, shares, value, trade_date, filing_date
            FROM insiders
            WHERE trade_date >= date('now', '-' || ? || ' days')
            ORDER BY value DESC
            LIMIT ?
        """, (days, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'ticker': row[0],
                'insider_name': row[1],
                'trade_type': row[2],
                'shares': row[3],
                'value': row[4],
                'trade_date': row[5],
                'filing_date': row[6]
            })
        return results

    def get_insider_buy_sell_ratio(self, days: int = 30) -> Dict[str, int]:
        """Get count of insider buys vs sells"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT trade_type, COUNT(*) as count
            FROM insiders
            WHERE trade_date >= date('now', '-' || ? || ' days')
            GROUP BY trade_type
        """, (days,))

        result = {'buy': 0, 'sell': 0}
        for row in cursor.fetchall():
            trade_type = row[0].lower() if row[0] else 'unknown'
            if 'buy' in trade_type or 'purchase' in trade_type:
                result['buy'] = row[1]
            elif 'sell' in trade_type or 'sale' in trade_type:
                result['sell'] = row[1]
        return result

    def get_top_social_mentions(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """Get top mentioned tickers on social media"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ticker, mentions, upvotes,
                   mentions * (1 + upvotes/100.0) as viral_score,
                   collected_at
            FROM mentions
            WHERE collected_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY viral_score DESC
            LIMIT ?
        """, (hours, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                'ticker': row[0],
                'mention_count': row[1],  # Keep dict key as mention_count for compatibility
                'upvotes': row[2],
                'viral_score': row[3],
                'collected_at': row[4]
            })
        return results

    def get_sentiment_shifts(self, min_change: float = 0.3, days: int = 7) -> List[Dict[str, Any]]:
        """Get tickers with significant sentiment changes"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT v.ticker, v.sentiment_velocity,
                   p1.news_sentiment as current_sentiment,
                   p2.news_sentiment as previous_sentiment,
                   (p1.news_sentiment - p2.news_sentiment) as sentiment_change
            FROM velocity v
            LEFT JOIN prices p1 ON v.ticker = p1.ticker
                AND p1.collected_at = (SELECT MAX(collected_at) FROM prices WHERE ticker = v.ticker)
            LEFT JOIN prices p2 ON v.ticker = p2.ticker
                AND p2.collected_at = (SELECT MAX(collected_at) FROM prices WHERE ticker = v.ticker
                    AND collected_at < datetime('now', '-' || ? || ' days'))
            WHERE ABS(v.sentiment_velocity) >= ?
            ORDER BY ABS(v.sentiment_velocity) DESC
            LIMIT 20
        """, (days, min_change))

        results = []
        for row in cursor.fetchall():
            if row[0]:  # Ensure ticker exists
                results.append({
                    'ticker': row[0],
                    'sentiment_velocity': row[1],
                    'current_sentiment': row[2] if row[2] is not None else 0,
                    'previous_sentiment': row[3] if row[3] is not None else 0,
                    'sentiment_change': row[4] if row[4] is not None else 0
                })
        return results

    def get_macro_indicator_history(self, indicator: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical values for a macro indicator"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(macro_indicators)")
        columns = [row['name'] for row in cursor.fetchall()]
        date_col = "observation_date" if "observation_date" in columns else "date"

        cursor.execute(f"""
            SELECT indicator_name, value, {date_col}
            FROM macro_indicators
            WHERE indicator_name = ?
              AND {date_col} >= date('now', '-' || ? || ' days')
            ORDER BY {date_col} ASC
        """, (indicator, days))

        results = []
        for row in cursor.fetchall():
            results.append({
                'indicator': row[0],
                'value': row[1],
                'date': row[2]
            })
        return results

    def get_signal_performance_by_type(self) -> List[Dict[str, Any]]:
        """Get aggregated performance stats by signal type"""
        conn = self.connect()
        cursor = conn.cursor()

        # Try to use profit_loss or fallback to a dummy if signal_id is missing from paper_trades schema
        # In paper_trading_schema.sql, paper_trades has profit_loss, and signal_id is not explicitly defined
        # We'll join on ticker and created_date if signal_id is missing, or just assume signal_id is added

        # Check if signal_id exists
        cursor.execute("PRAGMA table_info(paper_trades)")
        columns = [row['name'] for row in cursor.fetchall()]
        join_clause = "ON s.id = pt.signal_id" if "signal_id" in columns else "ON s.ticker = pt.ticker AND date(s.created_at) = date(pt.entry_date)"
        pnl_col = "profit_loss" if "profit_loss" in columns else "pnl"

        cursor.execute(f"""
            SELECT s.signal_type,
                   COUNT(DISTINCT s.id) as signal_count,
                   AVG(s.conviction_score) as avg_conviction,
                   COUNT(DISTINCT pt.id) as trades_executed,
                   SUM(CASE WHEN pt.{pnl_col} > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pt.{pnl_col} <= 0 AND pt.{pnl_col} IS NOT NULL THEN 1 ELSE 0 END) as losses,
                   AVG(pt.{pnl_col}) as avg_pnl,
                   MAX(pt.{pnl_col}) as best_trade,
                   MIN(pt.{pnl_col}) as worst_trade
            FROM signals s
            LEFT JOIN paper_trades pt {join_clause} AND pt.exit_date IS NOT NULL
            WHERE s.created_at >= datetime('now', '-90 days')
            GROUP BY s.signal_type
            ORDER BY signal_count DESC
        """)

        results = []
        for row in cursor.fetchall():
            wins = row[4] or 0
            losses = row[5] or 0
            total_closed = wins + losses
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

            results.append({
                'signal_type': row[0],
                'signal_count': row[1],
                'avg_conviction': row[2],
                'trades_executed': row[3] or 0,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_pnl': row[6] or 0,
                'best_trade': row[7] or 0,
                'worst_trade': row[8] or 0
            })
        return results

    def get_paper_trading_equity_curve(self, days: int = 90) -> List[Dict[str, Any]]:
        """Get daily equity curve for paper trading"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(paper_trades)")
        columns = [row['name'] for row in cursor.fetchall()]
        pnl_col = "profit_loss" if "profit_loss" in columns else "pnl"

        cursor.execute("""
            SELECT date(snapshot_date) as trade_date,
                   SUM(unrealized_pnl) as daily_unrealized,
                   COUNT(DISTINCT trade_id) as open_positions
            FROM paper_trade_snapshots
            WHERE snapshot_date >= datetime('now', '-' || ? || ' days')
            GROUP BY date(snapshot_date)
            ORDER BY trade_date ASC
        """, (days,))

        equity_curve = []
        cumulative_realized = 0

        for row in cursor.fetchall():
            equity_curve.append({
                'date': row[0],
                'unrealized_pnl': row[1] or 0,
                'open_positions': row[2],
                'total_equity': cumulative_realized + (row[1] or 0)
            })

        # Add realized P/L
        cursor.execute(f"""
            SELECT date(exit_date) as trade_date, SUM({pnl_col}) as realized_pnl
            FROM paper_trades
            WHERE exit_date IS NOT NULL
              AND exit_date >= datetime('now', '-' || ? || ' days')
            GROUP BY date(exit_date)
            ORDER BY trade_date ASC
        """, (days,))

        realized_by_date = {row[0]: row[1] for row in cursor.fetchall()}

        # Combine realized and unrealized
        for point in equity_curve:
            if point['date'] in realized_by_date:
                cumulative_realized += realized_by_date[point['date']]
            point['total_equity'] = cumulative_realized + point['unrealized_pnl']
            point['realized_pnl'] = cumulative_realized

        return equity_curve

    def get_emerging_tickers(self, hours: int = 24, min_mentions: int = 5) -> List[Dict[str, Any]]:
        """Get tickers that recently entered the top mentions"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m1.ticker, m1.mentions, m1.collected_at
            FROM mentions m1
            WHERE m1.collected_at >= datetime('now', '-' || ? || ' hours')
              AND m1.mentions >= ?
              AND NOT EXISTS (
                  SELECT 1 FROM mentions m2
                  WHERE m2.ticker = m1.ticker
                    AND m2.collected_at < datetime('now', '-' || ? || ' hours')
                    AND m2.collected_at >= datetime('now', '-' || ? || ' hours')
              )
            ORDER BY m1.mentions DESC
            LIMIT 10
        """, (hours, min_mentions, hours, hours * 2))

        results = []
        for row in cursor.fetchall():
            results.append({
                'ticker': row[0],
                'mention_count': row[1],  # Keep dict key as mention_count for compatibility
                'first_seen': row[2]
            })
        return results

