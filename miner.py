"""
WAHOOPREDICT - Miner implementation for the Bittensor subnet.

Miners pull live markets from WAHOO's API, produce prob_yes predictions,
and submit them via both Bittensor synapse and FastAPI service.
"""

import bittensor as bt
import time
import hashlib
import hmac
import os
import httpx
import asyncio
from protocol import WAHOOPredict
from wahoopredict.services.wahoo_api import fetch_wahoo_events, fetch_wahoo_event_details


# FastAPI service URL (can be configured via env)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MINER_ID = os.getenv("MINER_ID", "")  # Set from wallet hotkey or config


def main():
    # Parse command line arguments
    parser = bt.subtensor.add_args()
    parser = bt.logging.add_args(parser)
    parser = bt.wallet.add_args(parser)
    parser = bt.axon.add_args(parser)
    config = bt.config(parser)
    
    # Initialize wallet and subtensor
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    metagraph = subtensor.metagraph(config.netuid)
    
    # Set miner ID from wallet hotkey
    miner_id = MINER_ID or wallet.hotkey.ss58_address
    
    # Create axon server
    axon = bt.axon(wallet=wallet, port=config.axon.port)
    
    def forward(synapse: WAHOOPredict) -> WAHOOPredict:
        """
        Forward function called when miner receives a query from a validator.
        Miner provides probability prediction for the event.
        """
        # Generate prediction using WAHOO API and miner's model
        # Miners should implement their own prediction logic here
        # This is a placeholder - replace with your own model/strategy
        try:
            # Fetch event details from WAHOO
            wahoo_market_id = synapse.event_id.replace("wahoo_", "")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            event_details = loop.run_until_complete(fetch_wahoo_event_details(wahoo_market_id))
            loop.close()
            
            # Simple prediction logic (miners should customize this)
            if event_details and "current_odds" in event_details:
                prob_yes = float(event_details["current_odds"])
            else:
                prob_yes = 0.5  # Default neutral prediction
        except:
            # Fallback to default if prediction fails
            prob_yes = 0.5
        
        synapse.prob_yes = prob_yes
        
        # Generate manifest hash
        manifest_data = f"{synapse.event_id}:{synapse.prob_yes}"
        synapse.manifest_hash = hashlib.sha256(manifest_data.encode()).hexdigest()
        
        # Sign with HMAC (using API_SECRET from config)
        api_secret = os.getenv("API_SECRET", "dev-secret")
        synapse.sig = hmac.new(
            api_secret.encode(),
            synapse.manifest_hash.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Also submit to FastAPI service for database storage
        try:
            submit_to_api(synapse.event_id, miner_id, prob_yes, synapse.manifest_hash, synapse.sig)
        except Exception as e:
            bt.logging.warning(f"Failed to submit to API: {e}")
        
        return synapse
    
    def blacklist(synapse: WAHOOPredict) -> tuple[bool, str]:
        """
        Determine if a synapse should be blacklisted.
        """
        # Check if hotkey is in metagraph
        if synapse.dendrite.hotkey not in metagraph.hotkeys:
            return True, "Hotkey not in metagraph"
        return False, ""
    
    def priority(synapse: WAHOOPredict) -> float:
        """
        Determine the priority of a synapse.
        Higher priority = processed first.
        """
        # Prioritize based on stake
        uid = metagraph.hotkeys.index(synapse.dendrite.hotkey)
        return float(metagraph.S[uid])
    
    # Attach functions to axon
    axon.attach(
        forward_fn=forward,
        blacklist_fn=blacklist,
        priority_fn=priority,
    )
    
    # Serve axon
    axon.serve(netuid=config.netuid, subtensor=subtensor)
    
    # Subscribe to metagraph updates
    subtensor.serve_axon(netuid=config.netuid, axon=axon)
    
    bt.logging.info(f"Miner started on {config.axon.port}")
    
    # Background task: Pull events from WAHOO and submit predictions
    async def miner_loop():
        """Background loop to pull events and submit predictions."""
        while True:
            try:
                # Get active events from WAHOO
                wahoo_events = await fetch_wahoo_events()
                
                # Filter to active events (before lock_time)
                from datetime import datetime, timezone
                from dateutil.parser import parse as parse_date
                
                now = datetime.now(timezone.utc)
                active_events = []
                
                for event in wahoo_events:
                    lock_time_str = (
                        event.get("lock_time") or 
                        event.get("lockTime") or 
                        event.get("deadline") or
                        event.get("end_time") or
                        event.get("endTime")
                    )
                    
                    if lock_time_str:
                        try:
                            lock_time = parse_date(lock_time_str)
                            if lock_time.tzinfo is None:
                                lock_time = lock_time.replace(tzinfo=timezone.utc)
                            if now < lock_time:
                                active_events.append(event)
                        except:
                            pass
                
                for event in active_events:
                    event_id = f"wahoo_{event.get('id', '')}"
                    
                    # Generate prediction (miners should implement their own logic)
                    # This is a placeholder - replace with your own model/strategy
                    event_details = await fetch_wahoo_event_details(event.get('id', ''))
                    if event_details and "current_odds" in event_details:
                        prob_yes = float(event_details["current_odds"])
                    else:
                        prob_yes = 0.5  # Default neutral prediction
                    
                    # Create manifest hash
                    manifest_data = f"{event_id}:{prob_yes}"
                    manifest_hash = hashlib.sha256(manifest_data.encode()).hexdigest()
                    
                    # Sign with HMAC
                    api_secret = os.getenv("API_SECRET", "dev-secret")
                    sig = hmac.new(
                        api_secret.encode(),
                        manifest_hash.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    
                    # Submit to FastAPI service
                    submit_to_api(event_id, miner_id, prob_yes, manifest_hash, sig)
                    
                    bt.logging.info(f"Submitted prediction for {event_id}: prob_yes={prob_yes:.3f}")
                
                # Wait before next cycle
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                bt.logging.error(f"Error in miner loop: {e}")
                await asyncio.sleep(60)
    
    # Start background task
    import threading
    def run_async_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(miner_loop())
    
    miner_thread = threading.Thread(target=run_async_loop, daemon=True)
    miner_thread.start()
    
    # Keep running
    try:
        while True:
            # Update metagraph periodically
            metagraph = subtensor.metagraph(config.netuid)
            
            # Log status if miner is registered
            if wallet.hotkey.ss58_address in metagraph.hotkeys:
                uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
                bt.logging.info(
                    f"Miner {uid} | "
                    f"Stake: {metagraph.S[uid]:.2f} | "
                    f"Incentive: {metagraph.I[uid]:.2f}"
                )
            
            time.sleep(60)
            
    except KeyboardInterrupt:
        bt.logging.info("Miner stopped by user")


def submit_to_api(event_id: str, miner_id: str, prob_yes: float, manifest_hash: str, sig: str):
    """Submit prediction to FastAPI service."""
    import requests
    try:
        response = requests.post(
            f"{API_BASE_URL}/submit",
            json={
                "event_id": event_id,
                "miner_id": miner_id,
                "prob_yes": prob_yes,
                "manifest_hash": manifest_hash,
                "sig": sig
            },
            timeout=10
        )
        response.raise_for_status()
    except Exception as e:
        bt.logging.warning(f"API submission failed: {e}")


if __name__ == "__main__":
    main()

