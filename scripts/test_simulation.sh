#!/bin/bash
# Quick test of the simulation setup

set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=========================================="
echo "Testing Simulation Setup"
echo "=========================================="
echo ""

# Test 1: Check mock API
echo "[1/3] Testing mock API server..."
if curl -s "http://localhost:8000/events" > /dev/null 2>&1; then
    echo "✅ Mock API is running"
    curl -s "http://localhost:8000/events" | python -m json.tool | head -10
else
    echo "❌ Mock API not running"
    echo "   Start it: ./scripts/start_mock_api.sh"
fi
echo ""

# Test 2: Check database
echo "[2/3] Testing database..."
if [ -f "validator.db" ]; then
    echo "✅ Database exists"
    COUNT=$(sqlite3 validator.db "SELECT COUNT(*) FROM miners;" 2>/dev/null || echo "0")
    echo "   Miners in database: $COUNT"
else
    echo "⚠️  Database doesn't exist (will be created on first run)"
fi
echo ""

# Test 3: Check validator can start
echo "[3/3] Testing validator import..."
if python -c "from wahoo.validator.validator import main; print('OK')" 2>/dev/null; then
    echo "✅ Validator can be imported"
else
    echo "❌ Validator import failed"
    echo "   Activate venv: source .venv/bin/activate"
    echo "   Install: pip install -e '.[dev]'"
fi
echo ""

echo "=========================================="
echo "Ready to simulate!"
echo "=========================================="
echo ""
echo "Run full simulation:"
echo "  ./scripts/simulate_full_flow.sh"
echo ""

