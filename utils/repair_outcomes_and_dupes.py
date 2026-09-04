"""
@file repair_outcomes_and_dupes.py
@brief One-time repair: collapse duplicate insider/signal rows, clear forward
       returns computed on a mixed adjustment basis, and install the UNIQUE
       indexes that stop both defects recurring.
@details Three defects found 2026-08-23:
         1. `insiders` had no UNIQUE constraint and used a plain INSERT.
            OpenInsider's cluster / CEO-CFO / purchase views overlap, so each
            trade landed several times per run and again on every later run:
            3,400 rows -> 753 distinct (78% duplicated). The insider_cluster
            trigger counts rows, so a single CEO purchase read as a 7-buyer
            cluster (INTC: one $10.0M buy reported as "7 insiders bought
            $69,999,895").
         2. `signals` had UNIQUE(ticker, created_at), but created_at carries
            microseconds, so every run of a given day inserted a fresh row.
            67 outcome-bearing rows collapsed to 55 distinct.
         3. `outcomes.py` used the live, unadjusted `price_at_signal` as the
            baseline against retroactively split-adjusted bars, fabricating
            returns (SOXS 2026-05-22 recorded +706.78% at 5d). Every stored
            forward return is therefore suspect and is cleared for recompute
            by the fixed src/analysis/outcomes.py.
@usage python utils/repair_outcomes_and_dupes.py           # dry run, prints report
       python utils/repair_outcomes_and_dupes.py --apply   # writes changes
@warning --apply removes duplicate rows. Per the project's historical-
         preservation rule every removed row is first written verbatim to
         archive/repair_<timestamp>/removed_*.json.
@version 1.0.0
@date 2026-08-23
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB_DEFAULT = 'data/sentiment.db'

INSIDER_KEY = ("ticker, trade_date, COALESCE(insider_name,''), "
               "COALESCE(insider_title,''), trade_type, shares, price")
SIGNAL_KEY = "ticker, signal_type, substr(created_at,1,10)"

OUTCOME_COLUMNS = ('fwd_return_5d', 'fwd_return_10d', 'fwd_return_30d',
                   'outcome_price', 'outcome_date', 'outcome_pct')


def _doomed_ids(conn, table: str, key: str):
    """@brief Ids that are not the lowest id within their natural-key group."""
    rows = conn.execute(
        f"SELECT id FROM {table} WHERE id NOT IN "
        f"(SELECT MIN(id) FROM {table} GROUP BY {key})").fetchall()
    return [r[0] for r in rows]


def _dump(conn, table: str, ids, path: Path):
    """@brief Write full rows verbatim to JSON before removal."""
    if not ids:
        return
    conn.row_factory = sqlite3.Row
    marks = ','.join('?' * len(ids))
    rows = conn.execute(f"SELECT * FROM {table} WHERE id IN ({marks})", ids).fetchall()
    path.write_text(json.dumps([dict(r) for r in rows], indent=1, default=str),
                    encoding='utf-8')
    conn.row_factory = None


def repair(db_path: str, apply: bool) -> dict:
    """
    @brief Run the repair.
    @param db_path Path to sentiment.db
    @param apply False = report only; True = write
    @return Summary dict of counts
    """
    conn = sqlite3.connect(db_path)
    report = {}

    ins_dupes = _doomed_ids(conn, 'insiders', INSIDER_KEY)
    sig_dupes = _doomed_ids(conn, 'signals', SIGNAL_KEY)
    stored_outcomes = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE outcome_pct IS NOT NULL").fetchone()[0]

    report['insiders_total'] = conn.execute("SELECT COUNT(*) FROM insiders").fetchone()[0]
    report['insiders_duplicate'] = len(ins_dupes)
    report['signals_total'] = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    report['signals_duplicate'] = len(sig_dupes)
    report['outcomes_cleared'] = stored_outcomes

    if not apply:
        conn.close()
        return report

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive = Path('archive') / f'repair_{stamp}'
    archive.mkdir(parents=True, exist_ok=True)
    _dump(conn, 'insiders', ins_dupes, archive / 'removed_insiders.json')
    _dump(conn, 'signals', sig_dupes, archive / 'removed_signals.json')
    report['archive'] = str(archive)

    cur = conn.cursor()
    for table, ids in (('insiders', ins_dupes), ('signals', sig_dupes)):
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            cur.execute(f"DELETE FROM {table} WHERE id IN ({','.join('?' * len(chunk))})",
                        chunk)

    # Every stored forward return was computed on a mixed adjustment basis.
    # Clear them; the fixed outcomes.py recomputes bar-to-bar on next run.
    cur.execute("UPDATE signals SET " +
                ", ".join(f"{c} = NULL" for c in OUTCOME_COLUMNS))

    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ux_insiders_trade "
                f"ON insiders({INSIDER_KEY})")
    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ux_signals_daily "
                f"ON signals({SIGNAL_KEY})")
    conn.commit()

    report['insiders_remaining'] = conn.execute("SELECT COUNT(*) FROM insiders").fetchone()[0]
    report['signals_remaining'] = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    report['indexes'] = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name IN ('ux_insiders_trade','ux_signals_daily')").fetchall()]
    conn.close()
    return report


def main():
    parser = argparse.ArgumentParser(
        description='Collapse duplicate insider/signal rows and clear contaminated outcomes')
    parser.add_argument('--db', default=DB_DEFAULT, help='Path to sentiment.db')
    parser.add_argument('--apply', action='store_true', help='Write changes (default: dry run)')
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"ERROR: database not found at {args.db}")
        return 1

    report = repair(args.db, args.apply)
    mode = 'APPLIED' if args.apply else 'DRY RUN (no changes written)'
    print(f"=== repair_outcomes_and_dupes — {mode} ===")
    for k, v in report.items():
        print(f"  {k:22} {v}")
    if not args.apply:
        print("\n  Re-run with --apply to write.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
