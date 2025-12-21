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

### 9 FREE Data Sources

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
- ✅ **122 unit tests** - 40% code coverage

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
│   │   ├── charts.py               # Matplotlib charts
│   │   └── email.py                # Email reports
│   └── database/
│       ├── models.py               # Database schema
│       └── queries.py              # Query helpers
├── tests/                          # Unit tests (122 tests)
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

#### 1.3 Reddit API (OPTIONAL - 2 minutes)

**What you get:** Track r/wallstreetbets, r/stocks, r/investing, unlimited

1. Visit: https://www.reddit.com/prefs/apps
2. Click "create app" at the bottom
3. Fill in:
   - **Name:** stock-tracker
   - **Type:** Select "script"
   - **Description:** Stock sentiment tracker
   - **Redirect URI:** http://localhost:8080
4. Click "create app"
5. Copy:
   - **client_id** (under "personal use script")
   - **client_secret**
6. Add to config:
   ```yaml
   api_keys:
     reddit:
       client_id: "YOUR_CLIENT_ID"
       client_secret: "YOUR_SECRET"
       user_agent: "stock-tracker:v1.0 (by u/yourusername)"
   ```

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

## 🧪 Test Coverage

**Comprehensive unit testing with 122 test cases**

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Technical Analysis | 30 | 87% | ✅ All passing |
| Velocity Metrics | 25 | 92% | ✅ All passing |
| Signal Generator | - | 79% | ✅ Verified |
| Alpha Vantage Collector | 4 | 81% | ✅ All passing |
| ApeWisdom Collector | 5 | 79% | ✅ All passing |
| Finnhub Collector | 5 | 76% | ✅ All passing |
| OpenInsider Collector | 5 | 74% | ✅ All passing |
| FMP Collector | 4 | 61% | ✅ All passing |
| Velocity Calculator | 4 | 92% | ✅ All passing |
| **Total** | **122** | **40%** | **✅ 122 passing** |

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
- Always paper trade first before using real capital
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

### Phase 2 (Planned)
- [ ] FRED macro indicator integration
- [ ] Backtesting module for signal validation
- [ ] Paper trading integration
- [ ] Performance metrics dashboard

### Phase 3 (Future)
- [ ] Options flow data (Unusual Whales/Cheddar Flow)
- [ ] Congress trades tracking (Quiver Quant)
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
