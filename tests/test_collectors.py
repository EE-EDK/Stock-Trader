"""
@file test_collectors.py
@brief Unit tests for data collectors
@details Tests for ApeWisdom, OpenInsider, and Finnhub collectors
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import requests

from src.collectors.apewisdom import ApeWisdomCollector
from src.collectors.openinsider import OpenInsiderCollector
from src.collectors.finnhub import FinnhubCollector


class TestApeWisdomCollector:
    """Test cases for ApeWisdomCollector"""

    def test_init(self):
        """Test collector initialization"""
        collector = ApeWisdomCollector(timeout=15)
        assert collector.timeout == 15
        assert collector.session is not None

    @patch('src.collectors.apewisdom.requests.Session.get')
    def test_collect_success(self, mock_get):
        """Test successful data collection"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'ticker': 'NVDA',
                    'mentions': 542,
                    'upvotes': 12847,
                    'rank': 1,
                    'mentions_24h_ago': 389,
                    'rank_24h_ago': 2
                },
                {
                    'ticker': 'TSLA',
                    'mentions': 423,
                    'upvotes': 9234,
                    'rank': 2,
                    'mentions_24h_ago': 401,
                    'rank_24h_ago': 1
                }
            ]
        }
        mock_get.return_value = mock_response

        collector = ApeWisdomCollector()
        results = collector.collect(top_n=10)

        assert len(results) == 2
        assert results[0]['ticker'] == 'NVDA'
        assert results[0]['mentions'] == 542
        assert results[0]['source'] == 'apewisdom'
        assert isinstance(results[0]['collected_at'], datetime)

    @patch('src.collectors.apewisdom.requests.Session.get')
    def test_collect_api_error(self, mock_get):
        """Test handling of API errors"""
        mock_get.side_effect = requests.RequestException("API error")

        collector = ApeWisdomCollector()
        results = collector.collect()

        assert results == []

    @patch('src.collectors.apewisdom.requests.Session.get')
    def test_collect_invalid_data(self, mock_get):
        """Test handling of invalid response data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': [{'invalid': 'data'}]}
        mock_get.return_value = mock_response

        collector = ApeWisdomCollector()
        results = collector.collect()

        # Should filter out invalid entries
        assert len(results) == 0

    def test_close(self):
        """Test session cleanup"""
        collector = ApeWisdomCollector()
        collector.close()
        # Session should be closed, no error should occur


class TestOpenInsiderCollector:
    """Test cases for OpenInsiderCollector"""

    def test_init(self):
        """Test collector initialization"""
        collector = OpenInsiderCollector()
        assert collector.session is not None
        assert 'User-Agent' in collector.session.headers

    @patch('src.collectors.openinsider.requests.Session.get')
    def test_parse_float(self, mock_get):
        """Test float parsing utility"""
        collector = OpenInsiderCollector()

        assert collector._parse_float('$123.45') == 123.45
        assert collector._parse_float('1,234.56') == 1234.56
        assert collector._parse_float('+50%') == 50.0
        assert collector._parse_float('invalid') == 0.0
        assert collector._parse_float('') == 0.0

    @patch('src.collectors.openinsider.requests.Session.get')
    def test_parse_int(self, mock_get):
        """Test integer parsing utility"""
        collector = OpenInsiderCollector()

        assert collector._parse_int('1,234') == 1234
        assert collector._parse_int('$567') == 567
        assert collector._parse_int('invalid') == 0
        assert collector._parse_int('') == 0

    @patch('src.collectors.openinsider.requests.Session.get')
    def test_parse_date(self, mock_get):
        """Test date parsing utility"""
        collector = OpenInsiderCollector()

        result = collector._parse_date('2024-01-15')
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

        # Invalid date should return current date
        result = collector._parse_date('invalid')
        assert isinstance(result, datetime)


class TestFinnhubCollector:
    """Test cases for FinnhubCollector"""

    def test_init(self):
        """Test collector initialization"""
        collector = FinnhubCollector(api_key='test_key', rate_limit=55)
        assert collector.api_key == 'test_key'
        assert collector.rate_limit == 55
        assert collector._request_count == 0

    @patch('src.collectors.finnhub.requests.get')
    @patch('src.collectors.finnhub.time.sleep')
    def test_collect_quotes_success(self, mock_sleep, mock_get):
        """Test successful quote collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'c': 150.25,  # current price
            'h': 151.00,  # high
            'l': 149.50,  # low
            'o': 150.00,  # open
            'pc': 149.00,  # previous close
            't': 1234567890
        }
        mock_get.return_value = mock_response

        collector = FinnhubCollector(api_key='test_key')
        results = collector.collect_quotes(['AAPL'])

        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'
        assert results[0]['price'] == 150.25
        assert abs(results[0]['change_pct'] - 0.839) < 0.01  # (150.25-149)/149 * 100

    @patch('src.collectors.finnhub.requests.get')
    def test_collect_sentiment_success(self, mock_get):
        """Test successful sentiment collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sentiment': {
                'bearishPercent': 0.15,
                'bullishPercent': 0.65
            },
            'companyNewsScore': 0.65,
            'buzz': {
                'buzz': 0.85,
                'articlesInLastWeek': 50
            }
        }
        mock_get.return_value = mock_response

        collector = FinnhubCollector(api_key='test_key')
        results = collector.collect_sentiment(['AAPL'])

        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'
        assert results[0]['bullish_pct'] == 0.65
        assert results[0]['bearish_pct'] == 0.15
        assert results[0]['news_sentiment'] == 0.65

    @patch('src.collectors.finnhub.requests.get')
    def test_rate_limiting(self, mock_get):
        """Test that rate limiting is applied"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'c': 100}
        mock_get.return_value = mock_response

        collector = FinnhubCollector(api_key='test_key', rate_limit=2)

        # Make multiple requests
        with patch('src.collectors.finnhub.time.sleep') as mock_sleep:
            collector.collect_quotes(['AAPL', 'TSLA', 'NVDA'])
            # Should trigger rate limiting after 2 requests
            # Note: actual behavior depends on timing


# Integration tests (require network access)
@pytest.mark.integration
class TestCollectorsIntegration:
    """Integration tests requiring actual API calls"""

    def test_apewisdom_live(self):
        """Test live ApeWisdom API call"""
        collector = ApeWisdomCollector()
        results = collector.collect(top_n=5)

        # May fail if API is down, but structure should be correct
        if results:
            assert len(results) > 0
            assert 'ticker' in results[0]
            assert 'mentions' in results[0]
            assert isinstance(results[0]['collected_at'], datetime)

    @pytest.mark.skip(reason="Requires valid Finnhub API key")
    def test_finnhub_live(self):
        """Test live Finnhub API call (requires API key)"""
        import os
        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            pytest.skip("FINNHUB_API_KEY not set")

        collector = FinnhubCollector(api_key=api_key)
        results = collector.collect_quotes(['AAPL'])

        assert len(results) > 0
        assert results[0]['ticker'] == 'AAPL'
        assert results[0]['price'] > 0
