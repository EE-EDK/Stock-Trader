"""
@file test_signals.py
@brief Unit tests for signal generation
@details Tests for SignalGenerator and Signal class
"""

import pytest
from datetime import datetime, timedelta
from src.signals.generator import Signal, SignalGenerator


class TestSignal:
    """Test cases for Signal dataclass"""

    def test_signal_creation(self):
        """Test creating a signal"""
        signal = Signal(
            ticker='AAPL',
            signal_type='velocity_spike',
            conviction_score=75.0,
            price_at_signal=150.25,
            triggers=['velocity_spike'],
            notes='Test signal',
            created_at=datetime.now()
        )

        assert signal.ticker == 'AAPL'
        assert signal.conviction_score == 75.0
        assert isinstance(signal.triggers, list)


class TestSignalGenerator:
    """Test cases for SignalGenerator"""

    def test_init_default_thresholds(self):
        """Test initialization with default thresholds"""
        gen = SignalGenerator()
        assert gen.thresholds is not None
        assert 'velocity_spike' in gen.thresholds

    def test_init_custom_thresholds(self):
        """Test initialization with custom thresholds"""
        custom = {
            'velocity_spike': {
                'mention_vel_24h_min': 200,
                'composite_score_min': 70
            }
        }
        gen = SignalGenerator(thresholds=custom)
        assert gen.thresholds['velocity_spike']['mention_vel_24h_min'] == 200

    def test_check_velocity_spike_pass(self):
        """Test velocity spike detection - passing case"""
        gen = SignalGenerator()
        vel = {
            'mention_velocity_24h': 150,
            'composite_score': 70
        }
        assert gen._check_velocity_spike(vel) is True

    def test_check_velocity_spike_fail(self):
        """Test velocity spike detection - failing case"""
        gen = SignalGenerator()
        vel = {
            'mention_velocity_24h': 50,
            'composite_score': 40
        }
        assert gen._check_velocity_spike(vel) is False

    def test_check_insider_cluster_pass(self):
        """Test insider cluster detection - passing case"""
        gen = SignalGenerator()
        now = datetime.now()
        insiders = [
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=5),
                'value': 60000
            },
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=3),
                'value': 50000
            }
        ]
        assert gen._check_insider_cluster(insiders) is True

    def test_check_insider_cluster_fail_insufficient_insiders(self):
        """Test insider cluster detection - too few insiders"""
        gen = SignalGenerator()
        now = datetime.now()
        insiders = [
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=5),
                'value': 120000
            }
        ]
        assert gen._check_insider_cluster(insiders) is False

    def test_check_insider_cluster_fail_insufficient_value(self):
        """Test insider cluster detection - insufficient total value"""
        gen = SignalGenerator()
        now = datetime.now()
        insiders = [
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=5),
                'value': 30000
            },
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=3),
                'value': 40000
            }
        ]
        assert gen._check_insider_cluster(insiders) is False

    def test_check_insider_cluster_old_trades(self):
        """Test insider cluster detection - trades too old"""
        gen = SignalGenerator()
        now = datetime.now()
        insiders = [
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=30),
                'value': 60000
            },
            {
                'trade_type': 'P',
                'trade_date': now - timedelta(days=25),
                'value': 50000
            }
        ]
        assert gen._check_insider_cluster(insiders) is False

    def test_check_sentiment_flip_positive(self):
        """Test sentiment flip detection - bullish flip"""
        gen = SignalGenerator()
        vel = {'sentiment_velocity': 0.35}
        assert gen._check_sentiment_flip(vel) is True

    def test_check_sentiment_flip_negative(self):
        """Test sentiment flip detection - bearish flip"""
        gen = SignalGenerator()
        vel = {'sentiment_velocity': -0.35}
        assert gen._check_sentiment_flip(vel) is True

    def test_check_sentiment_flip_fail(self):
        """Test sentiment flip detection - insufficient change"""
        gen = SignalGenerator()
        vel = {'sentiment_velocity': 0.15}
        assert gen._check_sentiment_flip(vel) is False

    def test_generate_notes_velocity_spike(self):
        """Test note generation for velocity spike"""
        gen = SignalGenerator()
        vel = {'mention_velocity_24h': 150, 'composite_score': 70}
        notes = gen._generate_notes('AAPL', vel, [], ['velocity_spike'])
        assert 'Mentions up 150%' in notes
        assert 'Composite: 70' in notes

    def test_generate_notes_insider_cluster(self):
        """Test note generation for insider cluster"""
        gen = SignalGenerator()
        vel = {'composite_score': 65}
        insiders = [
            {'trade_type': 'P', 'value': 60000},
            {'trade_type': 'P', 'value': 50000}
        ]
        notes = gen._generate_notes('AAPL', vel, insiders, ['insider_cluster'])
        assert '2 insiders' in notes
        assert '110,000' in notes

    def test_generate_notes_combined(self):
        """Test note generation for combined signals"""
        gen = SignalGenerator()
        vel = {
            'mention_velocity_24h': 200,
            'sentiment_velocity': 0.4,
            'composite_score': 75
        }
        insiders = [{'trade_type': 'P', 'value': 100000}]
        triggers = ['velocity_spike', 'insider_cluster', 'sentiment_flip']
        notes = gen._generate_notes('AAPL', vel, insiders, triggers)

        assert 'Mentions up 200%' in notes
        assert '1 insiders' in notes
        assert 'bullish' in notes

    def test_generate_signals_velocity_spike_only(self):
        """Test signal generation with only velocity spike"""
        gen = SignalGenerator()

        velocity_data = {
            'AAPL': {
                'mention_velocity_24h': 150,
                'composite_score': 70,
                'sentiment_velocity': 0.1
            }
        }
        insider_data = {}
        price_data = {'AAPL': {'price': 150.25}}

        signals = gen.generate_signals(velocity_data, insider_data, price_data)

        assert len(signals) == 1
        assert signals[0].ticker == 'AAPL'
        assert 'velocity_spike' in signals[0].triggers
        assert signals[0].conviction_score > 40

    def test_generate_signals_combined(self):
        """Test signal generation with multiple triggers"""
        gen = SignalGenerator()

        now = datetime.now()
        velocity_data = {
            'NVDA': {
                'mention_velocity_24h': 200,
                'composite_score': 80,
                'sentiment_velocity': 0.35
            }
        }
        insider_data = {
            'NVDA': [
                {'trade_type': 'P', 'trade_date': now - timedelta(days=5), 'value': 70000},
                {'trade_type': 'P', 'trade_date': now - timedelta(days=3), 'value': 60000}
            ]
        }
        price_data = {'NVDA': {'price': 500.00}}

        signals = gen.generate_signals(velocity_data, insider_data, price_data)

        assert len(signals) == 1
        assert signals[0].ticker == 'NVDA'
        assert len(signals[0].triggers) >= 2
        assert signals[0].signal_type == 'combined'
        assert signals[0].conviction_score > 70

    def test_generate_signals_no_triggers(self):
        """Test signal generation with no triggers met"""
        gen = SignalGenerator()

        velocity_data = {
            'XYZ': {
                'mention_velocity_24h': 10,
                'composite_score': 30,
                'sentiment_velocity': 0.05
            }
        }
        insider_data = {}
        price_data = {'XYZ': {'price': 10.00}}

        signals = gen.generate_signals(velocity_data, insider_data, price_data)

        assert len(signals) == 0

    def test_generate_signals_sorting(self):
        """Test that signals are sorted by conviction"""
        gen = SignalGenerator()

        now = datetime.now()
        velocity_data = {
            'LOW': {
                'mention_velocity_24h': 110,
                'composite_score': 61,
                'sentiment_velocity': 0.1
            },
            'HIGH': {
                'mention_velocity_24h': 300,
                'composite_score': 85,
                'sentiment_velocity': 0.4
            }
        }
        insider_data = {
            'HIGH': [
                {'trade_type': 'P', 'trade_date': now - timedelta(days=5), 'value': 80000},
                {'trade_type': 'P', 'trade_date': now - timedelta(days=3), 'value': 70000}
            ]
        }
        price_data = {
            'LOW': {'price': 50.00},
            'HIGH': {'price': 200.00}
        }

        signals = gen.generate_signals(velocity_data, insider_data, price_data)

        assert len(signals) >= 1
        # First signal should have highest conviction
        for i in range(len(signals) - 1):
            assert signals[i].conviction_score >= signals[i + 1].conviction_score

    def test_filter_by_conviction(self):
        """Test filtering signals by conviction score"""
        gen = SignalGenerator()

        signals = [
            Signal('A', 'test', 80, 100, [], '', datetime.now()),
            Signal('B', 'test', 50, 100, [], '', datetime.now()),
            Signal('C', 'test', 30, 100, [], '', datetime.now()),
        ]

        filtered = gen.filter_by_conviction(signals, min_conviction=45)
        assert len(filtered) == 2
        assert all(s.conviction_score >= 45 for s in filtered)

    def test_get_top_signals(self):
        """Test getting top N signals"""
        gen = SignalGenerator()

        signals = [
            Signal('A', 'test', 90, 100, [], '', datetime.now()),
            Signal('B', 'test', 80, 100, [], '', datetime.now()),
            Signal('C', 'test', 70, 100, [], '', datetime.now()),
            Signal('D', 'test', 60, 100, [], '', datetime.now()),
        ]

        top = gen.get_top_signals(signals, n=2)
        assert len(top) == 2
        assert top[0].ticker == 'A'
        assert top[1].ticker == 'B'

    def test_group_by_type(self):
        """Test grouping signals by type"""
        gen = SignalGenerator()

        signals = [
            Signal('A', 'velocity_spike', 80, 100, [], '', datetime.now()),
            Signal('B', 'insider_cluster', 75, 100, [], '', datetime.now()),
            Signal('C', 'velocity_spike', 70, 100, [], '', datetime.now()),
            Signal('D', 'combined', 90, 100, [], '', datetime.now()),
        ]

        grouped = gen.group_by_type(signals)

        assert len(grouped) == 3
        assert len(grouped['velocity_spike']) == 2
        assert len(grouped['insider_cluster']) == 1
        assert len(grouped['combined']) == 1
