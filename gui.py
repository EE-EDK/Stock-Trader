#!/usr/bin/env python3
"""
Stock Trader GUI - Modern interface for configuration and pipeline execution
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import yaml
import subprocess
import threading
import queue
import os
from pathlib import Path


class StockTraderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Trader - Configuration & Control Panel")
        self.root.geometry("1200x800")

        # Config file path
        self.config_path = "config/config.yaml"
        self.config = {}

        # GUI settings file path (for utils folder location)
        self.settings_path = ".gui_settings.yaml"
        self.settings = {}

        # Queue for pipeline output
        self.output_queue = queue.Queue()
        self.pipeline_process = None

        # Queue for utilities output
        self.util_output_queue = queue.Queue()

        # Load GUI settings
        self.load_settings()

        # Create main container
        self.create_widgets()

        # Load existing config
        self.load_config()

        # Start output queue checkers
        self.check_output_queue()
        self.check_util_output_queue()

    def create_widgets(self):
        """Create all GUI widgets"""
        # Create notebook (tabbed interface)
        self.notebook = ttkb.Notebook(self.root, bootstyle="dark")
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Create tabs
        self.create_api_keys_tab()
        self.create_collection_tab()
        self.create_paper_trading_tab()
        self.create_backtesting_tab()
        self.create_thresholds_tab()
        self.create_email_tab()
        self.create_utilities_tab()
        self.create_pipeline_tab()

        # Bottom buttons
        button_frame = ttkb.Frame(self.root)
        button_frame.pack(fill=X, padx=10, pady=10)

        ttkb.Button(
            button_frame,
            text="💾 Save Configuration",
            command=self.save_config,
            bootstyle="success"
        ).pack(side=LEFT, padx=5)

        ttkb.Button(
            button_frame,
            text="🔄 Reload Configuration",
            command=self.load_config,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)

        ttkb.Button(
            button_frame,
            text="❌ Exit",
            command=self.root.quit,
            bootstyle="danger"
        ).pack(side=RIGHT, padx=5)

    def create_api_keys_tab(self):
        """API Keys configuration tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="🔑 API Keys")

        # Help button at the top
        help_frame = ttkb.Frame(tab)
        help_frame.pack(fill=X, padx=10, pady=10)

        ttkb.Button(
            help_frame,
            text="📖 API Setup Guide",
            command=self.show_api_setup_guide,
            bootstyle="info-outline",
            width=20
        ).pack(side=LEFT, padx=5)

        ttkb.Label(
            help_frame,
            text="Click for detailed instructions on getting your FREE API keys",
            font=("Helvetica", 9, "italic")
        ).pack(side=LEFT, padx=10)

        # Scrollable frame
        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollbar = ttkb.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # API Keys section
        self.api_vars = {}

        # Finnhub (Required)
        self.create_labeled_entry(
            scrollable_frame, "Finnhub API Key (REQUIRED)", "api_keys.finnhub",
            "https://finnhub.io/register - FREE tier: 60 calls/min", row=0
        )

        # Alpha Vantage
        self.create_labeled_entry(
            scrollable_frame, "Alpha Vantage API Key", "api_keys.alphavantage",
            "https://www.alphavantage.co/support/#api-key - FREE: 100 calls/day", row=1
        )

        # FMP
        self.create_labeled_entry(
            scrollable_frame, "Financial Modeling Prep Key", "api_keys.fmp",
            "https://site.financialmodelingprep.com - FREE: 250 calls/day", row=2
        )

        # FRED
        self.create_labeled_entry(
            scrollable_frame, "FRED API Key", "api_keys.fred",
            "https://fred.stlouisfed.org/docs/api/api_key.html - FREE", row=3
        )

        # Reddit section
        ttkb.Label(
            scrollable_frame,
            text="Reddit API (Optional)",
            font=("Helvetica", 12, "bold"),
            bootstyle="info"
        ).grid(row=4, column=0, columnspan=2, sticky=W, padx=10, pady=(20, 5))

        self.create_labeled_entry(
            scrollable_frame, "Reddit Client ID", "api_keys.reddit.client_id",
            "https://www.reddit.com/prefs/apps - Create app", row=5
        )

        self.create_labeled_entry(
            scrollable_frame, "Reddit Client Secret", "api_keys.reddit.client_secret",
            "", row=6
        )

        self.create_labeled_entry(
            scrollable_frame, "Reddit User Agent", "api_keys.reddit.user_agent",
            "Example: stock-tracker:v1.0 (by u/yourusername)", row=7
        )

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_collection_tab(self):
        """Data collection settings tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="📊 Data Collection")

        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollbar = ttkb.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0

        # Alpha Vantage
        self.create_section_header(scrollable_frame, "Alpha Vantage Sentiment", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.alphavantage.enabled", row,
            tooltip="Enable Alpha Vantage news sentiment analysis. Provides bullish/bearish sentiment scores from financial news articles. Uses FREE API tier (100 calls/day).")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Top N Tickers", "collection.alphavantage.top_n", 1, 100, row,
            tooltip="Analyze sentiment for top N tickers by social media mentions. Lower = fewer API calls. Recommended: 20 for FREE tier to stay within limits.")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Articles per Ticker", "collection.alphavantage.articles_per_ticker", 1, 100, row,
            tooltip="Number of news articles to analyze per ticker. More articles = better sentiment accuracy but uses more API calls. Recommended: 50.")
        row += 1

        # YFinance
        self.create_section_header(scrollable_frame, "Yahoo Finance (FREE - Unlimited)", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.yfinance.enabled", row,
            tooltip="Enable Yahoo Finance data collection. Provides stock fundamentals, company info, and financial metrics. 100% FREE with unlimited calls.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect Fundamentals", "collection.yfinance.collect_fundamentals", row,
            tooltip="Collect fundamental data: P/E ratio, market cap, EPS, dividend yield, debt ratios. Used to filter out overvalued or risky stocks.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect Analyst Ratings", "collection.yfinance.collect_analyst_ratings", row,
            tooltip="Collect Wall Street analyst recommendations (buy/hold/sell) and price targets. Useful for confirming signal quality.")
        row += 1

        # VADER Sentiment
        self.create_section_header(scrollable_frame, "VADER Sentiment (Local - No API)", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.vader_sentiment.enabled", row,
            tooltip="Enable VADER (Valence Aware Dictionary for sEntiment Reasoning). Local sentiment analysis - no API required. Analyzes scraped headlines for bullish/bearish tone.")
        row += 1
        self.create_checkbox(scrollable_frame, "Scrape Headlines", "collection.vader_sentiment.scrape_headlines", row,
            tooltip="Automatically scrape financial news headlines from public sources and analyze sentiment. Backup for Alpha Vantage when API limit reached.")
        row += 1

        # Reddit
        self.create_section_header(scrollable_frame, "Reddit", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.reddit.enabled", row,
            tooltip="Enable Reddit data collection from r/wallstreetbets, r/stocks, r/investing. Tracks social momentum and viral stocks. Requires API credentials.")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Lookback Hours", "collection.reddit.lookback_hours", 1, 168, row,
            tooltip="How many hours of Reddit history to analyze. 24 hours = daily momentum. 168 hours = weekly trends. Lower = fresher signals.")
        row += 1

        # Technical Analysis
        self.create_section_header(scrollable_frame, "Technical Analysis (No API)", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.technical_analysis.enabled", row,
            tooltip="Enable technical indicator calculations: RSI, MACD, Bollinger Bands, Moving Averages. Uses local price data - no API required.")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Lookback Days", "collection.technical_analysis.lookback_days", 10, 200, row,
            tooltip="Days of price history for technical calculations. 50 days = standard for RSI/MACD. More = smoother trends but slower reaction. Less = faster signals but noisier.")
        row += 1

        # FRED
        self.create_section_header(scrollable_frame, "FRED Macro Indicators", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.fred.enabled", row,
            tooltip="Enable Federal Reserve Economic Data (FRED) collection. Tracks macro economic conditions to assess market risk. FREE API with 120 calls/minute.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect VIX", "collection.fred.collect_vix", row,
            tooltip="VIX (Volatility Index) - Market 'fear gauge'. High VIX (>30) = high volatility/risk. Low VIX (<15) = calm market. Used to adjust position sizing.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect Rates", "collection.fred.collect_rates", row,
            tooltip="10-Year Treasury Rate - Risk-free rate benchmark. Rising rates can pressure stock valuations. Affects discount rate for future earnings.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect Unemployment", "collection.fred.collect_unemployment", row,
            tooltip="Unemployment Rate - Economic health indicator. Low (<4%) = strong economy. High (>7%) = recession risk. Affects consumer spending and earnings.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect Inflation", "collection.fred.collect_inflation", row,
            tooltip="CPI (Consumer Price Index) - Inflation measure. Target ~2% = healthy. High (>4%) = inflation concerns, Fed may raise rates. Affects profit margins.")
        row += 1
        self.create_checkbox(scrollable_frame, "Collect Forex", "collection.fred.collect_forex", row,
            tooltip="USD/EUR Exchange Rate - Dollar strength indicator. Strong dollar hurts international revenue. Affects companies with foreign exposure.")
        row += 1

        # Congress Trades
        self.create_section_header(scrollable_frame, "Congress Stock Trades (100% FREE!)", row)
        row += 1
        self.create_checkbox(scrollable_frame, "Enabled", "collection.congress.enabled", row,
            tooltip="Track stock trades by US Congress members (House & Senate). Studies show Congressional trades can outperform market. 100% FREE - no API key needed!")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Lookback Days", "collection.congress.lookback_days", 7, 365, row,
            tooltip="Days of Congressional trading history to collect. 90 days = quarterly activity. Trades must be reported within 45 days of transaction. Longer lookback = more historical context.")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_paper_trading_tab(self):
        """Paper trading configuration tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="📈 Paper Trading")

        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollbar = ttkb.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0

        self.create_checkbox(scrollable_frame, "Enable Paper Trading", "paper_trading.enabled", row,
            tooltip="Enable mock trading system to validate signals before risking real capital. Tracks entry/exit, P/L, win rate. Build confidence with 30+ days of paper trading first!")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Minimum Conviction", "paper_trading.min_conviction", 0, 100, row,
            tooltip="Only create paper trades for signals with conviction >= this value. Higher = more selective. Recommended: 60 for quality signals. 70+ for high conviction only.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Position Size ($)", "paper_trading.position_size", 100, 10000, row,
            tooltip="Base position size in dollars. Actual size scales with conviction (50 conv = 1x, 100 conv = 2x). Example: $1000 base, 75 conviction = $1500 position.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Max Open Positions", "paper_trading.max_open_positions", 1, 50, row,
            tooltip="Maximum concurrent open positions. Limits total capital deployed. Prevents over-concentration. Recommended: 10 for diversification. Lower = more selective.")
        row += 1

        self.create_section_header(scrollable_frame, "Exit Strategy", row)
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Hold Days", "paper_trading.hold_days", 1, 365, row,
            tooltip="Auto-close positions after this many days. Conservative: 14 days. Moderate: 30 days. Aggressive: 60 days. Longer = more patience for gains.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Stop Loss %", "paper_trading.stop_loss_pct", -50, 0, row,
            tooltip="Exit if position loses this %. -10% = exit when down 10%. Conservative: -5%. Moderate: -10%. Aggressive: -15%. Protects against large losses.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Take Profit %", "paper_trading.take_profit_pct", 0, 200, row,
            tooltip="Exit if position gains this %. 20% = exit when up 20%. Conservative: 10%. Moderate: 20%. Aggressive: 30%. Locks in profits before reversals.")
        row += 1

        self.create_section_header(scrollable_frame, "Reporting", row)
        row += 1

        self.create_checkbox(scrollable_frame, "Report in Dashboard", "paper_trading.report_in_dashboard", row,
            tooltip="Include paper trading performance section in HTML dashboard. Shows win rate, total P/L, open positions, recent closes. Recommended: enabled for visibility.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Backfill Days", "paper_trading.backfill_days", 0, 365, row,
            tooltip="On first run, create paper trades for historical signals from last N days. 30 days = good starting data. 0 = no backfill. Safe to run multiple times (idempotent).")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_backtesting_tab(self):
        """Backtesting configuration tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="🔬 Backtesting")

        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        row = 0

        self.create_labeled_spinbox(scrollable_frame, "Initial Capital ($)", "backtesting.initial_capital", 1000, 100000, row,
            tooltip="Starting capital for backtest simulation. $10,000 typical. Higher = more realistic position sizing. Doesn't affect returns % but affects absolute P/L.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Position Size ($)", "backtesting.position_size", 100, 10000, row,
            tooltip="Base position size per trade. Gets multiplied by conviction if 'Conviction Weighted' enabled. $1,000 standard. Lower = more diversification, higher = concentrated bets.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Max Positions", "backtesting.max_positions", 1, 50, row,
            tooltip="Maximum concurrent open positions in backtest. 10 = good diversification. Lower = fewer trades (need stronger signals). Higher = more capital deployed.")
        row += 1

        self.create_checkbox(scrollable_frame, "Conviction Weighted Sizing", "backtesting.conviction_weighted", row,
            tooltip="Scale position size by conviction score. 50 conv = 1x base, 100 conv = 2x base. Recommended: enabled. Puts more capital behind high-conviction signals.")
        row += 1

        self.create_section_header(scrollable_frame, "Exit Strategy", row)
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Hold Days", "backtesting.hold_days", 1, 365, row,
            tooltip="Maximum days to hold position before auto-exit. 30 days standard. Longer = more patience for winners. Shorter = faster turnover. Must match paper trading for comparison.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Stop Loss %", "backtesting.stop_loss_pct", -50, 0, row,
            tooltip="Exit when position loses this %. -10% standard. Tighter (-5%) = less drawdown but more whipsaws. Looser (-15%) = ride out dips but bigger losses possible.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Take Profit %", "backtesting.take_profit_pct", 0, 200, row,
            tooltip="Exit when position gains this %. 20% standard. Lower (10%) = lock profits early, higher (30%) = let winners run. Match paper trading settings for valid comparison.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "Min Conviction", "backtesting.min_conviction", 0, 100, row,
            tooltip="Only backtest signals with conviction >= this value. 60+ recommended. Higher = test only quality signals. Lower = test all signals. Affects number of trades in backtest.")

        canvas.pack(side="left", fill="both", expand=True)

    def create_thresholds_tab(self):
        """Signal thresholds configuration tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="⚙️ Signal Thresholds")

        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollbar = ttkb.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0

        # Velocity Spike
        self.create_section_header(scrollable_frame, "Velocity Spike", row)
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Mention Velocity 24h Min (%)", "thresholds.velocity_spike.mention_vel_24h_min", 0, 1000, row,
            tooltip="Minimum % increase in social mentions over 24 hours to trigger velocity spike signal. 100% = mentions doubled. Higher = stricter, fewer signals. 100-150% recommended.")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Composite Score Min", "thresholds.velocity_spike.composite_score_min", 0, 100, row,
            tooltip="Minimum composite velocity score (combines mention trend, sentiment velocity, volume divergence). 60+ recommended. Higher = higher quality velocity signals. 0-100 scale.")
        row += 1

        # Insider Cluster
        self.create_section_header(scrollable_frame, "Insider Cluster", row)
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Min Insiders", "thresholds.insider_cluster.min_insiders", 1, 10, row,
            tooltip="Minimum number of different insiders buying to trigger cluster signal. 2+ = multiple insiders agree. Higher = stronger signal but fewer triggers. 2-3 recommended.")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Lookback Days", "thresholds.insider_cluster.lookback_days", 1, 90, row,
            tooltip="Days to look back for insider purchases. 14 days = recent insider activity. Longer = more historical context. Shorter = fresher signals. 14-30 days recommended.")
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Min Value Total ($)", "thresholds.insider_cluster.min_value_total", 1000, 10000000, row,
            tooltip="Minimum combined dollar value of insider purchases to trigger signal. $100K+ = serious money. Higher = more conviction from insiders. $100K-$500K recommended.")
        row += 1

        # Minimum Conviction
        self.create_section_header(scrollable_frame, "Reporting", row)
        row += 1
        self.create_labeled_spinbox(scrollable_frame, "Minimum Conviction to Report", "thresholds.minimum_conviction", 0, 100, row,
            tooltip="Only show signals in dashboard/email with conviction >= this value. 40+ = all signals. 60+ = quality signals. 70+ = high conviction only. Filters noise from output.")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_email_tab(self):
        """Email configuration tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="📧 Email")

        canvas = tk.Canvas(tab, bg='#2b3e50')
        scrollable_frame = ttkb.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        row = 0

        self.create_checkbox(scrollable_frame, "Enable Email Reports", "email.enabled", row,
            tooltip="Send email alerts when new signals are generated. Get notified immediately of trading opportunities. Requires SMTP credentials below. Gmail recommended.")
        row += 1

        self.create_labeled_entry(scrollable_frame, "SMTP Server", "email.smtp_server", "smtp.gmail.com", row,
            tooltip="SMTP server for sending emails. Gmail: smtp.gmail.com. Outlook: smtp-mail.outlook.com. Yahoo: smtp.mail.yahoo.com. Port 587 for TLS.")
        row += 1

        self.create_labeled_spinbox(scrollable_frame, "SMTP Port", "email.smtp_port", 1, 65535, row,
            tooltip="SMTP server port. 587 = TLS (recommended, encrypted). 465 = SSL. 25 = unencrypted (not recommended). Gmail/Outlook use 587.")
        row += 1

        self.create_labeled_entry(scrollable_frame, "Sender Email", "email.sender", "your-email@gmail.com", row,
            tooltip="Email address to send from. Must match credentials below. For Gmail, use your full Gmail address (yourname@gmail.com).")
        row += 1

        self.create_labeled_entry(scrollable_frame, "Password (App Password)", "email.password", "Use Gmail app password", row, show="*",
            tooltip="For Gmail: Use App Password, NOT your regular password. Enable 2FA, then generate app password at https://myaccount.google.com/apppasswords. Other providers: use account password.")
        row += 1

        self.create_labeled_entry(scrollable_frame, "Recipients (comma-separated)", "email.recipients", "email1@gmail.com,email2@gmail.com", row,
            tooltip="Email addresses to send alerts to. Separate multiple recipients with commas. Can include your own email for testing. Example: trader1@gmail.com,trader2@yahoo.com")

        canvas.pack(side="left", fill="both", expand=True)

    def create_utilities_tab(self):
        """Development utilities tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="🛠️ Utilities")

        # Main container with padding
        container = ttkb.Frame(tab)
        container.pack(fill=BOTH, expand=YES, padx=20, pady=20)

        # Title with button frame
        title_frame = ttkb.Frame(container)
        title_frame.pack(fill=X, pady=(0, 20))

        ttkb.Label(
            title_frame,
            text="Development & Testing Utilities",
            font=("Helvetica", 16, "bold")
        ).pack(side=LEFT)

        # Utils folder path button
        ttkb.Button(
            title_frame,
            text="📁 Set Utils Folder Location",
            command=self.set_utils_folder,
            bootstyle="info-outline",
            width=25
        ).pack(side=RIGHT, padx=5)

        # Display current utils folder path
        self.utils_path_label = ttkb.Label(
            container,
            text=f"Utils folder: {self.get_utils_folder()}",
            font=("Helvetica", 9, "italic"),
            foreground="#7f8c8d"
        )
        self.utils_path_label.pack(anchor=W, pady=(0, 10))

        # Type Verification section
        type_frame = ttkb.LabelFrame(container, text="Type Safety Verification", padding=15)
        type_frame.pack(fill=X, pady=10)

        ttkb.Label(
            type_frame,
            text="AST-based type checker - finds dict/float confusion, NoneType issues, unsafe JSON parsing",
            wraplength=600
        ).pack(anchor=W, pady=5)

        ttkb.Button(
            type_frame,
            text="🔍 Run Type Checker",
            command=lambda: self.run_utility("utils/type_check.py", "Type Checker"),
            bootstyle="info"
        ).pack(anchor=W, pady=5)

        # Bug Fix Verification section
        verify_frame = ttkb.LabelFrame(container, text="Bug Fix Verification", padding=15)
        verify_frame.pack(fill=X, pady=10)

        ttkb.Label(
            verify_frame,
            text="Verify all known bug fixes are present in your codebase",
            wraplength=600
        ).pack(anchor=W, pady=5)

        ttkb.Button(
            verify_frame,
            text="✅ Verify Bug Fixes",
            command=lambda: self.run_utility("utils/verify_version.py", "Bug Fix Verifier"),
            bootstyle="success"
        ).pack(anchor=W, pady=5)

        # Backtesting section
        backtest_frame = ttkb.LabelFrame(container, text="Backtesting", padding=15)
        backtest_frame.pack(fill=X, pady=10)

        ttkb.Label(
            backtest_frame,
            text="Run backtest on historical signals to validate strategy performance",
            wraplength=600
        ).pack(anchor=W, pady=5)

        days_frame = ttkb.Frame(backtest_frame)
        days_frame.pack(anchor=W, pady=5)

        ttkb.Label(days_frame, text="Lookback days:").pack(side=LEFT, padx=5)
        self.backtest_days = ttkb.Entry(days_frame, width=10)
        self.backtest_days.insert(0, "90")
        self.backtest_days.pack(side=LEFT, padx=5)

        ttkb.Button(
            backtest_frame,
            text="📊 Run Backtest",
            command=self.run_backtest,
            bootstyle="primary"
        ).pack(anchor=W, pady=5)

        # Runtime Validation section
        runtime_frame = ttkb.LabelFrame(container, text="Runtime Validation", padding=15)
        runtime_frame.pack(fill=X, pady=10)

        ttkb.Label(
            runtime_frame,
            text="Test complete pipeline with mock data (no API calls required)",
            wraplength=600
        ).pack(anchor=W, pady=5)

        ttkb.Button(
            runtime_frame,
            text="🧪 Run Runtime Tests",
            command=lambda: self.run_utility("utils/test_runtime.py", "Runtime Validator"),
            bootstyle="warning"
        ).pack(anchor=W, pady=5)

        # Output area
        output_frame = ttkb.LabelFrame(container, text="Output", padding=10)
        output_frame.pack(fill=BOTH, expand=YES, pady=10)

        self.util_output = scrolledtext.ScrolledText(
            output_frame,
            height=15,
            bg='#2b3e50',
            fg='#ecf0f1',
            font=('Courier', 10)
        )
        self.util_output.pack(fill=BOTH, expand=YES)

    def run_utility(self, script_path, name):
        """Run a utility script and display output"""
        print(f"[DEBUG] run_utility called: {name}, {script_path}")  # Debug
        self.util_output.delete(1.0, tk.END)
        self.util_output_queue.put(f"Running {name}...\n\n")
        print(f"[DEBUG] Queued initial message")  # Debug

        def run():
            try:
                # Get the directory where gui.py is located (project root)
                project_root = os.path.dirname(os.path.abspath(__file__))

                # Use custom utils folder if set
                utils_folder = self.get_utils_folder()
                script_filename = os.path.basename(script_path)
                full_script_path = os.path.join(utils_folder, script_filename)

                # Check if script exists
                if not os.path.exists(full_script_path):
                    self.util_output_queue.put(f"❌ Error: Script not found at {full_script_path}\n")
                    self.util_output_queue.put(f"Please set the correct utils folder location.\n")
                    return

                print(f"[DEBUG] Project root: {project_root}")  # Debug
                print(f"[DEBUG] Starting subprocess: python {full_script_path}")  # Debug

                process = subprocess.Popen(
                    ["python", full_script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',  # Explicitly use UTF-8 to handle emojis on Windows
                    bufsize=1,
                    cwd=project_root  # Run from project root
                )

                print(f"[DEBUG] Process started, reading output...")  # Debug
                for line in process.stdout:
                    self.util_output_queue.put(line)

                process.wait()
                print(f"[DEBUG] Process finished with code: {process.returncode}")  # Debug

                if process.returncode == 0:
                    self.util_output_queue.put(f"\n✅ {name} completed successfully\n")
                else:
                    self.util_output_queue.put(f"\n❌ {name} failed with code {process.returncode}\n")

            except Exception as e:
                print(f"[DEBUG] Exception in run_utility: {e}")  # Debug
                import traceback
                traceback.print_exc()  # Debug
                self.util_output_queue.put(f"\n❌ Error: {str(e)}\n")

        print(f"[DEBUG] Starting background thread")  # Debug
        threading.Thread(target=run, daemon=True).start()
        print(f"[DEBUG] Thread started")  # Debug

    def run_backtest(self):
        """Run backtest with specified days"""
        days = self.backtest_days.get()
        try:
            days_int = int(days)
            if days_int <= 0:
                messagebox.showerror("Invalid Input", "Days must be a positive number")
                return
        except ValueError:
            messagebox.showerror("Invalid Input", "Days must be a valid number")
            return

        self.util_output.delete(1.0, tk.END)
        self.util_output_queue.put(f"Running backtest for last {days} days...\n\n")

        def run():
            try:
                # Get the directory where gui.py is located (project root)
                project_root = os.path.dirname(os.path.abspath(__file__))

                # Use custom utils folder if set
                utils_folder = self.get_utils_folder()
                backtest_script = os.path.join(utils_folder, "backtest.py")

                # Check if script exists
                if not os.path.exists(backtest_script):
                    self.util_output_queue.put(f"❌ Error: backtest.py not found at {backtest_script}\n")
                    self.util_output_queue.put(f"Please set the correct utils folder location.\n")
                    return

                process = subprocess.Popen(
                    ["python", backtest_script, "--days", days],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',  # Explicitly use UTF-8 to handle emojis on Windows
                    bufsize=1,
                    cwd=project_root  # Run from project root
                )

                for line in process.stdout:
                    self.util_output_queue.put(line)

                process.wait()

                if process.returncode == 0:
                    self.util_output_queue.put(f"\n✅ Backtest completed successfully\n")
                else:
                    self.util_output_queue.put(f"\n❌ Backtest failed with code {process.returncode}\n")

            except Exception as e:
                self.util_output_queue.put(f"\n❌ Error: {str(e)}\n")

        threading.Thread(target=run, daemon=True).start()

    def create_pipeline_tab(self):
        """Pipeline execution tab"""
        tab = ttkb.Frame(self.notebook)
        self.notebook.add(tab, text="▶️ Run Pipeline")

        # Control buttons
        control_frame = ttkb.Frame(tab)
        control_frame.pack(fill=X, padx=10, pady=10)

        self.run_btn = ttkb.Button(
            control_frame,
            text="▶️ Run Main Pipeline",
            command=self.run_pipeline,
            bootstyle="success",
            width=20
        )
        self.run_btn.pack(side=LEFT, padx=5)

        self.stop_btn = ttkb.Button(
            control_frame,
            text="⏹️ Stop Pipeline",
            command=self.stop_pipeline,
            bootstyle="danger",
            width=20,
            state=DISABLED
        )
        self.stop_btn.pack(side=LEFT, padx=5)

        ttkb.Button(
            control_frame,
            text="🧪 Run Backtest",
            command=self.run_backtest_from_pipeline,
            bootstyle="info",
            width=20
        ).pack(side=LEFT, padx=5)

        ttkb.Button(
            control_frame,
            text="🧹 Clear Output",
            command=self.clear_output,
            bootstyle="warning",
            width=20
        ).pack(side=LEFT, padx=5)

        # Output console
        console_frame = ttkb.LabelFrame(tab, text="Console Output", bootstyle="primary")
        console_frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        self.console = scrolledtext.ScrolledText(
            console_frame,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#00ff00',
            font=('Consolas', 10),
            state=DISABLED
        )
        self.console.pack(fill=BOTH, expand=YES, padx=5, pady=5)

    # Helper methods for creating form elements
    def create_section_header(self, parent, text, row):
        """Create a section header"""
        ttkb.Label(
            parent,
            text=text,
            font=("Helvetica", 12, "bold"),
            bootstyle="info"
        ).grid(row=row, column=0, columnspan=2, sticky=W, padx=10, pady=(15, 5))

    def create_labeled_entry(self, parent, label, config_key, placeholder="", row=0, show=None, tooltip=None):
        """Create a labeled entry field"""
        label_widget = ttkb.Label(
            parent,
            text=label,
            bootstyle="inverse-dark"
        )
        label_widget.grid(row=row, column=0, sticky=W, padx=10, pady=5)

        var = tk.StringVar()
        entry = ttkb.Entry(
            parent,
            textvariable=var,
            width=40,
            show=show
        )
        entry.grid(row=row, column=1, sticky=W, padx=10, pady=5)

        if placeholder:
            ttkb.Label(
                parent,
                text=placeholder,
                font=("Helvetica", 8),
                bootstyle="secondary"
            ).grid(row=row, column=2, sticky=W, padx=5, pady=5)

        # Add tooltip if provided
        if tooltip:
            self.create_tooltip(label_widget, tooltip)
            self.create_tooltip(entry, tooltip)

        self.api_vars[config_key] = var
        return var

    def create_labeled_spinbox(self, parent, label, config_key, from_, to, row, tooltip=None):
        """Create a labeled spinbox"""
        label_widget = ttkb.Label(
            parent,
            text=label,
            bootstyle="inverse-dark"
        )
        label_widget.grid(row=row, column=0, sticky=W, padx=10, pady=5)

        var = tk.IntVar()
        spinbox = ttkb.Spinbox(
            parent,
            from_=from_,
            to=to,
            textvariable=var,
            width=20
        )
        spinbox.grid(row=row, column=1, sticky=W, padx=10, pady=5)

        # Add tooltip if provided
        if tooltip:
            self.create_tooltip(label_widget, tooltip)
            self.create_tooltip(spinbox, tooltip)

        self.api_vars[config_key] = var
        return var

    def create_checkbox(self, parent, label, config_key, row, tooltip=None):
        """Create a checkbox"""
        var = tk.BooleanVar()
        checkbox = ttkb.Checkbutton(
            parent,
            text=label,
            variable=var,
            bootstyle="success-round-toggle"
        )
        checkbox.grid(row=row, column=0, columnspan=2, sticky=W, padx=10, pady=5)

        # Add tooltip if provided
        if tooltip:
            self.create_tooltip(checkbox, tooltip)

        self.api_vars[config_key] = var
        return var

    def get_nested_value(self, config, key_path):
        """Get nested dictionary value using dot notation"""
        keys = key_path.split('.')
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    def set_nested_value(self, config, key_path, value):
        """Set nested dictionary value using dot notation"""
        keys = key_path.split('.')
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}

                # Populate form fields
                for key, var in self.api_vars.items():
                    value = self.get_nested_value(self.config, key)
                    if value is not None:
                        if isinstance(var, tk.BooleanVar):
                            var.set(bool(value))
                        elif isinstance(var, tk.IntVar):
                            var.set(int(value))
                        elif isinstance(var, tk.StringVar):
                            # Handle list for recipients
                            if key == "email.recipients" and isinstance(value, list):
                                var.set(",".join(value))
                            else:
                                var.set(str(value))

                self.log_to_console("✓ Configuration loaded successfully\n")
            else:
                self.log_to_console("⚠ No config file found, using defaults\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            self.log_to_console(f"✗ Error loading config: {e}\n")

    def save_config(self):
        """Save configuration to YAML file"""
        try:
            # Build config from form values
            config = {
                'api_keys': {},
                'database': {'path': 'data/sentiment.db'},
                'collection': {},
                'paper_trading': {},
                'backtesting': {},
                'thresholds': {},
                'email': {},
                'report': {}
            }

            for key, var in self.api_vars.items():
                value = var.get()

                # Handle recipients list
                if key == "email.recipients" and isinstance(value, str):
                    value = [email.strip() for email in value.split(',') if email.strip()]

                # Don't save placeholder values
                if isinstance(value, str) and ('YOUR_' in value or not value):
                    continue

                self.set_nested_value(config, key, value)

            # Ensure config directory exists
            Path("config").mkdir(exist_ok=True)

            # Save to file
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            messagebox.showinfo("Success", "Configuration saved successfully!")
            self.log_to_console("✓ Configuration saved to config/config.yaml\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            self.log_to_console(f"✗ Error saving config: {e}\n")

    def load_settings(self):
        """Load GUI settings from YAML file"""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    self.settings = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[DEBUG] Failed to load settings: {e}")
            self.settings = {}

    def save_settings(self):
        """Save GUI settings to YAML file"""
        try:
            with open(self.settings_path, 'w') as f:
                yaml.dump(self.settings, f, default_flow_style=False)
        except Exception as e:
            print(f"[DEBUG] Failed to save settings: {e}")

    def get_utils_folder(self):
        """Get the utils folder path from settings or use default"""
        default_utils = "utils"
        utils_folder = self.settings.get('utils_folder', default_utils)

        # Convert to absolute path if relative
        if not os.path.isabs(utils_folder):
            project_root = os.path.dirname(os.path.abspath(__file__))
            utils_folder = os.path.join(project_root, utils_folder)

        return utils_folder

    def set_utils_folder(self):
        """Open dialog to set utils folder location"""
        current_folder = self.get_utils_folder()

        # Open folder selection dialog
        folder = filedialog.askdirectory(
            title="Select Utils Folder Location",
            initialdir=current_folder
        )

        if folder:
            # Save to settings
            self.settings['utils_folder'] = folder
            self.save_settings()

            # Update label
            self.utils_path_label.config(text=f"Utils folder: {folder}")

            messagebox.showinfo(
                "Success",
                f"Utils folder location updated to:\n{folder}\n\nThis setting will be remembered."
            )

    def run_pipeline(self):
        """Run the main pipeline in a separate thread"""
        if self.pipeline_process and self.pipeline_process.poll() is None:
            messagebox.showwarning("Warning", "Pipeline is already running!")
            return

        self.run_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.clear_output()
        self.log_to_console("▶️ Starting main pipeline...\n\n")

        # Run pipeline in thread
        thread = threading.Thread(target=self._run_pipeline_thread, daemon=True)
        thread.start()

    def _run_pipeline_thread(self):
        """Thread function to run pipeline"""
        try:
            self.pipeline_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # Explicitly use UTF-8 to handle emojis on Windows
                bufsize=1
            )

            # Read output line by line
            for line in iter(self.pipeline_process.stdout.readline, ''):
                if line:
                    self.output_queue.put(line)

            self.pipeline_process.wait()

            if self.pipeline_process.returncode == 0:
                self.output_queue.put("\n✓ Pipeline completed successfully!\n")
            else:
                self.output_queue.put(f"\n✗ Pipeline exited with code {self.pipeline_process.returncode}\n")

        except Exception as e:
            self.output_queue.put(f"\n✗ Error running pipeline: {e}\n")

        finally:
            self.root.after(0, lambda: self.run_btn.config(state=NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=DISABLED))

    def stop_pipeline(self):
        """Stop the running pipeline"""
        if self.pipeline_process and self.pipeline_process.poll() is None:
            self.pipeline_process.terminate()
            self.log_to_console("\n⏹️ Pipeline stopped by user\n")
            self.run_btn.config(state=NORMAL)
            self.stop_btn.config(state=DISABLED)

    def run_backtest_from_pipeline(self):
        """Run backtesting script from pipeline tab"""
        self.clear_output()
        self.log_to_console("🧪 Running backtest...\n\n")

        thread = threading.Thread(target=self._run_backtest_pipeline_thread, daemon=True)
        thread.start()

    def _run_backtest_pipeline_thread(self):
        """Thread function to run backtest from pipeline tab"""
        try:
            # Get the directory where gui.py is located (project root)
            project_root = os.path.dirname(os.path.abspath(__file__))

            process = subprocess.Popen(
                ["python", "utils/backtest.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # Explicitly use UTF-8 to handle emojis on Windows
                bufsize=1,
                cwd=project_root  # Run from project root
            )

            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output_queue.put(line)

            process.wait()

            if process.returncode == 0:
                self.output_queue.put("\n✓ Backtest completed!\n")
            else:
                self.output_queue.put(f"\n✗ Backtest failed with code {process.returncode}\n")

        except Exception as e:
            self.output_queue.put(f"\n✗ Error running backtest: {e}\n")

    def log_to_console(self, message):
        """Log message to console"""
        self.console.config(state=NORMAL)
        self.console.insert(tk.END, message)
        self.console.see(tk.END)
        self.console.config(state=DISABLED)

    def clear_output(self):
        """Clear console output"""
        self.console.config(state=NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=DISABLED)

    def show_api_setup_guide(self):
        """Show API setup guide in a popup window"""
        guide_window = tk.Toplevel(self.root)
        guide_window.title("API Setup Quick Start Guide")
        guide_window.geometry("800x700")
        guide_window.configure(bg='#2b3e50')

        # Make it modal
        guide_window.transient(self.root)
        guide_window.grab_set()

        # Scrollable text widget
        text_frame = ttkb.Frame(guide_window)
        text_frame.pack(fill=BOTH, expand=YES, padx=20, pady=20)

        text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            bg='#1e1e1e',
            fg='#ecf0f1',
            font=('Helvetica', 10),
            padx=15,
            pady=15
        )
        text_widget.pack(fill=BOTH, expand=YES)

        # Add content
        guide_content = """🔑 API SETUP QUICK START GUIDE
═══════════════════════════════════════════════════════════

All APIs are 100% FREE with no credit card required!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ FINNHUB (REQUIRED - 2 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What you get: Stock prices, 60 API calls/minute

Steps:
 1. Visit: https://finnhub.io/register
 2. Sign up with email (no credit card)
 3. Copy your API key from the dashboard
 4. Paste into "Finnhub API Key" field above
 5. Click "Save Configuration" at the bottom

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ ALPHA VANTAGE (Recommended - 2 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What you get: News sentiment, market movers, 100 calls/day

Steps:
 1. Visit: https://www.alphavantage.co/support/#api-key
 2. Enter your email → Get instant key (no credit card!)
 3. Copy your API key
 4. Paste into "Alpha Vantage API Key" field
 5. Click "Save Configuration"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ FRED (Optional - 2 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What you get: Economic indicators (VIX, rates, unemployment), 120/min

Steps:
 1. Visit: https://fred.stlouisfed.org/docs/api/api_key.html
 2. Click "Request API Key"
 3. Fill in your information (instant approval)
 4. Copy your API key
 5. Paste into "FRED API Key" field
 6. Go to "Data Collection" tab → Enable FRED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ FINANCIAL MODELING PREP (Optional - 2 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What you get: Earnings calendar, analyst estimates, 250 calls/day

Steps:
 1. Visit: https://site.financialmodelingprep.com/developer/docs/pricing
 2. Sign up for FREE tier
 3. Copy your API key
 4. Paste into "Financial Modeling Prep Key" field

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5️⃣ REDDIT (Optional - Requires manual approval)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Note: Reddit now requires manual approval (1-3 days)

What you get: Track r/wallstreetbets, r/stocks mentions

Steps:
 1. Request Access:
    Visit: https://support.reddithelp.com/hc/en-us/requests/new
    Form: Data API Access Request
    App Name: Stock Sentiment Tracker
    Use Case: Educational/Personal research

 2. Wait for approval email (1-3 days)

 3. Once approved:
    a. Visit: https://www.reddit.com/prefs/apps
    b. Click "create app" at bottom
    c. Name: stock-tracker
    d. Type: Select "script"
    e. Redirect URI: http://localhost:8080
    f. Click "create app"

 4. Copy client_id and client_secret
 5. Paste into Reddit fields above
 6. Set user agent: "stock-tracker:v1.0 (by u/yourname)"

Alternative: System works great without Reddit (9 other FREE sources!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ QUICK START CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Minimum to get started:
 ☐ Finnhub API key (REQUIRED)
 ☐ Alpha Vantage API key (Recommended)
 ☐ Click "Save Configuration"
 ☐ Go to "Run Pipeline" tab
 ☐ Click "Run Main Pipeline"
 ☐ View dashboard in reports/ folder

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 TIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• All APIs are 100% FREE forever - no credit card needed
• Start with just Finnhub + Alpha Vantage (5 min total)
• Add others later as you explore features
• Free tiers have generous limits for personal use
• No recurring costs - own your data locally

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Need help? Check the full README.md for detailed documentation.
"""

        text_widget.insert(1.0, guide_content)
        text_widget.config(state=DISABLED)

        # Close button
        btn_frame = ttkb.Frame(guide_window)
        btn_frame.pack(fill=X, padx=20, pady=(0, 20))

        ttkb.Button(
            btn_frame,
            text="Close",
            command=guide_window.destroy,
            bootstyle="secondary",
            width=15
        ).pack(side=RIGHT)

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget that appears on hover"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

            label = tk.Label(
                tooltip,
                text=text,
                background="#333333",
                foreground="#ffffff",
                relief=tk.SOLID,
                borderwidth=1,
                font=("Helvetica", 9),
                wraplength=300,
                justify=tk.LEFT,
                padx=8,
                pady=6
            )
            label.pack()

            widget._tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                del widget._tooltip

        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def check_output_queue(self):
        """Check output queue and update console"""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.log_to_console(message)
        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.check_output_queue)

    def check_util_output_queue(self):
        """Check utilities output queue and update util_output"""
        try:
            while True:
                message = self.util_output_queue.get_nowait()
                print(f"[DEBUG] Got message from queue: {message[:50]}...")  # Debug
                self.util_output.insert(tk.END, message)
                self.util_output.see(tk.END)
        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.check_util_output_queue)


def main():
    # Create root window with dark theme
    root = ttkb.Window(themename="darkly")
    app = StockTraderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
