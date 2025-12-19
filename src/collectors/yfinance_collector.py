"""
@file yfinance_collector.py
@brief Yahoo Finance data collector using yfinance library
@details 100% FREE, unlimited API calls - perfect for supplemental data
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed - run: pip install yfinance")


class YFinanceCollector:
    """
    @class YFinanceCollector
    @brief Yahoo Finance data collector
    @details Free, unlimited access to stock data, fundamentals, and analyst ratings
    """

    def __init__(self):
        """
        @brief Initialize YFinance collector
        @note No API key required - 100% free!
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance package not installed. Install with: pip install yfinance")

    def collect_stock_info(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Collect comprehensive stock information
        @param tickers List of stock ticker symbols
        @return List of stock info dictionaries

        Includes: PE ratio, market cap, analyst ratings, earnings date, etc.
        """
        results = []

        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info

                if not info or 'symbol' not in info:
                    logger.warning(f"No data available for {ticker_symbol}")
                    continue

                results.append({
                    'ticker': ticker_symbol,
                    'company_name': info.get('longName', ''),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'market_cap': info.get('marketCap', 0),
                    'pe_ratio': info.get('trailingPE', 0),
                    'forward_pe': info.get('forwardPE', 0),
                    'peg_ratio': info.get('pegRatio', 0),
                    'price_to_book': info.get('priceToBook', 0),
                    'dividend_yield': info.get('dividendYield', 0),
                    'beta': info.get('beta', 0),
                    'fifty_day_avg': info.get('fiftyDayAverage', 0),
                    'two_hundred_day_avg': info.get('twoHundredDayAverage', 0),
                    'analyst_recommendation': info.get('recommendationKey', 'none'),
                    'target_price': info.get('targetMeanPrice', 0),
                    'num_analyst_opinions': info.get('numberOfAnalystOpinions', 0),
                    'earnings_date': self._parse_earnings_date(info.get('earningsTimestamp')),
                    'collected_at': datetime.now()
                })

                logger.debug(f"Collected info for {ticker_symbol}: PE={info.get('trailingPE')}, MCap=${info.get('marketCap', 0):,}")

            except Exception as e:
                logger.error(f"Error collecting data for {ticker_symbol}: {e}")
                continue

        logger.info(f"Collected yfinance data for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_analyst_ratings(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Collect analyst recommendations and price targets
        @param tickers List of stock ticker symbols
        @return List of analyst rating dictionaries
        """
        results = []

        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info

                # Get recommendations
                recommendation = info.get('recommendationKey', 'none')
                target_high = info.get('targetHighPrice', 0)
                target_low = info.get('targetLowPrice', 0)
                target_mean = info.get('targetMeanPrice', 0)
                current_price = info.get('currentPrice', 0)

                # Calculate upside potential
                upside = 0
                if current_price > 0 and target_mean > 0:
                    upside = ((target_mean - current_price) / current_price) * 100

                results.append({
                    'ticker': ticker_symbol,
                    'recommendation': recommendation,
                    'target_high': target_high,
                    'target_low': target_low,
                    'target_mean': target_mean,
                    'current_price': current_price,
                    'upside_potential': round(upside, 2),
                    'num_analysts': info.get('numberOfAnalystOpinions', 0),
                    'collected_at': datetime.now()
                })

            except Exception as e:
                logger.error(f"Error collecting analyst data for {ticker_symbol}: {e}")
                continue

        logger.info(f"Collected analyst ratings for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_financials(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Collect financial metrics and ratios
        @param tickers List of stock ticker symbols
        @return List of financial dictionaries
        """
        results = []

        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info

                results.append({
                    'ticker': ticker_symbol,
                    'revenue': info.get('totalRevenue', 0),
                    'gross_profit': info.get('grossProfits', 0),
                    'ebitda': info.get('ebitda', 0),
                    'net_income': info.get('netIncomeToCommon', 0),
                    'earnings_growth': info.get('earningsGrowth', 0),
                    'revenue_growth': info.get('revenueGrowth', 0),
                    'operating_margin': info.get('operatingMargins', 0),
                    'profit_margin': info.get('profitMargins', 0),
                    'return_on_equity': info.get('returnOnEquity', 0),
                    'return_on_assets': info.get('returnOnAssets', 0),
                    'debt_to_equity': info.get('debtToEquity', 0),
                    'current_ratio': info.get('currentRatio', 0),
                    'quick_ratio': info.get('quickRatio', 0),
                    'free_cash_flow': info.get('freeCashflow', 0),
                    'collected_at': datetime.now()
                })

            except Exception as e:
                logger.error(f"Error collecting financials for {ticker_symbol}: {e}")
                continue

        logger.info(f"Collected financials for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_historical_prices(self, tickers: List[str], period: str = "1mo") -> Dict[str, List[Dict]]:
        """
        @brief Collect historical price data
        @param tickers List of stock ticker symbols
        @param period Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        @return Dictionary mapping ticker to list of price dictionaries
        """
        results = {}

        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period=period)

                if hist.empty:
                    logger.warning(f"No historical data for {ticker_symbol}")
                    continue

                prices = []
                for index, row in hist.iterrows():
                    prices.append({
                        'ticker': ticker_symbol,
                        'date': index.strftime('%Y-%m-%d'),
                        'open': round(row['Open'], 2),
                        'high': round(row['High'], 2),
                        'low': round(row['Low'], 2),
                        'close': round(row['Close'], 2),
                        'volume': int(row['Volume']),
                        'collected_at': datetime.now()
                    })

                results[ticker_symbol] = prices
                logger.debug(f"Collected {len(prices)} price points for {ticker_symbol}")

            except Exception as e:
                logger.error(f"Error collecting historical data for {ticker_symbol}: {e}")
                continue

        logger.info(f"Collected historical prices for {len(results)}/{len(tickers)} tickers")
        return results

    def get_earnings_calendar(self, tickers: List[str]) -> List[Dict]:
        """
        @brief Get upcoming earnings dates
        @param tickers List of stock ticker symbols
        @return List of earnings calendar entries
        """
        results = []

        for ticker_symbol in tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info

                earnings_timestamp = info.get('earningsTimestamp')
                if earnings_timestamp:
                    earnings_date = self._parse_earnings_date(earnings_timestamp)

                    results.append({
                        'ticker': ticker_symbol,
                        'earnings_date': earnings_date,
                        'earnings_timestamp': earnings_timestamp,
                        'collected_at': datetime.now()
                    })

            except Exception as e:
                logger.error(f"Error collecting earnings date for {ticker_symbol}: {e}")
                continue

        logger.info(f"Collected earnings dates for {len(results)}/{len(tickers)} tickers")
        return results

    def _parse_earnings_date(self, timestamp: Optional[int]) -> Optional[str]:
        """
        @brief Parse earnings timestamp to readable date
        @param timestamp Unix timestamp
        @return Formatted date string or None
        """
        if not timestamp:
            return None

        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except Exception:
            return None

    def close(self):
        """
        @brief Cleanup method (no-op for yfinance)
        """
        pass
