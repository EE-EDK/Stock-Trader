# Data Pipeline Diagnostic Report
**Generated:** 2026-01-04
**Pipeline Run:** 2026-01-03 19:46:34

---

## Executive Summary

Based on your pipeline output, several data sources are returning **zero or limited data**. This diagnostic identifies whether data is:
- ❌ **Not available** from the source
- ⚠️ **Being filtered out** by collection logic
- 🔧 **Not forwarding correctly** through the pipeline

---

## Issues Identified

### 🔴 CRITICAL ISSUES

#### 1. VADER Sentiment: 0 Headlines Scraped (All Tickers)
**Status:** Web scraping selectors are likely outdated

**Evidence from logs:**
```
2026-01-03 19:50:44,596 - src.collectors.vader_sentiment - INFO - Scraped 0 headlines for AAPL
2026-01-03 19:50:45,399 - src.collectors.vader_sentiment - INFO - Scraped 0 headlines from Yahoo Finance for AAPL
2026-01-03 19:50:45,400 - src.collectors.vader_sentiment - WARNING - No headlines found for AAPL
```

**Root Cause:**
Web scraping depends on specific HTML class names:
- **Google News:** Looking for class `gPFEn` (line 109 in vader_sentiment.py:109)
- **Yahoo Finance:** Looking for class `Mb(5px)` (line 140 in vader_sentiment.py:140)

These class names change frequently when websites update their design.

**Impact:**
- VADER sentiment is NOT contributing to signal generation
- Missing 15-20 points of conviction score for news sentiment
- No local sentiment analysis available

**Fix Options:**
1. **Update selectors** - Inspect current HTML and update class names
2. **Switch to API-based** - Use Alpha Vantage (already working with 20 tickers)
3. **Disable VADER** - Set `vader_sentiment.enabled: false` in config to reduce noise

---

#### 2. OpenInsider: 0 Trades Collected
**Status:** Either no cluster buys available OR web scraping issue

**Evidence from logs:**
```
2026-01-03 19:46:35,931 - src.collectors.openinsider - INFO - Successfully scraped 0 insider trades
2026-01-03 19:46:37,100 - src.collectors.openinsider - INFO - Successfully scraped 0 insider trades
```

**Root Cause (Possible):**
- Website structure changed (looking for `class='tinytable'` at openinsider.py:88)
- OR legitimately no cluster buys/CEO-CFO purchases available today

**Impact:**
- No insider trading signals (40 points of conviction score)
- Missing a key alpha source

**How to Verify:**
1. Manually visit http://openinsider.com/latest-cluster-buys
2. Check if there are any trades listed
3. If yes → scraping issue; if no → data not available

**Fix:**
- Run the diagnostic script: `python debug_collectors.py`
- Update table selector if HTML changed

---

### ⚠️ MODERATE ISSUES

#### 3. Congress Trades: 403 Forbidden
**Status:** Data source access denied

**Evidence from logs:**
```
2026-01-03 19:53:42,509 - src.collectors.congress - ERROR - Failed to collect House trades: 403 Client Error: Forbidden for url: https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json
```

**Root Cause:**
The S3 bucket has restricted access or been moved.

**Impact:**
- Missing congressional trading data
- This is supplementary data, not critical for core signals

**Fix:**
- Check https://housestockwatcher.com for new API endpoint
- Or disable in config: `congress.enabled: false`

---

#### 4. FRED: Missing UNEMPLOYMENT and INFLATION Data
**Status:** Lookback period too short for monthly indicators

**Evidence from logs:**
```
2026-01-03 19:49:49,682 - src.collectors.fred - WARNING - No observations found for UNRATE
2026-01-03 19:49:49,784 - src.collectors.fred - WARNING - No observations found for CPIAUCSL
```

**Root Cause:**
Code searches last **30 days** for data (fred.py:116), but:
- **UNRATE** (unemployment) is published **monthly**
- **CPIAUCSL** (CPI) is published **monthly**

If the indicator hasn't been updated in the last 30 days, it won't be found.

**Impact:**
- Market risk assessment missing unemployment and inflation factors
- Still getting VIX, Treasury rates, and USD/EUR (working correctly)
- Risk score calculated with limited data

**Fix:**
Increase lookback period for monthly indicators in fred.py:105:
```python
# Current
def get_latest_observation(self, series_id: str, days_back: int = 30)

# Change to
def get_latest_observation(self, series_id: str, days_back: int = 60)
```

Or make it indicator-specific:
```python
# In collect_all_indicators(), customize per indicator:
if indicator_name in ['UNEMPLOYMENT', 'INFLATION']:
    observation = self.get_latest_observation(series_id, days_back=60)
else:
    observation = self.get_latest_observation(series_id, days_back=30)
```

---

### ✅ WORKING CORRECTLY

#### 5. Limited Data Sources Working Well
- ✓ **ApeWisdom:** 100 mentions collected
- ✓ **Finnhub:** 209 price data points (sentiment skipped, requires paid plan)
- ✓ **YFinance:** 208/209 stock info (1 failure due to 503 error on VOO)
- ✓ **Alpha Vantage:** 20 sentiment analyses (FREE tier, working)
- ✓ **FRED:** 3/5 indicators (VIX, Treasury, USD/EUR working)

---

## Data Flow Analysis

### Pipeline Flow
```
┌─────────────────┐
│  Data Sources   │
└────────┬────────┘
         │
         │  Collectors gather raw data
         ▼
┌─────────────────┐
│    Database     │ ← Mentions: 100 ✓
│   (sentiment.db)│ ← Prices: 209 ✓
└────────┬────────┘ ← Insiders: 0 ✗
         │         ← Sentiment: 20 ✓
         │
         │  Velocity calculator processes mentions
         ▼
┌─────────────────┐
│ Velocity Metrics│ ← 89 tickers with velocity ✓
└────────┬────────┘
         │
         │  Signal generator evaluates conditions
         ▼
┌─────────────────┐
│     Signals     │ ← 1 signal generated
└────────┬────────┘   0 above conviction threshold ✗
         │
         ▼
     Reports
```

### Why Only 1 Signal Generated (0 High Conviction)?

Looking at your output:
```
2026-01-03 19:53:42,579 - src.signals.generator - INFO - Generated 1 signals from 89 tickers
2026-01-03 19:53:42,590 - src.signals.generator - INFO - Filtered 0/1 signals above 70 conviction
```

**Signal Generation Logic** (from signals/generator.py):
- **Velocity spike:** +30 points
- **Insider cluster:** +40 points
- **Sentiment flip:** +20 points
- **Technical breakout:** +25 points
- **RSI oversold:** +15 points
- **Golden cross:** +20 points
- **News sentiment:** +15 points
- **Reddit viral:** +10 points
- **Combined signals (2+):** +15 bonus
- **Technical score:** +0-20 points

**Default conviction threshold:** 70 points (main.py uses this for paper trading)

**Problem:**
- **No insider data** (0 trades) → Missing 40 points
- **No VADER sentiment** (0 headlines) → Missing 15 points
- Limited technical signals → Missing 15-25 points

**Result:**
Even with velocity spike (30) + technical breakout (25) + news sentiment (15) = **70 points** (barely threshold)

Most tickers only have 1-2 triggers, resulting in **30-50 point conviction** → filtered out

---

## Recommendations

### Immediate Actions

1. **Run Diagnostic Script**
   ```bash
   python debug_collectors.py
   ```
   This will test each collector and show exactly what's failing.

2. **Fix FRED Monthly Indicators**
   - Increase lookback to 60 days for UNRATE and CPIAUCSL
   - This is an easy fix with high value

3. **Verify OpenInsider Manually**
   - Visit the site to check if data exists
   - If exists, update scraping selectors
   - If not, this is expected (no cluster buys today)

4. **Disable or Fix VADER**
   - If you need free sentiment: Fix the web scraping selectors
   - If you have Alpha Vantage: Disable VADER, use Alpha Vantage instead
   - Set `vader_sentiment.enabled: false` in config/config.yaml

5. **Congress Trades**
   - Check https://housestockwatcher.com for API updates
   - Or disable: `congress.enabled: false`

### Medium-Term Improvements

6. **Lower Conviction Threshold (Temporary)**
   - If you want to see more signals while fixing collectors:
   - In main.py, change the filter from 70 to 50:
   ```python
   # Line ~425 in main.py
   high_conviction_signals = signal_gen.filter_signals(signals, min_conviction=50)
   ```

7. **Add More Alpha Vantage Coverage**
   - Currently only analyzing 20 tickers
   - Free tier allows 25 requests/day
   - Increase to use full quota:
   ```yaml
   alphavantage:
     enabled: true
     articles_per_ticker: 50
     max_tickers: 25  # Use full free tier
   ```

8. **Monitor Data Sources**
   - Web scraping is fragile (sites change)
   - Consider switching to API-based sources where possible
   - Alpha Vantage is working well (API-based)

---

## Data Availability vs Filtering Summary

| Data Source | Status | Issue Type | Impact |
|------------|--------|------------|--------|
| ApeWisdom | ✅ Working | None | 100 mentions |
| OpenInsider | ❌ Zero data | Unknown (scraping or availability) | Missing 40 conviction pts |
| Finnhub Prices | ✅ Working | None | 209 prices |
| Finnhub Sentiment | ⚠️ Skipped | Requires paid plan | N/A |
| YFinance | ✅ Mostly working | 1 ticker failed (503) | 208/209 tickers |
| VADER | ❌ Zero data | Scraping selectors outdated | Missing 15 conviction pts |
| Alpha Vantage | ✅ Working | None | 20 sentiment analyses |
| FRED VIX | ✅ Working | None | Market volatility tracked |
| FRED Treasury | ✅ Working | None | Rates tracked |
| FRED Unemployment | ❌ Zero data | Lookback too short | Market risk incomplete |
| FRED Inflation | ❌ Zero data | Lookback too short | Market risk incomplete |
| FRED USD/EUR | ✅ Working | None | Currency tracked |
| Congress | ❌ 403 Error | Data source access | Supplementary only |

---

## Next Steps

1. ✅ **Run:** `python debug_collectors.py` to see detailed test results
2. ⚙️ **Fix:** FRED lookback period (easy, high impact)
3. 🔍 **Investigate:** OpenInsider (manual check + scraping test)
4. 🎯 **Decide:** Keep or disable VADER sentiment
5. 📊 **Consider:** Lowering conviction threshold temporarily to see signals

---

## Questions to Ask Yourself

1. **Is this a market timing issue?**
   - Maybe there genuinely are no cluster buys today
   - Maybe no tickers meet high conviction criteria
   - This could be normal on a quiet trading day

2. **Do you need all data sources?**
   - Some sources provide overlapping data
   - Alpha Vantage sentiment works, VADER doesn't → disable VADER
   - Congress trades are supplementary → can disable

3. **What's your conviction threshold?**
   - 70 is conservative (good for paper trading)
   - 50-60 might give you more signals to evaluate
   - Adjust based on your risk tolerance

4. **Are you expecting signals every day?**
   - High-quality setups may be rare
   - 0-1 signals/day could be normal for a selective strategy

---

## Contact & Support

If you need help:
- Check the logs in `logs/pipeline.log` for detailed errors
- Run the diagnostic script for specific test results
- Review the dashboard at `reports/dashboard_20260103_195342.html`

Good luck! 🚀
