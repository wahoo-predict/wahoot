"""
WAHOOPREDICT - Validator implementation for the Bittensor subnet.

Validators call APIs, score miner responses, and set weights on-chain.
Simple loop: sync metagraph → get WAHOO validation data → query miners → score → set weights
"""

import bittensor as bt
import torch
import time
import os
import httpx
from typing import List, Dict, Any, Optional

from template.protocol import WAHOOPredict
from template.reward import reward
from neurons.validator_db import ValidatorDB
from neurons.scoring import compute_final_weights


# API URLs (configured via environment variables)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WAHOO_API_URL = os.getenv("WAHOO_API_URL", "https://api.wahoopredict.com")

# Optional: Enable SQLite backup for validators
USE_VALIDATOR_DB = os.getenv("USE_VALIDATOR_DB", "false").lower() == "true"
VALIDATOR_DB_PATH = os.getenv("VALIDATOR_DB_PATH", None)


def get_active_uids(metagraph: "bt.metagraph.Metagraph") -> List[int]:
    """Get list of active miner UIDs."""
    return [
        uid for uid in range(metagraph.n)
        if metagraph.axons[uid].ip != "0.0.0.0"
    ]


def get_weights_from_api(api_base_url: str, validator_db: Optional[ValidatorDB] = None) -> Dict[str, float]:
    """
    Get normalized weights from API, with SQLite backup fallback.
    
    Args:
        api_base_url: Base URL for the API
        validator_db: Optional validator database for backup
        
    Returns:
        Dictionary mapping miner_id (hotkey) to weight
    """
    try:
        response = httpx.get(f"{api_base_url}/weights", timeout=10.0)
        if response.status_code == 200:
            weights_data = response.json()
            weights = {w["miner_id"]: w["weight"] for w in weights_data.get("weights", [])}
            
            # Cache weights in validator DB if available
            if validator_db:
                validator_db.cache_weights(weights)
            
            return weights
    except Exception as e:
        bt.logging.warning(f"Failed to get weights from API: {e}")
        
        # Fallback to cached weights if API fails
        if validator_db:
            cached_weights = validator_db.get_cached_weights()
            if cached_weights:
                bt.logging.info(f"Using cached weights from backup database ({len(cached_weights)} miners)")
                return cached_weights
    
    return {}


def get_wahoo_validation_data(
    hotkeys: List[str],
    start_date: str = None,
    end_date: str = None,
    batch_size: int = 246,
    validator_db: Optional[ValidatorDB] = None
) -> List[Dict[str, Any]]:
    """
    Get miner validation data from WAHOO API.
    
    This endpoint provides time-filtered performance data for a list of hotkeys.
    Handles batching for large hotkey lists (max 246-248 per request).
    
    Args:
        hotkeys: List of SS58 hotkey addresses (max 256, but should be 246-248)
        start_date: Optional ISO 8601 datetime string (e.g., "2024-01-01T00:00:00Z")
        end_date: Optional ISO 8601 datetime string (e.g., "2024-01-08T00:00:00Z")
        batch_size: Maximum number of hotkeys per request (default: 246)
        validator_db: Optional validator database for caching
        
    Returns:
        List of validation data dictionaries with hotkey, signature, message, and performance metrics
    """
    all_results = []
    
    # Batch hotkeys into chunks of batch_size
    for i in range(0, len(hotkeys), batch_size):
        batch_hotkeys = hotkeys[i:i + batch_size]
        
        try:
            # Build query parameters
            params = {
                "hotkeys": ",".join(batch_hotkeys)
            }
            
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            
            # Make GET request to validation endpoint
            response = httpx.get(
                f"{WAHOO_API_URL}/api/v2/users/validation",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle response format: {"status": "success", "data": [...]}
            batch_results = []
            if isinstance(data, dict):
                if data.get("status") == "success" and "data" in data:
                    batch_results = data["data"]
                elif isinstance(data.get("data"), list):
                    batch_results = data["data"]
            elif isinstance(data, list):
                batch_results = data
            
            all_results.extend(batch_results)
            
            # Cache validation data in validator DB if available
            if validator_db:
                for result in batch_results:
                    hotkey = result.get("hotkey")
                    if hotkey:
                        validator_db.cache_validation_data(hotkey, result)
                
        except httpx.HTTPStatusError as e:
            bt.logging.warning(f"HTTP error getting WAHOO validation data for batch {i//batch_size + 1}: {e}")
            # Try to use cached data if available
            if validator_db:
                for hotkey in batch_hotkeys:
                    cached = validator_db.get_cached_validation_data(hotkey)
                    if cached:
                        all_results.append(cached)
        except Exception as e:
            bt.logging.warning(f"Failed to get WAHOO validation data for batch {i//batch_size + 1}: {e}")
            # Try to use cached data if available
            if validator_db:
                for hotkey in batch_hotkeys:
                    cached = validator_db.get_cached_validation_data(hotkey)
                    if cached:
                        all_results.append(cached)
    
    return all_results


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
    
    # Initialize validator database if enabled
    validator_db = None
    if USE_VALIDATOR_DB:
        validator_db = ValidatorDB(db_path=VALIDATOR_DB_PATH)
        bt.logging.info(f"Validator database enabled: {validator_db.db_path}")
    
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
            
            # Store hotkeys in validator DB if enabled
            if validator_db:
                for hotkey in hotkeys:
                    validator_db.add_hotkey(hotkey)
            
            # Get miner validation data from WAHOO API
            # Optionally filter by date range (default: all history for registered miners)
            validation_data = get_wahoo_validation_data(
                hotkeys=hotkeys,
                start_date=None,  # None = all history
                end_date=None,    # None = most recent data
                validator_db=validator_db,
            )
            if validation_data:
                bt.logging.info(f"Retrieved validation data for {len(validation_data)} miners from WAHOO API")
            
            # Compute weights from WAHOO validation data
            # This is the primary scoring mechanism
            # Ranks miners by spending and volume, then combines rankings
            wahoo_weights = compute_final_weights(
                validation_data=validation_data,
                spending_weight=0.5,  # Weight for spending ranking
                volume_weight=0.5,    # Weight for volume ranking
                min_spending=0.0,     # Minimum spending threshold
                min_volume=0.0        # Minimum volume threshold
            )
            
            if wahoo_weights:
                bt.logging.info(f"Computed weights for {len(wahoo_weights)} miners")
            
            # Get active event (optional - can use a default if API is down)
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
            
            # Compute rewards (uses WAHOO weights as primary, with fallbacks)
            # This converts the wahoo_weights dict into a PyTorch tensor aligned with uids
            # The tensor is already normalized (sums to 1.0)
            rewards = reward(
                validator=None,
                responses=responses,
                uids=active_uids,
                metagraph=metagraph,
                api_base_url=API_BASE_URL,
                wahoo_weights=wahoo_weights,
                wahoo_validation_data=validation_data,
                validator_db=validator_db,
            )
            
            # Set weights on-chain using Bittensor's subtensor.set_weights()
            # This posts the weights to the blockchain for all active miners
            # weights: PyTorch tensor of shape [len(uids)], already normalized
            # uids: List of miner UIDs corresponding to each weight
            if rewards.sum() > 0:
                try:
                    subtensor.set_weights(
                        wallet=wallet,           # Validator wallet (pays transaction fees)
                        netuid=config.netuid,    # Subnet UID
                        uids=active_uids,        # List of miner UIDs
                        weights=rewards,         # PyTorch tensor of weights (normalized, sums to 1.0)
                        wait_for_inclusion=True, # Wait for transaction to be included in block
                    )
                    bt.logging.info(f"Updated on-chain weights for {len(active_uids)} miners")
                except Exception as e:
                    bt.logging.error(f"Error setting weights: {e}")
            
            # Cleanup old cache if validator DB is enabled
            if validator_db:
                validator_db.cleanup_old_cache(days=7)
            
            # Wait before next iteration (100 seconds)
            time.sleep(100)
            
    except KeyboardInterrupt:
        bt.logging.info("Validator stopped by user")


if __name__ == "__main__":
    main()
