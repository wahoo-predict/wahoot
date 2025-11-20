#!/bin/bash
# Register wallets on localnet subnet
# Registers: owner (as owner), validator, and miners

set -e

WALLETS_DIR=".wallets"
NETUID=${NETUID:-1}  # Default subnet UID, can be overridden

echo "=========================================="
echo "Registering Wallets on Localnet"
echo "=========================================="
echo "Subnet UID: $NETUID"
echo ""

# Check if wallets exist
if [ ! -d "$WALLETS_DIR/owner" ]; then
    echo "ERROR: Wallets not found. Run ./scripts/create_wallets.sh first"
    exit 1
fi

# Function to register wallet
register_wallet() {
    local wallet_name=$1
    local wallet_type=$2  # "owner", "validator", or "miner"
    
    echo "[Registering $wallet_type: $wallet_name]"
    
    if [ "$wallet_type" == "owner" ]; then
        # Register as owner (requires --wallet.name and --wallet.hotkey)
        btcli wallet register \
            --netuid "$NETUID" \
            --wallet.name "$wallet_name" \
            --wallet.path "$WALLETS_DIR" \
            --wallet.hotkey "$wallet_name" \
            --network local || {
            echo "⚠ Failed to register $wallet_name as owner (may already be registered)"
        }
    else
        # Register as validator or miner
        btcli wallet register \
            --netuid "$NETUID" \
            --wallet.name "$wallet_name" \
            --wallet.path "$WALLETS_DIR" \
            --wallet.hotkey "$wallet_name" \
            --network local || {
            echo "⚠ Failed to register $wallet_name (may already be registered)"
        }
    fi
    
    echo "✓ Registered: $wallet_name"
    echo ""
}

# Register owner
echo "[1/5] Registering owner..."
register_wallet "owner" "owner"

# Register validator
echo "[2/5] Registering validator..."
register_wallet "validator" "validator"

# Register miners
echo "[3/5] Registering miner1..."
register_wallet "miner1" "miner"

echo "[4/5] Registering miner2..."
register_wallet "miner2" "miner"

echo "[5/5] Registering miner3..."
register_wallet "miner3" "miner"

echo "=========================================="
echo "✓ Registration complete!"
echo "=========================================="
echo ""
echo "All wallets registered on subnet $NETUID"
echo ""
echo "Next steps:"
echo "  1. Start validator: ./scripts/run_validator.sh"
echo "  2. Start miners: ./scripts/run_miner.sh <miner_name>"
echo ""

