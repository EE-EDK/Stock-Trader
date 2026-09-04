"""
@file journal.py
@brief Trade lineage: links a decision and its rationale to what actually happened.
@details Closes the open TODO in CLAUDE.md — "record the real fill back against
         the same signal_id so real results, paper results, and backtest results
         stay comparable in one lineage."

         Before this, a live trade existed only in a chat transcript and a prose
         document. `paper_trades` has no broker order id, no rationale, and no
         link to a live fill, so nothing could be scored after the fact: you
         could not ask "when I acted on trigger X at conviction Y, what happened,
         and was my stated expectation any good?"

         Lives in SQLite, not a flat file, per the project's data-integrity rule
         (AGENTS.md §Project Identity). Table `live_trades`, keyed on
         broker_order_id, joinable to `signals` via signal_id.

         The `expected` column is what makes this a learning loop rather than a
         logbook. Record the prediction BEFORE the outcome is known, then score
         calibration later. A journal without a prior is just history.

@usage  python docs/memory/journal.py open --ticker REFI --side buy --qty 18 \\
            --order-id 6a8c... --rationale "..." --expected '{"...": ...}'
        python docs/memory/journal.py close --order-id 6a8c... \\
            --exit-price 10.55 --exit-reason manual_exit
        python docs/memory/journal.py report
        python docs/memory/journal.py schema        # create/migrate the table

@version 1.0.0
@date 2026-08-29
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from typing import Any, Dict, Optional

DB_DEFAULT = 'data/sentiment.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS live_trades (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id             INTEGER,          -- FK signals.id; NULL if discretionary
    broker_order_id       TEXT UNIQUE,      -- the audit anchor
    venue                 TEXT DEFAULT 'robinhood',
    account               TEXT,             -- masked, last 4 only
    ticker                TEXT NOT NULL,
    side                  TEXT NOT NULL,    -- buy | sell
    order_type            TEXT,             -- limit | market | stop_market | stop_limit
    quantity              REAL,
    limit_price           REAL,
    stop_price            REAL,
    placed_at             TIMESTAMP,
    filled_at             TIMESTAMP,
    fill_price            REAL,
    fees                  REAL DEFAULT 0,
    rationale             TEXT,             -- why THIS one
    filters_passed        TEXT,             -- JSON: gates it cleared
    rejected_alternatives TEXT,             -- JSON: what else was considered, and why not
    expected              TEXT,             -- JSON: the prior, recorded before the outcome
    exit_order_id         TEXT,
    exit_at               TIMESTAMP,
    exit_price            REAL,
    exit_reason           TEXT,             -- stop | target | time_limit | manual_exit
    realized_pnl          REAL,
    realized_pct          REAL,
    status                TEXT DEFAULT 'open',   -- open | closed | cancelled
    notes                 TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_live_trades_signal ON live_trades(signal_id);
CREATE INDEX IF NOT EXISTS idx_live_trades_ticker ON live_trades(ticker, placed_at);
"""


def _conn(db_path: str) -> sqlite3.Connection:
    """@brief Open the database with row access by name."""
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def ensure_schema(db_path: str) -> None:
    """
    @brief Create the live_trades table and indexes if absent (idempotent).
    @param db_path Path to sentiment.db
    """
    with _conn(db_path) as c:
        c.executescript(SCHEMA)


def open_trade(db_path: str, override_reason: Optional[str] = None,
               **kw: Any) -> int:
    """
    @brief Record an entry at the moment it is placed, with its rationale.
    @param db_path Path to sentiment.db
    @param override_reason Required if the ledger blocks this action. Recorded.
    @param kw Column values; broker_order_id and ticker are required
    @return Row id of the journal entry
    @pre Record this BEFORE the outcome is known — the value is in the prior.
    @throws RuntimeError if guard.py blocks and no override_reason is supplied
    @details Journalling is the chokepoint: this is the one function every live
             trade must pass through, so the ledger gate lives here rather than
             scattered across call sites. A block is NOT absolute — you may
             override — but the override reason is written into the row, so
             "we traded anyway because X" becomes part of the record instead of
             an undocumented exception.
    """
    from guard import check                       # local import: optional dep
    targets = ['action:live_trade']
    if kw.get('side'):
        targets.append(f"action:{kw['side']}")
    verdict = check(*targets)
    if verdict.blocked:
        if not override_reason:
            raise RuntimeError(
                "Ledger blocks this trade. Supply override_reason to proceed "
                "and record why.\n" + verdict.explain())
        kw['notes'] = ((kw.get('notes') or '') +
                       f" | LEDGER OVERRIDE: {override_reason} | blocked by: " +
                       ', '.join(f"#{e['id']}" for e in verdict.blocking))
    ensure_schema(db_path)
    for j in ('filters_passed', 'rejected_alternatives', 'expected'):
        if isinstance(kw.get(j), (dict, list)):
            kw[j] = json.dumps(kw[j])
    cols = ', '.join(kw)
    marks = ', '.join('?' * len(kw))
    with _conn(db_path) as c:
        cur = c.execute(f"INSERT OR IGNORE INTO live_trades ({cols}) VALUES ({marks})",
                        list(kw.values()))
        return cur.lastrowid


def close_trade(db_path: str, broker_order_id: str, exit_price: float,
                exit_reason: str, exit_order_id: Optional[str] = None,
                exit_at: Optional[str] = None) -> Dict[str, Any]:
    """
    @brief Record the exit and compute realised P&L against the actual fill.
    @param db_path Path to sentiment.db
    @param broker_order_id The ENTRY order id this exit closes
    @param exit_price Realised exit price per share
    @param exit_reason stop | target | time_limit | manual_exit
    @return Summary dict of the closed trade
    @throws SystemExit if the entry order is not journalled
    """
    ensure_schema(db_path)
    with _conn(db_path) as c:
        row = c.execute("SELECT * FROM live_trades WHERE broker_order_id = ?",
                        (broker_order_id,)).fetchone()
        if row is None:
            raise SystemExit(f"ERROR: no journal entry for order {broker_order_id}")
        qty = row['quantity'] or 0
        entry = row['fill_price'] or 0
        pnl = (exit_price - entry) * qty - (row['fees'] or 0)
        pct = ((exit_price / entry) - 1) * 100 if entry else None
        c.execute("""UPDATE live_trades SET exit_order_id=?, exit_at=?, exit_price=?,
                     exit_reason=?, realized_pnl=?, realized_pct=?, status='closed',
                     updated_at=CURRENT_TIMESTAMP WHERE broker_order_id=?""",
                  (exit_order_id, exit_at or datetime.now().isoformat(), exit_price,
                   exit_reason, round(pnl, 4), round(pct, 4) if pct is not None else None,
                   broker_order_id))
        return {'ticker': row['ticker'], 'quantity': qty, 'entry': entry,
                'exit': exit_price, 'pnl': round(pnl, 2),
                'pct': round(pct, 2) if pct is not None else None}


def report(db_path: str) -> int:
    """
    @brief Print the live trade ledger and, where available, calibration.
    @param db_path Path to sentiment.db
    @return Process exit code
    """
    ensure_schema(db_path)
    with _conn(db_path) as c:
        rows = c.execute("SELECT * FROM live_trades ORDER BY placed_at").fetchall()
    if not rows:
        print("No live trades journalled.")
        return 0
    print(f"{'id':<4}{'ticker':<8}{'side':<6}{'qty':>6}{'entry':>9}{'exit':>9}"
          f"{'P&L':>9}{'pct':>8}  {'status':<9} signal")
    for r in rows:
        print(f"{r['id']:<4}{r['ticker']:<8}{r['side']:<6}{r['quantity'] or 0:>6.0f}"
              f"{r['fill_price'] or 0:>9.2f}{r['exit_price'] or 0:>9.2f}"
              f"{r['realized_pnl'] or 0:>9.2f}{r['realized_pct'] or 0:>7.2f}%"
              f"  {r['status']:<9} {r['signal_id'] if r['signal_id'] else '-'}")
    closed = [r for r in rows if r['status'] == 'closed']
    if closed:
        tot = sum(r['realized_pnl'] or 0 for r in closed)
        wins = sum(1 for r in closed if (r['realized_pnl'] or 0) > 0)
        print(f"\n{len(closed)} closed · total ${tot:+.2f} · {wins}/{len(closed)} profitable")
    print("\n--- stated expectations vs outcome (calibration) ---")
    for r in rows:
        if not r['expected']:
            continue
        exp = json.loads(r['expected'])
        got = (f"{r['realized_pct']:+.2f}%" if r['realized_pct'] is not None else 'open')
        print(f"  {r['ticker']}: expected {exp} -> actual {got}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description='Live trade lineage journal')
    p.add_argument('--db', default=DB_DEFAULT)
    sub = p.add_subparsers(dest='cmd', required=True)

    o = sub.add_parser('open', help='journal an entry')
    for f in ('ticker', 'side', 'order-id', 'rationale', 'order-type', 'account',
              'placed-at', 'filled-at', 'expected', 'filters-passed', 'notes'):
        o.add_argument(f'--{f}', default=None)
    o.add_argument('--qty', type=float, default=None)
    o.add_argument('--fill-price', type=float, default=None)
    o.add_argument('--limit-price', type=float, default=None)
    o.add_argument('--signal-id', type=int, default=None)
    o.add_argument('--override-reason', default=None,
                   help='required if the ledger blocks this action; it is recorded')
    o.set_defaults(func=lambda a: _cli_open(a))

    cl = sub.add_parser('close', help='journal an exit')
    cl.add_argument('--order-id', required=True)
    cl.add_argument('--exit-price', type=float, required=True)
    cl.add_argument('--exit-reason', required=True)
    cl.add_argument('--exit-order-id', default=None)
    cl.set_defaults(func=lambda a: (print(close_trade(
        a.db, a.order_id, a.exit_price, a.exit_reason, a.exit_order_id)), 0)[1])

    r = sub.add_parser('report', help='print the ledger')
    r.set_defaults(func=lambda a: report(a.db))

    s = sub.add_parser('schema', help='create/migrate the table')
    s.set_defaults(func=lambda a: (ensure_schema(a.db), print('live_trades ready'), 0)[2])

    args = p.parse_args()
    return args.func(args)


def _cli_open(a) -> int:
    kw = {k: v for k, v in {
        'ticker': a.ticker, 'side': a.side, 'broker_order_id': a.order_id,
        'order_type': a.order_type, 'quantity': a.qty, 'fill_price': a.fill_price,
        'limit_price': a.limit_price, 'account': a.account, 'placed_at': a.placed_at,
        'filled_at': a.filled_at, 'rationale': a.rationale, 'expected': a.expected,
        'filters_passed': a.filters_passed, 'signal_id': a.signal_id, 'notes': a.notes,
    }.items() if v is not None}
    rid = open_trade(a.db, override_reason=a.override_reason, **kw)
    print(f"journalled trade #{rid}: {a.side} {a.qty} {a.ticker}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
