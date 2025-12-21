-- Paper Trading Tables
-- Track simulated trades to validate signal performance before using real capital

-- Main paper trades table
CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,

    -- Entry details
    entry_date DATETIME NOT NULL,
    entry_price REAL NOT NULL,
    shares INTEGER NOT NULL,
    conviction INTEGER NOT NULL,
    signal_types TEXT NOT NULL,        -- JSON array of trigger types

    -- Position details
    position_size REAL NOT NULL,       -- Dollar amount invested
    stop_loss REAL,                    -- Stop loss price
    target_price REAL,                 -- Take profit price

    -- Exit details (NULL if still open)
    exit_date DATETIME,
    exit_price REAL,
    exit_reason TEXT,                  -- 'time_limit', 'stop_loss', 'take_profit', 'manual'

    -- Performance metrics
    return_pct REAL,
    profit_loss REAL,
    days_held INTEGER,

    -- Metadata
    status TEXT DEFAULT 'open',        -- 'open', 'closed'
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Ensure no duplicate trades for same signal
    UNIQUE(ticker, entry_date)
);

-- Daily price snapshots for open positions
CREATE TABLE IF NOT EXISTS paper_trade_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    snapshot_date DATETIME NOT NULL,
    current_price REAL NOT NULL,
    unrealized_pnl REAL,
    unrealized_pct REAL,
    FOREIGN KEY (trade_id) REFERENCES paper_trades(id),
    UNIQUE(trade_id, snapshot_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status);
CREATE INDEX IF NOT EXISTS idx_paper_trades_ticker ON paper_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_paper_trades_entry_date ON paper_trades(entry_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_trade_date ON paper_trade_snapshots(trade_id, snapshot_date);
