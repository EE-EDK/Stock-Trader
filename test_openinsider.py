#!/usr/bin/env python3
"""Quick test to debug OpenInsider parsing"""

import requests
from bs4 import BeautifulSoup
import time

url = "http://openinsider.com/latest-cluster-buys"
print(f"Testing: {url}\n")

try:
    time.sleep(1)
    response = requests.get(url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', class_='tinytable')
    if not table:
        print("No table found!")
        exit(1)

    rows = table.find_all('tr')
    print(f"Total rows: {len(rows)}\n")

    # Check header row
    print("Header row:")
    header_cells = rows[0].find_all('th')
    for i, th in enumerate(header_cells):
        print(f"  [{i}] {th.text.strip()}")

    print(f"\nFirst data row analysis:")
    first_data_row = rows[1]
    cells = first_data_row.find_all('td')
    print(f"Number of cells: {len(cells)}\n")

    for i, cell in enumerate(cells[:12]):  # First 12 cells
        text = cell.text.strip()[:50]
        link = cell.find('a')
        print(f"  [{i}] Text: '{text}'")
        if link:
            print(f"       Link: {link.get('href')} -> {link.text.strip()}")

    # Try to find ticker
    print(f"\nLooking for ticker (expected at index 3):")
    if len(cells) > 3:
        ticker_cell = cells[3]
        ticker_link = ticker_cell.find('a')
        if ticker_link:
            print(f"  ✓ Found ticker link: {ticker_link.text.strip()}")
        else:
            print(f"  ✗ No link in cell 3. Text: '{ticker_cell.text.strip()}'")
            # Try other cells
            for i, cell in enumerate(cells):
                links = cell.find_all('a')
                if links:
                    print(f"  Cell [{i}] has {len(links)} link(s):")
                    for link in links:
                        print(f"    -> {link.text.strip()} ({link.get('href')})")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
