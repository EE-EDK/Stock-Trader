"""
@file engine.py
@brief Pure bar-walking exit engine shared by paper trading and the backtester.
@details Replays daily OHLCV bars in date order and returns the first exit a
         real resting order would have produced. No I/O - fully testable.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True)
class ExitEvent:
    """@brief The first exit a position's rules produce while walking bars."""
    date: str        # 'YYYY-MM-DD' market date of the exit
    price: float     # fill price
    reason: str      # 'stop_loss' | 'take_profit' | 'time_limit'
    days_held: int   # calendar days from entry to exit


def _days_between(entry_date: str, bar_date: str) -> int:
    d0 = datetime.strptime(entry_date[:10], '%Y-%m-%d')
    d1 = datetime.strptime(bar_date[:10], '%Y-%m-%d')
    return (d1 - d0).days


def walk_bars(entry_date: str, entry_price: float, stop_loss: float,
              target_price: float, hold_days: int,
              bars: Sequence[Dict[str, Any]]) -> Optional[ExitEvent]:
    """
    @brief Walk daily bars after entry_date and return the first exit, if any.
    @details Per bar: gap-open through stop/target fills at the open; an
             intrabar stop fills at the stop price (checked before the target -
             conservative when both hit); intrabar target fills at the target
             price; calendar hold_days exit fills at the close. The entry-day
             bar is skipped because intraday sequencing is unknown.
    """
    entry_day = entry_date[:10]
    for b in bars:
        bar_date = b['date'][:10]
        if bar_date <= entry_day:
            continue
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        if o is None or h is None or l is None or c is None:
            continue
        held = _days_between(entry_day, bar_date)

        if o <= stop_loss:
            return ExitEvent(bar_date, o, 'stop_loss', held)
        if o >= target_price:
            return ExitEvent(bar_date, o, 'take_profit', held)
        if l <= stop_loss:
            return ExitEvent(bar_date, stop_loss, 'stop_loss', held)
        if h >= target_price:
            return ExitEvent(bar_date, target_price, 'take_profit', held)
        if held >= hold_days:
            return ExitEvent(bar_date, c, 'time_limit', held)
    return None
