"""
@file generator.py
@brief Signal generation logic for trading opportunities
@details Analyzes velocity and insider data to generate ranked trading signals
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """
    @class Signal
    @brief Data class representing a trading signal
    @details Contains all information about a potential trading opportunity
    """
    ticker: str  ## Stock ticker symbol
    signal_type: str  ## Type of signal (velocity_spike, insider_cluster, etc.)
    conviction_score: float  ## Conviction score 0-100
    price_at_signal: float  ## Stock price when signal was generated
    triggers: List[str]  ## List of conditions that triggered this signal
    notes: str  ## Human-readable description
    created_at: datetime  ## Timestamp when signal was created


class SignalGenerator:
    """
    @class SignalGenerator
    @brief Generates trading signals based on velocity and insider data
    @details Applies configurable thresholds to identify high-conviction opportunities
    """

    # Default thresholds (can be overridden via config)
    DEFAULT_THRESHOLDS = {
        'velocity_spike': {
            'mention_vel_24h_min': 100,     # 100%+ increase in 24h
            'composite_score_min': 60,       # Minimum composite score
        },
        'insider_cluster': {
            'min_insiders': 2,               # At least 2 insiders buying
            'lookback_days': 14,             # Within 14 days
            'min_value_total': 100000,       # $100k+ total
        },
        'sentiment_flip': {
            'sentiment_delta_min': 0.3,      # 30%+ shift in sentiment
            'lookback_days': 7,
        },
        'combined': {
            'velocity_score_min': 50,        # Lower threshold when combined
            'requires_insider': True,        # Must have insider activity
        }
    }

    def __init__(self, thresholds: Optional[Dict] = None):
        """
        @brief Initialize signal generator
        @param thresholds Optional custom threshold configuration
        """
        self.thresholds = thresholds if thresholds else self.DEFAULT_THRESHOLDS.copy()

    def generate_signals(self,
                         velocity_data: Dict[str, Dict[str, float]],
                         insider_data: Dict[str, List[Dict[str, Any]]],
                         price_data: Dict[str, Dict[str, Any]],
                         technical_data: Optional[Dict[str, Dict[str, Any]]] = None,
                         sentiment_data: Optional[Dict[str, Dict[str, Any]]] = None,
                         reddit_data: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Signal]:
        """
        @brief Main signal generation logic with FREE data sources
        @param velocity_data Dictionary mapping ticker to velocity metrics
        @param insider_data Dictionary mapping ticker to list of insider trades
        @param price_data Dictionary mapping ticker to current price info
        @param technical_data Dictionary mapping ticker to technical analysis (RSI, MACD, etc.)
        @param sentiment_data Dictionary mapping ticker to news sentiment (Alpha Vantage/VADER)
        @param reddit_data Dictionary mapping ticker to Reddit mentions/sentiment
        @return List of Signal objects sorted by conviction score (descending)
        """
        signals = []

        # Default to empty dicts if not provided
        technical_data = technical_data or {}
        sentiment_data = sentiment_data or {}
        reddit_data = reddit_data or {}

        for ticker in velocity_data.keys():
            vel = velocity_data[ticker]
            insiders = insider_data.get(ticker, [])
            price = price_data.get(ticker, {})
            tech = technical_data.get(ticker, {})
            sentiment = sentiment_data.get(ticker, {})
            reddit = reddit_data.get(ticker, {})

            triggers = []
            conviction = 0.0

            # Check velocity spike
            if self._check_velocity_spike(vel):
                triggers.append('velocity_spike')
                conviction += 30

            # Check insider cluster
            if self._check_insider_cluster(insiders):
                triggers.append('insider_cluster')
                conviction += 40

            # Check sentiment flip
            if self._check_sentiment_flip(vel):
                triggers.append('sentiment_flip')
                conviction += 20

            # NEW: Technical breakout detection
            if tech and self._check_technical_breakout(tech):
                triggers.append('technical_breakout')
                conviction += 25

            # NEW: RSI oversold signal
            if tech and self._check_rsi_oversold(tech):
                triggers.append('rsi_oversold')
                conviction += 15

            # NEW: Golden cross
            if tech and tech.get('golden_cross'):
                triggers.append('golden_cross')
                conviction += 20

            # NEW: Positive news sentiment
            if sentiment and self._check_positive_sentiment(sentiment):
                triggers.append('news_sentiment_bullish')
                conviction += 15

            # NEW: Reddit viral signal
            if reddit and self._check_reddit_viral(reddit):
                triggers.append('reddit_viral')
                conviction += 10

            # Add technical score contribution (0-100 scale)
            if tech and 'technical_score' in tech and tech['technical_score'] is not None:
                conviction += tech['technical_score'] * 0.2  # 20% weight

            # Boost for combined signals
            if len(triggers) >= 2:
                conviction += 15

            # Add base composite score contribution
            conviction += vel.get('composite_score', 0) * 0.3

            # Cap at 100
            conviction = min(100, conviction)

            # Generate signal if triggers exist and conviction meets minimum
            if triggers and conviction >= 40:
                signals.append(Signal(
                    ticker=ticker,
                    signal_type='combined' if len(triggers) > 1 else triggers[0],
                    conviction_score=conviction,
                    price_at_signal=price.get('price', 0.0),
                    triggers=triggers,
                    notes=self._generate_notes(ticker, vel, insiders, triggers, tech, sentiment, reddit),
                    created_at=datetime.now()
                ))

        # Sort by conviction descending
        signals.sort(key=lambda s: s.conviction_score, reverse=True)

        logger.info(f"Generated {len(signals)} signals from {len(velocity_data)} tickers")
        return signals

    def _check_velocity_spike(self, vel: Dict[str, float]) -> bool:
        """
        @brief Check if velocity meets spike threshold
        @param vel Velocity metrics dictionary
        @return True if velocity spike criteria are met
        """
        threshold = self.thresholds.get('velocity_spike', {})
        return (
            vel.get('mention_velocity_24h', 0) >= threshold.get('mention_vel_24h_min', 100) and
            vel.get('composite_score', 0) >= threshold.get('composite_score_min', 60)
        )

    def _check_insider_cluster(self, insiders: List[Dict[str, Any]]) -> bool:
        """
        @brief Check if insider buying meets cluster criteria
        @param insiders List of insider trade dictionaries
        @return True if insider cluster criteria are met
        """
        if not insiders:
            return False

        threshold = self.thresholds.get('insider_cluster', {})
        lookback_days = threshold.get('lookback_days', 14)
        min_insiders = threshold.get('min_insiders', 2)
        min_value_total = threshold.get('min_value_total', 100000)

        cutoff = datetime.now() - timedelta(days=lookback_days)

        # Filter for recent purchases
        recent_buys = []
        for insider in insiders:
            trade_date = insider.get('trade_date')
            if isinstance(trade_date, str):
                try:
                    trade_date = datetime.fromisoformat(trade_date)
                except ValueError:
                    continue

            if (insider.get('trade_type') == 'P' and
                trade_date and trade_date >= cutoff):
                recent_buys.append(insider)

        if len(recent_buys) < min_insiders:
            return False

        total_value = sum(buy.get('value', 0) for buy in recent_buys)
        return total_value >= min_value_total

    def _check_sentiment_flip(self, vel: Dict[str, float]) -> bool:
        """
        @brief Check if sentiment has flipped significantly
        @param vel Velocity metrics dictionary
        @return True if sentiment flip criteria are met
        """
        threshold = self.thresholds.get('sentiment_flip', {})
        sentiment_delta_min = threshold.get('sentiment_delta_min', 0.3)

        return abs(vel.get('sentiment_velocity', 0)) >= sentiment_delta_min

    def _generate_notes(self,
                       ticker: str,
                       vel: Dict[str, float],
                       insiders: List[Dict[str, Any]],
                       triggers: List[str],
                       tech: Optional[Dict[str, Any]] = None,
                       sentiment: Optional[Dict[str, Any]] = None,
                       reddit: Optional[Dict[str, Any]] = None) -> str:
        """
        @brief Generate human-readable notes for the signal
        @param ticker Stock ticker symbol
        @param vel Velocity metrics
        @param insiders List of insider trades
        @param triggers List of trigger types
        @param tech Technical analysis data
        @param sentiment Sentiment analysis data
        @param reddit Reddit data
        @return Formatted note string
        """
        notes = []

        if 'velocity_spike' in triggers:
            vel_24h = vel.get('mention_velocity_24h', 0)
            notes.append(f"Mentions up {vel_24h:.0f}% in 24h")

        if 'insider_cluster' in triggers:
            buy_count = len([i for i in insiders if i.get('trade_type') == 'P'])
            total_val = sum(i.get('value', 0) for i in insiders if i.get('trade_type') == 'P')
            notes.append(f"{buy_count} insiders bought ${total_val:,.0f} recently")

        if 'sentiment_flip' in triggers:
            sent_vel = vel.get('sentiment_velocity', 0)
            direction = "bullish" if sent_vel > 0 else "bearish"
            notes.append(f"Sentiment flipping {direction}")

        if 'technical_breakout' in triggers:
            notes.append("Technical breakout detected")

        if 'rsi_oversold' in triggers and tech:
            rsi = tech.get('rsi_14', 0)
            notes.append(f"RSI oversold ({rsi:.1f})")

        if 'golden_cross' in triggers:
            notes.append("Golden cross (SMA)")

        if 'news_sentiment_bullish' in triggers and sentiment:
            score = sentiment.get('sentiment_score', 0)
            notes.append(f"News bullish ({score:.2f})")

        if 'reddit_viral' in triggers and reddit:
            mentions = reddit.get('mention_count', 0)
            notes.append(f"Reddit viral ({mentions} mentions)")

        # Add composite score
        comp_score = vel.get('composite_score', 0)
        notes.append(f"Composite: {comp_score:.0f}")

        return " | ".join(notes)

    def _check_technical_breakout(self, tech: Dict[str, Any]) -> bool:
        """
        @brief Check if stock is breaking out (technical analysis)
        @param tech Technical analysis dictionary
        @return True if breakout detected
        """
        return tech.get('breakout_detected', False)

    def _check_rsi_oversold(self, tech: Dict[str, Any]) -> bool:
        """
        @brief Check if RSI indicates oversold condition
        @param tech Technical analysis dictionary
        @return True if RSI < 30 (oversold)
        """
        rsi = tech.get('rsi_14', 50)
        if rsi is None:
            return False
        return rsi < 30

    def _check_positive_sentiment(self, sentiment: Dict[str, Any]) -> bool:
        """
        @brief Check if news sentiment is positive
        @param sentiment Sentiment analysis dictionary
        @return True if sentiment is bullish
        """
        # Works with both Alpha Vantage and VADER sentiment
        score = sentiment.get('sentiment_score', 0)
        if score is None:
            score = 0
        label = sentiment.get('sentiment_label', '')
        if label is None:
            label = ''

        return score > 0.15 or 'bullish' in label.lower() or 'positive' in label.lower()

    def _check_reddit_viral(self, reddit: Dict[str, Any]) -> bool:
        """
        @brief Check if ticker is going viral on Reddit
        @param reddit Reddit data dictionary
        @return True if mention count is high
        """
        mention_count = reddit.get('mention_count', 0)
        if mention_count is None:
            return False
        return mention_count >= 10  # 10+ mentions indicates viral potential

    def filter_by_conviction(self, signals: List[Signal], min_conviction: float = 40) -> List[Signal]:
        """
        @brief Filter signals by minimum conviction score
        @param signals List of signals to filter
        @param min_conviction Minimum conviction score threshold
        @return Filtered list of signals
        """
        filtered = [s for s in signals if s.conviction_score >= min_conviction]
        logger.info(f"Filtered {len(filtered)}/{len(signals)} signals above {min_conviction} conviction")
        return filtered

    def get_top_signals(self, signals: List[Signal], n: int = 10) -> List[Signal]:
        """
        @brief Get top N signals by conviction
        @param signals List of signals
        @param n Number of top signals to return
        @return List of top N signals
        """
        return signals[:n]

    def group_by_type(self, signals: List[Signal]) -> Dict[str, List[Signal]]:
        """
        @brief Group signals by signal type
        @param signals List of signals
        @return Dictionary mapping signal type to list of signals
        """
        grouped: Dict[str, List[Signal]] = {}

        for signal in signals:
            signal_type = signal.signal_type
            if signal_type not in grouped:
                grouped[signal_type] = []
            grouped[signal_type].append(signal)

        return grouped
