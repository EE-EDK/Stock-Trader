"""
@file test_bars_backfill.py
@brief Tests for the gap-aware daily-bar backfill into price_bars.
"""

from datetime import datetime, timedelta
import pytest
from src.database.models import Database
from src.collectors.bars_backfill import backfill_price_bars, _period_for_gap


class FakeCollector:
    def __init__(self):
        self.calls = []

    def collect_historical_prices(self, tickers, period="1mo"):
        self.calls.append((tuple(tickers), period))
        out = {}
        for t in tickers:
            out[t] = [
                {'ticker': t, 'date': '2026-08-18', 'open': 1.0, 'high': 2.0,
                 'low': 0.9, 'close': 1.5, 'volume': 100, 'collected_at': datetime.now()},
                {'ticker': t, 'date': '2026-08-19', 'open': 1.5, 'high': 2.5,
                 'low': 1.4, 'close': 2.0, 'volume': 200, 'collected_at': datetime.now()},
            ]
        return out


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "test.db"))
    d.initialize()
    yield d
    d.close()


def test_backfill_new_ticker_uses_long_period(db):
    fake = FakeCollector()
    written = backfill_price_bars(db, fake, ['NEW'], min_history_days=180)
    assert written == {'NEW': 2}
    assert fake.calls[0][1] == '1y'
    assert db.get_last_bar_date('NEW') == '2026-08-19'


def test_backfill_small_gap_uses_short_period(db):
    recent = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    db.insert_price_bars([{'ticker': 'OLD', 'date': recent,
                           'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1}])
    fake = FakeCollector()
    backfill_price_bars(db, fake, ['OLD'])
    assert fake.calls[0][1] == '5d'


def test_period_mapping():
    assert _period_for_gap(3) == '5d'
    assert _period_for_gap(20) == '1mo'
    assert _period_for_gap(80) == '3mo'
    assert _period_for_gap(150) == '6mo'
    assert _period_for_gap(400) == '1y'


def test_up_to_date_ticker_is_skipped(db):
    today = datetime.now().strftime('%Y-%m-%d')
    db.insert_price_bars([{'ticker': 'CUR', 'date': today,
                           'open': 1, 'high': 1, 'low': 1, 'close': 1, 'volume': 1}])
    fake = FakeCollector()
    written = backfill_price_bars(db, fake, ['CUR'])
    assert written == {} and fake.calls == []
