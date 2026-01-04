#!/usr/bin/env python3
"""
@file debug_collectors.py
@brief Diagnostic script to test individual data collectors
@details Tests each collector independently to identify data availability vs pipeline issues
"""

import logging
import sys
import yaml
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration"""
    try:
        with open('config/config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def test_vader_sentiment():
    """Test VADER sentiment collector"""
    print("\n" + "="*60)
    print("TESTING VADER SENTIMENT COLLECTOR")
    print("="*60)

    try:
        from src.collectors.vader_sentiment import VaderSentimentAnalyzer

        vader = VaderSentimentAnalyzer()
        test_ticker = "AAPL"

        # Test Google News scraping
        print(f"\n[1/3] Testing Google News scraping for {test_ticker}...")
        google_url = f"https://news.google.com/search?q={test_ticker}+stock"
        print(f"      URL: {google_url}")

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(google_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try different possible selectors
            articles = soup.find_all('article')
            print(f"      Found {len(articles)} article elements")

            if articles:
                print(f"\n      Inspecting first article structure:")
                print(f"      Classes in article: {articles[0].get('class')}")

                # Try different headline selectors
                selectors_to_try = [
                    ('a', {'class': 'gPFEn'}),
                    ('a', {'class': 'JtKRv'}),
                    ('h3', {}),
                    ('h4', {}),
                    ('a', {})
                ]

                for tag, attrs in selectors_to_try:
                    found = articles[0].find(tag, attrs)
                    if found:
                        print(f"      ✓ Found <{tag}> with attrs {attrs}: {found.get_text()[:50]}...")
                        break
                else:
                    print(f"      ✗ No headline found with known selectors")
                    print(f"      Article HTML: {str(articles[0])[:500]}...")
            else:
                print(f"      ✗ No articles found on page")
                print(f"      Page title: {soup.title.string if soup.title else 'No title'}")

        except Exception as e:
            print(f"      ✗ Error: {e}")

        # Test Yahoo Finance scraping
        print(f"\n[2/3] Testing Yahoo Finance scraping for {test_ticker}...")
        yahoo_url = f"https://finance.yahoo.com/quote/{test_ticker}"
        print(f"      URL: {yahoo_url}")

        try:
            response = requests.get(yahoo_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try different possible selectors
            selectors_to_try = [
                ('h3', {'class': 'Mb(5px)'}),
                ('h3', {}),
                ('a', {'data-test': 'quoteNews'}),
            ]

            for tag, attrs in selectors_to_try:
                found = soup.find_all(tag, attrs)
                if found:
                    print(f"      ✓ Found {len(found)} <{tag}> elements with attrs {attrs}")
                    if found:
                        print(f"        First: {found[0].get_text()[:50]}...")
                    break
            else:
                print(f"      ✗ No headlines found with known selectors")

        except Exception as e:
            print(f"      ✗ Error: {e}")

        # Test full sentiment analysis
        print(f"\n[3/3] Testing full sentiment analysis for {test_ticker}...")
        result = vader.analyze_ticker_sentiment(test_ticker)
        print(f"      Headlines found: {result.get('total_headlines', 0)}")
        if result.get('total_headlines', 0) > 0:
            print(f"      Sentiment: {result.get('sentiment_label')}")
            print(f"      Average score: {result.get('avg_sentiment')}")
            print(f"      ✓ VADER is working")
        else:
            print(f"      ✗ No headlines scraped - web scraping selectors may be outdated")

    except ImportError:
        print("      ✗ vaderSentiment not installed. Run: pip install vaderSentiment")
    except Exception as e:
        print(f"      ✗ Error: {e}")

def test_openinsider():
    """Test OpenInsider collector"""
    print("\n" + "="*60)
    print("TESTING OPENINSIDER COLLECTOR")
    print("="*60)

    try:
        from src.collectors.openinsider import OpenInsiderCollector

        insider = OpenInsiderCollector()

        # Test cluster buys
        print("\n[1/2] Testing cluster buys...")
        url = "http://openinsider.com/latest-cluster-buys"
        print(f"      URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            table = soup.find('table', class_='tinytable')
            if table:
                rows = table.find_all('tr')
                print(f"      ✓ Found table with {len(rows)} rows")
                if len(rows) > 1:
                    print(f"      First data row has {len(rows[1].find_all('td'))} columns")
            else:
                # Try finding any table
                tables = soup.find_all('table')
                print(f"      ✗ No table with class 'tinytable' found")
                print(f"      Found {len(tables)} total tables on page")
                if tables:
                    for i, t in enumerate(tables[:3]):
                        print(f"      Table {i+1} classes: {t.get('class')}")

        except Exception as e:
            print(f"      ✗ Error: {e}")

        # Test actual collection
        print("\n[2/2] Testing actual collection...")
        trades = insider.collect_cluster_buys()
        print(f"      Trades collected: {len(trades)}")
        if trades:
            print(f"      ✓ OpenInsider is working")
            print(f"      Sample: {trades[0]['ticker']} - ${trades[0]['value']:,}")
        else:
            print(f"      ✗ No trades found - either site structure changed or no cluster buys available")

    except Exception as e:
        print(f"      ✗ Error: {e}")

def test_congress():
    """Test Congress trades collector"""
    print("\n" + "="*60)
    print("TESTING CONGRESS TRADES COLLECTOR")
    print("="*60)

    url = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
    print(f"\n[1/1] Testing House Stock Watcher API...")
    print(f"      URL: {url}")

    try:
        response = requests.get(url, timeout=30)
        print(f"      Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"      ✓ Success! {len(data)} total trades available")
            if data:
                print(f"      Sample: {data[0].get('representative')} - {data[0].get('ticker')}")
        elif response.status_code == 403:
            print(f"      ✗ 403 Forbidden - Access denied to S3 bucket")
            print(f"      This data source may have changed permissions or moved")
            print(f"      Alternative: Check https://housestockwatcher.com for new API")
        else:
            print(f"      ✗ Unexpected status code: {response.status_code}")

    except Exception as e:
        print(f"      ✗ Error: {e}")

def test_fred():
    """Test FRED collector"""
    print("\n" + "="*60)
    print("TESTING FRED COLLECTOR")
    print("="*60)

    config = load_config()
    fred_key = config.get('api_keys', {}).get('fred')

    if not fred_key or fred_key == 'YOUR_FRED_KEY':
        print("      ✗ FRED API key not configured in config.yaml")
        return

    try:
        from src.collectors.fred import FREDCollector

        fred = FREDCollector(api_key=fred_key)

        # Test each indicator with different lookback periods
        indicators_to_test = [
            ('VIXCLS', 'VIX', 30, 'Daily'),
            ('DGS10', 'Treasury 10Y', 30, 'Daily'),
            ('UNRATE', 'Unemployment', 60, 'Monthly'),  # Try 60 days for monthly data
            ('CPIAUCSL', 'Inflation (CPI)', 60, 'Monthly'),  # Try 60 days for monthly data
            ('DEXUSEU', 'USD/EUR', 30, 'Daily'),
        ]

        print("\nTesting indicators with appropriate lookback periods:")
        for series_id, name, days_back, frequency in indicators_to_test:
            print(f"\n      [{name}] ({series_id}) - {frequency} updates")
            print(f"      Looking back {days_back} days...")

            obs = fred.get_latest_observation(series_id, days_back=days_back)
            if obs:
                print(f"      ✓ Value: {obs['value']} (date: {obs['date']})")
            else:
                print(f"      ✗ No data found")
                if frequency == 'Monthly':
                    print(f"         Try increasing lookback to 90 days for monthly indicators")

    except ImportError:
        print("      ✗ FRED collector not available")
    except Exception as e:
        print(f"      ✗ Error: {e}")

def test_data_flow():
    """Test data flow through pipeline"""
    print("\n" + "="*60)
    print("TESTING DATA FLOW")
    print("="*60)

    try:
        from src.database.models import Database

        db = Database('data/sentiment.db')

        # Check recent data
        print("\n[1/5] Checking mentions...")
        mentions = db.get_recent_mentions(days=1)
        print(f"      Mentions in last 24h: {len(mentions)}")

        print("\n[2/5] Checking prices...")
        prices = db.get_latest_prices()
        print(f"      Tickers with price data: {len(prices)}")

        print("\n[3/5] Checking velocity calculations...")
        tracked = db.get_tracked_tickers(days=7)
        print(f"      Tracked tickers: {len(tracked)}")

        print("\n[4/5] Checking insider trades...")
        insiders = db.get_recent_insiders(days=30)
        print(f"      Insider trades (30d): {len(insiders)}")

        print("\n[5/5] Checking signals...")
        signals = db.get_recent_signals(days=7)
        print(f"      Signals (7d): {len(signals)}")

        print("\n      DATA FLOW SUMMARY:")
        print(f"      Mentions → Velocity: {len(mentions)} → {len(tracked)}")
        print(f"      Velocity → Signals: {len(tracked)} → {len(signals)}")

        if len(mentions) > 0 and len(tracked) == 0:
            print(f"      ⚠️  Mentions are being collected but not converted to velocity")
        if len(tracked) > 0 and len(signals) == 0:
            print(f"      ⚠️  Velocity calculated but no signals generated (may not meet thresholds)")

    except Exception as e:
        print(f"      ✗ Error: {e}")

def main():
    """Run all diagnostic tests"""
    print("\n" + "="*70)
    print("STOCK TRADER DATA PIPELINE DIAGNOSTICS")
    print(f"Timestamp: {datetime.now()}")
    print("="*70)

    test_vader_sentiment()
    test_openinsider()
    test_congress()
    test_fred()
    test_data_flow()

    print("\n" + "="*70)
    print("DIAGNOSTICS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Review failed tests above")
    print("  2. Check if web scraping selectors need updating")
    print("  3. Verify API keys are configured correctly")
    print("  4. Consider increasing FRED lookback days for monthly indicators")
    print("  5. Look for alternative Congress trades data source if 403 persists")
    print("\n")

if __name__ == "__main__":
    main()
