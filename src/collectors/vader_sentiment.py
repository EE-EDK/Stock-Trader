"""
@file vader_sentiment.py
@brief Local sentiment analysis using VADER (Valence Aware Dictionary and sEntiment Reasoner)
@details 100% offline, no API calls - analyze scraped headlines locally
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("vaderSentiment not installed - run: pip install vaderSentiment")


class VaderSentimentAnalyzer:
    """
    @class VaderSentimentAnalyzer
    @brief Local sentiment analysis with VADER
    @details 100% free, offline sentiment analysis of news headlines
    """

    def __init__(self):
        """
        @brief Initialize VADER sentiment analyzer
        @note No API key required - fully local analysis
        """
        if not VADER_AVAILABLE:
            raise ImportError("vaderSentiment package not installed. Install with: pip install vaderSentiment")

        self.analyzer = SentimentIntensityAnalyzer()

    def analyze_text(self, text: str) -> Dict:
        """
        @brief Analyze sentiment of a single text
        @param text Text to analyze (headline, tweet, etc.)
        @return Dictionary with sentiment scores
        """
        scores = self.analyzer.polarity_scores(text)

        return {
            'text': text,
            'compound': scores['compound'],  # -1 (negative) to 1 (positive)
            'positive': scores['pos'],
            'neutral': scores['neu'],
            'negative': scores['neg'],
            'sentiment_label': self._classify_sentiment(scores['compound']),
            'analyzed_at': datetime.now()
        }

    def analyze_headlines(self, headlines: List[str]) -> Dict:
        """
        @brief Analyze sentiment of multiple headlines
        @param headlines List of news headlines
        @return Aggregate sentiment dictionary
        """
        if not headlines:
            return self._empty_result()

        scores = [self.analyzer.polarity_scores(h)['compound'] for h in headlines]

        avg_score = sum(scores) / len(scores)
        positive_count = sum(1 for s in scores if s > 0.05)
        negative_count = sum(1 for s in scores if s < -0.05)
        neutral_count = len(scores) - positive_count - negative_count

        return {
            'avg_sentiment': round(avg_score, 3),
            'sentiment_label': self._classify_sentiment(avg_score),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'total_headlines': len(headlines),
            'positive_pct': round((positive_count / len(headlines)) * 100, 1),
            'negative_pct': round((negative_count / len(headlines)) * 100, 1),
            'analyzed_at': datetime.now()
        }

    def scrape_google_news(self, ticker: str, company_name: str = None, max_headlines: int = 20) -> List[str]:
        """
        @brief Scrape headlines from Google News
        @param ticker Stock ticker symbol
        @param company_name Company name for better search results
        @param max_headlines Maximum number of headlines to scrape
        @return List of headline strings
        @note Google News frequently changes structure - may need selector updates
        """
        search_query = company_name if company_name else ticker
        url = f"https://news.google.com/search?q={search_query}+stock"

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = []

            # Try multiple selectors as Google News structure changes frequently
            # Method 1: Try finding article elements with links
            articles = soup.find_all('article')
            if articles:
                for article in articles[:max_headlines]:
                    # Try different link classes
                    for link_class in ['gPFEn', 'JtKRv', 'VDXfz']:
                        headline_tag = article.find('a', class_=link_class)
                        if headline_tag and headline_tag.get_text().strip():
                            headlines.append(headline_tag.get_text().strip())
                            break
                    # If no class works, try any link in article
                    if not headline_tag:
                        any_link = article.find('a')
                        if any_link and any_link.get_text().strip():
                            headlines.append(any_link.get_text().strip())

            # Method 2: If no articles, try h3/h4 tags (fallback)
            if not headlines:
                for tag_name in ['h3', 'h4']:
                    tags = soup.find_all(tag_name)
                    for tag in tags[:max_headlines]:
                        text = tag.get_text().strip()
                        if text and len(text) > 10:  # Filter out short strings
                            headlines.append(text)
                    if headlines:
                        break

            logger.info(f"Scraped {len(headlines)} headlines for {ticker}")
            return headlines

        except Exception as e:
            logger.error(f"Error scraping Google News for {ticker}: {e}")
            return []

    def scrape_yahoo_finance_news(self, ticker: str, max_headlines: int = 20) -> List[str]:
        """
        @brief Scrape headlines from Yahoo Finance
        @param ticker Stock ticker symbol
        @param max_headlines Maximum number of headlines to scrape
        @return List of headline strings
        @note Yahoo Finance structure changes frequently - using flexible selectors
        """
        url = f"https://finance.yahoo.com/quote/{ticker}"

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = []

            # Try multiple methods to extract headlines
            # Method 1: Try specific news section classes
            for h3_class in ['Mb(5px)', 'clamp']:
                h3_tags = soup.find_all('h3', class_=h3_class)
                if h3_tags:
                    for h3 in h3_tags[:max_headlines]:
                        text = h3.get_text().strip()
                        if text and len(text) > 10:
                            headlines.append(text)
                    break

            # Method 2: If method 1 failed, try all h3 tags and filter by content
            if not headlines:
                all_h3 = soup.find_all('h3')
                for h3 in all_h3[:max_headlines * 2]:  # Check more since we're filtering
                    text = h3.get_text().strip()
                    # Filter out navigation/UI elements (too short or common UI text)
                    if (text and
                        len(text) > 15 and
                        len(text) < 200 and
                        'News' not in text and
                        'Yahoo' not in text and
                        'Finance' not in text):
                        headlines.append(text)
                        if len(headlines) >= max_headlines:
                            break

            # Method 3: Try news stream items
            if not headlines:
                news_items = soup.find_all('li', class_='stream-item')
                for item in news_items[:max_headlines]:
                    h3 = item.find('h3')
                    if h3:
                        text = h3.get_text().strip()
                        if text:
                            headlines.append(text)

            logger.info(f"Scraped {len(headlines)} headlines from Yahoo Finance for {ticker}")
            return headlines

        except Exception as e:
            logger.error(f"Error scraping Yahoo Finance for {ticker}: {e}")
            return []

    def analyze_ticker_sentiment(self, ticker: str, company_name: str = None) -> Dict:
        """
        @brief Complete sentiment analysis for a ticker
        @param ticker Stock ticker symbol
        @param company_name Optional company name for better scraping
        @return Dictionary with comprehensive sentiment analysis
        """
        # Scrape headlines from multiple sources
        google_headlines = self.scrape_google_news(ticker, company_name)
        yahoo_headlines = self.scrape_yahoo_finance_news(ticker)

        all_headlines = google_headlines + yahoo_headlines

        if not all_headlines:
            logger.warning(f"No headlines found for {ticker}")
            return self._empty_result(ticker)

        # Analyze sentiment
        sentiment = self.analyze_headlines(all_headlines)
        sentiment['ticker'] = ticker
        sentiment['sources'] = {
            'google_news': len(google_headlines),
            'yahoo_finance': len(yahoo_headlines)
        }

        return sentiment

    def _classify_sentiment(self, compound_score: float) -> str:
        """
        @brief Classify compound score into sentiment label
        @param compound_score VADER compound score (-1 to 1)
        @return Sentiment label
        """
        if compound_score >= 0.5:
            return 'very_positive'
        elif compound_score >= 0.05:
            return 'positive'
        elif compound_score > -0.05:
            return 'neutral'
        elif compound_score > -0.5:
            return 'negative'
        else:
            return 'very_negative'

    def _empty_result(self, ticker: str = None) -> Dict:
        """Return empty sentiment result"""
        result = {
            'avg_sentiment': 0,
            'sentiment_label': 'neutral',
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'total_headlines': 0,
            'positive_pct': 0,
            'negative_pct': 0,
            'analyzed_at': datetime.now()
        }
        if ticker:
            result['ticker'] = ticker
        return result

    def close(self):
        """Cleanup method (no-op for VADER)"""
        pass
