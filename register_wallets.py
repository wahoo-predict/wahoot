#!/usr/bin/env python3
"""
Register wallets on local subnet
Usage: python register_wallets.py
"""

import bittensor as bt
import sys

NETUID = 1
NETWORK = "ws://127.0.0.1:9945"
PASSWORD = "testnet"

def register_wallet(wallet_name: str, hotkey_name: str, role: str):
    """Register a wallet on the subnet"""
    print(f"\n{'='*60}")
    print(f"Registering {role} ({wallet_name}/{hotkey_name})...")
    print(f"{'='*60}")
    
    subtensor = bt.subtensor(network=NETWORK)
    wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
    
    # Check if already registered
    uid = subtensor.get_uid_for_hotkey_on_subnet(
        wallet.hotkey.ss58_address, 
        netuid=NETUID
    )
    
    if uid is not None:
        print(f"✓ {role} already registered as UID {uid}")
        return uid
    
    print(f"Registering on subnet {NETUID}...")
    print(f"Password: {PASSWORD}")
    
    try:
        # Register (will prompt for password)
        result = subtensor.register(
            wallet=wallet,
            netuid=NETUID,
            wait_for_inclusion=True,
        )
        
        # Get UID after registration
        uid = subtensor.get_uid_for_hotkey_on_subnet(
            wallet.hotkey.ss58_address, 
            netuid=NETUID
        )
        
        if uid is not None:
            print(f"✓ {role} registered successfully as UID {uid}")
            return uid
        else:
            print(f"⚠ Registration may have succeeded but UID not found")
            return None
            
    except Exception as e:
        print(f"✗ Registration failed: {e}")
        return None

if __name__ == "__main__":
    print("="*60)
    print("WaHooNet Wallet Registration on LOCAL NET")
    print("="*60)
    print(f"⚠️  LOCAL NET ONLY - Connecting to: {NETWORK}")
    print("⚠️  This will NOT affect testnet or mainnet")
    print("="*60)
    
    # Safety confirmation
    response = input("\nContinue with LOCAL NET registration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Registration cancelled.")
        sys.exit(0)
    
    # Register miner
    miner_uid = register_wallet("test-miner", "default", "Miner")
    
    # Register validator
    validator_uid = register_wallet("test-validator", "default", "Validator")
    
    print("\n" + "="*60)
    print("Registration Summary")
    print("="*60)
    if miner_uid is not None:
        print(f"✓ Miner: UID {miner_uid}")
    else:
        print("✗ Miner: Not registered")
        
    if validator_uid is not None:
        print(f"✓ Validator: UID {validator_uid}")
    else:
        print("✗ Validator: Not registered")
    
    print("="*60)

