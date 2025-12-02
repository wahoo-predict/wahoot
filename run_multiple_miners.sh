#!/bin/bash

# Run multiple mock miners for testing
# Usage: ./run_multiple_miners.sh <netuid> <num_miners>

set -e

NETUID=${1:-1}
NUM_MINERS=${2:-3}

cd ~/wahoonet
source .venv/bin/activate

export CHAIN_ENDPOINT=ws://127.0.0.1:9945
export NETUID=$NETUID

LOG_DIR="$HOME/wahoonet/logs"
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Starting $NUM_MINERS Mock Miners"
echo "=========================================="
echo "NetUID: $NETUID"
echo "Logs: $LOG_DIR"
echo ""

MINER_PIDS=()

# Start multiple miners with different ports
for i in $(seq 0 $((NUM_MINERS - 1))); do
    PORT=$((8091 + i))
    WALLET_NAME="test-miner-$i"
    
    echo "Starting miner $i (port $PORT, wallet: $WALLET_NAME)..."
    
    export WALLET_NAME=$WALLET_NAME
    export HOTKEY_NAME=default
    export MINER_PORT=$PORT
    
    # Note: Each miner needs to be registered separately
    # For now, we'll use test-miner for all (you'll need to register each)
    # Or modify miner.py to accept port as parameter
    
    python -m wahoo.miner.miner > "$LOG_DIR/miner_${i}.log" 2>&1 &
    MINER_PID=$!
    MINER_PIDS+=($MINER_PID)
    echo "  Started (PID: $MINER_PID)"
    sleep 2
done

echo ""
echo "=========================================="
echo "All miners started!"
echo "PIDs: ${MINER_PIDS[@]}"
echo ""
echo "To stop all miners:"
echo "  kill ${MINER_PIDS[@]}"
echo "=========================================="

# Wait for interrupt
trap "echo 'Stopping all miners...'; kill ${MINER_PIDS[@]} 2>/dev/null; exit" INT TERM

wait
