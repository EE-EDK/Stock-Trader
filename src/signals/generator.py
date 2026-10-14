"""
@file generator.py
@brief Signal generation logic for trading opportunities
@details Analyzes velocity and insider data to generate ranked trading signals
"""

import copy
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from src.analysis.insider_grain import ClusterVerdict, evaluate_cluster

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """
    @class Signal
    @brief Data class representing a trading signal
    @details Contains all information about a potential trading opportunity
    """

    ticker: str  # Stock ticker symbol
    signal_type: str  # Type of signal (velocity_spike, insider_cluster, etc.)
    conviction_score: float  # Conviction score 0-100
    price_at_signal: float  # Stock price when signal was generated
    triggers: List[str]  # List of conditions that triggered this signal
    notes: str  # Human-readable description
    created_at: datetime  # Timestamp when signal was created


class SignalGenerator:
    """
    @class SignalGenerator
    @brief Generates trading signals based on velocity and insider data
    @details Applies thresholds to identify high-conviction opportunities
    """

    # Default thresholds (can be overridden via config)
    DEFAULT_THRESHOLDS = {
        "velocity_spike": {
            "mention_vel_24h_min": 100,  # 100%+ increase in 24h
            "composite_score_min": 60,  # Minimum composite score
        },
        "insider_cluster": {
            "min_insiders": 2,  # At least 2 insiders buying
            "lookback_days": 14,  # Within 14 days
            "min_value_total": 100000,  # $100k+ total
        },
        "sentiment_flip": {
            "sentiment_delta_min": 0.3,  # 30%+ shift in sentiment
            "lookback_days": 7,
        },
        "combined": {
            "velocity_score_min": 50,  # Lower threshold when combined
            "requires_insider": True,  # Must have insider activity
        },
    }

    def __init__(self, thresholds: Optional[Dict] = None):
        """
        @brief Initialize signal generator
        @param thresholds Optional custom threshold configuration
        """
        defaults = copy.deepcopy(self.DEFAULT_THRESHOLDS)
        if thresholds:
            for key, val in thresholds.items():
                if isinstance(val, dict) and key in defaults and isinstance(defaults[key], dict):
                    defaults[key].update(val)
                else:
                    defaults[key] = val
        self.thresholds = defaults

    def generate_signals(
        self,
        velocity_data: Dict[str, Dict[str, float]],
        insider_data: Dict[str, List[Dict[str, Any]]],
        price_data: Dict[str, Dict[str, Any]],
        technical_data: Optional[Dict[str, Dict[str, Any]]] = None,
        sentiment_data: Optional[Dict[str, Dict[str, Any]]] = None,
        signal_date: Optional[datetime] = None,
    ) -> List[Signal]:
        """
        @brief Main signal generation logic with FREE data sources
        @param velocity_data Dict mapping ticker to velocity metrics
        @param insider_data Dict mapping ticker to list of insider trades
        @param price_data Dict mapping ticker to current price info
        @param technical_data Dict mapping ticker to technical analysis
        @param sentiment_data Dict mapping ticker to news sentiment
        @param signal_date Optional datetime for signal generation
        @return List of Signal objects sorted by conviction score (descending)
        """
        signals = []

        # Default to empty dicts if not provided
        technical_data = technical_data or {}
        sentiment_data = sentiment_data or {}

        # Iterate the UNION of velocity and insider tickers, not velocity_data
        # alone. A ticker with a qualifying insider cluster but no mention
        # velocity (no ApeWisdom chatter) used to be structurally invisible --
        # evaluate_cluster() ran, could return fires=True, and the result was
        # simply never reached because the ticker was never a loop candidate.
        # Measured 2026-08-24: 44 live qualifying clusters, most unreachable.
        all_tickers = set(velocity_data.keys()) | set(insider_data.keys())
        for ticker in all_tickers:
            vel = velocity_data.get(ticker, {})
            insiders = insider_data.get(ticker, [])
            price = price_data.get(ticker, {})
            tech = technical_data.get(ticker, {})
            sentiment = sentiment_data.get(ticker, {})

            triggers = []
            conviction = 0.0

            # Check velocity spike
            if self._check_velocity_spike(vel):
                triggers.append("velocity_spike")
                conviction += 20

            # Evaluate the insider cluster once and reuse the verdict for the
            # note, so the trigger and the text it produces can never disagree.
            cluster_verdict = evaluate_cluster(insiders, self.thresholds)
            if cluster_verdict.fires:
                triggers.append("insider_cluster")
                conviction += 25

            # Check sentiment flip
            if self._check_sentiment_flip(vel):
                triggers.append("sentiment_flip")
                conviction += 10

            # Technical breakout detection
            if tech and self._check_technical_breakout(tech):
                triggers.append("technical_breakout")
                conviction += 15

            # RSI oversold signal
            if tech and self._check_rsi_oversold(tech):
                triggers.append("rsi_oversold")
                conviction += 10

            # Golden cross
            if tech and tech.get("golden_cross"):
                triggers.append("golden_cross")
                conviction += 10

            # Positive news sentiment
            if sentiment and self._check_positive_sentiment(sentiment):
                triggers.append("news_sentiment_bullish")
                conviction += 10

            # Add technical score contribution (0-100 scale)
            if (
                tech
                and "technical_score" in tech
                and tech["technical_score"] is not None
            ):
                conviction += tech["technical_score"] * 0.15  # 15% weight

            # Boost for combined signals
            if len(triggers) >= 2:
                conviction += 10

            # Add base composite score contribution
            conviction += (vel.get("composite_score") or 0) * 0.2

            # Cap at 100
            conviction = min(100, conviction)

            # Generate signal if triggers exist and conviction meets minimum
            min_sig_conviction = (self.thresholds.get("minimum_conviction") or 40)
            if triggers and conviction >= min_sig_conviction:
                notes_text = self._generate_notes(
                    ticker, vel, insiders, triggers, tech, sentiment,
                    cluster_verdict=cluster_verdict,
                )
                sig_type = "combined" if len(triggers) > 1 else triggers[0]
                created = signal_date if signal_date else datetime.now()
                signals.append(
                    Signal(
                        ticker=ticker,
                        signal_type=sig_type,
                        conviction_score=conviction,
                        price_at_signal=(price.get("price") or 0.0),
                        triggers=triggers,
                        notes=notes_text,
                        created_at=created,
                    )
                )

        # Sort by conviction descending
        signals.sort(key=lambda s: s.conviction_score, reverse=True)

        insider_only = len(all_tickers) - len(velocity_data)
        logger.info(
            f"Generated {len(signals)} signals "
            f"from {len(all_tickers)} tickers "
            f"({len(velocity_data)} velocity, {insider_only} insider-only)"
        )
        return signals

    def _check_velocity_spike(self, vel: Dict[str, float]) -> bool:
        """
        @brief Check if velocity meets spike threshold
        @param vel Velocity metrics dictionary
        @return True if velocity spike criteria are met
        """
        threshold = self.thresholds.get("velocity_spike", {})
        vel_24h = (vel.get("mention_velocity_24h") or 0)
        vel_min = (threshold.get("mention_vel_24h_min") or 100)
        comp_score = (vel.get("composite_score") or 0)
        comp_min = (threshold.get("composite_score_min") or 60)

        return vel_24h >= vel_min and comp_score >= comp_min

    def _check_insider_cluster(self, insiders: List[Dict[str, Any]]) -> bool:
        """
        @brief Check if insider buying meets cluster criteria.
        @param insiders List of insider trade dictionaries for one ticker
        @return True if insider cluster criteria are met
        @details Delegates to src.analysis.insider_grain.evaluate_cluster, which
                 keeps Form 4 filings and OpenInsider cluster roll-ups on separate
                 grains (this method used to count both, so one CEO purchase read
                 as a seven-buyer cluster) and drops fills the open market did not
                 price (offerings, exercises at strike).
        @see src/analysis/insider_grain.py
        """
        return evaluate_cluster(insiders, self.thresholds).fires

    def _check_sentiment_flip(self, vel: Dict[str, float]) -> bool:
        """
        @brief Check if sentiment has flipped significantly
        @param vel Velocity metrics dictionary
        @return True if sentiment flip criteria are met
        """
        threshold = self.thresholds.get("sentiment_flip", {})
        sentiment_delta_min = (threshold.get("sentiment_delta_min") or 0.3)

        return abs(vel.get("sentiment_velocity") or 0) >= sentiment_delta_min

    def _generate_notes(
        self,
        ticker: str,
        vel: Dict[str, float],
        insiders: List[Dict[str, Any]],
        triggers: List[str],
        tech: Optional[Dict[str, Any]] = None,
        sentiment: Optional[Dict[str, Any]] = None,
        cluster_verdict: Optional[ClusterVerdict] = None,
    ) -> str:
        """
        @brief Generate human-readable notes for the signal
        @param ticker Stock ticker symbol
        @param vel Velocity metrics
        @param insiders List of insider trades
        @param triggers List of trigger types
        @param tech Technical analysis data
        @param sentiment Sentiment analysis data
        @param cluster_verdict Verdict already computed by generate_signals.
               Pass it so the note cannot disagree with the trigger that fired;
               omitted, it is recomputed from `insiders`.
        @return Formatted note string
        """
        notes = []

        if "velocity_spike" in triggers:
            vel_24h = (vel.get("mention_velocity_24h") or 0)
            notes.append(f"Mentions up {vel_24h:.0f}% in 24h")

        if "insider_cluster" in triggers:
            # Grain-aware: the total comes from one grain only, never a
            # roll-up plus the individual filings it already summarises.
            verdict = cluster_verdict or evaluate_cluster(insiders, self.thresholds)
            notes.append(verdict.note())

        if "sentiment_flip" in triggers:
            sent_vel = (vel.get("sentiment_velocity") or 0)
            direction = "bullish" if sent_vel > 0 else "bearish"
            notes.append(f"Sentiment flipping {direction}")

        if "technical_breakout" in triggers:
            notes.append("Technical breakout detected")

        if "rsi_oversold" in triggers and tech:
            rsi = (tech.get("rsi_14") or 0)
            notes.append(f"RSI oversold ({rsi:.1f})")

        if "golden_cross" in triggers:
            notes.append("Golden cross (SMA)")

        if "news_sentiment_bullish" in triggers and sentiment:
            score = (sentiment.get("sentiment_score") or 0)
            notes.append(f"News bullish ({score:.2f})")

        # Add composite score
        comp_score = (vel.get("composite_score") or 0)
        notes.append(f"Composite: {comp_score:.0f}")

        return " | ".join(notes)

    def _check_technical_breakout(self, tech: Dict[str, Any]) -> bool:
        """
        @brief Check if stock is breaking out (technical analysis)
        @param tech Technical analysis dictionary
        @return True if breakout detected
        """
        return tech.get("breakout_detected", False)

    def _check_rsi_oversold(self, tech: Dict[str, Any]) -> bool:
        """
        @brief Check if RSI indicates oversold condition
        @param tech Technical analysis dictionary
        @return True if RSI < 30 (oversold)
        """
        rsi = tech.get("rsi_14", 50)
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
        score = sentiment.get("sentiment_score", 0)
        if score is None:
            score = 0
        label = sentiment.get("sentiment_label", "")
        if label is None:
            label = ""

        label_lower = label.lower()
        return (
            score > 0.15
            or "bullish" in label_lower
            or "positive" in label_lower
        )

    def filter_by_conviction(
        self, signals: List[Signal], min_conviction: float = 40
    ) -> List[Signal]:
        """
        @brief Filter signals by minimum conviction score
        @param signals List of signals to filter
        @param min_conviction Minimum conviction score threshold
        @return Filtered list of signals
        """
        filtered = [s for s in signals if s.conviction_score >= min_conviction]
        logger.info(
            f"Filtered {len(filtered)} signals "
            f"above {min_conviction} conviction"
        )
        return filtered

    def get_top_signals(
        self, signals: List[Signal], n: int = 10
    ) -> List[Signal]:
        """
        @brief Get top N signals by conviction
        @param signals List of signals
        @param n Number of top signals to return
        @return List of top N signals
        """
        return signals[:n]

    def group_by_type(
        self, signals: List[Signal]
    ) -> Dict[str, List[Signal]]:
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
