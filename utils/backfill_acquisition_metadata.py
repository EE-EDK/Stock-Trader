"""
@file backfill_acquisition_metadata.py
@brief One-time backfill of row_grain and acquisition_channel on existing
       insider rows, using the price_bars spine to test each Form 4 fill.
@details New rows are classified at collection time by the patched
         src/collectors/openinsider.py. Rows already in the table predate that
         change and carry NULLs, which evaluate_cluster reads as 'unverified'.
         This script classifies them from the bars already stored.

         acquisition_code cannot be backfilled: the collector flattened
         OpenInsider's qualified trade-type string to 'P' and discarded the
         original before it ever reached the database. Historical rows keep a
         NULL code and are classified on the bar-range test alone. Only rows
         collected after the collector patch will carry a code.
@usage python utils/backfill_acquisition_metadata.py           # dry run, prints report
       python utils/backfill_acquisition_metadata.py --apply   # writes changes
@version 1.0.0
@date 2026-08-23
@see src/analysis/insider_grain.py
"""

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis.insider_grain import (  # noqa: E402
    CHANNEL_OFF_MARKET,
    CHANNEL_PRICE_ANOMALY,
    classify_channel,
    classify_grain,
)

DB_DEFAULT = 'data/sentiment.db'


def backfill(db_path: str, apply: bool) -> dict:
    """
    @brief Classify every insider row's grain and acquisition channel.
    @param db_path Path to sentiment.db
    @param apply False = report only; True = write
    @return Summary counts keyed by grain and channel
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cols = {r[1] for r in conn.execute("PRAGMA table_info(insiders)")}
    missing = {'row_grain', 'acquisition_code', 'acquisition_channel'} - cols
    if missing:
        conn.close()
        raise SystemExit(
            f"ERROR: insiders is missing {sorted(missing)}. "
            "Run the pipeline once so Database.initialize() adds the columns.")

    rows = conn.execute("""
        SELECT i.id, i.ticker, i.price, i.is_cluster_buy, i.acquisition_code,
               i.insider_title, substr(i.trade_date, 1, 10) AS day,
               b.low AS bar_low, b.high AS bar_high
        FROM insiders i
        LEFT JOIN price_bars b
               ON b.ticker = i.ticker AND b.date = substr(i.trade_date, 1, 10)
    """).fetchall()

    grains, channels, flagged = Counter(), Counter(), []
    updates = []
    for r in rows:
        grain = classify_grain(r['is_cluster_buy'])
        channel = classify_channel(grain, r['price'], r['bar_low'], r['bar_high'],
                                   r['acquisition_code'])
        grains[grain] += 1
        channels[channel] += 1
        if channel in (CHANNEL_OFF_MARKET, CHANNEL_PRICE_ANOMALY):
            flagged.append((r['ticker'], r['day'], r['price'], r['bar_low'],
                            r['bar_high'], channel, r['insider_title'] or ''))
        updates.append((grain, channel, r['id']))

    if apply:
        conn.executemany(
            "UPDATE insiders SET row_grain = ?, acquisition_channel = ? WHERE id = ?",
            updates)
        conn.commit()

    conn.close()
    return {'rows': len(rows), 'grains': dict(grains), 'channels': dict(channels),
            'flagged': flagged}


def main():
    parser = argparse.ArgumentParser(
        description='Backfill insider row grain and acquisition channel')
    parser.add_argument('--db', default=DB_DEFAULT, help='Path to sentiment.db')
    parser.add_argument('--apply', action='store_true',
                        help='Write changes (default: dry run)')
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"ERROR: database not found at {args.db}")
        return 1

    report = backfill(args.db, args.apply)
    mode = 'APPLIED' if args.apply else 'DRY RUN (no changes written)'
    print(f"=== backfill_acquisition_metadata — {mode} ===")
    print(f"  rows        {report['rows']}")
    print(f"  grains      {report['grains']}")
    print(f"  channels    {report['channels']}")
    if report['flagged']:
        print(f"\n  rows the open market did not price ({len(report['flagged'])}):")
        print(f"    {'ticker':7}{'date':12}{'paid':>10}{'low':>9}{'high':>9}  "
              f"{'channel':22} title")
        for t, d, px, lo, hi, ch, ttl in sorted(report['flagged']):
            lo_s = f"{lo:.2f}" if lo is not None else '-'
            hi_s = f"{hi:.2f}" if hi is not None else '-'
            print(f"    {t:7}{str(d):12}{px:>10}{lo_s:>9}{hi_s:>9}  {ch:22} {ttl[:24]}")
    if not args.apply:
        print("\n  Re-run with --apply to write.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
