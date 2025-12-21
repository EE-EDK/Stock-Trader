-- Macro Economic Indicators Schema
-- Stores data from FRED and other macro sources

CREATE TABLE IF NOT EXISTS macro_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_name TEXT NOT NULL,              -- VIX, UNEMPLOYMENT, etc.
    series_id TEXT NOT NULL,                   -- FRED series ID (e.g., 'VIXCLS')
    value REAL NOT NULL,                       -- Indicator value
    observation_date DATE NOT NULL,            -- Date of observation
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(indicator_name, observation_date)   -- One value per indicator per day
);

CREATE TABLE IF NOT EXISTS market_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_date DATE NOT NULL UNIQUE,      -- Date of assessment
    risk_level TEXT NOT NULL,                  -- LOW, MEDIUM, HIGH
    risk_score INTEGER NOT NULL,               -- 0-100
    conditions TEXT,                           -- JSON array of conditions
    warnings TEXT,                             -- JSON array of warnings
    recommendations TEXT,                      -- JSON array of recommendations
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_macro_indicator_date
    ON macro_indicators(indicator_name, observation_date DESC);

CREATE INDEX IF NOT EXISTS idx_assessment_date
    ON market_assessments(assessment_date DESC);
