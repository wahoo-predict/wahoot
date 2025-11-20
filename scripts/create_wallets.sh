#!/bin/bash
# Create wallets for localnet testing
# Creates: owner, validator, and 1-3 miners

set -e

WALLETS_DIR=".wallets"
mkdir -p "$WALLETS_DIR"

echo "=========================================="
echo "Creating Wallets for Localnet Testing"
echo "=========================================="

# Function to create wallet
create_wallet() {
    local wallet_name=$1
    local wallet_path="$WALLETS_DIR/$wallet_name"
    
    if [ -d "$wallet_path" ]; then
        echo "⚠ Wallet '$wallet_name' already exists, skipping..."
        return
    fi
    
    echo "Creating wallet: $wallet_name"
    btcli wallet new_coldkey --wallet.name "$wallet_name" --wallet.path "$WALLETS_DIR" || {
        echo "ERROR: Failed to create coldkey for $wallet_name"
        exit 1
    }
    
    btcli wallet new_hotkey --wallet.name "$wallet_name" --wallet.path "$WALLETS_DIR" || {
        echo "ERROR: Failed to create hotkey for $wallet_name"
        exit 1
    }
    
    echo "✓ Created wallet: $wallet_name"
}

# Create owner wallet
echo ""
echo "[1/5] Creating owner wallet..."
create_wallet "owner"

# Create validator wallet
echo ""
echo "[2/5] Creating validator wallet..."
create_wallet "validator"

# Create miner wallets (1-3)
echo ""
echo "[3/5] Creating miner wallets..."
create_wallet "miner1"
create_wallet "miner2"
create_wallet "miner3"

echo ""
echo "=========================================="
echo "✓ All wallets created successfully!"
echo "=========================================="
echo ""
echo "Wallets created in: $WALLETS_DIR/"
echo ""
echo "Wallet structure:"
echo "  owner/     - Owner wallet (for subnet management)"
echo "  validator/ - Validator wallet"
echo "  miner1/    - Miner 1"
echo "  miner2/    - Miner 2"
echo "  miner3/    - Miner 3"
echo ""
echo "Next step: Run ./scripts/register_localnet.sh"
echo ""

