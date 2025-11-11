"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Brier scoring, EMA(7d), and weight normalization.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
import numpy as np

from wahoopredict.models import (
    Event,
    Resolution,
    Submission,
    BrierArchive,
    MinerStats,
    Weight,
    Miner
)
from wahoopredict.services.submissions import get_last_prelock_submission


# EMA alpha for 7-day window: alpha = 2/(7+1) = 0.25
EMA_ALPHA = 2.0 / (7.0 + 1.0)


def compute_brier(prob_yes: float, outcome: bool) -> float:
    """
    Compute Brier score: (prob_yes - outcome)^2.
    
    Args:
        prob_yes: Probability of YES (0.0-1.0)
        outcome: True for YES, False for NO
        
    Returns:
        Brier score
    """
    outcome_value = 1.0 if outcome else 0.0
    return (prob_yes - outcome_value) ** 2


async def latest_prelock(
    db: AsyncSession,
    event_id: str
) -> List[Submission]:
    """
    Get latest pre-lock submissions for all miners for an event.
    
    Args:
        db: Database session
        event_id: Event ID
        
    Returns:
        List of last pre-lock submissions per miner
    """
    # Get all miners
    miners_result = await db.execute(select(Miner))
    miners = list(miners_result.scalars().all())
    
    # Get last pre-lock submission for each miner
    submissions = []
    for miner in miners:
        submission = await get_last_prelock_submission(db, event_id, miner.miner_id)
        if submission:
            submissions.append(submission)
    
    return submissions


async def update_scores_and_weights(db: AsyncSession) -> Dict[str, int]:
    """
    Compute Brier scores for newly-resolved events, update EMA(7d), and recalculate weights.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with counts of processed events, miners, etc.
    """
    # Get all resolved events that haven't been scored yet
    # (events with resolutions but no brier_archive entries)
    query = select(Event).join(Resolution).where(
        ~select(1).where(
            BrierArchive.event_id == Event.event_id
        ).exists()
    ).options(selectinload(Event.resolution))
    
    result = await db.execute(query)
    resolved_events = list(result.scalars().all())
    
    stats = {
        "events_processed": 0,
        "miners_scored": 0,
        "weights_updated": 0
    }
    
    for event in resolved_events:
        if not event.resolution:
            continue
        
        # Get latest pre-lock submissions for all miners
        submissions = await latest_prelock(db, event.event_id)
        
        for submission in submissions:
            # Compute Brier score
            brier = compute_brier(float(submission.prob_yes), event.resolution.outcome)
            
            # Archive Brier score
            archive = BrierArchive(
                event_id=event.event_id,
                miner_id=submission.miner_id,
                brier=brier,
                computed_at=datetime.now(timezone.utc)
            )
            db.add(archive)
            
            # Update miner stats (EMA)
            await update_miner_ema(db, submission.miner_id, brier)
            stats["miners_scored"] += 1
        
        stats["events_processed"] += 1
    
    # Recalculate all weights
    await normalize_weights(db)
    
    # Count updated weights
    weights_result = await db.execute(select(Weight))
    stats["weights_updated"] = len(list(weights_result.scalars().all()))
    
    await db.commit()
    return stats


async def update_miner_ema(db: AsyncSession, miner_id: str, new_brier: float) -> None:
    """
    Update miner EMA(7d) Brier score.
    
    Args:
        db: Database session
        miner_id: Miner ID
        new_brier: New Brier score to incorporate
    """
    # Get current stats
    stats = await db.get(MinerStats, miner_id)
    
    if not stats or stats.ema_brier is None:
        # No prior EMA, set to current Brier
        if not stats:
            stats = MinerStats(miner_id=miner_id, ema_brier=new_brier)
            db.add(stats)
        else:
            stats.ema_brier = new_brier
    else:
        # Update EMA: EMA_new = alpha * new_value + (1 - alpha) * EMA_old
        stats.ema_brier = EMA_ALPHA * new_brier + (1.0 - EMA_ALPHA) * stats.ema_brier
    
    stats.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def normalize_weights(
    db: AsyncSession,
    use_v2_scoring: bool = False,
    lambda_usage: float = 0.1,
    lambda_referrals: float = 0.1
) -> None:
    """
    Compute and upsert normalized weights for all miners.
    
    Weights: raw = exp(-ema_brier), normalized to sum=1.0
    Miners without EMA get weight = 0.
    
    Optional v2 scoring: score_i = exp(-EMA7_Brier_i) × (1 + λ₁·sqrt(usage_i) + λ₂·EMA7(referrals_i))
    
    Args:
        db: Database session
        use_v2_scoring: Whether to use v2 scoring with usage/referral terms
        lambda_usage: Weight for usage term (default 0.1)
        lambda_referrals: Weight for referrals term (default 0.1)
    """
    # Get all miner stats
    stats_result = await db.execute(select(MinerStats))
    all_stats = list(stats_result.scalars().all())
    
    # Compute raw weights
    raw_weights: Dict[str, float] = {}
    for stat in all_stats:
        if stat.ema_brier is not None:
            raw_weights[stat.miner_id] = np.exp(-stat.ema_brier)
        else:
            raw_weights[stat.miner_id] = 0.0
    
    # Apply v2 scoring if enabled
    if use_v2_scoring:
        from wahoopredict.models import MinerUsage
        
        # Get usage stats
        usage_result = await db.execute(select(MinerUsage))
        usage_stats = {u.miner_id: u for u in usage_result.scalars().all()}
        
        # Compute v2 scores
        v2_scores = {}
        for miner_id, base_weight in raw_weights.items():
            usage = usage_stats.get(miner_id)
            if usage and base_weight > 0:
                # score_i = exp(-EMA7_Brier_i) × (1 + λ₁·sqrt(usage_i) + λ₂·EMA7(referrals_i))
                usage_term = lambda_usage * np.sqrt(usage.unique_clicks) if usage.unique_clicks > 0 else 0
                referral_term = lambda_referrals * usage.referrals if usage.referrals > 0 else 0
                v2_scores[miner_id] = base_weight * (1.0 + usage_term + referral_term)
            else:
                v2_scores[miner_id] = base_weight
        
        raw_weights = v2_scores
    
    # Normalize to sum=1.0
    total = sum(raw_weights.values())
    if total > 0:
        normalized = {mid: w / total for mid, w in raw_weights.items()}
    else:
        normalized = {mid: 0.0 for mid in raw_weights.keys()}
    
    # Upsert weights
    for miner_id, weight in normalized.items():
        weight_obj = await db.get(Weight, miner_id)
        if not weight_obj:
            weight_obj = Weight(miner_id=miner_id, weight=weight)
            db.add(weight_obj)
        else:
            weight_obj.weight = weight
            weight_obj.updated_at = datetime.now(timezone.utc)
    
    await db.flush()

