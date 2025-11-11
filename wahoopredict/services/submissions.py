"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Submission creation, deduplication, and late-rejection.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from wahoopredict.models import Submission, SubmissionAlert, Event
from wahoopredict.services.events import get_lock_time, is_locked
from wahoopredict.utils import now_utc


async def create_submission(
    db: AsyncSession,
    event_id: str,
    miner_id: str,
    prob_yes: float,
    manifest_hash: str,
    sig: str,
    submitted_at: Optional[datetime] = None
) -> tuple[Optional[Submission], Optional[str]]:
    """
    Create a new submission.
    
    Args:
        db: Database session
        event_id: Event ID
        miner_id: Miner ID
        prob_yes: Probability of YES (0.0-1.0)
        manifest_hash: Manifest hash
        sig: HMAC signature
        submitted_at: Submission timestamp (defaults to now)
        
    Returns:
        Tuple of (Submission or None, error message or None)
    """
    submitted_at = submitted_at or now_utc()
    
    # Check if event exists
    event = await db.get(Event, event_id)
    if not event:
        return None, "Event not found"
    
    # Check if locked
    if await is_locked(db, event_id, submitted_at):
        return None, "Event is locked (submission at/after lock_time)"
    
    # Check for duplicate manifest_hash
    existing = await db.execute(
        select(Submission).where(
            and_(
                Submission.event_id == event_id,
                Submission.manifest_hash == manifest_hash
            )
        )
    )
    if existing.scalar_one_or_none():
        # Create alert for duplicate
        alert = SubmissionAlert(
            event_id=event_id,
            miner_id=miner_id,
            reason="dup_manifest"
        )
        db.add(alert)
        await db.commit()
        return None, "Duplicate manifest_hash (replay detected)"
    
    # Create submission
    submission = Submission(
        event_id=event_id,
        miner_id=miner_id,
        submitted_at=submitted_at,
        prob_yes=prob_yes,
        manifest_hash=manifest_hash,
        sig=sig
    )
    
    try:
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        return submission, None
    except IntegrityError as e:
        await db.rollback()
        return None, f"Database error: {str(e)}"


async def get_last_prelock_submission(
    db: AsyncSession,
    event_id: str,
    miner_id: str
) -> Optional[Submission]:
    """
    Get the last submission before lock_time for a given (event, miner).
    
    Args:
        db: Database session
        event_id: Event ID
        miner_id: Miner ID
        
    Returns:
        Last pre-lock submission or None
    """
    # Get event lock time
    event = await db.get(Event, event_id)
    if not event:
        return None
    
    # Get last submission before lock_time
    query = select(Submission).where(
        and_(
            Submission.event_id == event_id,
            Submission.miner_id == miner_id,
            Submission.submitted_at < event.lock_time
        )
    ).order_by(Submission.submitted_at.desc()).limit(1)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()

