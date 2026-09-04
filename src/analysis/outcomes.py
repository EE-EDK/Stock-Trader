"""
@file outcomes.py
@brief Backfill signal forward returns from the price_bars spine.
@details The learning loop: every signal gets +5/+10/+30 trading-day forward
         returns once bars exist, making per-trigger edge measurable.

         Both ends of every return are read from price_bars so the numerator
         and denominator always share one corporate-action adjustment basis.
         `price_at_signal` is captured live and unadjusted; using it as the
         baseline against retroactively split-adjusted bars fabricates returns
         (observed 2026-08-23: SOXS 2026-05-22 recorded +706.78% at 5d,
         SPCX +593.24%, from split adjustment alone).
@version 1.1.0
@date 2026-08-23
@see docs/superpowers/plans/2026-08-19-market-date-spine-spec.md
"""

import logging
from typing import Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

HORIZONS = ((5, 'fwd_return_5d'), (10, 'fwd_return_10d'), (30, 'fwd_return_30d'))

# A single-session close-to-close ratio outside this band is treated as a
# corporate-action discontinuity in the bar series, not a real price move.
# yfinance applies split adjustments retroactively and can leave a stored
# series internally inconsistent across the adjustment boundary; a forward
# return measured across such a boundary is fabricated.
#
# Tradeoff: a genuine single-session move beyond -50% / +100% is rejected too.
# That is deliberate. A NULL outcome is recoverable; a poisoned edge table
# silently mis-weights every downstream conviction score.
SPLIT_RATIO_LOW = 0.5
SPLIT_RATIO_HIGH = 2.0

# price_at_signal is captured live (unadjusted). Disagreement with the
# signal-day bar close beyond this fraction means the series was re-adjusted
# after capture. Logged for visibility; the bar close still wins as baseline.
BASELINE_MISMATCH_TOLERANCE = 0.20


def _split_boundary(bars: Sequence[Tuple[str, float]], upto: int) -> Optional[str]:
    """
    @brief Find a corporate-action discontinuity within bars[0..upto].
    @param bars Ascending (date, close) pairs, non-null closes
    @param upto Highest index that will be read by the caller
    @return Date string of the first offending bar, or None if the window is clean
    @pre bars is sorted ascending by date
    """
    last = min(upto, len(bars) - 1)
    for i in range(1, last + 1):
        prev_close = bars[i - 1][1]
        if not prev_close or prev_close <= 0:
            return bars[i][0]
        ratio = bars[i][1] / prev_close
        if ratio < SPLIT_RATIO_LOW or ratio > SPLIT_RATIO_HIGH:
            return bars[i][0]
    return None


def update_signal_outcomes(db) -> int:
    """
    @brief Fill fwd_return_5d/10d/30d for signals missing them; mirror the
           10-day point into outcome_price/outcome_date/outcome_pct.
    @param db Database instance
    @return Number of signals that received at least one new value
    @warning Horizons whose bar window crosses a split boundary are left NULL
             and logged rather than written with a fabricated value.
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
    skipped_split = 0
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

        # Baseline is ALWAYS the anchor bar close, never price_at_signal:
        # numerator and denominator must share one adjustment basis.
        baseline_date, baseline = bars[0]
        if not baseline or baseline <= 0:
            continue

        if price_at_signal and price_at_signal > 0:
            drift = abs(price_at_signal - baseline) / baseline
            if drift > BASELINE_MISMATCH_TOLERANCE:
                logger.warning(
                    "%s %s: live price_at_signal %.4f vs bar close %.4f "
                    "(%.1f%% apart) - bar series re-adjusted since capture; "
                    "using bar close as baseline",
                    ticker, baseline_date, price_at_signal, baseline, drift * 100)

        sets, params = [], []
        ten_day = None  # type: Optional[tuple]
        for n, column in HORIZONS:
            if existing[column] is not None:
                continue
            if len(bars) <= n:               # bars[0] is the signal day itself
                continue

            boundary = _split_boundary(bars, n)
            if boundary:
                logger.warning(
                    "%s %s: skipping %s - corporate-action discontinuity in "
                    "bar series at %s", ticker, baseline_date, column, boundary)
                skipped_split += 1
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
    if skipped_split:
        logger.warning(
            "Skipped %d horizon(s) crossing a corporate-action boundary", skipped_split)
    return updated
