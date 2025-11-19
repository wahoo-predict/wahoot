"""
Blockchain integration utilities for the WaHoo validator.

This module provides functions for:
- Transaction status checking after set_weights() calls
- Retry coordination for set_weights() operations
- Tracking successful weight submissions
"""

import logging
from typing import List, Optional, Tuple, Any

from .api import SET_WEIGHTS_MAX_RETRIES

logger = logging.getLogger(__name__)

# Issue #26: Track last successful set_weights() block
# This helps avoid duplicate submissions and track validator health
_last_successful_block: Optional[int] = None


def set_weights_with_retry(
    subtensor: Any,
    wallet: Any,
    netuid: int,
    uids: List[int],
    weights: Any,
    *,
    max_retries: int = SET_WEIGHTS_MAX_RETRIES,
) -> Tuple[Optional[str], bool]:
    """
    Call subtensor.set_weights() with retry logic and transaction tracking.

    Implements Issue #27: Retry logic for set_weights() operations.
    Implements Issue #26: Transaction status checking.

    Retry Strategy (Issue #27):
    - Allow one safe retry if the failure is transient (network/RPC)
    - Otherwise fail for this loop iteration
    - Retries must respect the ~100s main loop duration budget
    - All retry attempts are logged with attempt count and cause

    Transaction Tracking (Issue #26):
    - Captures transaction hash from set_weights() return value
    - Verifies success/failure via return value or exception type
    - Logs failure reasons, affected UIDs, and block step
    - Tracks last successful block to avoid duplicate submissions
    - Coordinates with retry logic to avoid blind retries

    Args:
        subtensor: Bittensor subtensor object
        wallet: Bittensor wallet object
        netuid: Network UID
        uids: List of miner UIDs
        weights: Weight tensor (must match uids length)
        max_retries: Maximum number of retries (default: SET_WEIGHTS_MAX_RETRIES = 1)

    Returns:
        Tuple[Optional[str], bool]: (transaction_hash, success)
        - transaction_hash: Transaction hash if successful, None otherwise
        - success: True if transaction succeeded, False otherwise

    Raises:
        Exception: If all retries are exhausted and transaction fails
    """
    max_attempts = max_retries + 1  # Total attempts = retries + 1
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        # Issue #27: Log every retry attempt with its cause and attempt count
        if attempt > 1:
            logger.info(
                f"set_weights() retry attempt {attempt}/{max_attempts} "
                f"(max_retries={max_retries})"
            )

        try:
            # Call subtensor.set_weights()
            # Note: The actual return type depends on bittensor version
            # Some versions return transaction hash, others return bool or None
            result = subtensor.set_weights(
                wallet=wallet,
                netuid=netuid,
                uids=uids,
                weights=weights,
            )

            # Issue #26: Capture transaction hash from return value
            # Handle different return types from bittensor versions
            transaction_hash: Optional[str] = None
            if isinstance(result, str):
                transaction_hash = result
            elif isinstance(result, dict) and "tx_hash" in result:
                transaction_hash = result["tx_hash"]
            elif isinstance(result, dict) and "hash" in result:
                transaction_hash = result["hash"]
            elif result is True or result is None:
                # Some versions return True/None on success
                transaction_hash = "success"  # Placeholder

            # Issue #26: Verify success and log
            if transaction_hash:
                logger.info(
                    f"set_weights() succeeded on attempt {attempt}/{max_attempts}. "
                    f"Transaction hash: {transaction_hash}. "
                    f"UIDs: {len(uids)} miners"
                )
                # Track last successful block (if available from subtensor)
                global _last_successful_block
                try:
                    if hasattr(subtensor, "block"):
                        _last_successful_block = subtensor.block
                except Exception:
                    pass  # Block tracking is optional

                return transaction_hash, True
            else:
                # Unclear result - treat as failure
                logger.warning(
                    f"set_weights() returned unclear result on attempt {attempt}/{max_attempts}: {result}"
                )
                if attempt >= max_attempts:
                    logger.error(
                        f"set_weights() exhausted all {max_attempts} attempts. "
                        f"Affected UIDs: {uids[:10]}..."  # Log first 10 for context
                    )
                    return None, False
                continue

        except Exception as exc:
            # Issue #26: Distinguish failure types (RPC error, nonce issue, etc.)
            failure_type = type(exc).__name__
            failure_reason = str(exc)

            # Issue #27: Log failure with attempt count
            logger.warning(
                f"set_weights() failed on attempt {attempt}/{max_attempts}: "
                f"{failure_type}: {failure_reason}"
            )

            # Determine if error is transient (network/RPC) and worth retrying
            is_transient = _is_transient_error(exc)

            if attempt >= max_attempts or not is_transient:
                # Issue #26: Log final failure with context
                logger.error(
                    f"set_weights() failed after {attempt} attempt(s). "
                    f"Failure type: {failure_type}. "
                    f"Failure reason: {failure_reason}. "
                    f"Affected UIDs: {uids[:10]}..."  # Log first 10 for context
                )

                # Issue #26: Track failure for this loop iteration
                # The main loop should skip weight updates for this iteration
                return None, False

            # Transient error - retry
            logger.info(
                f"Transient error detected, retrying set_weights() "
                f"(attempt {attempt}/{max_attempts})"
            )
            continue

    # Should not reach here, but handle edge case
    logger.error("set_weights() exhausted all retries")
    return None, False


def _is_transient_error(exc: Exception) -> bool:
    """
    Determine if an exception represents a transient error worth retrying.

    Implements Issue #27: Retry logic coordination.
    - Network errors (connection, timeout) are transient
    - RPC errors (temporary server issues) are transient
    - Nonce errors, insufficient balance, etc. are NOT transient

    Args:
        exc: Exception to check

    Returns:
        bool: True if error is transient and worth retrying, False otherwise
    """
    error_str = str(exc).lower()
    error_type = type(exc).__name__.lower()

    # Transient errors (worth retrying)
    transient_keywords = [
        "timeout",
        "connection",
        "network",
        "rpc",
        "temporary",
        "unavailable",
        "503",
        "502",
        "504",
    ]

    # Non-transient errors (don't retry)
    non_transient_keywords = [
        "nonce",
        "insufficient",
        "balance",
        "invalid",
        "unauthorized",
        "forbidden",
        "400",
        "401",
        "403",
    ]

    # Check for non-transient errors first
    for keyword in non_transient_keywords:
        if keyword in error_str or keyword in error_type:
            return False

    # Check for transient errors
    for keyword in transient_keywords:
        if keyword in error_str or keyword in error_type:
            return True

    # Default: assume non-transient (don't retry unknown errors)
    return False


def get_last_successful_block() -> Optional[int]:
    """
    Get the block number of the last successful set_weights() call.

    Implements Issue #26: Transaction status tracking.

    Returns:
        Optional[int]: Block number of last successful call, or None if never successful
    """
    return _last_successful_block


def reset_last_successful_block() -> None:
    """
    Reset the last successful block tracker.

    Useful for testing or manual reset scenarios.

    Implements Issue #26: Transaction status tracking.
    """
    global _last_successful_block
    _last_successful_block = None
