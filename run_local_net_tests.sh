#!/bin/bash

# Comprehensive Local Net Test Runner for WaHooNet
# Tests all critical paths for release readiness

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "WaHooNet Local Net Integration Tests"
echo "=========================================="
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    exit 1
fi

# Check if local chain is running
if ! docker ps | grep -q "local_chain"; then
    echo -e "${YELLOW}⚠ Local chain not running${NC}"
    echo "Starting local chain..."
    ./start_local_chain.sh
    sleep 3
fi

# Check Python environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing test dependencies..."
    pip install -e ".[dev]" > /dev/null 2>&1
fi

# Start mock API server in background
echo -e "${BLUE}Starting mock Wahoo API server...${NC}"
MOCK_API_PID=""
MOCK_API_PORT=8000

# Check if port is already in use
if lsof -Pi :$MOCK_API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Port $MOCK_API_PORT already in use, assuming mock server is running${NC}"
else
    python -m tests.mock_wahoo_api $MOCK_API_PORT > /tmp/mock_api.log 2>&1 &
    MOCK_API_PID=$!
    echo -e "${GREEN}✓ Mock API server started (PID: $MOCK_API_PID)${NC}"
    sleep 2
fi

# Cleanup function
cleanup() {
    if [ ! -z "$MOCK_API_PID" ]; then
        echo -e "${BLUE}Stopping mock API server...${NC}"
        kill $MOCK_API_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Run tests
echo ""
echo -e "${BLUE}Running integration tests...${NC}"
echo ""

# Set environment variables for tests
export WAHOO_API_URL="http://127.0.0.1:$MOCK_API_PORT"
export WAHOO_VALIDATION_ENDPOINT="http://127.0.0.1:$MOCK_API_PORT/api/v2/event/bittensor/statistics"
export NETWORK="local"
export NETUID="1"

# Run pytest with verbose output
pytest tests/test_local_net_integration.py -v --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Release readiness checklist:"
    echo "  ✓ Validator-Miner connection"
    echo "  ✓ Main loop (9 steps)"
    echo "  ✓ Database operations"
    echo "  ✓ Scoring & weights"
    echo "  ✓ Error handling"
    echo "  ✓ End-to-end"
    echo ""
    echo -e "${GREEN}Ready for testnet!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Review the test output above for details"
fi
echo "=========================================="

exit $TEST_EXIT_CODE

