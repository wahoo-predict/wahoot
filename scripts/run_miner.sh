#!/bin/bash
# Run miner on localnet

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <miner_name>"
    echo "Example: $0 miner1"
    exit 1
fi

MINER_NAME=$1
WALLETS_DIR=".wallets"
NETUID=${NETUID:-1}
NETWORK=${NETWORK:-local}

echo "=========================================="
echo "Starting WaHoo Predict Miner: $MINER_NAME"
echo "=========================================="
echo "Network: $NETWORK"
echo "Subnet UID: $NETUID"
echo ""

# Check if miner wallet exists
if [ ! -d "$WALLETS_DIR/$MINER_NAME" ]; then
    echo "ERROR: Miner wallet '$MINER_NAME' not found."
    echo "Available miners:"
    ls -d "$WALLETS_DIR"/miner* 2>/dev/null | sed 's|.*/||' || echo "  (none found)"
    exit 1
fi

# Set environment variables
export NETUID=$NETUID
export NETWORK=$NETWORK
export WALLET_NAME=$MINER_NAME
export HOTKEY_NAME=$MINER_NAME
export WALLET_PATH=$WALLETS_DIR

echo "Configuration:"
echo "  Wallet: $WALLET_NAME/$HOTKEY_NAME"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run miner
echo "Starting miner..."
echo "Press Ctrl+C to stop"
echo ""

python -m wahoo.miner.miner

