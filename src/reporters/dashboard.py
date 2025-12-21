"""
@file dashboard.py
@brief HTML dashboard generator for viewing trading signals
@details Creates a local HTML dashboard to visualize all signals and metrics
"""

from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class DashboardGenerator:
    """
    @class DashboardGenerator
    @brief Generate HTML dashboard for trading signals
    @details Creates beautiful, interactive HTML reports viewable in any browser
    """

    def __init__(self, output_dir: str = "reports"):
        """
        @brief Initialize dashboard generator
        @param output_dir Directory to save HTML reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate(self,
                signals: List[Any],
                velocity_data: Dict[str, Dict],
                technical_data: Dict[str, Dict] = None,
                sentiment_data: Dict[str, Dict] = None,
                reddit_data: Dict[str, Dict] = None,
                paper_trading_stats: Dict = None) -> str:
        """
        @brief Generate complete HTML dashboard
        @param signals List of Signal objects
        @param velocity_data Velocity metrics
        @param technical_data Technical analysis data
        @param sentiment_data Sentiment analysis data
        @param reddit_data Reddit mention data
        @param paper_trading_stats Paper trading performance statistics
        @return Path to generated HTML file
        """
        technical_data = technical_data or {}
        sentiment_data = sentiment_data or {}
        reddit_data = reddit_data or {}
        paper_trading_stats = paper_trading_stats or {}

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Trading Signals - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            font-size: 14px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-label {{
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        .signals {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .signal-card {{
            border: 2px solid #f0f0f0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .signal-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }}
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .ticker {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .conviction {{
            font-size: 20px;
            font-weight: bold;
            padding: 8px 15px;
            border-radius: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .signal-type {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 10px;
            background: #f0f0f0;
            color: #333;
        }}
        .triggers {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }}
        .trigger {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .trigger.velocity {{ background: #ffeaa7; color: #d63031; }}
        .trigger.insider {{ background: #74b9ff; color: #0984e3; }}
        .trigger.sentiment {{ background: #a29bfe; color: #6c5ce7; }}
        .trigger.technical {{ background: #55efc4; color: #00b894; }}
        .trigger.reddit {{ background: #fab1a0; color: #e17055; }}
        .notes {{
            color: #666;
            line-height: 1.6;
            margin-top: 10px;
        }}
        .price {{
            font-size: 18px;
            color: #00b894;
            margin-top: 5px;
        }}
        .free-badge {{
            display: inline-block;
            background: #00b894;
            color: white;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #666;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            font-size: 12px;
        }}
        .paper-trading {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .pt-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .pt-metric-card {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            text-align: center;
        }}
        .pt-metric-value {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .pt-metric-value.positive {{ color: #00b894; }}
        .pt-metric-value.negative {{ color: #d63031; }}
        .pt-metric-value.neutral {{ color: #667eea; }}
        .pt-metric-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .pt-position {{
            border-left: 4px solid #00b894;
            padding: 10px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .pt-closed {{
            border-left-color: #667eea;
        }}
        .pt-loss {{
            border-left-color: #d63031;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 Stock Trading Signals Dashboard</h1>
            <p class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p class="subtitle">Using 100% FREE Data Sources <span class="free-badge">FREE</span></p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Signals</div>
                <div class="stat-value">{len(signals)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tickers Analyzed</div>
                <div class="stat-value">{len(velocity_data)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Technical Analysis</div>
                <div class="stat-value">{len(technical_data)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Sentiment Tracked</div>
                <div class="stat-value">{len(sentiment_data)}</div>
            </div>
        </div>

        {self._generate_paper_trading_html(paper_trading_stats)}

        <div class="signals">
            <h2>🎯 Top Trading Signals</h2>
            {self._generate_signals_html(signals, velocity_data, technical_data, sentiment_data, reddit_data)}
        </div>

        <div class="footer">
            <p>Stock Trader - Powered by FREE data sources</p>
            <p>Alpha Vantage • YFinance • VADER • Reddit • Technical Analysis</p>
        </div>
    </div>
</body>
</html>
        """

        # Save to file
        filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)

    def _generate_signals_html(self,
                               signals: List[Any],
                               velocity_data: Dict,
                               technical_data: Dict,
                               sentiment_data: Dict,
                               reddit_data: Dict) -> str:
        """Generate HTML for signal cards"""
        if not signals:
            return "<p>No signals generated</p>"

        html = ""
        for signal in signals[:20]:  # Top 20 signals
            ticker = signal.ticker
            vel = velocity_data.get(ticker, {})
            tech = technical_data.get(ticker, {})
            sent = sentiment_data.get(ticker, {})
            reddit = reddit_data.get(ticker, {})

            # Generate trigger badges with proper styling
            trigger_badges = ""
            for trigger in signal.triggers:
                css_class = self._get_trigger_class(trigger)
                trigger_badges += f'<span class="trigger {css_class}">{self._format_trigger(trigger)}</span>'

            # Technical details
            tech_info = ""
            if tech:
                rsi = tech.get('rsi_14', 0)
                trend = tech.get('trend', 'neutral')
                tech_score = tech.get('technical_score', 0)
                tech_info = f"""
                <div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Technical:</strong> RSI: {rsi:.1f} | Trend: {trend} | Score: {tech_score:.0f}/100
                </div>
                """

            # Sentiment details
            sent_info = ""
            if sent:
                sent_score = sent.get('sentiment_score', 0)
                sent_label = sent.get('sentiment_label', 'neutral')
                sent_info = f"""
                <div style="margin-top: 5px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Sentiment:</strong> {sent_label} ({sent_score:.2f})
                </div>
                """

            # Reddit details
            reddit_info = ""
            if reddit:
                mentions = reddit.get('mention_count', 0)
                reddit_info = f"""
                <div style="margin-top: 5px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <strong>Reddit:</strong> {mentions} mentions in last 24h
                </div>
                """

            html += f"""
            <div class="signal-card">
                <div class="signal-header">
                    <div>
                        <span class="ticker">{ticker}</span>
                        <span class="signal-type">{signal.signal_type.replace('_', ' ').title()}</span>
                    </div>
                    <span class="conviction">{signal.conviction_score:.0f}</span>
                </div>
                <div class="triggers">
                    {trigger_badges}
                </div>
                <div class="notes">{signal.notes}</div>
                <div class="price">Current Price: ${signal.price_at_signal:.2f}</div>
                {tech_info}
                {sent_info}
                {reddit_info}
            </div>
            """

        return html

    def _get_trigger_class(self, trigger: str) -> str:
        """Map trigger type to CSS class"""
        if 'velocity' in trigger or 'mention' in trigger:
            return 'velocity'
        elif 'insider' in trigger:
            return 'insider'
        elif 'sentiment' in trigger:
            return 'sentiment'
        elif 'technical' in trigger or 'rsi' in trigger or 'golden' in trigger or 'breakout' in trigger:
            return 'technical'
        elif 'reddit' in trigger:
            return 'reddit'
        return ''

    def _format_trigger(self, trigger: str) -> str:
        """Format trigger name for display"""
        return trigger.replace('_', ' ').title()

    def _generate_paper_trading_html(self, stats: Dict) -> str:
        """Generate HTML for paper trading performance section"""
        if not stats or not stats.get('closed_trades'):
            return ""

        closed = stats['closed_trades']
        open_pos = stats['open_positions']

        # Determine color classes
        win_rate_class = 'positive' if closed['win_rate'] >= 50 else 'negative'
        avg_return_class = 'positive' if closed['avg_return_pct'] > 0 else 'negative'
        total_pnl_class = 'positive' if closed['total_pnl'] > 0 else 'negative'
        unrealized_class = 'positive' if open_pos.get('unrealized_pnl', 0) > 0 else 'negative'

        html = f"""
        <div class="paper-trading">
            <h2>📊 Paper Trading Performance</h2>
            <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                Tracking mock trades to validate signal performance (Moderate Strategy: 30 days, -10% stop, +20% target)
            </p>

            <h3 style="margin-top: 20px; color: #667eea;">Closed Positions Stats</h3>
            <div class="pt-metrics">
                <div class="pt-metric-card">
                    <div class="pt-metric-value neutral">{closed['count']}</div>
                    <div class="pt-metric-label">Total Trades</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value {win_rate_class}">{closed['win_rate']:.1f}%</div>
                    <div class="pt-metric-label">Win Rate</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value {avg_return_class}">{closed['avg_return_pct']:+.1f}%</div>
                    <div class="pt-metric-label">Avg Return</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value {total_pnl_class}">${closed['total_pnl']:+.0f}</div>
                    <div class="pt-metric-label">Total P/L</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value neutral">{closed['avg_days_held']:.0f}</div>
                    <div class="pt-metric-label">Avg Days Held</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value positive">{closed['best_return']:.1f}%</div>
                    <div class="pt-metric-label">Best Trade</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value negative">{closed['worst_return']:.1f}%</div>
                    <div class="pt-metric-label">Worst Trade</div>
                </div>
            </div>

            <h3 style="margin-top: 25px; color: #667eea;">Open Positions ({open_pos['count']})</h3>
            <div class="pt-metrics">
                <div class="pt-metric-card">
                    <div class="pt-metric-value neutral">${open_pos['total_deployed']:,.0f}</div>
                    <div class="pt-metric-label">Capital Deployed</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value {unrealized_class}">${open_pos.get('unrealized_pnl', 0):+.0f}</div>
                    <div class="pt-metric-label">Unrealized P/L</div>
                </div>
                <div class="pt-metric-card">
                    <div class="pt-metric-value {unrealized_class}">{open_pos.get('unrealized_pct', 0):+.1f}%</div>
                    <div class="pt-metric-label">Unrealized %</div>
                </div>
            </div>
        """

        # Add recent closes if available
        if 'recent_closes' in stats and stats['recent_closes']:
            html += """
            <h3 style="margin-top: 25px; color: #667eea;">Recent Closes (Last 7 Days)</h3>
            """
            for trade in stats['recent_closes'][:5]:
                pnl_class = 'pt-position' if trade['profit_loss'] > 0 else 'pt-position pt-loss'
                exit_icon = '✅' if trade['profit_loss'] > 0 else '❌'
                html += f"""
                <div class="{pnl_class}">
                    <strong>{exit_icon} {trade['ticker']}</strong> •
                    {trade['exit_reason'].replace('_', ' ').title()} •
                    <span style="color: {'#00b894' if trade['profit_loss'] > 0 else '#d63031'}; font-weight: bold;">
                        {trade['return_pct']:+.1f}% (${trade['profit_loss']:+.0f})
                    </span> •
                    {trade['days_held']} days •
                    Entry: ${trade['entry_price']:.2f} → Exit: ${trade['exit_price']:.2f}
                </div>
                """

        # Add open positions if available
        if 'open_positions' in stats and stats['open_positions']:
            html += """
            <h3 style="margin-top: 25px; color: #667eea;">Current Open Positions</h3>
            """
            for pos in stats['open_positions'][:10]:
                current_price = pos.get('current_price')
                if current_price:
                    pnl_class = 'pt-position' if pos.get('unrealized_pnl', 0) > 0 else 'pt-position pt-loss'
                    html += f"""
                    <div class="{pnl_class}">
                        <strong>{pos['ticker']}</strong> •
                        Conviction: {pos['conviction']} •
                        Entry: ${pos['entry_price']:.2f} → Now: ${current_price:.2f} •
                        <span style="color: {'#00b894' if pos.get('unrealized_pnl', 0) > 0 else '#d63031'}; font-weight: bold;">
                            {pos.get('unrealized_pct', 0):+.1f}% (${pos.get('unrealized_pnl', 0):+.0f})
                        </span> •
                        {pos['days_held']} days •
                        Stop: ${pos['stop_loss']:.2f} | Target: ${pos['target_price']:.2f}
                    </div>
                    """

        html += """
        </div>
        """

        return html
