"""
Common validation utilities for API responses and data structures.

This module provides validation functions for:
- WAHOO API response structures
- Validation data records
- Event data structures
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def validate_validation_record(record: Dict[str, Any]) -> bool:
    """
    Validate a single validation data record structure and types.

    Enforces required keys and correct types:
    - hotkey: str (required, non-null) at top level
    - performance: dict (required) containing performance metrics
      - total_volume_usd: numeric (required, can be string or number)
      - realized_profit_usd: numeric (required, can be string or number)
      - win_rate: numeric (optional, 0.0-1.0, can be string or number)
      - Other optional performance fields
    - Optional top-level fields: signature, message, wahoo_user_id

    Supports both nested structure (performance object) and flat structure
    for backward compatibility.

    Args:
        record: Dictionary containing validation data for a single hotkey

    Returns:
        bool: True if record is valid, False otherwise
    """
    if not isinstance(record, dict):
        logger.debug("Record is not a dictionary")
        return False

    # Check required top-level field: hotkey
    if "hotkey" not in record:
        logger.debug("Missing required field: hotkey")
        return False

    hotkey = record["hotkey"]
    if not isinstance(hotkey, str) or len(hotkey.strip()) == 0:
        logger.debug("hotkey is empty or not a string")
        return False

    # Check if record uses nested structure (performance object) or flat structure
    has_performance = "performance" in record and isinstance(record["performance"], dict)
    performance = record.get("performance", {})

    # Performance metrics that can be in nested 'performance' object or at top level
    # Required numeric fields (can be string or number)
    required_numeric_fields = ["total_volume_usd", "realized_profit_usd"]

    # Check required fields - look in performance object first, then top level
    for field_name in required_numeric_fields:
        if has_performance:
            value = performance.get(field_name)
        else:
            value = record.get(field_name)

        if value is None:
            logger.debug(f"Missing required field: {field_name}")
            return False

        # Try to convert to float (handles both string and numeric types)
        try:
            float_value = float(value)
            # Check it's a valid number (not NaN or Inf)
            if not (float_value == float_value):  # NaN check
                logger.debug(f"Field {field_name} is NaN")
                return False
        except (ValueError, TypeError):
            logger.debug(
                f"Field {field_name} cannot be converted to float: {value} (type: {type(value)})"
            )
            return False

    # Optional numeric fields in performance object
    optional_numeric_fields = {
        "unrealized_profit_usd": (int, float, str),
        "win_rate": (int, float, str),
        "total_fees_paid_usd": (int, float, str),
        "referral_volume_usd": (int, float, str),
    }

    for field_name, field_types in optional_numeric_fields.items():
        if has_performance:
            value = performance.get(field_name)
        else:
            value = record.get(field_name)

        if value is None:
            continue

        # Try to convert to float for numeric validation
        try:
            float_value = float(value)
            # Special validation for win_rate (should be 0.0-1.0)
            if field_name == "win_rate":
                if not (0.0 <= float_value <= 1.0):
                    logger.debug(f"win_rate out of range: {float_value}")
                    return False
        except (ValueError, TypeError):
            logger.debug(
                f"Optional numeric field {field_name} cannot be converted to float: {value}"
            )
            return False

    # Optional integer fields in performance object
    optional_int_fields = {
        "trade_count": int,
        "open_positions_count": int,
        "referral_count": int,
    }

    for field_name, field_type in optional_int_fields.items():
        if has_performance:
            value = performance.get(field_name)
        else:
            value = record.get(field_name)

        if value is None:
            continue

        # Allow string or int (API may return strings)
        try:
            int(value)  # Just validate it can be converted
        except (ValueError, TypeError):
            logger.debug(
                f"Optional integer field {field_name} cannot be converted to int: {value}"
            )
            return False

    # Optional string fields at top level
    optional_string_fields = {
        "signature": str,
        "message": str,
        "wahoo_user_id": str,
    }

    for field_name, field_type in optional_string_fields.items():
        if field_name in record:
            value = record[field_name]
            # Allow None for optional fields
            if value is None:
                continue

            # Check type if value is present
            if not isinstance(value, field_type):
                logger.debug(
                    f"Optional field {field_name} has wrong type: "
                    f"{type(value)}, expected {field_type}"
                )
                return False

    # Check last_active_timestamp (can be in performance object or top level)
    last_active_timestamp = None
    if has_performance:
        last_active_timestamp = performance.get("last_active_timestamp")
    if last_active_timestamp is None:
        last_active_timestamp = record.get("last_active_timestamp")

    if last_active_timestamp is not None and not isinstance(last_active_timestamp, str):
        logger.debug(
            f"Optional field last_active_timestamp has wrong type: "
            f"{type(last_active_timestamp)}, expected str"
        )
        return False

    return True


def validate_validation_data_batch(
    data: List[Dict[str, Any]], batch_hotkeys: List[str]
) -> List[Dict[str, Any]]:
    """
    Validate a batch of validation records and return only valid ones.

    Drops entries that fail structural or type checks and logs them.
    If all records for a batch fail validation, logs a warning.

    Args:
        data: List of validation records from API response
        batch_hotkeys: List of hotkeys that were requested (for logging context)

    Returns:
        List[Dict[str, Any]]: List of valid validation records
    """
    if not isinstance(data, list):
        logger.warning("Validation data is not a list")
        return []

    valid_records: List[Dict[str, Any]] = []
    invalid_count = 0

    for record in data:
        if validate_validation_record(record):
            valid_records.append(record)
        else:
            invalid_count += 1
            hotkey = record.get("hotkey", "unknown")
            logger.warning(
                f"Invalid response structure for hotkey {hotkey}. "
                "Dropping record from batch."
            )

    # Log if all records failed validation
    if len(valid_records) == 0 and len(data) > 0:
        logger.warning(
            f"All {len(data)} records in batch failed validation. "
            f"Requested hotkeys: {batch_hotkeys[:5]}..."  # Log first 5 for context
        )

    if invalid_count > 0:
        logger.info(
            f"Validated batch: {len(valid_records)} valid, {invalid_count} invalid "
            f"out of {len(data)} total records"
        )

    return valid_records


def validate_events_response(data: Any) -> Optional[str]:
    """
    Validate /events API response structure and extract active event_id.

    Requires:
    - Response is a dict or list
    - Contains events list or event data
    - Has an event_id for active event

    Args:
        data: Parsed JSON response from /events endpoint

    Returns:
        Optional[str]: Active event_id if found and valid, None otherwise
    """
    if data is None:
        logger.debug("Events response is None")
        return None

    # Handle different response structures
    events_list = None

    if isinstance(data, dict):
        # Check for wrapped response
        if "data" in data and isinstance(data["data"], list):
            events_list = data["data"]
        elif "events" in data and isinstance(data["events"], list):
            events_list = data["events"]
        elif "event_id" in data:
            # Direct event_id in response
            event_id = data.get("event_id")
            if isinstance(event_id, str) and len(event_id.strip()) > 0:
                return event_id.strip()
    elif isinstance(data, list):
        events_list = data

    # If we have an events list, find active event
    if events_list:
        for event in events_list:
            if not isinstance(event, dict):
                continue

            # Check for active event (status or is_active field)
            is_active = event.get("is_active", False) or event.get("status") == "active"

            if is_active and "event_id" in event:
                event_id = event.get("event_id")
                if isinstance(event_id, str) and len(event_id.strip()) > 0:
                    return event_id.strip()

            # If no active flag, check for event_id directly (assume first is active)
            if "event_id" in event and not any(
                e.get("is_active", False) for e in events_list if isinstance(e, dict)
            ):
                event_id = event.get("event_id")
                if isinstance(event_id, str) and len(event_id.strip()) > 0:
                    return event_id.strip()

    logger.debug("No valid active event_id found in events response")
    return None
