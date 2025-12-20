# 📈 Stock Trading Signals System

> **Comprehensive stock trading signals powered entirely by FREE data sources**
>
> Combines social momentum, insider trading, technical analysis, and news sentiment to generate high-conviction trading signals. **100% free APIs** - zero recurring costs forever.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FREE APIs](https://img.shields.io/badge/APIs-100%25%20FREE-brightgreen.svg)](https://github.com)

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
# Edit config/config.yaml with your keys

# 4. Run
python main.py

# 5. View results
firefox reports/dashboard_*.html
```

---

## 📊 What You Get

### 9 FREE Data Sources

| Source | Data | API Calls/Day | Cost |
|--------|------|---------------|------|
| **Finnhub** | Stock prices | 200+ | FREE |
| **Alpha Vantage** | News sentiment | 100 | FREE |
| **Yahoo Finance** | Fundamentals, ratios | Unlimited | FREE |
| **VADER** | Local sentiment | Unlimited | FREE |
| **Reddit (PRAW)** | Social mentions | ~100/min | FREE |
| **OpenInsider** | Insider trades | Unlimited | FREE |
| **ApeWisdom** | Reddit stock mentions | Unlimited | FREE |
| **FMP** | Earnings, estimates | 250 | FREE |
| **Technical** | RSI, MACD, Bollinger | Unlimited | FREE |

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

- ✅ **Multi-source analysis** - Combines 9 different data sources
- ✅ **Conviction scoring** - Ranks signals 0-100 based on strength
- ✅ **HTML dashboards** - Beautiful visual reports
- ✅ **Email alerts** - Optional email notifications
- ✅ **Technical analysis** - Professional-grade indicators
- ✅ **Sentiment analysis** - News + social media
- ✅ **Insider tracking** - Follow the smart money
- ✅ **100% FREE** - Zero recurring costs
- ✅ **Local database** - Your data stays on your machine
- ✅ **Automated** - Set and forget with cron

---

## 📁 Project Structure

```
Stock-Trader/
├── main.py                          # Main pipeline orchestrator
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
│   │   └── openinsider.py          # Insider trades
│   ├── metrics/
│   │   ├── velocity.py             # Social momentum
│   │   └── technical.py            # Technical indicators
│   ├── signals/
│   │   └── generator.py            # Signal generation
│   ├── reporters/
│   │   ├── dashboard.py            # HTML dashboard
│   │   └── email.py                # Email reports
│   └── database/
│       └── models.py               # Database models
├── reports/                         # Generated dashboards
├── logs/                           # Application logs
├── data/                           # SQLite database
├── requirements.txt                # Dependencies
├── SETUP_GUIDE.md                  # Detailed setup
└── README.md                       # This file
```

---

## 🔧 Setup Guide

### 1. Get Your FREE API Keys

**Required (2 minutes):**

**Finnhub** (FREE tier: 60 calls/min)
1. Visit: https://finnhub.io/register
2. Sign up with email
3. Copy your API key
4. Add to `config/config.yaml`:
   ```yaml
   api_keys:
     finnhub: "YOUR_KEY_HERE"
   ```

**Recommended (5 minutes total):**

**Alpha Vantage** (FREE: 100 calls/day)
1. Visit: https://www.alphavantage.co/support/#api-key
2. Enter email → Get instant key
3. Add to config:
   ```yaml
   api_keys:
     alphavantage: "YOUR_KEY_HERE"
   ```

**Reddit API** (FREE: unlimited within rate limits)
1. Visit: https://www.reddit.com/prefs/apps
2. Click "create app"
3. Fill in:
   - Name: `stock-tracker`
   - Type: Select "script"
   - Redirect URI: `http://localhost:8080`
4. Copy `client_id` and `client_secret`
5. Add to config:
   ```yaml
   api_keys:
     reddit:
       client_id: "YOUR_CLIENT_ID"
       client_secret: "YOUR_SECRET"
       user_agent: "stock-tracker:v1.0 (by u/yourname)"
   ```

**Optional:**

**Financial Modeling Prep** (FREE: 250 calls/day)
- Visit: https://site.financialmodelingprep.com/developer/docs/pricing
- Sign up for free tier
- Add key to config

### 2. Configure

```bash
cp config/config.example.yaml config/config.yaml
nano config/config.yaml  # or your favorite editor
```

Minimal configuration:
```yaml
api_keys:
  finnhub: "your_finnhub_key"
  alphavantage: "your_alpha_key"  # Optional but recommended

collection:
  alphavantage:
    enabled: true
    top_n: 20                      # Analyze top 20 to save API calls

  yfinance:
    enabled: true                  # No API key needed

  vader_sentiment:
    enabled: true                  # Offline analysis

  reddit:
    enabled: false                 # Set true if you have credentials

  technical_analysis:
    enabled: true                  # Uses your price data
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Core: `requests`, `beautifulsoup4`, `pyyaml`, `numpy`, `pandas`
- FREE data: `vaderSentiment`, `praw`
- Visualization: `matplotlib`

### 4. Run

```bash
python main.py
```

Output:
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

### 5. View Dashboard

```bash
# Open the HTML dashboard in your browser
firefox reports/dashboard_*.html
# or
open reports/dashboard_*.html  # Mac
```

---

## 🔍 How It Works

### Pipeline Flow

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
  password: "your-app-password"
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

## 🎨 Dashboard Features

The HTML dashboard shows:

- **Signal Cards** - Color-coded by conviction
- **Trigger Badges** - Visual indicators for each signal type
- **Technical Breakdown** - RSI, trend, technical score
- **Sentiment Analysis** - News sentiment with scores
- **Reddit Data** - Mention counts and viral status
- **Responsive Design** - Works on desktop and mobile

---

## 🐛 Troubleshooting

### Alpha Vantage API limit reached
**Solution:** Wait 24 hours or reduce `top_n` in config. System automatically falls back to VADER.

### VADER not available
**Solution:** `pip install vaderSentiment`

### Reddit API errors
**Solution:** 
- Verify you created a "script" type app
- Check credentials in config
- Ensure `reddit.enabled: true`

### No signals generated
**Solution:**
- Lower `minimum_conviction` threshold
- Wait for more historical data
- Check logs for collector errors

### YFinance installation fails
**Solution:** YFinance is optional. System works without it. VADER provides alternative sentiment.

---

## 🔒 Security & Privacy

- **API Keys**: Never commit `config/config.yaml`
- **Database**: Local SQLite - your data stays on your machine
- **Email**: Use app-specific passwords
- **Reddit**: Read-only access, no personal data

---

## 📅 Automated Runs

### Cron (Linux/Mac)

```bash
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/Stock-Trader && python3 main.py
```

### Task Scheduler (Windows)

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\Stock-Trader\main.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "StockTrader"
```

---

## 💡 Tips & Best Practices

### API Call Management

1. **Alpha Vantage (100/day)**
   - Set `top_n: 20` for top momentum tickers
   - VADER provides unlimited fallback

2. **Reddit API**
   - Enable only if you have credentials
   - Combine with other signals

3. **Technical Analysis**
   - Uses your price data (zero API calls)
   - Most reliable after ~50 days of history

### Signal Interpretation

| Conviction | Meaning | Action |
|------------|---------|--------|
| 70-100 | High | Strong buy consideration |
| 50-69 | Medium | Monitor closely |
| 40-49 | Low | Watch for confirmation |

### Performance

- **Run time**: 2-5 minutes
- **Memory**: ~100-200 MB
- **Database**: ~50 MB after 30 days

---

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Not financial advice
- Do your own research (DYOR)
- Past performance ≠ future results
- Trading involves risk
- You may lose money

**Use at your own risk.**

---

## 📜 License

MIT License - See LICENSE file

---

## 🤝 Contributing

Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📞 Support

- **Setup Guide**: See `SETUP_GUIDE.md` for detailed instructions
- **Issues**: https://github.com/EE-EDK/Stock-Trader/issues
- **Discussions**: https://github.com/EE-EDK/Stock-Trader/discussions

---

## 🙏 Acknowledgments

**FREE Data Providers:**
- Finnhub, Alpha Vantage, Yahoo Finance, Reddit, OpenInsider, ApeWisdom

**Python Libraries:**
- pandas, numpy, vaderSentiment, praw, requests, beautifulsoup4

---

<div align="center">

**Built with ❤️ by the community**

**100% FREE • Zero Recurring Costs • Forever**

[⭐ Star this repo](https://github.com/EE-EDK/Stock-Trader) • [🐛 Report Bug](https://github.com/EE-EDK/Stock-Trader/issues) • [💡 Request Feature](https://github.com/EE-EDK/Stock-Trader/issues)

</div>
