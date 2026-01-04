"""
@file finnhub.py
@brief Finnhub API client for price and sentiment data
@details Collects stock prices, news sentiment, and market data from Finnhub API with rate limiting
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)


class FinnhubCollector:
    """
    @class FinnhubCollector
    @brief API client for Finnhub market data
    @details Fetches price quotes and sentiment data with automatic rate limiting
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str, rate_limit: int = 55):
        """
        @brief Initialize Finnhub collector
        @param api_key Finnhub API key
        @param rate_limit Maximum requests per minute (default 55 for free tier)
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._request_count = 0
        self._minute_start = time.time()
        self._sentiment_endpoint_forbidden = False  # Track if sentiment endpoint is unavailable

    def _rate_limit_wait(self):
        """
        @brief Implement rate limiting to stay under API limits
        @details Tracks requests per minute and sleeps if limit is reached
        """
        self._request_count += 1
        elapsed = time.time() - self._minute_start

        if elapsed < 60 and self._request_count >= self.rate_limit:
            sleep_time = 60 - elapsed + 1
            logger.debug(f"Rate limit reached, sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self._request_count = 0
            self._minute_start = time.time()
        elif elapsed >= 60:
            # Reset counter after 1 minute
            self._request_count = 1
            self._minute_start = time.time()

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        @brief Make rate-limited GET request to Finnhub API
        @param endpoint API endpoint path
        @param params Query parameters (token is added automatically)
        @return JSON response as dictionary
        @throws requests.RequestException on API errors
        """
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
        except requests.exceptions.HTTPError as e:
            # Re-raise 403 errors so caller can handle paid-tier limitations
            if e.response.status_code == 403:
                raise
            logger.error(f"Finnhub API error for {endpoint}: {e}")
            return {}
        except requests.RequestException as e:
            logger.error(f"Finnhub API error for {endpoint}: {e}")
            return {}
        except ValueError as e:
            logger.error(f"Invalid JSON response from Finnhub: {e}")
            return {}

    def collect_quotes(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Fetch current price quotes for list of tickers
        @param tickers List of stock ticker symbols
        @return List of quote dictionaries with price data
        """
        results = []

        for ticker in tickers:
            data = self._get('quote', {'symbol': ticker})

            if data and 'c' in data:
                prev_close = data.get('pc', 0)
                current = data.get('c', 0)

                # Calculate percentage change
                change_pct = 0.0
                if prev_close is not None and prev_close > 0:
                    change_pct = ((current - prev_close) / prev_close) * 100

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
            else:
                logger.warning(f"No quote data for {ticker}")

        logger.info(f"Collected quotes for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_sentiment(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Fetch news sentiment data for list of tickers
        @param tickers List of stock ticker symbols
        @return List of sentiment dictionaries
        @note Sentiment endpoint requires paid Finnhub plan - gracefully skips if forbidden
        """
        results = []

        # Skip if we've already detected this endpoint is forbidden
        if self._sentiment_endpoint_forbidden:
            logger.info("Sentiment endpoint unavailable (requires paid plan) - skipping")
            return results

        for ticker in tickers:
            try:
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
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    # Sentiment endpoint requires paid plan
                    self._sentiment_endpoint_forbidden = True
                    logger.warning(f"Sentiment endpoint requires paid Finnhub plan - skipping remaining tickers")
                    break

        if results:
            logger.info(f"Collected sentiment for {len(results)}/{len(tickers)} tickers")
        elif not self._sentiment_endpoint_forbidden:
            logger.warning("No sentiment data collected")

        return results

    def collect_social_sentiment(self, ticker: str) -> Optional[Dict]:
        """
        @brief Fetch social media sentiment (social media) for a ticker
        @param ticker Stock ticker symbol
        @return Dictionary with social sentiment or None
        @note This endpoint may have limited data for free tier
        """
        data = self._get('stock/social-sentiment', {'symbol': ticker})

        if not data:
            return None

        # Extract Reddit data if available
                'twitter_mentions': twitter_data[0].get('mention', 0) if twitter_data else 0,
                'twitter_score': twitter_data[0].get('score', 0) if twitter_data else 0,
                'collected_at': datetime.now()
            }

        return None

    def get_company_profile(self, ticker: str) -> Optional[Dict]:
        """
        @brief Get basic company information
        @param ticker Stock ticker symbol
        @return Dictionary with company profile or None
        """
        data = self._get('stock/profile2', {'symbol': ticker})

        if data and 'name' in data:
            return {
                'ticker': ticker,
                'name': data.get('name'),
                'country': data.get('country'),
                'exchange': data.get('exchange'),
                'industry': data.get('finnhubIndustry'),
                'market_cap': data.get('marketCapitalization'),
                'collected_at': datetime.now()
            }

        return None

    def combine_price_and_sentiment(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Collect both price and sentiment data in one call per ticker
        @param tickers List of stock ticker symbols
        @return List of combined price/sentiment dictionaries
        @details More efficient than calling collect_quotes and collect_sentiment separately
        """
        combined_results = []

        quotes = self.collect_quotes(tickers)
        sentiments = self.collect_sentiment(tickers)

        # Create lookup dict for sentiments
        sentiment_lookup = {s['ticker']: s for s in sentiments}

        for quote in quotes:
            ticker = quote['ticker']
            combined = quote.copy()

            # Merge sentiment data if available
            if ticker in sentiment_lookup:
                sentiment = sentiment_lookup[ticker]
                combined.update({
                    'news_sentiment': sentiment['news_sentiment'],
                    'bullish_pct': sentiment['bullish_pct'],
                    'bearish_pct': sentiment['bearish_pct'],
                    'buzz_score': sentiment['buzz_score'],
                    'articles_week': sentiment['articles_week']
                })

            combined_results.append(combined)

        return combined_results
