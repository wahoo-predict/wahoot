"""
WAHOOPREDICT - Validator forward pass.

Defines how validators query miners for predictions.
"""

import bittensor as bt
from typing import List
from template.protocol import WAHOOPredict


async def forward(
    validator: any,
    synapse: WAHOOPredict,
    response: WAHOOPredict,
) -> float:
    """
    Validator forward pass.
    
    This function is called after receiving a response from a miner.
    It validates the response and returns a score.
    
    Args:
        validator: The validator neuron instance (unused, kept for compatibility)
        synapse: The original synapse sent to the miner
        response: The miner's response
        
    Returns:
        Score for the miner's response (0.0 to 1.0)
    """
    # Validate response
    if response is None:
        return 0.0
    
    # Check if response has required fields
    if not hasattr(response, 'prob_yes'):
        return 0.0
    
    # Validate prob_yes is in valid range
    if not (0.0 <= response.prob_yes <= 1.0):
        return 0.0
    
    # Validate manifest hash and signature if present
    if hasattr(response, 'manifest_hash') and response.manifest_hash:
        # Basic validation - in production, verify HMAC signature
        if not response.manifest_hash:
            return 0.0
    
    # Return base score for valid response
    # Actual scoring is done in reward.py based on Brier scores
    return 1.0

