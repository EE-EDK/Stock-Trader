"""
@file charts.py
@brief Chart generation for visualization of velocity and signals
@details Creates matplotlib visualizations for mention trends, velocity, and signal analysis
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import io
import logging

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    @class ChartGenerator
    @brief Generate charts for trading signals and velocity metrics
    @details Creates various chart types using matplotlib for analysis and reporting
    """

    def __init__(self, style: str = 'seaborn-v0_8-darkgrid'):
        """
        @brief Initialize chart generator
        @param style Matplotlib style to use
        """
        try:
            plt.style.use(style)
        except:
            logger.warning(f"Style {style} not available, using default")

        self.fig_size = (12, 6)
        self.dpi = 100

    def create_mention_trend_chart(self,
                                   ticker: str,
                                   mention_history: List[Tuple[datetime, int]]) -> Optional[bytes]:
        """
        @brief Create line chart of mention count over time
        @param ticker Stock ticker symbol
        @param mention_history List of (timestamp, mentions) tuples
        @return PNG image as bytes or None on error
        """
        if len(mention_history) < 2:
            logger.warning(f"Insufficient data for {ticker} mention chart")
            return None

        try:
            fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)

            dates = [ts for ts, _ in mention_history]
            mentions = [count for _, count in mention_history]

            ax.plot(dates, mentions, marker='o', linewidth=2, markersize=6)
            ax.fill_between(dates, mentions, alpha=0.3)

            ax.set_title(f'{ticker} - Mention Trend (7 Days)', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Mention Count', fontsize=12)
            ax.grid(True, alpha=0.3)

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45)

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except Exception as e:
            logger.error(f"Error creating mention trend chart: {e}")
            plt.close('all')
            return None

    def create_velocity_comparison_chart(self,
                                        velocity_data: Dict[str, Dict[str, float]],
                                        top_n: int = 10) -> Optional[bytes]:
        """
        @brief Create bar chart comparing top tickers by composite score
        @param velocity_data Dictionary mapping ticker to velocity metrics
        @param top_n Number of top tickers to show
        @return PNG image as bytes or None on error
        """
        if not velocity_data:
            logger.warning("No velocity data for comparison chart")
            return None

        try:
            # Sort by composite score and take top N
            sorted_data = sorted(
                velocity_data.items(),
                key=lambda x: x[1].get('composite_score', 0),
                reverse=True
            )[:top_n]

            tickers = [ticker for ticker, _ in sorted_data]
            scores = [data.get('composite_score', 0) for _, data in sorted_data]

            fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)

            bars = ax.barh(tickers, scores)

            # Color bars based on score
            for i, (bar, score) in enumerate(zip(bars, scores)):
                if score >= 70:
                    bar.set_color('#00c853')  # Green
                elif score >= 50:
                    bar.set_color('#ffc107')  # Yellow
                else:
                    bar.set_color('#ff5722')  # Red

            ax.set_title(f'Top {top_n} Tickers by Composite Score', fontsize=16, fontweight='bold')
            ax.set_xlabel('Composite Score', fontsize=12)
            ax.set_ylabel('Ticker', fontsize=12)
            ax.grid(True, alpha=0.3, axis='x')

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except Exception as e:
            logger.error(f"Error creating velocity comparison chart: {e}")
            plt.close('all')
            return None

    def create_signal_distribution_chart(self, signals: List[Any]) -> Optional[bytes]:
        """
        @brief Create pie chart showing distribution of signal types
        @param signals List of Signal objects
        @return PNG image as bytes or None on error
        """
        if not signals:
            logger.warning("No signals for distribution chart")
            return None

        try:
            # Count signal types
            type_counts: Dict[str, int] = {}
            for signal in signals:
                signal_type = signal.signal_type
                type_counts[signal_type] = type_counts.get(signal_type, 0) + 1

            labels = list(type_counts.keys())
            sizes = list(type_counts.values())

            fig, ax = plt.subplots(figsize=(8, 8), dpi=self.dpi)

            colors = ['#00c853', '#ffc107', '#ff5722', '#2196f3', '#9c27b0']
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors[:len(labels)])
            ax.set_title('Signal Type Distribution', fontsize=16, fontweight='bold')

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except Exception as e:
            logger.error(f"Error creating signal distribution chart: {e}")
            plt.close('all')
            return None

    def create_price_mention_correlation_chart(self,
                                               ticker: str,
                                               price_history: List[Dict[str, Any]],
                                               mention_history: List[Tuple[datetime, int]]) -> Optional[bytes]:
        """
        @brief Create dual-axis chart showing price vs mentions
        @param ticker Stock ticker symbol
        @param price_history List of price data dictionaries
        @param mention_history List of (timestamp, mentions) tuples
        @return PNG image as bytes or None on error
        """
        if not price_history or not mention_history:
            logger.warning(f"Insufficient data for {ticker} correlation chart")
            return None

        try:
            fig, ax1 = plt.subplots(figsize=self.fig_size, dpi=self.dpi)

            # Price on left axis
            price_dates = [p['collected_at'] for p in price_history]
            prices = [p['price'] for p in price_history]

            ax1.plot(price_dates, prices, color='#2196f3', marker='o', label='Price')
            ax1.set_xlabel('Date', fontsize=12)
            ax1.set_ylabel('Price ($)', fontsize=12, color='#2196f3')
            ax1.tick_params(axis='y', labelcolor='#2196f3')
            ax1.grid(True, alpha=0.3)

            # Mentions on right axis
            ax2 = ax1.twinx()
            mention_dates = [ts for ts, _ in mention_history]
            mentions = [count for _, count in mention_history]

            ax2.plot(mention_dates, mentions, color='#ff5722', marker='s', label='Mentions')
            ax2.set_ylabel('Mention Count', fontsize=12, color='#ff5722')
            ax2.tick_params(axis='y', labelcolor='#ff5722')

            # Title and legend
            ax1.set_title(f'{ticker} - Price vs Mentions', fontsize=16, fontweight='bold')

            # Format dates
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45)

            # Combined legend
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except Exception as e:
            logger.error(f"Error creating correlation chart: {e}")
            plt.close('all')
            return None

    def create_conviction_scatter_chart(self, signals: List[Any]) -> Optional[bytes]:
        """
        @brief Create scatter plot of signals by conviction and price
        @param signals List of Signal objects
        @return PNG image as bytes or None on error
        """
        if not signals:
            logger.warning("No signals for scatter chart")
            return None

        try:
            fig, ax = plt.subplots(figsize=self.fig_size, dpi=self.dpi)

            prices = [s.price_at_signal for s in signals]
            convictions = [s.conviction_score for s in signals]
            tickers = [s.ticker for s in signals]

            # Color by conviction
            colors = ['#00c853' if c >= 70 else '#ffc107' if c >= 50 else '#ff5722'
                     for c in convictions]

            scatter = ax.scatter(prices, convictions, c=colors, s=200, alpha=0.6, edgecolors='black')

            # Add ticker labels
            for i, ticker in enumerate(tickers):
                ax.annotate(ticker, (prices[i], convictions[i]),
                           fontsize=9, fontweight='bold',
                           ha='center', va='center')

            ax.set_xlabel('Price at Signal ($)', fontsize=12)
            ax.set_ylabel('Conviction Score', fontsize=12)
            ax.set_title('Signal Conviction vs Price', fontsize=16, fontweight='bold')
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except Exception as e:
            logger.error(f"Error creating scatter chart: {e}")
            plt.close('all')
            return None

    def save_chart_to_file(self, chart_data: bytes, filepath: str) -> bool:
        """
        @brief Save chart bytes to file
        @param chart_data Chart image as bytes
        @param filepath Output file path
        @return True if saved successfully, False otherwise
        """
        try:
            with open(filepath, 'wb') as f:
                f.write(chart_data)
            logger.info(f"Chart saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving chart to {filepath}: {e}")
            return False
