#!/bin/bash
# Quick view of miner data in database

DB_PATH=${VALIDATOR_DB_PATH:-validator.db}

if [ ! -f "$DB_PATH" ]; then
    echo "Database not found. Run: python scripts/populate_test_data.py"
    exit 1
fi

echo "=========================================="
echo "Miner Data in Database"
echo "=========================================="
echo ""

echo "=== Miners Table ==="
sqlite3 "$DB_PATH" -header -column "SELECT hotkey, uid, first_seen_ts, last_seen_ts FROM miners LIMIT 10;"
echo ""

echo "=== Performance Data (Top 10 by Volume) ==="
sqlite3 "$DB_PATH" -header -column "
SELECT 
    hotkey,
    total_volume_usd as 'Volume ($)',
    realized_profit_usd as 'Profit ($)',
    trade_count as 'Trades',
    open_positions_count as 'Open',
    win_rate as 'Win Rate'
FROM performance_snapshots 
ORDER BY total_volume_usd DESC 
LIMIT 10;
"
echo ""

echo "=== Summary Statistics ==="
sqlite3 "$DB_PATH" "
SELECT 
    COUNT(*) as 'Total Miners',
    SUM(total_volume_usd) as 'Total Volume ($)',
    SUM(realized_profit_usd) as 'Total Profit ($)',
    AVG(win_rate) as 'Avg Win Rate'
FROM performance_snapshots;
"
echo ""

