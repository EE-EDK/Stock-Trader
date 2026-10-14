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
