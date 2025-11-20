#!/bin/bash
# Simple commands that work - no interactive Python needed!

set -e

echo "=========================================="
echo "Simple Commands for WaHoo Validator"
echo "=========================================="
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠ No virtual environment found"
fi

echo ""
echo "Available commands:"
echo ""
echo "1. Run all tests:"
echo "   ./scripts/run_tests.sh all -v"
echo ""
echo "2. View database:"
echo "   python scripts/explore_database.py"
echo ""
echo "3. Test mock data generation:"
echo "   python scripts/test_mock_data.py"
echo ""
echo "4. View validator help:"
echo "   python -m wahoo.validator.validator --help"
echo ""
echo "5. View database tables:"
echo "   sqlite3 validator.db '.tables'"
echo ""
echo "6. View database schema:"
echo "   sqlite3 validator.db '.schema miners'"
echo ""

# Run a quick test if requested
if [ "$1" == "test" ]; then
    echo "Running quick test..."
    python scripts/test_mock_data.py
fi

