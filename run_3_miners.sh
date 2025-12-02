#!/bin/bash

# Run 3 miners with different hotkeys
# Usage: ./run_3_miners.sh <netuid>

set -e

NETUID=${1:-1}

cd ~/wahoonet
source .venv/bin/activate

export CHAIN_ENDPOINT=ws://127.0.0.1:9945
export NETUID=$NETUID

LOG_DIR="$HOME/wahoonet/logs"
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Starting 3 Miners"
echo "=========================================="
echo "NetUID: $NETUID"
echo "Logs: $LOG_DIR"
echo ""

MINER_PIDS=()
MINER_HOTKEYS=("default" "miner2" "miner3")

# Start 3 miners with different hotkeys
for i in {0..2}; do
    HOTKEY=${MINER_HOTKEYS[$i]}
    PORT=$((8091 + i))
    
    echo "Starting miner $((i+1)) (hotkey: $HOTKEY, port: $PORT)..."
    
    export WALLET_NAME=test-miner
    export HOTKEY_NAME=$HOTKEY
    export MINER_PORT=$PORT
    
    python -m wahoo.miner.miner > "$LOG_DIR/miner_${HOTKEY}.log" 2>&1 &
    MINER_PID=$!
    MINER_PIDS+=($MINER_PID)
    echo "  Started (PID: $MINER_PID, hotkey: $HOTKEY)"
    sleep 3
done

echo ""
echo "=========================================="
echo "All 3 miners started!"
echo "PIDs: ${MINER_PIDS[@]}"
echo ""
echo "Hotkeys:"
echo "  - Miner 1: default (PID: ${MINER_PIDS[0]})"
echo "  - Miner 2: miner2 (PID: ${MINER_PIDS[1]})"
echo "  - Miner 3: miner3 (PID: ${MINER_PIDS[2]})"
echo ""
echo "To stop all miners:"
echo "  kill ${MINER_PIDS[@]}"
echo "=========================================="

# Wait for interrupt
cleanup() {
    echo ""
    echo "Stopping all miners..."
    for pid in "${MINER_PIDS[@]}"; do
        kill $pid 2>/dev/null || true
    done
    for pid in "${MINER_PIDS[@]}"; do
        wait $pid 2>/dev/null || true
    done
    echo "Done"
    exit
}

trap cleanup INT TERM

# Keep script running
echo "All miners running. Press Ctrl+C to stop."
echo ""
wait

