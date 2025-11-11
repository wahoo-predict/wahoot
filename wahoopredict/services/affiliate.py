"""
WAHOOPREDICT - Affiliate tracking and revenue sharing.

Track clicks, postbacks, and distribute revenue share.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from decimal import Decimal

from wahoopredict.models import (
    AffiliateClick,
    AffiliatePostback,
    MinerUsage,
    RevenuePool,
    MinerRevenueShare,
    MinerStats,
    Weight
)


def generate_deeplink(market_id: str, affid: str, subid: Optional[str] = None) -> str:
    """
    Generate WAHOO deeplink with affiliate tracking.
    
    Format: https://wahoopredict.com/markets/{MARKET_ID}?utm_source=aff&utm_campaign={AFFID}&utm_content={SUBID}
    
    Args:
        market_id: WAHOO market ID
        affid: Affiliate ID
        subid: Sub ID (miner-specific, optional)
        
    Returns:
        Deeplink URL
    """
    base_url = f"https://wahoopredict.com/markets/{market_id}"
    params = f"utm_source=aff&utm_campaign={affid}"
    if subid:
        params += f"&utm_content={subid}"
    return f"{base_url}?{params}"


async def track_click(
    db: AsyncSession,
    miner_id: str,
    market_id: Optional[str],
    affid: str,
    subid: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AffiliateClick:
    """
    Track a click to WAHOO via affiliate link.
    
    Args:
        db: Database session
        miner_id: Miner ID
        market_id: WAHOO market ID
        affid: Affiliate ID
        subid: Sub ID
        ip_address: IP address
        user_agent: User agent string
        
    Returns:
        AffiliateClick record
    """
    click = AffiliateClick(
        miner_id=miner_id,
        market_id=market_id,
        affid=affid,
        subid=subid or miner_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(click)
    
    # Update miner usage stats
    usage = await db.get(MinerUsage, miner_id)
    if not usage:
        usage = MinerUsage(miner_id=miner_id)
        db.add(usage)
    
    # Check if unique click (by IP + user agent hash)
    # Simplified: just increment total for now
    usage.total_clicks += 1
    # In production, track unique clicks more carefully
    
    await db.flush()
    return click


async def handle_postback(
    db: AsyncSession,
    postback_type: str,
    affid: str,
    subid: Optional[str],
    market_id: Optional[str],
    amount: Optional[Decimal],
    payload: Dict[str, Any]
) -> AffiliatePostback:
    """
    Handle S2S postback from WAHOO.
    
    Postback types: signup, first_deposit, first_prediction, settled_prediction
    
    Args:
        db: Database session
        postback_type: Type of postback
        affid: Affiliate ID
        subid: Sub ID (miner ID)
        market_id: Market ID
        amount: Revenue amount
        payload: Full postback payload
        
    Returns:
        AffiliatePostback record
    """
    postback = AffiliatePostback(
        postback_type=postback_type,
        affid=affid,
        subid=subid,
        market_id=market_id,
        amount=amount,
        payload=payload
    )
    db.add(postback)
    
    # Update miner usage stats
    if subid:
        usage = await db.get(MinerUsage, subid)
        if not usage:
            usage = MinerUsage(miner_id=subid)
            db.add(usage)
        
        # Track referrals (qualified first deposits)
        if postback_type == "first_deposit" and amount and amount > 0:
            usage.referrals += 1
        
        await db.flush()
    
    await db.flush()
    return postback


async def create_revenue_pool(
    db: AsyncSession,
    week_start: datetime,
    week_end: datetime,
    total_revenue: Decimal
) -> RevenuePool:
    """
    Create a new revenue pool for a week.
    
    Args:
        db: Database session
        week_start: Week start datetime
        week_end: Week end datetime
        total_revenue: Total revenue for the week
        
    Returns:
        RevenuePool record
    """
    pool = RevenuePool(
        week_start=week_start,
        week_end=week_end,
        total_revenue=total_revenue,
        miners_share=total_revenue * Decimal("0.60"),  # 60%
        validators_share=total_revenue * Decimal("0.20"),  # 20%
        treasury_share=total_revenue * Decimal("0.20")  # 20%
    )
    db.add(pool)
    await db.flush()
    return pool


async def distribute_revenue_pool(
    db: AsyncSession,
    pool_id: int,
    use_v2_scoring: bool = False,
    lambda_usage: float = 0.1,
    lambda_referrals: float = 0.1
) -> Dict[str, int]:
    """
    Distribute revenue pool to miners based on weights.
    
    Args:
        db: Database session
        pool_id: Revenue pool ID
        use_v2_scoring: Whether to use v2 scoring with usage/referral terms
        lambda_usage: Weight for usage term (default 0.1)
        lambda_referrals: Weight for referrals term (default 0.1)
        
    Returns:
        Dictionary with distribution stats
    """
    pool = await db.get(RevenuePool, pool_id)
    if not pool or pool.distributed:
        return {"error": "Pool not found or already distributed"}
    
    # Get all miner weights
    weights_result = await db.execute(select(Weight))
    weights = {w.miner_id: w.weight for w in weights_result.scalars().all()}
    
    if not weights:
        return {"error": "No weights found"}
    
    # Apply v2 scoring if enabled
    if use_v2_scoring:
        # Get usage stats
        usage_result = await db.execute(select(MinerUsage))
        usage_stats = {u.miner_id: u for u in usage_result.scalars().all()}
        
        # Compute v2 scores
        v2_scores = {}
        for miner_id, base_weight in weights.items():
            usage = usage_stats.get(miner_id)
            if usage:
                # score_i = exp(-EMA7_Brier_i) × (1 + λ₁·sqrt(usage_i) + λ₂·EMA7(referrals_i))
                usage_term = lambda_usage * (usage.unique_clicks ** 0.5) if usage.unique_clicks > 0 else 0
                referral_term = lambda_referrals * usage.referrals if usage.referrals > 0 else 0
                v2_scores[miner_id] = base_weight * (1.0 + usage_term + referral_term)
            else:
                v2_scores[miner_id] = base_weight
        
        # Renormalize
        total_v2 = sum(v2_scores.values())
        if total_v2 > 0:
            weights = {mid: w / total_v2 for mid, w in v2_scores.items()}
    
    # Distribute miners' share (60%)
    total_weight = sum(weights.values())
    if total_weight > 0:
        for miner_id, weight in weights.items():
            amount = pool.miners_share * Decimal(str(weight / total_weight))
            share = MinerRevenueShare(
                pool_id=pool_id,
                miner_id=miner_id,
                weight=weight,
                amount=amount
            )
            db.add(share)
    
    # Mark pool as distributed
    pool.distributed = True
    pool.distributed_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "pool_id": pool_id,
        "miners_count": len(weights),
        "total_distributed": float(pool.miners_share)
    }

