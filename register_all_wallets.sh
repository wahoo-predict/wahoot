#!/bin/bash

# Register all wallets on local subnet using btcli
# - 1 validator: test-validator/default
# - 3 miners: test-miner/default, test-miner/miner2, test-miner/miner3

set -e

cd ~/wahoonet
source .venv/bin/activate

NETUID=1
NETWORK="ws://127.0.0.1:9945"

echo "============================================================"
echo "WaHooNet Wallet Registration on LOCAL NET"
echo "============================================================"
echo "⚠️  LOCAL NET ONLY - Connecting to: $NETWORK"
echo "⚠️  This will NOT affect testnet or mainnet"
echo "============================================================"
echo ""
echo "Registering wallets:"
echo "  - Validator: test-validator/default"
echo "  - Miner 1: test-miner/default"
echo "  - Miner 2: test-miner/miner2"
echo "  - Miner 3: test-miner/miner3"
echo ""

read -p "Continue with LOCAL NET registration? (yes/no): " response
if [[ ! $response =~ ^[Yy][Ee][Ss]$ ]] && [[ ! $response =~ ^[Yy]$ ]]; then
    echo "Registration cancelled."
    exit 0
fi

register_wallet() {
    local wallet_name=$1
    local hotkey_name=$2
    local role=$3
    
    echo ""
    echo "============================================================"
    echo "Registering $role ($wallet_name/$hotkey_name)..."
    echo "============================================================"
    
    # Use printf to send password and 'y' for confirmation
    printf "testnet\ny\n" | btcli subnet register \
        --wallet.name $wallet_name \
        --wallet.hotkey $hotkey_name \
        --netuid $NETUID \
        --network $NETWORK
    
    if [ $? -eq 0 ]; then
        echo "✓ $role registered successfully"
    else
        echo "✗ $role registration failed"
    fi
}

register_wallet "test-validator" "default" "Validator"
register_wallet "test-miner" "default" "Miner 1"
register_wallet "test-miner" "miner2" "Miner 2"
register_wallet "test-miner" "miner3" "Miner 3"

echo ""
echo "============================================================"
echo "Registration Complete!"
echo "============================================================"
echo ""
echo "Verifying registrations..."

# Verify using Python
python3 << EOF
import bittensor as bt

subtensor = bt.subtensor(network="$NETWORK")
netuid = $NETUID

wallets = [
    ("test-validator", "default", "Validator"),
    ("test-miner", "default", "Miner 1"),
    ("test-miner", "miner2", "Miner 2"),
    ("test-miner", "miner3", "Miner 3"),
]

print()
for wallet_name, hotkey_name, role in wallets:
    wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
    uid = subtensor.get_uid_for_hotkey_on_subnet(
        wallet.hotkey.ss58_address,
        netuid=netuid
    )
    if uid is not None:
        print(f"✓ {role} ({wallet_name}/{hotkey_name}): UID {uid}")
    else:
        print(f"✗ {role} ({wallet_name}/{hotkey_name}): NOT registered")

print()
EOF

echo "============================================================"

