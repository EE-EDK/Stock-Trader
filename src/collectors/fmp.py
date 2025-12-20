"""
@file fmp.py
@brief Financial Modeling Prep API client
@details FREE tier: 250 API calls/day for financial data
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)


class FMPCollector:
    """
    @class FMPCollector
    @brief Financial Modeling Prep API client
    @details Free tier: 250 calls/day - earnings, analyst ratings, SEC filings
    """

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str, rate_limit: int = 250):
        """
        @brief Initialize FMP collector
        @param api_key FMP API key (free from financialmodelingprep.com)
        @param rate_limit Maximum requests per day (default 250 for free tier)
        """
        self.api_key = api_key
        self.rate_limit = rate_limit
        self._request_count = 0

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        @brief Make GET request to FMP API
        @param endpoint API endpoint path
        @param params Query parameters (apikey is added automatically)
        @return JSON response as dictionary
        """
        if params is None:
            params = {}
        params['apikey'] = self.api_key

        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            self._request_count += 1
            return response.json()
        except requests.RequestException as e:
            logger.error(f"FMP API error for {endpoint}: {e}")
            return {}
        except ValueError as e:
            logger.error(f"Invalid JSON response from FMP: {e}")
            return {}

    def collect_earnings_calendar(self, from_date: str, to_date: str) -> List[Dict]:
        """
        @brief Fetch earnings calendar for date range
        @param from_date Start date (YYYY-MM-DD)
        @param to_date End date (YYYY-MM-DD)
        @return List of earnings events
        """
        data = self._get('earning_calendar', {'from': from_date, 'to': to_date})

        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            results.append({
                'ticker': item.get('symbol'),
                'date': item.get('date'),
                'eps_estimated': item.get('epsEstimated'),
                'eps_actual': item.get('eps'),
                'revenue_estimated': item.get('revenueEstimated'),
                'revenue_actual': item.get('revenue'),
                'time': item.get('time'),
                'collected_at': datetime.now()
            })

        logger.info(f"Collected {len(results)} earnings events")
        return results

    def collect_analyst_estimates(self, ticker: str) -> Optional[Dict]:
        """
        @brief Fetch analyst estimates for a ticker
        @param ticker Stock ticker symbol
        @return Dictionary with analyst estimates
        """
        data = self._get(f'analyst-estimates/{ticker}')

        if not isinstance(data, list) or not data:
            return None

        latest = data[0]
        return {
            'ticker': ticker,
            'date': latest.get('date'),
            'estimated_revenue_low': latest.get('estimatedRevenueLow'),
            'estimated_revenue_high': latest.get('estimatedRevenueHigh'),
            'estimated_revenue_avg': latest.get('estimatedRevenueAvg'),
            'estimated_ebitda_low': latest.get('estimatedEbitdaLow'),
            'estimated_ebitda_high': latest.get('estimatedEbitdaHigh'),
            'estimated_ebitda_avg': latest.get('estimatedEbitdaAvg'),
            'estimated_eps_low': latest.get('estimatedEpsLow'),
            'estimated_eps_high': latest.get('estimatedEpsHigh'),
            'estimated_eps_avg': latest.get('estimatedEpsAvg'),
            'num_analysts': latest.get('numberAnalystsEstimatedRevenue'),
            'collected_at': datetime.now()
        }

    def collect_stock_news(self, tickers: List[str], limit: int = 50) -> List[Dict]:
        """
        @brief Fetch recent stock news
        @param tickers List of stock ticker symbols
        @param limit Number of news items per ticker
        @return List of news articles
        """
        results = []

        for ticker in tickers:
            data = self._get(f'stock_news', {'tickers': ticker, 'limit': limit})

            if not isinstance(data, list):
                continue

            for article in data:
                results.append({
                    'ticker': ticker,
                    'published_date': article.get('publishedDate'),
                    'title': article.get('title'),
                    'text': article.get('text', '')[:500],  # First 500 chars
                    'site': article.get('site'),
                    'url': article.get('url'),
                    'collected_at': datetime.now()
                })

        logger.info(f"Collected {len(results)} news articles")
        return results

    def collect_sec_filings(self, ticker: str, filing_type: str = '10-K', limit: int = 10) -> List[Dict]:
        """
        @brief Fetch SEC filings for a ticker
        @param ticker Stock ticker symbol
        @param filing_type Type of filing (10-K, 10-Q, 8-K, etc.)
        @param limit Number of filings to retrieve
        @return List of SEC filings
        """
        data = self._get(f'sec_filings/{ticker}', {'type': filing_type, 'limit': limit})

        if not isinstance(data, list):
            return []

        results = []
        for filing in data:
            results.append({
                'ticker': ticker,
                'filing_type': filing.get('type'),
                'filing_date': filing.get('fillingDate'),
                'accepted_date': filing.get('acceptedDate'),
                'link': filing.get('link'),
                'final_link': filing.get('finalLink'),
                'collected_at': datetime.now()
            })

        logger.info(f"Collected {len(results)} SEC filings for {ticker}")
        return results

    def collect_price_target(self, ticker: str) -> Optional[Dict]:
        """
        @brief Fetch analyst price targets
        @param ticker Stock ticker symbol
        @return Dictionary with price target data
        """
        data = self._get(f'price-target/{ticker}')

        if not isinstance(data, list) or not data:
            return None

        latest = data[0]
        return {
            'ticker': ticker,
            'published_date': latest.get('publishedDate'),
            'analyst_name': latest.get('analystName'),
            'analyst_company': latest.get('analystCompany'),
            'price_target': latest.get('priceTarget'),
            'adj_price_target': latest.get('adjPriceTarget'),
            'price_when_posted': latest.get('priceWhenPosted'),
            'news_publisher': latest.get('newsPublisher'),
            'news_title': latest.get('newsTitle'),
            'collected_at': datetime.now()
        }

    def close(self):
        """Cleanup method (no-op for FMP)"""
        pass
