"""
@file test_trade_engine.py
@brief Tests for the pure bar-walking exit engine.
"""

from src.trading.engine import walk_bars, ExitEvent


def bar(date, o, h, l, c):
    return {'date': date, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 0}


# Entry: $10.00 on 2026-06-01; stop $9.00 (-10%), target $12.00 (+20%), hold 30d
ARGS = dict(entry_date='2026-06-01', entry_price=10.0, stop_loss=9.0,
            target_price=12.0, hold_days=30)


def test_no_exit_returns_none():
    bars = [bar('2026-06-02', 10.0, 10.5, 9.8, 10.2)]
    assert walk_bars(bars=bars, **ARGS) is None


def test_entry_day_bar_is_skipped():
    bars = [bar('2026-06-01', 10.0, 15.0, 5.0, 10.0)]  # wild entry-day bar
    assert walk_bars(bars=bars, **ARGS) is None


def test_intrabar_stop_fills_at_stop_price():
    bars = [bar('2026-06-02', 9.8, 10.0, 8.5, 9.5)]
    e = walk_bars(bars=bars, **ARGS)
    assert e == ExitEvent(date='2026-06-02', price=9.0, reason='stop_loss', days_held=1)


def test_gap_down_fills_at_open_not_stop():
    bars = [bar('2026-06-02', 7.0, 7.5, 6.8, 7.2)]  # opened far below the stop
    e = walk_bars(bars=bars, **ARGS)
    assert e.price == 7.0 and e.reason == 'stop_loss'


def test_intrabar_target_fills_at_target_price():
    bars = [bar('2026-06-02', 10.5, 12.5, 10.4, 12.1)]
    e = walk_bars(bars=bars, **ARGS)
    assert e.price == 12.0 and e.reason == 'take_profit'


def test_gap_up_fills_at_open():
    bars = [bar('2026-06-02', 13.0, 13.5, 12.8, 13.2)]
    e = walk_bars(bars=bars, **ARGS)
    assert e.price == 13.0 and e.reason == 'take_profit'


def test_stop_wins_when_both_hit_same_bar():
    bars = [bar('2026-06-02', 10.0, 12.5, 8.5, 11.0)]  # touched both
    e = walk_bars(bars=bars, **ARGS)
    assert e.reason == 'stop_loss'


def test_first_triggering_bar_wins():
    bars = [bar('2026-06-02', 10.0, 10.5, 9.9, 10.1),
            bar('2026-06-03', 10.1, 12.5, 10.0, 12.2),   # target here
            bar('2026-06-04', 12.2, 12.4, 8.0, 8.1)]     # stop later - never reached
    e = walk_bars(bars=bars, **ARGS)
    assert e.date == '2026-06-03' and e.reason == 'take_profit'


def test_time_limit_exits_at_close():
    bars = [bar('2026-06-15', 10.0, 10.5, 9.9, 10.1),
            bar('2026-07-02', 10.1, 10.6, 10.0, 10.4)]   # 31 calendar days after entry
    e = walk_bars(bars=bars, **ARGS)
    assert e == ExitEvent(date='2026-07-02', price=10.4, reason='time_limit', days_held=31)


def test_stop_beats_time_limit_on_same_bar():
    bars = [bar('2026-07-02', 9.5, 9.6, 8.8, 9.0)]
    e = walk_bars(bars=bars, **ARGS)
    assert e.reason == 'stop_loss' and e.price == 9.0
