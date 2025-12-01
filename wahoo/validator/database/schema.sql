-- Enable WAL mode for better write concurrency
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS miners (
    hotkey TEXT PRIMARY KEY,
    uid INTEGER,
    last_signature TEXT,
    last_message TEXT,
    first_seen_ts TEXT, -- ISO8601 string; SQLite stores as TEXT
    last_seen_ts TEXT,
    axon_ip TEXT
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotkey TEXT NOT NULL,
    timestamp TEXT NOT NULL,  -- ISO8601 'YYYY-MM-DDTHH:MM:SSZ'
    
    total_volume_usd REAL,
    trade_count INTEGER,
    realized_profit_usd REAL,
    unrealized_profit_usd REAL,
    win_rate REAL,
    total_fees_paid_usd REAL,
    open_positions_count INTEGER,
    referral_count INTEGER,
    referral_volume REAL,

    volume_delta REAL,
    profit_delta REAL,
    trade_delta INTEGER,
    activity_score REAL,

    FOREIGN KEY(hotkey) REFERENCES miners(hotkey)
);

CREATE INDEX IF NOT EXISTS idx_perf_hotkey_ts
    ON performance_snapshots(hotkey, timestamp);

CREATE TABLE IF NOT EXISTS scoring_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    hotkey TEXT NOT NULL,
    score REAL,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_scoring_hotkey_ts
    ON scoring_runs(hotkey, ts DESC);


