# 🚀 Complete Setup Guide - FREE Data Sources Integration

This guide will help you set up all the FREE data sources to supercharge your stock trading system with ZERO ongoing costs!

## 📊 What You're Getting (All FREE!)

| Feature | Source | API Calls | Cost | Setup Time |
|---------|--------|-----------|------|------------|
| Price Data | Finnhub | 200+/day | FREE | ✅ Done |
| News Sentiment | Alpha Vantage | 100/day | FREE | 2 mins |
| Technical Analysis | Your own data | Unlimited | FREE | 0 mins |
| Stock Fundamentals | Yahoo Finance | Unlimited | FREE | 0 mins |
| Local Sentiment | VADER | Unlimited | FREE | 0 mins |
| Reddit Data | PRAW | ~100/min | FREE | 2 mins |
| Alternative Data | FMP | 250/day | FREE | 2 mins |

**Total Setup Time: ~10 minutes**
**Total Cost: $0 forever**

---

## 🛠️ Installation

### Step 1: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

This installs:
- `yfinance` - Yahoo Finance data (unlimited, free!)
- `vaderSentiment` - Local sentiment analysis (no API required)
- `praw` - Reddit API wrapper (free API key required)

### Step 2: Get Your FREE API Keys

#### 2.1 Alpha Vantage (100 calls/day - instant approval)

1. Visit: https://www.alphavantage.co/support/#api-key
2. Enter your email
3. Get instant API key (no credit card!)
4. Copy your key

**What you get:**
- News sentiment analysis for stocks
- Market movers (gainers/losers)
- 100 API calls per day

#### 2.2 Financial Modeling Prep - Optional (250 calls/day)

1. Visit: https://site.financialmoderingprep.com/developer/docs/pricing
2. Sign up for FREE tier
3. Get your API key

**What you get:**
- Earnings calendar
- Analyst estimates
- SEC filings
- Price targets
- 250 API calls per day

#### 2.3 Reddit API - Optional (unlimited within rate limits)

1. Visit: https://www.reddit.com/prefs/apps
2. Click "create app" at the bottom
3. Fill in:
   - **Name:** stock-tracker
   - **Type:** script
   - **Description:** Stock sentiment tracker
   - **Redirect URI:** http://localhost:8080
4. Click "create app"
5. Copy:
   - **client_id** (under "personal use script")
   - **client_secret**

**What you get:**
- Track mentions from r/wallstreetbets, r/stocks, r/investing
- Sentiment analysis of Reddit discussions
- Unlimited access (free)

### Step 3: Configure Your System

```bash
# Copy the example config
cp config/config.example.yaml config/config.yaml

# Edit with your API keys
nano config/config.yaml  # or use your favorite editor
```

Update these sections:

```yaml
api_keys:
  finnhub: "YOUR_FINNHUB_KEY"                # You already have this
  alphavantage: "YOUR_ALPHAVANTAGE_KEY"      # Add your new key here
  fmp: "YOUR_FMP_KEY"                        # Optional - add if you got one

  # Reddit API (optional but recommended)
  reddit:
    client_id: "YOUR_REDDIT_CLIENT_ID"
    client_secret: "YOUR_REDDIT_SECRET"
    user_agent: "stock-tracker:v1.0 (by u/yourusername)"

# Enable FREE data sources
collection:
  alphavantage:
    enabled: true           # Enable Alpha Vantage sentiment
    top_n: 20               # Analyze top 20 tickers to save API calls
    articles_per_ticker: 50

  yfinance:
    enabled: true           # Enable Yahoo Finance (no key needed!)
    collect_fundamentals: true
    collect_analyst_ratings: true

  vader_sentiment:
    enabled: true           # Enable local VADER sentiment (no API!)
    scrape_headlines: true

  reddit:
    enabled: true           # Set to true if you have Reddit credentials
    subreddits: ["wallstreetbets", "stocks", "investing"]
    lookback_hours: 24

  technical_analysis:
    enabled: true           # Enable technical analysis (no API!)
    lookback_days: 50
```

---

## 🏃 Run Your Enhanced System

```bash
# Run the complete pipeline
python main.py

# Skip email report (just generate dashboard)
python main.py --skip-email

# Use debug logging
python main.py --log-level DEBUG
```

---

## 📈 What Happens Now?

Your system will now:

1. **Collect Traditional Data**
   - Social mentions from ApeWisdom
   - Insider trades from OpenInsider
   - Price data from Finnhub

2. **NEW: Collect FREE Data**
   - ✅ News sentiment from Alpha Vantage (100 tickers/day)
   - ✅ Stock fundamentals from Yahoo Finance (unlimited!)
   - ✅ Local sentiment from VADER (unlimited!)
   - ✅ Reddit mentions (if configured)
   - ✅ Technical indicators (RSI, MACD, Bollinger Bands, etc.)

3. **Generate Enhanced Signals**
   - Velocity spikes (social momentum)
   - Insider clusters (smart money)
   - **NEW: Technical breakouts**
   - **NEW: RSI oversold signals**
   - **NEW: Golden crosses**
   - **NEW: News sentiment shifts**
   - **NEW: Reddit viral signals**

4. **Create Beautiful Dashboard**
   - Open `reports/dashboard_YYYYMMDD_HHMMSS.html` in your browser
   - See all signals with conviction scores
   - View technical analysis, sentiment, and Reddit data
   - 100% local, no external dependencies

---

## 🎯 Example Output

```
========== Pipeline Run ==========
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
  [OK] Dashboard saved to: reports/dashboard_20241219_143052.html
  [TIP] Open reports/dashboard_20241219_143052.html in your browser!

========== Summary ==========
- Top signal: TSLA (conviction: 87)
  • TSLA: 87 - Mentions up 150% in 24h | Technical breakout detected | News bullish (0.45) | RSI oversold (28.5) | Reddit viral (25 mentions)
```

---

## 🔍 Understanding New Signal Types

### Technical Breakout
- Stock price breaks above resistance
- High volume surge (1.5x average)
- Price above Bollinger Band upper limit
- **Conviction: +25 points**

### RSI Oversold
- RSI < 30 (oversold territory)
- Potential bounce opportunity
- **Conviction: +15 points**

### Golden Cross
- SMA 20 crosses above SMA 50
- Bullish trend indicator
- **Conviction: +20 points**

### News Sentiment Bullish
- Alpha Vantage or VADER sentiment > 0.15
- Positive news coverage
- **Conviction: +15 points**

### Reddit Viral
- 10+ mentions in 24 hours
- Social momentum building
- **Conviction: +10 points**

---

## 📊 View Your Dashboard

After running the pipeline:

1. Find the latest HTML file: `reports/dashboard_YYYYMMDD_HHMMSS.html`
2. Open in any browser (Chrome, Firefox, Safari, Edge)
3. View:
   - Total signals and conviction scores
   - Technical analysis (RSI, trend, score)
   - News sentiment breakdown
   - Reddit mention counts
   - All trigger types with color coding

---

## 💡 Tips for Maximizing FREE Data

### Save Alpha Vantage API Calls
- Configure `top_n: 20` to analyze only top momentum tickers
- Reduce `articles_per_ticker` if you hit limits
- Use VADER as backup for unlimited local sentiment

### Avoid Getting Blocked (Web Scraping)
- VADER scrapes Google News + Yahoo Finance
- System auto-limits to 10 tickers to avoid blocks
- Headlines are analyzed locally (no external API)

### Reddit Best Practices
- Enable only if you have credentials
- Monitor r/wallstreetbets for high-momentum plays
- Combine with other signals for confirmation

### Technical Analysis
- Uses your existing price data (zero API calls!)
- Analyzes last 50 days by default
- Adjust `lookback_days` in config for different timeframes

---

## 🐛 Troubleshooting

### "Alpha Vantage API limit reached"
- You've used your 100 calls for today
- System automatically falls back to VADER sentiment
- Wait 24 hours or reduce `top_n` in config

### "VADER sentiment not available"
- Run: `pip install vaderSentiment`
- Check: `pip list | grep vader`

### "YFinance not available"
- Run: `pip install yfinance`
- Some tickers may have limited data

### "Reddit API error"
- Check your client_id and client_secret
- Verify user_agent format
- Make sure you created a "script" type app

### No technical analysis data
- System needs historical price data
- Run pipeline a few times to build history
- Check: `sqlite3 data/sentiment.db "SELECT COUNT(*) FROM prices;"`

---

## 🎉 You're All Set!

You now have a complete stock trading system powered by:
- ✅ 6 different data sources
- ✅ 100% free data (no recurring costs)
- ✅ Advanced technical analysis
- ✅ Multi-source sentiment
- ✅ Social momentum tracking
- ✅ Beautiful HTML dashboards

**Next Steps:**
1. Run the pipeline: `python main.py`
2. Open the generated dashboard in your browser
3. Review the signals and conviction scores
4. Set up a cron job to run daily:
   ```bash
   0 9 * * * cd /path/to/Stock-Trader && python main.py
   ```

Happy trading! 🚀📈
