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
                reddit_data: Dict[str, Dict] = None,
                paper_trading_stats: Dict = None,
                macro_indicators: Dict = None,
                market_assessment: Dict = None,
                congress_trades: List[Dict] = None) -> str:
        """Generate complete modern HTML dashboard"""

        technical_data = technical_data or {}
        sentiment_data = sentiment_data or {}
        reddit_data = reddit_data or {}
        paper_trading_stats = paper_trading_stats or {}
        macro_indicators = macro_indicators or {}
        market_assessment = market_assessment or {}
        congress_trades = congress_trades or []

        # Calculate market health score (0-100)
        market_score = self._calculate_market_score(market_assessment, macro_indicators)

        # Generate sections
        header_html = self._generate_header(market_score, market_assessment)
        overview_html = self._generate_overview_stats(signals, velocity_data, paper_trading_stats)
        signals_html = self._generate_signals_section(signals, velocity_data, technical_data, sentiment_data)
        activity_html = self._generate_activity_section(congress_trades, velocity_data, sentiment_data)
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
        {signals_html}
        {activity_html}
        {technical_html}
        {self._generate_footer()}
    </div>
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

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }

            .grid-2 {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 24px;
                letter-spacing: 3px;
            }
        }
    </style>"""

    def _generate_chart_scripts(self) -> str:
        """Generate JavaScript for interactive charts"""
        return """<script>
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

            rsi = tech.get('rsi', 'N/A')
            trend = tech.get('trend', 'Unknown')
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

    def _generate_activity_section(self, congress_trades: List[Dict], velocity_data: Dict, sentiment_data: Dict) -> str:
        """Generate insider & congress activity section"""
        if not congress_trades:
            congress_html = '<p style="color: var(--light-text); text-align: center; padding: 20px;">No recent congressional trades</p>'
        else:
            # Get top 10 recent trades
            recent_trades = sorted(congress_trades, key=lambda t: t.get('transaction_date', ''), reverse=True)[:10]

            rows_html = ""
            for trade in recent_trades:
                ticker = trade.get('ticker', 'N/A')
                member = trade.get('representative_name', 'Unknown')
                tx_type = trade.get('transaction_type', 'unknown')
                tx_date = trade.get('transaction_date', 'N/A')
                amount_from = trade.get('amount_from', 0) or 0
                amount_to = trade.get('amount_to', 0) or 0
                amount_mid = (amount_from + amount_to) / 2 if amount_from and amount_to else 0

                type_color = 'var(--success)' if tx_type == 'purchase' else 'var(--coral)'

                rows_html += f"""<tr>
                    <td style="color: {type_color}; font-weight: 600;">{tx_date}</td>
                    <td><strong>{ticker}</strong></td>
                    <td>{member[:25]}</td>
                    <td style="color: {type_color}; text-transform: uppercase; font-size: 11px; letter-spacing: 1px;">{tx_type}</td>
                    <td style="text-align: right;">${amount_mid:,.0f}</td>
                </tr>"""

            congress_html = f"""<table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Ticker</th>
                        <th>Member</th>
                        <th>Type</th>
                        <th style="text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>"""

        # Sentiment overview
        if sentiment_data:
            positive_count = sum(1 for s in sentiment_data.values() if s.get('avg_sentiment', 0) > 0.1)
            neutral_count = sum(1 for s in sentiment_data.values() if -0.1 <= s.get('avg_sentiment', 0) <= 0.1)
            negative_count = sum(1 for s in sentiment_data.values() if s.get('avg_sentiment', 0) < -0.1)
            total = positive_count + neutral_count + negative_count

            if total > 0:
                pos_pct = (positive_count / total) * 100
                neu_pct = (neutral_count / total) * 100
                neg_pct = (negative_count / total) * 100

                sentiment_html = f"""<div class="sentiment-bar">
                    <div class="sentiment-positive" style="width: {pos_pct}%;">{positive_count} Bullish</div>
                    <div class="sentiment-neutral" style="width: {neu_pct}%;">{neutral_count} Neutral</div>
                    <div class="sentiment-negative" style="width: {neg_pct}%;">{negative_count} Bearish</div>
                </div>"""
            else:
                sentiment_html = '<p style="color: var(--light-text); text-align: center;">No sentiment data available</p>'
        else:
            sentiment_html = '<p style="color: var(--light-text); text-align: center;">No sentiment data available</p>'

        return f"""<div class="grid-2">
            <div class="section">
                <h2 class="section-title">🏛️ Congress Trades</h2>
                {congress_html}
            </div>
            <div class="section">
                <h2 class="section-title">📊 Market Sentiment</h2>
                {sentiment_html}
            </div>
        </div>"""

    def _generate_technical_section(self, technical_data: Dict) -> str:
        """Generate technical indicators overview"""
        if not technical_data:
            return ""

        # Get summary stats
        oversold = sum(1 for t in technical_data.values() if t.get('rsi', 50) < 30)
        overbought = sum(1 for t in technical_data.values() if t.get('rsi', 50) > 70)
        uptrend = sum(1 for t in technical_data.values() if t.get('trend', '').lower() == 'up')
        downtrend = sum(1 for t in technical_data.values() if t.get('trend', '').lower() == 'down')

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

    def _generate_footer(self) -> str:
        """Generate footer"""
        return f"""<div class="footer">
        <p>Stock Trader • Powered by FREE Data Sources</p>
        <p style="margin-top: 10px;">Finnhub • Alpha Vantage • YFinance • VADER • FMP • Technical Analysis</p>
        <p style="margin-top: 15px; opacity: 0.5;">Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>"""
