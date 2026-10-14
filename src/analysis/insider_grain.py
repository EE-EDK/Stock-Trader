"""
@file insider_grain.py
@brief Grain separation and acquisition-channel classification for insider rows.
@details OpenInsider is scraped through three overlapping views (cluster buys,
         CEO/CFO buys, general purchases). Two distinct defects follow:

         1. GRAIN MIXING. The cluster view returns *roll-up* rows that aggregate
            several insiders' Form 4 filings into one line, and those roll-ups
            sit in the same table as the individual filings they summarise.
            Counting both grains double-counts. Measured 2026-08-23: 352 of 753
            rows are roll-ups (47%). Only 4 of them reconcile exactly against
            their components, because the individual views capture only officers
            and directors above a dollar floor - the roll-up's other buyers were
            never scraped. Reconciliation is therefore NOT achievable; grain
            separation is. Totals must come from exactly one grain, never a sum
            of both.

         2. CHANNEL BLINDNESS. Form 4 transaction code 'P' covers any purchase,
            including one filled at a price the open market did not set - a
            registered offering or an exercise at strike. Intel's CEO bought
            105,263 shares at exactly $95.00 on 2026-08-11 inside a $20B upsized
            offering; the pipeline read it as a $10M conviction buy. The scraper
            also discarded OpenInsider's qualified code string (e.g.
            "P - Purchase+OE"), destroying the only direct evidence.

         The test that separates them: an open-market fill must print inside that
         session's low-high range. A price BELOW the day's low indicates a price
         the market did not set (offering discount, exercise at strike). A price
         ABOVE the day's high is not an offering - offerings price at or below
         market - so it is classified separately as a data anomaly.

         Validated 2026-08-23 against 23 Form 4 rows with matching bars:
           INTC 2026-08-11  $95.00 vs 95.35-98.35  BELOW  -> known $20B offering
           MSTR 2026-03-19  $99.62 vs 132.76-139.78 BELOW -> 26% under market
           FEMY 2026-08-07  $3.20  vs 2.29-3.14    ABOVE  -> anomaly, x2 rows
         Zero false positives against the KEEL, CC and OPEN open-market buys.
         Roll-up rows are excluded from the test: their price is a blended
         average across several days and misfires (KEEL 2026-08-17).
@version 1.0.0
@date 2026-08-23
@see utils/backfill_acquisition_metadata.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# --- Row grain ------------------------------------------------------------
GRAIN_FORM4 = 'form4'      # one individual Form 4 filing
GRAIN_ROLLUP = 'rollup'    # OpenInsider cluster line aggregating several filings

# --- Acquisition channel --------------------------------------------------
CHANNEL_OPEN_MARKET = 'open_market'
CHANNEL_OFF_MARKET = 'off_market_suspected'
CHANNEL_PRICE_ANOMALY = 'price_anomaly'
CHANNEL_UNVERIFIED = 'unverified'

#: Channels that may contribute to a cluster's buyer count. UNVERIFIED counts:
#: a missing bar must not silently destroy a real signal. A positively
#: identified off-market fill does not count - that is the Intel case.
COUNTABLE_CHANNELS = (CHANNEL_OPEN_MARKET, CHANNEL_UNVERIFIED)

#: Substrings in OpenInsider's qualified trade-type string that mark a fill the
#: open market did not price, regardless of what the bar range says.
OFF_MARKET_CODE_MARKERS = ('+OE', 'OPTION', 'EXERCISE', 'CONVERT', 'AWARD', 'GRANT')


def classify_grain(is_cluster_buy: Any) -> str:
    """
    @brief Map the legacy is_cluster_buy flag onto an explicit grain label.
    @param is_cluster_buy Truthy for an OpenInsider cluster roll-up row
    @return GRAIN_ROLLUP or GRAIN_FORM4
    """
    return GRAIN_ROLLUP if is_cluster_buy else GRAIN_FORM4


def classify_channel(
    grain: str,
    price: Optional[float],
    bar_low: Optional[float],
    bar_high: Optional[float],
    acquisition_code: Optional[str] = None,
) -> str:
    """
    @brief Decide whether a purchase price was set by the open market.
    @param grain GRAIN_FORM4 or GRAIN_ROLLUP
    @param price Price paid per share
    @param bar_low Session low for the trade date
    @param bar_high Session high for the trade date
    @param acquisition_code Raw OpenInsider trade-type string, if preserved
    @return One of the CHANNEL_* constants
    @pre bar_low <= bar_high when both are supplied
    @warning Roll-up rows always return CHANNEL_UNVERIFIED - their price is a
             blended average across several sessions and cannot be range-tested.
    """
    if acquisition_code:
        upper = acquisition_code.upper()
        if any(marker in upper for marker in OFF_MARKET_CODE_MARKERS):
            return CHANNEL_OFF_MARKET

    if grain == GRAIN_ROLLUP:
        return CHANNEL_UNVERIFIED
    if price is None or price <= 0 or bar_low is None or bar_high is None:
        return CHANNEL_UNVERIFIED
    if price < bar_low:
        return CHANNEL_OFF_MARKET
    if price > bar_high:
        return CHANNEL_PRICE_ANOMALY
    return CHANNEL_OPEN_MARKET


@dataclass
class ClusterVerdict:
    """
    @brief Outcome of evaluating insider rows against the cluster thresholds.
    @details `basis` names the single grain the dollar total came from, so a
             reader can never mistake it for a cross-grain sum.
    """
    fires: bool = False
    buyer_count: int = 0
    buyer_count_exact: bool = False          # True when buyer_count is OpenInsider's
                                              # own "Ins" column, not the min_insiders floor
    total_value: float = 0.0
    basis: str = 'none'                      # 'form4' | 'rollup' | 'none'
    rollup_present: bool = False
    excluded: Dict[str, int] = field(default_factory=dict)
    titles: List[str] = field(default_factory=list)

    def note(self) -> str:
        """@brief One-line human-readable summary for the signal note field."""
        if not self.fires:
            return 'no qualifying insider cluster'
        who = f"{self.buyer_count} insider{'s' if self.buyer_count != 1 else ''}"
        if self.basis == 'rollup':
            hedge = '' if self.buyer_count_exact else '+'
            who = f"cluster filing ({self.buyer_count}{hedge} insiders)"
        out = f"{who} bought ${self.total_value:,.0f} [{self.basis}]"
        if self.excluded:
            drops = ', '.join(f"{n} {k}" for k, n in sorted(self.excluded.items()))
            out += f" (excluded: {drops})"
        return out


def _parse_date(value: Any) -> Optional[datetime]:
    """@brief Parse a trade_date that may be a datetime or an ISO-ish string."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value[:10])
            except ValueError:
                return None
    return None


def _identity(row: Dict[str, Any]) -> Tuple[str, str]:
    """@brief Normalised (name, title) key for counting distinct people."""
    return ((row.get('insider_name') or '').strip().upper(),
            (row.get('insider_title') or '').strip().upper())


def evaluate_cluster(
    rows: Sequence[Dict[str, Any]],
    thresholds: Optional[Dict[str, Any]] = None,
    as_of: Optional[datetime] = None,
) -> ClusterVerdict:
    """
    @brief Evaluate insider rows for a single ticker against cluster criteria.
    @param rows Insider rows for one ticker (both grains may be present)
    @param thresholds The `insider_cluster` threshold block from config
    @param as_of Evaluation instant; defaults to now. Pass explicitly for
                 reproducible backtests and tests.
    @return ClusterVerdict describing the decision and its basis
    @post verdict.total_value is drawn from exactly one grain (verdict.basis)

    @details Cluster status is established by EITHER of two independent routes:
             - at least `min_insiders` distinct countable Form 4 buyers, or
             - the presence of a roll-up row, which is itself proof that
               OpenInsider's cluster screen matched (that screen only lists
               tickers with multiple insiders buying).
             The dollar total then comes from the roll-up when one exists -
             it is the superset - and from the Form 4 rows otherwise. The two
             are never added together.
    """
    verdict = ClusterVerdict()
    if not rows:
        return verdict

    threshold = (thresholds or {}).get('insider_cluster', {}) or {}
    lookback_days = threshold.get('lookback_days') or 14
    min_insiders = threshold.get('min_insiders') or 2
    min_value_total = threshold.get('min_value_total') or 100000

    cutoff = (as_of or datetime.now()) - timedelta(days=lookback_days)

    form4: List[Dict[str, Any]] = []
    rollups: List[Dict[str, Any]] = []
    for row in rows:
        if row.get('trade_type') != 'P':
            continue
        trade_date = _parse_date(row.get('trade_date'))
        if trade_date is None or trade_date < cutoff:
            continue

        grain = row.get('row_grain') or classify_grain(row.get('is_cluster_buy'))
        if grain == GRAIN_ROLLUP:
            rollups.append(row)
            continue

        channel = row.get('acquisition_channel') or CHANNEL_UNVERIFIED
        if channel not in COUNTABLE_CHANNELS:
            verdict.excluded[channel] = verdict.excluded.get(channel, 0) + 1
            continue
        form4.append(row)

    verdict.rollup_present = bool(rollups)
    distinct = {_identity(r) for r in form4}
    form4_total = sum((r.get('value') or 0) for r in form4)
    rollup_total = max((r.get('value') or 0) for r in rollups) if rollups else 0.0

    # OpenInsider's cluster-buys table carries its own buyer count (the 'Ins'
    # column, captured 2026-09-02 -- see src/collectors/openinsider.py). Rows
    # collected before that date have insider_count=None; for those, keep the
    # old behavior (presence of a roll-up implies >= min_insiders, and the
    # reported count is a hedged floor) rather than silently reclassifying
    # historical clusters.
    rollup_counts = [r['insider_count'] for r in rollups
                      if r.get('insider_count')]
    real_rollup_count = max(rollup_counts) if rollup_counts else None

    # Totals come from one grain only. The roll-up is the superset when present.
    if rollups and rollup_total >= form4_total:
        verdict.basis = 'rollup'
        verdict.total_value = rollup_total
        if real_rollup_count is not None:
            verdict.buyer_count = max(len(distinct), real_rollup_count)
            verdict.buyer_count_exact = True
        else:
            verdict.buyer_count = max(len(distinct), min_insiders)
    elif form4:
        verdict.basis = 'form4'
        verdict.total_value = form4_total
        verdict.buyer_count = len(distinct)
    else:
        return verdict

    verdict.titles = sorted({t for _, t in distinct if t})
    if real_rollup_count is not None:
        rollup_qualifies = real_rollup_count >= min_insiders
    else:
        rollup_qualifies = verdict.rollup_present
    is_cluster = len(distinct) >= min_insiders or rollup_qualifies
    verdict.fires = bool(is_cluster and verdict.total_value >= min_value_total)
    if not verdict.fires:
        verdict.buyer_count = len(distinct)
        verdict.buyer_count_exact = False
    return verdict
