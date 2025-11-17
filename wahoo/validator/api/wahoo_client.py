"""
WAHOO API client for validator operations.

This module handles all HTTP communication with the WAHOO Predict API.
Based on the WAHOO API documentation and actual endpoint structure.
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# API Configuration
DEFAULT_API_BASE_URL = "https://api.wahoopredict.com"
DEFAULT_TIMEOUT = 30.0
MAX_HOTKEYS_PER_REQUEST = 256


def get_wahoo_validation_data(
    hotkeys: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """
    Fetch validation data from WAHOO API for a list of hotkeys.

    This function implements the main data retrieval from the WAHOO API as specified
    in the validator flowchart. It batches hotkeys (max 246 per request) and handles
    API responses with proper error handling and caching fallback support.

    API Endpoint: GET /api/v2/event/bittensor/statistics

    Note: This is the actual endpoint implemented by WAHOO Predict team.
    The spec document referenced /api/v2/users/validation, but the actual
    endpoint is /api/v2/event/bittensor/statistics.

    Args:
        hotkeys: List of hotkey strings to query
        start_date: Optional start date for statistics (ISO 8601 format)
        end_date: Optional end date for statistics (ISO 8601 format)
        api_base_url: Base URL for WAHOO API (default: https://api.wahoopredict.com)
        timeout: Request timeout in seconds (default: 30.0)

    Returns:
        List[Dict[str, Any]]: List of validation data dictionaries, each containing:
            - hotkey: str
            - signature: str (optional)
            - message: str (optional)
            - total_volume_usd: float
            - realized_profit_usd: float
            - unrealized_profit_usd: float
            - win_rate: float
            - trade_count: int
            - open_positions_count: int
            - total_fees_paid_usd: float
            - last_active_timestamp: str (ISO 8601, optional)
            - referral_count: int
            - referral_volume_usd: float
            - wahoo_user_id: str (optional)

        Empty list if API call fails (caller should handle cache fallback)

    Note: Response structure matches WAHOO API spec:
        {"status": "success", "data": [...]} or direct array (backward compatibility)
    """
    if not hotkeys:
        return []

    # Batch hotkeys into chunks of max_per_request
    all_results: List[Dict[str, Any]] = []

    for i in range(0, len(hotkeys), MAX_HOTKEYS_PER_REQUEST):
        batch = hotkeys[i : i + MAX_HOTKEYS_PER_REQUEST]

        try:
            # Build query parameters
            params: Dict[str, Any] = {
                "hotkeys": ",".join(batch),
            }

            # Add optional date parameters if provided
            if start_date:
                # Convert to ISO 8601 format if datetime object
                if isinstance(start_date, datetime):
                    params["start_date"] = start_date.isoformat()
                else:
                    params["start_date"] = str(start_date)

            if end_date:
                if isinstance(end_date, datetime):
                    params["end_date"] = end_date.isoformat()
                else:
                    params["end_date"] = str(end_date)

            # Make HTTP request
            url = f"{api_base_url}/api/v2/event/bittensor/statistics"

            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()  # Raises exception for 4xx/5xx status

            # Parse JSON response
            response_data = response.json()

            # Handle wrapped response structure: {"status": "success", "data": [...]}
            # or direct array response (for backward compatibility)
            if isinstance(response_data, dict):
                if response_data.get("status") != "success":
                    logger.warning(
                        f"API returned non-success status: {response_data.get('status')}"
                    )
                    continue
                data = response_data.get("data", [])
            elif isinstance(response_data, list):
                # Direct array response (backward compatibility)
                data = response_data
            else:
                logger.warning(
                    f"Invalid API response structure: expected dict or list, got {type(response_data)}"
                )
                continue

            # Process each item in response
            for item in data:
                if not isinstance(item, dict):
                    continue

                hotkey = item.get("hotkey")
                if not hotkey:
                    continue

                # Check if performance data exists
                performance = item.get("performance")
                if not performance or not isinstance(performance, dict):
                    # No performance data for this hotkey (e.g., fakeadresstotest)
                    # Return minimal entry with zero values
                    all_results.append(
                        {
                            "hotkey": hotkey,
                            "signature": item.get("signature"),
                            "message": item.get("message"),
                            "total_volume_usd": 0.0,
                            "realized_profit_usd": 0.0,
                            "unrealized_profit_usd": 0.0,
                            "win_rate": 0.0,
                            "trade_count": 0,
                            "open_positions_count": 0,
                            "total_fees_paid_usd": 0.0,
                            "last_active_timestamp": None,
                            "referral_count": 0,
                            "referral_volume_usd": 0.0,
                            "wahoo_user_id": item.get("wahoo_user_id"),
                        }
                    )
                    continue

                # Extract and convert performance metrics
                try:
                    total_volume_usd = float(performance.get("total_volume_usd", 0))
                    realized_profit_usd = float(
                        performance.get("realized_profit_usd", 0)
                    )
                    unrealized_profit_usd = float(
                        performance.get("unrealized_profit_usd", 0)
                    )
                    trade_count = int(performance.get("trade_count", 0))
                    open_positions_count = int(
                        performance.get("open_positions_count", 0)
                    )
                    win_rate = float(performance.get("win_rate", 0.0))
                    total_fees_paid_usd = float(
                        performance.get("total_fees_paid_usd", 0)
                    )
                    last_active_timestamp = performance.get("last_active_timestamp")
                    referral_count = int(performance.get("referral_count", 0))
                    referral_volume_usd = float(
                        performance.get("referral_volume_usd", 0)
                    )

                    all_results.append(
                        {
                            "hotkey": hotkey,
                            "signature": item.get("signature"),
                            "message": item.get("message"),
                            "total_volume_usd": total_volume_usd,
                            "realized_profit_usd": realized_profit_usd,
                            "unrealized_profit_usd": unrealized_profit_usd,
                            "win_rate": win_rate,
                            "trade_count": trade_count,
                            "open_positions_count": open_positions_count,
                            "total_fees_paid_usd": total_fees_paid_usd,
                            "last_active_timestamp": last_active_timestamp,
                            "referral_count": referral_count,
                            "referral_volume_usd": referral_volume_usd,
                            "wahoo_user_id": item.get("wahoo_user_id"),
                        }
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Error parsing performance data for hotkey {hotkey}: {e}"
                    )
                    # Return entry with zero values on parse error
                    all_results.append(
                        {
                            "hotkey": hotkey,
                            "signature": item.get("signature"),
                            "message": item.get("message"),
                            "total_volume_usd": 0.0,
                            "realized_profit_usd": 0.0,
                            "unrealized_profit_usd": 0.0,
                            "win_rate": 0.0,
                            "trade_count": 0,
                            "open_positions_count": 0,
                            "total_fees_paid_usd": 0.0,
                            "last_active_timestamp": None,
                            "referral_count": 0,
                            "referral_volume_usd": 0.0,
                            "wahoo_user_id": item.get("wahoo_user_id"),
                        }
                    )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching WAHOO validation data: {e.response.status_code} - {e.response.text}"
            )
            # Continue to next batch, caller should handle cache fallback
            continue
        except httpx.RequestError as e:
            logger.error(f"Request error fetching WAHOO validation data: {e}")
            # Continue to next batch, caller should handle cache fallback
            continue
        except Exception as e:
            logger.error(f"Unexpected error fetching WAHOO validation data: {e}")
            continue

    return all_results


def get_active_event_id(
    api_base_url: str = DEFAULT_API_BASE_URL, timeout: float = 10.0
) -> str:
    """
    Get the active event ID from WAHOO API.

    This function retrieves the currently active event ID that validators should
    query miners about. Falls back to a default value if API call fails.

    Args:
        api_base_url: Base URL for WAHOO API
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        str: Active event ID, or 'wahoo_test_event' as fallback
    """
    try:
        # TODO: Determine the correct endpoint for active events
        # This might be GET /events or similar
        # For now, return default as specified in flowchart
        url = f"{api_base_url}/events"

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            # TODO: Parse response to extract active event_id
            # This will depend on the actual API response structure
            # data = response.json()  # Uncomment when parsing is implemented
            event_id = "wahoo_test_event"  # Placeholder

            return event_id

    except Exception as e:
        logger.warning(f"Failed to get active event ID from API: {e}")
        # Fallback to default as specified in flowchart
        return "wahoo_test_event"
