"""
@file apewisdom.py
@brief ApeWisdom social mention data collector
@details Collects stock mention data from ApeWisdom API tracking social media
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ApeWisdomCollector:
    """
    @class ApeWisdomCollector
    @brief Collector for social mention data from ApeWisdom
    @details Fetches trending stock mentions from social media platforms
    """

    BASE_URL = "https://apewisdom.io/api/v1.0"

    def __init__(self, timeout: int = 30):
        """
        @brief Initialize ApeWisdom collector
        @param timeout Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SentimentVelocityTracker/1.0',
            'Accept': 'application/json'
        })

    def collect(self, top_n: int = 100) -> List[Dict]:
        """
        @brief Fetch top mentioned stocks from ApeWisdom
        @param top_n Number of top tickers to return
        @return List of dictionaries containing ticker mention data
        @throws requests.RequestException on API errors
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/filter/all-stocks",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get('results', [])[:top_n]:
                # Validate required fields
                if not item.get('ticker'):
                    continue

                results.append({
                    'ticker': item.get('ticker', '').upper().strip(),
                    'mentions': item.get('mentions', 0),
                    'upvotes': item.get('upvotes', 0),
                    'rank': item.get('rank', 0),
                    'mentions_24h_ago': item.get('mentions_24h_ago', 0),
                    'rank_24h_ago': item.get('rank_24h_ago', 0),
                    'collected_at': datetime.now(),
                    'source': 'apewisdom'
                })

            logger.info(f"Successfully collected {len(results)} mentions from ApeWisdom")
            return results

        except requests.RequestException as e:
            logger.error(f"ApeWisdom API error: {e}")
            return []
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"ApeWisdom data parsing error: {e}")
            return []

    def get_ticker_details(self, ticker: str) -> Optional[Dict]:
        """
        @brief Get detailed information for a specific ticker
        @param ticker Stock ticker symbol
        @return Dictionary with ticker details or None if not found
        """
        try:
            # Note: This endpoint may not exist in the current API
            # Keeping for future extensibility
            response = self.session.get(
                f"{self.BASE_URL}/filter/{ticker.upper()}",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            if data:
                return {
                    'ticker': ticker.upper(),
                    'mentions': data.get('mentions', 0),
                    'upvotes': data.get('upvotes', 0),
                    'rank': data.get('rank', 0),
                    'collected_at': datetime.now()
                }

        except requests.RequestException as e:
            logger.warning(f"Could not fetch details for {ticker}: {e}")

        return None

    def close(self):
        """
        @brief Close the session and cleanup resources
        """
        if self.session:
            self.session.close()
