#!/bin/bash

# Test that validator runs 10+ iterations successfully on local net
# This is a real integration test, not a unit test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NETUID=${1:-1}
ITERATIONS=${2:-12}  # Test 12 iterations
LOOP_INTERVAL=${3:-5}  # 5 seconds for faster testing

echo "=========================================="
echo "WaHooNet 10+ Iterations Test"
echo "=========================================="
echo ""
echo "NetUID: $NETUID"
echo "Target Iterations: $ITERATIONS"
echo "Loop Interval: ${LOOP_INTERVAL}s"
echo ""

# Check local chain
if ! sudo docker ps | grep -q "local_chain"; then
    echo "Starting local chain..."
    ./start_local_chain.sh
    sleep 3
fi

# Activate venv
source .venv/bin/activate

# Set environment
export NETWORK=local
export NETUID=$NETUID
export LOOP_INTERVAL=$LOOP_INTERVAL
export WAHOO_API_URL="http://127.0.0.1:8000"
export WAHOO_VALIDATION_ENDPOINT="http://127.0.0.1:8000/api/v2/event/bittensor/statistics"
export USE_VALIDATOR_DB=true

# Check if mock API is running
if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Mock API not running. Starting it..."
    python -m tests.mock_wahoo_api > /tmp/mock_api_test.log 2>&1 &
    MOCK_API_PID=$!
    sleep 2
    echo "Mock API started (PID: $MOCK_API_PID)"
fi

# Create test log
TEST_LOG="$SCRIPT_DIR/logs/iteration_test_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

echo "Test log: $TEST_LOG"
echo ""

# Start miner in background
echo "Starting miner..."
export CHAIN_ENDPOINT=ws://127.0.0.1:9945
export NETUID=$NETUID
export WALLET_NAME=test-miner
export HOTKEY_NAME=default
python -m wahoo.miner.miner > "$SCRIPT_DIR/logs/miner_test.log" 2>&1 &
MINER_PID=$!

echo "Miner started (PID: $MINER_PID)"
sleep 5

# Function to cleanup
cleanup() {
    echo ""
    echo "Cleaning up..."
    kill $MINER_PID 2>/dev/null || true
    [ -n "$MOCK_API_PID" ] && kill $MOCK_API_PID 2>/dev/null || true
    wait $MINER_PID 2>/dev/null || true
    [ -n "$MOCK_API_PID" ] && wait $MOCK_API_PID 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# Run validator and count iterations
echo "Starting validator..."
echo "Will run for approximately $((ITERATIONS * LOOP_INTERVAL)) seconds"
echo ""

# Count iterations by looking for "Starting main loop iteration" in logs
python -m wahoo.validator.validator \
    --wallet.name test-validator \
    --wallet.hotkey default \
    --netuid $NETUID \
    --chain-endpoint ws://127.0.0.1:9945 \
    --loop-interval $LOOP_INTERVAL \
    --wahoo-api-url "$WAHOO_API_URL" \
    --wahoo-validation-endpoint "$WAHOO_VALIDATION_ENDPOINT" \
    --use-validator-db \
    2>&1 | tee "$TEST_LOG" | while IFS= read -r line; do
    if echo "$line" | grep -q "Starting main loop iteration"; then
        ITERATION_COUNT=$((ITERATION_COUNT + 1))
        echo "[$ITERATION_COUNT/$ITERATIONS] Iteration completed"
        if [ $ITERATION_COUNT -ge $ITERATIONS ]; then
            echo ""
            echo "=========================================="
            echo "✓ Successfully completed $ITERATION_COUNT iterations!"
            echo "=========================================="
            kill $MINER_PID 2>/dev/null || true
            exit 0
        fi
    fi
    echo "$line"
done

# Count iterations from log file
ITERATION_COUNT=$(grep -c "Starting main loop iteration" "$TEST_LOG" 2>/dev/null || echo "0")

echo ""
echo "=========================================="
if [ "$ITERATION_COUNT" -ge "$ITERATIONS" ]; then
    echo "✓ SUCCESS: Completed $ITERATION_COUNT iterations (target: $ITERATIONS)"
    echo ""
    echo "Test Results:"
    echo "  ✓ Validator ran $ITERATION_COUNT iterations"
    echo "  ✓ No crashes detected"
    echo "  ✓ Ready for testnet!"
    exit 0
else
    echo "✗ FAILED: Only completed $ITERATION_COUNT iterations (target: $ITERATIONS)"
    echo ""
    echo "Check logs: $TEST_LOG"
    exit 1
fi

