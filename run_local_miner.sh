#!/bin/bash

# Quick script to run miner on local net
# Usage: ./run_local_miner.sh <netuid>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <netuid>"
    echo "Example: $0 1"
    exit 1
fi

NETUID=$1

cd ~/wahoonet
source .venv/bin/activate

echo "Starting miner on local net (netuid: $NETUID)..."
echo "Wallet: test-miner"
echo "Network: local"
echo ""

# Miner uses environment variables - use chain_endpoint for local
export CHAIN_ENDPOINT=ws://127.0.0.1:9945
export NETUID=$NETUID
python -m wahoo.miner.miner

