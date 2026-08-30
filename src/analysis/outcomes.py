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
        ten_day = None  # type: Optional[tuple]
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
