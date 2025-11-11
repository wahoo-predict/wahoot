"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Event routes.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from wahoopredict.db import get_db
from wahoopredict.schemas import EventSchema
from wahoopredict.services.events import list_events
from wahoopredict.services.validator_sync import sync_event_registry

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=List[EventSchema])
async def get_events(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List all events.
    
    Returns:
        List of events
    """
    events = await list_events(db, limit=limit, offset=offset)
    return events


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_events(
    db: AsyncSession = Depends(get_db)
):
    """
    Sync event registry from WAHOO API (validator endpoint).
    
    Validators publish the event registry by mirroring WAHOO (/event/events-list)
    and stamping each with lock_time + resolution rule/links.
    """
    stats = await sync_event_registry(db)
    return {
        "status": "success",
        "stats": stats
    }

