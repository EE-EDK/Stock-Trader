"""
@file dashboard_v2.py
@brief Modern HTML dashboard generator with charts and visual analytics
@details Creates a polished, data-rich HTML dashboard with graphs and visual representations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import json


class ModernDashboardGenerator:
    """
    @class ModernDashboardGenerator
    @brief Generate modern, chart-heavy HTML dashboard
    @details Professional dashboard with navy/leather color scheme and data visualization
    """

    def __init__(self, output_dir: str = "reports", project_root: str = None):
        """Initialize dashboard generator"""
        if project_root:
            self.output_dir = Path(project_root) / output_dir
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate(self,
                signals: List[Any],
                velocity_data: Dict[str, Dict],
                technical_data: Dict[str, Dict] = None,
                sentiment_data: Dict[str, Dict] = None,
                paper_trading_stats: Dict = None,
                macro_indicators: Dict = None,
                market_assessment: Dict = None,
                db = None) -> str:
        """Generate complete modern HTML dashboard with enhanced analytics"""

        technical_data = technical_data or {}
        sentiment_data = sentiment_data or {}
        paper_trading_stats = paper_trading_stats or {}
        macro_indicators = macro_indicators or {}
        market_assessment = market_assessment or {}

        # Calculate market health score (0-100)
        market_score = self._calculate_market_score(market_assessment, macro_indicators)

        # Get additional data from database if available
        top_velocity = []
        insider_trades = []
        insider_ratio = {'buy': 0, 'sell': 0}
        social_mentions = []
        sentiment_shifts = []
        signal_performance = []
        equity_curve = []
        emerging_tickers = []
        vix_history = []
        treasury_history = []

        if db:
            try:
                top_velocity = db.get_top_velocity_gainers(limit=10, hours=24)
                insider_trades = db.get_recent_insider_trades_detailed(days=30, limit=20)
                insider_ratio = db.get_insider_buy_sell_ratio(days=30)
                social_mentions = db.get_top_social_mentions(limit=10, hours=24)
                sentiment_shifts = db.get_sentiment_shifts(min_change=0.3, days=7)
                signal_performance = db.get_signal_performance_by_type()
                equity_curve = db.get_paper_trading_equity_curve(days=90)
                emerging_tickers = db.get_emerging_tickers(hours=24, min_mentions=5)
                vix_history = db.get_macro_indicator_history('VIX', days=30)
                treasury_history = db.get_macro_indicator_history('TREASURY_10Y', days=30)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not fetch enhanced dashboard data: {e}")

        # Generate sections
        header_html = self._generate_header(market_score, market_assessment)
        overview_html = self._generate_overview_stats(signals, velocity_data, paper_trading_stats)

        # NEW: Top Movers section
        top_movers_html = self._generate_top_movers_section(top_velocity, insider_trades, social_mentions, sentiment_shifts)

        signals_html = self._generate_signals_section(signals, velocity_data, technical_data, sentiment_data)

        # NEW: Enhanced sections
        insider_panel_html = self._generate_insider_panel(insider_trades, insider_ratio)
        technical_deepdive_html = self._generate_technical_deepdive(technical_data, velocity_data)
        performance_html = self._generate_performance_section(signal_performance, equity_curve, paper_trading_stats)
        sentiment_breakdown_html = self._generate_sentiment_breakdown(sentiment_data, sentiment_shifts)
        macro_trends_html = self._generate_macro_trends(vix_history, treasury_history, macro_indicators, market_assessment)
        social_insights_html = self._generate_social_insights(social_mentions, emerging_tickers, top_velocity)

        # Original sections
        activity_html = self._generate_sentiment_section(sentiment_data)
        technical_html = self._generate_technical_section(technical_data)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Signals Dashboard - {datetime.now().strftime('%B %d, %Y')}</title>
    {self._generate_styles()}
    {self._generate_chart_scripts()}
</head>
<body>
    {header_html}
    <div class="container">
        {overview_html}
        {top_movers_html}
        {signals_html}
        {insider_panel_html}
        {technical_deepdive_html}
        {performance_html}
        {sentiment_breakdown_html}
        {macro_trends_html}
        {social_insights_html}
        {activity_html}
        {technical_html}
    </div>
    {self._generate_footer()}
</body>
</html>"""

        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f'dashboard_{timestamp}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filename)

    def _calculate_market_score(self, assessment: Dict, indicators: Dict) -> int:
        """Calculate market health score 0-100"""
        if not assessment:
            return 50  # Neutral

        risk_level = assessment.get('risk_level', 'MEDIUM')
        risk_score = assessment.get('risk_score', 50)

        # Invert risk score to health score (low risk = high health)
        health_score = 100 - risk_score
        return max(0, min(100, int(health_score)))

    def _generate_styles(self) -> str:
        """Generate modern CSS styles"""
        return """<style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --navy: #0F1626;
            --leather: #AB987A;
            --coral: #FF533D;
            --eggshell: #F5F5F5;
            --white: #FFFFFF;
            --dark-text: #1a1a1a;
            --light-text: #6b7280;
            --success: #10b981;
            --warning: #f59e0b;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--eggshell);
            min-height: 100vh;
            color: var(--dark-text);
            line-height: 1.6;
        }

        .header {
            background: var(--navy);
            color: var(--white);
            padding: 40px 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 36px;
            font-weight: 300;
            letter-spacing: 6px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }

        .header p {
            opacity: 0.7;
            font-size: 12px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .market-score {
            background: var(--leather);
            color: var(--white);
            padding: 30px 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 40px;
            flex-wrap: wrap;
        }

        .score-gauge {
            position: relative;
            width: 120px;
            height: 120px;
        }

        .score-circle {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: conic-gradient(
                var(--white) 0deg,
                var(--white) calc(var(--score) * 3.6deg),
                rgba(255,255,255,0.2) calc(var(--score) * 3.6deg),
                rgba(255,255,255,0.2) 360deg
            );
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .score-inner {
            width: 85%;
            height: 85%;
            border-radius: 50%;
            background: var(--leather);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .score-value {
            font-size: 42px;
            font-weight: 300;
            letter-spacing: -2px;
        }

        .score-label {
            font-size: 10px;
            letter-spacing: 2px;
            text-transform: uppercase;
            opacity: 0.8;
        }

        .score-info {
            text-align: left;
        }

        .score-info h3 {
            font-size: 14px;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 10px;
            opacity: 0.9;
        }

        .score-info p {
            opacity: 0.8;
            font-size: 13px;
            margin: 5px 0;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 20px;
        }

        .section {
            background: var(--white);
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .section-title {
            font-size: 20px;
            font-weight: 300;
            letter-spacing: 3px;
            margin-bottom: 25px;
            color: var(--navy);
            text-transform: uppercase;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--leather);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: var(--eggshell);
            padding: 24px;
            border-radius: 6px;
            border-left: 4px solid var(--leather);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .stat-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--light-text);
            margin-bottom: 8px;
            font-weight: 600;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 300;
            color: var(--navy);
            letter-spacing: -1px;
        }

        .stat-change {
            font-size: 12px;
            margin-top: 5px;
            color: var(--light-text);
        }

        .stat-change.positive { color: var(--success); }
        .stat-change.negative { color: var(--coral); }

        .signal-card {
            background: var(--white);
            border: 1px solid var(--eggshell);
            border-left: 4px solid var(--leather);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 6px;
            transition: all 0.2s;
        }

        .signal-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }

        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .signal-ticker {
            font-size: 24px;
            font-weight: 300;
            color: var(--navy);
            letter-spacing: 2px;
        }

        .conviction-badge {
            background: var(--leather);
            color: var(--white);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            letter-spacing: 1px;
        }

        .conviction-badge.high {
            background: var(--success);
        }

        .conviction-badge.medium {
            background: var(--warning);
        }

        .conviction-badge.low {
            background: var(--leather);
        }

        .signal-triggers {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 12px 0;
        }

        .trigger-tag {
            background: var(--eggshell);
            color: var(--navy);
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .mini-chart {
            height: 60px;
            background: var(--eggshell);
            border-radius: 4px;
            padding: 10px;
            margin: 15px 0;
            position: relative;
            overflow: hidden;
        }

        .chart-bar {
            display: inline-block;
            width: 8px;
            background: var(--leather);
            margin: 0 2px;
            border-radius: 2px 2px 0 0;
            vertical-align: bottom;
            opacity: 0.7;
            transition: opacity 0.2s, background 0.2s;
        }

        .chart-bar:hover {
            opacity: 1;
            background: var(--navy);
        }

        .data-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 20px 0;
        }

        .data-table th {
            background: var(--navy);
            color: var(--white);
            padding: 14px 12px;
            text-align: left;
            font-weight: 400;
            font-size: 11px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .data-table th:first-child {
            border-radius: 6px 0 0 0;
        }

        .data-table th:last-child {
            border-radius: 0 6px 0 0;
        }

        .data-table td {
            padding: 14px 12px;
            border-bottom: 1px solid var(--eggshell);
            font-size: 14px;
        }

        .data-table tr:hover {
            background: var(--eggshell);
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--eggshell);
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }

        .progress-fill {
            height: 100%;
            background: var(--leather);
            transition: width 0.3s ease;
            border-radius: 4px;
        }

        .progress-fill.success { background: var(--success); }
        .progress-fill.warning { background: var(--warning); }
        .progress-fill.danger { background: var(--coral); }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
        }

        .sentiment-bar {
            display: flex;
            height: 40px;
            border-radius: 6px;
            overflow: hidden;
            margin: 15px 0;
        }

        .sentiment-positive {
            background: var(--success);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--white);
            font-size: 12px;
            font-weight: 600;
        }

        .sentiment-neutral {
            background: var(--warning);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--white);
            font-size: 12px;
            font-weight: 600;
        }

        .sentiment-negative {
            background: var(--coral);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--white);
            font-size: 12px;
            font-weight: 600;
        }

        .footer {
            text-align: center;
            padding: 30px 20px;
            color: var(--light-text);
            background: var(--navy);
            margin-top: 40px;
        }

        .footer p {
            color: rgba(255,255,255,0.6);
            font-size: 12px;
            letter-spacing: 1px;
        }

        .footer a {
            color: var(--leather);
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }

        .footer a:hover {
            border-bottom-color: var(--leather);
        }

        /* New Dashboard Components */
        .grid-4 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }

        .card {
            background: var(--white);
            border: 1px solid var(--eggshell);
            border-radius: 6px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s;
        }

        .card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .card-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--navy);
            margin-bottom: 15px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .movers-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .mover-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: var(--eggshell);
            border-radius: 4px;
            transition: background 0.2s;
        }

        .mover-item:hover {
            background: #e8e8e8;
        }

        .rank {
            font-size: 11px;
            font-weight: 600;
            color: var(--light-text);
            min-width: 30px;
        }

        .ticker-name {
            font-size: 14px;
            font-weight: 600;
            color: var(--navy);
            letter-spacing: 1px;
            flex: 1;
            margin-left: 10px;
        }

        .mover-value {
            font-size: 13px;
            font-weight: 600;
            color: var(--dark-text);
        }

        .mover-value.positive {
            color: var(--success);
        }

        .mover-value.negative {
            color: var(--coral);
        }

        .empty-state {
            text-align: center;
            padding: 30px 20px;
            color: var(--light-text);
            font-size: 13px;
            font-style: italic;
        }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .badge.positive {
            background: #d1fae5;
            color: #065f46;
        }

        .badge.negative {
            background: #fee2e2;
            color: #991b1b;
        }

        .badge.neutral {
            background: var(--eggshell);
            color: var(--dark-text);
        }

        .table-container {
            overflow-x: auto;
            margin: 15px 0;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }

        .emerging-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }

        .emerging-ticker {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 15px;
            background: var(--eggshell);
            border-radius: 6px;
            border-left: 3px solid var(--leather);
        }

        .ticker-badge {
            font-size: 13px;
            font-weight: 700;
            color: var(--navy);
            letter-spacing: 1px;
        }

        .mention-count {
            font-size: 12px;
            color: var(--light-text);
        }

        .new-badge {
            background: var(--coral);
            color: var(--white);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }

            .grid-2 {
                grid-template-columns: 1fr;
            }

            .grid-4 {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 24px;
                letter-spacing: 3px;
            }

            .chart-container {
                height: 250px;
            }
        }
    </style>"""

    def _generate_chart_scripts(self) -> str:
        """Generate JavaScript for interactive charts"""
        return """<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script>
        // Initialize tooltips and interactive elements
        document.addEventListener('DOMContentLoaded', function() {
            // Add hover effects to chart bars
            document.querySelectorAll('.chart-bar').forEach(bar => {
                bar.addEventListener('mouseover', function() {
                    const value = this.getAttribute('data-value');
                    if (value) {
                        this.title = `Value: ${value}`;
                    }
                });
            });
        });
    </script>"""

    def _generate_header(self, market_score: int, assessment: Dict) -> str:
        """Generate header with market health score"""
        risk_level = assessment.get('risk_level', 'UNKNOWN')
        risk_emoji = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}.get(risk_level, '⚪')

        conditions = assessment.get('conditions', [])
        recommendations = assessment.get('recommendations', [])

        return f"""<div class="header">
        <h1>Trading Signals</h1>
        <p>{datetime.now().strftime('%B %d, %Y • %I:%M %p')}</p>
    </div>
    <div class="market-score">
        <div class="score-gauge">
            <div class="score-circle" style="--score: {market_score};">
                <div class="score-inner">
                    <div class="score-value">{market_score}</div>
                    <div class="score-label">Health</div>
                </div>
            </div>
        </div>
        <div class="score-info">
            <h3>{risk_emoji} Market Risk: {risk_level}</h3>
            <p>{conditions[0] if conditions else 'Market conditions unknown'}</p>
            <p style="opacity: 0.7;">{recommendations[0] if recommendations else 'Proceed with normal risk management'}</p>
        </div>
    </div>"""

    def _generate_overview_stats(self, signals: List, velocity_data: Dict, paper_stats: Dict) -> str:
        """Generate overview statistics cards"""
        high_conviction = len([s for s in signals if s.conviction_score >= 70])
        avg_conviction = sum(s.conviction_score for s in signals) / len(signals) if signals else 0

        total_trades = paper_stats.get('total_trades', 0)
        win_rate = paper_stats.get('win_rate', 0)
        total_pl = paper_stats.get('total_pl', 0)

        active_tickers = len(velocity_data)

        return f"""<div class="section">
        <h2 class="section-title">Portfolio Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Active Signals</div>
                <div class="stat-value">{len(signals)}</div>
                <div class="stat-change positive">↑ {high_conviction} high conviction</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Conviction</div>
                <div class="stat-value">{avg_conviction:.0f}</div>
                <div class="stat-change">/100 score</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Paper Trades</div>
                <div class="stat-value">{total_trades}</div>
                <div class="stat-change {'positive' if win_rate >= 50 else 'negative'}">{win_rate:.1f}% win rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Paper P/L</div>
                <div class="stat-value">${abs(total_pl):,.0f}</div>
                <div class="stat-change {'positive' if total_pl >= 0 else 'negative'}">{'↑' if total_pl >= 0 else '↓'} ${abs(total_pl):,.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tracked Tickers</div>
                <div class="stat-value">{active_tickers}</div>
                <div class="stat-change">with velocity data</div>
            </div>
        </div>
    </div>"""

    def _generate_signals_section(self, signals: List, velocity_data: Dict, technical_data: Dict, sentiment_data: Dict) -> str:
        """Generate signals section with visual cards"""
        if not signals:
            return """<div class="section">
                <h2 class="section-title">Trading Signals</h2>
                <p style="text-align: center; color: var(--light-text); padding: 40px;">No signals generated in this run</p>
            </div>"""

        # Sort by conviction
        sorted_signals = sorted(signals, key=lambda s: s.conviction_score, reverse=True)

        signal_cards = ""
        for signal in sorted_signals[:10]:  # Top 10
            conviction_class = 'high' if signal.conviction_score >= 70 else 'medium' if signal.conviction_score >= 50 else 'low'

            # Get velocity chart data
            velocity = velocity_data.get(signal.ticker, {})
            chart_html = self._generate_mini_chart(velocity)

            # Get triggers
            triggers_html = ""
            for trigger in signal.triggers:
                triggers_html += f'<span class="trigger-tag">{trigger}</span>'

            # Get technical and sentiment data
            tech = technical_data.get(signal.ticker, {})
            sent = sentiment_data.get(signal.ticker, {})

            rsi = tech.get('rsi_14', 'N/A')
            # Determine trend from momentum
            momentum = tech.get('momentum_10d', 0)
            if momentum > 5:
                trend = 'Up'
            elif momentum < -5:
                trend = 'Down'
            else:
                trend = 'Neutral'
            sentiment_score = sent.get('avg_sentiment', 0)

            signal_cards += f"""<div class="signal-card">
                <div class="signal-header">
                    <div class="signal-ticker">{signal.ticker}</div>
                    <div class="conviction-badge {conviction_class}">{signal.conviction_score:.0f}</div>
                </div>
                <div class="signal-triggers">{triggers_html}</div>
                {chart_html}
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px;">
                    <div>
                        <div class="stat-label">RSI</div>
                        <div style="font-size: 20px; color: var(--navy);">{rsi if isinstance(rsi, str) else f"{rsi:.1f}"}</div>
                    </div>
                    <div>
                        <div class="stat-label">Trend</div>
                        <div style="font-size: 20px; color: var(--navy);">{trend}</div>
                    </div>
                    <div>
                        <div class="stat-label">Sentiment</div>
                        <div style="font-size: 20px; color: {'var(--success)' if sentiment_score > 0.1 else 'var(--coral)' if sentiment_score < -0.1 else 'var(--warning)'};">{sentiment_score:+.2f}</div>
                    </div>
                </div>
            </div>"""

        return f"""<div class="section">
            <h2 class="section-title">Top Trading Signals</h2>
            {signal_cards}
        </div>"""

    def _generate_mini_chart(self, velocity: Dict) -> str:
        """Generate mini velocity chart (sparkline)"""
        # Create a simple bar chart showing velocity over time
        mention_velocity = velocity.get('mention_velocity_24h', 0)
        composite_score = velocity.get('composite_score', 0)

        # Generate 10 bars with some variation for visual effect
        base_height = 30
        bars_html = ""
        for i in range(10):
            # Simulate historical data (in real app, this would be actual historical data)
            height = base_height + (i * 3) + (composite_score / 10)
            bars_html += f'<span class="chart-bar" style="height: {min(height, 50)}px;" data-value="{height:.0f}"></span>'

        return f'<div class="mini-chart">{bars_html}</div>'

    def _generate_sentiment_section(self, sentiment_data: Dict) -> str:
        """Generate market sentiment section"""
        # Sentiment overview
        if sentiment_data:
            # Handle None values explicitly
            positive_count = sum(1 for s in sentiment_data.values()
                               if (s.get('avg_sentiment') or 0) > 0.1)
            neutral_count = sum(1 for s in sentiment_data.values()
                              if -0.1 <= (s.get('avg_sentiment') or 0) <= 0.1)
            negative_count = sum(1 for s in sentiment_data.values()
                               if (s.get('avg_sentiment') or 0) < -0.1)
            total = positive_count + neutral_count + negative_count

            if total > 0:
                pos_pct = (positive_count / total) * 100
                neu_pct = (neutral_count / total) * 100
                neg_pct = (negative_count / total) * 100

                # Build sentiment bar with only non-zero categories
                sentiment_parts = []
                if positive_count > 0:
                    sentiment_parts.append(f'<div class="sentiment-positive" style="width: {pos_pct}%;">{positive_count} Bullish</div>')
                if neutral_count > 0:
                    sentiment_parts.append(f'<div class="sentiment-neutral" style="width: {neu_pct}%;">{neutral_count} Neutral</div>')
                if negative_count > 0:
                    sentiment_parts.append(f'<div class="sentiment-negative" style="width: {neg_pct}%;">{negative_count} Bearish</div>')

                sentiment_html = f"""<div class="sentiment-bar">
                    {''.join(sentiment_parts)}
                </div>"""
            else:
                sentiment_html = '<p style="color: var(--light-text); text-align: center;">No sentiment data available</p>'
        else:
            sentiment_html = '<p style="color: var(--light-text); text-align: center;">No sentiment data available</p>'

        return f"""<div class="section">
            <h2 class="section-title">📊 Market Sentiment</h2>
            {sentiment_html}
        </div>"""

    def _generate_technical_section(self, technical_data: Dict) -> str:
        """Generate technical indicators overview"""
        if not technical_data:
            return ""

        # Get summary stats (using correct field names from TechnicalAnalyzer)
        # Handle None values explicitly since .get() default only applies if key doesn't exist
        oversold = sum(1 for t in technical_data.values()
                      if (t.get('rsi_14') or 50) < 30)
        overbought = sum(1 for t in technical_data.values()
                        if (t.get('rsi_14') or 50) > 70)

        # Determine trend from momentum
        uptrend = sum(1 for t in technical_data.values()
                     if (t.get('momentum_10d') or 0) > 5)
        downtrend = sum(1 for t in technical_data.values()
                       if (t.get('momentum_10d') or 0) < -5)

        return f"""<div class="section">
            <h2 class="section-title">Technical Overview</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Oversold (RSI < 30)</div>
                    <div class="stat-value">{oversold}</div>
                    <div class="stat-change">potential bounce opportunities</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Overbought (RSI > 70)</div>
                    <div class="stat-value">{overbought}</div>
                    <div class="stat-change">potential pullback risk</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Uptrend</div>
                    <div class="stat-value">{uptrend}</div>
                    <div class="stat-change positive">↑ momentum</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Downtrend</div>
                    <div class="stat-value">{downtrend}</div>
                    <div class="stat-change negative">↓ momentum</div>
                </div>
            </div>
        </div>"""

    def _generate_top_movers_section(self, velocity_gainers: List, insider_trades: List,
                                      social_mentions: List, sentiment_shifts: List) -> str:
        """Generate Top Movers dashboard section with 4 key metrics"""
        if not any([velocity_gainers, insider_trades, social_mentions, sentiment_shifts]):
            return ""

        # Top 5 velocity gainers
        velocity_html = ""
        for i, v in enumerate(velocity_gainers[:5], 1):
            velocity_html += f"""
                <div class="mover-item">
                    <span class="rank">#{i}</span>
                    <span class="ticker-name">{v['ticker']}</span>
                    <span class="mover-value positive">↑ {v['composite_score']:.1f}</span>
                </div>"""

        # Top 5 insider activity
        insider_html = ""
        for i, trade in enumerate(insider_trades[:5], 1):
            trade_class = "positive" if 'buy' in trade['trade_type'].lower() or 'purchase' in trade['trade_type'].lower() else "negative"
            insider_html += f"""
                <div class="mover-item">
                    <span class="rank">#{i}</span>
                    <span class="ticker-name">{trade['ticker']}</span>
                    <span class="mover-value {trade_class}">${trade['value']/1000:.0f}K</span>
                </div>"""

        # Top 5 social mentions
        social_html = ""
        for i, mention in enumerate(social_mentions[:5], 1):
            social_html += f"""
                <div class="mover-item">
                    <span class="rank">#{i}</span>
                    <span class="ticker-name">{mention['ticker']}</span>
                    <span class="mover-value">{mention['mention_count']} mentions</span>
                </div>"""

        # Top 5 sentiment shifts
        sentiment_html = ""
        for i, shift in enumerate(sentiment_shifts[:5], 1):
            shift_class = "positive" if shift['sentiment_change'] > 0 else "negative"
            arrow = "↑" if shift['sentiment_change'] > 0 else "↓"
            sentiment_html += f"""
                <div class="mover-item">
                    <span class="rank">#{i}</span>
                    <span class="ticker-name">{shift['ticker']}</span>
                    <span class="mover-value {shift_class}">{arrow} {abs(shift['sentiment_change']):.2f}</span>
                </div>"""

        return f"""<div class="section">
            <h2 class="section-title">📊 Top Movers (24h)</h2>
            <div class="grid-4">
                <div class="card">
                    <h3 class="card-title">🚀 Velocity Gainers</h3>
                    <div class="movers-list">{velocity_html or '<p class="empty-state">No data available</p>'}</div>
                </div>
                <div class="card">
                    <h3 class="card-title">💼 Insider Activity</h3>
                    <div class="movers-list">{insider_html or '<p class="empty-state">No recent trades</p>'}</div>
                </div>
                <div class="card">
                    <h3 class="card-title">💬 Social Buzz</h3>
                    <div class="movers-list">{social_html or '<p class="empty-state">No mentions</p>'}</div>
                </div>
                <div class="card">
                    <h3 class="card-title">📈 Sentiment Shifts</h3>
                    <div class="movers-list">{sentiment_html or '<p class="empty-state">No shifts detected</p>'}</div>
                </div>
            </div>
        </div>"""

    def _generate_insider_panel(self, insider_trades: List, insider_ratio: Dict) -> str:
        """Generate detailed insider trading panel with table and chart"""
        if not insider_trades and not insider_ratio:
            return ""

        # Build trades table
        trades_html = ""
        for trade in insider_trades[:10]:
            trade_type_class = "positive" if 'buy' in trade['trade_type'].lower() or 'purchase' in trade['trade_type'].lower() else "negative"
            trades_html += f"""
                <tr>
                    <td><strong>{trade['ticker']}</strong></td>
                    <td>{trade['insider_name'][:30]}</td>
                    <td><span class="badge {trade_type_class}">{trade['trade_type']}</span></td>
                    <td>${trade['value']/1000:.0f}K</td>
                    <td>{trade['trade_date']}</td>
                </tr>"""

        # Buy/Sell ratio pie chart
        buys = insider_ratio.get('buy', 0)
        sells = insider_ratio.get('sell', 0)
        total = buys + sells
        buy_pct = (buys / total * 100) if total > 0 else 0
        sell_pct = (sells / total * 100) if total > 0 else 0

        return f"""<div class="section">
            <h2 class="section-title">💼 Insider Trading Activity (30 Days)</h2>
            <div class="grid-2">
                <div class="card">
                    <h3 class="card-title">Recent Transactions</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Insider</th>
                                    <th>Type</th>
                                    <th>Value</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>{trades_html or '<tr><td colspan="5" class="empty-state">No insider trades in last 30 days</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">Buy/Sell Ratio</h3>
                    <div class="chart-container">
                        <canvas id="insiderRatioChart"></canvas>
                    </div>
                    <div class="stats-grid" style="margin-top: 20px;">
                        <div class="stat-card">
                            <div class="stat-label">Buys</div>
                            <div class="stat-value positive">{buys}</div>
                            <div class="stat-change">{buy_pct:.1f}%</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Sells</div>
                            <div class="stat-value negative">{sells}</div>
                            <div class="stat-change">{sell_pct:.1f}%</div>
                        </div>
                    </div>
                </div>
            </div>
            <script>
                new Chart(document.getElementById('insiderRatioChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: ['Buys', 'Sells'],
                        datasets: [{{
                            data: [{buys}, {sells}],
                            backgroundColor: ['#27AE60', '#E74C3C']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{
                            legend: {{ position: 'bottom' }}
                        }}
                    }}
                }});
            </script>
        </div>"""

    def _generate_technical_deepdive(self, technical_data: Dict, velocity_data: Dict) -> str:
        """Generate technical analysis deep dive with RSI distribution and MACD signals"""
        if not technical_data:
            return ""

        # RSI distribution
        rsi_values = [t.get('rsi_14', 50) for t in technical_data.values() if t.get('rsi_14') is not None]
        rsi_oversold = sum(1 for r in rsi_values if r < 30)
        rsi_neutral = sum(1 for r in rsi_values if 30 <= r <= 70)
        rsi_overbought = sum(1 for r in rsi_values if r > 70)

        # MACD signals table
        macd_signals_html = ""
        macd_count = 0
        for ticker, data in sorted(technical_data.items(), key=lambda x: x[1].get('technical_score', 0) or 0, reverse=True)[:10]:
            if data.get('macd'):
                macd = data.get('macd', {})
                macd_hist = macd.get('histogram', 0) if isinstance(macd, dict) else 0
                signal_class = "positive" if macd_hist > 0 else "negative"
                macd_signals_html += f"""
                    <tr>
                        <td><strong>{ticker}</strong></td>
                        <td><span class="badge {signal_class}">{'Bullish' if macd_hist > 0 else 'Bearish'}</span></td>
                        <td>{data.get('rsi_14', 'N/A') if data.get('rsi_14') else 'N/A'}</td>
                        <td>{data.get('technical_score', 0):.0f}/100</td>
                    </tr>"""
                macd_count += 1

        return f"""<div class="section">
            <h2 class="section-title">📉 Technical Analysis Deep Dive</h2>
            <div class="grid-2">
                <div class="card">
                    <h3 class="card-title">RSI Distribution</h3>
                    <div class="chart-container">
                        <canvas id="rsiDistChart"></canvas>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">Top MACD Signals</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Signal</th>
                                    <th>RSI</th>
                                    <th>Tech Score</th>
                                </tr>
                            </thead>
                            <tbody>{macd_signals_html or '<tr><td colspan="4" class="empty-state">No MACD data available</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <script>
                new Chart(document.getElementById('rsiDistChart'), {{
                    type: 'bar',
                    data: {{
                        labels: ['Oversold (<30)', 'Neutral (30-70)', 'Overbought (>70)'],
                        datasets: [{{
                            label: 'Ticker Count',
                            data: [{rsi_oversold}, {rsi_neutral}, {rsi_overbought}],
                            backgroundColor: ['#27AE60', '#F39C12', '#E74C3C']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{ y: {{ beginAtZero: true }} }},
                        plugins: {{ legend: {{ display: false }} }}
                    }}
                }});
            </script>
        </div>"""

    def _generate_performance_section(self, signal_performance: List, equity_curve: List, paper_stats: Dict) -> str:
        """Generate historical performance section with equity curve and signal success rates"""
        if not signal_performance and not equity_curve:
            return ""

        # Signal performance table
        perf_html = ""
        for perf in signal_performance[:8]:
            win_rate_class = "positive" if perf['win_rate'] > 50 else "negative" if perf['win_rate'] < 50 else ""
            perf_html += f"""
                <tr>
                    <td><strong>{perf['signal_type']}</strong></td>
                    <td>{perf['signal_count']}</td>
                    <td>{perf['trades_executed']}</td>
                    <td><span class="badge {win_rate_class}">{perf['win_rate']:.1f}%</span></td>
                    <td>${perf['avg_pnl']:.2f}</td>
                </tr>"""

        # Equity curve data for chart
        if equity_curve:
            dates = [point['date'] for point in equity_curve]
            equity_values = [point['total_equity'] for point in equity_curve]
            dates_js = json.dumps(dates)
            equity_js = json.dumps(equity_values)
        else:
            dates_js = "[]"
            equity_js = "[]"

        return f"""<div class="section">
            <h2 class="section-title">📊 Historical Performance (90 Days)</h2>
            <div class="grid-2">
                <div class="card">
                    <h3 class="card-title">Signal Type Success Rates</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Signal Type</th>
                                    <th>Generated</th>
                                    <th>Traded</th>
                                    <th>Win Rate</th>
                                    <th>Avg P/L</th>
                                </tr>
                            </thead>
                            <tbody>{perf_html or '<tr><td colspan="5" class="empty-state">No performance data available</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">Paper Trading Equity Curve</h3>
                    <div class="chart-container">
                        <canvas id="equityCurveChart"></canvas>
                    </div>
                </div>
            </div>
            <script>
                new Chart(document.getElementById('equityCurveChart'), {{
                    type: 'line',
                    data: {{
                        labels: {dates_js},
                        datasets: [{{
                            label: 'Total Equity',
                            data: {equity_js},
                            borderColor: '#3498DB',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: false,
                                ticks: {{ callback: value => '$' + value.toFixed(2) }}
                            }}
                        }},
                        plugins: {{
                            legend: {{ display: true, position: 'bottom' }}
                        }}
                    }}
                }});
            </script>
        </div>"""

    def _generate_sentiment_breakdown(self, sentiment_data: Dict, sentiment_shifts: List) -> str:
        """Generate sentiment analysis breakdown showing shifts and comparisons"""
        if not sentiment_data and not sentiment_shifts:
            return ""

        # Sentiment shifts table
        shifts_html = ""
        for shift in sentiment_shifts[:10]:
            shift_class = "positive" if shift['sentiment_change'] > 0 else "negative"
            arrow = "↑" if shift['sentiment_change'] > 0 else "↓"
            shifts_html += f"""
                <tr>
                    <td><strong>{shift['ticker']}</strong></td>
                    <td>{shift['previous_sentiment']:.2f}</td>
                    <td>{shift['current_sentiment']:.2f}</td>
                    <td><span class="badge {shift_class}">{arrow} {abs(shift['sentiment_change']):.2f}</span></td>
                </tr>"""

        # Sentiment distribution
        if sentiment_data:
            positive = sum(1 for s in sentiment_data.values() if (s.get('avg_sentiment') or 0) > 0.1)
            neutral = sum(1 for s in sentiment_data.values() if -0.1 <= (s.get('avg_sentiment') or 0) <= 0.1)
            negative = sum(1 for s in sentiment_data.values() if (s.get('avg_sentiment') or 0) < -0.1)
        else:
            positive = neutral = negative = 0

        return f"""<div class="section">
            <h2 class="section-title">💭 Sentiment Analysis</h2>
            <div class="grid-2">
                <div class="card">
                    <h3 class="card-title">Sentiment Distribution</h3>
                    <div class="chart-container">
                        <canvas id="sentimentDistChart"></canvas>
                    </div>
                    <div class="stats-grid" style="margin-top: 20px;">
                        <div class="stat-card">
                            <div class="stat-label">Positive</div>
                            <div class="stat-value positive">{positive}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Neutral</div>
                            <div class="stat-value">{neutral}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Negative</div>
                            <div class="stat-value negative">{negative}</div>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">Top Sentiment Shifts (7 Days)</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Previous</th>
                                    <th>Current</th>
                                    <th>Change</th>
                                </tr>
                            </thead>
                            <tbody>{shifts_html or '<tr><td colspan="4" class="empty-state">No significant shifts</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <script>
                new Chart(document.getElementById('sentimentDistChart'), {{
                    type: 'pie',
                    data: {{
                        labels: ['Positive', 'Neutral', 'Negative'],
                        datasets: [{{
                            data: [{positive}, {neutral}, {negative}],
                            backgroundColor: ['#27AE60', '#95A5A6', '#E74C3C']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{ legend: {{ position: 'bottom' }} }}
                    }}
                }});
            </script>
        </div>"""

    def _generate_macro_trends(self, vix_history: List, treasury_history: List,
                                macro_indicators: Dict, market_assessment: Dict) -> str:
        """Generate macro economic trends section with VIX and interest rate charts"""
        if not vix_history and not treasury_history:
            return ""

        # VIX chart data
        if vix_history:
            vix_dates = [v['date'] for v in vix_history]
            vix_values = [v['value'] for v in vix_history]
            vix_dates_js = json.dumps(vix_dates)
            vix_values_js = json.dumps(vix_values)
        else:
            vix_dates_js = "[]"
            vix_values_js = "[]"

        # Treasury chart data
        if treasury_history:
            treasury_dates = [t['date'] for t in treasury_history]
            treasury_values = [t['value'] for t in treasury_history]
            treasury_dates_js = json.dumps(treasury_dates)
            treasury_values_js = json.dumps(treasury_values)
        else:
            treasury_dates_js = "[]"
            treasury_values_js = "[]"

        # Current macro values
        current_vix = vix_history[-1]['value'] if vix_history else 0
        current_treasury = treasury_history[-1]['value'] if treasury_history else 0

        return f"""<div class="section">
            <h2 class="section-title">🌍 Macro Economic Trends (30 Days)</h2>
            <div class="grid-2">
                <div class="card">
                    <h3 class="card-title">VIX (Volatility Index)</h3>
                    <div class="chart-container">
                        <canvas id="vixChart"></canvas>
                    </div>
                    <div class="stat-card" style="margin-top: 15px;">
                        <div class="stat-label">Current VIX</div>
                        <div class="stat-value">{current_vix:.2f}</div>
                        <div class="stat-change">{'LOW volatility' if current_vix < 20 else 'HIGH volatility' if current_vix > 30 else 'MODERATE volatility'}</div>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">10-Year Treasury Rate</h3>
                    <div class="chart-container">
                        <canvas id="treasuryChart"></canvas>
                    </div>
                    <div class="stat-card" style="margin-top: 15px;">
                        <div class="stat-label">Current Rate</div>
                        <div class="stat-value">{current_treasury:.2f}%</div>
                        <div class="stat-change">{'Rising rates' if len(treasury_history) > 1 and treasury_history[-1]['value'] > treasury_history[-2]['value'] else 'Falling rates'}</div>
                    </div>
                </div>
            </div>
            <script>
                new Chart(document.getElementById('vixChart'), {{
                    type: 'line',
                    data: {{
                        labels: {vix_dates_js},
                        datasets: [{{
                            label: 'VIX',
                            data: {vix_values_js},
                            borderColor: '#E74C3C',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{ y: {{ beginAtZero: true }} }},
                        plugins: {{ legend: {{ display: false }} }}
                    }}
                }});

                new Chart(document.getElementById('treasuryChart'), {{
                    type: 'line',
                    data: {{
                        labels: {treasury_dates_js},
                        datasets: [{{
                            label: '10Y Rate',
                            data: {treasury_values_js},
                            borderColor: '#3498DB',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{ y: {{ beginAtZero: false }} }},
                        plugins: {{ legend: {{ display: false }} }}
                    }}
                }});
            </script>
        </div>"""

    def _generate_social_insights(self, social_mentions: List, emerging_tickers: List, top_velocity: List) -> str:
        """Generate social media insights with viral scores and emerging tickers"""
        if not social_mentions and not emerging_tickers:
            return ""

        # Top social mentions table
        social_html = ""
        for i, mention in enumerate(social_mentions[:10], 1):
            social_html += f"""
                <tr>
                    <td>#{i}</td>
                    <td><strong>{mention['ticker']}</strong></td>
                    <td>{mention['mention_count']}</td>
                    <td>{mention['upvotes']}</td>
                    <td>{mention['viral_score']:.1f}</td>
                </tr>"""

        # Emerging tickers
        emerging_html = ""
        for ticker in emerging_tickers[:8]:
            emerging_html += f"""
                <div class="emerging-ticker">
                    <span class="ticker-badge">{ticker['ticker']}</span>
                    <span class="mention-count">{ticker['mention_count']} mentions</span>
                    <span class="new-badge">NEW</span>
                </div>"""

        return f"""<div class="section">
            <h2 class="section-title">💬 Social Media Insights</h2>
            <div class="grid-2">
                <div class="card">
                    <h3 class="card-title">Top Social Mentions (24h)</h3>
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Ticker</th>
                                    <th>Mentions</th>
                                    <th>Upvotes</th>
                                    <th>Viral Score</th>
                                </tr>
                            </thead>
                            <tbody>{social_html or '<tr><td colspan="5" class="empty-state">No social data available</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
                <div class="card">
                    <h3 class="card-title">🌟 Emerging Tickers</h3>
                    <p style="opacity: 0.7; margin-bottom: 15px;">Tickers that recently entered top mentions</p>
                    <div class="emerging-container">
                        {emerging_html or '<p class="empty-state">No emerging tickers detected</p>'}
                    </div>
                </div>
            </div>
        </div>"""

    def _generate_footer(self) -> str:
        """Generate footer"""
        return f"""<div class="footer">
        <p>Stock Trader • Powered by FREE Data Sources</p>
        <p style="margin-top: 10px;">Finnhub • Alpha Vantage • YFinance • VADER • FMP • Technical Analysis</p>
        <p style="margin-top: 15px; opacity: 0.5;">Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>"""
