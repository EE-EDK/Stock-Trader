"""
@file test_insider_grain.py
@brief Tests for insider row-grain separation and acquisition-channel classification.
@details Fixtures use the real rows that exposed each defect on 2026-08-23 so a
         regression reads as a concrete, checkable claim rather than a synthetic one.
@version 1.0.0
@date 2026-08-23
"""

from datetime import datetime

import pytest

from src.analysis.insider_grain import (
    CHANNEL_OFF_MARKET,
    CHANNEL_OPEN_MARKET,
    CHANNEL_PRICE_ANOMALY,
    CHANNEL_UNVERIFIED,
    GRAIN_FORM4,
    GRAIN_ROLLUP,
    classify_channel,
    classify_grain,
    evaluate_cluster,
)

THRESHOLDS = {'insider_cluster': {'min_insiders': 2, 'lookback_days': 14,
                                  'min_value_total': 100000}}
AS_OF = datetime(2026, 8, 21, 18, 30)


def _row(grain=GRAIN_FORM4, channel=CHANNEL_OPEN_MARKET, name='', title='CEO',
         value=100000.0, date='2026-08-14 00:00:00', insider_count=None):
    return {'trade_type': 'P', 'trade_date': date, 'row_grain': grain,
            'acquisition_channel': channel, 'insider_name': name,
            'insider_title': title, 'value': value,
            'is_cluster_buy': 1 if grain == GRAIN_ROLLUP else 0,
            'insider_count': insider_count}


class TestClassifyGrain:
    def test_cluster_flag_maps_to_rollup(self):
        assert classify_grain(1) == GRAIN_ROLLUP

    def test_falsey_flag_maps_to_form4(self):
        assert classify_grain(0) == GRAIN_FORM4
        assert classify_grain(None) == GRAIN_FORM4


class TestClassifyChannel:
    def test_intel_offering_price_below_session_low(self):
        """INTC 2026-08-11: $95.00 fill vs 95.35-98.35 bar, a $20B offering."""
        assert classify_channel(GRAIN_FORM4, 95.00, 95.35, 98.35) == CHANNEL_OFF_MARKET

    def test_mstr_exercise_far_below_session_low(self):
        """MSTR 2026-03-19: $99.62 fill vs 132.76-139.78 bar."""
        assert classify_channel(GRAIN_FORM4, 99.62, 132.76, 139.78) == CHANNEL_OFF_MARKET

    def test_open_market_buys_inside_range(self):
        """CC and KEEL buys that are genuine open-market fills."""
        assert classify_channel(GRAIN_FORM4, 14.95, 14.56, 15.19) == CHANNEL_OPEN_MARKET
        assert classify_channel(GRAIN_FORM4, 3.33, 3.26, 3.78) == CHANNEL_OPEN_MARKET

    def test_price_above_high_is_anomaly_not_offering(self):
        """FEMY 2026-08-07: $3.20 vs 2.29-3.14. Offerings never price above market."""
        assert classify_channel(GRAIN_FORM4, 3.20, 2.29, 3.14) == CHANNEL_PRICE_ANOMALY

    def test_rollup_is_never_range_tested(self):
        """KEEL 2026-08-17 roll-up $3.47 vs 3.63-3.92 is a blended average."""
        assert classify_channel(GRAIN_ROLLUP, 3.47, 3.63, 3.92) == CHANNEL_UNVERIFIED

    def test_missing_bar_is_unverified(self):
        assert classify_channel(GRAIN_FORM4, 10.0, None, None) == CHANNEL_UNVERIFIED

    def test_qualified_code_overrides_range(self):
        """A price inside the range is still off-market if the code says so."""
        assert classify_channel(GRAIN_FORM4, 15.0, 14.0, 16.0,
                                acquisition_code='P - Purchase+OE') == CHANNEL_OFF_MARKET


class TestEvaluateCluster:
    def test_intel_single_off_market_buy_does_not_fire(self):
        """One CEO buy, filled off-market, no roll-up: the Intel false positive."""
        rows = [_row(channel=CHANNEL_OFF_MARKET, name='TAN LIP-BU',
                     value=9999985.0, date='2026-08-11 00:00:00')]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is False
        assert v.excluded.get(CHANNEL_OFF_MARKET) == 1

    def test_open_two_filings_one_person_does_not_fire(self):
        """OPEN: two Form 4 rows, same CEO. One distinct buyer, no roll-up."""
        rows = [_row(name='NEJATIAN KASRA', value=100003.0),
                _row(name='NEJATIAN KASRA', value=100003.0)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is False
        assert v.buyer_count == 1

    def test_keel_rollup_establishes_cluster_despite_one_named_buyer(self):
        """KEEL: only the CEO was scraped individually, but a roll-up exists."""
        rows = [_row(name='GAGNON BEN', value=196097.0, date='2026-08-13 00:00:00'),
                _row(name='GAGNON BEN', value=129497.0, date='2026-08-21 00:00:00'),
                _row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED, name='', title='',
                     value=525657.0, date='2026-08-21 00:00:00')]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.basis == 'rollup'
        assert v.rollup_present is True

    def test_chemours_two_distinct_officers_fire(self):
        rows = [_row(name='DIGNAM DENISE', title='CEO', value=50501.0,
                     date='2026-08-11 00:00:00'),
                _row(name='NEWMAN SHANE', title='CFO', value=50049.0,
                     date='2026-08-06 00:00:00'),
                _row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED, name='', title='',
                     value=458620.0, date='2026-08-12 00:00:00')]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.buyer_count >= 2

    def test_total_is_never_a_cross_grain_sum(self):
        """The defect this module exists to prevent: roll-up + components."""
        rows = [_row(name='A', value=196097.0, date='2026-08-13 00:00:00'),
                _row(name='B', title='COO', value=129497.0, date='2026-08-21 00:00:00'),
                _row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED, name='', title='',
                     value=525657.0, date='2026-08-21 00:00:00')]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.total_value == 525657.0
        assert v.total_value != pytest.approx(196097.0 + 129497.0 + 525657.0)
        assert v.basis == 'rollup'

    def test_rows_outside_lookback_are_ignored(self):
        rows = [_row(name='A', value=500000.0, date='2026-05-11 00:00:00'),
                _row(name='B', title='CFO', value=500000.0, date='2026-05-11 00:00:00')]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is False

    def test_below_min_value_does_not_fire(self):
        rows = [_row(name='A', value=1000.0), _row(name='B', title='CFO', value=1000.0)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is False

    def test_unverified_form4_still_counts(self):
        """A missing bar must not silently destroy a real signal."""
        rows = [_row(channel=CHANNEL_UNVERIFIED, name='A', value=80000.0),
                _row(channel=CHANNEL_UNVERIFIED, name='B', title='CFO', value=80000.0)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.basis == 'form4'

    def test_empty_rows_do_not_fire(self):
        assert evaluate_cluster([], THRESHOLDS, as_of=AS_OF).fires is False

    def test_note_names_the_basis_and_exclusions(self):
        rows = [_row(name='A', value=90000.0),
                _row(name='B', title='CFO', value=90000.0),
                _row(channel=CHANNEL_OFF_MARKET, name='C', title='Dir', value=5e6)]
        note = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF).note()
        assert 'form4' in note
        assert 'excluded' in note
        assert '5,000,000' not in note

    def test_rollup_reports_the_real_ins_count_not_a_floor(self):
        """Ledger #21 fix: OpenInsider's 'Ins' column (captured 2026-09-02)
        gives the real buyer count instead of an undifferentiated presence
        flag. GO 2026-09-01: Ins=2, exactly at min_insiders."""
        rows = [_row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED,
                     value=403900.0, insider_count=2)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.buyer_count == 2
        assert v.buyer_count_exact is True
        assert '2 insiders' in v.note()
        assert '2+ insiders' not in v.note()

    def test_rollup_with_large_real_count_is_not_floored_at_min_insiders(self):
        """LILA 2026-09-01 live: Ins=5. The old code floored every rollup's
        buyer_count at max(named_buyers, min_insiders) -- a 5-buyer cluster
        and a 2-buyer cluster were indistinguishable. Now they are not."""
        rows = [_row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED,
                     value=37846079.0, insider_count=5)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.buyer_count == 5
        assert '5 insiders' in v.note()

    def test_rollup_below_min_insiders_real_count_does_not_fire(self):
        """With a real count available, a rollup under min_insiders must not
        fire just because a roll-up row is present -- presence alone was the
        old, cruder proxy."""
        rows = [_row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED,
                     value=200000.0, insider_count=1)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is False

    def test_legacy_rollup_without_insider_count_keeps_old_presence_behavior(self):
        """Rows collected before 2026-09-02 have insider_count=None. Must not
        be silently reclassified -- presence-based firing and the
        min_insiders floor still apply, and the note keeps its '+' hedge."""
        rows = [_row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED,
                     value=525657.0, insider_count=None)]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.buyer_count == 2   # floored at min_insiders, as before
        assert v.buyer_count_exact is False
        assert '2+ insiders' in v.note()

    def test_rollup_real_count_combines_with_named_form4_buyers(self):
        """The real rollup count and independently-named Form 4 buyers both
        feed buyer_count; the larger of the two is reported."""
        rows = [_row(name='A', title='CEO', value=50000.0,
                     date='2026-08-13 00:00:00'),
                _row(name='B', title='CFO', value=50000.0,
                     date='2026-08-14 00:00:00'),
                _row(grain=GRAIN_ROLLUP, channel=CHANNEL_UNVERIFIED,
                     value=300000.0, insider_count=4,
                     date='2026-08-14 00:00:00')]
        v = evaluate_cluster(rows, THRESHOLDS, as_of=AS_OF)
        assert v.fires is True
        assert v.buyer_count == 4
        assert v.buyer_count_exact is True
