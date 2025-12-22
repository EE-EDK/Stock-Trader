-- Congress Stock Trades Schema
-- Tracks stock trades made by US Congress members (House + Senate)
-- Data sources: House Stock Watcher API (FREE), Finnhub Congress API (FREE)

CREATE TABLE IF NOT EXISTS congress_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Member information
    representative_name TEXT NOT NULL,
    party TEXT,
    chamber TEXT CHECK(chamber IN ('house', 'senate')),
    state TEXT,
    district TEXT,

    -- Trade details
    ticker TEXT NOT NULL,
    asset_name TEXT,
    transaction_type TEXT CHECK(transaction_type IN ('purchase', 'sale', 'exchange')),
    transaction_date DATE NOT NULL,
    filing_date DATE,
    disclosure_date DATE,

    -- Amount (range since exact amounts not always disclosed)
    amount_from REAL,
    amount_to REAL,
    amount_mid REAL,  -- Midpoint for calculations

    -- Additional context
    owner TEXT,  -- self, spouse, dependent, joint
    position TEXT,
    asset_type TEXT,  -- stock, options, bond, etc

    -- Metadata
    source TEXT DEFAULT 'housestockwatcher',
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicates
    UNIQUE(representative_name, ticker, transaction_date, transaction_type, amount_from)
);

-- Index for fast ticker lookups
CREATE INDEX IF NOT EXISTS idx_congress_ticker_date
ON congress_trades(ticker, transaction_date);

-- Index for representative lookups
CREATE INDEX IF NOT EXISTS idx_congress_rep_date
ON congress_trades(representative_name, transaction_date);

-- Index for recent trades
CREATE INDEX IF NOT EXISTS idx_congress_collected
ON congress_trades(collected_at DESC);

-- Aggregate view: Congress activity per ticker
CREATE VIEW IF NOT EXISTS congress_ticker_activity AS
SELECT
    ticker,
    COUNT(*) as total_trades,
    SUM(CASE WHEN transaction_type = 'purchase' THEN 1 ELSE 0 END) as buy_count,
    SUM(CASE WHEN transaction_type = 'sale' THEN 1 ELSE 0 END) as sell_count,
    SUM(CASE WHEN transaction_type = 'purchase' THEN amount_mid ELSE 0 END) as total_buys,
    SUM(CASE WHEN transaction_type = 'sale' THEN amount_mid ELSE 0 END) as total_sells,
    COUNT(DISTINCT representative_name) as unique_members,
    MAX(transaction_date) as latest_trade_date,
    MIN(transaction_date) as earliest_trade_date
FROM congress_trades
GROUP BY ticker;
