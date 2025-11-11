"""
WAHOOPREDICT - Reward mechanism.

Defines how validators reward miner responses based on API data.
"""

import bittensor as bt
from typing import List, Dict, Any
import torch
import httpx

from template.protocol import WAHOOPredict


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


def reward(
    validator: any,
    responses: List[WAHOOPredict],
    uids: List[int],
    metagraph: "bt.metagraph.Metagraph",
    api_base_url: str = "http://localhost:8000",
    wahoo_rankings: List[Dict[str, Any]] = None,
) -> torch.FloatTensor:
    """
    Reward miners based on their responses and API data.
    
    This function computes rewards for miners based on:
    1. API weights (computed from EMA(7d) Brier scores)
    2. WAHOO API rankings (volume, profit, etc.)
    3. Response validity (fallback if no API weight available)
    
    Args:
        validator: The validator neuron instance (unused, kept for compatibility)
        responses: List of miner responses
        uids: List of miner UIDs
        metagraph: The metagraph
        api_base_url: Base URL for the API
        wahoo_rankings: Optional list of miner rankings from WAHOO API
        
    Returns:
        Tensor of rewards for each miner
    """
    # Get weights from API
    db_weights = get_weights_from_api(api_base_url)
    
    # Create mapping of hotkey to WAHOO ranking
    wahoo_weights = {}
    if wahoo_rankings:
        for ranking in wahoo_rankings:
            hotkey = ranking.get("ss58_address") or ranking.get("hotkey")
            if hotkey:
                # Use rank or metrics to compute weight
                rank = ranking.get("rank", 999)
                volume = ranking.get("volume", 0.0)
                profit = ranking.get("profit", 0.0)
                
                # Combine metrics (normalize by rank, weight by volume/profit)
                # Lower rank number = better rank
                rank_weight = 1.0 / max(rank, 1)  # Inverse rank
                volume_weight = float(volume) / 1000.0 if volume > 0 else 0.0  # Normalize volume
                profit_weight = float(profit) / 100.0 if profit > 0 else 0.0  # Normalize profit
                
                # Combined weight from WAHOO rankings
                wahoo_weights[hotkey] = rank_weight * (1.0 + volume_weight + profit_weight)
    
    # Initialize rewards tensor
    rewards = torch.zeros(len(uids))
    
    # Score each miner
    for idx, (uid, response) in enumerate(zip(uids, responses)):
        miner_id = metagraph.hotkeys[uid]
        
        # Priority: 1. API weights, 2. WAHOO rankings, 3. Response validity
        if miner_id in db_weights:
            rewards[idx] = db_weights[miner_id]
        elif miner_id in wahoo_weights:
            rewards[idx] = wahoo_weights[miner_id]
        elif response is not None and hasattr(response, 'prob_yes'):
            # Fallback: score based on response validity
            if 0.0 <= response.prob_yes <= 1.0:
                rewards[idx] = 1.0
            else:
                rewards[idx] = 0.0
        else:
            rewards[idx] = 0.0
    
    # Normalize rewards
    total = rewards.sum()
    if total > 0:
        rewards = rewards / total
    
    return rewards
