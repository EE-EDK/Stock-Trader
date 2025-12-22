"""
@file congress.py
@brief Collector for US Congress stock trading data
@details FREE data sources: House Stock Watcher API (no key needed), Finnhub Congressional Trading API
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)


class CongressTradesCollector:
    """
    @class CongressTradesCollector
    @brief Collects stock trading data from US Congress members
    @details Uses multiple FREE sources:
             - House Stock Watcher API (https://housestockwatcher.com/api) - No API key required
             - Finnhub Congressional Trading API - Uses existing Finnhub key
    """

    HOUSE_API_URL = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
    FINNHUB_CONGRESS_URL = "https://finnhub.io/api/v1/stock/congressional-trading"

    def __init__(self, config: dict):
        """
        @brief Initialize Congress trades collector
        @param config Configuration dictionary
        """
        self.config = config.get('collection', {}).get('congress', {})
        self.enabled = self.config.get('enabled', False)
        self.lookback_days = self.config.get('lookback_days', 90)

        # Finnhub API key (optional, for enhanced data)
        self.finnhub_key = config.get('api_keys', {}).get('finnhub')

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Stock-Trader/1.3.0 (Educational Project)'
        })

    def collect_house_trades(self) -> List[Dict]:
        """
        @brief Collect House of Representatives trades from House Stock Watcher
        @return List of trade dictionaries
        """
        if not self.enabled:
            return []

        try:
            logger.info("Fetching House trades from House Stock Watcher...")
            response = self.session.get(self.HOUSE_API_URL, timeout=30)
            response.raise_for_status()

            all_trades = response.json()

            # Filter to recent trades
            cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
            recent_trades = []

            for trade in all_trades:
                transaction_date_str = self._parse_date(trade.get('transaction_date'))
                if not transaction_date_str:
                    continue

                # Convert to datetime for comparison
                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d')

                if transaction_date >= cutoff_date:
                    recent_trades.append(self._normalize_house_trade(trade))

            logger.info(f"Collected {len(recent_trades)} recent House trades (last {self.lookback_days} days)")
            return recent_trades

        except Exception as e:
            logger.error(f"Failed to collect House trades: {e}")
            return []

    def collect_finnhub_congress_trades(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        @brief Collect Congress trades from Finnhub API
        @param symbol Optional stock symbol to filter
        @return List of trade dictionaries
        """
        if not self.enabled or not self.finnhub_key:
            return []

        try:
            # Note: Finnhub's congress API requires a symbol parameter
            # We'll skip this for now unless we have specific symbols to query
            # This is a premium feature anyway
            logger.info("Finnhub congressional trading requires premium tier, skipping")
            return []

        except Exception as e:
            logger.error(f"Failed to collect Finnhub Congress trades: {e}")
            return []

    def collect_all_trades(self) -> List[Dict]:
        """
        @brief Collect trades from all available sources
        @return Combined list of trade dictionaries
        """
        if not self.enabled:
            logger.info("Congress trades collection is disabled")
            return []

        all_trades = []

        # Collect from House Stock Watcher (primary FREE source)
        house_trades = self.collect_house_trades()
        all_trades.extend(house_trades)

        logger.info(f"Total Congress trades collected: {len(all_trades)}")
        return all_trades

    def _normalize_house_trade(self, trade: Dict) -> Dict:
        """
        @brief Normalize House Stock Watcher trade format to standard format
        @param trade Raw trade data from House Stock Watcher
        @return Normalized trade dictionary
        """
        # Extract ticker from disclosure_url or asset field
        ticker = self._extract_ticker(trade)

        # Parse amount range
        amount_from, amount_to = self._parse_amount_range(trade.get('amount', ''))

        # Normalize transaction type
        transaction_type = self._normalize_transaction_type(trade.get('type', ''))

        return {
            'representative_name': trade.get('representative', ''),
            'party': trade.get('party', ''),
            'chamber': 'house',
            'state': trade.get('state', ''),
            'district': trade.get('district', ''),
            'ticker': ticker,
            'asset_name': trade.get('asset_description', ''),
            'transaction_type': transaction_type,
            'transaction_date': self._parse_date(trade.get('transaction_date')),
            'filing_date': self._parse_date(trade.get('disclosure_date')),
            'disclosure_date': self._parse_date(trade.get('disclosure_date')),
            'amount_from': amount_from,
            'amount_to': amount_to,
            'owner': trade.get('owner', 'self'),
            'position': '',
            'asset_type': trade.get('asset_type', 'stock'),
            'source': 'housestockwatcher'
        }

    def _extract_ticker(self, trade: Dict) -> str:
        """
        @brief Extract stock ticker from trade data
        @param trade Trade dictionary
        @return Ticker symbol or empty string
        """
        # Try ticker field first
        ticker = trade.get('ticker', '').strip().upper()
        if ticker and ticker != '--':
            return ticker

        # Try to extract from asset_description
        asset_desc = trade.get('asset_description', '')
        if asset_desc:
            # Look for ticker in parentheses like "Apple Inc (AAPL)"
            import re
            match = re.search(r'\(([A-Z]{1,5})\)', asset_desc)
            if match:
                return match.group(1)

        return ''

    def _parse_amount_range(self, amount_str: str) -> tuple:
        """
        @brief Parse amount range string like "$1,001 - $15,000"
        @param amount_str Amount range string
        @return Tuple of (amount_from, amount_to)
        """
        if not amount_str or amount_str == '--':
            return None, None

        try:
            # Remove $ and commas, split on -
            cleaned = amount_str.replace('$', '').replace(',', '').strip()

            if ' - ' in cleaned:
                parts = cleaned.split(' - ')
                amount_from = float(parts[0].strip())
                amount_to = float(parts[1].strip())
                return amount_from, amount_to
            elif '+' in cleaned:
                # Handle "$50,000,000+" format
                amount_from = float(cleaned.replace('+', '').strip())
                return amount_from, amount_from * 2  # Estimate upper bound
            else:
                # Single value
                amount = float(cleaned)
                return amount, amount

        except Exception as e:
            logger.debug(f"Could not parse amount '{amount_str}': {e}")
            return None, None

    def _normalize_transaction_type(self, type_str: str) -> str:
        """
        @brief Normalize transaction type to standard values
        @param type_str Transaction type string
        @return Normalized type: 'purchase', 'sale', or 'exchange'
        """
        type_lower = type_str.lower().strip()

        if 'purchase' in type_lower or 'buy' in type_lower:
            return 'purchase'
        elif 'sale' in type_lower or 'sell' in type_lower:
            return 'sale'
        elif 'exchange' in type_lower:
            return 'exchange'
        else:
            return type_lower

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        @brief Parse date string to ISO format
        @param date_str Date string in various formats
        @return ISO format date string (YYYY-MM-DD) or None
        """
        if not date_str:
            return None

        try:
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If all formats fail, return None
            logger.debug(f"Could not parse date: {date_str}")
            return None

        except Exception as e:
            logger.debug(f"Date parsing error for '{date_str}': {e}")
            return None
