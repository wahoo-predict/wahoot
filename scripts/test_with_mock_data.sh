#!/bin/bash
# Test validator with mock data (no real wallets or miners needed)

set -e

echo "=========================================="
echo "WaHoo Predict - Mock Data Testing"
echo "=========================================="
echo ""
echo "This script tests the validator with mock data."
echo "No real wallets or miners are needed."
echo ""

# Check prerequisites
if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: Please run from wahoonet project root"
    exit 1
fi

# Configuration
NETUID=${NETUID:-1}
NETWORK=${NETWORK:-local}
WALLET_NAME=${WALLET_NAME:-default}
HOTKEY_NAME=${HOTKEY_NAME:-default}

echo "Test Configuration:"
echo "  Network: $NETWORK"
echo "  Subnet UID: $NETUID"
echo "  Wallet: $WALLET_NAME/$HOTKEY_NAME"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

echo "Starting validator with mock data support..."
echo ""
echo "Note: For full testing, you may need to:"
echo "  1. Mock the WAHOO API responses"
echo "  2. Provide mock validation data"
echo "  3. Mock miner dendrite responses"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run validator
python -m wahoo.validator.validator \
    --netuid "$NETUID" \
    --network "$NETWORK" \
    --wallet.name "$WALLET_NAME" \
    --wallet.hotkey "$HOTKEY_NAME" \
    --loop-interval 100.0 \
    --log-level INFO

