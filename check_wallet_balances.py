#!/usr/bin/env python3
"""Check wallet balances on local Bittensor network."""

import bittensor as bt
from decimal import Decimal

def format_balance(balance: int) -> str:
    """Format balance from rao to TAO."""
    tao = Decimal(balance) / Decimal(10**9)
    return f"{tao:,.2f} TAO ({balance:,} rao)"

def check_wallet_balance(wallet_name: str, hotkey_name: str = None):
    """Check balance for a specific wallet and hotkey."""
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        subtensor = bt.subtensor(network='local')
        
        # Get coldkey balance
        coldkey_ss58 = wallet.coldkeypub.ss58_address
        coldkey_balance = subtensor.get_balance(coldkey_ss58)
        
        # Get hotkey balance if specified
        hotkey_balance = None
        if hotkey_name:
            hotkey_ss58 = wallet.hotkey.ss58_address
            hotkey_balance = subtensor.get_balance(hotkey_ss58)
        
        return {
            'wallet_name': wallet_name,
            'hotkey_name': hotkey_name,
            'coldkey_address': coldkey_ss58,
            'coldkey_balance': coldkey_balance,
            'hotkey_address': wallet.hotkey.ss58_address if hotkey_name else None,
            'hotkey_balance': hotkey_balance
        }
    except Exception as e:
        return {
            'wallet_name': wallet_name,
            'hotkey_name': hotkey_name,
            'error': str(e)
        }

def main():
    """Check all wallet balances."""
    print("=" * 80)
    print("Checking Wallet Balances on Local Network")
    print("=" * 80)
    print()
    
    # Define wallets to check
    wallets_to_check = [
        ('test-miner', 'default'),
        ('test-miner', 'miner2'),
        ('test-miner', 'miner3'),
        ('test-validator', None),
        ('alice', None),
        ('sn-creator', None),
    ]
    
    results = []
    for wallet_name, hotkey_name in wallets_to_check:
        print(f"Checking {wallet_name}" + (f"/{hotkey_name}" if hotkey_name else ""))
        result = check_wallet_balance(wallet_name, hotkey_name)
        results.append(result)
    
    print()
    print("=" * 80)
    print("BALANCE SUMMARY")
    print("=" * 80)
    print()
    
    for result in results:
        if 'error' in result:
            print(f"❌ {result['wallet_name']}" + 
                  (f"/{result['hotkey_name']}" if result['hotkey_name'] else "") + 
                  f": ERROR - {result['error']}")
        else:
            print(f" wallet: {result['wallet_name']}")
            print(f"   Coldkey: {result['coldkey_address']}")
            print(f"   Balance: {format_balance(result['coldkey_balance'])}")
            
            if result['hotkey_name']:
                print(f"   Hotkey: {result['hotkey_name']} ({result['hotkey_address']})")
                print(f"   Hotkey Balance: {format_balance(result['hotkey_balance'])}")
            print()
    
    # Summary totals
    print("=" * 80)
    print("TOTAL BALANCES")
    print("=" * 80)
    total_coldkey = sum(r.get('coldkey_balance', 0) for r in results if 'error' not in r)
    total_hotkey = sum(r.get('hotkey_balance', 0) for r in results if 'error' not in r and r.get('hotkey_balance'))
    
    print(f"Total Coldkey Balance: {format_balance(total_coldkey)}")
    if total_hotkey > 0:
        print(f"Total Hotkey Balance: {format_balance(total_hotkey)}")
    print()

if __name__ == "__main__":
    main()
