"""
@file openinsider.py
@brief OpenInsider web scraper for insider trading data
@details Scrapes insider buying and selling activity from openinsider.com
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)


class OpenInsiderCollector:
    """
    @class OpenInsiderCollector
    @brief Web scraper for insider trading data
    @details Scrapes insider transactions from openinsider.com with respectful rate limiting
    """

    BASE_URL = "http://openinsider.com"

    def __init__(self, timeout: int = 30):
        """
        @brief Initialize OpenInsider collector
        @param timeout Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

    def collect_cluster_buys(self) -> List[Dict]:
        """
        @brief Scrape latest cluster buys (multiple insiders buying same stock)
        @return List of insider trade dictionaries
        """
        url = f"{self.BASE_URL}/latest-cluster-buys"
        logger.info(f"Scraping cluster buys from {url}")
        return self._scrape_table(url, is_cluster=True)

    def collect_ceo_cfo_buys(self, min_value: int = 25000) -> List[Dict]:
        """
        @brief Scrape CEO/CFO purchases over minimum value
        @param min_value Minimum transaction value in dollars
        @return List of insider trade dictionaries
        """
        url = f"{self.BASE_URL}/latest-ceo-cfo-purchases-25k"
        logger.info(f"Scraping CEO/CFO buys from {url}")
        return self._scrape_table(url, is_cluster=False)

    def collect_insider_purchases(self, min_value: int = 25000, days: int = 7) -> List[Dict]:
        """
        @brief Scrape all insider purchases over minimum value
        @param min_value Minimum transaction value
        @param days Number of days to look back
        @return List of insider trade dictionaries
        """
        url = (f"{self.BASE_URL}/screener?s=&o=&pl=&ph=&ll=&lh=&fd={days}&fdr=&td=0&tdr=&"
               f"xp=1&vl={min_value}&vh=&ocl=&och=&sic1=-1&sic2=-1&sic3=-1&sic4=-1&"
               f"sort=trade_date&order=desc")
        logger.info(f"Scraping insider purchases from screener")
        return self._scrape_table(url, is_cluster=False)

    def _scrape_table(self, url: str, is_cluster: bool = False) -> List[Dict]:
        """
        @brief Parse insider trading table from OpenInsider page
        @param url Page URL to scrape
        @param is_cluster Whether this is cluster buy data
        @return List of insider trade dictionaries
        @throws requests.RequestException on network errors
        """
        try:
            # Be respectful - add small delay
            time.sleep(1)

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='tinytable')

            if not table:
                logger.warning(f"No table found at {url}")
                return []

            results = []
            rows = table.find_all('tr')[1:]  # Skip header row

            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                try:
                    # Extract ticker from link
                    ticker_link = cells[3].find('a')
                    if not ticker_link:
                        continue

                    ticker = ticker_link.text.strip().upper()
                    if not ticker:
                        continue

                    # Parse trade data
                    trade_data = {
                        'ticker': ticker,
                        'filing_date': self._parse_date(cells[1].text.strip()),
                        'trade_date': self._parse_date(cells[2].text.strip()),
                        'insider_name': cells[4].text.strip(),
                        'insider_title': cells[5].text.strip(),
                        'trade_type': cells[6].text.strip(),  # P = Purchase, S = Sale
                        'price': self._parse_float(cells[7].text),
                        'shares': self._parse_int(cells[8].text),
                        'value': self._parse_int(cells[9].text),
                        'ownership_change_pct': self._parse_float(cells[10].text) if len(cells) > 10 else 0.0,
                        'is_cluster_buy': is_cluster,
                        'collected_at': datetime.now()
                    }

                    # Only collect purchases (P = Purchase)
                    if trade_data['trade_type'] == 'P' and trade_data['value'] > 0:
                        results.append(trade_data)

                except (IndexError, ValueError, AttributeError) as e:
                    logger.debug(f"Row parse error: {e}")
                    continue

            logger.info(f"Successfully scraped {len(results)} insider trades")
            return results

        except requests.RequestException as e:
            logger.error(f"OpenInsider scrape error for {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping OpenInsider: {e}")
            return []

    def _parse_date(self, date_str: str) -> datetime:
        """
        @brief Parse date string from OpenInsider
        @param date_str Date string in YYYY-MM-DD format
        @return datetime object
        """
        try:
            cleaned = date_str.strip()
            return datetime.strptime(cleaned, '%Y-%m-%d')
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse date: {date_str}")
            return datetime.now()

    def _parse_float(self, value_str: str) -> float:
        """
        @brief Parse float from string, handling $, commas, %
        @param value_str String containing numeric value
        @return Parsed float value or 0.0 on error
        """
        try:
            cleaned = value_str.replace('$', '').replace(',', '').replace('%', '').replace('+', '').strip()
            return float(cleaned) if cleaned and cleaned not in ['-', 'N/A'] else 0.0
        except (ValueError, AttributeError):
            return 0.0

    def _parse_int(self, value_str: str) -> int:
        """
        @brief Parse integer from string, handling commas and formatting
        @param value_str String containing numeric value
        @return Parsed integer value or 0 on error
        """
        try:
            cleaned = value_str.replace('$', '').replace(',', '').replace('+', '').strip()
            return int(float(cleaned)) if cleaned and cleaned not in ['-', 'N/A'] else 0
        except (ValueError, AttributeError):
            return 0

    def close(self):
        """
        @brief Close session and cleanup resources
        """
        if self.session:
            self.session.close()
