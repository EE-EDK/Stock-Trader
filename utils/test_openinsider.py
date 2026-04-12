import requests
from bs4 import BeautifulSoup

def test_openinsider():
    urls = [
        "http://openinsider.com/latest-cluster-buys",
        "http://openinsider.com/latest-ceo-cfo-purchases-25k"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    for url in urls:
        try:
            print(f"\nTesting {url}...")
            response = requests.get(url, headers=headers, timeout=15)
            print(f"Status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='tinytable')
            
            if table:
                rows = table.find_all('tr')[1:]
                print(f"Found {len(rows)} rows in table.")
                if rows:
                    cells = rows[0].find_all('td')
                    print(f"First row has {len(cells)} cells.")
                    for i, cell in enumerate(cells):
                        print(f"Cell {i}: {cell.text.strip()}")
            else:
                print("No table found.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_openinsider()
