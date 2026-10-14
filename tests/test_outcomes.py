"""
@file test_outcomes.py
@brief Tests for signal forward-return backfill from price_bars.
"""

import pytest
from src.database.models import Database
from src.analysis.outcomes import update_signal_outcomes


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "t.db"))
    d.initialize()
    yield d
    d.close()


def _seed_signal(db, ticker, created_at, price):
    db.connect().execute(
        "INSERT INTO signals (ticker, signal_type, conviction_score, price_at_signal, created_at) "
        "VALUES (?, 'insider_cluster', 50, ?, ?)", (ticker, price, created_at))
    db.connect().commit()


def _seed_bars(db, ticker, start_close, n):
    # n consecutive weekday bars, close rising 1% per bar from start_close
    from datetime import date, timedelta
    bars, d = [], date(2026, 6, 1)
    close = start_close
    while len(bars) < n:
        if d.weekday() < 5:
            bars.append({'ticker': ticker, 'date': d.isoformat(), 'open': close,
                         'high': close * 1.01, 'low': close * 0.99,
                         'close': round(close, 4), 'volume': 1})
            close *= 1.01
        d += timedelta(days=1)
    db.insert_price_bars(bars)
    return bars


def test_full_horizons_filled(db):
    bars = _seed_bars(db, 'WIN', 100.0, 40)
    _seed_signal(db, 'WIN', bars[0]['date'] + ' 12:00:00', 100.0)
    assert update_signal_outcomes(db) == 1
    row = db.connect().execute(
        "SELECT fwd_return_5d, fwd_return_10d, fwd_return_30d, outcome_pct, outcome_date "
        "FROM signals").fetchone()
    # +5 trading days at 1%/bar compounding ~ +5.1%
    assert 4.5 < row[0] < 5.6 and 9.0 < row[1] < 11.5 and 33.0 < row[2] < 36.5
    assert row[3] == row[1]                       # outcome_pct mirrors the 10d point
    assert row[4] is not None


def test_partial_horizons_fill_incrementally(db):
    bars = _seed_bars(db, 'NEW', 100.0, 7)       # only 7 bars: 5d fills, 10d/30d don't
    _seed_signal(db, 'NEW', bars[0]['date'] + ' 12:00:00', 100.0)
    update_signal_outcomes(db)
    row = db.connect().execute(
        "SELECT fwd_return_5d, fwd_return_10d, fwd_return_30d FROM signals").fetchone()
    assert row[0] is not None and row[1] is None and row[2] is None


def test_no_bars_no_crash(db):
    _seed_signal(db, 'GHOST', '2026-06-01 12:00:00', 10.0)
    assert update_signal_outcomes(db) == 0


def test_completed_signals_skipped(db):
    bars = _seed_bars(db, 'DONE', 100.0, 40)
    _seed_signal(db, 'DONE', bars[0]['date'] + ' 12:00:00', 100.0)
    update_signal_outcomes(db)
    assert update_signal_outcomes(db) == 0        # nothing left to fill
