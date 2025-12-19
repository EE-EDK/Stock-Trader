"""
@file reddit_collector.py
@brief Reddit data collector using PRAW (Python Reddit API Wrapper)
@details FREE API access - scrape r/wallstreetbets, r/stocks, r/investing
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logger.warning("praw not installed - run: pip install praw")


class RedditCollector:
    """
    @class RedditCollector
    @brief Collect stock mentions and sentiment from Reddit
    @details Free API access to r/wallstreetbets, r/stocks, r/investing
    """

    STOCK_SUBREDDITS = ['wallstreetbets', 'stocks', 'investing', 'StockMarket']

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        @brief Initialize Reddit collector
        @param client_id Reddit app client ID
        @param client_secret Reddit app client secret
        @param user_agent User agent string (e.g., "stock-tracker:v1.0 (by u/yourusername)")

        Get credentials at: https://www.reddit.com/prefs/apps
        """
        if not PRAW_AVAILABLE:
            raise ImportError("praw package not installed. Install with: pip install praw")

        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )

    def collect_ticker_mentions(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        @brief Collect stock ticker mentions from Reddit
        @param hours Hours to look back
        @param limit Maximum posts to analyze per subreddit
        @return List of ticker mention dictionaries
        """
        ticker_counts = Counter()
        ticker_posts = {}  # Store example posts for each ticker

        cutoff_time = datetime.now() - timedelta(hours=hours)

        for subreddit_name in self.STOCK_SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                for post in subreddit.new(limit=limit):
                    # Check if post is recent enough
                    post_time = datetime.fromtimestamp(post.created_utc)
                    if post_time < cutoff_time:
                        continue

                    # Extract tickers from title and body
                    text = f"{post.title} {post.selftext}"
                    tickers = self._extract_tickers(text)

                    for ticker in tickers:
                        ticker_counts[ticker] += 1

                        # Store example post
                        if ticker not in ticker_posts:
                            ticker_posts[ticker] = {
                                'title': post.title,
                                'subreddit': subreddit_name,
                                'score': post.score,
                                'url': f"https://reddit.com{post.permalink}"
                            }

                logger.info(f"Processed {limit} posts from r/{subreddit_name}")

            except Exception as e:
                logger.error(f"Error collecting from r/{subreddit_name}: {e}")
                continue

        # Convert to list of dictionaries
        results = []
        for ticker, count in ticker_counts.most_common(100):
            example_post = ticker_posts.get(ticker, {})
            results.append({
                'ticker': ticker,
                'mention_count': count,
                'example_title': example_post.get('title', ''),
                'example_subreddit': example_post.get('subreddit', ''),
                'example_score': example_post.get('score', 0),
                'example_url': example_post.get('url', ''),
                'lookback_hours': hours,
                'collected_at': datetime.now()
            })

        logger.info(f"Collected {len(results)} unique ticker mentions from Reddit")
        return results

    def collect_subreddit_sentiment(self, ticker: str, subreddit_name: str = 'wallstreetbets',
                                   limit: int = 50) -> Dict:
        """
        @brief Analyze sentiment for a specific ticker in a subreddit
        @param ticker Stock ticker symbol
        @param subreddit_name Subreddit to analyze
        @param limit Maximum posts to analyze
        @return Dictionary with sentiment metrics
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            search_query = f"{ticker}"

            posts = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            total_score = 0

            for post in subreddit.search(search_query, limit=limit, time_filter='week'):
                posts.append({
                    'title': post.title,
                    'score': post.score,
                    'num_comments': post.num_comments,
                    'created': datetime.fromtimestamp(post.created_utc)
                })

                total_score += post.score

                # Simple sentiment based on score and comments
                if post.score > 100 or post.num_comments > 50:
                    positive_count += 1
                elif post.score < 0:
                    negative_count += 1
                else:
                    neutral_count += 1

            if not posts:
                return self._empty_sentiment(ticker, subreddit_name)

            avg_score = total_score / len(posts)
            avg_comments = sum(p['num_comments'] for p in posts) / len(posts)

            return {
                'ticker': ticker,
                'subreddit': subreddit_name,
                'total_posts': len(posts),
                'avg_score': round(avg_score, 2),
                'avg_comments': round(avg_comments, 2),
                'positive_posts': positive_count,
                'negative_posts': negative_count,
                'neutral_posts': neutral_count,
                'positive_pct': round((positive_count / len(posts)) * 100, 1),
                'sentiment_signal': self._classify_reddit_sentiment(positive_count, negative_count, len(posts)),
                'collected_at': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {ticker} in r/{subreddit_name}: {e}")
            return self._empty_sentiment(ticker, subreddit_name)

    def collect_trending_tickers(self, subreddit_name: str = 'wallstreetbets',
                                limit: int = 100) -> List[Dict]:
        """
        @brief Get currently trending tickers in a subreddit
        @param subreddit_name Subreddit to analyze
        @param limit Number of hot posts to analyze
        @return List of trending tickers with mention counts
        """
        ticker_counts = Counter()

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            for post in subreddit.hot(limit=limit):
                text = f"{post.title} {post.selftext}"
                tickers = self._extract_tickers(text)

                for ticker in tickers:
                    ticker_counts[ticker] += 1

            results = []
            for ticker, count in ticker_counts.most_common(20):
                results.append({
                    'ticker': ticker,
                    'mention_count': count,
                    'subreddit': subreddit_name,
                    'collected_at': datetime.now()
                })

            logger.info(f"Found {len(results)} trending tickers in r/{subreddit_name}")
            return results

        except Exception as e:
            logger.error(f"Error collecting trending tickers from r/{subreddit_name}: {e}")
            return []

    def _extract_tickers(self, text: str) -> List[str]:
        """
        @brief Extract stock ticker symbols from text
        @param text Text to search for tickers
        @return List of unique ticker symbols
        """
        import re

        # Find all potential tickers (1-5 uppercase letters preceded by $ or space)
        pattern = r'\$([A-Z]{1,5})\b|\s([A-Z]{2,5})\b'
        matches = re.findall(pattern, text.upper())

        # Flatten the tuple results
        tickers = [m[0] or m[1] for m in matches]

        # Filter out common false positives
        blacklist = {'THE', 'AND', 'FOR', 'ARE', 'NOT', 'BUT', 'WITH', 'THIS', 'THAT',
                    'FROM', 'HAVE', 'MORE', 'BEEN', 'WILL', 'WHEN', 'WHAT', 'THERE',
                    'THEIR', 'WHICH', 'THAN', 'THEM', 'THESE', 'WOULD', 'COULD',
                    'EDIT', 'TLDR', 'IMO', 'YOLO', 'FOMO', 'WSB', 'DD', 'TO', 'BE', 'OF',
                    'AT', 'BY', 'ON', 'UP', 'OUT', 'IF', 'ABOUT', 'INTO', 'SUCH', 'ONLY'}

        filtered = [t for t in tickers if t not in blacklist and len(t) >= 2]

        return list(set(filtered))  # Return unique tickers

    def _classify_reddit_sentiment(self, positive: int, negative: int, total: int) -> str:
        """Classify Reddit sentiment based on post distribution"""
        if total == 0:
            return 'neutral'

        positive_pct = (positive / total) * 100

        if positive_pct >= 60:
            return 'bullish'
        elif positive_pct >= 40:
            return 'neutral'
        else:
            return 'bearish'

    def _empty_sentiment(self, ticker: str, subreddit: str) -> Dict:
        """Return empty sentiment result"""
        return {
            'ticker': ticker,
            'subreddit': subreddit,
            'total_posts': 0,
            'avg_score': 0,
            'avg_comments': 0,
            'positive_posts': 0,
            'negative_posts': 0,
            'neutral_posts': 0,
            'positive_pct': 0,
            'sentiment_signal': 'neutral',
            'collected_at': datetime.now()
        }

    def close(self):
        """Cleanup method (no-op for PRAW)"""
        pass
