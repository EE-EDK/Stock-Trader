import sqlite3
import os

db_path = 'data/sentiment.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['mentions', 'insiders', 'prices', 'velocity', 'signals', 'paper_trades', 'macro_indicators']

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Table {table:16}: {count:6} rows")
    except sqlite3.OperationalError as e:
        print(f"Table {table:16}: ERROR ({e})")

conn.close()
