"""
WAHOOPREDICT - Validator sync service.

Publish event registry by mirroring WAHOO and stamping with lock_time + resolution rules.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from wahoopredict.models import Event, Resolution
from wahoopredict.services.wahoo_api import fetch_wahoo_events, parse_wahoo_event
from wahoopredict.services.events import get_event


async def sync_event_registry(db: AsyncSession) -> Dict[str, int]:
    """
    Sync event registry from WAHOO API.
    
    Validators publish the event registry by mirroring WAHOO (/event/events-list)
    and stamping each with lock_time + resolution rule/links.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with sync stats
    """
    # Fetch events from WAHOO
    wahoo_events = await fetch_wahoo_events()
    
    stats = {
        "fetched": len(wahoo_events),
        "created": 0,
        "updated": 0,
        "errors": 0
    }
    
    for wahoo_event in wahoo_events:
        try:
            # Parse WAHOO event
            parsed = parse_wahoo_event(wahoo_event)
            event_id = parsed["event_id"]
            
            # Check if event exists
            existing = await get_event(db, event_id)
            
            if existing:
                # Update existing event
                existing.title = parsed["title"]
                existing.lock_time = parsed["lock_time"]
                existing.rule = parsed["rule"]
                if parsed.get("truth_source"):
                    existing.truth_source = parsed["truth_source"]
                stats["updated"] += 1
            else:
                # Create new event
                new_event = Event(
                    event_id=event_id,
                    title=parsed["title"],
                    lock_time=parsed["lock_time"],
                    resolution_type=parsed["resolution_type"],
                    rule=parsed["rule"],
                    truth_source=parsed.get("truth_source")
                )
                db.add(new_event)
                stats["created"] += 1
        except Exception as e:
            print(f"Error syncing event {wahoo_event.get('id', 'unknown')}: {e}")
            stats["errors"] += 1
    
    await db.commit()
    return stats


async def handle_settled_prediction(
    db: AsyncSession,
    market_id: str,
    outcome: bool,
    source: Optional[str] = None
) -> bool:
    """
    Handle settled_prediction postback from WAHOO.
    
    Freeze the book at lock; compute Brier per miner once WAHOO settles the market.
    
    Args:
        db: Database session
        market_id: WAHOO market ID
        outcome: Market outcome (True for YES, False for NO)
        source: Resolution source URL
        
    Returns:
        True if successful
    """
    # Find event by WAHOO market ID
    # In production, store wahoo_market_id in Event model
    event_id = f"wahoo_{market_id}"
    event = await get_event(db, event_id, include_resolution=True)
    
    if not event:
        return False
    
    # Check if already resolved
    if event.resolution:
        return True
    
    # Create resolution
    resolution = Resolution(
        event_id=event_id,
        outcome=outcome,
        source=source or f"https://wahoopredict.com/markets/{market_id}"
    )
    db.add(resolution)
    
    await db.commit()
    
    # Trigger scoring (this should be done by the scoring service)
    # from wahoopredict.services.scoring import update_scores_and_weights
    # await update_scores_and_weights(db)
    
    return True

