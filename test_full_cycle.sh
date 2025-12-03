#!/bin/bash

# Comprehensive test of full validator-miner cycle
# Tests all 6 critical areas with multiple miners

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NETUID=${1:-1}
ITERATIONS=${2:-15}
LOOP_INTERVAL=${3:-5}
NUM_MINERS=${4:-3}

echo "=========================================="
echo "WaHooNet Full Cycle Test"
echo "=========================================="
echo "NetUID: $NETUID"
echo "Iterations: $ITERATIONS"
echo "Loop Interval: ${LOOP_INTERVAL}s"
echo "Miners: $NUM_MINERS"
echo ""

# Check prerequisites
if ! sudo docker ps | grep -q "local_chain"; then
    echo "❌ Local chain not running. Start with: ./start_local_chain.sh"
    exit 1
fi

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
    echo "Starting mock API server..."
    python -m tests.mock_wahoo_api > /tmp/mock_api_test.log 2>&1 &
    MOCK_API_PID=$!
    sleep 2
    echo "✓ Mock API started (PID: $MOCK_API_PID)"
else
    MOCK_API_PID=""
    echo "✓ Mock API already running"
fi

# Create log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
TEST_LOG="$LOG_DIR/full_cycle_test_$(date +%Y%m%d_%H%M%S).log"

echo "Test log: $TEST_LOG"
echo ""

# Start miners (using different hotkeys: default, miner2, miner3)
echo "Starting $NUM_MINERS miners..."
MINER_PIDS=()
MINER_HOTKEYS=("default" "miner2" "miner3")

for i in $(seq 0 $((NUM_MINERS - 1))); do
    HOTKEY=${MINER_HOTKEYS[$i]}
    export CHAIN_ENDPOINT=ws://127.0.0.1:9945
    export NETUID=$NETUID
    export WALLET_NAME=test-miner
    export HOTKEY_NAME=$HOTKEY
    
    python -m wahoo.miner.miner > "$LOG_DIR/miner_${HOTKEY}.log" 2>&1 &
    MINER_PID=$!
    MINER_PIDS+=($MINER_PID)
    echo "  Miner $((i+1)) started (PID: $MINER_PID, hotkey: $HOTKEY)"
    sleep 3
done

echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    for pid in "${MINER_PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
    [ -n "$MOCK_API_PID" ] && kill $MOCK_API_PID 2>/dev/null || true
    wait ${MINER_PIDS[@]} 2>/dev/null || true
    [ -n "$MOCK_API_PID" ] && wait $MOCK_API_PID 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# Wait for miners to start
echo "Waiting for miners to initialize..."
sleep 5

# Run validator and count iterations
echo "Starting validator..."
echo "Will run for approximately $((ITERATIONS * LOOP_INTERVAL)) seconds"
echo ""

ITERATION_COUNT=0
WEIGHT_SET_COUNT=0
MINER_QUERY_COUNT=0

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
    # Count iterations
    if echo "$line" | grep -q "Starting main loop iteration"; then
        ITERATION_COUNT=$((ITERATION_COUNT + 1))
        echo "[$ITERATION_COUNT/$ITERATIONS] Iteration completed"
    fi
    
    # Count weight sets
    if echo "$line" | grep -q "Setting weights\|Weights set"; then
        WEIGHT_SET_COUNT=$((WEIGHT_SET_COUNT + 1))
    fi
    
    # Count miner queries
    if echo "$line" | grep -q "Querying.*miners\|Queried.*miners"; then
        MINER_QUERY_COUNT=$((MINER_QUERY_COUNT + 1))
    fi
    
    # Show progress
    echo "$line"
    
    # Stop after target iterations
    if [ "$ITERATION_COUNT" -ge "$ITERATIONS" ]; then
        echo ""
        echo "=========================================="
        echo "✓ Completed $ITERATION_COUNT iterations!"
        echo "=========================================="
        cleanup
        exit 0
    fi
done

# Count from log file
ITERATION_COUNT=$(grep -c "Starting main loop iteration" "$TEST_LOG" 2>/dev/null || echo "0")
WEIGHT_SET_COUNT=$(grep -c "Setting weights\|Weights set" "$TEST_LOG" 2>/dev/null || echo "0")
ACTIVE_UID_COUNT=$(grep -c "Found.*active UIDs" "$TEST_LOG" 2>/dev/null || echo "0")

echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo "Iterations completed: $ITERATION_COUNT / $ITERATIONS"
echo "Weight sets: $WEIGHT_SET_COUNT"
echo "Active UID detections: $ACTIVE_UID_COUNT"
echo ""

# Verify database
echo "Verifying database..."
python verify_database.py

echo ""
echo "=========================================="
if [ "$ITERATION_COUNT" -ge "$ITERATIONS" ] && [ "$WEIGHT_SET_COUNT" -gt 0 ]; then
    echo "✓ SUCCESS: Full cycle test passed!"
    echo ""
    echo "✓ $ITERATION_COUNT iterations completed"
    echo "✓ $WEIGHT_SET_COUNT weight cycles"
    echo "✓ Database verified"
    echo "✓ Ready for testnet!"
    exit 0
else
    echo "✗ FAILED: Some checks did not pass"
    echo ""
    echo "Check logs: $TEST_LOG"
    exit 1
fi

