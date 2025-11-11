"""
WAHOOPREDICT - WAHOO API integration for miner rankings.

Validators call WAHOO API with list of hotkeys to get miner rankings
based on metrics like volume, profit, etc.
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from wahoopredict.config import settings


async def get_miner_rankings(
    hotkeys: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get miner rankings from WAHOO API.
    
    Validators call this endpoint with a list of hotkeys on the subnet.
    WAHOO returns rankings based on metrics like volume, profit, etc.
    
    Args:
        hotkeys: List of SS58 hotkey addresses
        start_date: Optional start date for time filtering (e.g., past 7 days)
        end_date: Optional end date for time filtering
        metrics: Optional list of metrics to include (e.g., ['volume', 'profit'])
        
    Returns:
        List of miner ranking dictionaries with format:
        [
            {
                "ss58_address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
                "rank": 1,
                "volume": 1000.0,
                "profit": 500.0,
                "metrics": {...}
            },
            ...
        ]
    """
    async with httpx.AsyncClient() as client:
        try:
            # Prepare request payload
            payload = {
                "hotkeys": hotkeys
            }
            
            # Add time filtering if provided
            if start_date:
                payload["start_date"] = start_date.isoformat()
            if end_date:
                payload["end_date"] = end_date.isoformat()
            if metrics:
                payload["metrics"] = metrics
            
            # Call WAHOO API endpoint
            # This endpoint should be provided by WAHOO
            # Example: POST /api/v1/miners/rankings
            response = await client.post(
                f"{settings.wahoo_base_url}/api/v1/miners/rankings",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "rankings" in data:
                return data["rankings"]
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return []
                
        except httpx.HTTPStatusError as e:
            # Log error and return empty list
            print(f"HTTP error fetching miner rankings: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"Error fetching miner rankings: {e}")
            return []


async def get_miner_rankings_past_days(
    hotkeys: List[str],
    days: int = 7,
    metrics: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get miner rankings for the past N days.
    
    Convenience function to get rankings for a specific time period.
    
    Args:
        hotkeys: List of SS58 hotkey addresses
        days: Number of days to look back (default: 7)
        metrics: Optional list of metrics to include
        
    Returns:
        List of miner ranking dictionaries
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    return await get_miner_rankings(
        hotkeys=hotkeys,
        start_date=start_date,
        end_date=end_date,
        metrics=metrics
    )

