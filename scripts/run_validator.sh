#!/bin/bash
# Run validator on localnet (updated for argparse)

set -e

NETUID=${NETUID:-1}
NETWORK=${NETWORK:-local}
WALLET_NAME=${WALLET_NAME:-default}
HOTKEY_NAME=${HOTKEY_NAME:-default}

echo "=========================================="
echo "Starting WaHoo Predict Validator"
echo "=========================================="
echo "Network: $NETWORK"
echo "Subnet UID: $NETUID"
echo "Wallet: $WALLET_NAME/$HOTKEY_NAME"
echo ""

# Optional: Enable ValidatorDB
export USE_VALIDATOR_DB=${USE_VALIDATOR_DB:-false}
export VALIDATOR_DB_PATH=${VALIDATOR_DB_PATH:-validator.db}

# WAHOO API configuration
export WAHOO_API_URL=${WAHOO_API_URL:-https://api.wahoopredict.com}
export WAHOO_VALIDATION_ENDPOINT=${WAHOO_VALIDATION_ENDPOINT:-https://api.wahoopredict.com/api/v2/event/bittensor/statistics}

# Loop configuration
export LOOP_INTERVAL=${LOOP_INTERVAL:-100.0}

echo "Configuration:"
echo "  ValidatorDB: $USE_VALIDATOR_DB"
echo "  Loop interval: ${LOOP_INTERVAL}s"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run validator with argparse
echo "Starting validator..."
echo "Press Ctrl+C to stop"
echo ""

python -m wahoo.validator.validator \
    --netuid "$NETUID" \
    --network "$NETWORK" \
    --wallet.name "$WALLET_NAME" \
    --wallet.hotkey "$HOTKEY_NAME" \
    --loop-interval "$LOOP_INTERVAL" \
    ${USE_VALIDATOR_DB:+--use-validator-db} \
    --validator-db-path "$VALIDATOR_DB_PATH" \
    --wahoo-api-url "$WAHOO_API_URL" \
    --wahoo-validation-endpoint "$WAHOO_VALIDATION_ENDPOINT"
