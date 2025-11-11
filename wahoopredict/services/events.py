"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Event registry and lock checks.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from wahoopredict.models import Event, Resolution


async def get_event(
    db: AsyncSession,
    event_id: str,
    include_resolution: bool = False
) -> Optional[Event]:
    """
    Get event by ID.
    
    Args:
        db: Database session
        event_id: Event ID
        include_resolution: Whether to include resolution
        
    Returns:
        Event or None
    """
    query = select(Event).where(Event.event_id == event_id)
    
    if include_resolution:
        query = query.options(selectinload(Event.resolution))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_events(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> List[Event]:
    """
    List all events.
    
    Args:
        db: Database session
        limit: Maximum number of events to return
        offset: Number of events to skip
        
    Returns:
        List of events
    """
    query = select(Event).order_by(Event.lock_time.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def is_locked(db: AsyncSession, event_id: str, check_time: datetime) -> bool:
    """
    Check if event is locked (past lock_time).
    
    Args:
        db: Database session
        event_id: Event ID
        check_time: Time to check against
        
    Returns:
        True if locked, False otherwise
    """
    event = await get_event(db, event_id)
    if not event:
        return False
    
    return check_time >= event.lock_time


async def get_lock_time(db: AsyncSession, event_id: str) -> Optional[datetime]:
    """
    Get event lock time.
    
    Args:
        db: Database session
        event_id: Event ID
        
    Returns:
        Lock time or None
    """
    event = await get_event(db, event_id)
    return event.lock_time if event else None

