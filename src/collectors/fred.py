"""
@file fred.py
@brief FRED (Federal Reserve Economic Data) Collector
@details Collects macro economic indicators from FRED API to assess market conditions
@see https://fred.stlouisfed.org/docs/api/fred/
"""

import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class FREDCollector:
    """
    @brief Collects macro economic indicators from FRED API
    @details FREE API - requires registration at https://fred.stlouisfed.org/docs/api/api_key.html

    Key indicators collected:
    - VIX: Market volatility (fear index)
    - DGS10: 10-Year Treasury Rate
    - UNRATE: Unemployment Rate
    - CPIAUCSL: Consumer Price Index (inflation)
    - DEXUSEU: USD/EUR Exchange Rate

    API limits: 120 requests per minute (free tier)
    """

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    # Key economic indicators to track
    INDICATORS = {
        'VIX': {
            'series_id': 'VIXCLS',
            'name': 'CBOE Volatility Index',
            'description': 'Market fear gauge - higher = more volatile',
            'threshold_low': 15,   # Calm market
            'threshold_high': 30   # High volatility
        },
        'TREASURY_10Y': {
            'series_id': 'DGS10',
            'name': '10-Year Treasury Constant Maturity Rate',
            'description': 'Risk-free rate benchmark',
            'threshold_low': 2.0,
            'threshold_high': 5.0
        },
        'UNEMPLOYMENT': {
            'series_id': 'UNRATE',
            'name': 'Unemployment Rate',
            'description': 'Economic health indicator',
            'threshold_low': 4.0,  # Strong economy
            'threshold_high': 7.0  # Weak economy
        },
        'INFLATION': {
            'series_id': 'CPIAUCSL',
            'name': 'Consumer Price Index',
            'description': 'Inflation measure',
            'threshold_low': 2.0,
            'threshold_high': 4.0
        },
        'USD_EUR': {
            'series_id': 'DEXUSEU',
            'name': 'US Dollar to Euro Exchange Rate',
            'description': 'Dollar strength indicator',
            'threshold_low': 0.85,
            'threshold_high': 1.15
        }
    }

    def __init__(self, api_key: str):
        """
        @brief Initialize FRED collector
        @param api_key FRED API key (free from fred.stlouisfed.org)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.request_count = 0
        self.last_request_time = time.time()

    def _rate_limit(self):
        """
        @brief Enforce rate limiting (120 requests per minute)
        @details Sleeps if necessary to avoid hitting rate limits
        """
        self.request_count += 1

        # Reset counter every minute
        current_time = time.time()
        if current_time - self.last_request_time >= 60:
            self.request_count = 0
            self.last_request_time = current_time

        # If approaching limit, sleep
        if self.request_count >= 115:  # Leave some buffer
            sleep_time = 60 - (current_time - self.last_request_time)
            if sleep_time > 0:
                logger.info(f"Rate limit approaching, sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()

    def get_latest_observation(self, series_id: str, days_back: int = 30) -> Optional[Dict]:
        """
        @brief Get most recent observation for a FRED series
        @param series_id FRED series ID (e.g., 'VIXCLS')
        @param days_back How many days back to search for data
        @return Dictionary with date and value, or None if error
        """
        self._rate_limit()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'observation_start': start_date.strftime('%Y-%m-%d'),
            'observation_end': end_date.strftime('%Y-%m-%d'),
            'sort_order': 'desc',  # Most recent first
            'limit': 1
        }

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            if 'observations' not in data or not data['observations']:
                logger.warning(f"No observations found for {series_id}")
                return None

            obs = data['observations'][0]

            # Handle missing or invalid values
            if obs['value'] == '.' or obs['value'] is None:
                logger.warning(f"Invalid value for {series_id}: {obs['value']}")
                return None

            return {
                'series_id': series_id,
                'date': obs['date'],
                'value': float(obs['value']),
                'collected_at': datetime.now()
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {series_id} from FRED: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing FRED response for {series_id}: {e}")
            return None

    def collect_all_indicators(self) -> Dict[str, Dict]:
        """
        @brief Collect all key macro indicators
        @return Dictionary of indicator_name -> observation data
        """
        logger.info("Collecting FRED macro indicators...")
        results = {}

        for indicator_name, indicator_info in self.INDICATORS.items():
            series_id = indicator_info['series_id']

            observation = self.get_latest_observation(series_id)

            if observation:
                results[indicator_name] = {
                    **observation,
                    'name': indicator_info['name'],
                    'description': indicator_info['description'],
                    'threshold_low': indicator_info['threshold_low'],
                    'threshold_high': indicator_info['threshold_high']
                }
                logger.info(f"  {indicator_name}: {observation['value']} ({observation['date']})")
            else:
                logger.warning(f"  Failed to collect {indicator_name}")

        return results

    def assess_market_conditions(self, indicators: Dict[str, Dict]) -> Dict:
        """
        @brief Assess overall market conditions based on indicators
        @param indicators Dictionary of indicator data from collect_all_indicators()
        @return Dictionary with market condition assessment
        """
        assessment = {
            'risk_level': 'MEDIUM',  # LOW, MEDIUM, HIGH
            'risk_score': 50,  # 0-100 (0=lowest risk, 100=highest risk)
            'conditions': [],
            'warnings': [],
            'recommendations': []
        }

        risk_points = 0
        max_points = 0

        # VIX assessment
        if 'VIX' in indicators:
            vix = indicators['VIX']['value']
            max_points += 20

            if vix < 15:
                assessment['conditions'].append("Low volatility (calm market)")
                risk_points += 0
            elif vix < 20:
                assessment['conditions'].append("Normal volatility")
                risk_points += 5
            elif vix < 30:
                assessment['conditions'].append("Elevated volatility")
                risk_points += 12
                assessment['warnings'].append("Increased market volatility")
            else:
                assessment['conditions'].append("High volatility (fear in market)")
                risk_points += 20
                assessment['warnings'].append("Very high market volatility - consider reducing positions")

        # Unemployment assessment
        if 'UNEMPLOYMENT' in indicators:
            unemp = indicators['UNEMPLOYMENT']['value']
            max_points += 20

            if unemp < 4.0:
                assessment['conditions'].append("Low unemployment (strong economy)")
                risk_points += 0
            elif unemp < 5.5:
                assessment['conditions'].append("Moderate unemployment")
                risk_points += 5
            elif unemp < 7.0:
                assessment['conditions'].append("Elevated unemployment")
                risk_points += 12
                assessment['warnings'].append("Rising unemployment may indicate economic slowdown")
            else:
                assessment['conditions'].append("High unemployment (weak economy)")
                risk_points += 20
                assessment['warnings'].append("High unemployment - recession risk")

        # Interest rates assessment
        if 'TREASURY_10Y' in indicators:
            rate = indicators['TREASURY_10Y']['value']
            max_points += 15

            if rate < 2.0:
                assessment['conditions'].append("Low interest rates")
                risk_points += 0
            elif rate < 4.0:
                assessment['conditions'].append("Moderate interest rates")
                risk_points += 5
            elif rate < 5.0:
                assessment['conditions'].append("Elevated interest rates")
                risk_points += 10
                assessment['warnings'].append("Rising rates may pressure equity valuations")
            else:
                assessment['conditions'].append("High interest rates")
                risk_points += 15
                assessment['warnings'].append("High rates - consider bonds over stocks")

        # Calculate final risk score
        if max_points > 0:
            assessment['risk_score'] = int((risk_points / max_points) * 100)

        # Determine risk level
        if assessment['risk_score'] < 30:
            assessment['risk_level'] = 'LOW'
            assessment['recommendations'].append("Favorable conditions for aggressive trading")
        elif assessment['risk_score'] < 60:
            assessment['risk_level'] = 'MEDIUM'
            assessment['recommendations'].append("Normal market conditions - standard position sizing")
        else:
            assessment['risk_level'] = 'HIGH'
            assessment['recommendations'].append("Elevated risk - consider reducing position sizes or staying in cash")

        return assessment

    def close(self):
        """
        @brief Close the session
        """
        self.session.close()
