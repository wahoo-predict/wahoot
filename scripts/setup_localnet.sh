#!/bin/bash
# Setup script for Bittensor localnet testing
# This script initializes a local Bittensor network for testing

set -e

echo "=========================================="
echo "WaHoo Predict - Localnet Setup"
echo "=========================================="

# Check if btcli is available
if ! command -v btcli &> /dev/null; then
    echo "ERROR: btcli not found. Please install bittensor CLI."
    echo "Run: pip install bittensor"
    exit 1
fi

# Check if we're in the project directory
if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: Please run this script from the wahoonet project root"
    exit 1
fi

echo ""
echo "This script will:"
echo "  1. Check/create localnet configuration"
echo "  2. Initialize local Bittensor network (if needed)"
echo "  3. Create wallet directory structure"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Create wallets directory if it doesn't exist
WALLETS_DIR=".wallets"
mkdir -p "$WALLETS_DIR"

echo ""
echo "✓ Localnet setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/create_wallets.sh"
echo "  2. Run: ./scripts/register_localnet.sh"
echo "  3. Start validator: ./scripts/run_validator.sh"
echo "  4. Start miners: ./scripts/run_miner.sh <miner_name>"
echo ""

