"""
@file test_congress.py
@brief Unit tests for Congress trades collector
@details Tests for CongressTradesCollector and all Congress trading functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import tempfile
import sqlite3
import os

from src.collectors.congress import CongressTradesCollector


class TestCongressCollectorInit:
    """Test cases for CongressTradesCollector initialization"""

    def test_init_enabled(self):
        """Test initialization with Congress trades enabled"""
        config = {
            'collection': {
                'congress': {
                    'enabled': True,
                    'lookback_days': 90
                }
            },
            'api_keys': {}
        }

        collector = CongressTradesCollector(config)

        assert collector.enabled is True
        assert collector.lookback_days == 90

    def test_init_disabled(self):
        """Test initialization with Congress trades disabled"""
        config = {
            'collection': {
                'congress': {
                    'enabled': False
                }
            },
            'api_keys': {}
        }

        collector = CongressTradesCollector(config)
        assert collector.enabled is False

    def test_init_defaults(self):
        """Test initialization with default values"""
        config = {
            'collection': {},
            'api_keys': {}
        }

        collector = CongressTradesCollector(config)

        # Check defaults
        assert collector.enabled is False
        assert collector.lookback_days == 90


class TestExtractTicker:
    """Test cases for ticker extraction"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    def test_extract_ticker_from_field(self):
        """Test extracting ticker from ticker field"""
        trade = {'ticker': 'AAPL'}
        ticker = self.collector._extract_ticker(trade)
        assert ticker == 'AAPL'

    def test_extract_ticker_from_description(self):
        """Test extracting ticker from asset description"""
        trade = {
            'ticker': '--',
            'asset_description': 'Apple Inc (AAPL)'
        }
        ticker = self.collector._extract_ticker(trade)
        assert ticker == 'AAPL'

    def test_extract_ticker_missing(self):
        """Test handling of missing ticker"""
        trade = {'ticker': '--', 'asset_description': 'No ticker here'}
        ticker = self.collector._extract_ticker(trade)
        assert ticker == ''

    def test_extract_ticker_uppercase(self):
        """Test ticker is converted to uppercase"""
        trade = {'ticker': 'aapl'}
        ticker = self.collector._extract_ticker(trade)
        assert ticker == 'AAPL'


class TestParseAmountRange:
    """Test cases for amount range parsing"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    def test_parse_simple_range(self):
        """Test parsing simple amount range"""
        amount_str = "$1,001 - $15,000"
        amount_from, amount_to = self.collector._parse_amount_range(amount_str)
        assert amount_from == 1001
        assert amount_to == 15000

    def test_parse_large_amount(self):
        """Test parsing large amount with commas"""
        amount_str = "$1,000,000 - $5,000,000"
        amount_from, amount_to = self.collector._parse_amount_range(amount_str)
        assert amount_from == 1000000
        assert amount_to == 5000000

    def test_parse_plus_format(self):
        """Test parsing amount with + sign"""
        amount_str = "$50,000,000+"
        amount_from, amount_to = self.collector._parse_amount_range(amount_str)
        assert amount_from == 50000000
        assert amount_to == 100000000  # 2x estimate

    def test_parse_single_value(self):
        """Test parsing single amount value"""
        amount_str = "$10,000"
        amount_from, amount_to = self.collector._parse_amount_range(amount_str)
        assert amount_from == 10000
        assert amount_to == 10000

    def test_parse_missing_amount(self):
        """Test handling missing amount"""
        amount_str = "--"
        amount_from, amount_to = self.collector._parse_amount_range(amount_str)
        assert amount_from is None
        assert amount_to is None

    def test_parse_empty_string(self):
        """Test handling empty string"""
        amount_str = ""
        amount_from, amount_to = self.collector._parse_amount_range(amount_str)
        assert amount_from is None
        assert amount_to is None


class TestNormalizeTransactionType:
    """Test cases for transaction type normalization"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    def test_normalize_purchase(self):
        """Test normalizing purchase types"""
        assert self.collector._normalize_transaction_type('Purchase') == 'purchase'
        assert self.collector._normalize_transaction_type('BUY') == 'purchase'
        assert self.collector._normalize_transaction_type('purchase') == 'purchase'

    def test_normalize_sale(self):
        """Test normalizing sale types"""
        assert self.collector._normalize_transaction_type('Sale') == 'sale'
        assert self.collector._normalize_transaction_type('SELL') == 'sale'
        assert self.collector._normalize_transaction_type('sale') == 'sale'

    def test_normalize_exchange(self):
        """Test normalizing exchange types"""
        assert self.collector._normalize_transaction_type('Exchange') == 'exchange'
        assert self.collector._normalize_transaction_type('EXCHANGE') == 'exchange'

    def test_normalize_unknown(self):
        """Test handling unknown type"""
        result = self.collector._normalize_transaction_type('Unknown')
        assert result == 'unknown'


class TestParseDateFormats:
    """Test cases for date parsing"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    def test_parse_iso_date(self):
        """Test parsing ISO format date"""
        date_str = "2025-12-21"
        result = self.collector._parse_date(date_str)
        assert result == "2025-12-21"

    def test_parse_us_date(self):
        """Test parsing US format date"""
        date_str = "12/21/2025"
        result = self.collector._parse_date(date_str)
        assert result == "2025-12-21"

    def test_parse_datetime(self):
        """Test parsing datetime string"""
        date_str = "2025-12-21T10:30:00"
        result = self.collector._parse_date(date_str)
        assert result == "2025-12-21"

    def test_parse_none(self):
        """Test handling None date"""
        result = self.collector._parse_date(None)
        assert result is None

    def test_parse_invalid_date(self):
        """Test handling invalid date format"""
        date_str = "invalid-date"
        result = self.collector._parse_date(date_str)
        assert result is None


class TestNormalizeHouseTrade:
    """Test cases for normalizing House trade data"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    def test_normalize_complete_trade(self):
        """Test normalizing complete trade data"""
        trade = {
            'representative': 'John Smith',
            'party': 'D',
            'state': 'CA',
            'district': '12',
            'ticker': 'AAPL',
            'asset_description': 'Apple Inc',
            'type': 'Purchase',
            'transaction_date': '2025-12-01',
            'disclosure_date': '2025-12-15',
            'amount': '$15,001 - $50,000',
            'owner': 'self',
            'asset_type': 'stock'
        }

        result = self.collector._normalize_house_trade(trade)

        assert result['representative_name'] == 'John Smith'
        assert result['party'] == 'D'
        assert result['chamber'] == 'house'
        assert result['state'] == 'CA'
        assert result['district'] == '12'
        assert result['ticker'] == 'AAPL'
        assert result['asset_name'] == 'Apple Inc'
        assert result['transaction_type'] == 'purchase'
        assert result['transaction_date'] == '2025-12-01'
        assert result['amount_from'] == 15001
        assert result['amount_to'] == 50000
        assert result['owner'] == 'self'
        assert result['source'] == 'fmp'  # Financial Modeling Prep API

    def test_normalize_minimal_trade(self):
        """Test normalizing trade with minimal data"""
        trade = {
            'representative': 'Jane Doe',
            'ticker': 'TSLA',
            'type': 'Sale',
            'transaction_date': '2025-12-10'
        }

        result = self.collector._normalize_house_trade(trade)

        assert result['representative_name'] == 'Jane Doe'
        assert result['ticker'] == 'TSLA'
        assert result['transaction_type'] == 'sale'
        assert result['chamber'] == 'house'


class TestCollectHouseTrades:
    """Test cases for collecting House trades"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True, 'lookback_days': 30}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    @patch('src.collectors.congress.requests.Session.get')
    def test_collect_success(self, mock_get):
        """Test successful collection of House trades"""
        # Mock API response
        recent_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'representative': 'Test Rep',
                'ticker': 'AAPL',
                'type': 'Purchase',
                'transaction_date': recent_date,
                'amount': '$15,001 - $50,000'
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        trades = self.collector.collect_house_trades()

        assert len(trades) > 0
        assert trades[0]['ticker'] == 'AAPL'
        assert trades[0]['transaction_type'] == 'purchase'

    @patch('src.collectors.congress.requests.Session.get')
    def test_collect_filters_old_trades(self, mock_get):
        """Test that old trades are filtered out"""
        # Mock API response with old trade
        old_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'representative': 'Test Rep',
                'ticker': 'AAPL',
                'type': 'Purchase',
                'transaction_date': old_date,
                'amount': '$15,001 - $50,000'
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        trades = self.collector.collect_house_trades()

        # Should filter out trades older than lookback_days (30)
        assert len(trades) == 0

    @patch('src.collectors.congress.requests.Session.get')
    def test_collect_api_error(self, mock_get):
        """Test handling of API errors"""
        mock_get.side_effect = Exception("API Error")

        trades = self.collector.collect_house_trades()

        assert trades == []

    def test_collect_when_disabled(self):
        """Test that collection returns empty when disabled"""
        config = {
            'collection': {'congress': {'enabled': False}},
            'api_keys': {}
        }
        collector = CongressTradesCollector(config)

        trades = collector.collect_house_trades()

        assert trades == []


class TestCollectAllTrades:
    """Test cases for collecting all trades"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True, 'lookback_days': 30}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    @patch('src.collectors.congress.CongressTradesCollector.collect_house_trades')
    def test_collect_all(self, mock_house):
        """Test collecting from all sources"""
        mock_house.return_value = [
            {'ticker': 'AAPL', 'transaction_type': 'purchase'}
        ]

        trades = self.collector.collect_all_trades()

        assert len(trades) == 1
        mock_house.assert_called_once()

    def test_collect_all_disabled(self):
        """Test that collect_all returns empty when disabled"""
        config = {
            'collection': {'congress': {'enabled': False}},
            'api_keys': {}
        }
        collector = CongressTradesCollector(config)

        trades = collector.collect_all_trades()

        assert trades == []


class TestEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Setup test collector"""
        config = {
            'collection': {'congress': {'enabled': True}},
            'api_keys': {}
        }
        self.collector = CongressTradesCollector(config)

    def test_malformed_amount_string(self):
        """Test handling malformed amount strings"""
        result = self.collector._parse_amount_range("invalid$format")
        assert result == (None, None)

    def test_empty_trade_data(self):
        """Test normalizing empty trade"""
        trade = {}
        result = self.collector._normalize_house_trade(trade)

        # Should have defaults
        assert result['chamber'] == 'house'
        assert result['source'] == 'fmp'  # Financial Modeling Prep API

    def test_special_characters_in_name(self):
        """Test handling special characters in representative name"""
        trade = {
            'representative': "O'Connor, Jr.",
            'ticker': 'AAPL',
            'type': 'Purchase',
            'transaction_date': '2025-12-01'
        }

        result = self.collector._normalize_house_trade(trade)
        assert result['representative_name'] == "O'Connor, Jr."
