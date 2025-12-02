#!/bin/bash

# Run validator and miner together on local net with logging
# This verifies real communication and 10+ iterations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NETUID=${1:-1}
LOOP_INTERVAL=${2:-10}  # 10 seconds for faster testing

echo "=========================================="
echo "WaHooNet Local Net - Validator + Miner"
echo "=========================================="
echo ""
echo "NetUID: $NETUID"
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
    echo "⚠️  Mock API not running on port 8000"
    echo "Start it in another terminal: python -m tests.mock_wahoo_api"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
VALIDATOR_LOG="$LOG_DIR/validator_$(date +%Y%m%d_%H%M%S).log"
MINER_LOG="$LOG_DIR/miner_$(date +%Y%m%d_%H%M%S).log"

echo "Logs will be written to:"
echo "  Validator: $VALIDATOR_LOG"
echo "  Miner: $MINER_LOG"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $MINER_PID 2>/dev/null || true
    kill $VALIDATOR_PID 2>/dev/null || true
    wait $MINER_PID 2>/dev/null || true
    wait $VALIDATOR_PID 2>/dev/null || true
    echo "Done"
}

trap cleanup EXIT INT TERM

# Start miner in background
echo "Starting miner..."
export CHAIN_ENDPOINT=ws://127.0.0.1:9945
export NETUID=$NETUID
export WALLET_NAME=test-miner
export HOTKEY_NAME=default
python -m wahoo.miner.miner > "$MINER_LOG" 2>&1 &
MINER_PID=$!

echo "Miner started (PID: $MINER_PID)"
sleep 3

# Start validator in foreground (so we can see output)
echo "Starting validator..."
echo "Press Ctrl+C to stop"
echo ""
echo "=========================================="
echo ""

python -m wahoo.validator.validator \
    --wallet.name test-validator \
    --wallet.hotkey default \
    --netuid $NETUID \
    --chain-endpoint ws://127.0.0.1:9945 \
    --loop-interval $LOOP_INTERVAL \
    --wahoo-api-url "$WAHOO_API_URL" \
    --wahoo-validation-endpoint "$WAHOO_VALIDATION_ENDPOINT" \
    --use-validator-db \
    2>&1 | tee "$VALIDATOR_LOG"

