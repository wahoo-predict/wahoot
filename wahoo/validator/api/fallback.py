"""
Fallback logic utilities for Issue #16: Cache check and empty data handling.

This module provides utilities for:
- Checking if validation data is usable (has non-empty metrics)
- Determining if weight computation should be skipped
- Logging empty data scenarios
"""

import logging
from typing import List, Optional

from ..models import ValidationRecord

logger = logging.getLogger(__name__)


def has_usable_metrics(record: ValidationRecord) -> bool:
    """
    Check if a ValidationRecord has usable performance metrics.

    A record is considered usable if it has at least one non-zero metric:
    - total_volume_usd > 0
    - realized_profit_usd is not None
    - trade_count > 0

    Args:
        record: ValidationRecord to check

    Returns:
        bool: True if record has usable metrics, False otherwise
    """
    if not record or not record.performance:
        return False

    perf = record.performance

    # Check if at least one key metric is present and non-zero
    has_volume = perf.total_volume_usd is not None and perf.total_volume_usd > 0
    has_profit = perf.realized_profit_usd is not None
    has_trades = perf.trade_count is not None and perf.trade_count > 0

    return has_volume or has_profit or has_trades


def filter_usable_records(records: List[ValidationRecord]) -> List[ValidationRecord]:
    """
    Filter validation records to only include those with usable metrics.

    Implements Issue #16: Exclude records with empty metrics.

    Args:
        records: List of ValidationRecord objects

    Returns:
        List[ValidationRecord]: Filtered list containing only records with usable metrics
    """
    if not records:
        return []

    usable = [r for r in records if has_usable_metrics(r)]
    excluded = len(records) - len(usable)

    if excluded > 0:
        logger.warning(
            f"Excluded {excluded} validation record(s) with empty metrics "
            f"({len(usable)} usable, {excluded} excluded)"
        )

    return usable


def should_skip_weight_computation(
    validation_data: Optional[List[ValidationRecord]],
    *,
    log_reason: bool = True,
) -> bool:
    """
    Determine if weight computation should be skipped due to empty validation data.

    Implements Issue #16: Skip weight computation if validation_data is empty
    after API + cache fallback.

    Args:
        validation_data: List of ValidationRecord objects (may be None or empty)
        log_reason: If True, log the reason for skipping

    Returns:
        bool: True if weight computation should be skipped, False otherwise
    """
    if not validation_data or len(validation_data) == 0:
        if log_reason:
            logger.warning(
                "No usable validation data available after API + cache fallback. "
                "Skipping weight computation and set_weights() call."
            )
        return True

    # Filter to only usable records
    usable_records = filter_usable_records(validation_data)
    if len(usable_records) == 0:
        if log_reason:
            logger.warning(
                f"All {len(validation_data)} validation record(s) have empty metrics. "
                "Skipping weight computation and set_weights() call."
            )
        return True

    return False


__all__ = [
    "has_usable_metrics",
    "filter_usable_records",
    "should_skip_weight_computation",
]
