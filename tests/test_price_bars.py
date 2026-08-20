"""
@file test_price_bars.py
@brief Tests for the price_bars market-date spine table and its accessors.
"""

import pytest
from src.database.models import Database

BARS = [
    {'ticker': 'TEST', 'date': '2026-08-10', 'open': 10.0, 'high': 11.0, 'low': 9.5, 'close': 10.5, 'volume': 1000},
    {'ticker': 'TEST', 'date': '2026-08-11', 'open': 10.5, 'high': 12.0, 'low': 10.4, 'close': 11.8, 'volume': 1500},
    {'ticker': 'TEST', 'date': '2026-08-12', 'open': 11.8, 'high': 11.9, 'low': 10.9, 'close': 11.0, 'volume': 900},
]


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    d.initialize()
    yield d
    d.close()


def test_insert_and_read_back(db):
    assert db.insert_price_bars(BARS) == 3
    bars = db.get_bars_since('TEST', '2026-08-10')
    assert [b['date'] for b in bars] == ['2026-08-11', '2026-08-12']
    assert bars[0]['high'] == 12.0 and bars[0]['volume'] == 1500


def test_upsert_is_idempotent(db):
    db.insert_price_bars(BARS)
    db.insert_price_bars(BARS)  # same rows again
    assert len(db.get_bars_since('TEST', '2026-08-09')) == 3


def test_last_bar_date(db):
    assert db.get_last_bar_date('TEST') is None
    db.insert_price_bars(BARS)
    assert db.get_last_bar_date('TEST') == '2026-08-12'


def test_close_history_ascending(db):
    db.insert_price_bars(BARS)
    assert db.get_close_history('TEST', days=3650) == [10.5, 11.8, 11.0]
    assert db.get_close_history('OTHER') == []


def test_empty_insert(db):
    assert db.insert_price_bars([]) == 0


def test_signal_and_trade_tickers(db):
    conn = db.connect()
    conn.execute("INSERT INTO signals (ticker, signal_type, conviction_score, created_at) "
                 "VALUES ('AAA', 'insider_cluster', 50, '2026-08-01')")
    conn.execute("""INSERT INTO paper_trades
        (ticker, entry_date, entry_price, shares, conviction, signal_types, position_size)
        VALUES ('BBB', '2026-08-01', 10.0, 5, 50, '["insider_cluster"]', 50.0)""")
    conn.commit()
    assert db.get_signal_and_trade_tickers() == ['AAA', 'BBB']
