"""
WAHOOPREDICT - Validator implementation for the Bittensor subnet.

Validators call APIs, score miner responses, and set weights on-chain.
Simple loop: sync metagraph → get rankings → query miners → score → set weights
"""

import bittensor as bt
import torch
import time
import os
import httpx
from typing import List, Dict, Any

from template.protocol import WAHOOPredict
from template.reward import reward


# API URLs (configured via environment variables)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WAHOO_API_URL = os.getenv("WAHOO_API_URL", "https://api.wahoopredict.com")


def get_active_uids(metagraph: "bt.metagraph.Metagraph") -> List[int]:
    """Get list of active miner UIDs."""
    return [
        uid for uid in range(metagraph.n)
        if metagraph.axons[uid].ip != "0.0.0.0"
    ]


def get_weights_from_api(api_base_url: str) -> Dict[str, float]:
    """
    Get normalized weights from API.
    
    Args:
        api_base_url: Base URL for the API
        
    Returns:
        Dictionary mapping miner_id (hotkey) to weight
    """
    try:
        response = httpx.get(f"{api_base_url}/weights", timeout=10.0)
        if response.status_code == 200:
            weights_data = response.json()
            return {w["miner_id"]: w["weight"] for w in weights_data.get("weights", [])}
    except Exception as e:
        bt.logging.warning(f"Failed to get weights from API: {e}")
    
    return {}


def get_wahoo_rankings(
    hotkeys: List[str],
    days: int = 7,
    metrics: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Get miner rankings from WAHOO API.
    
    Args:
        hotkeys: List of SS58 hotkey addresses
        days: Number of days to look back (default: 7)
        metrics: Optional list of metrics to include
        
    Returns:
        List of miner ranking dictionaries
    """
    if metrics is None:
        metrics = ['volume', 'profit']
    
    try:
        from datetime import datetime, timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        payload = {
            "hotkeys": hotkeys,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metrics": metrics
        }
        
        response = httpx.post(
            f"{WAHOO_API_URL}/api/v1/miners/rankings",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "rankings" in data:
            return data["rankings"]
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return []
            
    except Exception as e:
        bt.logging.warning(f"Failed to get WAHOO rankings: {e}")
        return []


def get_active_event_id(api_base_url: str) -> str:
    """Get an active event ID from the API."""
    try:
        response = httpx.get(f"{api_base_url}/events", timeout=10)
        if response.status_code == 200:
            events = response.json()
            if events:
                return events[0]["event_id"]
    except Exception as e:
        bt.logging.warning(f"Failed to get events from API: {e}")
    
    return "wahoo_test_event"


def main():
    """Main entry point for validator."""
    # Parse command line arguments
    parser = bt.subtensor.add_args()
    parser = bt.logging.add_args(parser)
    parser = bt.wallet.add_args(parser)
    config = bt.config(parser)
    
    # Initialize wallet and subtensor
    wallet = bt.wallet(config=config)
    subtensor = bt.subtensor(config=config)
    dendrite = bt.dendrite(wallet=wallet)
    
    bt.logging.info("Validator started")
    
    # Main loop: Query miners and set weights
    try:
        while True:
            # Sync metagraph - this keeps the metagraph in sync for weight setting
            metagraph = subtensor.metagraph(config.netuid)
            
            # Get active miners
            active_uids = get_active_uids(metagraph)
            
            if not active_uids:
                bt.logging.warning("No active miners found")
                time.sleep(60)
                continue
            
            # Get list of hotkeys from metagraph
            hotkeys = [metagraph.hotkeys[uid] for uid in active_uids]
            
            # Get miner rankings from WAHOO API (past 7 days)
            rankings = get_wahoo_rankings(
                hotkeys=hotkeys,
                days=7,
                metrics=['volume', 'profit']
            )
            if rankings:
                bt.logging.info(f"Retrieved rankings for {len(rankings)} miners from WAHOO API")
            
            # Get active event
            event_id = get_active_event_id(API_BASE_URL)
            
            bt.logging.info(f"Querying {len(active_uids)} miners for event {event_id}")
            
            # Query miners
            synapses = [WAHOOPredict(event_id=event_id) for _ in active_uids]
            axons = [metagraph.axons[uid] for uid in active_uids]
            responses = dendrite.query(
                axons=axons,
                synapses=synapses,
                deserialize=True,
                timeout=12.0,
            )
            
            # Compute rewards (incorporates WAHOO rankings and API weights)
            rewards = reward(
                validator=None,
                responses=responses,
                uids=active_uids,
                metagraph=metagraph,
                api_base_url=API_BASE_URL,
                wahoo_rankings=rankings,
            )
            
            # Set weights on-chain
            if rewards.sum() > 0:
                try:
                    subtensor.set_weights(
                        wallet=wallet,
                        netuid=config.netuid,
                        uids=active_uids,
                        weights=rewards,
                        wait_for_inclusion=True,
                    )
                    bt.logging.info(f"Updated on-chain weights for {len(active_uids)} miners")
                except Exception as e:
                    bt.logging.error(f"Error setting weights: {e}")
            
            # Wait before next iteration (100 seconds)
            time.sleep(100)
            
    except KeyboardInterrupt:
        bt.logging.info("Validator stopped by user")


if __name__ == "__main__":
    main()
