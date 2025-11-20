"""
Mock data utilities for testing the validator without real WAHOO API or miners.

This module provides functions to generate mock validation data and miner responses
for localnet testing. The mock data format matches the real WAHOO API response format.
"""

from typing import List, Dict, Any
import random
from .models import ValidationRecord, PerformanceMetrics


def generate_mock_validation_record(hotkey: str, **kwargs) -> ValidationRecord:
    """
    Generate a mock ValidationRecord for testing.
    
    Matches the real WAHOO API response format:
    {
        "hotkey": "5Dnh2o9x9kTRtfeF5g3W4uzfzWNeGD1EJo4aCtibAESzP2iE",
        "signature": "673PvPKoEEgmnnrH-5p6V",
        "message": "message with v1SKb_5YKRZ2C9iZIbRl0",
        "performance": {
            "total_volume_usd": "17581.69866",  # String in API
            "realized_profit_usd": "-1517.98587",  # String, can be negative
            "unrealized_profit_usd": 0,  # Number
            "trade_count": 781,  # Number
            "open_positions_count": 0  # Number
            # Optional: win_rate, total_fees_paid_usd, referral_count, etc.
        }
    }
    
    Args:
        hotkey: Miner hotkey
        **kwargs: Override default values:
            - total_volume_usd: Trading volume
            - realized_profit_usd: Realized profit (can be negative)
            - unrealized_profit_usd: Unrealized profit (can be negative)
            - trade_count: Number of trades
            - open_positions_count: Number of open positions
            - signature: Optional signature
            - message: Optional message
    
    Returns:
        ValidationRecord with mock data matching API format
    """
    defaults = {
        "total_volume_usd": random.uniform(100.0, 20000.0),
        "realized_profit_usd": random.uniform(-2000.0, 2000.0),
        "unrealized_profit_usd": random.uniform(-100.0, 800.0),
        "trade_count": random.randint(10, 800),
        "open_positions_count": random.randint(0, 50),
        # Optional fields (may not be in all API responses)
        "win_rate": random.uniform(0.3, 0.8) if random.random() > 0.3 else None,
        "total_fees_paid_usd": random.uniform(1.0, 50.0) if random.random() > 0.5 else None,
        "referral_count": random.randint(0, 20) if random.random() > 0.7 else None,
        "referral_volume_usd": random.uniform(0.0, 5000.0) if random.random() > 0.7 else None,
    }
    
    # Override with provided kwargs
    defaults.update(kwargs)
    
    performance = PerformanceMetrics(**defaults)
    
    # Generate signature and message like real API (if not provided)
    signature = kwargs.get("signature")
    if signature is None:
        signature = f"{random.randint(1000, 9999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(10, 99)}"
    
    message = kwargs.get("message")
    if message is None:
        message = f"message with {''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))}"
    
    return ValidationRecord(
        hotkey=hotkey,
        signature=signature,
        message=message,
        performance=performance,
        wahoo_user_id=f"user_{hotkey[:8]}" if random.random() > 0.3 else None,
    )


def generate_mock_validation_data(hotkeys: List[str]) -> List[ValidationRecord]:
    """
    Generate mock validation data for a list of hotkeys.
    
    This simulates what the WAHOO API returns for multiple hotkeys.
    
    Args:
        hotkeys: List of miner hotkeys
    
    Returns:
        List of ValidationRecord objects matching API format
    """
    return [generate_mock_validation_record(hk) for hk in hotkeys]


def create_mock_miner_responses(
    active_uids: List[int],
    event_id: str = "wahoo_test_event",
) -> List[Dict[str, Any]]:
    """
    Create mock miner responses for testing.
    
    This simulates what miners would return via dendrite queries.
    In reality, miners use the WAHOO Predict platform and don't need
    a separate script.
    
    Args:
        active_uids: List of active miner UIDs
        event_id: Event ID to respond about
    
    Returns:
        List of mock response dictionaries (can be converted to WAHOOPredict synapses)
    """
    responses = []
    
    for uid in active_uids:
        # Generate random but valid probabilities
        prob_yes = random.uniform(0.0, 1.0)
        prob_no = 1.0 - prob_yes
        confidence = random.uniform(0.5, 1.0)
        
        responses.append({
            "uid": uid,
            "event_id": event_id,
            "prob_yes": prob_yes,
            "prob_no": prob_no,
            "confidence": confidence,
            "protocol_version": "1.0",
        })
    
    return responses


def create_real_api_format_example() -> List[Dict[str, Any]]:
    """
    Create example data in the exact format returned by WAHOO API.
    
    This matches the real API response structure for testing/validation.
    
    Returns:
        List of dictionaries matching real API format
    """
    return [
        {
            "hotkey": "5Dnh2o9x9kTRtfeF5g3W4uzfzWNeGD1EJo4aCtibAESzP2iE",
            "signature": "673PvPKoEEgmnnrH-5p6V",
            "message": "message with v1SKb_5YKRZ2C9iZIbRl0",
            "performance": {
                "total_volume_usd": "17581.69866",
                "realized_profit_usd": "-1517.98587",
                "unrealized_profit_usd": 0,
                "trade_count": 781,
                "open_positions_count": 0
            }
        },
        {
            "hotkey": "5FddqPQUhEFeLqVNbenAj6EDRKuqgezciN9TmTgBmNABsj53",
            "signature": "9V49ry12SIPB7YST9KJve",
            "message": "message with _P5uUPdqRmykHuONuKesK",
            "performance": {
                "total_volume_usd": "7917.93311",
                "realized_profit_usd": "28.70325",
                "unrealized_profit_usd": 760.3283832764167,
                "trade_count": 30,
                "open_positions_count": 12
            }
        },
    ]
