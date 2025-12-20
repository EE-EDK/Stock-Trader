"""
@file alphavantage.py
@brief Alpha Vantage API client for free news sentiment data
@details Free alternative to Finnhub sentiment with 100 calls/day limit
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
    @brief Free news sentiment collector from Alpha Vantage
    @details Sign up at https://www.alphavantage.co/support/#api-key (free, instant)
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str, calls_per_day: int = 100):
        """
        @brief Initialize Alpha Vantage collector
        @param api_key Alpha Vantage API key (free from alphavantage.co)
        @param calls_per_day Daily API call limit (default 100 for free tier)
        """
        self.api_key = api_key
        self.calls_per_day = calls_per_day
        self._call_count = 0
        self._delay = 12  # 12 seconds between calls = ~100 calls in 20 mins

    def collect_news_sentiment(self, tickers: List[str], limit_per_ticker: int = 50) -> List[Dict]:
        """
        @brief Fetch news sentiment for list of tickers
        @param tickers List of stock ticker symbols
        @param limit_per_ticker Number of news articles to analyze per ticker
        @return List of sentiment dictionaries
        @details Free tier: 100 calls/day, use wisely
        """
        results = []

        for ticker in tickers:
            if self._call_count >= self.calls_per_day:
                logger.warning(f"Daily API limit reached ({self.calls_per_day} calls)")
                break

            # Rate limiting - 12 seconds between calls
            if self._call_count > 0:
                time.sleep(self._delay)

            try:
                params = {
                    'function': 'NEWS_SENTIMENT',
                    'tickers': ticker,
                    'limit': limit_per_ticker,
                    'apikey': self.api_key
                }

                response = requests.get(self.BASE_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                self._call_count += 1

                # Parse sentiment data
                if 'feed' in data and data['feed']:
                    ticker_sentiment = self._calculate_aggregate_sentiment(ticker, data['feed'])
                    if ticker_sentiment:
                        results.append(ticker_sentiment)
                        logger.debug(f"Sentiment collected for {ticker}")

            except requests.RequestException as e:
                logger.error(f"Alpha Vantage API error for {ticker}: {e}")
                continue
            except (KeyError, ValueError) as e:
                logger.error(f"Data parsing error for {ticker}: {e}")
                continue

        logger.info(f"Collected sentiment for {len(results)} tickers ({self._call_count} API calls used)")
        return results

    def _calculate_aggregate_sentiment(self, ticker: str, news_feed: List[Dict]) -> Optional[Dict]:
        """
        @brief Calculate aggregate sentiment from news articles
        @param ticker Stock ticker symbol
        @param news_feed List of news articles with sentiment
        @return Aggregated sentiment dictionary
        """
        if not news_feed:
            return None

        sentiment_scores = []
        relevance_scores = []
        total_articles = len(news_feed)

        for article in news_feed:
            # Find ticker-specific sentiment in article
            ticker_sentiments = article.get('ticker_sentiment', [])
            for ts in ticker_sentiments:
                if ts.get('ticker', '').upper() == ticker.upper():
                    try:
                        sentiment_score = float(ts.get('ticker_sentiment_score', 0))
                        relevance = float(ts.get('relevance_score', 0))

                        sentiment_scores.append(sentiment_score)
                        relevance_scores.append(relevance)
                    except (ValueError, TypeError):
                        continue

        if not sentiment_scores:
            return None

        # Calculate weighted average sentiment
        if relevance_scores:
            weighted_sentiment = sum(s * r for s, r in zip(sentiment_scores, relevance_scores))
            total_relevance = sum(relevance_scores)
            avg_sentiment = weighted_sentiment / total_relevance if total_relevance > 0 else 0
        else:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)

        # Convert to 0-1 scale (Alpha Vantage uses -1 to 1)
        normalized_sentiment = (avg_sentiment + 1) / 2

        # Calculate bullish/bearish percentages
        positive_count = sum(1 for s in sentiment_scores if s > 0.05)
        negative_count = sum(1 for s in sentiment_scores if s < -0.05)
        total_scored = len(sentiment_scores)

        return {
            'ticker': ticker,
            'news_sentiment': normalized_sentiment,
            'bullish_pct': positive_count / total_scored if total_scored > 0 else 0,
            'bearish_pct': negative_count / total_scored if total_scored > 0 else 0,
            'articles_analyzed': total_articles,
            'sentiment_score_raw': avg_sentiment,  # -1 to 1 scale
            'collected_at': datetime.now()
        }

    def get_top_gainers_losers(self) -> Dict:
        """
        @brief Get top gainers and losers (free endpoint, no authentication needed)
        @return Dictionary with top gainers, losers, and most actively traded
        """
        try:
            params = {
                'function': 'TOP_GAINERS_LOSERS',
                'apikey': self.api_key
            }

            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            self._call_count += 1
            logger.info("Retrieved top gainers/losers")

            return {
                'top_gainers': data.get('top_gainers', []),
                'top_losers': data.get('top_losers', []),
                'most_active': data.get('most_actively_traded', []),
                'collected_at': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error fetching top gainers/losers: {e}")
            return {}

    def reset_call_count(self):
        """
        @brief Reset daily API call counter
        @details Call this at the start of each day
        """
        self._call_count = 0
        logger.info("API call counter reset")
