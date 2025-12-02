#!/usr/bin/env python3
"""
Register all wallets on local subnet
- 1 validator: test-validator/default
- 3 miners: test-miner/default, test-miner/miner2, test-miner/miner3
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
    
    print("\nRegistering wallets:")
    print("  - Validator: test-validator/default")
    print("  - Miner 1: test-miner/default")
    print("  - Miner 2: test-miner/miner2")
    print("  - Miner 3: test-miner/miner3")
    print()
    
    # Register validator
    validator_uid = register_wallet("test-validator", "default", "Validator")
    
    # Register all 3 miners
    miner1_uid = register_wallet("test-miner", "default", "Miner 1")
    miner2_uid = register_wallet("test-miner", "miner2", "Miner 2")
    miner3_uid = register_wallet("test-miner", "miner3", "Miner 3")
    
    print("\n" + "="*60)
    print("Registration Summary")
    print("="*60)
    if validator_uid is not None:
        print(f"✓ Validator: UID {validator_uid}")
    else:
        print("✗ Validator: Not registered")
        
    if miner1_uid is not None:
        print(f"✓ Miner 1 (default): UID {miner1_uid}")
    else:
        print("✗ Miner 1: Not registered")
        
    if miner2_uid is not None:
        print(f"✓ Miner 2 (miner2): UID {miner2_uid}")
    else:
        print("✗ Miner 2: Not registered")
        
    if miner3_uid is not None:
        print(f"✓ Miner 3 (miner3): UID {miner3_uid}")
    else:
        print("✗ Miner 3: Not registered")
    
    print("="*60)
    
    # Check all registered
    if all([validator_uid, miner1_uid, miner2_uid, miner3_uid]):
        print("\n✓ All wallets registered successfully!")
        print("You can now start testing with multiple miners.")
    else:
        print("\n⚠ Some registrations may have failed. Check errors above.")

