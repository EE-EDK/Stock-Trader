"""
@file technical.py
@brief Technical analysis indicators using price data
@details Calculate indicators without requiring additional API calls
"""

from typing import List, Dict, Optional
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    @brief Calculate Relative Strength Index
    @param prices List of closing prices (oldest first)
    @param period RSI period (default 14)
    @return RSI value (0-100) or None if insufficient data
    @details RSI < 30 = oversold, RSI > 70 = overbought
    """
    if len(prices) < period + 1:
        return None

    # Calculate price changes
    deltas = np.diff(prices)

    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # Calculate average gain and loss
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return float(rsi)


def calculate_moving_average(prices: List[float], period: int) -> Optional[float]:
    """
    @brief Calculate Simple Moving Average
    @param prices List of closing prices
    @param period Number of periods
    @return SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None

    return float(np.mean(prices[-period:]))


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    @brief Calculate Exponential Moving Average
    @param prices List of closing prices
    @param period EMA period
    @return EMA value or None if insufficient data
    """
    if len(prices) < period:
        return None

    multiplier = 2 / (period + 1)
    ema = prices[0]

    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return float(ema)


def detect_golden_cross(prices: List[float]) -> bool:
    """
    @brief Detect bullish golden cross (50 MA crosses above 200 MA)
    @param prices List of closing prices (need at least 200)
    @return True if golden cross detected
    """
    if len(prices) < 200:
        return False

    ma50_current = calculate_moving_average(prices[-50:], 50)
    ma200_current = calculate_moving_average(prices[-200:], 200)
    ma50_prev = calculate_moving_average(prices[-51:-1], 50)
    ma200_prev = calculate_moving_average(prices[-201:-1], 200)

    if None in [ma50_current, ma200_current, ma50_prev, ma200_prev]:
        return False

    # Golden cross: 50 MA crosses above 200 MA
    return ma50_prev <= ma200_prev and ma50_current > ma200_current


def detect_death_cross(prices: List[float]) -> bool:
    """
    @brief Detect bearish death cross (50 MA crosses below 200 MA)
    @param prices List of closing prices (need at least 200)
    @return True if death cross detected
    """
    if len(prices) < 200:
        return False

    ma50_current = calculate_moving_average(prices[-50:], 50)
    ma200_current = calculate_moving_average(prices[-200:], 200)
    ma50_prev = calculate_moving_average(prices[-51:-1], 50)
    ma200_prev = calculate_moving_average(prices[-201:-1], 200)

    if None in [ma50_current, ma200_current, ma50_prev, ma200_prev]:
        return False

    # Death cross: 50 MA crosses below 200 MA
    return ma50_prev >= ma200_prev and ma50_current < ma200_current


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
    """
    @brief Calculate Bollinger Bands
    @param prices List of closing prices
    @param period Period for moving average (default 20)
    @param std_dev Standard deviations for bands (default 2)
    @return Dictionary with upper, middle, lower bands or None
    """
    if len(prices) < period:
        return None

    recent_prices = prices[-period:]
    middle_band = np.mean(recent_prices)
    std = np.std(recent_prices)

    upper_band = middle_band + (std_dev * std)
    lower_band = middle_band - (std_dev * std)

    current_price = prices[-1]

    # Calculate position within bands (0 = lower band, 1 = upper band)
    if upper_band != lower_band:
        band_position = (current_price - lower_band) / (upper_band - lower_band)
    else:
        band_position = 0.5

    return {
        'upper': float(upper_band),
        'middle': float(middle_band),
        'lower': float(lower_band),
        'current': float(current_price),
        'position': float(band_position),  # 0-1, where >0.8 = overbought, <0.2 = oversold
        'width': float(upper_band - lower_band)
    }


def calculate_price_momentum(prices: List[float], period: int = 10) -> Optional[float]:
    """
    @brief Calculate price momentum
    @param prices List of closing prices
    @param period Lookback period
    @return Momentum percentage change or None
    """
    if len(prices) < period + 1:
        return None

    old_price = prices[-period - 1]
    current_price = prices[-1]

    if old_price == 0:
        return None

    momentum = ((current_price - old_price) / old_price) * 100
    return float(momentum)


def detect_breakout(prices: List[float], period: int = 20, threshold: float = 1.02) -> bool:
    """
    @brief Detect price breakout above recent range
    @param prices List of closing prices
    @param period Lookback period for range
    @param threshold Breakout threshold (1.02 = 2% above high)
    @return True if breakout detected
    """
    if len(prices) < period + 1:
        return False

    recent_high = max(prices[-period - 1:-1])  # Exclude current price
    current_price = prices[-1]

    return current_price >= (recent_high * threshold)


class TechnicalAnalyzer:
    """
    @class TechnicalAnalyzer
    @brief Analyze price data to generate technical signals
    """

    def __init__(self, database):
        """
        @brief Initialize technical analyzer
        @param database Database instance for querying price data
        """
        self.db = database

    def analyze_ticker(self, ticker: str, days: int = 30) -> Dict:
        """
        @brief Perform comprehensive technical analysis on a ticker
        @param ticker Stock ticker symbol
        @param days Number of days of price data to analyze
        @return Dictionary with all technical indicators
        """
        # Get price history
        price_history = self.db.get_price_history(ticker, days=days)

        if not price_history:
            return {}

        prices = [p['price'] for p in price_history if p['price'] > 0]

        if len(prices) < 5:
            logger.debug(f"Insufficient price data for {ticker}")
            return {}

        # Calculate all indicators
        result = {
            'ticker': ticker,
            'current_price': prices[-1],
            'rsi_14': calculate_rsi(prices, 14),
            'momentum_10d': calculate_price_momentum(prices, 10),
            'ma_20': calculate_moving_average(prices, 20),
            'ma_50': calculate_moving_average(prices, 50) if len(prices) >= 50 else None,
            'ema_12': calculate_ema(prices, 12),
            'bollinger': calculate_bollinger_bands(prices, 20),
            'breakout_detected': detect_breakout(prices, 20),
            'analyzed_at': datetime.now()
        }

        # Add interpretations
        if result['rsi_14']:
            if result['rsi_14'] < 30:
                result['rsi_signal'] = 'oversold'
            elif result['rsi_14'] > 70:
                result['rsi_signal'] = 'overbought'
            else:
                result['rsi_signal'] = 'neutral'

        if result['bollinger']:
            bb = result['bollinger']
            if bb['position'] < 0.2:
                result['bb_signal'] = 'oversold'
            elif bb['position'] > 0.8:
                result['bb_signal'] = 'overbought'
            else:
                result['bb_signal'] = 'neutral'

        return result

    def get_technical_score(self, analysis: Dict) -> float:
        """
        @brief Calculate composite technical score (0-100)
        @param analysis Technical analysis dictionary
        @return Composite score
        """
        if not analysis:
            return 0.0

        score = 50.0  # Neutral baseline

        # RSI contribution
        rsi = analysis.get('rsi_14')
        if rsi is not None:
            if rsi < 30:  # Oversold = bullish
                score += 15
            elif rsi > 70:  # Overbought = bearish
                score -= 15
            elif 40 <= rsi <= 60:  # Neutral
                score += 5

        # Momentum contribution
        momentum = analysis.get('momentum_10d')
        if momentum is not None:
            if momentum > 10:  # Strong upward momentum
                score += 20
            elif momentum > 5:
                score += 10
            elif momentum < -10:
                score -= 20
            elif momentum < -5:
                score -= 10

        # Bollinger Bands contribution
        bb = analysis.get('bollinger')
        if bb:
            if bb['position'] < 0.2:  # Near lower band = oversold
                score += 10
            elif bb['position'] > 0.8:  # Near upper band = overbought
                score -= 10

        # Breakout bonus
        if analysis.get('breakout_detected'):
            score += 15

        # Clamp to 0-100
        return max(0, min(100, score))
