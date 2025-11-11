"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Public routes: aggregated odds and weights.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from wahoopredict.db import get_db
from wahoopredict.schemas import AggregatedOddsResponse, WeightsResponse, WeightItem
from wahoopredict.models import Event, Submission
from wahoopredict.services.weights import get_current_weights, export_weights_json
from wahoopredict.utils import now_utc

router = APIRouter(prefix="", tags=["public"])


@router.get("/agg_odds", response_model=AggregatedOddsResponse)
async def get_aggregated_odds(
    event_id: str = Query(..., description="Event ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated odds for an event.
    
    Returns mean of miners' last pre-lock prob_yes + count.
    
    Args:
        event_id: Event ID
        db: Database session
        
    Returns:
        Aggregated odds response
        
    Raises:
        HTTPException: If event not found
    """
    # Get event
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get last pre-lock submissions for all miners
    # This is a simplified query - in production, use the latest_prelock service
    query = select(
        func.avg(Submission.prob_yes).label("mean_prob_yes"),
        func.count(Submission.submission_id).label("miners_count")
    ).where(
        and_(
            Submission.event_id == event_id,
            Submission.submitted_at < event.lock_time
        )
    ).group_by(Submission.event_id)
    
    result = await db.execute(query)
    row = result.first()
    
    if not row or row.miners_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submissions found for this event"
        )
    
    return AggregatedOddsResponse(
        event_id=event_id,
        mean_prob_yes=float(row.mean_prob_yes),
        miners_count=int(row.miners_count),
        computed_at=now_utc()
    )


@router.get("/weights", response_model=WeightsResponse)
async def get_weights(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current normalized weights + timestamp.
    
    Args:
        db: Database session
        
    Returns:
        Weights response
    """
    weights_data = await export_weights_json(db)
    
    return WeightsResponse(
        weights=[WeightItem(**w) for w in weights_data["weights"]],
        updated_at=datetime.fromisoformat(weights_data["updated_at"]),
        sum=weights_data["sum"]
    )

