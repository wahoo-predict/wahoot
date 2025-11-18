"""
Reward computation module for the WaHoo validator.

This module implements the priority-based reward system:
WAHOO → Response validity

The priority system ensures that:
1. Primary: Use WAHOO weights (local scoring from this validator) when available
2. Fallback: Validate miner responses and assign temporary weights

Note: Weights are calculated locally by each validator based on data from WAHOO Predict API.
Multiple validators run independently, and Bittensor's consensus mechanism aggregates
the weights from all validators.
"""

import logging
import torch
from typing import Dict, List, Optional, Any

from wahoo.validator.utils.miners import build_uid_to_hotkey, is_valid_hotkey

logger = logging.getLogger(__name__)

# Note: Weights are calculated locally by each validator, not fetched from API.
# The ValidationAPIClient (wahoo/client.py) is for fetching DATA from WAHOO Predict API
# (trading statistics, validation data), not for fetching weights.


def _validate_response(response: Any) -> bool:
    """
    Validate a miner's response structure and values.

    Checks:
    - prob_yes is between 0.0 and 1.0 (inclusive)
    - prob_yes + prob_no equals 1.0 (within floating point tolerance)
    - Response is not None/empty

    Args:
        response: Miner response object (expected to have prob_yes, prob_no attributes)

    Returns:
        bool: True if response is valid, False otherwise
    """
    if response is None:
        return False

    # Check if response has required attributes
    if not hasattr(response, "prob_yes") or not hasattr(response, "prob_no"):
        return False

    try:
        prob_yes = float(response.prob_yes)
        prob_no = float(response.prob_no)

        # Check prob_yes is in valid range [0.0, 1.0]
        if not (0.0 <= prob_yes <= 1.0):
            return False

        # Check prob_yes + prob_no equals 1.0 (with tolerance for floating point)
        # Using small epsilon for floating point comparison
        epsilon = 1e-6
        if abs((prob_yes + prob_no) - 1.0) > epsilon:
            return False

        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _get_hotkey_from_uid(
    uid: int, metagraph: Any, uid_to_hotkey: Optional[Dict[int, str]] = None
) -> Optional[str]:
    """
    Extract hotkey string from UID using uid_to_hotkey mapping or metagraph.

    Priority:
    1. Use uid_to_hotkey mapping if provided (preferred)
    2. Fallback to metagraph.hotkeys[uid]

    Args:
        uid: Miner UID
        metagraph: Bittensor metagraph object
        uid_to_hotkey: Optional pre-built UID-to-hotkey mapping

    Returns:
        Optional[str]: Hotkey string if found and valid, None otherwise
    """
    # Try uid_to_hotkey mapping first (preferred)
    if uid_to_hotkey is not None and uid in uid_to_hotkey:
        hotkey = uid_to_hotkey[uid]
        if is_valid_hotkey(hotkey):
            return hotkey
    
    # Fallback to metagraph
    try:
        if hasattr(metagraph, "hotkeys") and uid < len(metagraph.hotkeys):
            hotkey = metagraph.hotkeys[uid]
            if is_valid_hotkey(hotkey):
                return str(hotkey).strip()
    except (IndexError, AttributeError, TypeError):
        pass
    
    return None


def reward(
    responses: List[Any],
    uids: List[int],
    metagraph: Any,
    wahoo_weights: Optional[Dict[str, float]] = None,
    wahoo_validation_data: Optional[List[Any]] = None,
    uid_to_hotkey: Optional[Dict[int, str]] = None,
) -> torch.FloatTensor:
    """
    Compute rewards for miners using a strict priority system.

    Priority System (applied per-UID):
    1. PRIMARY: Use wahoo_weights[hotkey] (local scoring output from this validator) when available
    2. FALLBACK: Validate miner response:
       - If valid (prob_yes in [0,1] and prob_yes + prob_no = 1.0) → weight 1.0
       - If invalid or missing → weight 0.0

    Note: Weights are calculated locally by each validator based on WAHOO Predict API data.
    Multiple validators run independently and calculate their own weights. Bittensor's
    consensus mechanism aggregates weights from all validators.

    This ensures partial WAHOO coverage is handled correctly - each UID is evaluated
    independently, so some miners may use WAHOO weights while others fall back to
    response validation.

    Args:
        responses: List of miner responses (synapse objects with prob_yes, prob_no)
        uids: List of miner UIDs corresponding to responses
        metagraph: Bittensor metagraph object for hotkey lookup
        wahoo_weights: Optional dict mapping hotkey to weight from local scoring
                      (typically from OperatorPipeline)
        wahoo_validation_data: Optional validation data (ValidationRecord objects from API)
        uid_to_hotkey: Optional pre-built mapping of UID to hotkey. If not provided,
                      will be built from metagraph. Recommended to build once and reuse.

    Returns:
        torch.FloatTensor: Normalized reward tensor with shape (len(uids),)
                          Sum equals 1.0, or all zeros if no valid rewards
    """
    if not uids or len(uids) == 0:
        return torch.FloatTensor([])

    if len(responses) != len(uids):
        # Mismatch in responses and UIDs - return zeros
        logger.warning(
            f"Mismatch: {len(responses)} responses for {len(uids)} UIDs. "
            "Returning zero rewards."
        )
        return torch.zeros(len(uids), dtype=torch.float32)

    # Build uid_to_hotkey mapping if not provided
    if uid_to_hotkey is None:
        logger.debug("Building uid_to_hotkey mapping from metagraph")
        uid_to_hotkey = build_uid_to_hotkey(metagraph, active_uids=uids)

    # Initialize rewards dictionary
    rewards_dict: Dict[int, float] = {}

    # Normalize wahoo_weights to empty dict if None
    if wahoo_weights is None:
        wahoo_weights = {}

    # Process each UID independently (per-UID priority)
    for idx, uid in enumerate(uids):
        response = responses[idx] if idx < len(responses) else None
        hotkey = _get_hotkey_from_uid(uid, metagraph, uid_to_hotkey)

        # Sanity check: if UID has no hotkey or malformed hotkey, set reward to 0 and log
        if hotkey is None or not is_valid_hotkey(hotkey):
            logger.warning(
                f"UID {uid} has no hotkey or malformed hotkey. "
                "Setting reward to 0.0"
            )
            rewards_dict[uid] = 0.0
            continue

        # PRIORITY 1: PRIMARY - Use WAHOO weights (local scoring from this validator)
        if hotkey in wahoo_weights:
            weight = wahoo_weights[hotkey]
            # Validate weight is a valid number
            try:
                weight_float = float(weight)
                if weight_float >= 0.0:  # Allow zero but not negative
                    rewards_dict[uid] = weight_float
                    continue
            except (ValueError, TypeError):
                pass  # Fall through to fallback

        # PRIORITY 2: FALLBACK - Validate response and assign temporary weight
        if _validate_response(response):
            # Valid response → temporary weight 1.0
            rewards_dict[uid] = 1.0
        else:
            # Invalid or missing response → weight 0.0
            rewards_dict[uid] = 0.0

    # Convert to tensor
    rewards = torch.FloatTensor([rewards_dict.get(uid, 0.0) for uid in uids])

    # Normalize to sum equals 1.0
    rewards_sum = rewards.sum()
    if rewards_sum > 0.0:
        rewards = rewards / rewards_sum
    else:
        # All zeros - return as is (sum is already 0.0)
        rewards = torch.zeros(len(uids), dtype=torch.float32)

    return rewards
