# 📈 Stock Trading Signals System

> **Comprehensive stock trading signals powered entirely by FREE data sources**
>
> Combines social momentum, insider trading, technical analysis, and news sentiment to generate high-conviction trading signals. **100% free APIs** - zero recurring costs forever.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FREE APIs](https://img.shields.io/badge/APIs-100%25%20FREE-brightgreen.svg)](https://github.com)
[![Tests](https://img.shields.io/badge/tests-122%20passing-success.svg)](https://github.com)

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/EE-EDK/Stock-Trader.git
cd Stock-Trader

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure (add your FREE API keys)
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your keys (see Setup Guide below)

# 4. Run
python main.py

# 5. View results
firefox reports/dashboard_*.html
```

---

## 📊 What You Get

### 11 FREE Data Sources

| Source | Data | API Calls/Day | Cost | Setup Time |
|--------|------|---------------|------|------------|
| **Finnhub** | Stock prices | 200+ | FREE | 2 min |
| **Alpha Vantage** | News sentiment | 100 | FREE | 2 min |
| **Yahoo Finance** | Fundamentals, ratios | Unlimited | FREE | 0 min |
| **VADER** | Local sentiment | Unlimited | FREE | 0 min |
| **Reddit (PRAW)** | Social mentions | ~100/min | FREE | 2 min |
| **OpenInsider** | Insider trades | Unlimited | FREE | 0 min |
| **ApeWisdom** | Reddit stock mentions | Unlimited | FREE | 0 min |
| **FMP** | Earnings, estimates | 250 | FREE | 2 min |
| **FRED** | Macro indicators (VIX, rates) | 120/min | FREE | 2 min |
| **Congress Trades** | Congressional stock trades | Unlimited | FREE | 0 min |
| **Technical** | RSI, MACD, Bollinger | Unlimited | FREE | 0 min |

**Total: $0/month forever**

### 8 Signal Types

1. **Velocity Spike** - Social mentions surge 100%+ in 24h
2. **Insider Cluster** - Multiple insiders buying
3. **Sentiment Flip** - Major news sentiment shift
4. **Technical Breakout** - Price breaks resistance with volume
5. **RSI Oversold** - RSI < 30, bounce potential
6. **Golden Cross** - SMA20 crosses above SMA50
7. **News Sentiment Bullish** - Positive news coverage
8. **Reddit Viral** - 10+ mentions in 24h

### Technical Indicators

- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Simple & Exponential Moving Averages
- Momentum & Rate of Change
- Support/Resistance Levels
- Trend Detection
- Volume Analysis
- Breakout Detection

---

## 🎯 Features

- ✅ **Multi-source analysis** - Combines 11 different FREE data sources
- ✅ **Conviction scoring** - Ranks signals 0-100 based on strength
- ✅ **HTML dashboards** - Beautiful visual reports
- ✅ **Email alerts** - Optional email notifications
- ✅ **Technical analysis** - Professional-grade indicators
- ✅ **Sentiment analysis** - News + social media
- ✅ **Insider tracking** - Follow the smart money
- ✅ **Congress trades** - Track stock trades by US Representatives & Senators (100% FREE!)
- ✅ **Paper trading** - Mock purchases to validate signals before risking capital
- ✅ **Backtesting** - Validate strategy against historical data with comprehensive metrics
- ✅ **Macro indicators** - FRED economic data integration (VIX, rates, unemployment, etc.)
- ✅ **100% FREE** - Zero recurring costs
- ✅ **Local database** - Your data stays on your machine
- ✅ **Automated** - Set and forget with cron
- ✅ **240+ unit tests** - Comprehensive test coverage

---

## 📁 Project Structure

```
Stock-Trader/
├── main.py                          # Main pipeline orchestrator
├── gui.py                           # Graphical user interface
├── config/
│   ├── config.yaml                  # Your configuration
│   └── config.example.yaml          # Template
├── src/
│   ├── collectors/                  # Data collectors
│   │   ├── alphavantage.py         # Alpha Vantage sentiment
│   │   ├── yfinance_collector.py   # Yahoo Finance data
│   │   ├── vader_sentiment.py      # Local sentiment
│   │   ├── reddit_collector.py     # Reddit data
│   │   ├── fmp.py                  # Financial Modeling Prep
│   │   ├── finnhub.py              # Finnhub prices
│   │   ├── apewisdom.py            # Reddit mentions
│   │   ├── openinsider.py          # Insider trades
│   │   ├── fred.py                 # FRED macro indicators
│   │   └── congress.py             # Congress stock trades
│   ├── metrics/
│   │   ├── velocity.py             # Social momentum
│   │   └── technical.py            # Technical indicators
│   ├── signals/
│   │   └── generator.py            # Signal generation
│   ├── trading/
│   │   └── paper_trading.py        # Paper trading manager
│   ├── analysis/
│   │   └── backtester.py           # Backtesting engine
│   ├── reporters/
│   │   ├── dashboard.py            # HTML dashboard
│   │   ├── charts.py               # Matplotlib charts
│   │   └── email.py                # Email reports
│   └── database/
│       ├── models.py               # Database schema
│       ├── queries.py              # Query helpers
│       ├── paper_trading_schema.sql # Paper trading tables
│       ├── macro_schema.sql        # Macro indicators tables
│       └── congress_schema.sql     # Congress trades tables
├── utils/                          # Development utilities
│   ├── backtest.py                 # Backtesting CLI tool
│   ├── type_check.py               # Type verification system
│   ├── verify_version.py           # Bug fix validator
│   └── test_runtime.py             # Runtime validation
├── tests/                          # Unit tests (238 tests, 50% coverage)
├── reports/                        # Generated dashboards
├── logs/                          # Application logs
├── data/                          # SQLite database
└── requirements.txt               # Dependencies
```

---

## 🔧 Complete Setup Guide

### Step 1: Get Your FREE API Keys

#### 1.1 Finnhub (REQUIRED - 2 minutes)

**What you get:** Stock prices, 60 API calls/minute

1. Visit: https://finnhub.io/register
2. Sign up with email (no credit card needed)
3. Copy your API key
4. Add to `config/config.yaml`:
   ```yaml
   api_keys:
     finnhub: "YOUR_FINNHUB_KEY"
   ```

#### 1.2 Alpha Vantage (RECOMMENDED - 2 minutes)

**What you get:** News sentiment, market movers, 100 calls/day

1. Visit: https://www.alphavantage.co/support/#api-key
2. Enter your email → Get instant key (no credit card!)
3. Copy your API key
4. Add to config:
   ```yaml
   api_keys:
     alphavantage: "YOUR_ALPHAVANTAGE_KEY"
   ```

#### 1.3 Reddit API (OPTIONAL - Manual Approval Required)

**What you get:** Track r/wallstreetbets, r/stocks, r/investing, unlimited

**⚠️ Note:** Reddit now requires manual approval for API access. This can take 1-3 days.

1. Visit: https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164
2. Fill out the form:
   - **Request Type:** Data API Access Request
   - **App Name:** Stock Sentiment Tracker
   - **Description:** Personal project to track stock mentions for sentiment analysis
   - **Use Case:** Educational/Personal research
3. Wait for approval email (typically 1-3 business days)
4. Once approved, visit: https://www.reddit.com/prefs/apps
5. Click "create app" at the bottom
6. Fill in:
   - **Name:** stock-tracker
   - **Type:** Select "script"
   - **Description:** Stock sentiment tracker
   - **Redirect URI:** http://localhost:8080
7. Click "create app"
8. Copy:
   - **client_id** (under "personal use script")
   - **client_secret**
9. Add to config:
   ```yaml
   api_keys:
     reddit:
       client_id: "YOUR_CLIENT_ID"
       client_secret: "YOUR_SECRET"
       user_agent: "stock-tracker:v1.0 (by u/yourusername)"
   ```

**Alternative:** The system works great without Reddit data - you still have 9 other FREE data sources!

#### 1.4 Financial Modeling Prep (OPTIONAL - 2 minutes)

**What you get:** Earnings calendar, analyst estimates, SEC filings, 250 calls/day

1. Visit: https://site.financialmodelingprep.com/developer/docs/pricing
2. Sign up for FREE tier
3. Copy your API key
4. Add to config:
   ```yaml
   api_keys:
     fmp: "YOUR_FMP_KEY"
   ```

### Step 2: Install Dependencies

```bash
# Install all packages
pip install -r requirements.txt
```

This installs:
- **Core:** requests, beautifulsoup4, pyyaml, numpy, pandas
- **FREE data:** yfinance, vaderSentiment, praw
- **Visualization:** matplotlib
- **Testing:** pytest, pytest-cov

### Step 3: Configure Your System

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit with your API keys
nano config/config.yaml  # or use your favorite editor
```

**Minimal configuration:**
```yaml
api_keys:
  finnhub: "your_finnhub_key"        # REQUIRED
  alphavantage: "your_alpha_key"     # Recommended

collection:
  alphavantage:
    enabled: true
    top_n: 20                        # Analyze top 20 to save API calls
    articles_per_ticker: 50

  yfinance:
    enabled: true                    # No API key needed
    collect_fundamentals: true

  vader_sentiment:
    enabled: true                    # Offline, no API needed
    scrape_headlines: true

  reddit:
    enabled: false                   # Set true if you have credentials

  technical_analysis:
    enabled: true                    # Uses your price data, no API
    lookback_days: 50

thresholds:
  minimum_conviction: 40             # Only report signals ≥ 40
```

### Step 4: Run the Pipeline

**Option 1: GUI (Recommended for beginners)**

```bash
python gui.py
```

The GUI provides:
- Visual configuration editor for all settings
- API key management
- Data collection toggles
- Paper trading controls
- Backtesting configuration
- Signal threshold tuning
- Email setup
- Live console output during pipeline runs
- Save/load configuration with one click

**Option 2: Command Line**

```bash
# Full run with dashboard
python main.py

# Skip email notification
python main.py --skip-email

# Debug mode
python main.py --log-level DEBUG

# Custom config
python main.py --config /path/to/config.yaml
```

**Expected output:**
```
============================================================
Starting pipeline run at 2025-12-20 09:00:00
============================================================

Step 1: Collecting data from sources...
  [OK] ApeWisdom: 100 tickers collected
  [OK] OpenInsider: 15 trades collected
  [OK] Finnhub: 95 ticker data points collected

Step 1b: Collecting FREE data sources...
  [OK] Alpha Vantage: 20 sentiment analyses
  [OK] YFinance: 95 stock info records
  [OK] VADER Sentiment: 10 tickers analyzed
  [OK] Reddit: 35 ticker mentions

Step 2: Calculating velocity metrics...
  [OK] Calculated velocity for 100 tickers

Step 2b: Running technical analysis...
  [OK] Technical analysis for 100 tickers

Step 3: Generating signals with FREE data sources...
  [OK] Generated 15 signals above 40 conviction

Step 4b: Generating HTML dashboard...
  [OK] Dashboard saved to: reports/dashboard_20251220_090532.html
  [TIP] Open reports/dashboard_20251220_090532.html in your browser!
============================================================
```

### Step 5: View Your Dashboard

```bash
# Open the HTML dashboard in your browser
firefox reports/dashboard_*.html
# or
open reports/dashboard_*.html  # Mac
```

The dashboard shows:
- **Signal Cards** - Color-coded by conviction
- **Trigger Badges** - Visual indicators for each signal type
- **Technical Breakdown** - RSI, trend, technical score
- **Sentiment Analysis** - News sentiment with scores
- **Reddit Data** - Mention counts and viral status
- **Responsive Design** - Works on desktop and mobile

---

## 🖥️ Graphical User Interface (GUI)

**Modern dark-themed GUI for easy configuration and control**

The Stock Trader includes a full-featured GUI built with ttkbootstrap for users who prefer visual configuration over editing YAML files.

### Features

- **8 Tabbed Sections:**
  1. **API Keys** - Manage all API credentials
  2. **Data Collection** - Toggle and configure data sources
  3. **Paper Trading** - Configure mock trading settings
  4. **Backtesting** - Set up backtesting parameters
  5. **Thresholds** - Tune signal detection thresholds
  6. **Email** - Configure email alerts
  7. **Utilities** - Run development tools (type checker, bug verifier, backtest, runtime tests)
  8. **Run Pipeline** - Execute the pipeline with live console output

- **Dark Theme** - Professional dark UI using ttkbootstrap's "darkly" theme
- **Live Console Output** - See pipeline progress in real-time
- **Configuration Management** - Save/load settings to `config/config.yaml`
- **Input Validation** - Prevents invalid configurations
- **📖 API Setup Guide** - Click-to-open popup with step-by-step FREE API key instructions
- **🎯 Comprehensive Tooltips** - 50+ hover tooltips explaining every configuration option with financial context, recommended values, and trade-offs

### Installation

The GUI requires ttkbootstrap (already in requirements.txt):

```bash
pip install ttkbootstrap
```

### Usage

```bash
# Launch the GUI
python gui.py
```

**Workflow:**
1. Fill in your API keys in the "API Keys" tab
2. Configure data collection settings
3. Set paper trading parameters
4. Adjust signal thresholds
5. Click "Save Configuration" to write to `config/config.yaml`
6. Switch to "Run Pipeline" tab
7. Click "Run Pipeline" to execute with live output

### GUI vs Command Line

| Feature | GUI | Command Line |
|---------|-----|--------------|
| Configuration | Visual forms | Edit YAML file |
| API Key Setup | Copy/paste in tabs | Edit text file |
| Pipeline Execution | Click button | Run `python main.py` |
| Output | Live console in window | Terminal output |
| Validation | Real-time input checks | Manual YAML validation |
| Best For | Beginners, visual learners | Advanced users, automation |

### Screenshot Features

**API Keys Tab:**
- **📖 API Setup Guide Button** - Opens comprehensive popup window with:
  - Step-by-step instructions for all 5 FREE APIs
  - Exact URLs for registration
  - What you get from each API (rates, limits, features)
  - Quick start checklist (get running in 5 minutes)
  - Tips: 100% FREE forever, no credit card needed
- Finnhub API key input (with hover tooltip)
- Alpha Vantage API key input (with hover tooltip)
- FMP API key input (with hover tooltip)
- Reddit API credentials: client ID, secret, user agent (with hover tooltips)
- FRED API key input (with hover tooltip)

**Data Collection Tab:**
- Alpha Vantage toggle and settings (top_n, articles_per_ticker) - **All fields include hover tooltips** explaining API usage, limits, and recommendations
- YFinance toggle and options (fundamentals, analyst ratings) - **Tooltips explain** what data is collected and why it matters
- VADER sentiment toggle - **Tooltip describes** offline sentiment analysis process
- Reddit toggle and subreddits - **Tooltips explain** social media tracking and API requirements
- Technical analysis settings (lookback days) - **Tooltips define** RSI, MACD, Bollinger Bands with financial context
- FRED toggle and indicator selection - **Tooltips explain** VIX (volatility), CPI (inflation), rates, unemployment, forex
- Congress trades toggle and lookback period - **Tooltips describe** Congressional trading data and significance
- **20+ hover tooltips total** - Comprehensive explanations for financial tracking, API tiers, and recommended values

**Paper Trading Tab:**
- Enable/disable toggle - **Tooltip encourages** 30+ days of paper trading before risking real capital
- Minimum conviction threshold - **Tooltip explains** conviction scoring (50-100 scale) and filtering
- Base position size - **Tooltip describes** conviction-weighted sizing formula (1x-2x multiplier)
- Max open positions - **Tooltip explains** capital allocation and risk management
- Hold days limit - **Tooltip defines** maximum hold period before auto-exit
- Stop loss percentage - **Tooltip explains** downside risk protection and exit triggers
- Take profit percentage - **Tooltip describes** profit target and exit strategy
- Backfill days - **Tooltip explains** historical trade backfill for performance analysis
- **9 comprehensive tooltips** - Financial context, position sizing math, risk management strategies

**Backtesting Tab:**
- Initial capital - **Tooltip explains** starting capital for simulation ($10,000 typical)
- Position size - **Tooltip describes** base position sizing and conviction weighting
- Max positions - **Tooltip explains** portfolio concentration and risk limits
- Conviction weighted toggle - **Tooltip describes** dynamic position sizing based on signal strength
- Hold days - **Tooltip defines** maximum hold period for backtest trades
- Stop loss/take profit thresholds - **Tooltips explain** exit strategy and risk/reward ratios
- Minimum conviction filter - **Tooltip describes** filtering low-quality signals from backtest
- **7 comprehensive tooltips** - Simulation parameters, capital management, strategy validation

**Thresholds Tab:**
- Velocity spike settings (mention velocity, composite score) - **Tooltips explain** social mention acceleration, 100%+ surge detection
- Insider cluster settings (min insiders, lookback days, total value) - **Tooltips describe** "smart money" tracking and minimum thresholds
- Combined signal settings - **Tooltips explain** multi-factor signal requirements and conviction bonuses
- Minimum conviction for reporting - **Tooltip describes** filtering strategy and recommended values (40-60 range)
- **7 comprehensive tooltips** - Signal detection thresholds, recommended ranges, trade-offs between sensitivity and precision

**Email Tab:**
- Enable/disable toggle - **Tooltip explains** optional email alert system for daily signals
- SMTP server and port - **Tooltip provides** common SMTP settings (Gmail: smtp.gmail.com:587)
- Sender email - **Tooltip describes** account used to send alerts
- Password (app password for Gmail) - **Tooltip includes** instructions for Gmail app password generation (2FA + app password URL)
- Recipients list - **Tooltip explains** comma-separated email list for alerts
- Test email button - **Tooltip encourages** testing before enabling automatic alerts
- **6 comprehensive tooltips** - Email setup guide, Gmail-specific instructions, security best practices

**Utilities Tab:**
- Type Safety Verification section with "Run Type Checker" button
- Bug Fix Verification section with "Verify Bug Fixes" button
- Backtesting section with configurable lookback days and "Run Backtest" button
- Runtime Validation section with "Run Runtime Tests" button
- Live output area showing results from utility scripts
- All utilities run in background threads

**Run Pipeline Tab:**
- Large "Run Pipeline" button
- Live console output display
- Auto-scrolling output
- Colored log levels (INFO, WARNING, ERROR)
- Progress indicators

### Technical Details

**GUI Framework:** ttkbootstrap (modern tkinter styling)
**Theme:** darkly (dark mode)
**File Size:** ~27 KB
**Dependencies:** ttkbootstrap, tkinter (built-in), yaml, os, subprocess
**Platform:** Cross-platform (Windows, macOS, Linux)

### Customization

The GUI can be customized by editing `gui.py`:
- Change theme: `self.root = ttkbootstrap.Window(themename="superhero")` (line 12)
- Modify window size: `self.root.geometry("1200x900")` (line 13)
- Adjust fonts: Edit font definitions in `__init__()` method
- Add new tabs: Use `ttk.Frame(self.notebook)` and `self.notebook.add()`

---

## 🔍 How It Works

### Architecture Overview

```
┌──────────────── DATA COLLECTION ────────────────┐
│                                                 │
│  Social          Insider         Prices         │
│  ↓               ↓                ↓              │
│  ApeWisdom      OpenInsider    Finnhub          │
│  Reddit         ┌────────┐     Alpha Vantage    │
│                 │        │     YFinance          │
│                 │SQLite  │     VADER             │
│                 │Database│                       │
│                 └────────┘                       │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌──────────────── ANALYSIS ───────────────────────┐
│                                                 │
│  Velocity Calculator    Technical Analyzer      │
│  • 24h mention velocity • RSI, MACD            │
│  • 7d trend            • Bollinger Bands       │
│  • Sentiment velocity  • Moving Averages       │
│  • Composite score     • Trend detection       │
│                                                 │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌──────────────── SIGNAL GENERATION ──────────────┐
│                                                 │
│  • Combine all data sources                     │
│  • Apply thresholds                             │
│  • Calculate conviction (0-100)                 │
│  • Rank by strength                             │
│                                                 │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌──────────────── REPORTING ──────────────────────┐
│                                                 │
│  HTML Dashboard         Email Alert            │
│  • Visual report        • Top signals          │
│  • Color-coded         • Watchlist             │
│  • Interactive         • Charts (optional)      │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Database Schema

**Location:** `data/sentiment.db` (SQLite)

**Tables:**
- `mentions` - Social media mention counts over time
- `insiders` - Insider trading transactions
- `prices` - Price and sentiment data from Finnhub
- `velocity` - Calculated velocity metrics
- `signals` - Generated trading signals
- `paper_trades` - Paper trading positions (entry, exit, P/L)
- `paper_trade_snapshots` - Daily price snapshots for open positions
- `macro` - Macro economic indicators (future)

### Conviction Scoring

Signals are scored 0-100:

```python
Base Score:
├─ Velocity spike:        +30
├─ Insider cluster:       +40
├─ Sentiment flip:        +20
├─ Technical breakout:    +25
├─ RSI oversold:          +15
├─ Golden cross:          +20
├─ News sentiment:        +15
└─ Reddit viral:          +10

Bonuses:
├─ Multi-factor (2+):     +15
├─ Technical score:       0-20 (based on analysis)
└─ Composite score:       0-30 (social momentum)

Total: Capped at 100
```

**Example Signal:**
```
TSLA: 87 conviction
├─ Mentions up 150% in 24h         (+30)
├─ Technical breakout detected     (+25)
├─ News bullish (0.45)             (+15)
├─ RSI oversold (28.5)             (+15)
├─ Reddit viral (25 mentions)      (+10)
├─ Multi-factor bonus              (+15)
├─ Technical score: 75             (+15)
└─ Composite: 75                   (+22)
= 147 → capped at 100
```

---

## 📊 Paper Trading System

**Validate signals before risking real capital**

The paper trading system automatically tracks mock purchases to measure real-world signal performance. This lets you build confidence in the system before using real money.

### How It Works

1. **Auto-Create Positions** - When signals are generated with conviction ≥ threshold, paper trades are automatically created
2. **Conviction-Weighted Sizing** - Position size scales with conviction (50→1x, 100→2x base size)
3. **Daily Updates** - Positions are updated with current prices each pipeline run
4. **Automatic Exits** - Positions close when stop loss, take profit, or time limit is hit
5. **Performance Tracking** - Win rate, avg return, total P/L calculated automatically
6. **Dashboard Integration** - Results displayed in HTML dashboard

### Position Sizing Formula

**Conviction-weighted sizing** (not fixed amounts):

```
conviction 50  → 1.0x base = $1,000
conviction 60  → 1.2x base = $1,200
conviction 75  → 1.5x base = $1,500
conviction 100 → 2.0x base = $2,000

Formula: multiplier = 1.0 + ((conviction - 50) / 50)
Position size = base_position_size × multiplier
Shares = position_size / entry_price
```

Higher conviction signals get larger positions, aligning risk with signal strength.

### Exit Strategies

The system supports three exit strategies (configured in `config.yaml`):

#### Conservative (Low Risk)
```yaml
paper_trading:
  hold_days: 14          # Close after 2 weeks
  stop_loss_pct: -5      # Exit if down 5%
  take_profit_pct: 10    # Exit if up 10%
```

#### Moderate (Balanced) - **DEFAULT**
```yaml
paper_trading:
  hold_days: 30          # Close after 1 month
  stop_loss_pct: -10     # Exit if down 10%
  take_profit_pct: 20    # Exit if up 20%
```

#### Aggressive (High Risk)
```yaml
paper_trading:
  hold_days: 60          # Close after 2 months
  stop_loss_pct: -15     # Exit if down 15%
  take_profit_pct: 30    # Exit if up 30%
```

### Configuration

Add this section to `config/config.yaml`:

```yaml
# Paper Trading (validate signals with mock purchases)
paper_trading:
  enabled: true              # Enable paper trading system
  min_conviction: 60         # Only trade signals with conviction ≥ 60
  position_size: 1000        # Base position size in dollars ($1000)
  max_open_positions: 10     # Maximum concurrent positions

  # Exit strategy (Moderate)
  hold_days: 30              # Auto-close after 30 days
  stop_loss_pct: -10         # Exit if down 10%
  take_profit_pct: 20        # Exit if up 20%

  # Reporting
  report_in_dashboard: true  # Include in HTML dashboard
  backfill_days: 30          # Backfill trades from last 30 days on first run
```

### Backfill Feature

The system can backfill paper trades from historical signals:

```python
# On first run, automatically creates paper trades for signals from last 30 days
# Safe to run multiple times (idempotent - skips duplicates)
```

**Example:**
- Day 1: Run pipeline → Creates paper trades for last 30 days of signals
- Day 15: Run pipeline → Creates new paper trades, updates existing ones
- Day 30: Run pipeline → Still works incrementally, no duplicates created

### Performance Metrics

The dashboard shows:

**Closed Positions:**
- Total trades closed
- Win rate (% profitable)
- Average return %
- Total profit/loss
- Best trade
- Worst trade
- Average hold time

**Open Positions:**
- Current open positions (max 10)
- Total capital deployed
- Unrealized P/L
- Days held
- Current price vs entry price

**Recent Closes:**
- Last 7 days of closed positions
- Exit reason (stop_loss, take_profit, time_limit)
- Actual returns achieved

### Database Tables

#### paper_trades
Stores all paper trading positions:
- Entry/exit dates and prices
- Share count and position size
- Stop loss and target prices
- Conviction score
- Signal types that triggered the trade
- Profit/loss and return %
- Exit reason
- Status (open/closed)

#### paper_trade_snapshots
Daily price snapshots for open positions:
- Current price
- Unrealized P/L
- Unrealized return %

### Example Output

```
Paper Trading Performance (Last 30 Days)
=========================================

Closed Positions:
  Trades:        15
  Win Rate:      66.7%
  Avg Return:    +8.3%
  Total P/L:     +$1,245
  Best Trade:    NVDA +24.5% ($367)
  Worst Trade:   TSLA -10.0% ($-158)

Open Positions:
  Count:         7
  Deployed:      $9,800
  Unrealized:    +$421 (+4.3%)

Recent Closes (Last 7 days):
  AAPL  → +12.4%  (take_profit)   +$186
  MSFT  → +20.1%  (take_profit)   +$322
  AMD   → -10.0%  (stop_loss)     -$145
```

### Best Practices

1. **Run for 30 days minimum** before evaluating performance
2. **Start with moderate settings** (default values)
3. **Adjust thresholds** based on your risk tolerance
4. **Monitor win rate** - aim for >50% with positive avg return
5. **Use higher min_conviction** (70+) for more selective trading
6. **Review exit reasons** - too many time_limits may indicate bad signals

### Interpretation Guide

| Win Rate | Avg Return | Assessment |
|----------|------------|------------|
| >60% | >5% | Excellent - consider real capital |
| 50-60% | >3% | Good - signals working |
| 40-50% | >0% | Marginal - adjust thresholds |
| <40% | Any | Poor - revise strategy |

---

## 🌍 FRED Macro Indicators

**Track economic conditions to inform trading decisions**

The FRED (Federal Reserve Economic Data) integration provides real-time macro economic indicators to assess market conditions and risk.

### Key Indicators Tracked

1. **VIX (CBOE Volatility Index)** - Market "fear gauge"
   - Low (<15): Calm market
   - Normal (15-30): Typical volatility
   - High (>30): High fear/volatility

2. **10-Year Treasury Rate** - Risk-free rate benchmark
   - Affects stock valuations
   - Rising rates can pressure equities

3. **Unemployment Rate** - Economic health indicator
   - Low (<4%): Strong economy
   - High (>7%): Recession risk

4. **Consumer Price Index (CPI)** - Inflation measure
   - Target ~2%: Healthy
   - High (>4%): Inflation concerns

5. **USD/EUR Exchange Rate** - Dollar strength indicator
   - Affects international exposure

### Market Risk Assessment

The system automatically assesses market conditions using these indicators:

**Risk Levels:**
- ✅ **LOW** (Score 0-30): Favorable conditions for aggressive trading
- ⚠️ **MEDIUM** (Score 30-60): Normal conditions - standard approach
- 🔴 **HIGH** (Score 60-100): Elevated risk - reduce positions or stay in cash

**Dashboard Integration:**
The market conditions are displayed at the top of the HTML dashboard with:
- Current risk level and score
- Key market conditions
- Warnings (if any)
- Actionable recommendations

### Configuration

```yaml
collection:
  fred:
    enabled: false           # Enable FRED macro indicators
    collect_vix: true        # Market volatility
    collect_rates: true      # Interest rates
    collect_unemployment: true  # Unemployment data
    collect_inflation: true  # CPI inflation
    collect_forex: true      # USD/EUR rate

api_keys:
  fred: "YOUR_FRED_KEY"      # Get free at https://fred.stlouisfed.org/docs/api/api_key.html
```

### Setup (2 minutes)

1. Visit: https://fred.stlouisfed.org/docs/api/api_key.html
2. Click "Request API Key"
3. Fill in your information (instant approval)
4. Copy your API key
5. Add to `config/config.yaml`:
   ```yaml
   api_keys:
     fred: "your_fred_api_key_here"

   collection:
     fred:
       enabled: true
   ```

### API Limits

- **FREE tier:** 120 requests per minute
- **Daily limit:** Effectively unlimited
- **Cost:** $0 forever

### Example Output

```
Market Conditions
=================
🟢 Market Risk: LOW (Score: 25/100)

Conditions:
  • Low volatility (calm market)
  • Low unemployment (strong economy)
  • Moderate interest rates

Recommendations:
  • Favorable conditions for aggressive trading
```

---

## 📊 Backtesting Module

**Validate your signal strategy against historical data**

The backtesting module simulates trading based on historical signals to measure real-world performance **before** risking capital.

### How It Works

1. **Load Historical Signals** - Retrieves signals from database within date range
2. **Simulate Trades** - Executes trades using actual historical prices
3. **Track Performance** - Monitors P/L, exit conditions, drawdowns
4. **Compare Benchmark** - Calculates alpha vs SPY buy-and-hold
5. **Generate Report** - Comprehensive metrics and analysis

### Key Metrics

**Trade Statistics:**
- Total trades executed
- Win rate percentage
- Average holding period
- Best/worst trades

**Performance Metrics:**
- Total return %
- Total P/L ($)
- Average return per trade
- Average win vs average loss

**Risk Metrics:**
- Maximum drawdown
- Sharpe ratio (risk-adjusted return)
- Benchmark comparison (SPY)
- Alpha (excess return)

### Running a Backtest

**Command Line Tool:**

```bash
# Backtest last 90 days
python backtest.py --days 90

# Backtest specific date range
python backtest.py --start 2024-01-01 --end 2024-12-31

# Export results to file
python backtest.py --days 180 --output backtest_results.txt
```

**Example Output:**

```
======================================================================
BACKTEST RESULTS
======================================================================
Period: 2024-01-01 to 2024-12-31
Initial Capital: $10,000.00

TRADE STATISTICS:
----------------------------------------------------------------------
  Total Trades:        45
  Winning Trades:      28 (62.2%)
  Losing Trades:       17
  Avg Hold Time:       18.5 days

PERFORMANCE METRICS:
----------------------------------------------------------------------
  Total Return:        +24.50%
  Total P/L:           +$2,450.00
  Avg Return/Trade:    +3.15%
  Avg Win:             +12.80%
  Avg Loss:            -8.40%
  Best Trade:          +45.20%
  Worst Trade:         -10.00%

RISK METRICS:
----------------------------------------------------------------------
  Max Drawdown:        -12.30%
  Sharpe Ratio:        1.85

BENCHMARK COMPARISON:
----------------------------------------------------------------------
  SPY Buy & Hold:      +18.50%
  Alpha (Excess):      +6.00%

TOP 5 WINNING TRADES:
----------------------------------------------------------------------
  1. NVDA: +45.20% ($542.40) - take_profit
  2. TSLA: +32.10% ($385.20) - take_profit
  3. AAPL: +28.90% ($346.80) - take_profit
  ...
======================================================================
✅ EXCELLENT PERFORMANCE - Strategy shows strong potential
======================================================================
```

### Configuration

```yaml
backtesting:
  initial_capital: 10000     # Starting capital ($10,000)
  position_size: 1000        # Base position size
  max_positions: 10          # Maximum concurrent positions
  conviction_weighted: true  # Use conviction-weighted sizing

  # Exit strategy
  hold_days: 30              # Maximum hold period
  stop_loss_pct: -10         # Stop loss threshold
  take_profit_pct: 20        # Take profit target

  # Filtering
  min_conviction: 60         # Only backtest signals >= 60
```

### Exit Conditions (Same as Paper Trading)

1. **Take Profit**: Exit when price hits +20% target
2. **Stop Loss**: Exit when price hits -10% stop
3. **Time Limit**: Auto-exit after 30 days

### Interpreting Results

| Win Rate | Total Return | Sharpe Ratio | Assessment |
|----------|--------------|--------------|------------|
| >60% | >15% | >1.5 | Excellent - ready for live trading |
| 50-60% | 10-15% | 1.0-1.5 | Good - strategy is profitable |
| 40-50% | 0-10% | 0.5-1.0 | Marginal - tune thresholds |
| <40% | <0% | <0.5 | Poor - major revision needed |

**Alpha Analysis:**
- **Positive Alpha**: Strategy outperforms market - good!
- **Negative Alpha**: Strategy underperforms - consider index fund instead

### Best Practices

1. **Minimum 90 days of data** for statistical significance
2. **Test multiple periods** (bull market, bear market, sideways)
3. **Match paper trading settings** for apples-to-apples comparison
4. **Iterate on thresholds** based on backtest results
5. **Consider transaction costs** (not currently modeled)

### Limitations

- Uses closing prices (no intraday data)
- No transaction costs or slippage modeled
- Assumes all orders fill at target price
- Past performance ≠ future results
- Market conditions change over time

### Integration with Paper Trading

**Recommended Workflow:**
1. **Backtest** historical data (90-180 days)
2. **Tune parameters** based on backtest results
3. **Paper trade** for 30+ days with tuned settings
4. **Compare results** - backtest vs paper trading
5. **Go live** only if both show consistent profitability

---

## 🏛️ Congress Stock Trades Tracking

**Track stock purchases and sales by US Congress members - 100% FREE, no API key needed!**

The Congress trades feature monitors financial disclosures from US Representatives and Senators to identify trading patterns and potential investment opportunities. This data is completely free and requires no API key.

### Why Track Congress Trades?

Studies have shown that Congress members' stock trades can outperform the market. This feature lets you:
- **Follow the money**: See what stocks politicians are buying/selling
- **Identify trends**: Spot patterns in Congressional trading activity
- **Gauge sentiment**: Multiple Congress members buying the same stock may signal confidence
- **Research compliance**: Track adherence to the STOCK Act (45-day disclosure requirement)

### Data Source

- **Provider**: [House Stock Watcher](https://housestockwatcher.com/api)
- **Cost**: 100% FREE (no API key required)
- **Coverage**: US House of Representatives + US Senate
- **Update Frequency**: Daily
- **Data Points**: Representative name, party, ticker, transaction type, amount range, filing date

### How It Works

1. **Daily Collection**: Automatically fetches recent Congressional trades
2. **Database Storage**: Stores all trade details with full metadata
3. **Dashboard Display**: Shows recent activity with color-coded party badges
4. **Ticker Aggregation**: Summarizes Congressional activity per stock

### Setup

Enable in `config/config.yaml`:

```yaml
collection:
  congress:
    enabled: true           # Enable Congress trades tracking
    lookback_days: 90       # Collect trades from last 90 days
```

**That's it!** No API key needed. The collector will automatically fetch data from the House Stock Watcher API.

### Usage Example

```bash
# Enable in config, then run pipeline
python main.py

# View in dashboard
open reports/dashboard_*.html
```

### Dashboard Display

The Congress trades section shows:

```
🏛️ Congress Stock Trades (Last 90 Days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Statistics:
  Total Trades: 247     Purchases: 156     Sales: 91     Members: 42

Recent Trades Table:
┌────────────┬─────────────────┬───────┬────────┬──────────┬──────────────────┬────────┐
│ Date       │ Member          │ Party │ Ticker │ Type     │ Amount           │ Owner  │
├────────────┼─────────────────┼───────┼────────┼──────────┼──────────────────┼────────┤
│ 2025-12-20 │ Nancy Pelosi    │ D     │ NVDA   │ PURCHASE │ $1,001 - $15,000 │ spouse │
│ 2025-12-19 │ Tommy Tuberville│ R     │ TSLA   │ SALE     │ $50,001 - $100K  │ self   │
│ 2025-12-18 │ Josh Gottheimer │ D     │ AAPL   │ PURCHASE │ $15,001 - $50K   │ self   │
└────────────┴─────────────────┴───────┴────────┴──────────┴──────────────────┴────────┘
```

**Visual Features:**
- 🟦 **Blue badges** for Democrats (D)
- 🟥 **Red badges** for Republicans (R)
- ⬜ **Gray badges** for Independents (I)
- 🟢 **Green** for purchases
- 🔴 **Red** for sales
- 🟡 **Yellow** for exchanges

### Database Schema

```sql
CREATE TABLE congress_trades (
    id INTEGER PRIMARY KEY,
    representative_name TEXT,
    party TEXT,
    chamber TEXT,           -- 'house' or 'senate'
    state TEXT,
    district TEXT,
    ticker TEXT,
    asset_name TEXT,
    transaction_type TEXT,  -- 'purchase', 'sale', 'exchange'
    transaction_date DATE,
    filing_date DATE,
    amount_from REAL,
    amount_to REAL,
    amount_mid REAL,       -- Midpoint for calculations
    owner TEXT,            -- 'self', 'spouse', 'dependent', 'joint'
    source TEXT,
    collected_at TIMESTAMP
);

-- Aggregate view for ticker analysis
CREATE VIEW congress_ticker_activity AS
SELECT
    ticker,
    COUNT(*) as total_trades,
    SUM(CASE WHEN transaction_type = 'purchase' THEN 1 ELSE 0 END) as buy_count,
    SUM(CASE WHEN transaction_type = 'sale' THEN 1 ELSE 0 END) as sell_count,
    COUNT(DISTINCT representative_name) as unique_members,
    MAX(transaction_date) as latest_trade_date
FROM congress_trades
GROUP BY ticker;
```

### Programmatic Access

```python
from src.database.models import Database

db = Database('data/sentiment.db')

# Get recent trades for a specific ticker
trades = db.get_recent_congress_trades(days=30, ticker='AAPL')

# Get aggregated activity for a ticker
activity = db.get_congress_ticker_activity('TSLA')
print(f"Total trades: {activity['total_trades']}")
print(f"Buys: {activity['buy_count']}, Sells: {activity['sell_count']}")
print(f"Unique members: {activity['unique_members']}")
```

### Understanding the Data

**Transaction Types:**
- **Purchase**: Member or spouse bought shares
- **Sale**: Member or spouse sold shares
- **Exchange**: Conversion or swap of assets

**Amount Ranges:**
Congress members report ranges, not exact amounts:
- $1,001 - $15,000
- $15,001 - $50,000
- $50,001 - $100,000
- $100,001 - $250,000
- $250,001 - $500,000
- $500,001 - $1,000,000
- $1,000,001 - $5,000,000
- $5,000,001 - $25,000,000
- $25,000,001 - $50,000,000
- Over $50,000,000

The system calculates `amount_mid` (midpoint) for analysis purposes.

**Owner Types:**
- **self**: Congress member's personal account
- **spouse**: Spouse's account
- **dependent**: Dependent child's account
- **joint**: Joint account

### Important Disclaimers

⚠️ **Legal Requirements**:
- Congress members must file within **45 days** of transaction
- Some trades may be reported late (filing date ≠ transaction date)
- Not all transactions require disclosure (mutual funds, diversified funds exempt)

⚠️ **Investment Considerations**:
- **Past performance ≠ future results**: Congressional trades are historical data
- **Information lag**: Trades disclosed up to 45 days after execution
- **Context matters**: Members may trade for personal reasons, not investment thesis
- **Do your own research**: Use this as one signal among many

### Best Practices

1. **Look for clusters**: Multiple members buying the same stock is more significant than one trade
2. **Check the amount**: Larger trades ($1M+) may indicate higher conviction
3. **Consider the party**: Bipartisan agreement on a stock may be noteworthy
4. **Verify the timing**: Check if trades preceded major company announcements
5. **Use as confirmation**: Combine with other signals (velocity, insider trades, technicals)

### Example Analysis Workflow

```python
# 1. Collect Congress trades
python main.py  # Runs daily collection

# 2. Analyze ticker of interest
from src.database.models import Database
db = Database('data/sentiment.db')

ticker = 'NVDA'
activity = db.get_congress_ticker_activity(ticker)

if activity and activity['buy_count'] > activity['sell_count'] * 2:
    print(f"🟢 Bullish signal: {activity['buy_count']} buys vs {activity['sell_count']} sells")
    print(f"   {activity['unique_members']} Congress members involved")

    # Get recent trades for details
    trades = db.get_recent_congress_trades(days=90, ticker=ticker)
    for trade in trades[:5]:
        print(f"   {trade['transaction_date']}: {trade['representative_name']} "
              f"({trade['party']}) - {trade['transaction_type'].upper()}")
```

### Data Quality Notes

- **Completeness**: House Stock Watcher aggregates from official sources
- **Accuracy**: Data directly from Congressional disclosure filings
- **Timeliness**: Updated daily as new filings become available
- **Coverage**: All House members; Senate coverage varies

### Resources

- **House Stock Watcher**: https://housestockwatcher.com
- **Capitol Trades**: https://www.capitoltrades.com
- **Official House Disclosures**: https://disclosures-clerk.house.gov
- **Official Senate Disclosures**: https://efdsearch.senate.gov
- **STOCK Act Info**: https://www.congress.gov/bill/112th-congress/senate-bill/2038

---

## 📖 Configuration Reference

### Full Config Example

```yaml
# API Keys
api_keys:
  # REQUIRED
  finnhub: "YOUR_FINNHUB_KEY"

  # OPTIONAL (all FREE!)
  alphavantage: "YOUR_ALPHAVANTAGE_KEY"
  fmp: "YOUR_FMP_KEY"
  reddit:
    client_id: "YOUR_CLIENT_ID"
    client_secret: "YOUR_SECRET"
    user_agent: "stock-tracker:v1.0 (by u/yourname)"

# Database
database:
  path: "data/sentiment.db"

# Collection Settings
collection:
  apewisdom:
    top_n: 100                     # Track top 100 tickers

  alphavantage:
    enabled: true
    top_n: 20                      # Analyze top 20 (save API calls)
    articles_per_ticker: 50

  yfinance:
    enabled: true
    collect_fundamentals: true
    collect_analyst_ratings: true

  vader_sentiment:
    enabled: true
    scrape_headlines: true

  reddit:
    enabled: false                 # Set true if configured
    subreddits: ["wallstreetbets", "stocks", "investing"]
    lookback_hours: 24

  technical_analysis:
    enabled: true
    lookback_days: 50

# Paper Trading (mock purchases to validate signals)
paper_trading:
  enabled: true              # Enable paper trading system
  min_conviction: 60         # Only trade signals with conviction >= 60
  position_size: 1000        # Base position size in dollars ($1000)
  max_open_positions: 10     # Maximum concurrent positions

  # Exit strategy (Moderate)
  hold_days: 30              # Auto-close after 30 days
  stop_loss_pct: -10         # Exit if down 10%
  take_profit_pct: 20        # Exit if up 20%

  # Reporting
  report_in_dashboard: true  # Include in HTML dashboard
  backfill_days: 30          # Backfill trades from last 30 days on first run

# Signal Thresholds
thresholds:
  velocity_spike:
    mention_vel_24h_min: 100       # 100%+ increase
    composite_score_min: 60

  insider_cluster:
    min_insiders: 2
    lookback_days: 14
    min_value_total: 100000        # $100k+ total

  minimum_conviction: 40           # Only report above this

# Email Settings (optional)
email:
  enabled: false
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender: "your-email@gmail.com"
  password: "your-app-password"   # Use app password for Gmail
  recipients:
    - "your-email@gmail.com"

# Report Settings
report:
  include_charts: true
  max_signals: 10
  include_watchlist: true
  watchlist_size: 20
```

---

## 🎨 Customization Guide

### Adjusting Thresholds

Edit `config/config.yaml` to make signals more or less strict:

```yaml
thresholds:
  velocity_spike:
    mention_vel_24h_min: 150  # Increase for stricter filtering
    composite_score_min: 70   # Higher score requirement

  insider_cluster:
    min_insiders: 3           # Require more insiders
    min_value_total: 200000   # Higher dollar amount

  minimum_conviction: 50      # Only report signals ≥ 50
```

### Custom Velocity Weights

Modify velocity composite score weights in `src/metrics/velocity.py`:

```python
weights = {
    'mention_24h': 0.40,   # Increase importance of 24h velocity
    'mention_7d': 0.20,    # Decrease 7d trend weight
    'sentiment': 0.30,     # Increase sentiment weight
    'divergence': 0.10     # Decrease divergence weight
}
```

### Signal Interpretation

| Conviction | Meaning | Action |
|------------|---------|--------|
| 70-100 | High | Strong buy consideration |
| 50-69 | Medium | Monitor closely |
| 40-49 | Low | Watch for confirmation |

---

## 📅 Automated Runs

### Cron (Linux/Mac)

```bash
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/Stock-Trader && python3 main.py

# Run every 4 hours
0 */4 * * * cd /path/to/Stock-Trader && python3 main.py >> logs/cron.log 2>&1
```

### Task Scheduler (Windows)

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\Stock-Trader\main.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "StockTrader"
```

---

## 🐛 Troubleshooting

### Alpha Vantage API limit reached
**Problem:** "Alpha Vantage API limit reached"
**Solution:**
- You've used your 100 calls for today
- System automatically falls back to VADER sentiment
- Wait 24 hours or reduce `top_n` in config

### VADER not available
**Problem:** "VADER sentiment not available"
**Solution:**
```bash
pip install vaderSentiment
pip list | grep vader  # Verify installation
```

### YFinance installation fails
**Problem:** Installation errors with yfinance
**Solution:**
- YFinance is optional, system works without it
- VADER provides alternative sentiment
- Try: `pip install yfinance --upgrade`

### Reddit API errors
**Problem:** "Reddit API error" or "401 Unauthorized"
**Solution:**
- Verify you created a "script" type app (not "web app")
- Check client_id and client_secret in config
- Ensure `reddit.enabled: true` in config
- Verify user_agent format: `"appname:v1.0 (by u/username)"`

### No signals generated
**Problem:** Pipeline runs but no signals
**Solution:**
- Lower `minimum_conviction` threshold
- Wait for more historical data (run for several days)
- Check logs for collector errors
- Verify thresholds aren't too strict

### No technical analysis data
**Problem:** Technical analysis shows empty
**Solution:**
- System needs historical price data
- Run pipeline a few times to build history
- Check database: `sqlite3 data/sentiment.db "SELECT COUNT(*) FROM prices;"`

### Email sending failed
**Problem:** "Email sending failed" error
**Solution:**
- For Gmail: Use app password, not regular password
  1. Enable 2-factor authentication
  2. Generate app password: https://myaccount.google.com/apppasswords
  3. Use app password in config
- Check SMTP settings in config
- Verify firewall isn't blocking port 587

### OpenInsider scraping failed
**Problem:** "OpenInsider scraping failed"
**Solution:**
- Website structure may have changed
- Check if site is accessible
- Respect rate limits (1 second delay between requests)
- Check logs for specific error

---

## 💡 Tips & Best Practices

### API Call Management

1. **Alpha Vantage (100/day)**
   - Set `top_n: 20` for top momentum tickers
   - VADER provides unlimited fallback
   - Reduce `articles_per_ticker` if hitting limits

2. **Reddit API**
   - Enable only if you have credentials
   - Monitor r/wallstreetbets for high-momentum plays
   - Combine with other signals for confirmation

3. **Technical Analysis**
   - Uses your price data (zero API calls)
   - Most reliable after ~50 days of history
   - Adjust `lookback_days` for different timeframes

### Performance

- **Run time:** 2-5 minutes (depends on # of tickers)
- **Memory:** ~100-200 MB
- **Database:** ~50 MB after 30 days
- **API rate limits:**
  - ApeWisdom: ~100 requests/day
  - OpenInsider: 1 request/URL/run (with 1s delay)
  - Finnhub: 55 requests/minute (free tier = 60/min)

### Database Maintenance

Consider pruning old data periodically:

```sql
-- Delete data older than 90 days
DELETE FROM mentions WHERE collected_at < date('now', '-90 days');
DELETE FROM prices WHERE collected_at < date('now', '-90 days');
DELETE FROM velocity WHERE calculated_at < date('now', '-90 days');

-- Vacuum to reclaim space
VACUUM;
```

---

## 🛠️ Development Tools

**Comprehensive type checking and verification utilities**

The project includes several development utilities in the `utils/` folder to ensure code quality and type safety:

### Type Verification System

**Location:** `utils/type_check.py`

A comprehensive AST-based static analyzer that checks for:
- Dict/float confusion patterns
- NoneType comparison issues
- Unsafe JSON parsing
- Missing None checks
- Dict access without defaults

**Usage:**
```bash
python utils/type_check.py
```

**Results:**
- **Files Checked**: 22 Python files
- **Lines Analyzed**: 12,000+
- **Critical Errors**: 0 (all fixed in recent commits)
- **Warnings**: 156 (mostly intentional `.get()` patterns)
- **Status**: ✅ **TYPE-SAFE** - All critical bugs fixed

### Bug Fix Verification

**Location:** `utils/verify_version.py`

Verifies that all known bug fixes are present in your codebase:
- Paper trading price extraction fixes
- Dashboard variable initialization
- Signal generator NoneType checks
- JSON parsing safety
- FRED initialization

**Usage:**
```bash
python utils/verify_version.py
```

### Backtesting CLI Tool

**Location:** `utils/backtest.py` (moved from root)

Command-line tool for running backtests on historical signals. See [Backtesting Module](#-backtesting-module) section for full documentation.

**Usage:**
```bash
python utils/backtest.py --days 90
```

### Runtime Validation

**Location:** `utils/test_runtime.py`

Runtime validation script that tests the complete pipeline with mock data (no real API calls):
- Validates all collectors work without errors
- Tests signal generation end-to-end
- Confirms dashboard generation
- No API keys required for testing

**Usage:**
```bash
python utils/test_runtime.py
```

### Type Safety Summary

All critical type-related bugs have been fixed in recent commits:
- ✅ **commit 559b366** - Paper trading update fix
- ✅ **commit 6804774** - Paper trade creation fix
- ✅ **commit 58eaa25** - Signal generator NoneType fixes
- ✅ **commit f49137e** - JSON parsing fix
- ✅ **commit 92ad916** - FRED initialization fix
- ✅ **commit 957e0ef** - Dashboard variable initialization
- ✅ **commit 828904d** - Comprehensive type verification system
- ✅ **commit 54fb785** - Dashboard slice error guards

The 156 warnings found by the type checker are mostly intentional `.get()` usage patterns where returning `None` is the desired behavior.

---

## 🧪 Test Coverage

**Comprehensive unit testing with 238 test cases**

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Congress Trades Collector | 33 | 96% | ✅ All passing |
| Backtesting Module | 32 | 94% | ✅ All passing |
| Paper Trading System | 31 | 95% | ✅ All passing |
| Technical Analysis | 30 | 87% | ✅ All passing |
| Velocity Metrics | 25 | 92% | ✅ All passing |
| FRED Macro Indicators | 24 | 93% | ✅ All passing |
| Signal Generator | - | 79% | ✅ Verified |
| Alpha Vantage Collector | 4 | 81% | ✅ All passing |
| ApeWisdom Collector | 5 | 79% | ✅ All passing |
| Finnhub Collector | 5 | 76% | ✅ All passing |
| OpenInsider Collector | 5 | 74% | ✅ All passing |
| FMP Collector | 4 | 61% | ✅ All passing |
| Velocity Calculator | 4 | 92% | ✅ All passing |
| **Total** | **238** | **50%** | **✅ 238 passing** |

### Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Specific test file
python -m pytest tests/test_technical_analyzer.py -v
python -m pytest tests/test_collectors_detailed.py -v
python -m pytest tests/test_velocity.py -v
python -m pytest tests/test_paper_trading.py -v
python -m pytest tests/test_backtester.py -v
python -m pytest tests/test_fred.py -v
python -m pytest tests/test_congress.py -v

# Run specific test class
python -m pytest tests/test_technical_analyzer.py::TestRSI -v

# Skip integration tests
pytest tests/ -v -m "not integration"
```

### Test Features

- ✅ **API mocking** - No real API calls during tests
- ✅ **Edge cases** - Empty data, timeouts, malformed responses
- ✅ **Error handling** - Network errors, invalid data
- ✅ **Rate limiting** - Verified for all collectors
- ✅ **Windows 11 compatible** - All paths and dependencies tested

---

## 🔒 Security & Privacy

- **API Keys:** Never commit `config/config.yaml` (use `.gitignore`)
- **Database:** Local SQLite - your data stays on your machine
- **Email:** Use app-specific passwords for Gmail
- **Reddit:** Read-only access, no personal data collected

---

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Not financial advice
- Do your own research (DYOR)
- Past performance ≠ future results
- Trading involves risk
- You may lose money
- Social sentiment can be manipulated
- **Always use the paper trading system first** - Build confidence with 30+ days of mock trading
- Paper trading performance ≠ real trading results (emotions, slippage, fees not modeled)
- Verify all signals independently before trading
- Consider consulting a licensed financial advisor

**Use at your own risk.**

---

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:

### Code Style
- Use Doxygen-style comments for all functions/classes
- Follow PEP 8 style guide
- Use type hints where applicable

### Testing
- Add unit tests for all major functions
- Mock external API calls in tests
- Mark integration tests with `@pytest.mark.integration`

### Development Process
1. Fork the repository
2. Create a feature branch
3. Make your changes with proper documentation
4. Add/update unit tests
5. Test thoroughly
6. Update README.md if needed
7. Submit a pull request

---

## 📜 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

**FREE Data Providers:**
- Finnhub, Alpha Vantage, Yahoo Finance, Reddit, OpenInsider, ApeWisdom, Financial Modeling Prep

**Python Libraries:**
- pandas, numpy, vaderSentiment, praw, requests, beautifulsoup4, matplotlib

---

## 📞 Support

- **Issues:** https://github.com/EE-EDK/Stock-Trader/issues
- **Discussions:** https://github.com/EE-EDK/Stock-Trader/discussions

### Helpful Resources
- **Finnhub Documentation:** https://finnhub.io/docs/api
- **Alpha Vantage Documentation:** https://www.alphavantage.co/documentation/
- **Reddit API (PRAW):** https://praw.readthedocs.io/
- **ApeWisdom:** https://apewisdom.io/
- **OpenInsider:** http://openinsider.com/

---

## 📚 Version History

### v1.3.0 (2025-12-22) - Phase 3: Congress Trades
- **Congress Stock Trades Tracking** - Monitor Congressional trading activity
  - 100% FREE data source (House Stock Watcher API, no API key needed)
  - Tracks purchases and sales by US Representatives and Senators
  - Complete metadata: representative name, party, ticker, amount range, filing date
  - Database schema with congress_trades table and aggregate view
  - Dashboard integration with color-coded party badges (D/R/I)
  - Visual trade type highlighting (purchases=green, sales=red)
  - Configurable lookback period (default 90 days)
  - Programmatic access via Database methods
  - 33 comprehensive unit tests with 96% coverage
- Updated dashboard footer to include all 11 FREE data sources
- Total test coverage: 238 tests (50% code coverage)
- Complete documentation with usage examples and disclaimers
- Database additions: congress_trades table, congress_ticker_activity view

### v1.2.0 (2025-12-21) - Phase 2 Complete
- **Backtesting Module** - Complete historical validation system
  - Simulates trades using actual historical prices
  - Comprehensive metrics (win rate, total return, Sharpe ratio, max drawdown)
  - Benchmark comparison vs SPY buy-and-hold
  - Alpha calculation (excess return)
  - CLI tool for easy backtesting (backtest.py)
  - 32 comprehensive unit tests with 94% coverage
- **FRED Macro Indicators** - Economic data integration
  - 5 key indicators: VIX, 10Y Treasury, Unemployment, CPI, USD/EUR
  - Automated market risk assessment (LOW/MEDIUM/HIGH)
  - Dashboard integration with color-coded warnings
  - 120 API calls/minute (FREE tier)
  - 24 unit tests with 93% coverage
- **Enhanced Dashboard** - Market conditions and risk assessment
  - FRED macro indicators section at top
  - Color-coded risk levels and recommendations
  - Individual indicator cards with current values
- Database schema additions (macro_indicators, market_assessments)
- Total test coverage increased to 50% (200+ tests)
- Complete documentation for all Phase 2 features

### v1.1.0 (2025-12-21)
- **Paper Trading System** - Complete mock trading implementation
  - Conviction-weighted position sizing (1x-2x base)
  - Automatic position creation from signals
  - Daily price updates and P/L tracking
  - Multiple exit strategies (stop loss, take profit, time limit)
  - Idempotent backfill from historical signals (30 days)
  - Performance metrics (win rate, avg return, total P/L)
  - Dashboard integration with visual reports
  - 28 comprehensive unit tests
- Database schema additions (paper_trades, paper_trade_snapshots)
- Updated documentation with paper trading guide
- Total test coverage increased to 45% (150+ tests)

### v1.0.0 (2025-12-18)
- Initial release
- Core pipeline implementation
- ApeWisdom, OpenInsider, Finnhub collectors
- Alpha Vantage, YFinance, VADER, Reddit, FMP integration
- Technical analysis engine (RSI, MACD, Bollinger Bands)
- Velocity metrics calculator
- Signal generator with multi-factor scoring (8 signal types)
- HTML dashboard generator
- Email reporter
- 122 unit tests with 40% coverage
- Full documentation

---

## 🗺️ Roadmap

### Phase 2 - ✅ COMPLETE (v1.2.0)
- [x] **Paper trading system** - ✅ Complete (v1.1.0)
- [x] **FRED macro indicators** - ✅ Complete (v1.2.0)
- [x] **Backtesting module** - ✅ Complete (v1.2.0)
- [x] **Enhanced dashboard** - ✅ Complete (v1.2.0)

### Phase 3 - 🚧 IN PROGRESS
- [x] **Congress trades tracking** - ✅ Complete (v1.3.0) - 100% FREE, no API key!
- [ ] Options flow data (Unusual Whales/Cheddar Flow) - Requires paid subscription
- [ ] Web dashboard (Flask/FastAPI)
- [ ] Discord/Telegram bot for notifications

### Phase 4 (Long-term)
- [ ] Machine learning for signal optimization
- [ ] Multi-timeframe analysis
- [ ] Correlation with market regime
- [ ] Real broker API integration

---

<div align="center">

**Built with ❤️ by the community**

**100% FREE • Zero Recurring Costs • Forever**

[⭐ Star this repo](https://github.com/EE-EDK/Stock-Trader) • [🐛 Report Bug](https://github.com/EE-EDK/Stock-Trader/issues) • [💡 Request Feature](https://github.com/EE-EDK/Stock-Trader/issues)

</div>
