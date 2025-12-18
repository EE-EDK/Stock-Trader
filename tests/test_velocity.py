"""
@file test_velocity.py
@brief Unit tests for velocity calculations
@details Tests for all velocity metric functions
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.metrics.velocity import (
    mention_velocity_pct,
    mention_velocity_trend,
    sentiment_velocity,
    volume_price_divergence,
    composite_score,
    VelocityCalculator
)


class TestMentionVelocityPct:
    """Test cases for mention_velocity_pct function"""

    def test_increase(self):
        """Test positive percentage change"""
        assert mention_velocity_pct(200, 100) == 100.0

    def test_decrease(self):
        """Test negative percentage change"""
        assert mention_velocity_pct(50, 100) == -50.0

    def test_no_change(self):
        """Test zero percentage change"""
        assert mention_velocity_pct(100, 100) == 0.0

    def test_zero_previous(self):
        """Test handling of zero previous value"""
        assert mention_velocity_pct(100, 0) == 100.0
        assert mention_velocity_pct(0, 0) == 0.0

    def test_large_increase(self):
        """Test large percentage increase"""
        result = mention_velocity_pct(1000, 10)
        assert result == 9900.0


class TestMentionVelocityTrend:
    """Test cases for mention_velocity_trend function"""

    def test_upward_trend(self):
        """Test positive trend detection"""
        now = datetime.now()
        history = [
            (now - timedelta(days=6), 10),
            (now - timedelta(days=5), 15),
            (now - timedelta(days=4), 20),
            (now - timedelta(days=3), 25),
            (now - timedelta(days=2), 30),
            (now - timedelta(days=1), 35),
            (now, 40)
        ]
        slope = mention_velocity_trend(history)
        assert slope > 0

    def test_downward_trend(self):
        """Test negative trend detection"""
        now = datetime.now()
        history = [
            (now - timedelta(days=6), 100),
            (now - timedelta(days=5), 90),
            (now - timedelta(days=4), 80),
            (now - timedelta(days=3), 70),
            (now - timedelta(days=2), 60),
            (now - timedelta(days=1), 50),
            (now, 40)
        ]
        slope = mention_velocity_trend(history)
        assert slope < 0

    def test_flat_trend(self):
        """Test flat/stable trend"""
        now = datetime.now()
        history = [
            (now - timedelta(days=i), 50)
            for i in range(7)
        ]
        slope = mention_velocity_trend(history)
        assert abs(slope) < 0.1

    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        now = datetime.now()
        history = [(now, 10)]
        assert mention_velocity_trend(history) == 0.0

    def test_empty_history(self):
        """Test handling of empty history"""
        assert mention_velocity_trend([]) == 0.0


class TestSentimentVelocity:
    """Test cases for sentiment_velocity function"""

    def test_increasing_sentiment(self):
        """Test positive sentiment velocity"""
        scores = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        vel = sentiment_velocity(scores)
        assert vel > 0

    def test_decreasing_sentiment(self):
        """Test negative sentiment velocity"""
        scores = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
        vel = sentiment_velocity(scores)
        assert vel < 0

    def test_stable_sentiment(self):
        """Test stable sentiment"""
        scores = [0.5] * 10
        vel = sentiment_velocity(scores)
        assert abs(vel) < 0.01

    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        scores = [0.5]
        assert sentiment_velocity(scores) == 0.0

    def test_empty_scores(self):
        """Test handling of empty list"""
        assert sentiment_velocity([]) == 0.0


class TestVolumePriceDivergence:
    """Test cases for volume_price_divergence function"""

    def test_positive_divergence(self):
        """Test mentions growing faster than price"""
        mention_changes = [50, 60, 70, 80]
        price_changes = [5, 6, 7, 8]
        div = volume_price_divergence(mention_changes, price_changes)
        # Mentions growing faster should give positive divergence
        assert div > 0

    def test_negative_divergence(self):
        """Test price growing faster than mentions"""
        mention_changes = [5, 6, 7, 8]
        price_changes = [50, 60, 70, 80]
        div = volume_price_divergence(mention_changes, price_changes)
        # Price growing faster should give negative divergence
        assert div < 0

    def test_equal_growth(self):
        """Test equal growth rates"""
        changes = [10, 20, 30, 40]
        div = volume_price_divergence(changes, changes)
        assert abs(div) < 0.1

    def test_mismatched_lengths(self):
        """Test handling of mismatched array lengths"""
        assert volume_price_divergence([1, 2, 3], [1, 2]) == 0.0

    def test_empty_arrays(self):
        """Test handling of empty arrays"""
        assert volume_price_divergence([], []) == 0.0


class TestCompositeScore:
    """Test cases for composite_score function"""

    def test_high_score(self):
        """Test high composite score calculation"""
        score = composite_score(
            mention_vel_24h=500,
            mention_vel_7d=50,
            sentiment_vel=1.0,
            divergence=2.0
        )
        assert 0 <= score <= 100
        assert score > 50  # Should be high

    def test_low_score(self):
        """Test low composite score calculation"""
        score = composite_score(
            mention_vel_24h=0,
            mention_vel_7d=0,
            sentiment_vel=0,
            divergence=0
        )
        assert 0 <= score <= 100
        assert score < 60  # Should be around 50 (neutral)

    def test_bounds(self):
        """Test score stays within 0-100 bounds"""
        score = composite_score(
            mention_vel_24h=10000,
            mention_vel_7d=1000,
            sentiment_vel=100,
            divergence=100
        )
        assert 0 <= score <= 100

    def test_custom_weights(self):
        """Test custom weight dictionary"""
        weights = {
            'mention_24h': 0.5,
            'mention_7d': 0.3,
            'sentiment': 0.15,
            'divergence': 0.05
        }
        score = composite_score(100, 10, 0.5, 1.0, weights=weights)
        assert 0 <= score <= 100

    def test_negative_inputs(self):
        """Test handling of negative velocities"""
        score = composite_score(
            mention_vel_24h=-50,
            mention_vel_7d=-10,
            sentiment_vel=-0.5,
            divergence=-1.0
        )
        assert 0 <= score <= 100


class TestVelocityCalculator:
    """Test cases for VelocityCalculator class"""

    def test_init(self):
        """Test calculator initialization"""
        mock_db = Mock()
        calc = VelocityCalculator(mock_db)
        assert calc.db == mock_db

    def test_calculate_ticker_velocity(self):
        """Test velocity calculation for single ticker"""
        mock_db = Mock()
        now = datetime.now()

        # Mock mention history
        mock_db.get_mention_history.return_value = [
            (now - timedelta(days=2), 100),
            (now - timedelta(days=1), 150),
            (now, 200)
        ]

        # Mock sentiment history
        mock_db.get_sentiment_history.return_value = [0.5, 0.6, 0.7]

        # Mock price history
        mock_db.get_price_history.return_value = [
            {'price': 100, 'collected_at': now - timedelta(days=2)},
            {'price': 105, 'collected_at': now - timedelta(days=1)},
            {'price': 110, 'collected_at': now}
        ]

        calc = VelocityCalculator(mock_db)
        result = calc.calculate_ticker_velocity('AAPL')

        assert 'mention_velocity_24h' in result
        assert 'mention_velocity_7d' in result
        assert 'sentiment_velocity' in result
        assert 'volume_price_divergence' in result
        assert 'composite_score' in result

        # 24h velocity should be positive (200 vs 150)
        assert result['mention_velocity_24h'] > 0

    def test_calculate_all_velocities(self):
        """Test velocity calculation for all tickers"""
        mock_db = Mock()
        now = datetime.now()

        mock_db.get_tracked_tickers.return_value = ['AAPL', 'TSLA']

        # Mock data for filtering
        mock_db.get_mention_history.return_value = [
            (now, 10)  # Meets minimum
        ]

        mock_db.get_sentiment_history.return_value = [0.5]
        mock_db.get_price_history.return_value = [{'price': 100}]

        calc = VelocityCalculator(mock_db)
        results = calc.calculate_all_velocities(min_mentions=5)

        assert isinstance(results, dict)
        # Should have calculated for both tickers
        assert len(results) <= 2

    def test_error_handling(self):
        """Test error handling in calculations"""
        mock_db = Mock()
        mock_db.get_mention_history.side_effect = Exception("DB Error")

        calc = VelocityCalculator(mock_db)
        result = calc.calculate_ticker_velocity('INVALID')

        # Should return zeros on error
        assert result['composite_score'] == 0.0
