"""
@file revalidate_paper_trades.py
@brief One-time paper-trade book repair: void duplicates and zero-share rows
       (annotated, never deleted), and re-close historical trades against real
       daily bars via the shared exit engine.
@usage python utils/revalidate_paper_trades.py           # dry run, prints report
       python utils/revalidate_paper_trades.py --apply   # writes changes
"""

import argparse
import contextlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.models import Database
from src.trading.engine import walk_bars

HOLD_DAYS = 30  # matches config paper_trading.hold_days


def find_duplicates(conn) -> List[int]:
    """@brief Ids to void: all but the lowest id per (ticker, entry day)."""
    rows = conn.execute("""
        SELECT id, ticker, substr(entry_date, 1, 10) AS day FROM paper_trades
        WHERE status IN ('open', 'closed') ORDER BY id
    """).fetchall()
    seen, dupes = set(), []
    for trade_id, ticker, day in rows:
        key = (ticker, day)
        if key in seen:
            dupes.append(trade_id)
        else:
            seen.add(key)
    return dupes


def revalidate(db_path: str, apply: bool) -> List[Dict]:
    db = Database(db_path)
    db.initialize()
    report: List[Dict] = []
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        for trade_id in find_duplicates(conn):
            report.append({'id': trade_id, 'action': 'void_duplicate'})
            if apply:
                conn.execute("UPDATE paper_trades SET status='void_duplicate', "
                             "notes=COALESCE(notes,'') || ' [voided: duplicate entry]' WHERE id=?",
                             (trade_id,))

        for (trade_id,) in conn.execute(
                "SELECT id FROM paper_trades WHERE shares = 0 AND status IN ('open','closed')").fetchall():
            report.append({'id': trade_id, 'action': 'void_zero_shares'})
            if apply:
                conn.execute("UPDATE paper_trades SET status='void_zero_shares', "
                             "notes=COALESCE(notes,'') || ' [voided: 0 shares]' WHERE id=?",
                             (trade_id,))
        if apply:
            conn.commit()

        # Re-close surviving closed trades against real bars
        for row in conn.execute("""
                SELECT id, ticker, entry_date, entry_price, shares, stop_loss,
                       target_price, exit_date, exit_price, exit_reason
                FROM paper_trades WHERE status='closed'""").fetchall():
            (trade_id, ticker, entry_date, entry_price, shares,
             stop_loss, target_price, old_date, old_price, old_reason) = row
            bars = db.get_bars_since(ticker, entry_date[:10])
            exit_event = walk_bars(entry_date[:10], entry_price, stop_loss,
                                   target_price, HOLD_DAYS, bars)
            if exit_event is None:
                continue
            delta = {'id': trade_id, 'ticker': ticker, 'action': 'reclose',
                     'old': {'exit_date': old_date, 'exit_price': old_price, 'exit_reason': old_reason},
                     'new': {'exit_date': exit_event.date, 'exit_price': exit_event.price,
                             'exit_reason': exit_event.reason}}
            report.append(delta)
            if apply:
                pnl = (exit_event.price - entry_price) * shares
                pct = ((exit_event.price - entry_price) / entry_price) * 100
                original = json.dumps({'original_exit': {
                    'exit_date': old_date, 'exit_price': old_price, 'exit_reason': old_reason}})
                conn.execute("""UPDATE paper_trades SET exit_date=?, exit_price=?, exit_reason=?,
                    profit_loss=?, return_pct=?, days_held=?, notes=? WHERE id=?""",
                    (exit_event.date, exit_event.price, exit_event.reason,
                     pnl, pct, exit_event.days_held, original, trade_id))
        if apply:
            conn.commit()
    db.close()
    return report


def main():
    parser = argparse.ArgumentParser(description='Repair the paper-trade book against real bars')
    parser.add_argument('--db', default='data/sentiment.db')
    parser.add_argument('--apply', action='store_true', help='Write changes (default: dry run)')
    args = parser.parse_args()
    report = revalidate(args.db, apply=args.apply)
    for entry in report:
        print(json.dumps(entry))
    print(f"\n{'APPLIED' if args.apply else 'DRY RUN'}: {len(report)} actions")


if __name__ == '__main__':
    main()
