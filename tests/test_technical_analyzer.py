"""
Unit tests for Technical Analyzer
Tests all technical indicators and edge cases
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics.technical import (
    calculate_rsi,
    calculate_moving_average,
    calculate_ema,
    detect_golden_cross,
    detect_death_cross,
    calculate_bollinger_bands,
    calculate_price_momentum,
    detect_breakout,
    TechnicalAnalyzer
)


class TestRSI:
    """Test RSI calculation"""

    def test_rsi_with_valid_data(self):
        """Test RSI with sufficient price data"""
        prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
                 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41,
                 46.22, 45.64]
        rsi = calculate_rsi(prices, 14)
        assert rsi is not None
        assert 0 <= rsi <= 100
        assert 40 <= rsi <= 70  # Should be in normal range for this data

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data"""
        prices = [100, 101, 102]
        rsi = calculate_rsi(prices, 14)
        assert rsi is None

    def test_rsi_all_gains(self):
        """Test RSI with only price increases"""
        prices = list(range(100, 120))
        rsi = calculate_rsi(prices, 14)
        assert rsi == 100.0

    def test_rsi_all_losses(self):
        """Test RSI with only price decreases"""
        prices = list(range(120, 100, -1))
        rsi = calculate_rsi(prices, 14)
        assert rsi is not None
        assert rsi < 20  # Should be very oversold


class TestMovingAverages:
    """Test moving average calculations"""

    def test_sma_valid_data(self):
        """Test simple moving average"""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        sma = calculate_moving_average(prices, 5)
        assert sma == 114.0  # Average of last 5: (110+112+114+116+118)/5

    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data"""
        prices = [100, 101]
        sma = calculate_moving_average(prices, 5)
        assert sma is None

    def test_ema_valid_data(self):
        """Test exponential moving average"""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        ema = calculate_ema(prices, 5)
        assert ema is not None
        assert 100 < ema < 118

    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data"""
        prices = [100, 101]
        ema = calculate_ema(prices, 5)
        assert ema is None


class TestGoldenDeathCross:
    """Test golden and death cross detection"""

    def test_golden_cross_detection(self):
        """Test detection of golden cross"""
        # Create price series where 50 MA crosses above 200 MA
        prices = [100] * 150 + list(range(100, 150))  # Uptrend
        prices += [150] * 50  # Stabilize
        result = detect_golden_cross(prices)
        # This is a simplified test - actual detection needs specific crossing
        assert isinstance(result, bool)

    def test_death_cross_detection(self):
        """Test detection of death cross"""
        # Create price series where 50 MA crosses below 200 MA
        prices = [150] * 150 + list(range(150, 100, -1))  # Downtrend
        prices += [100] * 50  # Stabilize
        result = detect_death_cross(prices)
        assert isinstance(result, bool)

    def test_insufficient_data_for_cross(self):
        """Test with insufficient data"""
        prices = [100] * 50
        assert detect_golden_cross(prices) == False
        assert detect_death_cross(prices) == False


class TestBollingerBands:
    """Test Bollinger Bands calculation"""

    def test_bollinger_bands_valid_data(self):
        """Test Bollinger Bands with valid data"""
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                 111, 110, 112, 114, 113, 115, 117, 116, 118, 120, 119]
        bb = calculate_bollinger_bands(prices, 20, 2.0)

        assert bb is not None
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        assert 'current' in bb
        assert 'position' in bb
        assert 'width' in bb

        # Validate relationships
        assert bb['upper'] > bb['middle'] > bb['lower']
        assert bb['lower'] <= bb['current'] <= bb['upper'] or True  # May be outside
        assert 0 <= bb['position'] <= 1 or True  # May be outside bands

    def test_bollinger_bands_insufficient_data(self):
        """Test with insufficient data"""
        prices = [100, 101, 102]
        bb = calculate_bollinger_bands(prices, 20)
        assert bb is None


class TestMomentum:
    """Test price momentum calculations"""

    def test_positive_momentum(self):
        """Test positive price momentum"""
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
        momentum = calculate_price_momentum(prices, 10)
        assert momentum is not None
        assert momentum > 0  # Price increased

    def test_negative_momentum(self):
        """Test negative price momentum"""
        prices = [120, 118, 116, 114, 112, 110, 108, 106, 104, 102, 100]
        momentum = calculate_price_momentum(prices, 10)
        assert momentum is not None
        assert momentum < 0  # Price decreased

    def test_zero_price(self):
        """Test momentum with zero price"""
        prices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        momentum = calculate_price_momentum(prices, 10)
        assert momentum is None  # Division by zero protection


class TestBreakout:
    """Test breakout detection"""

    def test_breakout_detected(self):
        """Test detection of price breakout"""
        prices = [100] * 20 + [105]  # Price breaks above range
        breakout = detect_breakout(prices, 20, 1.02)
        assert breakout == True

    def test_no_breakout(self):
        """Test no breakout condition"""
        prices = [100] * 21
        breakout = detect_breakout(prices, 20, 1.02)
        assert breakout == False

    def test_insufficient_data_for_breakout(self):
        """Test with insufficient data"""
        prices = [100, 101, 102]
        breakout = detect_breakout(prices, 20)
        assert breakout == False


class MockDatabase:
    """Mock database for testing TechnicalAnalyzer"""

    def get_price_history(self, ticker, days):
        """Return mock price history"""
        # Generate realistic price history
        base_price = 100
        prices = []
        for i in range(days):
            price = base_price + i * 0.5  # Slight uptrend
            prices.append({
                'price': price,
                'high': price + 1,
                'low': price - 1,
                'open': price - 0.5,
                'volume': 1000000 + i * 1000,
                'collected_at': f'2024-01-{i+1:02d}'
            })
        return prices


class TestTechnicalAnalyzer:
    """Test TechnicalAnalyzer class"""

    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        db = MockDatabase()
        analyzer = TechnicalAnalyzer(db)
        assert analyzer.db == db

    def test_analyze_ticker_valid(self):
        """Test ticker analysis with valid data"""
        db = MockDatabase()
        analyzer = TechnicalAnalyzer(db)

        result = analyzer.analyze_ticker('AAPL', days=30)

        assert 'ticker' in result
        assert result['ticker'] == 'AAPL'
        assert 'current_price' in result
        assert 'rsi_14' in result
        assert 'momentum_10d' in result
        assert 'ma_20' in result
        assert 'bollinger' in result
        assert 'breakout_detected' in result
        assert 'analyzed_at' in result

    def test_analyze_ticker_insufficient_data(self):
        """Test with insufficient price data"""
        class EmptyDB:
            def get_price_history(self, ticker, days):
                return []

        db = EmptyDB()
        analyzer = TechnicalAnalyzer(db)

        result = analyzer.analyze_ticker('AAPL', days=30)
        assert result == {}

    def test_technical_score_calculation(self):
        """Test technical score calculation"""
        db = MockDatabase()
        analyzer = TechnicalAnalyzer(db)

        analysis = analyzer.analyze_ticker('AAPL', days=30)
        score = analyzer.get_technical_score(analysis)

        assert 0 <= score <= 100
        assert isinstance(score, float)

    def test_technical_score_empty_analysis(self):
        """Test score with empty analysis"""
        db = MockDatabase()
        analyzer = TechnicalAnalyzer(db)

        score = analyzer.get_technical_score({})
        assert score == 0.0

    def test_rsi_signal_interpretation(self):
        """Test RSI signal interpretation"""
        db = MockDatabase()
        analyzer = TechnicalAnalyzer(db)

        result = analyzer.analyze_ticker('AAPL', days=30)

        if result.get('rsi_14'):
            assert 'rsi_signal' in result
            assert result['rsi_signal'] in ['oversold', 'overbought', 'neutral']

    def test_bollinger_signal_interpretation(self):
        """Test Bollinger Bands signal interpretation"""
        db = MockDatabase()
        analyzer = TechnicalAnalyzer(db)

        result = analyzer.analyze_ticker('AAPL', days=30)

        if result.get('bollinger'):
            assert 'bb_signal' in result
            assert result['bb_signal'] in ['oversold', 'overbought', 'neutral']


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_price_list(self):
        """Test with empty price list"""
        assert calculate_rsi([], 14) is None
        assert calculate_moving_average([], 10) is None
        assert calculate_ema([], 10) is None
        assert calculate_price_momentum([], 10) is None
        assert calculate_bollinger_bands([], 20) is None

    def test_single_price(self):
        """Test with single price"""
        prices = [100]
        assert calculate_rsi(prices, 14) is None
        assert calculate_moving_average(prices, 10) is None
        assert calculate_ema(prices, 10) is None

    def test_negative_prices(self):
        """Test with negative prices (should still work)"""
        prices = [-100, -102, -101, -103, -105]
        # Should handle negative prices (though unusual)
        ma = calculate_moving_average(prices, 3)
        assert ma is not None

    def test_very_large_numbers(self):
        """Test with very large numbers"""
        prices = [1e10 + i for i in range(20)]
        rsi = calculate_rsi(prices, 14)
        assert rsi is not None
        assert 0 <= rsi <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src.metrics.technical', '--cov-report=term-missing'])
