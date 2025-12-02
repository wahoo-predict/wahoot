#!/bin/bash
# Check when the next tempo window opens for weight setting

cd ~/wahoonet

python3 << 'PYTHON'
import bittensor as bt
import time
from datetime import datetime, timedelta

subtensor = bt.subtensor(network="ws://127.0.0.1:9945")
netuid = 1

try:
    tempo = subtensor.tempo(netuid=netuid)
    current_block = subtensor.get_current_block()
    
    print("=" * 70)
    print("TEMPO STATUS")
    print("=" * 70)
    print(f"Current Block: {current_block}")
    print(f"Subnet Tempo: {tempo} blocks")
    
    # Measure block time
    start_block = current_block
    start_time = time.time()
    time.sleep(5)
    end_block = subtensor.get_current_block()
    end_time = time.time()
    
    blocks_passed = end_block - start_block
    elapsed = end_time - start_time
    
    if blocks_passed > 0:
        block_time = elapsed / blocks_passed
        tempo_time = tempo * block_time
        
        print(f"Block Time: {block_time:.1f} seconds per block")
        print(f"Tempo Window: {tempo_time:.1f} seconds ({tempo_time/60:.1f} minutes)")
        print(f"\nThe validator can set weights every {tempo_time/60:.1f} minutes")
        print(f"Keep watching the logs - weights will be set when the tempo window opens!")
        
except Exception as e:
    print(f"Error: {e}")
PYTHON

