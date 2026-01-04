"""
@file congress.py
@brief Collector for US Congress stock trading data
@details Uses Financial Modeling Prep (FMP) API - Free tier available
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
    @details Uses Financial Modeling Prep API (https://financialmodelingprep.com)
             - Free tier: 250 requests/day
             - Endpoints: senate-disclosure, senate-trading, house-disclosure
    """

    FMP_BASE_URL = "https://financialmodelingprep.com/api/v4"

    def __init__(self, config: dict):
        """
        @brief Initialize Congress trades collector
        @param config Configuration dictionary
        """
        self.config = config.get('collection', {}).get('congress', {})
        self.enabled = self.config.get('enabled', False)
        self.lookback_days = self.config.get('lookback_days', 90)

        # FMP API key
        self.fmp_key = config.get('api_keys', {}).get('fmp')

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Stock-Trader/1.3.0 (Educational Project)'
        })

    def collect_house_trades(self) -> List[Dict]:
        """
        @brief Collect House of Representatives trades from FMP API
        @return List of trade dictionaries
        """
        if not self.enabled or not self.fmp_key:
            logger.info("Congress trades collection disabled or FMP API key not configured")
            return []

        try:
            logger.info("Fetching House trades from Financial Modeling Prep...")
            url = f"{self.FMP_BASE_URL}/house-disclosure"
            params = {'apikey': self.fmp_key}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            all_trades = response.json()

            if not isinstance(all_trades, list):
                logger.warning(f"Unexpected FMP response format: {type(all_trades)}")
                return []

            # Filter to recent trades
            cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
            recent_trades = []

            for trade in all_trades:
                transaction_date_str = trade.get('transactionDate')
                if not transaction_date_str:
                    continue

                # Parse transaction date
                try:
                    transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d')
                except ValueError:
                    continue

                if transaction_date >= cutoff_date:
                    normalized = self._normalize_fmp_trade(trade, 'house')
                    if normalized['ticker']:  # Only add if we have a ticker
                        recent_trades.append(normalized)

            logger.info(f"Collected {len(recent_trades)} recent House trades (last {self.lookback_days} days)")
            return recent_trades

        except Exception as e:
            logger.error(f"Failed to collect House trades from FMP: {e}")
            return []

    def collect_senate_trades(self) -> List[Dict]:
        """
        @brief Collect Senate trades from FMP API
        @return List of trade dictionaries
        """
        if not self.enabled or not self.fmp_key:
            return []

        try:
            logger.info("Fetching Senate trades from Financial Modeling Prep...")
            url = f"{self.FMP_BASE_URL}/senate-trading"
            params = {'apikey': self.fmp_key}

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            all_trades = response.json()

            if not isinstance(all_trades, list):
                logger.warning(f"Unexpected FMP response format: {type(all_trades)}")
                return []

            # Filter to recent trades
            cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
            recent_trades = []

            for trade in all_trades:
                transaction_date_str = trade.get('transactionDate')
                if not transaction_date_str:
                    continue

                try:
                    transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d')
                except ValueError:
                    continue

                if transaction_date >= cutoff_date:
                    normalized = self._normalize_fmp_trade(trade, 'senate')
                    if normalized['ticker']:
                        recent_trades.append(normalized)

            logger.info(f"Collected {len(recent_trades)} recent Senate trades (last {self.lookback_days} days)")
            return recent_trades

        except Exception as e:
            logger.error(f"Failed to collect Senate trades from FMP: {e}")
            return []

    def collect_all_trades(self) -> List[Dict]:
        """
        @brief Collect trades from all available sources (House and Senate)
        @return Combined list of trade dictionaries
        """
        if not self.enabled:
            logger.info("Congress trades collection is disabled")
            return []

        if not self.fmp_key or self.fmp_key == 'YOUR_FMP_KEY':
            logger.info("FMP API key not configured - skipping Congress trades")
            return []

        all_trades = []

        # Collect from both House and Senate
        house_trades = self.collect_house_trades()
        all_trades.extend(house_trades)

        senate_trades = self.collect_senate_trades()
        all_trades.extend(senate_trades)

        logger.info(f"Total Congress trades collected: {len(all_trades)} (House: {len(house_trades)}, Senate: {len(senate_trades)})")
        return all_trades

    def _normalize_fmp_trade(self, trade: Dict, chamber: str) -> Dict:
        """
        @brief Normalize FMP trade format to standard format
        @param trade Raw trade data from FMP API
        @param chamber 'house' or 'senate'
        @return Normalized trade dictionary
        """
        # Extract ticker symbol
        ticker = trade.get('symbol', '').upper()

        # Parse amount
        amount_str = trade.get('amount', '')
        amount_from, amount_to = self._parse_amount_range(amount_str)

        # Normalize transaction type
        transaction_type = self._normalize_transaction_type(trade.get('type', ''))

        return {
            'representative_name': trade.get('firstName', '') + ' ' + trade.get('lastName', ''),
            'party': '',  # FMP doesn't provide party info
            'chamber': chamber,
            'state': '',  # FMP doesn't provide state info
            'district': trade.get('district', ''),
            'ticker': ticker,
            'asset_name': trade.get('assetDescription', ''),
            'transaction_type': transaction_type,
            'transaction_date': trade.get('transactionDate'),
            'filing_date': trade.get('disclosureDate', trade.get('transactionDate')),
            'disclosure_date': trade.get('disclosureDate', trade.get('transactionDate')),
            'amount_from': amount_from,
            'amount_to': amount_to,
            'owner': trade.get('owner', 'self'),
            'position': trade.get('position', ''),
            'asset_type': trade.get('assetType', 'stock'),
            'source': 'fmp'
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
