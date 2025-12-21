"""
@file test_fred.py
@brief Unit tests for FRED macro indicator collector
@details Tests for FREDCollector class and all macro indicator functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from src.collectors.fred import FREDCollector


class TestFREDCollectorInit:
    """Test cases for FRED collector initialization"""

    def test_init(self):
        """Test collector initialization"""
        collector = FREDCollector(api_key="test_key")

        assert collector.api_key == "test_key"
        assert collector.session is not None
        assert collector.request_count == 0
        assert isinstance(collector.last_request_time, float)

    def test_indicators_defined(self):
        """Test that all expected indicators are defined"""
        expected_indicators = ['VIX', 'TREASURY_10Y', 'UNEMPLOYMENT', 'INFLATION', 'USD_EUR']

        for indicator in expected_indicators:
            assert indicator in FREDCollector.INDICATORS
            assert 'series_id' in FREDCollector.INDICATORS[indicator]
            assert 'name' in FREDCollector.INDICATORS[indicator]
            assert 'threshold_low' in FREDCollector.INDICATORS[indicator]
            assert 'threshold_high' in FREDCollector.INDICATORS[indicator]


class TestRateLimiting:
    """Test cases for rate limiting functionality"""

    def test_rate_limit_tracking(self):
        """Test that requests are tracked"""
        collector = FREDCollector(api_key="test_key")

        initial_count = collector.request_count
        collector._rate_limit()

        assert collector.request_count == initial_count + 1

    def test_rate_limit_sleep(self):
        """Test that rate limiting sleeps when approaching limit"""
        collector = FREDCollector(api_key="test_key")
        collector.request_count = 115  # Near limit

        with patch('time.sleep') as mock_sleep:
            collector._rate_limit()
            # Should have slept since we're at limit
            mock_sleep.assert_called_once()

    def test_rate_limit_counter_reset(self):
        """Test that counter resets after 60 seconds"""
        collector = FREDCollector(api_key="test_key")
        collector.request_count = 50
        collector.last_request_time = datetime.now().timestamp() - 61  # 61 seconds ago

        collector._rate_limit()

        # Counter should have been reset
        assert collector.request_count == 1  # New request


class TestGetLatestObservation:
    """Test cases for fetching individual observations"""

    @patch('src.collectors.fred.requests.Session.get')
    def test_get_observation_success(self, mock_get):
        """Test successful observation fetch"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'observations': [{
                'date': '2025-12-20',
                'value': '15.5'
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('VIXCLS')

        assert result is not None
        assert result['series_id'] == 'VIXCLS'
        assert result['value'] == 15.5
        assert result['date'] == '2025-12-20'
        assert 'collected_at' in result

    @patch('src.collectors.fred.requests.Session.get')
    def test_get_observation_missing_value(self, mock_get):
        """Test handling of missing/invalid values"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'observations': [{
                'date': '2025-12-20',
                'value': '.'  # FRED uses '.' for missing values
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('VIXCLS')

        assert result is None

    @patch('src.collectors.fred.requests.Session.get')
    def test_get_observation_no_data(self, mock_get):
        """Test handling when no observations returned"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'observations': []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('INVALID')

        assert result is None

    @patch('src.collectors.fred.requests.Session.get')
    def test_get_observation_network_error(self, mock_get):
        """Test handling of network errors"""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('VIXCLS')

        assert result is None

    @patch('src.collectors.fred.requests.Session.get')
    def test_get_observation_invalid_json(self, mock_get):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('VIXCLS')

        assert result is None

    @patch('src.collectors.fred.requests.Session.get')
    def test_get_observation_parameters(self, mock_get):
        """Test that correct API parameters are sent"""
        mock_response = Mock()
        mock_response.json.return_value = {'observations': []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = FREDCollector(api_key="test_key")
        collector.get_latest_observation('VIXCLS', days_back=14)

        # Verify API was called with correct parameters
        call_args = mock_get.call_args
        params = call_args[1]['params']

        assert params['series_id'] == 'VIXCLS'
        assert params['api_key'] == 'test_key'
        assert params['file_type'] == 'json'
        assert params['sort_order'] == 'desc'
        assert params['limit'] == 1


class TestCollectAllIndicators:
    """Test cases for collecting all macro indicators"""

    @patch.object(FREDCollector, 'get_latest_observation')
    def test_collect_all_success(self, mock_get_obs):
        """Test collecting all indicators successfully"""
        # Mock successful observations for all indicators
        mock_get_obs.return_value = {
            'series_id': 'TEST',
            'date': '2025-12-20',
            'value': 15.5,
            'collected_at': datetime.now()
        }

        collector = FREDCollector(api_key="test_key")
        results = collector.collect_all_indicators()

        # Should have results for all indicators
        assert len(results) == len(FREDCollector.INDICATORS)
        assert 'VIX' in results
        assert 'UNEMPLOYMENT' in results
        assert 'TREASURY_10Y' in results

        # Each result should have complete data
        for indicator_name, data in results.items():
            assert 'value' in data
            assert 'name' in data
            assert 'threshold_low' in data
            assert 'threshold_high' in data

    @patch.object(FREDCollector, 'get_latest_observation')
    def test_collect_all_partial_failure(self, mock_get_obs):
        """Test collecting when some indicators fail"""
        # Return None for some indicators (failure)
        def side_effect(series_id):
            if series_id == 'VIXCLS':
                return {
                    'series_id': 'VIXCLS',
                    'date': '2025-12-20',
                    'value': 15.5,
                    'collected_at': datetime.now()
                }
            else:
                return None

        mock_get_obs.side_effect = side_effect

        collector = FREDCollector(api_key="test_key")
        results = collector.collect_all_indicators()

        # Should only have successful indicators
        assert 'VIX' in results
        assert len(results) < len(FREDCollector.INDICATORS)


class TestAssessMarketConditions:
    """Test cases for market condition assessment"""

    def test_assess_low_risk(self):
        """Test assessment with low risk conditions"""
        indicators = {
            'VIX': {
                'value': 12.0,  # Low volatility
                'threshold_low': 15,
                'threshold_high': 30
            },
            'UNEMPLOYMENT': {
                'value': 3.5,  # Low unemployment
                'threshold_low': 4.0,
                'threshold_high': 7.0
            },
            'TREASURY_10Y': {
                'value': 2.5,  # Moderate rates
                'threshold_low': 2.0,
                'threshold_high': 5.0
            }
        }

        collector = FREDCollector(api_key="test_key")
        assessment = collector.assess_market_conditions(indicators)

        assert assessment['risk_level'] == 'LOW'
        assert assessment['risk_score'] < 30
        assert len(assessment['conditions']) > 0
        assert len(assessment['recommendations']) > 0

    def test_assess_high_risk(self):
        """Test assessment with high risk conditions"""
        indicators = {
            'VIX': {
                'value': 35.0,  # High volatility
                'threshold_low': 15,
                'threshold_high': 30
            },
            'UNEMPLOYMENT': {
                'value': 8.0,  # High unemployment
                'threshold_low': 4.0,
                'threshold_high': 7.0
            },
            'TREASURY_10Y': {
                'value': 5.5,  # High rates
                'threshold_low': 2.0,
                'threshold_high': 5.0
            }
        }

        collector = FREDCollector(api_key="test_key")
        assessment = collector.assess_market_conditions(indicators)

        assert assessment['risk_level'] == 'HIGH'
        assert assessment['risk_score'] > 60
        assert len(assessment['warnings']) > 0

    def test_assess_medium_risk(self):
        """Test assessment with medium risk conditions"""
        indicators = {
            'VIX': {
                'value': 22.0,  # Moderate volatility
                'threshold_low': 15,
                'threshold_high': 30
            },
            'UNEMPLOYMENT': {
                'value': 5.0,  # Moderate unemployment
                'threshold_low': 4.0,
                'threshold_high': 7.0
            }
        }

        collector = FREDCollector(api_key="test_key")
        assessment = collector.assess_market_conditions(indicators)

        assert assessment['risk_level'] == 'MEDIUM'
        assert 30 <= assessment['risk_score'] <= 60

    def test_assess_empty_indicators(self):
        """Test assessment with no indicators"""
        indicators = {}

        collector = FREDCollector(api_key="test_key")
        assessment = collector.assess_market_conditions(indicators)

        # Should return default assessment
        assert assessment['risk_level'] == 'MEDIUM'
        assert assessment['risk_score'] == 50
        assert len(assessment['conditions']) == 0

    def test_assess_vix_thresholds(self):
        """Test VIX-specific threshold logic"""
        collector = FREDCollector(api_key="test_key")

        # Test low VIX (< 15)
        indicators = {'VIX': {'value': 12.0, 'threshold_low': 15, 'threshold_high': 30}}
        assessment = collector.assess_market_conditions(indicators)
        assert any('calm' in cond.lower() for cond in assessment['conditions'])

        # Test high VIX (> 30)
        indicators = {'VIX': {'value': 35.0, 'threshold_low': 15, 'threshold_high': 30}}
        assessment = collector.assess_market_conditions(indicators)
        assert any('high volatility' in cond.lower() for cond in assessment['conditions'])
        assert len(assessment['warnings']) > 0

    def test_assess_unemployment_thresholds(self):
        """Test unemployment-specific threshold logic"""
        collector = FREDCollector(api_key="test_key")

        # Test low unemployment (< 4.0)
        indicators = {'UNEMPLOYMENT': {'value': 3.5, 'threshold_low': 4.0, 'threshold_high': 7.0}}
        assessment = collector.assess_market_conditions(indicators)
        assert any('low unemployment' in cond.lower() for cond in assessment['conditions'])

        # Test high unemployment (> 7.0)
        indicators = {'UNEMPLOYMENT': {'value': 8.0, 'threshold_low': 4.0, 'threshold_high': 7.0}}
        assessment = collector.assess_market_conditions(indicators)
        assert any('high unemployment' in cond.lower() for cond in assessment['conditions'])
        assert len(assessment['warnings']) > 0


class TestClose:
    """Test cases for closing the collector"""

    def test_close(self):
        """Test closing the session"""
        collector = FREDCollector(api_key="test_key")
        mock_session = Mock()
        collector.session = mock_session

        collector.close()

        mock_session.close.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_null_api_key(self):
        """Test initialization with None API key"""
        collector = FREDCollector(api_key=None)
        assert collector.api_key is None

    def test_empty_api_key(self):
        """Test initialization with empty API key"""
        collector = FREDCollector(api_key="")
        assert collector.api_key == ""

    @patch('src.collectors.fred.requests.Session.get')
    def test_timeout_handling(self, mock_get):
        """Test handling of request timeouts"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('VIXCLS')

        assert result is None

    @patch('src.collectors.fred.requests.Session.get')
    def test_invalid_float_value(self, mock_get):
        """Test handling of values that can't convert to float"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'observations': [{
                'date': '2025-12-20',
                'value': 'invalid'
            }]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        collector = FREDCollector(api_key="test_key")
        result = collector.get_latest_observation('VIXCLS')

        assert result is None
