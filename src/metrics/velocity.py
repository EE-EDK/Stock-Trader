"""
@file velocity.py
@brief Velocity metric calculations for sentiment analysis
@details Implements mention velocity, sentiment velocity, and composite scoring algorithms
"""

from typing import List, Tuple, Dict, Optional
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def mention_velocity_pct(current: int, previous: int) -> float:
    """
    @brief Calculate percentage change in mentions
    @param current Current mention count
    @param previous Previous period mention count
    @return Percentage change (-100 to +inf)
    @details Returns 0 if both are zero, 100 if previous is zero but current is positive
    """
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return ((current - previous) / previous) * 100


def mention_velocity_trend(mention_history: List[Tuple[datetime, int]],
                           window_days: int = 7) -> float:
    """
    @brief Calculate trend direction using linear regression slope
    @param mention_history List of (timestamp, mention_count) tuples
    @param window_days Days to consider for trend
    @return Slope of trend line (positive = accelerating, negative = decelerating)
    @details Uses numpy polyfit for linear regression
    """
    if len(mention_history) < 2:
        return 0.0

    cutoff = datetime.now() - timedelta(days=window_days)
    recent = [(ts, count) for ts, count in mention_history if ts >= cutoff]

    if len(recent) < 2:
        return 0.0

    x = np.arange(len(recent))
    y = np.array([count for _, count in recent])

    try:
        slope, _ = np.polyfit(x, y, 1)
        return float(slope)
    except (np.linalg.LinAlgError, ValueError) as e:
        logger.warning(f"Could not calculate trend: {e}")
        return 0.0


def sentiment_velocity(sentiment_scores: List[float], window: int = 6) -> float:
    """
    @brief Calculate rate of change in sentiment scores
    @param sentiment_scores List of sentiment scores in chronological order
    @param window Smoothing window size
    @return Smoothed velocity of sentiment change
    @details Uses numpy gradient for derivative calculation
    """
    if len(sentiment_scores) < 2:
        return 0.0

    scores = np.array(sentiment_scores)
    velocity = np.gradient(scores)

    if len(velocity) < window:
        return float(np.mean(velocity))

    # Apply moving average smoothing
    smoothed = np.convolve(velocity, np.ones(window)/window, mode='valid')
    return float(smoothed[-1]) if len(smoothed) > 0 else 0.0


def volume_price_divergence(mention_changes: List[float],
                            price_changes: List[float]) -> float:
    """
    @brief Detect when social volume outpaces price movement
    @param mention_changes List of mention percentage changes
    @param price_changes List of price percentage changes
    @return Divergence score
    @details Positive = mentions growing faster (potential breakout)
             Negative = price growing faster (potential reversal)
    """
    if len(mention_changes) != len(price_changes) or len(mention_changes) == 0:
        return 0.0

    mention_arr = np.array(mention_changes)
    price_arr = np.array(price_changes)

    # Normalize to same scale
    mention_std = np.std(mention_arr)
    price_std = np.std(price_arr)

    mention_norm = mention_arr / (mention_std + 0.001)
    price_norm = price_arr / (price_std + 0.001)

    divergence = mention_norm - price_norm
    return float(np.mean(divergence))


def composite_score(mention_vel_24h: float,
                    mention_vel_7d: float,
                    sentiment_vel: float,
                    divergence: float,
                    weights: Optional[Dict[str, float]] = None) -> float:
    """
    @brief Calculate weighted composite velocity score
    @param mention_vel_24h 24-hour mention velocity percentage
    @param mention_vel_7d 7-day mention trend slope
    @param sentiment_vel Sentiment velocity
    @param divergence Volume/price divergence
    @param weights Optional custom weights dictionary
    @return Composite score on 0-100 scale
    @details Uses sigmoid-like transformation to handle outliers and normalize to 0-100
    """
    if weights is None:
        weights = {
            'mention_24h': 0.35,
            'mention_7d': 0.25,
            'sentiment': 0.25,
            'divergence': 0.15
        }

    def normalize(x: float, scale: float) -> float:
        """
        @brief Sigmoid-like normalization to 0-100 scale
        @param x Input value
        @param scale Scaling factor for steepness
        @return Normalized value between 0 and 100
        """
        # Clip input to prevent overflow in exp()
        clipped = np.clip(x / scale, -500, 500)
        return 100 / (1 + np.exp(-clipped))

    try:
        score = (
            weights['mention_24h'] * normalize(mention_vel_24h, 100) +
            weights['mention_7d'] * normalize(mention_vel_7d, 10) +
            weights['sentiment'] * normalize(sentiment_vel * 100, 20) +
            weights['divergence'] * normalize(divergence * 50, 25)
        )

        return min(100, max(0, score))
    except (ValueError, OverflowError) as e:
        logger.warning(f"Error calculating composite score: {e}")
        return 0.0


class VelocityCalculator:
    """
    @class VelocityCalculator
    @brief Main calculator for all velocity metrics
    @details Orchestrates velocity calculations using database queries
    """

    def __init__(self, database):
        """
        @brief Initialize velocity calculator
        @param database Database instance for querying data
        """
        self.db = database

    def calculate_ticker_velocity(self, ticker: str) -> Dict[str, float]:
        """
        @brief Calculate all velocity metrics for a single ticker
        @param ticker Stock ticker symbol
        @return Dictionary with all velocity metrics
        """
        try:
            # Get mention history
            mention_history = self.db.get_mention_history(ticker, days=7)

            # Calculate 24h velocity
            vel_24h = 0.0
            if len(mention_history) >= 2:
                current = mention_history[-1][1]  # Latest mentions
                # Find mention count from ~24h ago
                day_ago = datetime.now() - timedelta(hours=24)
                prev_mentions = [count for ts, count in mention_history if ts <= day_ago]
                if prev_mentions:
                    vel_24h = mention_velocity_pct(current, prev_mentions[-1])

            # Calculate 7d trend
            vel_7d = mention_velocity_trend(mention_history, window_days=7)

            # Get sentiment history and calculate velocity
            sentiment_history = self.db.get_sentiment_history(ticker, days=7)
            sent_vel = sentiment_velocity(sentiment_history, window=min(6, len(sentiment_history)))

            # Calculate divergence
            price_history = self.db.get_price_history(ticker, days=7)
            mention_changes = []
            price_changes = []

            if len(mention_history) >= 2:
                for i in range(1, len(mention_history)):
                    mention_changes.append(mention_velocity_pct(
                        mention_history[i][1],
                        mention_history[i-1][1]
                    ))

            if len(price_history) >= 2:
                for i in range(1, len(price_history)):
                    curr_price = price_history[i].get('price', 0)
                    prev_price = price_history[i-1].get('price', 0)
                    if prev_price is not None and prev_price > 0:
                        price_changes.append(((curr_price - prev_price) / prev_price) * 100)

            # Make sure arrays are same length for divergence
            min_len = min(len(mention_changes), len(price_changes))
            divergence = volume_price_divergence(
                mention_changes[:min_len],
                price_changes[:min_len]
            ) if min_len > 0 else 0.0

            # Calculate composite score
            comp_score = composite_score(vel_24h, vel_7d, sent_vel, divergence)

            return {
                'mention_velocity_24h': vel_24h,
                'mention_velocity_7d': vel_7d,
                'sentiment_velocity': sent_vel,
                'volume_price_divergence': divergence,
                'composite_score': comp_score
            }

        except Exception as e:
            logger.error(f"Error calculating velocity for {ticker}: {e}")
            return {
                'mention_velocity_24h': 0.0,
                'mention_velocity_7d': 0.0,
                'sentiment_velocity': 0.0,
                'volume_price_divergence': 0.0,
                'composite_score': 0.0
            }

    def calculate_all_velocities(self, min_mentions: int = 5) -> Dict[str, Dict[str, float]]:
        """
        @brief Calculate velocity metrics for all tracked tickers
        @param min_mentions Minimum mention count to include ticker
        @return Dictionary mapping ticker to velocity metrics
        """
        tickers = self.db.get_tracked_tickers(days=7)
        results = {}

        logger.info(f"Calculating velocity for {len(tickers)} tickers")

        for ticker in tickers:
            # Get latest mention data to filter low-activity tickers
            mention_history = self.db.get_mention_history(ticker, days=1)
            if mention_history and mention_history[-1][1] >= min_mentions:
                results[ticker] = self.calculate_ticker_velocity(ticker)

        logger.info(f"Calculated velocity for {len(results)} tickers with sufficient activity")
        return results
