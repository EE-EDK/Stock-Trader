"""
@file technical.py
@brief Technical analysis module for stock price data
@details Zero API calls - uses historical price data you already have
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    @class TechnicalAnalyzer
    @brief Calculate technical indicators from price data
    @details Provides RSI, Bollinger Bands, Moving Averages, Momentum, Breakouts
    """

    def __init__(self, db):
        """
        @brief Initialize technical analyzer
        @param db Database instance for fetching historical prices
        """
        self.db = db

    def analyze_ticker(self, ticker: str, lookback_days: int = 50) -> Dict:
        """
        @brief Run full technical analysis on a ticker
        @param ticker Stock ticker symbol
        @param lookback_days Days of historical data to analyze
        @return Dictionary with all technical indicators
        """
        # Fetch historical prices
        prices = self._get_price_history(ticker, lookback_days)

        if len(prices) < 14:  # Need at least 14 days for RSI
            logger.warning(f"Insufficient price data for {ticker} ({len(prices)} days)")
            return {}

        # Extract price arrays
        closes = np.array([p['close'] for p in prices])
        highs = np.array([p['high'] for p in prices])
        lows = np.array([p['low'] for p in prices])
        volumes = np.array([p['volume'] for p in prices])

        # Calculate all indicators
        analysis = {
            'ticker': ticker,
            'current_price': closes[-1] if len(closes) > 0 else 0,
            'analyzed_at': datetime.now()
        }

        # RSI
        analysis['rsi_14'] = self._calculate_rsi(closes, period=14)
        analysis['rsi_signal'] = self._interpret_rsi(analysis['rsi_14'])

        # Moving Averages
        analysis['sma_20'] = self._calculate_sma(closes, period=20)
        analysis['sma_50'] = self._calculate_sma(closes, period=50)
        analysis['ema_12'] = self._calculate_ema(closes, period=12)
        analysis['ema_26'] = self._calculate_ema(closes, period=26)

        # MACD
        macd, signal, histogram = self._calculate_macd(closes)
        analysis['macd'] = macd
        analysis['macd_signal'] = signal
        analysis['macd_histogram'] = histogram

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes, period=20)
        analysis['bb_upper'] = bb_upper
        analysis['bb_middle'] = bb_middle
        analysis['bb_lower'] = bb_lower
        analysis['bb_width'] = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0
        analysis['bb_position'] = self._calculate_bb_position(closes[-1], bb_upper, bb_middle, bb_lower)

        # Momentum
        analysis['momentum_10'] = self._calculate_momentum(closes, period=10)
        analysis['roc_10'] = self._calculate_roc(closes, period=10)

        # Volume Analysis
        analysis['volume_sma_20'] = self._calculate_sma(volumes, period=20)
        analysis['volume_ratio'] = volumes[-1] / analysis['volume_sma_20'] if analysis['volume_sma_20'] > 0 else 1

        # Support/Resistance
        support, resistance = self._find_support_resistance(closes, highs, lows)
        analysis['support_level'] = support
        analysis['resistance_level'] = resistance

        # Breakout Detection
        analysis['breakout_detected'] = self._detect_breakout(
            closes[-1], volumes[-1], resistance,
            analysis['volume_sma_20'], analysis['bb_upper']
        )

        # Golden/Death Cross
        analysis['golden_cross'] = self._detect_golden_cross(analysis['sma_20'], analysis['sma_50'])
        analysis['death_cross'] = self._detect_death_cross(analysis['sma_20'], analysis['sma_50'])

        # Trend Detection
        analysis['trend'] = self._detect_trend(closes, analysis['sma_20'], analysis['sma_50'])

        return analysis

    def get_technical_score(self, analysis: Dict) -> float:
        """
        @brief Generate composite technical score 0-100
        @param analysis Technical analysis dictionary
        @return Score from 0 (very bearish) to 100 (very bullish)
        """
        if not analysis:
            return 50  # Neutral

        score = 50  # Start neutral

        # RSI contribution (0-20 points)
        rsi = analysis.get('rsi_14', 50)
        if rsi < 30:
            score += 15  # Oversold - bullish
        elif rsi > 70:
            score -= 15  # Overbought - bearish
        elif 40 <= rsi <= 60:
            score += 5  # Neutral zone

        # MACD contribution (0-15 points)
        macd = analysis.get('macd', 0)
        macd_signal = analysis.get('macd_signal', 0)
        if macd > macd_signal:
            score += 10  # Bullish crossover
        else:
            score -= 10  # Bearish crossover

        # Bollinger Bands (0-15 points)
        bb_position = analysis.get('bb_position', 0.5)
        if bb_position < 0.2:
            score += 10  # Near lower band - oversold
        elif bb_position > 0.8:
            score -= 10  # Near upper band - overbought

        # Trend (0-20 points)
        trend = analysis.get('trend', 'neutral')
        if trend == 'strong_uptrend':
            score += 20
        elif trend == 'uptrend':
            score += 10
        elif trend == 'downtrend':
            score -= 10
        elif trend == 'strong_downtrend':
            score -= 20

        # Golden/Death Cross (0-15 points)
        if analysis.get('golden_cross'):
            score += 15
        elif analysis.get('death_cross'):
            score -= 15

        # Volume (0-10 points)
        volume_ratio = analysis.get('volume_ratio', 1)
        if volume_ratio > 1.5:
            score += 10  # High volume - strength
        elif volume_ratio < 0.5:
            score -= 5  # Low volume - weakness

        # Breakout (0-10 points)
        if analysis.get('breakout_detected'):
            score += 10

        # Cap at 0-100
        return max(0, min(100, score))

    def _get_price_history(self, ticker: str, days: int) -> List[Dict]:
        """
        @brief Fetch historical price data from database
        @param ticker Stock ticker symbol
        @param days Number of days to look back
        @return List of price dictionaries
        """
        # Query database for historical prices
        query = """
            SELECT ticker, price as close, high, low, open, collected_at,
                   0 as volume  -- Volume not stored in current schema
            FROM prices
            WHERE ticker = ? AND collected_at >= datetime('now', ? || ' days')
            ORDER BY collected_at ASC
        """

        cursor = self.db.conn.cursor()
        cursor.execute(query, (ticker, -days))
        rows = cursor.fetchall()

        prices = []
        for row in rows:
            prices.append({
                'ticker': row[0],
                'close': row[1] or 0,
                'high': row[2] or row[1] or 0,
                'low': row[3] or row[1] or 0,
                'open': row[4] or row[1] or 0,
                'collected_at': row[5],
                'volume': row[6] or 0
            })

        return prices

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """
        @brief Calculate Relative Strength Index
        @param prices Array of closing prices
        @param period RSI period (default 14)
        @return RSI value 0-100
        """
        if len(prices) < period + 1:
            return 50  # Neutral if insufficient data

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _interpret_rsi(self, rsi: float) -> str:
        """Interpret RSI value"""
        if rsi >= 70:
            return 'overbought'
        elif rsi <= 30:
            return 'oversold'
        else:
            return 'neutral'

    def _calculate_sma(self, prices: np.ndarray, period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return 0
        return round(np.mean(prices[-period:]), 2)

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return 0

        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return round(ema, 2)

    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD, Signal line, and Histogram"""
        if len(prices) < slow:
            return 0, 0, 0

        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow

        # For signal line, we'd need to calculate EMA of MACD
        # Simplified: use current MACD as signal
        signal_line = macd_line * 0.9  # Simplified

        histogram = macd_line - signal_line

        return round(macd_line, 2), round(signal_line, 2), round(histogram, 2)

    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: float = 2) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return 0, 0, 0

        middle = self._calculate_sma(prices, period)
        std = np.std(prices[-period:])

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return round(upper, 2), round(middle, 2), round(lower, 2)

    def _calculate_bb_position(self, price: float, upper: float, middle: float, lower: float) -> float:
        """Calculate where price is within Bollinger Bands (0=lower, 1=upper)"""
        if upper == lower:
            return 0.5

        position = (price - lower) / (upper - lower)
        return round(position, 2)

    def _calculate_momentum(self, prices: np.ndarray, period: int = 10) -> float:
        """Calculate momentum (current price - price N periods ago)"""
        if len(prices) < period + 1:
            return 0

        momentum = prices[-1] - prices[-(period + 1)]
        return round(momentum, 2)

    def _calculate_roc(self, prices: np.ndarray, period: int = 10) -> float:
        """Calculate Rate of Change (%)"""
        if len(prices) < period + 1:
            return 0

        old_price = prices[-(period + 1)]
        if old_price == 0:
            return 0

        roc = ((prices[-1] - old_price) / old_price) * 100
        return round(roc, 2)

    def _find_support_resistance(self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray) -> Tuple[float, float]:
        """Find support and resistance levels"""
        if len(closes) < 10:
            return 0, 0

        # Simple approach: recent low = support, recent high = resistance
        support = np.min(lows[-20:]) if len(lows) >= 20 else np.min(lows)
        resistance = np.max(highs[-20:]) if len(highs) >= 20 else np.max(highs)

        return round(support, 2), round(resistance, 2)

    def _detect_breakout(self, current_price: float, current_volume: float,
                        resistance: float, avg_volume: float, bb_upper: float) -> bool:
        """Detect if stock is breaking out"""
        volume_surge = current_volume > (avg_volume * 1.5) if avg_volume > 0 else False
        price_breakout = current_price > resistance and current_price > bb_upper

        return volume_surge and price_breakout

    def _detect_golden_cross(self, sma_20: float, sma_50: float) -> bool:
        """Detect golden cross (bullish)"""
        # Simplified: SMA20 > SMA50 by significant margin
        if sma_20 == 0 or sma_50 == 0:
            return False
        return sma_20 > sma_50 * 1.02

    def _detect_death_cross(self, sma_20: float, sma_50: float) -> bool:
        """Detect death cross (bearish)"""
        # Simplified: SMA20 < SMA50 by significant margin
        if sma_20 == 0 or sma_50 == 0:
            return False
        return sma_20 < sma_50 * 0.98

    def _detect_trend(self, prices: np.ndarray, sma_20: float, sma_50: float) -> str:
        """Detect overall trend"""
        if len(prices) < 20:
            return 'neutral'

        current = prices[-1]

        # Strong uptrend: price > SMA20 > SMA50, all rising
        if current > sma_20 > sma_50:
            # Check if prices are generally rising
            recent_change = (prices[-1] - prices[-10]) / prices[-10] * 100
            if recent_change > 5:
                return 'strong_uptrend'
            return 'uptrend'

        # Strong downtrend: price < SMA20 < SMA50, all falling
        if current < sma_20 < sma_50:
            recent_change = (prices[-1] - prices[-10]) / prices[-10] * 100
            if recent_change < -5:
                return 'strong_downtrend'
            return 'downtrend'

        return 'neutral'
