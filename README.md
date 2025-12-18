# Sentiment Velocity Tracker - Technical Specification

## Overview

A Python-based daily pipeline that identifies stocks with unusual social momentum, cross-references against insider buying activity, and generates actionable alerts. Designed for a single developer to run on a local machine or cheap VPS.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DAILY CRON (6:00 AM ET)                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA COLLECTORS                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  ApeWisdom  │  │ OpenInsider │  │   Finnhub   │  │    FRED    │ │
│  │  (social)   │  │  (insiders) │  │(price/news) │  │  (macro)   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
└─────────┼────────────────┼────────────────┼───────────────┼────────┘
          │                │                │               │
          ▼                ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SQLite Database                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  mentions   │  │   insiders  │  │   prices    │  │   macro    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       VELOCITY CALCULATOR                           │
│  • 24h mention velocity (% change)                                  │
│  • 7d mention velocity (trend)                                      │
│  • Sentiment score delta                                            │
│  • Volume/price divergence                                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SIGNAL GENERATOR                             │
│  • Cross-reference velocity spikes with insider buys                │
│  • Flag tickers meeting threshold criteria                          │
│  • Score and rank by conviction                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        REPORT GENERATOR                             │
│  • HTML email with embedded charts                                  │
│  • JSON output for further processing                               │
│  • CSV trade log for paper trading                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
sentiment_velocity/
├── config/
│   ├── config.yaml          # API keys, thresholds, email settings
│   └── config.example.yaml  # Template without secrets
├── data/
│   └── sentiment.db         # SQLite database (gitignored)
├── src/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── apewisdom.py     # Social mention scraper
│   │   ├── openinsider.py   # Insider trading scraper
│   │   ├── finnhub.py       # Price + sentiment API
│   │   └── fred.py          # Macro indicators
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py        # SQLite table definitions
│   │   └── queries.py       # Common query functions
│   ├── metrics/
│   │   ├── __init__.py
│   │   └── velocity.py      # Velocity calculations
│   ├── signals/
│   │   ├── __init__.py
│   │   └── generator.py     # Signal logic + scoring
│   └── reporters/
│       ├── __init__.py
│       ├── email.py         # HTML email generation
│       └── charts.py        # Matplotlib visualizations
├── tests/
│   ├── test_collectors.py
│   ├── test_velocity.py
│   └── test_signals.py
├── main.py                  # Pipeline orchestrator
├── requirements.txt
├── .env.example             # Environment variables template
├── .gitignore
└── README.md
```

---

## Data Sources

### 1. ApeWisdom (Social Mentions)

**Endpoint:** `https://apewisdom.io/api/v1.0/filter/all-stocks`

**Method:** GET (no authentication required)

**Response Format:**
```json
{
  "results": [
    {
      "ticker": "NVDA",
      "name": "NVIDIA Corporation",
      "rank": 1,
      "mentions": 542,
      "upvotes": 12847,
      "rank_24h_ago": 2,
      "mentions_24h_ago": 389
    }
  ]
}
```

**Rate Limits:** ~100 requests/day (undocumented, be conservative)

**Collection Frequency:** Every 4 hours (6 times daily)

**Fields to Store:**
- ticker
- mentions
- upvotes  
- rank
- timestamp (collection time)

---

### 2. OpenInsider (Insider Trading)

**Method:** Web scraping (no official API)

**Target URLs:**
- Cluster buys: `http://openinsider.com/latest-cluster-buys`
- CEO/CFO buys: `http://openinsider.com/latest-ceo-cfo-purchases-25k`
- All insider buys: `http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=1&fdr=&td=0&tdr=&fdlyl=&fdlyh=&dtefrom=&dteto=&xp=1&vl=25&vh=&ocl=&och=&session=historic`

**Scraping Strategy:**
```python
# Use requests + BeautifulSoup
# Parse the HTML table with class "tinytable"
# Extract: Filing Date, Trade Date, Ticker, Insider Name, Title, 
#          Trade Type, Price, Qty, Owned, Delta Own, Value
```

**Rate Limits:** Be respectful, 1 request per URL per run

**Collection Frequency:** Once daily (morning)

**Fields to Store:**
- ticker
- insider_name
- insider_title (CEO, CFO, Director, 10% Owner)
- trade_type (P = Purchase, S = Sale)
- trade_date
- filing_date
- shares
- price
- value
- ownership_change_pct
- is_cluster_buy (boolean)

---

### 3. Finnhub (Price Data + News Sentiment)

**Base URL:** `https://finnhub.io/api/v1`

**Authentication:** API key as query param `?token=YOUR_KEY`

**Free Tier Limits:** 60 requests/minute

**Endpoints to Use:**

#### Quote (Current Price)
```
GET /quote?symbol=AAPL&token=xxx
Response: {"c": 150.25, "h": 151.00, "l": 149.50, "o": 150.00, "pc": 149.00, "t": 1234567890}
```

#### News Sentiment
```
GET /news-sentiment?symbol=AAPL&token=xxx
Response: {
  "buzz": {"articlesInLastWeek": 50, "buzz": 0.85, "weeklyAverage": 40},
  "companyNewsScore": 0.65,
  "sectorAverageBullishPercent": 0.55,
  "sectorAverageNewsScore": 0.50,
  "sentiment": {"bearishPercent": 0.15, "bullishPercent": 0.65}
}
```

#### Social Sentiment (Reddit/Twitter)
```
GET /stock/social-sentiment?symbol=AAPL&token=xxx
Response: {
  "reddit": [{"atTime": "2024-01-15", "mention": 150, "positiveScore": 0.8, "negativeScore": 0.1, "score": 0.7}],
  "twitter": [...]
}
```

**Fields to Store:**
- ticker
- price_current
- price_change_pct
- news_sentiment_score
- bullish_pct
- bearish_pct
- social_mention_count (from Finnhub)
- timestamp

---

### 4. FRED (Macro Indicators) - Optional Phase 2

**Base URL:** `https://api.stlouisfed.org/fred/series/observations`

**Authentication:** Free API key from https://fred.stlouisfed.org/docs/api/api_key.html

**Key Series:**
| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| T10Y2Y | 10Y-2Y Treasury Spread (yield curve) | Daily |
| VIXCLS | VIX Volatility Index | Daily |
| ICSA | Initial Jobless Claims | Weekly |
| UNRATE | Unemployment Rate | Monthly |

**Collection Frequency:** Once daily

---

## Database Schema

### SQLite Tables

```sql
-- Social mentions from ApeWisdom
CREATE TABLE mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    mentions INTEGER NOT NULL,
    upvotes INTEGER,
    rank INTEGER,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'apewisdom'
);
CREATE INDEX idx_mentions_ticker_time ON mentions(ticker, collected_at);

-- Insider trading from OpenInsider
CREATE TABLE insiders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    insider_name TEXT,
    insider_title TEXT,
    trade_type TEXT,  -- 'P' = Purchase, 'S' = Sale
    trade_date DATE,
    filing_date DATE,
    shares INTEGER,
    price REAL,
    value REAL,
    ownership_change_pct REAL,
    is_cluster_buy BOOLEAN DEFAULT 0,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_insiders_ticker_date ON insiders(ticker, trade_date);

-- Price and sentiment from Finnhub
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    price REAL,
    change_pct REAL,
    news_sentiment REAL,
    bullish_pct REAL,
    bearish_pct REAL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_prices_ticker_time ON prices(ticker, collected_at);

-- Calculated velocity metrics
CREATE TABLE velocity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    mention_velocity_24h REAL,  -- % change in mentions
    mention_velocity_7d REAL,
    sentiment_velocity REAL,    -- rate of change in sentiment score
    volume_price_divergence REAL,
    composite_score REAL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_velocity_ticker_time ON velocity(ticker, calculated_at);

-- Generated signals for tracking
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    signal_type TEXT,  -- 'velocity_spike', 'insider_cluster', 'sentiment_flip', 'combined'
    conviction_score REAL,  -- 0-100
    price_at_signal REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- For paper trading tracking
    outcome_price REAL,
    outcome_date DATE,
    outcome_pct REAL
);
CREATE INDEX idx_signals_ticker_date ON signals(ticker, created_at);

-- Macro indicators (Phase 2)
CREATE TABLE macro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT NOT NULL,
    value REAL,
    observation_date DATE,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Velocity Calculations

### Core Metrics

```python
# src/metrics/velocity.py

from typing import List, Tuple
import numpy as np
from datetime import datetime, timedelta

def mention_velocity_pct(current: int, previous: int) -> float:
    """
    Calculate percentage change in mentions.
    
    Args:
        current: Current mention count
        previous: Previous period mention count
        
    Returns:
        Percentage change (-100 to +inf)
    """
    if previous == 0:
        return 0.0 if current == 0 else 100.0  # Cap at 100% if from zero
    return ((current - previous) / previous) * 100


def mention_velocity_trend(mention_history: List[Tuple[datetime, int]], 
                           window_days: int = 7) -> float:
    """
    Calculate trend direction using linear regression slope.
    
    Args:
        mention_history: List of (timestamp, mention_count) tuples
        window_days: Days to consider
        
    Returns:
        Slope of trend line (positive = accelerating, negative = decelerating)
    """
    if len(mention_history) < 2:
        return 0.0
    
    cutoff = datetime.now() - timedelta(days=window_days)
    recent = [(ts, count) for ts, count in mention_history if ts >= cutoff]
    
    if len(recent) < 2:
        return 0.0
    
    x = np.arange(len(recent))
    y = np.array([count for _, count in recent])
    
    slope, _ = np.polyfit(x, y, 1)
    return slope


def sentiment_velocity(sentiment_scores: List[float], window: int = 6) -> float:
    """
    Calculate rate of change in sentiment scores.
    
    Args:
        sentiment_scores: List of sentiment scores (chronological order)
        window: Smoothing window size
        
    Returns:
        Smoothed velocity of sentiment change
    """
    if len(sentiment_scores) < 2:
        return 0.0
    
    scores = np.array(sentiment_scores)
    velocity = np.gradient(scores)
    
    if len(velocity) < window:
        return float(np.mean(velocity))
    
    smoothed = np.convolve(velocity, np.ones(window)/window, mode='valid')
    return float(smoothed[-1]) if len(smoothed) > 0 else 0.0


def volume_price_divergence(mention_changes: List[float], 
                            price_changes: List[float]) -> float:
    """
    Detect when social volume outpaces price movement.
    
    Positive divergence = mentions growing faster than price (potential breakout)
    Negative divergence = price growing faster than mentions (potential reversal)
    
    Args:
        mention_changes: List of mention % changes
        price_changes: List of price % changes
        
    Returns:
        Divergence score
    """
    if len(mention_changes) != len(price_changes) or len(mention_changes) == 0:
        return 0.0
    
    mention_arr = np.array(mention_changes)
    price_arr = np.array(price_changes)
    
    # Normalize to same scale
    mention_norm = mention_arr / (np.std(mention_arr) + 0.001)
    price_norm = price_arr / (np.std(price_arr) + 0.001)
    
    divergence = mention_norm - price_norm
    return float(np.mean(divergence))


def composite_score(mention_vel_24h: float,
                    mention_vel_7d: float,
                    sentiment_vel: float,
                    divergence: float,
                    weights: dict = None) -> float:
    """
    Calculate weighted composite velocity score.
    
    Args:
        mention_vel_24h: 24-hour mention velocity
        mention_vel_7d: 7-day mention trend
        sentiment_vel: Sentiment velocity
        divergence: Volume/price divergence
        weights: Custom weights dict
        
    Returns:
        Composite score (0-100 scale)
    """
    if weights is None:
        weights = {
            'mention_24h': 0.35,
            'mention_7d': 0.25,
            'sentiment': 0.25,
            'divergence': 0.15
        }
    
    # Normalize each component to 0-100 scale
    # Using sigmoid-like transformation to handle outliers
    def normalize(x, scale=50):
        return 100 / (1 + np.exp(-x / scale))
    
    score = (
        weights['mention_24h'] * normalize(mention_vel_24h, 100) +
        weights['mention_7d'] * normalize(mention_vel_7d, 10) +
        weights['sentiment'] * normalize(sentiment_vel * 100, 20) +
        weights['divergence'] * normalize(divergence * 50, 25)
    )
    
    return min(100, max(0, score))
```

---

## Signal Generation Logic

### Thresholds and Rules

```python
# src/signals/generator.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

@dataclass
class Signal:
    ticker: str
    signal_type: str
    conviction_score: float  # 0-100
    price_at_signal: float
    triggers: List[str]  # What triggered this signal
    notes: str
    created_at: datetime


class SignalGenerator:
    """Generate trading signals based on velocity and insider data."""
    
    # Configurable thresholds
    THRESHOLDS = {
        'velocity_spike': {
            'mention_vel_24h_min': 100,     # 100%+ increase in 24h
            'composite_score_min': 60,       # Minimum composite score
        },
        'insider_cluster': {
            'min_insiders': 2,               # At least 2 insiders buying
            'lookback_days': 14,             # Within 14 days
            'min_value_total': 100000,       # $100k+ total
        },
        'sentiment_flip': {
            'sentiment_delta_min': 0.3,      # 30%+ shift in sentiment
            'lookback_days': 7,
        },
        'combined': {
            'velocity_score_min': 50,        # Lower threshold when combined
            'requires_insider': True,        # Must have insider activity
        }
    }
    
    def generate_signals(self, 
                         velocity_data: dict,
                         insider_data: dict,
                         price_data: dict) -> List[Signal]:
        """
        Main signal generation logic.
        
        Args:
            velocity_data: Dict of ticker -> velocity metrics
            insider_data: Dict of ticker -> recent insider trades
            price_data: Dict of ticker -> current price info
            
        Returns:
            List of Signal objects, sorted by conviction
        """
        signals = []
        
        for ticker in velocity_data.keys():
            vel = velocity_data[ticker]
            insiders = insider_data.get(ticker, [])
            price = price_data.get(ticker, {})
            
            triggers = []
            conviction = 0
            
            # Check velocity spike
            if self._check_velocity_spike(vel):
                triggers.append('velocity_spike')
                conviction += 30
            
            # Check insider cluster
            if self._check_insider_cluster(insiders):
                triggers.append('insider_cluster')
                conviction += 40
            
            # Check sentiment flip
            if self._check_sentiment_flip(vel):
                triggers.append('sentiment_flip')
                conviction += 20
            
            # Boost for combined signals
            if len(triggers) >= 2:
                conviction += 15
            
            # Add base composite score
            conviction += vel.get('composite_score', 0) * 0.3
            
            # Cap at 100
            conviction = min(100, conviction)
            
            if triggers and conviction >= 40:
                signals.append(Signal(
                    ticker=ticker,
                    signal_type='combined' if len(triggers) > 1 else triggers[0],
                    conviction_score=conviction,
                    price_at_signal=price.get('price', 0),
                    triggers=triggers,
                    notes=self._generate_notes(ticker, vel, insiders, triggers),
                    created_at=datetime.now()
                ))
        
        # Sort by conviction descending
        signals.sort(key=lambda s: s.conviction_score, reverse=True)
        return signals
    
    def _check_velocity_spike(self, vel: dict) -> bool:
        """Check if velocity meets spike threshold."""
        return (
            vel.get('mention_velocity_24h', 0) >= self.THRESHOLDS['velocity_spike']['mention_vel_24h_min'] and
            vel.get('composite_score', 0) >= self.THRESHOLDS['velocity_spike']['composite_score_min']
        )
    
    def _check_insider_cluster(self, insiders: list) -> bool:
        """Check if insider buying meets cluster criteria."""
        if not insiders:
            return False
        
        cutoff = datetime.now() - timedelta(days=self.THRESHOLDS['insider_cluster']['lookback_days'])
        recent_buys = [i for i in insiders 
                       if i.get('trade_type') == 'P' and 
                       i.get('trade_date', datetime.min) >= cutoff]
        
        if len(recent_buys) < self.THRESHOLDS['insider_cluster']['min_insiders']:
            return False
        
        total_value = sum(i.get('value', 0) for i in recent_buys)
        return total_value >= self.THRESHOLDS['insider_cluster']['min_value_total']
    
    def _check_sentiment_flip(self, vel: dict) -> bool:
        """Check if sentiment has flipped significantly."""
        return abs(vel.get('sentiment_velocity', 0)) >= self.THRESHOLDS['sentiment_flip']['sentiment_delta_min']
    
    def _generate_notes(self, ticker: str, vel: dict, insiders: list, triggers: list) -> str:
        """Generate human-readable notes for the signal."""
        notes = []
        
        if 'velocity_spike' in triggers:
            notes.append(f"Mentions up {vel.get('mention_velocity_24h', 0):.0f}% in 24h")
        
        if 'insider_cluster' in triggers:
            buy_count = len([i for i in insiders if i.get('trade_type') == 'P'])
            total_val = sum(i.get('value', 0) for i in insiders if i.get('trade_type') == 'P')
            notes.append(f"{buy_count} insiders bought ${total_val:,.0f} recently")
        
        if 'sentiment_flip' in triggers:
            direction = "bullish" if vel.get('sentiment_velocity', 0) > 0 else "bearish"
            notes.append(f"Sentiment flipping {direction}")
        
        return " | ".join(notes)
```

---

## Configuration

### config.example.yaml

```yaml
# API Keys (get free keys from each provider)
api_keys:
  finnhub: "YOUR_FINNHUB_KEY"  # https://finnhub.io/register
  fred: "YOUR_FRED_KEY"        # https://fred.stlouisfed.org/docs/api/api_key.html

# Database
database:
  path: "data/sentiment.db"

# Collection settings
collection:
  apewisdom:
    interval_hours: 4        # How often to collect
    top_n: 100               # How many tickers to track
  openinsider:
    interval_hours: 24       # Once daily
    min_value: 25000         # Minimum transaction value
  finnhub:
    interval_hours: 4
    rate_limit_per_min: 55   # Stay under 60

# Signal thresholds (can be tuned)
thresholds:
  velocity_spike:
    mention_vel_24h_min: 100
    composite_score_min: 60
  insider_cluster:
    min_insiders: 2
    lookback_days: 14
    min_value_total: 100000
  minimum_conviction: 40     # Don't report signals below this

# Email settings
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender: "your-email@gmail.com"
  password: "your-app-password"  # Use Gmail app password
  recipients:
    - "your-email@gmail.com"

# Report settings
report:
  include_charts: true
  max_signals: 10            # Top N signals to include
  include_watchlist: true    # Include full velocity rankings
```

---

## Main Pipeline

### main.py

```python
#!/usr/bin/env python3
"""
Sentiment Velocity Tracker - Main Pipeline
==========================================
Run daily via cron: 0 6 * * * cd /path/to/sentiment_velocity && python main.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from src.collectors.apewisdom import ApeWisdomCollector
from src.collectors.openinsider import OpenInsiderCollector
from src.collectors.finnhub import FinnhubCollector
from src.database.models import Database
from src.metrics.velocity import VelocityCalculator
from src.signals.generator import SignalGenerator
from src.reporters.email import EmailReporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def run_pipeline(config: dict):
    """Execute the full data pipeline."""
    
    logger.info("=" * 60)
    logger.info(f"Starting pipeline run at {datetime.now()}")
    logger.info("=" * 60)
    
    # Initialize database
    db = Database(config['database']['path'])
    db.initialize()
    
    # Step 1: Collect data
    logger.info("Step 1: Collecting data...")
    
    # ApeWisdom (social mentions)
    try:
        ape = ApeWisdomCollector()
        mentions = ape.collect(top_n=config['collection']['apewisdom']['top_n'])
        db.insert_mentions(mentions)
        logger.info(f"  - ApeWisdom: {len(mentions)} tickers collected")
    except Exception as e:
        logger.error(f"  - ApeWisdom failed: {e}")
    
    # OpenInsider (insider trades)
    try:
        insider = OpenInsiderCollector()
        trades = insider.collect_cluster_buys()
        trades += insider.collect_ceo_cfo_buys(
            min_value=config['collection']['openinsider']['min_value']
        )
        db.insert_insiders(trades)
        logger.info(f"  - OpenInsider: {len(trades)} trades collected")
    except Exception as e:
        logger.error(f"  - OpenInsider failed: {e}")
    
    # Finnhub (prices + sentiment)
    try:
        finnhub = FinnhubCollector(api_key=config['api_keys']['finnhub'])
        # Get prices for tickers we're tracking
        tracked_tickers = db.get_tracked_tickers(days=7)
        prices = finnhub.collect_quotes(tracked_tickers)
        sentiments = finnhub.collect_sentiment(tracked_tickers)
        db.insert_prices(prices)
        logger.info(f"  - Finnhub: {len(prices)} prices, {len(sentiments)} sentiments")
    except Exception as e:
        logger.error(f"  - Finnhub failed: {e}")
    
    # Step 2: Calculate velocity metrics
    logger.info("Step 2: Calculating velocity metrics...")
    
    calc = VelocityCalculator(db)
    velocity_data = calc.calculate_all_velocities()
    db.insert_velocity(velocity_data)
    logger.info(f"  - Calculated velocity for {len(velocity_data)} tickers")
    
    # Step 3: Generate signals
    logger.info("Step 3: Generating signals...")
    
    gen = SignalGenerator(thresholds=config.get('thresholds', {}))
    signals = gen.generate_signals(
        velocity_data=velocity_data,
        insider_data=db.get_recent_insiders(days=14),
        price_data=db.get_latest_prices()
    )
    
    # Filter by minimum conviction
    min_conviction = config['thresholds'].get('minimum_conviction', 40)
    signals = [s for s in signals if s.conviction_score >= min_conviction]
    
    db.insert_signals(signals)
    logger.info(f"  - Generated {len(signals)} signals above {min_conviction} conviction")
    
    # Step 4: Generate and send report
    logger.info("Step 4: Generating report...")
    
    if config['email']['enabled'] and signals:
        reporter = EmailReporter(config['email'])
        report = reporter.generate_report(
            signals=signals[:config['report']['max_signals']],
            velocity_data=velocity_data,
            include_charts=config['report']['include_charts']
        )
        reporter.send(report)
        logger.info("  - Email report sent")
    elif not signals:
        logger.info("  - No signals to report")
    else:
        logger.info("  - Email disabled, skipping")
    
    # Step 5: Output summary
    logger.info("=" * 60)
    logger.info("Pipeline complete. Summary:")
    logger.info(f"  - Top signal: {signals[0].ticker if signals else 'None'} "
                f"({signals[0].conviction_score:.0f})" if signals else "")
    for s in signals[:5]:
        logger.info(f"    {s.ticker}: {s.conviction_score:.0f} - {s.notes}")
    logger.info("=" * 60)
    
    return signals


if __name__ == "__main__":
    config = load_config()
    
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    try:
        signals = run_pipeline(config)
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)
```

---

## Collector Implementations

### ApeWisdom Collector

```python
# src/collectors/apewisdom.py

import requests
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ApeWisdomCollector:
    """Collect social mention data from ApeWisdom API."""
    
    BASE_URL = "https://apewisdom.io/api/v1.0"
    
    def collect(self, top_n: int = 100) -> List[Dict]:
        """
        Fetch top mentioned stocks from ApeWisdom.
        
        Args:
            top_n: Number of top tickers to return
            
        Returns:
            List of dicts with ticker mention data
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/filter/all-stocks",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('results', [])[:top_n]:
                results.append({
                    'ticker': item.get('ticker', '').upper(),
                    'mentions': item.get('mentions', 0),
                    'upvotes': item.get('upvotes', 0),
                    'rank': item.get('rank', 0),
                    'mentions_24h_ago': item.get('mentions_24h_ago', 0),
                    'rank_24h_ago': item.get('rank_24h_ago', 0),
                    'collected_at': datetime.now(),
                    'source': 'apewisdom'
                })
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"ApeWisdom API error: {e}")
            return []
```

### OpenInsider Scraper

```python
# src/collectors/openinsider.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)

class OpenInsiderCollector:
    """Scrape insider trading data from OpenInsider."""
    
    BASE_URL = "http://openinsider.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def collect_cluster_buys(self) -> List[Dict]:
        """Scrape latest cluster buys."""
        return self._scrape_table(f"{self.BASE_URL}/latest-cluster-buys", is_cluster=True)
    
    def collect_ceo_cfo_buys(self, min_value: int = 25000) -> List[Dict]:
        """Scrape CEO/CFO purchases over min_value."""
        url = f"{self.BASE_URL}/screener?s=&o=&pl=&ph=&ll=&lh=&fd=7&td=0&xp=1&vl={min_value}&vh=&ocl=&och=&sic1=-1&sic2=-1&sic3=-1&sic4=-1&sort=trade_date&order=desc"
        return self._scrape_table(url, is_cluster=False)
    
    def _scrape_table(self, url: str, is_cluster: bool = False) -> List[Dict]:
        """
        Parse the insider trading table from OpenInsider.
        
        Args:
            url: Page URL to scrape
            is_cluster: Whether this is cluster buy data
            
        Returns:
            List of insider trade dicts
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='tinytable')
            
            if not table:
                logger.warning(f"No table found at {url}")
                return []
            
            results = []
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue
                
                try:
                    # Parse the row data
                    ticker_link = cells[3].find('a')
                    ticker = ticker_link.text.strip() if ticker_link else ''
                    
                    results.append({
                        'ticker': ticker.upper(),
                        'filing_date': self._parse_date(cells[1].text.strip()),
                        'trade_date': self._parse_date(cells[2].text.strip()),
                        'insider_name': cells[4].text.strip(),
                        'insider_title': cells[5].text.strip(),
                        'trade_type': cells[6].text.strip(),  # P = Purchase, S = Sale
                        'price': self._parse_float(cells[7].text),
                        'shares': self._parse_int(cells[8].text),
                        'value': self._parse_int(cells[9].text),
                        'ownership_change_pct': self._parse_float(cells[10].text) if len(cells) > 10 else 0,
                        'is_cluster_buy': is_cluster,
                        'collected_at': datetime.now()
                    })
                except (IndexError, ValueError) as e:
                    logger.debug(f"Row parse error: {e}")
                    continue
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"OpenInsider scrape error: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string from OpenInsider."""
        try:
            return datetime.strptime(date_str.strip(), '%Y-%m-%d')
        except ValueError:
            return datetime.now()
    
    def _parse_float(self, value_str: str) -> float:
        """Parse float from string, handling $, commas, %."""
        try:
            cleaned = value_str.replace('$', '').replace(',', '').replace('%', '').replace('+', '').strip()
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    
    def _parse_int(self, value_str: str) -> int:
        """Parse int from string, handling commas."""
        try:
            cleaned = value_str.replace('$', '').replace(',', '').replace('+', '').strip()
            return int(float(cleaned)) if cleaned else 0
        except ValueError:
            return 0
```

### Finnhub Collector

```python
# src/collectors/finnhub.py

import requests
from datetime import datetime
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)

class FinnhubCollector:
    """Collect price and sentiment data from Finnhub API."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str, rate_limit: int = 55):
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._request_count = 0
        self._minute_start = time.time()
    
    def _rate_limit_wait(self):
        """Implement rate limiting."""
        self._request_count += 1
        elapsed = time.time() - self._minute_start
        
        if elapsed < 60 and self._request_count >= self.rate_limit:
            sleep_time = 60 - elapsed + 1
            logger.debug(f"Rate limit reached, sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = time.time()
        elif elapsed >= 60:
            self._request_count = 1
            self._minute_start = time.time()
    
    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make rate-limited GET request."""
        self._rate_limit_wait()
        
        if params is None:
            params = {}
        params['token'] = self.api_key
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Finnhub API error: {e}")
            return {}
    
    def collect_quotes(self, tickers: List[str]) -> List[Dict]:
        """
        Fetch current quotes for list of tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of quote dicts
        """
        results = []
        
        for ticker in tickers:
            data = self._get('quote', {'symbol': ticker})
            
            if data and 'c' in data:
                prev_close = data.get('pc', 0)
                current = data.get('c', 0)
                change_pct = ((current - prev_close) / prev_close * 100) if prev_close else 0
                
                results.append({
                    'ticker': ticker,
                    'price': current,
                    'change_pct': change_pct,
                    'high': data.get('h', 0),
                    'low': data.get('l', 0),
                    'open': data.get('o', 0),
                    'prev_close': prev_close,
                    'collected_at': datetime.now()
                })
        
        return results
    
    def collect_sentiment(self, tickers: List[str]) -> List[Dict]:
        """
        Fetch news sentiment for list of tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            List of sentiment dicts
        """
        results = []
        
        for ticker in tickers:
            data = self._get('news-sentiment', {'symbol': ticker})
            
            if data and 'sentiment' in data:
                results.append({
                    'ticker': ticker,
                    'news_sentiment': data.get('companyNewsScore', 0),
                    'bullish_pct': data.get('sentiment', {}).get('bullishPercent', 0),
                    'bearish_pct': data.get('sentiment', {}).get('bearishPercent', 0),
                    'buzz_score': data.get('buzz', {}).get('buzz', 0),
                    'articles_week': data.get('buzz', {}).get('articlesInLastWeek', 0),
                    'collected_at': datetime.now()
                })
        
        return results
```

---

## Email Report Template

### HTML Email Structure

```python
# src/reporters/email.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List
import logging
import io

logger = logging.getLogger(__name__)

class EmailReporter:
    """Generate and send HTML email reports."""
    
    def __init__(self, config: dict):
        self.config = config
    
    def generate_report(self, signals: List, velocity_data: dict, 
                        include_charts: bool = True) -> str:
        """Generate HTML email content."""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
                .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                          color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
                .signal-card {{ background: white; border-radius: 10px; padding: 20px; 
                               margin-bottom: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .conviction {{ font-size: 24px; font-weight: bold; }}
                .conviction.high {{ color: #00c853; }}
                .conviction.medium {{ color: #ffc107; }}
                .conviction.low {{ color: #ff5722; }}
                .ticker {{ font-size: 28px; font-weight: bold; color: #1a1a2e; }}
                .triggers {{ display: flex; gap: 8px; margin-top: 10px; }}
                .trigger {{ background: #e3f2fd; color: #1565c0; padding: 4px 12px; 
                           border-radius: 15px; font-size: 12px; }}
                .notes {{ color: #666; margin-top: 10px; font-size: 14px; }}
                .velocity-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                .velocity-table th, .velocity-table td {{ padding: 12px; text-align: left; 
                                                          border-bottom: 1px solid #eee; }}
                .velocity-table th {{ background: #f5f5f5; font-weight: 600; }}
                .positive {{ color: #00c853; }}
                .negative {{ color: #ff5722; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin:0;">📊 Sentiment Velocity Report</h1>
                <p style="margin:10px 0 0 0; opacity: 0.8;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>
        """
        
        # Signals section
        if signals:
            html += "<h2>🎯 Today's Signals</h2>"
            
            for signal in signals:
                conviction_class = 'high' if signal.conviction_score >= 70 else \
                                   'medium' if signal.conviction_score >= 50 else 'low'
                
                triggers_html = ''.join([f'<span class="trigger">{t}</span>' 
                                         for t in signal.triggers])
                
                html += f"""
                <div class="signal-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="ticker">{signal.ticker}</span>
                        <span class="conviction {conviction_class}">{signal.conviction_score:.0f}</span>
                    </div>
                    <div class="triggers">{triggers_html}</div>
                    <div class="notes">{signal.notes}</div>
                    <div style="margin-top: 10px; font-size: 13px; color: #999;">
                        Price at signal: ${signal.price_at_signal:.2f}
                    </div>
                </div>
                """
        else:
            html += """
            <div class="signal-card">
                <p style="text-align: center; color: #666;">No signals met conviction threshold today.</p>
            </div>
            """
        
        # Velocity watchlist
        html += "<h2>📈 Velocity Watchlist (Top 20)</h2>"
        html += """
        <table class="velocity-table">
            <tr>
                <th>Ticker</th>
                <th>24h Velocity</th>
                <th>7d Trend</th>
                <th>Composite</th>
            </tr>
        """
        
        # Sort by composite score and take top 20
        sorted_velocity = sorted(velocity_data.items(), 
                                 key=lambda x: x[1].get('composite_score', 0), 
                                 reverse=True)[:20]
        
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
        
        # Footer
        html += """
            <div class="footer">
                <p>Generated by Sentiment Velocity Tracker</p>
                <p>⚠️ This is not financial advice. Paper trade first.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send(self, html_content: str):
        """Send the HTML email."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📊 Sentiment Velocity Report - {datetime.now().strftime('%m/%d')}"
            msg['From'] = self.config['sender']
            msg['To'] = ', '.join(self.config['recipients'])
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['sender'], self.config['password'])
                server.send_message(msg)
            
            logger.info("Email sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
```

---

## Requirements

### requirements.txt

```
# Core
requests>=2.28.0
beautifulsoup4>=4.11.0
pyyaml>=6.0
numpy>=1.23.0

# Database
# (sqlite3 is built into Python)

# Visualization (optional, for charts)
matplotlib>=3.6.0
pandas>=1.5.0

# Testing
pytest>=7.0.0
pytest-cov>=4.0.0

# Development
black>=22.0.0
flake8>=5.0.0
```

---

## Deployment

### Cron Setup (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line to run at 6 AM ET every day
0 6 * * * cd /path/to/sentiment_velocity && /usr/bin/python3 main.py >> logs/cron.log 2>&1

# Or run every 4 hours for more frequent collection
0 */4 * * * cd /path/to/sentiment_velocity && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

### Windows Task Scheduler

```powershell
# Create scheduled task to run daily at 6 AM
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\sentiment_velocity\main.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 6am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "SentimentVelocityTracker"
```

### VPS Deployment (Optional)

For always-on operation, deploy to a cheap VPS:

1. **Hetzner CX22** (~$4/month): 2 vCPU, 4GB RAM
2. **DigitalOcean Basic** ($4/month): 1 vCPU, 512MB RAM (sufficient)
3. **Oracle Cloud Free Tier**: Free forever, 1GB RAM

---

## Testing Strategy

### Unit Tests

```python
# tests/test_velocity.py

import pytest
from src.metrics.velocity import (
    mention_velocity_pct,
    sentiment_velocity,
    composite_score
)

def test_mention_velocity_pct_increase():
    assert mention_velocity_pct(200, 100) == 100.0

def test_mention_velocity_pct_decrease():
    assert mention_velocity_pct(50, 100) == -50.0

def test_mention_velocity_pct_zero_previous():
    assert mention_velocity_pct(100, 0) == 100.0

def test_sentiment_velocity_increasing():
    scores = [0.3, 0.4, 0.5, 0.6, 0.7]
    vel = sentiment_velocity(scores)
    assert vel > 0

def test_composite_score_bounds():
    score = composite_score(
        mention_vel_24h=500,
        mention_vel_7d=50,
        sentiment_vel=1.0,
        divergence=2.0
    )
    assert 0 <= score <= 100
```

### Integration Tests

```python
# tests/test_collectors.py

import pytest
from src.collectors.apewisdom import ApeWisdomCollector

@pytest.mark.integration
def test_apewisdom_live():
    """Test live API call (requires network)."""
    collector = ApeWisdomCollector()
    results = collector.collect(top_n=10)
    
    assert len(results) > 0
    assert 'ticker' in results[0]
    assert 'mentions' in results[0]
```

---

## Future Enhancements (Phase 2+)

1. **Backtesting Module**: Track signal outcomes over time, calculate win rate by signal type
2. **FRED Integration**: Add macro regime detection (risk-on/risk-off based on yield curve, VIX)
3. **Options Flow**: Integrate with Unusual Whales or Cheddar Flow API (paid)
4. **Congress Trades**: Add Quiver Quant scraping
5. **Web Dashboard**: Simple Flask/FastAPI UI for viewing signals
6. **Discord/Telegram Bot**: Push notifications instead of email
7. **Paper Trading Integration**: Connect to broker paper trading API for automated tracking

---

## Quick Start

```bash
# 1. Clone and setup
git clone <your-repo>
cd sentiment_velocity
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Configure
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your API keys and email settings

# 3. Initialize database
python -c "from src.database.models import Database; Database('data/sentiment.db').initialize()"

# 4. Test run
python main.py

# 5. Setup cron for daily runs
crontab -e
# Add: 0 6 * * * cd /path/to/sentiment_velocity && python main.py
```

---

## Notes for Implementation

- **Rate Limiting**: Be conservative with API calls. ApeWisdom is undocumented, don't hammer it.
- **Error Handling**: Every collector should fail gracefully and log errors. Pipeline should continue if one source fails.
- **Data Retention**: Consider pruning old data (>90 days) to keep DB size manageable.
- **Secrets**: Never commit API keys. Use environment variables or a gitignored config file.
- **Testing**: Paper trade for at least 4-6 weeks before committing real capital.

---

*Spec version: 1.0*  
*Last updated: December 2024*
