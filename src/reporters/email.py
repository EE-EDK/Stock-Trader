"""
@file email.py
@brief HTML email report generator and sender
@details Creates and sends formatted email reports with signals and velocity data
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EmailReporter:
    """
    @class EmailReporter
    @brief Generate and send HTML email reports
    @details Creates formatted email reports with trading signals and velocity watchlist
    """

    def __init__(self, config: Dict[str, Any]):
        """
        @brief Initialize email reporter
        @param config Email configuration dictionary
        """
        self.config = config
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.sender = config.get('sender')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])

    def generate_report(self,
                       signals: List[Any],
                       velocity_data: Dict[str, Dict[str, float]],
                       include_charts: bool = True,
                       watchlist_size: int = 20) -> str:
        """
        @brief Generate HTML email content
        @param signals List of Signal objects to include
        @param velocity_data Dictionary of velocity metrics by ticker
        @param include_charts Whether to include chart images
        @param watchlist_size Number of tickers to include in watchlist
        @return HTML content as string
        """
        html = self._generate_header()
        html += self._generate_signals_section(signals)
        html += self._generate_velocity_watchlist(velocity_data, watchlist_size)
        html += self._generate_footer()

        logger.info(f"Generated email report with {len(signals)} signals")
        return html

    def _generate_header(self) -> str:
        """
        @brief Generate email header with styling
        @return HTML header string
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .signal-card {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 15px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .conviction {{
                    font-size: 24px;
                    font-weight: bold;
                }}
                .conviction.high {{
                    color: #00c853;
                }}
                .conviction.medium {{
                    color: #ffc107;
                }}
                .conviction.low {{
                    color: #ff5722;
                }}
                .ticker {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #1a1a2e;
                }}
                .triggers {{
                    display: flex;
                    gap: 8px;
                    margin-top: 10px;
                    flex-wrap: wrap;
                }}
                .trigger {{
                    background: #e3f2fd;
                    color: #1565c0;
                    padding: 4px 12px;
                    border-radius: 15px;
                    font-size: 12px;
                }}
                .notes {{
                    color: #666;
                    margin-top: 10px;
                    font-size: 14px;
                }}
                .velocity-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                }}
                .velocity-table th, .velocity-table td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                }}
                .velocity-table th {{
                    background: #f5f5f5;
                    font-weight: 600;
                }}
                .positive {{
                    color: #00c853;
                }}
                .negative {{
                    color: #ff5722;
                }}
                .footer {{
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                    margin-top: 30px;
                }}
                h2 {{
                    color: #1a1a2e;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin:0;">📊 Sentiment Velocity Report</h1>
                <p style="margin:10px 0 0 0; opacity: 0.8;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>
        """

    def _generate_signals_section(self, signals: List[Any]) -> str:
        """
        @brief Generate HTML for signals section
        @param signals List of Signal objects
        @return HTML string
        """
        html = "<h2>🎯 Today's Signals</h2>"

        if not signals:
            html += """
            <div class="signal-card">
                <p style="text-align: center; color: #666;">No signals met conviction threshold today.</p>
            </div>
            """
            return html

        for signal in signals:
            conviction_class = 'high' if signal.conviction_score >= 70 else \
                              'medium' if signal.conviction_score >= 50 else 'low'

            triggers_html = ''.join([
                f'<span class="trigger">{t.replace("_", " ").title()}</span>'
                for t in signal.triggers
            ])

            # Build price display if available
            price_display = ""
            if signal.price_at_signal is not None:
                price_display = f'<div style="margin-top: 10px; font-size: 13px; color: #999;">Price at signal: ${signal.price_at_signal:.2f}</div>'

            html += f"""
            <div class="signal-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="ticker">{signal.ticker}</span>
                    <span class="conviction {conviction_class}">{signal.conviction_score:.0f}</span>
                </div>
                <div class="triggers">{triggers_html}</div>
                <div class="notes">{signal.notes}</div>
                {price_display}
            </div>
            """

        return html

    def _generate_velocity_watchlist(self,
                                     velocity_data: Dict[str, Dict[str, float]],
                                     size: int = 20) -> str:
        """
        @brief Generate HTML for velocity watchlist table
        @param velocity_data Dictionary of velocity metrics
        @param size Number of top tickers to show
        @return HTML string
        """
        html = "<h2>📈 Velocity Watchlist (Top 20)</h2>"
        html += """
        <table class="velocity-table">
            <tr>
                <th>Ticker</th>
                <th>24h Velocity</th>
                <th>7d Trend</th>
                <th>Composite</th>
            </tr>
        """

        # Sort by composite score and take top N
        sorted_velocity = sorted(
            velocity_data.items(),
            key=lambda x: x[1].get('composite_score', 0),
            reverse=True
        )[:size]

        for ticker, vel in sorted_velocity:
            vel_24h = vel.get('mention_velocity_24h', 0)
            vel_class = 'positive' if vel_24h > 0 else 'negative'

            html += f"""
            <tr>
                <td><strong>{ticker}</strong></td>
                <td class="{vel_class}">{vel_24h:+.0f}%</td>
                <td>{vel.get('mention_velocity_7d', 0):+.1f}</td>
                <td>{vel.get('composite_score', 0):.0f}</td>
            </tr>
            """

        html += "</table>"
        return html

    def _generate_footer(self) -> str:
        """
        @brief Generate email footer
        @return HTML footer string
        """
        return """
            <div class="footer">
                <p>Generated by Sentiment Velocity Tracker</p>
                <p>⚠️ This is not financial advice. Paper trade first.</p>
            </div>
        </body>
        </html>
        """

    def send(self, html_content: str, subject: Optional[str] = None) -> bool:
        """
        @brief Send the HTML email
        @param html_content HTML email body
        @param subject Optional custom subject line
        @return True if sent successfully, False otherwise
        """
        if not self.sender or not self.password or not self.recipients:
            logger.error("Email configuration incomplete")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject or f"📊 Sentiment Velocity Report - {datetime.now().strftime('%m/%d')}"
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)

            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {len(self.recipients)} recipients")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_test_email(self) -> bool:
        """
        @brief Send a test email to verify configuration
        @return True if sent successfully, False otherwise
        """
        test_html = """
        <html>
            <body>
                <h1>Test Email</h1>
                <p>This is a test email from Sentiment Velocity Tracker.</p>
                <p>If you receive this, your email configuration is working correctly.</p>
            </body>
        </html>
        """

        return self.send(test_html, subject="Test Email - Sentiment Velocity Tracker")
