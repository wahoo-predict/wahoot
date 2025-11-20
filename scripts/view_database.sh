#!/bin/bash
# View validator database contents

DB_PATH=${VALIDATOR_DB_PATH:-validator.db}

if [ ! -f "$DB_PATH" ]; then
    echo "Database not found at: $DB_PATH"
    echo "Create one by running the validator or tests"
    exit 1
fi

echo "=========================================="
echo "Validator Database Viewer"
echo "=========================================="
echo "Database: $DB_PATH"
echo ""

# Check if sqlite3 is available
if ! command -v sqlite3 &> /dev/null; then
    echo "ERROR: sqlite3 not found. Install with: sudo apt-get install sqlite3"
    exit 1
fi

echo "Tables in database:"
sqlite3 "$DB_PATH" ".tables"
echo ""

echo "=========================================="
echo "Hotkeys Table"
echo "=========================================="
sqlite3 "$DB_PATH" "SELECT * FROM hotkeys LIMIT 10;" 2>/dev/null || echo "Table 'hotkeys' not found"
echo ""

echo "=========================================="
echo "Validation Cache (Recent)"
echo "=========================================="
sqlite3 "$DB_PATH" "SELECT hotkey, timestamp, substr(data_json, 1, 100) as data_preview FROM validation_cache ORDER BY timestamp DESC LIMIT 5;" 2>/dev/null || echo "Table 'validation_cache' not found"
echo ""

echo "=========================================="
echo "Performance Snapshots (Recent)"
echo "=========================================="
sqlite3 "$DB_PATH" "SELECT hotkey, timestamp, total_volume_usd, realized_profit_usd, win_rate FROM performance_snapshots ORDER BY timestamp DESC LIMIT 5;" 2>/dev/null || echo "Table 'performance_snapshots' not found"
echo ""

echo "=========================================="
echo "Database Statistics"
echo "=========================================="
sqlite3 "$DB_PATH" "
SELECT 
    'Hotkeys' as table_name, 
    COUNT(*) as count 
FROM hotkeys
UNION ALL
SELECT 
    'Validation Cache', 
    COUNT(*) 
FROM validation_cache
UNION ALL
SELECT 
    'Performance Snapshots', 
    COUNT(*) 
FROM performance_snapshots;
" 2>/dev/null || echo "Could not get statistics"
echo ""

echo "To explore interactively, run:"
echo "  sqlite3 $DB_PATH"
echo ""

