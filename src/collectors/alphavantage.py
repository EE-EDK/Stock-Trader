"""
@file alphavantage.py
@brief Alpha Vantage API client for news sentiment data
@details FREE alternative to Finnhub sentiment - 100 API calls/day
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)


class AlphaVantageCollector:
    """
    @class AlphaVantageCollector
    @brief API client for Alpha Vantage news sentiment
    @details Free tier: 100 API calls/day - perfect for sentiment analysis
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str, rate_limit: int = 5):
        """
        @brief Initialize Alpha Vantage collector
        @param api_key Alpha Vantage API key (free from alphavantage.co)
        @param rate_limit Maximum requests per minute (default 5 for free tier)
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._request_count = 0
        self._minute_start = time.time()

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

    def _get(self, params: Dict) -> Dict:
        """
        @brief Make rate-limited GET request to Alpha Vantage API
        @param params Query parameters (apikey is added automatically)
        @return JSON response as dictionary
        @throws requests.RequestException on API errors
        """
        self._rate_limit_wait()

        params['apikey'] = self.api_key

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Check for API limit message
            if 'Information' in data or 'Note' in data:
                logger.warning(f"Alpha Vantage API limit reached: {data}")
                return {}

            return data
        except requests.RequestException as e:
            logger.error(f"Alpha Vantage API error: {e}")
            return {}
        except ValueError as e:
            logger.error(f"Invalid JSON response from Alpha Vantage: {e}")
            return {}

    def collect_news_sentiment(self, tickers: List[str], limit_per_ticker: int = 50) -> List[Dict]:
        """
        @brief Fetch news sentiment data for list of tickers
        @param tickers List of stock ticker symbols
        @param limit_per_ticker Maximum news items to analyze per ticker
        @return List of sentiment dictionaries

        Example response:
        {
            'ticker': 'AAPL',
            'sentiment_score': 0.25,  # -1 (bearish) to 1 (bullish)
            'sentiment_label': 'Somewhat-Bullish',
            'relevance_score': 0.8,
            'ticker_sentiment_score': 0.35,
            'articles_analyzed': 50,
            'collected_at': datetime.now()
        }
        """
        results = []

        for ticker in tickers:
            try:
                data = self._get({
                    'function': 'NEWS_SENTIMENT',
                    'tickers': ticker,
                    'limit': limit_per_ticker
                })

                if not data or 'feed' not in data:
                    logger.warning(f"No news sentiment data for {ticker}")
                    continue

                feed = data.get('feed', [])
                if not feed:
                    continue

                # Calculate aggregate sentiment
                ticker_sentiments = []
                relevance_scores = []
                overall_sentiments = []

                for article in feed:
                    # Extract ticker-specific sentiment
                    ticker_sentiment_data = article.get('ticker_sentiment', [])
                    for ts in ticker_sentiment_data:
                        if ts.get('ticker') == ticker:
                            ticker_sentiments.append(float(ts.get('ticker_sentiment_score', 0)))
                            relevance_scores.append(float(ts.get('relevance_score', 0)))

                    # Also track overall article sentiment
                    overall = article.get('overall_sentiment_score', 0)
                    if overall:
                        overall_sentiments.append(float(overall))

                if ticker_sentiments:
                    # Weighted average by relevance
                    if relevance_scores:
                        weighted_sentiment = sum(s * r for s, r in zip(ticker_sentiments, relevance_scores)) / sum(relevance_scores)
                    else:
                        weighted_sentiment = sum(ticker_sentiments) / len(ticker_sentiments)

                    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
                    avg_overall = sum(overall_sentiments) / len(overall_sentiments) if overall_sentiments else 0

                    # Convert score to label
                    sentiment_label = self._score_to_label(weighted_sentiment)

                    results.append({
                        'ticker': ticker,
                        'sentiment_score': round(weighted_sentiment, 3),
                        'sentiment_label': sentiment_label,
                        'relevance_score': round(avg_relevance, 3),
                        'overall_sentiment': round(avg_overall, 3),
                        'articles_analyzed': len(feed),
                        'collected_at': datetime.now()
                    })

                    logger.debug(f"{ticker}: sentiment={weighted_sentiment:.3f} ({sentiment_label}), relevance={avg_relevance:.3f}, articles={len(feed)}")

            except Exception as e:
                logger.error(f"Error processing news sentiment for {ticker}: {e}")
                continue

        logger.info(f"Collected news sentiment for {len(results)}/{len(tickers)} tickers")
        return results

    def _score_to_label(self, score: float) -> str:
        """
        @brief Convert sentiment score to human-readable label
        @param score Sentiment score from -1 to 1
        @return Sentiment label
        """
        if score >= 0.35:
            return 'Bullish'
        elif score >= 0.15:
            return 'Somewhat-Bullish'
        elif score > -0.15:
            return 'Neutral'
        elif score > -0.35:
            return 'Somewhat-Bearish'
        else:
            return 'Bearish'

    def get_top_gainers_losers(self) -> Dict:
        """
        @brief Get market top gainers, losers, and most active tickers
        @return Dictionary with market movers
        @note This uses 1 API call and provides great market overview
        """
        data = self._get({'function': 'TOP_GAINERS_LOSERS'})

        if not data:
            return {}

        result = {
            'top_gainers': [],
            'top_losers': [],
            'most_actively_traded': [],
            'collected_at': datetime.now()
        }

        # Process gainers
        for item in data.get('top_gainers', [])[:10]:
            result['top_gainers'].append({
                'ticker': item.get('ticker'),
                'price': float(item.get('price', 0)),
                'change_amount': float(item.get('change_amount', 0)),
                'change_percentage': item.get('change_percentage', '0%'),
                'volume': int(item.get('volume', 0))
            })

        # Process losers
        for item in data.get('top_losers', [])[:10]:
            result['top_losers'].append({
                'ticker': item.get('ticker'),
                'price': float(item.get('price', 0)),
                'change_amount': float(item.get('change_amount', 0)),
                'change_percentage': item.get('change_percentage', '0%'),
                'volume': int(item.get('volume', 0))
            })

        # Process most active
        for item in data.get('most_actively_traded', [])[:10]:
            result['most_actively_traded'].append({
                'ticker': item.get('ticker'),
                'price': float(item.get('price', 0)),
                'change_amount': float(item.get('change_amount', 0)),
                'change_percentage': item.get('change_percentage', '0%'),
                'volume': int(item.get('volume', 0))
            })

        logger.info(f"Collected market movers: {len(result['top_gainers'])} gainers, {len(result['top_losers'])} losers")
        return result
