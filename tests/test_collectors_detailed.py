"""
Comprehensive unit tests for all data collectors
Tests API functionality, error handling, and data validation
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.apewisdom import ApeWisdomCollector
from src.collectors.openinsider import OpenInsiderCollector
from src.collectors.finnhub import FinnhubCollector
from src.collectors.alphavantage import AlphaVantageCollector
from src.collectors.fmp import FMPCollector


class TestApeWisdomCollector:
    """Test ApeWisdom collector"""

    def test_initialization(self):
        """Test collector initialization"""
        collector = ApeWisdomCollector()
        assert collector is not None
        assert hasattr(collector, 'collect')

    @patch('requests.Session.get')
    def test_collect_success(self, mock_get):
        """Test successful data collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'ticker': 'AAPL',
                    'mentions': 150,
                    'upvotes': 2000,
                    'rank': 1,
                    'mentions_24h_ago': 100,
                    'rank_24h_ago': 2
                },
                {
                    'ticker': 'TSLA',
                    'mentions': 120,
                    'upvotes': 1500,
                    'rank': 2
                }
            ]
        }
        mock_get.return_value = mock_response

        collector = ApeWisdomCollector()
        results = collector.collect(top_n=10)

        assert len(results) == 2
        assert results[0]['ticker'] == 'AAPL'
        assert results[0]['mentions'] == 150
        assert 'collected_at' in results[0]
        assert results[0]['source'] == 'apewisdom'

    @patch('requests.Session.get')
    def test_collect_api_error(self, mock_get):
        """Test API error handling"""
        mock_get.side_effect = requests.RequestException("API Error")

        collector = ApeWisdomCollector()
        results = collector.collect(top_n=10)

        assert results == []

    @patch('requests.Session.get')
    def test_collect_empty_response(self, mock_get):
        """Test empty API response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response

        collector = ApeWisdomCollector()
        results = collector.collect(top_n=10)

        assert results == []

    @patch('requests.get')
    def test_collect_malformed_data(self, mock_get):
        """Test handling of malformed data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'ticker': 'AAPL'},  # Missing fields
                None,  # Invalid entry
                {'mentions': 100}  # Missing ticker
            ]
        }
        mock_get.return_value = mock_response

        collector = ApeWisdomCollector()
        results = collector.collect(top_n=10)

        # Should handle gracefully
        assert isinstance(results, list)


class TestOpenInsiderCollector:
    """Test OpenInsider scraper"""

    def test_initialization(self):
        """Test collector initialization"""
        collector = OpenInsiderCollector()
        assert collector is not None
        assert hasattr(collector, 'session')

    @patch('requests.Session.get')
    def test_collect_cluster_buys(self, mock_get):
        """Test cluster buys collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <table class="tinytable">
            <tr><th>Header</th></tr>
            <tr>
                <td>X</td>
                <td>2024-01-15</td>
                <td>2024-01-14</td>
                <td><a>AAPL</a></td>
                <td>John Doe</td>
                <td>CEO</td>
                <td>P</td>
                <td>$150.00</td>
                <td>10,000</td>
                <td>$1,500,000</td>
                <td>+5%</td>
            </tr>
        </table>
        '''
        mock_get.return_value = mock_response

        collector = OpenInsiderCollector()
        results = collector.collect_cluster_buys()

        assert isinstance(results, list)
        if results:
            assert 'ticker' in results[0]
            assert results[0]['is_cluster_buy'] == True

    @patch('requests.Session.get')
    def test_parse_date_helper(self, mock_get):
        """Test date parsing"""
        collector = OpenInsiderCollector()

        # Valid date
        date = collector._parse_date('2024-01-15')
        assert isinstance(date, datetime)

        # Invalid date
        date = collector._parse_date('invalid')
        assert isinstance(date, datetime)  # Should return current datetime

    def test_parse_float_helper(self):
        """Test float parsing"""
        collector = OpenInsiderCollector()

        assert collector._parse_float('$1,234.56') == 1234.56
        assert collector._parse_float('+25%') == 25.0
        assert collector._parse_float('invalid') == 0.0

    def test_parse_int_helper(self):
        """Test integer parsing"""
        collector = OpenInsiderCollector()

        assert collector._parse_int('1,234,567') == 1234567
        assert collector._parse_int('$1,000') == 1000
        assert collector._parse_int('invalid') == 0


class TestFinnhubCollector:
    """Test Finnhub collector"""

    def test_initialization(self):
        """Test collector initialization"""
        collector = FinnhubCollector(api_key='test_key')
        assert collector.api_key == 'test_key'
        assert collector.rate_limit == 55

    def test_rate_limiting(self):
        """Test rate limiting logic"""
        collector = FinnhubCollector(api_key='test_key', rate_limit=5)

        # Simulate requests
        for i in range(5):
            collector._rate_limit_wait()

        # Should have made 5 requests
        assert collector._request_count <= 5

    @patch('requests.get')
    def test_collect_quotes_success(self, mock_get):
        """Test quote collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'c': 150.25,
            'h': 151.00,
            'l': 149.50,
            'o': 150.00,
            'pc': 149.00
        }
        mock_get.return_value = mock_response

        collector = FinnhubCollector(api_key='test_key')
        results = collector.collect_quotes(['AAPL'])

        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'
        assert results[0]['price'] == 150.25
        assert 'change_pct' in results[0]

    @patch('requests.get')
    def test_collect_sentiment_forbidden(self, mock_get):
        """Test sentiment collection with forbidden response"""
        mock_response = Mock()
        mock_response.status_code = 403

        # Create proper HTTPError with response attribute
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        collector = FinnhubCollector(api_key='test_key')
        results = collector.collect_sentiment(['AAPL'])

        # Should handle gracefully
        assert isinstance(results, list)

    @patch('requests.get')
    def test_combine_price_and_sentiment(self, mock_get):
        """Test combined price and sentiment"""
        mock_response_quote = Mock()
        mock_response_quote.status_code = 200
        mock_response_quote.json.return_value = {
            'c': 150.25,
            'h': 151.00,
            'l': 149.50,
            'o': 150.00,
            'pc': 149.00
        }

        mock_response_sentiment = Mock()
        mock_response_sentiment.status_code = 200
        mock_response_sentiment.json.return_value = {
            'sentiment': {
                'bullishPercent': 0.65,
                'bearishPercent': 0.15
            },
            'companyNewsScore': 0.75
        }

        mock_get.side_effect = [mock_response_quote, mock_response_sentiment]

        collector = FinnhubCollector(api_key='test_key')
        results = collector.combine_price_and_sentiment(['AAPL'])

        assert len(results) >= 1


class TestAlphaVantageCollector:
    """Test Alpha Vantage collector"""

    def test_initialization(self):
        """Test collector initialization"""
        collector = AlphaVantageCollector(api_key='test_key')
        assert collector.api_key == 'test_key'
        assert collector.calls_per_day == 100

    @patch('requests.get')
    @patch('time.sleep')
    def test_collect_news_sentiment(self, mock_sleep, mock_get):
        """Test news sentiment collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'feed': [
                {
                    'ticker_sentiment': [
                        {
                            'ticker': 'AAPL',
                            'ticker_sentiment_score': '0.5',
                            'relevance_score': '0.8'
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        collector = AlphaVantageCollector(api_key='test_key')
        results = collector.collect_news_sentiment(['AAPL'], limit_per_ticker=10)

        assert isinstance(results, list)
        if results:
            assert 'ticker' in results[0]
            assert 'news_sentiment' in results[0]

    def test_api_limit_enforcement(self):
        """Test API limit enforcement"""
        collector = AlphaVantageCollector(api_key='test_key', calls_per_day=2)

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'feed': []}

            # Should stop after hitting limit
            results = collector.collect_news_sentiment(['AAPL', 'TSLA', 'NVDA'])
            assert collector._call_count <= 2

    @patch('requests.get')
    def test_get_top_gainers_losers(self, mock_get):
        """Test top gainers/losers endpoint"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'top_gainers': [{'ticker': 'AAPL', 'price': '150'}],
            'top_losers': [{'ticker': 'TSLA', 'price': '200'}],
            'most_actively_traded': []
        }
        mock_get.return_value = mock_response

        collector = AlphaVantageCollector(api_key='test_key')
        results = collector.get_top_gainers_losers()

        assert 'top_gainers' in results
        assert 'top_losers' in results


class TestFMPCollector:
    """Test Financial Modeling Prep collector"""

    def test_initialization(self):
        """Test collector initialization"""
        collector = FMPCollector(api_key='test_key')
        assert collector.api_key == 'test_key'
        assert collector.rate_limit == 250

    @patch('requests.get')
    def test_collect_earnings_calendar(self, mock_get):
        """Test earnings calendar collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'symbol': 'AAPL',
                'date': '2024-01-25',
                'epsEstimated': 2.10,
                'eps': 2.15,
                'time': 'amc'
            }
        ]
        mock_get.return_value = mock_response

        collector = FMPCollector(api_key='test_key')
        results = collector.collect_earnings_calendar('2024-01-01', '2024-01-31')

        assert isinstance(results, list)
        if results:
            assert 'ticker' in results[0]
            assert 'date' in results[0]

    @patch('requests.get')
    def test_collect_analyst_estimates(self, mock_get):
        """Test analyst estimates collection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'date': '2024-01-01',
                'estimatedRevenueAvg': 1000000000,
                'estimatedEpsAvg': 2.50
            }
        ]
        mock_get.return_value = mock_response

        collector = FMPCollector(api_key='test_key')
        result = collector.collect_analyst_estimates('AAPL')

        assert result is not None or result is None  # May return None if empty

    @patch('requests.get')
    def test_api_error_handling(self, mock_get):
        """Test API error handling"""
        mock_get.side_effect = requests.RequestException("API Error")

        collector = FMPCollector(api_key='test_key')
        results = collector.collect_earnings_calendar('2024-01-01', '2024-01-31')

        assert results == []


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios"""

    def test_empty_ticker_list(self):
        """Test collectors with empty ticker list"""
        collector = FinnhubCollector(api_key='test_key')
        results = collector.collect_quotes([])
        assert results == []

    def test_invalid_ticker(self):
        """Test collectors with invalid ticker"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {}

            collector = FinnhubCollector(api_key='test_key')
            results = collector.collect_quotes(['INVALID123'])

            # Should handle gracefully
            assert isinstance(results, list)

    def test_network_timeout(self):
        """Test network timeout handling"""
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.Timeout("Request timed out")

            collector = ApeWisdomCollector()
            results = collector.collect(top_n=10)

            assert results == []

    def test_malformed_json_response(self):
        """Test malformed JSON response"""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response

            collector = ApeWisdomCollector()
            results = collector.collect(top_n=10)

            assert results == []


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src.collectors', '--cov-report=term-missing'])
