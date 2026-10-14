"""
@file test_memory.py
@brief Tests for the project memory ledger, its enforcement gate, and trade lineage.
@details Covers the three invariants the system depends on:
         1. ledger.jsonl is strictly APPEND-ONLY — corrections and annotations
            never mutate an existing line (the historical-preservation red line).
         2. guard matching is a CONJUNCTION — an entry about 'velocity_spike +
            buy' must not fire on an unrelated buy. This is a regression test:
            the first implementation used intersection and wrongly blocked
            insider_cluster.
         3. open_trade refuses a blocked action unless an override reason is
            supplied, and records that reason.
@version 1.0.0
@date 2026-08-29
"""

import importlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

MEM_DIR = Path(__file__).resolve().parent.parent / 'docs' / 'memory'
sys.path.insert(0, str(MEM_DIR))


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    """@brief Fresh memory module bound to an isolated ledger under tmp_path."""
    import memory
    importlib.reload(memory)
    monkeypatch.setattr(memory, 'LEDGER_JSONL', tmp_path / 'ledger.jsonl')
    monkeypatch.setattr(memory, 'LEDGER_MD', tmp_path / 'LEDGER.md')
    return memory


class _Args:
    """@brief Minimal stand-in for the argparse namespace."""
    def __init__(self, **kw):
        defaults = dict(kind='finding', status='validated', confidence='VERIFIED',
                        title='t', detail='', evidence='', tags='', date=None,
                        supersedes=None, applies_to='', sample_n=None,
                        retest_when='', blocks=False)
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestAppendOnly:
    def test_ids_are_sequential_and_stable(self, ledger):
        ledger.add(_Args(title='one'))
        ledger.add(_Args(title='two'))
        assert [e['id'] for e in ledger.load()] == [1, 2]

    def test_supersede_does_not_mutate_the_original_line(self, ledger):
        ledger.add(_Args(title='old'))
        before = ledger.LEDGER_JSONL.read_text(encoding='utf-8').splitlines()[0]
        ledger.add(_Args(title='new', supersedes=1))
        after = ledger.LEDGER_JSONL.read_text(encoding='utf-8').splitlines()[0]
        assert before == after, "the original JSONL line must never be rewritten"

    def test_superseded_entry_is_retained_and_marked(self, ledger):
        ledger.add(_Args(title='old'))
        ledger.add(_Args(title='new', supersedes=1))
        entries = {e['id']: e for e in ledger.load()}
        assert entries[1]['status'] == 'superseded'
        assert entries[1]['superseded_by'] == 2
        assert entries[1]['title'] == 'old', "superseded entries are kept, not deleted"

    def test_annotate_appends_and_does_not_mutate(self, ledger):
        ledger.add(_Args(title='claim'))
        before = ledger.LEDGER_JSONL.read_text(encoding='utf-8').splitlines()[0]
        ledger.annotate(_Args(entry_id=1, applies_to='trigger:x', sample_n=43,
                              retest_when='n>=100', blocks=1))
        lines = ledger.LEDGER_JSONL.read_text(encoding='utf-8').splitlines()
        assert lines[0] == before
        e = ledger.load()[0]
        assert e['sample_n'] == 43 and e['blocks'] is True
        assert e['applies_to'] == ['trigger:x']

    def test_next_id_survives_annotation_records(self, ledger):
        """Regression: annotation rows carry id=None and broke max()."""
        ledger.add(_Args(title='one'))
        ledger.annotate(_Args(entry_id=1, applies_to='trigger:x', sample_n=None,
                              retest_when='', blocks=None))
        ledger.add(_Args(title='two'))
        assert [e['id'] for e in ledger.load()] == [1, 2]


class TestGuardMatching:
    @pytest.fixture
    def guarded(self, ledger, monkeypatch):
        import guard
        importlib.reload(guard)
        monkeypatch.setattr(guard, 'load', ledger.load)
        ledger.add(_Args(kind='failure', title='velocity is bad',
                         applies_to='trigger:velocity_spike,action:buy',
                         blocks=True, sample_n=43, retest_when='n>=100'))
        return guard

    def test_blocks_when_every_target_matches(self, guarded):
        v = guarded.check('trigger:velocity_spike', 'action:buy')
        assert v.blocked
        assert '#1' in v.explain() and 'n=43' in v.explain()

    def test_does_not_block_on_partial_match(self, guarded):
        """Regression: intersection matching wrongly blocked insider_cluster
        because it shared 'action:buy' with the velocity entry."""
        v = guarded.check('trigger:insider_cluster', 'action:buy')
        assert not v.blocked
        assert v.blocking == []

    def test_extra_query_targets_still_match(self, guarded):
        v = guarded.check('trigger:velocity_spike', 'action:buy', 'env:prod')
        assert v.blocked, "entry targets are a subset of the query, so it applies"

    def test_superseded_entries_stop_blocking(self, guarded, ledger):
        ledger.add(_Args(title='velocity re-measured, edge found', supersedes=1))
        assert not guarded.check('trigger:velocity_spike', 'action:buy').blocked

    def test_non_blocking_entry_is_an_advisory(self, guarded, ledger):
        ledger.add(_Args(kind='question', status='open', title='sample too small',
                         applies_to='action:live_trade'))
        v = guarded.check('action:live_trade')
        assert not v.blocked
        assert len(v.advisories) == 1

    def test_clean_verdict_on_unknown_targets(self, guarded):
        v = guarded.check('trigger:something_new')
        assert not v.blocked and 'No ledger entry applies' in v.explain()

    def test_require_raises_when_blocked(self, guarded):
        with pytest.raises(RuntimeError, match='BLOCKED'):
            guarded.require('trigger:velocity_spike', 'action:buy')


class TestTradeLineage:
    @pytest.fixture
    def jr(self, tmp_path, ledger, monkeypatch):
        import guard, journal
        importlib.reload(guard); importlib.reload(journal)
        monkeypatch.setattr(guard, 'load', ledger.load)
        monkeypatch.setitem(sys.modules, 'guard', guard)
        journal.DB = str(tmp_path / 'test.db')
        return journal, str(tmp_path / 'test.db')

    def test_open_and_close_computes_realised_pnl(self, jr):
        journal, db = jr
        journal.open_trade(db, ticker='REFI', side='buy', quantity=18,
                           fill_price=10.85, broker_order_id='abc')
        out = journal.close_trade(db, 'abc', 10.55, 'manual_exit')
        assert out['pnl'] == pytest.approx((10.55 - 10.85) * 18)
        # the summary dict rounds for display; the DB keeps 4dp
        assert out['pct'] == pytest.approx(-2.76, abs=1e-2)
        c = sqlite3.connect(db)
        stored = c.execute(
            "SELECT realized_pct, status FROM live_trades WHERE broker_order_id='abc'"
        ).fetchone()
        assert stored[0] == pytest.approx(-2.7650, abs=1e-4)
        assert stored[1] == 'closed'

    def test_blocked_trade_refuses_without_override(self, jr, ledger):
        journal, db = jr
        ledger.add(_Args(kind='decision', title='paper only',
                         applies_to='action:live_trade', blocks=True))
        with pytest.raises(RuntimeError, match='Ledger blocks this trade'):
            journal.open_trade(db, ticker='X', side='buy', quantity=1,
                               fill_price=1.0, broker_order_id='blocked')

    def test_override_is_permitted_and_recorded(self, jr, ledger):
        journal, db = jr
        ledger.add(_Args(kind='decision', title='paper only',
                         applies_to='action:live_trade', blocks=True))
        journal.open_trade(db, ticker='X', side='buy', quantity=1, fill_price=1.0,
                           broker_order_id='ovr', override_reason='edge re-measured')
        c = sqlite3.connect(db)
        notes = c.execute("SELECT notes FROM live_trades WHERE broker_order_id='ovr'"
                          ).fetchone()[0]
        assert 'LEDGER OVERRIDE: edge re-measured' in notes
        assert '#1' in notes, "the overridden entry id must be recorded"

    def test_expected_prior_round_trips(self, jr):
        journal, db = jr
        journal.open_trade(db, ticker='Y', side='buy', quantity=1, fill_price=2.0,
                           broker_order_id='exp',
                           expected={'p_stop_30d': 0.14, 'stated_edge': None})
        c = sqlite3.connect(db)
        raw = c.execute("SELECT expected FROM live_trades WHERE broker_order_id='exp'"
                        ).fetchone()[0]
        assert json.loads(raw)['p_stop_30d'] == 0.14

    def test_close_unknown_order_fails_loudly(self, jr):
        journal, db = jr
        journal.ensure_schema(db)
        with pytest.raises(SystemExit):
            journal.close_trade(db, 'nope', 1.0, 'stop')
