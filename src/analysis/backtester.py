"""
@file backtester.py
@brief Backtesting module for signal validation
@details Backtests trading signals against historical data to validate strategy performance
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """
    @brief Represents a single backtested trade
    """
    ticker: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    shares: int
    conviction: int
    signal_types: List[str]
    exit_reason: str  # 'stop_loss', 'take_profit', 'time_limit'
    profit_loss: float
    return_pct: float
    days_held: int


@dataclass
class BacktestResults:
    """
    @brief Contains complete backtest results
    """
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return_pct: float
    total_profit_loss: float
    avg_return_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    best_trade_pct: float
    worst_trade_pct: float
    avg_days_held: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[BacktestTrade]
    benchmark_return_pct: float  # Buy-and-hold SPY
    alpha: float  # Excess return vs benchmark


class Backtester:
    """
    @brief Backtests trading signals against historical price data
    @details Simulates trading based on historical signals to validate strategy
    """

    def __init__(self, db_path: str, config: Dict):
        """
        @brief Initialize backtester
        @param db_path Path to SQLite database
        @param config Configuration dictionary
        """
        self.db_path = db_path
        self.config = config

        # Get backtesting parameters from config
        backtest_config = config.get('backtesting', {})
        self.initial_capital = backtest_config.get('initial_capital', 10000)
        self.position_size = backtest_config.get('position_size', 1000)
        self.max_positions = backtest_config.get('max_positions', 10)
        self.stop_loss_pct = backtest_config.get('stop_loss_pct', -10)
        self.take_profit_pct = backtest_config.get('take_profit_pct', 20)
        self.hold_days = backtest_config.get('hold_days', 30)
        self.min_conviction = backtest_config.get('min_conviction', 60)

        # Use conviction-weighted sizing (same as paper trading)
        self.use_conviction_weighted = backtest_config.get('conviction_weighted', True)

    def calculate_position_size(self, conviction: int) -> float:
        """
        @brief Calculate position size based on conviction
        @param conviction Signal conviction score (0-100)
        @return Position size in dollars
        """
        if not self.use_conviction_weighted:
            return self.position_size

        # Same formula as paper trading: 1x base at conviction 50, 2x at conviction 100
        multiplier = 1.0 + ((conviction - 50) / 50)
        return self.position_size * multiplier

    def get_historical_price(self, ticker: str, date: datetime, offset_days: int = 0) -> Optional[float]:
        """
        @brief Get historical price for a ticker on a specific date
        @param ticker Stock ticker symbol
        @param date Date to get price for
        @param offset_days Days to offset (for looking ahead)
        @return Price, or None if not found
        """
        target_date = date + timedelta(days=offset_days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get price from database (within 7 days of target date)
        cursor.execute("""
            SELECT price
            FROM prices
            WHERE ticker = ?
            AND DATE(collected_at) BETWEEN DATE(?) AND DATE(?, '+7 days')
            ORDER BY ABS(JULIANDAY(collected_at) - JULIANDAY(?))
            LIMIT 1
        """, (ticker, target_date, target_date, target_date))

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    def simulate_trade(self, ticker: str, entry_date: datetime, entry_price: float,
                      conviction: int, signal_types: List[str]) -> Optional[BacktestTrade]:
        """
        @brief Simulate a single trade from entry to exit
        @param ticker Stock ticker
        @param entry_date Date of trade entry
        @param entry_price Entry price
        @param conviction Signal conviction score
        @param signal_types List of signal types that triggered
        @return BacktestTrade object, or None if trade couldn't be executed
        """
        if entry_price is None or entry_price <= 0:
            return None

        # Calculate position size and shares
        position_size = self.calculate_position_size(conviction)
        shares = int(position_size / entry_price)

        if shares == 0:
            return None

        # Calculate exit prices
        stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
        target_price = entry_price * (1 + self.take_profit_pct / 100)

        # Simulate daily price checks
        exit_date = None
        exit_price = None
        exit_reason = None

        for day in range(1, self.hold_days + 1):
            current_date = entry_date + timedelta(days=day)
            current_price = self.get_historical_price(ticker, current_date)

            if current_price is None:
                continue

            # Check exit conditions
            if current_price <= stop_loss:
                exit_date = current_date
                exit_price = current_price
                exit_reason = 'stop_loss'
                break
            elif current_price >= target_price:
                exit_date = current_date
                exit_price = current_price
                exit_reason = 'take_profit'
                break

        # If no exit condition hit, exit at time limit
        if exit_date is None:
            exit_date = entry_date + timedelta(days=self.hold_days)
            exit_price = self.get_historical_price(ticker, exit_date)
            exit_reason = 'time_limit'

        if exit_price is None:
            return None

        # Calculate P/L
        profit_loss = (exit_price - entry_price) * shares
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        days_held = (exit_date - entry_date).days

        return BacktestTrade(
            ticker=ticker,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=exit_date,
            exit_price=exit_price,
            shares=shares,
            conviction=conviction,
            signal_types=signal_types,
            exit_reason=exit_reason,
            profit_loss=profit_loss,
            return_pct=return_pct,
            days_held=days_held
        )

    def get_historical_signals(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        @brief Get historical signals from database
        @param start_date Start of backtest period
        @param end_date End of backtest period
        @return List of signal dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ticker, conviction_score, triggers, price_at_signal, created_at
            FROM signals
            WHERE DATE(created_at) BETWEEN DATE(?) AND DATE(?)
            AND conviction_score >= ?
            ORDER BY created_at ASC
        """, (start_date, end_date, self.min_conviction))

        signals = []
        for row in cursor.fetchall():
            try:
                triggers = json.loads(row[2]) if row[2] else []
            except:
                triggers = []

            signals.append({
                'ticker': row[0],
                'conviction': int(row[1]),
                'triggers': triggers,
                'price': row[3],
                'date': datetime.fromisoformat(row[4])
            })

        conn.close()
        logger.info(f"Found {len(signals)} historical signals from {start_date} to {end_date}")
        return signals

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        @brief Calculate Sharpe ratio
        @param returns List of returns (as decimals, not percentages)
        @param risk_free_rate Annual risk-free rate (default 2%)
        @return Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        import numpy as np

        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate

        if np.std(excess_returns) == 0:
            return 0.0

        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return sharpe * np.sqrt(252)  # Annualized

    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        @brief Calculate maximum drawdown
        @param equity_curve List of portfolio values over time
        @return Max drawdown as percentage
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = ((peak - value) / peak) * 100
            max_dd = max(max_dd, drawdown)

        return max_dd

    def run_backtest(self, start_date: datetime, end_date: datetime) -> BacktestResults:
        """
        @brief Run complete backtest over date range
        @param start_date Start of backtest period
        @param end_date End of backtest period
        @return BacktestResults object with complete analysis
        """
        logger.info(f"Running backtest from {start_date} to {end_date}")

        # Get historical signals
        signals = self.get_historical_signals(start_date, end_date)

        if not signals:
            logger.warning("No signals found in backtest period")
            return self._empty_results(start_date, end_date)

        # Simulate all trades
        trades = []
        open_positions = 0

        for signal in signals:
            # Respect max positions limit
            if open_positions >= self.max_positions:
                continue

            trade = self.simulate_trade(
                ticker=signal['ticker'],
                entry_date=signal['date'],
                entry_price=signal['price'],
                conviction=signal['conviction'],
                signal_types=signal['triggers']
            )

            if trade:
                trades.append(trade)
                open_positions += 1

                # Decrement when trade closes (simplified - assumes sequential)
                if trade.exit_date <= end_date:
                    open_positions -= 1

        if not trades:
            logger.warning("No trades could be executed")
            return self._empty_results(start_date, end_date)

        # Calculate metrics
        winning_trades = [t for t in trades if t.profit_loss > 0]
        losing_trades = [t for t in trades if t.profit_loss < 0]

        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
        total_profit_loss = sum(t.profit_loss for t in trades)
        total_return_pct = (total_profit_loss / self.initial_capital) * 100

        avg_return_pct = sum(t.return_pct for t in trades) / len(trades) if trades else 0.0
        avg_win_pct = sum(t.return_pct for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss_pct = sum(t.return_pct for t in losing_trades) / len(losing_trades) if losing_trades else 0.0

        best_trade_pct = max((t.return_pct for t in trades), default=0.0)
        worst_trade_pct = min((t.return_pct for t in trades), default=0.0)
        avg_days_held = sum(t.days_held for t in trades) / len(trades) if trades else 0.0

        # Calculate equity curve for drawdown
        equity_curve = [self.initial_capital]
        for trade in trades:
            equity_curve.append(equity_curve[-1] + trade.profit_loss)

        max_drawdown = self.calculate_max_drawdown(equity_curve)

        # Calculate Sharpe ratio
        returns = [t.return_pct / 100 for t in trades]  # Convert to decimal
        sharpe_ratio = self.calculate_sharpe_ratio(returns)

        # Benchmark (SPY buy-and-hold) - simplified
        benchmark_return = self._calculate_benchmark_return(start_date, end_date)
        alpha = total_return_pct - benchmark_return

        results = BacktestResults(
            start_date=start_date,
            end_date=end_date,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_return_pct=total_return_pct,
            total_profit_loss=total_profit_loss,
            avg_return_pct=avg_return_pct,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            best_trade_pct=best_trade_pct,
            worst_trade_pct=worst_trade_pct,
            avg_days_held=avg_days_held,
            max_drawdown_pct=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            benchmark_return_pct=benchmark_return,
            alpha=alpha
        )

        logger.info(f"Backtest complete: {len(trades)} trades, {win_rate:.1f}% win rate, {total_return_pct:.2f}% total return")
        return results

    def _empty_results(self, start_date: datetime, end_date: datetime) -> BacktestResults:
        """
        @brief Create empty results object
        """
        return BacktestResults(
            start_date=start_date,
            end_date=end_date,
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

    def _calculate_benchmark_return(self, start_date: datetime, end_date: datetime) -> float:
        """
        @brief Calculate benchmark (SPY) buy-and-hold return
        @param start_date Start date
        @param end_date End date
        @return Total return percentage
        """
        start_price = self.get_historical_price('SPY', start_date)
        end_price = self.get_historical_price('SPY', end_date)

        if start_price and end_price and start_price > 0:
            return ((end_price - start_price) / start_price) * 100
        else:
            return 0.0

    def generate_report(self, results: BacktestResults) -> str:
        """
        @brief Generate text report of backtest results
        @param results BacktestResults object
        @return Formatted text report
        """
        report = []
        report.append("=" * 70)
        report.append("BACKTEST RESULTS")
        report.append("=" * 70)
        report.append(f"Period: {results.start_date.strftime('%Y-%m-%d')} to {results.end_date.strftime('%Y-%m-%d')}")
        report.append(f"Initial Capital: ${self.initial_capital:,.2f}")
        report.append("")

        report.append("TRADE STATISTICS:")
        report.append("-" * 70)
        report.append(f"  Total Trades:        {results.total_trades}")
        report.append(f"  Winning Trades:      {results.winning_trades} ({results.win_rate:.1f}%)")
        report.append(f"  Losing Trades:       {results.losing_trades}")
        report.append(f"  Avg Hold Time:       {results.avg_days_held:.1f} days")
        report.append("")

        report.append("PERFORMANCE METRICS:")
        report.append("-" * 70)
        report.append(f"  Total Return:        {results.total_return_pct:+.2f}%")
        report.append(f"  Total P/L:           ${results.total_profit_loss:+,.2f}")
        report.append(f"  Avg Return/Trade:    {results.avg_return_pct:+.2f}%")
        report.append(f"  Avg Win:             {results.avg_win_pct:+.2f}%")
        report.append(f"  Avg Loss:            {results.avg_loss_pct:+.2f}%")
        report.append(f"  Best Trade:          {results.best_trade_pct:+.2f}%")
        report.append(f"  Worst Trade:         {results.worst_trade_pct:+.2f}%")
        report.append("")

        report.append("RISK METRICS:")
        report.append("-" * 70)
        report.append(f"  Max Drawdown:        {results.max_drawdown_pct:.2f}%")
        report.append(f"  Sharpe Ratio:        {results.sharpe_ratio:.2f}")
        report.append("")

        report.append("BENCHMARK COMPARISON:")
        report.append("-" * 70)
        report.append(f"  SPY Buy & Hold:      {results.benchmark_return_pct:+.2f}%")
        report.append(f"  Alpha (Excess):      {results.alpha:+.2f}%")
        report.append("")

        if results.total_trades > 0:
            report.append("TOP 5 WINNING TRADES:")
            report.append("-" * 70)
            winning_sorted = sorted([t for t in results.trades if t.profit_loss > 0],
                                   key=lambda t: t.return_pct, reverse=True)
            for i, trade in enumerate(winning_sorted[:5], 1):
                report.append(f"  {i}. {trade.ticker}: {trade.return_pct:+.2f}% "
                            f"(${trade.profit_loss:+,.2f}) - {trade.exit_reason}")

            report.append("")
            report.append("TOP 5 LOSING TRADES:")
            report.append("-" * 70)
            losing_sorted = sorted([t for t in results.trades if t.profit_loss < 0],
                                  key=lambda t: t.return_pct)
            for i, trade in enumerate(losing_sorted[:5], 1):
                report.append(f"  {i}. {trade.ticker}: {trade.return_pct:+.2f}% "
                            f"(${trade.profit_loss:+,.2f}) - {trade.exit_reason}")

        report.append("=" * 70)

        return "\n".join(report)
