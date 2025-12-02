#!/bin/bash

# Script to register wallets on local subnet
# Usage: ./register_wallets.sh

set -e

cd ~/wahoonet
source .venv/bin/activate

echo "=========================================="
echo "Registering Wallets on Local Subnet"
echo "=========================================="
echo ""
echo "Wallet password: testnet"
echo ""

NETUID=1
NETWORK="ws://127.0.0.1:9945"

# Register miner
echo "Registering miner (test-miner)..."
echo "testnet" | python -c "
import sys
import bittensor as bt

subtensor = bt.subtensor(network='$NETWORK')
wallet = bt.wallet(name='test-miner', hotkey='default')
netuid = $NETUID

# Check if already registered
uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid=netuid)
if uid is not None:
    print(f'✓ Miner already registered as UID {uid}')
else:
    print('Registering miner...')
    try:
        result = subtensor.register(wallet=wallet, netuid=netuid, wait_for_inclusion=True)
        uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid=netuid)
        print(f'✓ Miner registered as UID {uid}')
    except Exception as e:
        print(f'✗ Error: {e}')
        sys.exit(1)
"

echo ""

# Register validator
echo "Registering validator (test-validator)..."
echo "testnet" | python -c "
import sys
import bittensor as bt

subtensor = bt.subtensor(network='$NETWORK')
wallet = bt.wallet(name='test-validator', hotkey='default')
netuid = $NETUID

# Check if already registered
uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid=netuid)
if uid is not None:
    print(f'✓ Validator already registered as UID {uid}')
else:
    print('Registering validator...')
    try:
        result = subtensor.register(wallet=wallet, netuid=netuid, wait_for_inclusion=True)
        uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid=netuid)
        print(f'✓ Validator registered as UID {uid}')
    except Exception as e:
        print(f'✗ Error: {e}')
        sys.exit(1)
"

echo ""
echo "=========================================="
echo "Registration complete!"
echo "=========================================="

