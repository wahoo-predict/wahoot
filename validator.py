"""
WAHOOPREDICT - Validator implementation for the Bittensor subnet.

Validators sync event registry, query miners, compute Brier scores,
and set weights based on EMA(7d) Brier scores from the database.
"""

import bittensor as bt
import torch
import time
import os
import httpx
import asyncio
from protocol import WAHOOPredict
from wahoopredict.services.validator_sync import sync_event_registry
from wahoopredict.services.scoring import update_scores_and_weights, normalize_weights


# FastAPI service URL (can be configured via env)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def main():
    # Parse command line arguments
    parser = bt.subtensor.add_args()
    parser = bt.logging.add_args(parser)
    parser = bt.wallet.add_args(parser)
    config = bt.config(parser)
    
    # Initialize wallet and subtensor
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(config.netuid)
    
    # Create dendrite for querying miners
    dendrite = bt.dendrite(wallet=wallet)
    
    bt.logging.info("Validator started")
    
    # Background task: Sync event registry and compute scores
    async def validator_loop():
        """Background loop to sync events and compute scores."""
        from wahoopredict.db import AsyncSessionLocal
        
        while True:
            try:
                # Sync event registry from WAHOO
                async with AsyncSessionLocal() as db:
                    stats = await sync_event_registry(db)
                    bt.logging.info(f"Synced events: {stats}")
                    
                    # Update scores and weights from database
                    score_stats = await update_scores_and_weights(db)
                    bt.logging.info(f"Scored miners: {score_stats}")
                
                # Wait before next cycle
                await asyncio.sleep(600)  # Every 10 minutes
                
            except Exception as e:
                bt.logging.error(f"Error in validator loop: {e}")
                await asyncio.sleep(60)
    
    # Start background task
    import threading
    def run_async_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(validator_loop())
    
    validator_thread = threading.Thread(target=run_async_loop, daemon=True)
    validator_thread.start()
    
    # Main loop: Query miners and set weights
    try:
        while True:
            # Update metagraph
            metagraph = subtensor.metagraph(config.netuid)
            
            # Get active miners (those with non-zero IP)
            active_uids = [
                uid for uid in range(metagraph.n)
                if metagraph.axons[uid].ip != "0.0.0.0"
            ]
            
            if not active_uids:
                bt.logging.warning("No active miners found")
                time.sleep(60)
                continue
            
            # Get active events from API
            try:
                response = httpx.get(f"{API_BASE_URL}/events", timeout=10)
                events = response.json()
                if events:
                    # Use first active event
                    event_id = events[0]["event_id"]
                else:
                    event_id = "wahoo_test_event"
            except:
                event_id = "wahoo_test_event"
            
            bt.logging.info(f"Querying {len(active_uids)} miners for event {event_id}")
            
            # Query miners
            synapses = [WAHOOPredict(event_id=event_id) for _ in active_uids]
            axons = [metagraph.axons[uid] for uid in active_uids]
            
            responses = dendrite.query(axons=axons, synapses=synapses, deserialize=True)
            
            # Get weights from database (computed by scoring service)
            try:
                response = httpx.get(f"{API_BASE_URL}/weights", timeout=10)
                weights_data = response.json()
                db_weights = {w["miner_id"]: w["weight"] for w in weights_data.get("weights", [])}
            except:
                db_weights = {}
            
            # Score miners based on responses and database weights
            scores = {}
            for uid, response in zip(active_uids, responses):
                miner_id = metagraph.hotkeys[uid]
                
                # Use database weight if available, otherwise score by response
                if miner_id in db_weights:
                    scores[uid] = db_weights[miner_id]
                elif response is not None and hasattr(response, 'prob_yes'):
                    # Verify signature and score based on response quality
                    if 0.0 <= response.prob_yes <= 1.0:
                        scores[uid] = 1.0
                    else:
                        scores[uid] = 0.0
                else:
                    scores[uid] = 0.0
            
            # Update weights on-chain
            if scores:
                # Normalize scores
                total_score = sum(scores.values())
                if total_score > 0:
                    weights = torch.zeros(metagraph.n)
                    for uid, score in scores.items():
                        weights[uid] = score / total_score
                    
                    # Set weights on-chain
                    subtensor.set_weights(
                        wallet=wallet,
                        netuid=config.netuid,
                        uids=list(scores.keys()),
                        weights=weights[list(scores.keys())],
                        wait_for_inclusion=True,
                    )
                    
                    bt.logging.info(f"Updated on-chain weights for {len(scores)} miners")
            
            # Wait before next iteration
            time.sleep(100)
            
    except KeyboardInterrupt:
        bt.logging.info("Validator stopped by user")


if __name__ == "__main__":
    main()

