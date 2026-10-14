"""
@file test_revalidate.py
@brief Tests for the one-time paper-trade book revalidation utility.
"""

import json
import sqlite3
import contextlib
import pytest
from src.database.models import Database
from src.trading.paper_trading import PaperTradingManager
from utils.revalidate_paper_trades import revalidate


CONFIG = {'paper_trading': {'enabled': True, 'min_conviction': 25,
                            'position_size': 1000, 'max_open_positions': 10,
                            'hold_days': 30, 'stop_loss_pct': -10, 'take_profit_pct': 20}}


@pytest.fixture
def seeded(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.initialize()
    PaperTradingManager(db.db_path, CONFIG)  # creates paper_trades tables
    with contextlib.closing(sqlite3.connect(db.db_path)) as conn:
        # Two duplicates (same ticker, same entry day, minutes apart) + one zero-share
        rows = [
            ('DUP', '2026-06-01T10:00:00', 10.0, 100, 50, '["insider_cluster"]', 1000.0, 9.0, 12.0, 'closed'),
            ('DUP', '2026-06-01T10:05:00', 10.0, 100, 50, '["insider_cluster"]', 1000.0, 9.0, 12.0, 'closed'),
            ('ZRO', '2026-06-01T10:00:00', 700.0, 0, 25, '["news_sentiment_bullish"]', 0.0, 630.0, 840.0, 'closed'),
        ]
        for r in rows:
            conn.execute("""INSERT INTO paper_trades (ticker, entry_date, entry_price, shares,
                conviction, signal_types, position_size, stop_loss, target_price, status,
                exit_date, exit_price, exit_reason, return_pct, profit_loss, days_held)
                VALUES (?,?,?,?,?,?,?,?,?,?, '2026-08-19T00:00:00', 8.0, 'time_limit', -20.0, -200.0, 79)""", r)
        conn.commit()
    # Bars: stop (9.0) crossed on 2026-06-05
    db.insert_price_bars([
        {'ticker': 'DUP', 'date': '2026-06-02', 'open': 9.9, 'high': 10.1, 'low': 9.5, 'close': 9.6, 'volume': 1},
        {'ticker': 'DUP', 'date': '2026-06-05', 'open': 9.4, 'high': 9.5, 'low': 8.7, 'close': 8.8, 'volume': 1},
    ])
    yield db
    db.close()


def test_dry_run_changes_nothing(seeded):
    report = revalidate(seeded.db_path, apply=False)
    assert any(r['action'] == 'void_duplicate' for r in report)
    with contextlib.closing(sqlite3.connect(seeded.db_path)) as conn:
        statuses = [r[0] for r in conn.execute("SELECT status FROM paper_trades")]
    assert statuses == ['closed', 'closed', 'closed']


def test_apply_voids_and_recloses(seeded):
    revalidate(seeded.db_path, apply=True)
    with contextlib.closing(sqlite3.connect(seeded.db_path)) as conn:
        rows = list(conn.execute(
            "SELECT id, status, exit_reason, exit_price, notes FROM paper_trades ORDER BY id"))
    # Lowest id survives; duplicate + zero-share voided
    assert rows[0][1] == 'closed' and rows[1][1] == 'void_duplicate'
    assert rows[2][1] == 'void_zero_shares'
    # Survivor re-closed against bars: stop at 9.0 on 2026-06-05
    assert rows[0][2] == 'stop_loss' and rows[0][3] == 9.0
    original = json.loads(rows[0][4])['original_exit']
    assert original['exit_price'] == 8.0 and original['exit_reason'] == 'time_limit'
