#!/bin/bash

# Quick script to run validator on local net
# Usage: ./run_local_validator.sh <netuid>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <netuid>"
    echo "Example: $0 1"
    exit 1
fi

NETUID=$1

cd ~/wahoonet
source .venv/bin/activate

echo "Starting validator on local net (netuid: $NETUID)..."
echo "Wallet: test-validator"
echo "Network: local"
echo ""

python -m wahoo.validator.validator \
  --wallet.name test-validator \
  --wallet.hotkey default \
  --netuid $NETUID \
  --chain-endpoint ws://127.0.0.1:9945 \
  --loop-interval 10 \
  --wahoo-api-url http://127.0.0.1:8000 \
  --wahoo-validation-endpoint http://127.0.0.1:8000/api/v2/event/bittensor/statistics \
  --use-validator-db

