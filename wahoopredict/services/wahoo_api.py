"""
WAHOOPREDICT - WAHOO API integration.

Pull live markets from WAHOO's API (events list → event details).
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dateutil.parser import parse as parse_date

from wahoopredict.config import settings


async def fetch_wahoo_events() -> List[Dict[str, Any]]:
    """
    Fetch events list from WAHOO API.
    
    Returns:
        List of event dictionaries
    """
    async with httpx.AsyncClient() as client:
        try:
            # Fetch events list from WAHOO API
            # Adjust endpoint based on actual WAHOO API structure
            response = await client.get(
                f"{settings.wahoo_base_url}/events",
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "events" in data:
                return data["events"]
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return []
        except Exception as e:
            # Log error and return empty list
            print(f"Error fetching WAHOO events: {e}")
            return []


async def fetch_wahoo_event_details(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed event information from WAHOO API.
    
    Args:
        event_id: WAHOO event ID
        
    Returns:
        Event details dictionary or None
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.wahoo_base_url}/events/{event_id}",
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching WAHOO event {event_id}: {e}")
            return None


def parse_wahoo_event(wahoo_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse WAHOO event format to our Event model format.
    
    Args:
        wahoo_event: Raw WAHOO event dictionary
        
    Returns:
        Parsed event dictionary
    """
    # Extract event ID
    event_id = str(wahoo_event.get("id") or wahoo_event.get("event_id") or wahoo_event.get("market_id", ""))
    
    # Extract title
    title = wahoo_event.get("title") or wahoo_event.get("name") or wahoo_event.get("question", "")
    
    # Extract lock time
    lock_time_str = (
        wahoo_event.get("lock_time") or 
        wahoo_event.get("lockTime") or 
        wahoo_event.get("deadline") or
        wahoo_event.get("end_time") or
        wahoo_event.get("endTime")
    )
    
    lock_time = None
    if lock_time_str:
        try:
            lock_time = parse_date(lock_time_str)
            if lock_time.tzinfo is None:
                lock_time = lock_time.replace(tzinfo=timezone.utc)
        except:
            pass
    
    if not lock_time:
        lock_time = datetime.now(timezone.utc)
    
    # Extract rule/description
    rule = (
        wahoo_event.get("rule") or 
        wahoo_event.get("description") or 
        wahoo_event.get("resolution_criteria") or
        "WAHOOPREDICT event"
    )
    
    # Extract resolution links
    truth_source = []
    if wahoo_event.get("resolution_url"):
        truth_source.append(wahoo_event["resolution_url"])
    if wahoo_event.get("source_url"):
        truth_source.append(wahoo_event["source_url"])
    
    return {
        "event_id": f"wahoo_{event_id}",
        "title": title,
        "lock_time": lock_time,
        "resolution_type": "binary",
        "rule": rule,
        "truth_source": truth_source if truth_source else None,
        "wahoo_market_id": event_id,  # Store original WAHOO ID
        "raw_data": wahoo_event  # Store raw data for reference
    }

