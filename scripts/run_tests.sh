#!/bin/bash
# Run comprehensive validator tests

set -e

echo "=========================================="
echo "WaHoo Predict - Test Suite Runner"
echo "=========================================="
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Test categories
TESTS_VALIDATOR_LOOP="tests/test_validator_loop.py"
TESTS_DATABASE="tests/test_validator_database.py"
TESTS_INTEGRATION="tests/test_validator_integration.py"
TESTS_ALL="tests/"

# Parse arguments
TEST_TYPE=${1:-all}
VERBOSE=${2:-"-v"}

case "$TEST_TYPE" in
    loop)
        echo "Running validator loop tests..."
        pytest $TESTS_VALIDATOR_LOOP $VERBOSE
        ;;
    database)
        echo "Running database tests..."
        pytest $TESTS_DATABASE $VERBOSE
        ;;
    integration)
        echo "Running integration tests..."
        pytest $TESTS_INTEGRATION $VERBOSE
        ;;
    all)
        echo "Running all tests..."
        pytest $TESTS_ALL $VERBOSE
        ;;
    *)
        echo "Usage: $0 [loop|database|integration|all] [verbose flags]"
        echo ""
        echo "Examples:"
        echo "  $0 all              # Run all tests"
        echo "  $0 loop             # Run only loop tests"
        echo "  $0 database         # Run only database tests"
        echo "  $0 integration      # Run only integration tests"
        echo "  $0 all -v           # Run all tests with verbose output"
        echo "  $0 all -vv          # Run all tests with very verbose output"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Test run complete!"
echo "=========================================="

