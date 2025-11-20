#!/bin/bash
# Complete simulation: Mock API + Validator

set -e

echo "=========================================="
echo "WaHoo Predict - Full Flow Simulation"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Start mock API server (background)"
echo "  2. Wait a moment for API to start"
echo "  3. Start validator (foreground)"
echo "  4. Validator will fetch from mock API"
echo "  5. Process data, store in database"
echo "  6. Compute weights"
echo ""
echo "Press Ctrl+C to stop both"
echo ""

# Configuration
MOCK_API_PORT=${MOCK_API_PORT:-8000}
NETUID=${NETUID:-1}
NETWORK=${NETWORK:-local}

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Step 1: Start mock API in background
echo "[1/2] Starting mock API server..."
./scripts/start_mock_api.sh > /tmp/mock_api.log 2>&1 &
API_PID=$!

# Wait for API to start
echo "Waiting for API to start..."
sleep 3

# Check if API is running
if ! curl -s "http://localhost:$MOCK_API_PORT/events" > /dev/null 2>&1; then
    echo "ERROR: Mock API failed to start"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Mock API running (PID: $API_PID)"
echo ""

# Step 2: Start validator
echo "[2/2] Starting validator..."
echo ""

# Set environment for validator
export WAHOO_API_URL="http://localhost:$MOCK_API_PORT"
export WAHOO_VALIDATION_ENDPOINT="http://localhost:$MOCK_API_PORT/api/v2/event/bittensor/statistics"
export NETUID=$NETUID
export NETWORK=$NETWORK
export USE_VALIDATOR_DB=true
export VALIDATOR_DB_PATH=validator.db

# Trap to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $API_PID 2>/dev/null || true
    ./scripts/stop_mock_api.sh 2>/dev/null || true
    echo "✅ Cleanup complete"
}
trap cleanup EXIT INT TERM

# Run validator in mock mode
python -m wahoo.validator.validator \
    --netuid "$NETUID" \
    --network "$NETWORK" \
    --wahoo-api-url "$WAHOO_API_URL" \
    --wahoo-validation-endpoint "$WAHOO_VALIDATION_ENDPOINT" \
    --use-validator-db \
    --loop-interval 30.0 \
    --log-level INFO \
    --mock

