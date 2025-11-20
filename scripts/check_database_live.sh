#!/bin/bash
# Check database while simulation is running

set -e

echo "=========================================="
echo "Validator Database - Live Check"
echo "=========================================="
echo ""

DB_PATH=${VALIDATOR_DB_PATH:-validator.db}

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found: $DB_PATH"
    echo "   Wait for validator to create it (first loop iteration)"
    exit 1
fi

echo "Database: $DB_PATH"
echo "Last updated: $(stat -c %y "$DB_PATH" 2>/dev/null || stat -f "%Sm" "$DB_PATH" 2>/dev/null)"
echo ""

# Activate venv if needed
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the explore script
python scripts/explore_database.py

