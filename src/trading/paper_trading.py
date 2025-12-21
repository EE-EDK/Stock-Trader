"""
@file paper_trading.py
@brief Paper trading system for validating signal performance
@details Track mock purchases and measure real-world performance over time
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PaperTradingManager:
    """
    @class PaperTradingManager
    @brief Manages paper trading positions and performance tracking
    """

    def __init__(self, db_path: str, config: dict):
        """
        @brief Initialize paper trading manager
        @param db_path Path to SQLite database
        @param config Paper trading configuration
        """
        self.db_path = db_path
        self.config = config.get('paper_trading', {})
        self.enabled = self.config.get('enabled', False)
        self.min_conviction = self.config.get('min_conviction', 60)
        self.base_position_size = self.config.get('position_size', 1000)
        self.max_open_positions = self.config.get('max_open_positions', 10)
        self.hold_days = self.config.get('hold_days', 30)
        self.stop_loss_pct = self.config.get('stop_loss_pct', -10)
        self.take_profit_pct = self.config.get('take_profit_pct', 20)

        if self.enabled:
            self._init_tables()

    def _init_tables(self):
        """Initialize paper trading tables if they don't exist"""
        schema_path = 'src/database/paper_trading_schema.sql'
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            conn = sqlite3.connect(self.db_path)
            conn.executescript(schema_sql)
            conn.commit()
            conn.close()
            logger.info("Paper trading tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize paper trading tables: {e}")

    def calculate_position_size(self, conviction: int) -> float:
        """
        @brief Calculate position size based on conviction (weighted)
        @param conviction Signal conviction score (0-100)
        @return Dollar amount to invest

        conviction 100 → 2x base ($2000)
        conviction 80 → 1.6x base ($1600)
        conviction 60 → 1.2x base ($1200)
        conviction 50 → 1.0x base ($1000)
        """
        # Linear scaling from conviction
        # conviction 50 = 1.0x, conviction 100 = 2.0x
        multiplier = 1.0 + ((conviction - 50) / 50)
        return self.base_position_size * multiplier

    def create_paper_trade(self, ticker: str, entry_price: float, conviction: int,
                          signal_types: List[str], entry_date: datetime) -> Optional[int]:
        """
        @brief Create a new paper trade position
        @param ticker Stock ticker symbol
        @param entry_price Entry price
        @param conviction Signal conviction score
        @param signal_types List of signal trigger types
        @param entry_date Date of entry
        @return Trade ID if created, None if skipped
        """
        if not self.enabled:
            return None

        # Check if we already have this trade (for idempotent backfill)
        if self._trade_exists(ticker, entry_date):
            logger.debug(f"Paper trade already exists for {ticker} on {entry_date}, skipping")
            return None

        # Check max open positions
        open_count = self._count_open_positions()
        if open_count >= self.max_open_positions:
            logger.warning(f"Max open positions ({self.max_open_positions}) reached, skipping {ticker}")
            return None

        # Calculate position details
        position_size = self.calculate_position_size(conviction)
        shares = int(position_size / entry_price)
        actual_position_size = shares * entry_price

        # Calculate exit prices
        stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
        target_price = entry_price * (1 + self.take_profit_pct / 100)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO paper_trades
                (ticker, entry_date, entry_price, shares, conviction, signal_types,
                 position_size, stop_loss, target_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """, (ticker, entry_date, entry_price, shares, conviction,
                  json.dumps(signal_types), actual_position_size, stop_loss, target_price))

            trade_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Created paper trade: {ticker} | {shares} shares @ ${entry_price:.2f} "
                       f"| Position: ${actual_position_size:.2f} (conviction {conviction})")
            return trade_id

        except sqlite3.IntegrityError:
            # Duplicate trade (ticker + entry_date unique constraint)
            logger.debug(f"Duplicate paper trade for {ticker} on {entry_date}, skipping")
            return None
        except Exception as e:
            logger.error(f"Failed to create paper trade for {ticker}: {e}")
            return None

    def _trade_exists(self, ticker: str, entry_date: datetime) -> bool:
        """Check if a trade already exists for this ticker and date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM paper_trades
            WHERE ticker = ? AND entry_date = ?
        """, (ticker, entry_date))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def _count_open_positions(self) -> int:
        """Count currently open positions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM paper_trades WHERE status = 'open'")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def update_positions(self, current_prices: Dict[str, float], current_date: datetime):
        """
        @brief Update all open positions with current prices and check exit conditions
        @param current_prices Dict of {ticker: current_price}
        @param current_date Current date
        """
        if not self.enabled:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all open positions
        cursor.execute("""
            SELECT id, ticker, entry_date, entry_price, shares, stop_loss, target_price
            FROM paper_trades
            WHERE status = 'open'
        """)
        open_trades = cursor.fetchall()

        for trade in open_trades:
            trade_id, ticker, entry_date_str, entry_price, shares, stop_loss, target_price = trade

            # Get current price
            current_price = current_prices.get(ticker)
            if not current_price:
                logger.warning(f"No current price for {ticker}, skipping update")
                continue

            # Create snapshot
            unrealized_pnl = (current_price - entry_price) * shares
            unrealized_pct = ((current_price - entry_price) / entry_price) * 100

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO paper_trade_snapshots
                    (trade_id, snapshot_date, current_price, unrealized_pnl, unrealized_pct)
                    VALUES (?, ?, ?, ?, ?)
                """, (trade_id, current_date, current_price, unrealized_pnl, unrealized_pct))
            except Exception as e:
                logger.error(f"Failed to create snapshot for trade {trade_id}: {e}")

            # Check exit conditions
            entry_date = datetime.fromisoformat(entry_date_str)
            days_held = (current_date - entry_date).days

            exit_reason = None
            if current_price <= stop_loss:
                exit_reason = 'stop_loss'
            elif current_price >= target_price:
                exit_reason = 'take_profit'
            elif days_held >= self.hold_days:
                exit_reason = 'time_limit'

            if exit_reason:
                self._close_position(cursor, trade_id, current_price, current_date,
                                   exit_reason, entry_price, shares, days_held)

        conn.commit()
        conn.close()
        logger.info(f"Updated {len(open_trades)} open paper trading positions")

    def _close_position(self, cursor, trade_id: int, exit_price: float, exit_date: datetime,
                       exit_reason: str, entry_price: float, shares: int, days_held: int):
        """Close a position and record performance"""
        profit_loss = (exit_price - entry_price) * shares
        return_pct = ((exit_price - entry_price) / entry_price) * 100

        cursor.execute("""
            UPDATE paper_trades
            SET exit_date = ?, exit_price = ?, exit_reason = ?, status = 'closed',
                profit_loss = ?, return_pct = ?, days_held = ?
            WHERE id = ?
        """, (exit_date, exit_price, exit_reason, profit_loss, return_pct, days_held, trade_id))

        logger.info(f"Closed paper trade {trade_id}: {exit_reason} | "
                   f"P/L: ${profit_loss:.2f} ({return_pct:+.1f}%) | {days_held} days")

    def backfill_from_signals(self, days: int = 30):
        """
        @brief Backfill paper trades from historical signals (idempotent)
        @param days Number of days to look back
        """
        if not self.enabled:
            return

        logger.info(f"Backfilling paper trades from signals in last {days} days...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get signals from last N days with conviction >= threshold
        cutoff_date = datetime.now() - timedelta(days=days)
        cursor.execute("""
            SELECT ticker, conviction, triggers, generated_at
            FROM signals
            WHERE generated_at >= ? AND conviction >= ?
            ORDER BY generated_at ASC
        """, (cutoff_date, self.min_conviction))

        signals = cursor.fetchall()
        conn.close()

        created_count = 0
        skipped_count = 0

        for signal in signals:
            ticker, conviction, triggers_json, generated_at_str = signal
            signal_types = json.loads(triggers_json) if triggers_json else []
            generated_at = datetime.fromisoformat(generated_at_str)

            # Get entry price (from prices table at that date)
            entry_price = self._get_historical_price(ticker, generated_at)
            if not entry_price:
                logger.warning(f"No historical price for {ticker} on {generated_at}, skipping")
                skipped_count += 1
                continue

            # Create paper trade (will skip if already exists)
            trade_id = self.create_paper_trade(ticker, entry_price, conviction,
                                              signal_types, generated_at)
            if trade_id:
                created_count += 1
            else:
                skipped_count += 1

        logger.info(f"Backfill complete: {created_count} trades created, {skipped_count} skipped")

    def _get_historical_price(self, ticker: str, date: datetime) -> Optional[float]:
        """Get historical price for a ticker on a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get price closest to the date (within 1 day)
        cursor.execute("""
            SELECT current_price FROM prices
            WHERE ticker = ? AND collected_at >= ? AND collected_at < ?
            ORDER BY collected_at ASC
            LIMIT 1
        """, (ticker, date, date + timedelta(days=1)))

        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_performance_summary(self) -> Dict:
        """
        @brief Get overall performance statistics
        @return Dict with performance metrics
        """
        if not self.enabled:
            return {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Closed trades stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                AVG(return_pct) as avg_return_pct,
                SUM(profit_loss) as total_pnl,
                AVG(days_held) as avg_days_held,
                MAX(return_pct) as best_return,
                MIN(return_pct) as worst_return
            FROM paper_trades
            WHERE status = 'closed'
        """)
        closed_stats = cursor.fetchone()

        # Open positions stats
        cursor.execute("""
            SELECT COUNT(*), SUM(position_size)
            FROM paper_trades
            WHERE status = 'open'
        """)
        open_count, total_deployed = cursor.fetchone()

        # Get latest unrealized P/L for open positions
        cursor.execute("""
            SELECT SUM(s.unrealized_pnl), AVG(s.unrealized_pct)
            FROM paper_trade_snapshots s
            INNER JOIN (
                SELECT trade_id, MAX(snapshot_date) as max_date
                FROM paper_trade_snapshots
                GROUP BY trade_id
            ) latest ON s.trade_id = latest.trade_id AND s.snapshot_date = latest.max_date
        """)
        unrealized_pnl, unrealized_pct = cursor.fetchone()

        conn.close()

        if closed_stats[0] == 0:  # No closed trades yet
            win_rate = 0
            avg_return = 0
            total_pnl = 0
            avg_days = 0
            best_return = 0
            worst_return = 0
        else:
            total_trades, winning_trades, avg_return, total_pnl, avg_days, best_return, worst_return = closed_stats
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return {
            'closed_trades': {
                'count': closed_stats[0] or 0,
                'win_rate': win_rate,
                'avg_return_pct': avg_return or 0,
                'total_pnl': total_pnl or 0,
                'avg_days_held': avg_days or 0,
                'best_return': best_return or 0,
                'worst_return': worst_return or 0
            },
            'open_positions': {
                'count': open_count or 0,
                'total_deployed': total_deployed or 0,
                'unrealized_pnl': unrealized_pnl or 0,
                'unrealized_pct': unrealized_pct or 0
            }
        }

    def get_recent_closes(self, days: int = 7) -> List[Dict]:
        """Get recently closed positions"""
        if not self.enabled:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)
        cursor.execute("""
            SELECT ticker, entry_price, exit_price, profit_loss, return_pct,
                   days_held, exit_reason, exit_date
            FROM paper_trades
            WHERE status = 'closed' AND exit_date >= ?
            ORDER BY exit_date DESC
            LIMIT 10
        """, (cutoff_date,))

        rows = cursor.fetchall()
        conn.close()

        return [{
            'ticker': row[0],
            'entry_price': row[1],
            'exit_price': row[2],
            'profit_loss': row[3],
            'return_pct': row[4],
            'days_held': row[5],
            'exit_reason': row[6],
            'exit_date': row[7]
        } for row in rows]

    def get_open_positions(self) -> List[Dict]:
        """Get all currently open positions with latest snapshots"""
        if not self.enabled:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pt.ticker, pt.entry_date, pt.entry_price, pt.shares,
                pt.position_size, pt.conviction,
                s.current_price, s.unrealized_pnl, s.unrealized_pct,
                pt.stop_loss, pt.target_price
            FROM paper_trades pt
            LEFT JOIN (
                SELECT trade_id, current_price, unrealized_pnl, unrealized_pct
                FROM paper_trade_snapshots
                WHERE (trade_id, snapshot_date) IN (
                    SELECT trade_id, MAX(snapshot_date)
                    FROM paper_trade_snapshots
                    GROUP BY trade_id
                )
            ) s ON pt.id = s.trade_id
            WHERE pt.status = 'open'
            ORDER BY pt.entry_date DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        positions = []
        for row in rows:
            entry_date = datetime.fromisoformat(row[1])
            days_held = (datetime.now() - entry_date).days

            positions.append({
                'ticker': row[0],
                'entry_date': row[1],
                'entry_price': row[2],
                'shares': row[3],
                'position_size': row[4],
                'conviction': row[5],
                'current_price': row[6],
                'unrealized_pnl': row[7],
                'unrealized_pct': row[8],
                'stop_loss': row[9],
                'target_price': row[10],
                'days_held': days_held
            })

        return positions
