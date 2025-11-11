"""
WAHOOPREDICT - Reward mechanism.

Defines how validators reward miner responses based on WAHOO performance data.
"""

import bittensor as bt
from typing import List, Dict, Any
import torch
import httpx

from template.protocol import WAHOOPredict


def get_weights_from_api(api_base_url: str, validator_db: any = None) -> Dict[str, float]:
    """
    Get normalized weights from API (optional fallback).
    
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


def reward(
    validator: any,
    responses: List[WAHOOPredict],
    uids: List[int],
    metagraph: "bt.metagraph.Metagraph",
    api_base_url: str = "http://localhost:8000",
    wahoo_weights: Dict[str, float] = None,
    wahoo_validation_data: List[Dict[str, Any]] = None,
    validator_db: any = None,
) -> torch.FloatTensor:
    """
    Reward miners based on their responses and WAHOO performance data.
    
    This function computes rewards for miners based on:
    1. WAHOO weights (computed from performance metrics) - PRIMARY
    2. API weights (optional fallback from scoring API)
    3. Response validity (fallback if no weight available)
    
    Args:
        validator: The validator neuron instance (unused, kept for compatibility)
        responses: List of miner responses
        uids: List of miner UIDs
        metagraph: The metagraph
        api_base_url: Base URL for the API (optional fallback)
        wahoo_weights: Pre-computed weights from WAHOO validation data (PRIMARY)
        wahoo_validation_data: Optional list of validation data from WAHOO API
        validator_db: Optional validator database for backup
        
    Returns:
        Tensor of rewards for each miner
    """
    # Get weights from API (optional fallback)
    db_weights = get_weights_from_api(api_base_url, validator_db=validator_db)
    
    # Initialize rewards tensor (PyTorch tensor, shape: [len(uids)])
    # This tensor will be posted to the blockchain
    rewards = torch.zeros(len(uids))
    
    # Score each miner and assign weight to corresponding index in tensor
    # The index in rewards[idx] corresponds to uids[idx]
    for idx, (uid, response) in enumerate(zip(uids, responses)):
        miner_id = metagraph.hotkeys[uid]
        
        # Priority: 1. WAHOO weights (PRIMARY), 2. API weights (fallback), 3. Response validity
        if wahoo_weights and miner_id in wahoo_weights:
            # Use pre-computed weight from WAHOO scoring
            rewards[idx] = wahoo_weights[miner_id]
        elif db_weights and miner_id in db_weights:
            # Fallback to API weights if available
            rewards[idx] = db_weights[miner_id]
        elif response is not None and hasattr(response, 'prob_yes'):
            # Fallback: score based on response validity
            if 0.0 <= response.prob_yes <= 1.0:
                rewards[idx] = 1.0
            else:
                rewards[idx] = 0.0
        else:
            rewards[idx] = 0.0
    
    # Normalize rewards to sum to 1.0 (required by Bittensor)
    # This ensures the weights are properly distributed
    total = rewards.sum()
    if total > 0:
        rewards = rewards / total
    
    # Return PyTorch tensor that will be posted to blockchain
    # Shape: [len(uids)], values sum to 1.0
    return rewards
