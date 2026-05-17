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

    # Default hardcoded column indices (fallback when header detection fails)
    _DEFAULT_COLUMN_MAP: Dict[str, int] = {
        'filing_date': 1,
        'trade_date': 2,
        'ticker': 3,
        'insider_name': 5,
        'insider_title': 6,
        'trade_type': 7,
        'price': 8,
        'shares': 9,
        'ownership_change_pct': 11,
        'value': 12,
    }

    # Mapping from canonical field names to possible header text patterns
    _HEADER_PATTERNS: Dict[str, List[str]] = {
        'filing_date': ['filing date', 'filing\ndate', 'filingdate'],
        'trade_date': ['trade date', 'trade\ndate', 'tradedate'],
        'ticker': ['ticker'],
        'insider_name': ['insider name', 'insider\nname', 'insidername', 'owner name', 'owner\nname'],
        'insider_title': ['title'],
        'trade_type': ['trade type', 'trade\ntype', 'tradetype', 'type'],
        'price': ['price'],
        'shares': ['qty', 'shares', 'quantity'],
        'ownership_change_pct': ['owned', 'δown', 'own change', 'ownchange', '%own'],
        'value': ['value', 'value (usd)', 'value(usd)'],
    }

    def _detect_column_map(self, table) -> Dict[str, int]:
        """
        @brief Detect column indices by reading the table header row.
        @param table BeautifulSoup table element
        @return Mapping from canonical field name to column index.
                Falls back to _DEFAULT_COLUMN_MAP if detection fails.
        """
        # Try <thead> first, then fall back to first <tr>
        header_row = None
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
        if not header_row:
            first_row = table.find('tr')
            if first_row and first_row.find('th'):
                header_row = first_row

        if not header_row:
            logger.warning("OpenInsider: no header row detected, using hardcoded column indices")
            return dict(self._DEFAULT_COLUMN_MAP)

        header_cells = header_row.find_all(['th', 'td'])
        if not header_cells:
            logger.warning("OpenInsider: header row has no cells, using hardcoded column indices")
            return dict(self._DEFAULT_COLUMN_MAP)

        # Normalize header text: lowercase, collapse whitespace
        headers = []
        for cell in header_cells:
            text = cell.get_text(separator=' ').strip().lower()
            # Collapse multiple spaces / newlines into single space
            text = ' '.join(text.split())
            headers.append(text)

        logger.debug(f"OpenInsider detected headers ({len(headers)} cols): {headers}")

        # Build the mapping
        column_map: Dict[str, int] = {}
        for field, patterns in self._HEADER_PATTERNS.items():
            for idx, header_text in enumerate(headers):
                if any(pat in header_text for pat in patterns):
                    column_map[field] = idx
                    break

        # Validate: we need at least ticker, trade_date, and value to be useful
        required = {'ticker', 'trade_date', 'value'}
        missing = required - set(column_map.keys())
        if missing:
            logger.warning(
                f"OpenInsider: header detection missing required columns {missing}, "
                f"falling back to hardcoded indices. Detected: {column_map}"
            )
            return dict(self._DEFAULT_COLUMN_MAP)

        # Fill any non-required missing fields from defaults
        for field, default_idx in self._DEFAULT_COLUMN_MAP.items():
            if field not in column_map:
                logger.debug(f"OpenInsider: column '{field}' not found in headers, using default index {default_idx}")
                column_map[field] = default_idx

        logger.info(f"OpenInsider: header detection successful, mapped {len(column_map)} columns")
        return column_map

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

            # Detect column layout from header row
            col = self._detect_column_map(table)

            results = []
            rows = table.find_all('tr')[1:]  # Skip header row

            # Log table structure for first row (debugging)
            if rows and len(rows) > 0:
                first_cells = rows[0].find_all('td')
                logger.debug(f"Table has {len(rows)} data rows, first row has {len(first_cells)} columns")

            for row_idx, row in enumerate(rows):
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                try:
                    # Extract ticker using detected column index
                    ticker = None
                    ticker_link = None

                    ticker_idx = col.get('ticker', 3)
                    if len(cells) > ticker_idx:
                        ticker_link = cells[ticker_idx].find('a')
                        if ticker_link:
                            ticker = ticker_link.text.strip().upper()

                    # If not found at detected index, search all cells for a ticker-like link
                    if not ticker:
                        for cell in cells[:8]:  # Check first 8 columns
                            link = cell.find('a')
                            if link and link.get('href', '').startswith('http://openinsider.com/screener'):
                                potential_ticker = link.text.strip().upper()
                                # Tickers are typically 1-5 uppercase letters
                                if potential_ticker and len(potential_ticker) <= 5 and potential_ticker.isalpha():
                                    ticker = potential_ticker
                                    ticker_link = link
                                    break

                    if not ticker:
                        if row_idx == 0:  # Only log first failed row to avoid spam
                            logger.debug(f"No ticker found in row {row_idx}")
                        continue

                    # Parse trade data using detected column mapping
                    trade_data = {
                        'ticker': ticker,
                        'filing_date': self._parse_date(cells[col['filing_date']].text.strip()) if len(cells) > col['filing_date'] else None,
                        'trade_date': self._parse_date(cells[col['trade_date']].text.strip()) if len(cells) > col['trade_date'] else None,
                        'insider_name': cells[col['insider_name']].text.strip() if not is_cluster and len(cells) > col['insider_name'] else '',
                        'insider_title': cells[col['insider_title']].text.strip() if not is_cluster and len(cells) > col['insider_title'] else '',
                        'trade_type': cells[col['trade_type']].text.strip() if len(cells) > col['trade_type'] else '',
                        'price': self._parse_float(cells[col['price']].text) if len(cells) > col['price'] else 0.0,
                        'shares': self._parse_int(cells[col['shares']].text) if len(cells) > col['shares'] else 0,
                        'value': self._parse_int(cells[col['value']].text) if len(cells) > col['value'] else 0,
                        'ownership_change_pct': self._parse_float(cells[col['ownership_change_pct']].text) if len(cells) > col['ownership_change_pct'] else 0.0,
                        'is_cluster_buy': is_cluster,
                        'collected_at': datetime.now()
                    }

                    # Skip rows where trade_date could not be parsed —
                    # a None trade_date would otherwise appear as "today",
                    # triggering false signals on malformed historical rows.
                    if trade_data['trade_date'] is None:
                        logger.debug(f"Skipping row {row_idx}: unparseable trade_date")
                        continue

                    # Debug first parsed row
                    if row_idx == 0:
                        logger.debug(f"First row parsed: {ticker}, type={trade_data['trade_type']}, value={trade_data['value']}")

                    # Only collect purchases (P - Purchase)
                    trade_type_full = trade_data['trade_type'].upper()
                    if ('P' in trade_type_full or 'PURCHASE' in trade_type_full) and trade_data['value'] > 0:
                        # Normalize trade_type to 'P' for database consistency
                        trade_data['trade_type'] = 'P'
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

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        @brief Parse date string from OpenInsider
        @param date_str Date string in YYYY-MM-DD format
        @return datetime object, or None if parsing fails
        """
        try:
            cleaned = date_str.strip()
            return datetime.strptime(cleaned, '%Y-%m-%d')
        except (ValueError, AttributeError):
            logger.debug(f"Could not parse date: {date_str}")
            return None

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
