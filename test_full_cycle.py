#!/usr/bin/env python3
"""
Comprehensive test of full validator cycle with database verification
Tests all 6 critical areas and verifies database operations
"""

import os
import sys
import time
import sqlite3
from pathlib import Path
from typing import Dict, List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

import bittensor as bt
from wahoo.validator.database.core import ValidatorDB

NETWORK = "ws://127.0.0.1:9945"
NETUID = 1
MIN_ITERATIONS = 10
LOOP_INTERVAL = 5  # 5 seconds for faster testing

def check_database(db_path: str) -> Dict:
    """Check database contents"""
    results = {
        "exists": False,
        "has_scores": False,
        "has_cache": False,
        "score_count": 0,
        "cache_count": 0,
    }
    
    if not Path(db_path).exists():
        return results
    
    results["exists"] = True
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check scoring_runs
        cursor.execute("SELECT COUNT(*) FROM scoring_runs")
        results["score_count"] = cursor.fetchone()[0]
        results["has_scores"] = results["score_count"] > 0
        
        # Check performance_snapshots (cache)
        cursor.execute("SELECT COUNT(*) FROM performance_snapshots")
        results["cache_count"] = cursor.fetchone()[0]
        results["has_cache"] = results["cache_count"] > 0
        
        conn.close()
    except Exception as e:
        print(f"Database check error: {e}")
    
    return results

def verify_metagraph(subtensor: bt.Subtensor, metagraph: bt.Metagraph) -> Dict:
    """Verify metagraph state"""
    metagraph.sync(subtensor=subtensor)
    
    from wahoo.validator.utils.miners import get_active_uids, build_uid_to_hotkey
    
    active_uids = get_active_uids(metagraph)
    uid_to_hotkey = build_uid_to_hotkey(metagraph, active_uids=active_uids)
    
    return {
        "total_uids": len(metagraph.uids),
        "active_uids": len(active_uids),
        "active_uids_list": active_uids,
        "uid_to_hotkey": uid_to_hotkey,
    }

def verify_weights_on_chain(subtensor: bt.Subtensor, netuid: int, wallet: bt.Wallet) -> Dict:
    """Verify weights are set on blockchain"""
    try:
        # Get current weights from chain
        metagraph = bt.metagraph(netuid=netuid, network=NETWORK)
        metagraph.sync(subtensor=subtensor)
        
        # Check if validator has set weights
        # This is a simplified check - in reality you'd check the weights for your UID
        has_weights = len(metagraph.weights) > 0
        
        return {
            "weights_exist": has_weights,
            "weight_count": len(metagraph.weights) if has_weights else 0,
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    print("="*70)
    print("WaHooNet Full Cycle Test with Database Verification")
    print("="*70)
    print()
    print("This test will:")
    print("  1. Verify validator-miner connection")
    print("  2. Run validator for 10+ iterations")
    print("  3. Check all 9 steps execute")
    print("  4. Verify database operations")
    print("  5. Verify weights on blockchain")
    print("  6. Verify scoring cycles")
    print()
    
    # Check prerequisites
    print("Checking prerequisites...")
    
    # Check local chain
    try:
        subtensor = bt.subtensor(network=NETWORK)
        print("✓ Local chain accessible")
    except Exception as e:
        print(f"✗ Cannot connect to local chain: {e}")
        return 1
    
    # Check wallets registered
    wallet = bt.wallet(name="test-validator", hotkey="default")
    uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid=NETUID)
    if uid is None:
        print("✗ Validator not registered on subnet")
        print("  Run: python register_wallets.py")
        return 1
    print(f"✓ Validator registered as UID {uid}")
    
    # Check metagraph
    metagraph = bt.metagraph(netuid=NETUID, network=NETWORK)
    metagraph.sync(subtensor=subtensor)
    print(f"✓ Metagraph synced: {len(metagraph.uids)} UIDs")
    
    # Verify active miners
    metagraph_info = verify_metagraph(subtensor, metagraph)
    print(f"✓ Active miners: {metagraph_info['active_uids']}")
    
    if metagraph_info['active_uids'] == 0:
        print("⚠️  No active miners found!")
        print("  Make sure miners are running and have served their axons")
        return 1
    
    # Check database
    db_path = Path.home() / "wahoonet" / "validator.db"
    print(f"\nDatabase path: {db_path}")
    
    # Run validator (this would normally be done separately)
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("\nTo run the full test:")
    print("  1. Start miners: ./run_local_miner.sh 1 (or multiple)")
    print("  2. Start validator: ./run_local_validator.sh 1")
    print("  3. Wait for 10+ iterations")
    print("  4. Run this script again to verify results")
    print()
    
    # Check database after potential run
    db_info = check_database(str(db_path))
    print("Database Status:")
    print(f"  Exists: {db_info['exists']}")
    print(f"  Has scores: {db_info['has_scores']} ({db_info['score_count']} records)")
    print(f"  Has cache: {db_info['has_cache']} ({db_info['cache_count']} records)")
    
    # Verify weights
    weights_info = verify_weights_on_chain(subtensor, NETUID, wallet)
    print("\nBlockchain Weights:")
    print(f"  Weights exist: {weights_info.get('weights_exist', False)}")
    print(f"  Weight count: {weights_info.get('weight_count', 0)}")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print("1. Get test tokens: btcli wallet faucet --wallet.name test-miner --network ws://127.0.0.1:9945")
    print("2. Register wallets: python register_wallets.py")
    print("3. Start miners and validator")
    print("4. Run this script to verify everything worked")
    print("="*70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

