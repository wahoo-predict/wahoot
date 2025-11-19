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
import math
import os
import torch
from typing import Dict, List, Optional, Any

from wahoo.validator.utils.miners import build_uid_to_hotkey, is_valid_hotkey
from wahoo.validator.models import ValidationRecord

logger = logging.getLogger(__name__)

# Note: Weights are calculated locally by each validator, not fetched from API.
# The ValidationAPIClient (wahoo/client.py) is for fetching DATA from WAHOO Predict API
# (trading statistics, validation data), not for fetching weights.

# Configuration flag for Issue #22: Equal weights fallback
# When all rewards are zero, optionally assign equal weights to all miners with valid responses
USE_EQUAL_WEIGHTS_FALLBACK = (
    os.getenv("USE_EQUAL_WEIGHTS_FALLBACK", "false").lower() == "true"
)
# Threshold constants for Issue #20
MIN_VOLUME_USD = 0.0  # Minimum total volume in USD (0.0 = no minimum by default)
MIN_WIN_RATE = 0.0  # Minimum win rate (0.0-1.0, 0.0 = no minimum by default)


def _is_finite_number(value: float) -> bool:
    """
    Check if a value is a finite number (not NaN, not Inf).

    Implements Issue #25: Explicit finite/NaN checks for all numeric fields.

    Args:
        value: Numeric value to check

    Returns:
        bool: True if value is finite, False otherwise
    """
    return math.isfinite(value)


def _validate_response(response: Any) -> bool:
    """
    Validate a miner's response structure and values.

    Implements Issue #25: Response validation checks with protocol version,
    required fields, and explicit finite/NaN checks.

    Checks:
    - Response is not None/empty
    - Required fields present: prob_yes, prob_no
    - Optional fields validated if present: event_id, confidence, protocol_version
    - prob_yes is between 0.0 and 1.0 (inclusive) and is finite
    - prob_no is finite (can be negative for validation purposes, but must be finite)
    - prob_yes + prob_no equals 1.0 (within floating point tolerance)
    - All numeric fields are finite (not NaN, not Inf)

    Timeout Handling:
    - Responses that time out during dendrite.query() will be None or missing
    - This function returns False for None/missing responses, marking them invalid
    - Timeout handling is done at the dendrite.query() level (12s timeout per Issue #17)
    - Invalid responses (including timeouts) are assigned weight 0.0 in reward()

    Args:
        response: Miner response object (synapse with prob_yes, prob_no attributes)
                 Expected structure: WAHOOPredict synapse with:
                 - prob_yes: float (required, 0.0-1.0, finite)
                 - prob_no: float (required, finite)
                 - event_id: str (optional)
                 - confidence: float (optional, finite)
                 - protocol_version: str/int (optional)

    Returns:
        bool: True if response is valid, False otherwise
    """
    if response is None:
        logger.debug("Response is None (likely timeout or missing)")
        return False

    # Check if response has required attributes
    if not hasattr(response, "prob_yes") or not hasattr(response, "prob_no"):
        logger.debug("Response missing required fields: prob_yes or prob_no")
        return False

    try:
        # Convert to float and validate finite
        prob_yes = float(response.prob_yes)
        prob_no = float(response.prob_no)

        # Issue #25: Explicit finite/NaN checks for all numeric fields
        if not _is_finite_number(prob_yes):
            logger.debug(f"prob_yes is not finite: {prob_yes}")
            return False

        if not _is_finite_number(prob_no):
            logger.debug(f"prob_no is not finite: {prob_no}")
            return False

        # Check prob_yes is in valid range [0.0, 1.0]
        if not (0.0 <= prob_yes <= 1.0):
            logger.debug(f"prob_yes out of range [0.0, 1.0]: {prob_yes}")
            return False

        # Check prob_yes + prob_no equals 1.0 (with tolerance for floating point)
        # Using small epsilon for floating point comparison
        epsilon = 1e-6
        if abs((prob_yes + prob_no) - 1.0) > epsilon:
            logger.debug(
                f"prob_yes + prob_no != 1.0: {prob_yes} + {prob_no} = {prob_yes + prob_no}"
            )
            return False

        # Issue #25: Validate optional fields if present
        # Check event_id if present (should be non-empty string)
        if hasattr(response, "event_id") and response.event_id is not None:
            if not isinstance(response.event_id, str) or len(
                response.event_id.strip()
            ) == 0:
                logger.debug(f"event_id is invalid: {response.event_id}")
                return False

        # Check confidence if present (should be finite float, typically 0.0-1.0)
        if hasattr(response, "confidence") and response.confidence is not None:
            try:
                confidence = float(response.confidence)
                if not _is_finite_number(confidence):
                    logger.debug(f"confidence is not finite: {confidence}")
                    return False
                # Optional: validate confidence is in reasonable range [0.0, 1.0]
                if not (0.0 <= confidence <= 1.0):
                    logger.debug(
                        f"confidence out of range [0.0, 1.0]: {confidence}"
                    )
                    return False
            except (ValueError, TypeError):
                logger.debug(
                    f"confidence cannot be converted to float: {response.confidence}"
                )
                return False

        # Check protocol_version if present (should be string or int)
        if hasattr(response, "protocol_version") and response.protocol_version is not None:
            if not isinstance(response.protocol_version, (str, int)):
                logger.debug(
                    f"protocol_version has invalid type: {type(response.protocol_version)}"
                )
                return False

        return True
    except (ValueError, TypeError, AttributeError) as exc:
        logger.debug(f"Response validation error: {exc}")
        return False


def _check_thresholds(record: ValidationRecord) -> tuple[bool, Optional[str]]:
    """
    Check if validation record passes minimum thresholds.

    Implements Issue #20: Threshold checks for MIN_VOLUME_USD and MIN_WIN_RATE.

    Args:
        record: ValidationRecord to check

    Returns:
        tuple[bool, Optional[str]]: (passes_thresholds, failure_reason)
        - passes_thresholds: True if record passes all thresholds
        - failure_reason: None if passes, or reason string if fails
    """
    if not record or not record.performance:
        return False, "missing validation data"

    perf = record.performance

    # Check MIN_VOLUME_USD threshold
    volume = perf.total_volume_usd
    if volume is None or volume < MIN_VOLUME_USD:
        return False, f"volume below threshold (volume={volume}, min={MIN_VOLUME_USD})"

    # Check MIN_WIN_RATE threshold (if win_rate is available)
    win_rate = perf.win_rate
    if win_rate is not None and win_rate < MIN_WIN_RATE:
        return (
            False,
            f"win_rate below threshold (win_rate={win_rate}, min={MIN_WIN_RATE})",
        )

    return True, None


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

    Implements Issue #20: Build reward dictionary with threshold checks and detailed logging.

    Priority System (applied per-UID):
    1. PRIMARY: Use wahoo_weights[hotkey] (local scoring output from this validator) when available
    2. FALLBACK: Validate miner response:
       - If valid (prob_yes in [0,1] and prob_yes + prob_no = 1.0) → weight 1.0
       - If invalid or missing → weight 0.0

    Threshold Checks (Issue #20):
    - Miners below MIN_VOLUME_USD or MIN_WIN_RATE are assigned weight 0
    - Detailed logging explains why weight is 0 (missing data vs thresholds vs invalid response)

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
                          Sum equals 1.0 when total > 0, or all zeros if no valid rewards

    Implements Issues #21 and #22:
    - Issue #21: Tensor conversion with list comprehension, ordered by uids
    - Issue #22: Safe normalization with division-by-zero handling and invariant checks

    Note: The order of rewards in the returned tensor MUST match the order of uids
    passed to subtensor.set_weights(). This alignment is critical for correct on-chain
    weight assignment. The list comprehension guarantees deterministic ordering.
                          Sum equals 1.0, or all zeros if no valid rewards

    Note: rewards_dict is the single source of truth before tensor conversion (Issue #20).
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

    # Build uid_to_hotkey mapping if not provided (Issue #20: Task 1)
    if uid_to_hotkey is None:
        logger.debug("Building uid_to_hotkey mapping from metagraph")
        uid_to_hotkey = build_uid_to_hotkey(metagraph, active_uids=uids)

    # Initialize rewards dictionary (Issue #20: Single source of truth)
    rewards_dict: Dict[int, float] = {}

    # Normalize wahoo_weights to empty dict if None
    if wahoo_weights is None:
        wahoo_weights = {}

    # Build hotkey -> ValidationRecord mapping for threshold checks
    validation_by_hotkey: Dict[str, ValidationRecord] = {}
    if wahoo_validation_data:
        for record in wahoo_validation_data:
            if isinstance(record, ValidationRecord):
                validation_by_hotkey[record.hotkey] = record

    # Process each UID independently (per-UID priority) - Issue #20: Task 1 & 2
    for idx, uid in enumerate(uids):
        response = responses[idx] if idx < len(responses) else None
        hotkey = _get_hotkey_from_uid(uid, metagraph, uid_to_hotkey)

        # Sanity check: if UID has no hotkey or malformed hotkey, set reward to 0 and log
        if hotkey is None or not is_valid_hotkey(hotkey):
            logger.warning(
                f"UID {uid}: missing or invalid hotkey. Setting weight to 0.0"
            )
            rewards_dict[uid] = 0.0
            continue

        # PRIORITY 1: PRIMARY - Use WAHOO weights (local scoring from this validator)
        # Issue #20: Task 2 - Resolve weight using priority system
        if hotkey in wahoo_weights:
            weight = wahoo_weights[hotkey]
            # Validate weight is a valid number
            try:
                weight_float = float(weight)
                if weight_float >= 0.0:  # Allow zero but not negative
                    # Check thresholds before assigning weight (Issue #20: Task 4)
                    validation_record = validation_by_hotkey.get(hotkey)
                    if validation_record:
                        passes, reason = _check_thresholds(validation_record)
                        if not passes:
                            logger.warning(
                                f"UID {uid} (hotkey={hotkey}): "
                                f"failing thresholds - {reason}. Setting weight to 0.0"
                            )
                            rewards_dict[uid] = 0.0
                        else:
                            # Issue #20: Task 3 - Store resolved weight in rewards_dict
                            rewards_dict[uid] = weight_float
                    else:
                        # No validation data, but we have WAHOO weight - use it
                        rewards_dict[uid] = weight_float
                    continue
            except (ValueError, TypeError):
                pass  # Fall through to fallback

        # PRIORITY 2: FALLBACK - Validate response and assign temporary weight
        # Issue #20: Task 2 - Resolve weight using priority system (fallback path)
        if _validate_response(response):
            # Valid response → temporary weight 1.0
            # But first check thresholds if validation data exists (Issue #20: Task 4)
            validation_record = validation_by_hotkey.get(hotkey)
            if validation_record:
                passes, reason = _check_thresholds(validation_record)
                if not passes:
                    logger.warning(
                        f"UID {uid} (hotkey={hotkey}): "
                        f"failing thresholds - {reason}. Setting weight to 0.0"
                    )
                    rewards_dict[uid] = 0.0
                else:
                    rewards_dict[uid] = 1.0
            else:
                # No validation data, but valid response - use fallback weight
                rewards_dict[uid] = 1.0
        else:
            # Invalid or missing response → weight 0.0
            # Issue #20: Task 5 - Log reason for weight 0
            validation_record = validation_by_hotkey.get(hotkey)
            if validation_record:
                passes, reason = _check_thresholds(validation_record)
                if not passes:
                    logger.warning(
                        f"UID {uid} (hotkey={hotkey}): "
                        f"failing thresholds - {reason}. Setting weight to 0.0"
                    )
                else:
                    logger.debug(
                        f"UID {uid} (hotkey={hotkey}): "
                        "invalid response. Setting weight to 0.0"
                    )
            else:
                logger.debug(
                    f"UID {uid} (hotkey={hotkey}): "
                    "missing validation data and invalid response. Setting weight to 0.0"
                )
            rewards_dict[uid] = 0.0

    # Issue #21: Convert rewards_dict to tensor with list comprehension
    # CRITICAL: The order of rewards MUST match the order of uids passed to subtensor.set_weights()
    # This ensures correct on-chain alignment - each reward[i] corresponds to uids[i]
    # The list comprehension guarantees deterministic ordering based on the uids list
    # Issue #20: Task 6 - rewards_dict is the single source of truth before tensor conversion
    # Convert to tensor from rewards_dict
    rewards = torch.FloatTensor([rewards_dict.get(uid, 0.0) for uid in uids])

    # Issue #22: Safe normalization with division-by-zero handling
    total = rewards.sum()
    if total > 0.0:
        # Normal case: divide by sum to normalize
        rewards = rewards / total
    else:
        # Division-by-zero case: all rewards are zero
        # Optionally fall back to equal weights if config flag is enabled (Issue #22)
        if USE_EQUAL_WEIGHTS_FALLBACK:
            # Count valid responses (miners with valid responses got weight 1.0 in rewards_dict)
            valid_count = sum(1 for uid in uids if rewards_dict.get(uid, 0.0) > 0.0)
            if valid_count > 0:
                # Assign equal weights to all miners with valid responses
                equal_weight = 1.0 / valid_count
                rewards = torch.FloatTensor(
                    [
                        equal_weight if rewards_dict.get(uid, 0.0) > 0.0 else 0.0
                        for uid in uids
                    ]
                )
                logger.info(
                    f"All WAHOO weights zero, using equal weights fallback: "
                    f"{valid_count} miners with valid responses, weight={equal_weight:.6f}"
                )
            else:
                # No valid responses - return zeros
                rewards = torch.zeros(len(uids), dtype=torch.float32)
        else:
            # Default: return zeros when total is zero
            rewards = torch.zeros(len(uids), dtype=torch.float32)

    # Issue #22: Enforce invariants after normalization
    # Invariant 1: Shape must match uids length
    assert rewards.shape == (
        len(uids),
    ), f"Rewards shape mismatch: expected ({len(uids)},), got {rewards.shape}"

    # Invariant 2: When total > 0, sum must be approximately 1.0 (within floating point tolerance)
    if total > 0.0:
        sum_after_norm = rewards.sum().item()
        epsilon = 1e-6
        if abs(sum_after_norm - 1.0) >= epsilon:
            logger.warning(
                f"Normalization invariant violation: rewards.sum() = {sum_after_norm}, "
                f"expected 1.0 (tolerance: {epsilon})"
            )

    # Issue #22: Document when to call subtensor.set_weights()
    # Only call set_weights() when:
    #   1. total > 0 (at least one non-zero reward)
    #   2. rewards.sum() > 0 (after normalization, still has non-zero entries)
    # This matches the "Rewards Sum > 0 Only set weights if valid" requirement
    if total > 0.0 and rewards.sum().item() > 0.0:
        # Ready for set_weights() call
        pass
    else:
        # Do NOT call set_weights() - all rewards are zero
        logger.debug(
            "Skipping set_weights() call: all rewards are zero "
            f"(total={total}, rewards.sum()={rewards.sum().item()})"
        )

    return rewards
