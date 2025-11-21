import logging
from typing import List, Optional, Tuple, Any

from .api import SET_WEIGHTS_MAX_RETRIES

logger = logging.getLogger(__name__)

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
    max_attempts = max_retries + 1
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        if attempt > 1:
            logger.info(
                f"set_weights() retry attempt {attempt}/{max_attempts} "
                f"(max_retries={max_retries})"
            )

        try:
            result = subtensor.set_weights(
                wallet=wallet,
                netuid=netuid,
                uids=uids,
                weights=weights,
            )

            transaction_hash: Optional[str] = None
            if isinstance(result, str):
                transaction_hash = result
            elif isinstance(result, dict) and "tx_hash" in result:
                transaction_hash = result["tx_hash"]
            elif isinstance(result, dict) and "hash" in result:
                transaction_hash = result["hash"]
            elif result is True or result is None:
                transaction_hash = "success"

            if transaction_hash:
                logger.info(
                    f"set_weights() succeeded on attempt {attempt}/{max_attempts}. "
                    f"Transaction hash: {transaction_hash}. "
                    f"UIDs: {len(uids)} miners"
                )
                global _last_successful_block
                try:
                    if hasattr(subtensor, "block"):
                        _last_successful_block = subtensor.block
                except Exception:
                    pass

                return transaction_hash, True
            else:
                logger.warning(
                    f"set_weights() returned unclear result on attempt {attempt}/{max_attempts}: {result}"
                )
                if attempt >= max_attempts:
                    logger.error(
                        f"set_weights() exhausted all {max_attempts} attempts. "
                        f"Affected UIDs: {uids[:10]}..."
                    )
                    return None, False
                continue

        except Exception as exc:
            failure_type = type(exc).__name__
            failure_reason = str(exc)

            logger.warning(
                f"set_weights() failed on attempt {attempt}/{max_attempts}: "
                f"{failure_type}: {failure_reason}"
            )

            is_transient = _is_transient_error(exc)

            if attempt >= max_attempts or not is_transient:
                logger.error(
                    f"set_weights() failed after {attempt} attempt(s). "
                    f"Failure type: {failure_type}. "
                    f"Failure reason: {failure_reason}. "
                    f"Affected UIDs: {uids[:10]}..."
                )

                return None, False

            logger.info(
                f"Transient error detected, retrying set_weights() "
                f"(attempt {attempt}/{max_attempts})"
            )
            continue

    logger.error("set_weights() exhausted all retries")
    return None, False


def _is_transient_error(exc: Exception) -> bool:
    error_str = str(exc).lower()
    error_type = type(exc).__name__.lower()

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

    for keyword in non_transient_keywords:
        if keyword in error_str or keyword in error_type:
            return False

    for keyword in transient_keywords:
        if keyword in error_str or keyword in error_type:
            return True

    return False


def get_last_successful_block() -> Optional[int]:
    return _last_successful_block


def reset_last_successful_block() -> None:
    global _last_successful_block
    _last_successful_block = None
