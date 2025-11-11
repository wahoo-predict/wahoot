"""
WAHOOPREDICT - Affiliate tracking routes.

Handle clicks, postbacks, and revenue sharing.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from wahoopredict.db import get_db
from wahoopredict.services.affiliate import (
    generate_deeplink,
    track_click,
    handle_postback,
    create_revenue_pool,
    distribute_revenue_pool
)
from wahoopredict.services.validator_sync import handle_settled_prediction

router = APIRouter(prefix="/affiliate", tags=["affiliate"])


@router.get("/deeplink")
async def get_deeplink(
    market_id: str = Query(..., description="WAHOO market ID"),
    affid: str = Query(..., description="Affiliate ID"),
    subid: Optional[str] = Query(None, description="Sub ID (miner ID)")
):
    """
    Generate WAHOO deeplink with affiliate tracking.
    
    Format: https://wahoopredict.com/markets/{MARKET_ID}?utm_source=aff&utm_campaign={AFFID}&utm_content={SUBID}
    """
    deeplink = generate_deeplink(market_id, affid, subid)
    return {"deeplink": deeplink}


@router.post("/click")
async def track_affiliate_click(
    miner_id: str = Query(..., description="Miner ID"),
    market_id: Optional[str] = Query(None, description="WAHOO market ID"),
    affid: str = Query(..., description="Affiliate ID"),
    subid: Optional[str] = Query(None, description="Sub ID"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Track a click to WAHOO via affiliate link.
    """
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    
    click = await track_click(
        db,
        miner_id=miner_id,
        market_id=market_id,
        affid=affid,
        subid=subid,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    await db.commit()
    
    return {
        "click_id": click.id,
        "deeplink": generate_deeplink(market_id or "", affid, subid or miner_id)
    }


@router.post("/postback")
async def receive_postback(
    postback_type: str = Query(..., description="Postback type: signup, first_deposit, first_prediction, settled_prediction"),
    affid: str = Query(..., description="Affiliate ID"),
    subid: Optional[str] = Query(None, description="Sub ID (miner ID)"),
    market_id: Optional[str] = Query(None, description="Market ID"),
    amount: Optional[float] = Query(None, description="Revenue amount"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive S2S postback from WAHOO.
    
    Postback types: signup, first_deposit, first_prediction, settled_prediction
    """
    import json
    
    # Get full payload from request body
    try:
        payload = await request.json() if request else {}
    except:
        payload = {}
    
    # Handle settled_prediction specially
    if postback_type == "settled_prediction":
        # Extract outcome from payload
        outcome = payload.get("outcome") or payload.get("result")
        if outcome is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing outcome in settled_prediction postback"
            )
        
        # Convert outcome to boolean
        if isinstance(outcome, str):
            outcome_bool = outcome.lower() in ("yes", "true", "1", "win")
        else:
            outcome_bool = bool(outcome)
        
        # Handle settlement
        if market_id:
            await handle_settled_prediction(
                db,
                market_id=market_id,
                outcome=outcome_bool,
                source=payload.get("source")
            )
    
    # Record postback
    postback = await handle_postback(
        db,
        postback_type=postback_type,
        affid=affid,
        subid=subid,
        market_id=market_id,
        amount=Decimal(str(amount)) if amount else None,
        payload=payload
    )
    
    await db.commit()
    
    return {
        "postback_id": postback.id,
        "status": "recorded"
    }


@router.post("/revenue-pool")
async def create_weekly_revenue_pool(
    week_start: str = Query(..., description="Week start (ISO format)"),
    week_end: str = Query(..., description="Week end (ISO format)"),
    total_revenue: float = Query(..., description="Total revenue for the week"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new revenue pool for a week.
    
    Distribution: 60% miners, 20% validators, 20% treasury
    """
    from datetime import datetime
    from dateutil.parser import parse as parse_date
    
    week_start_dt = parse_date(week_start)
    week_end_dt = parse_date(week_end)
    
    pool = await create_revenue_pool(
        db,
        week_start=week_start_dt,
        week_end=week_end_dt,
        total_revenue=Decimal(str(total_revenue))
    )
    
    await db.commit()
    
    return {
        "pool_id": pool.id,
        "miners_share": float(pool.miners_share),
        "validators_share": float(pool.validators_share),
        "treasury_share": float(pool.treasury_share)
    }


@router.post("/revenue-pool/{pool_id}/distribute")
async def distribute_pool(
    pool_id: int,
    use_v2_scoring: bool = Query(False, description="Use v2 scoring with usage/referral terms"),
    lambda_usage: float = Query(0.1, description="Weight for usage term"),
    lambda_referrals: float = Query(0.1, description="Weight for referrals term"),
    db: AsyncSession = Depends(get_db)
):
    """
    Distribute revenue pool to miners based on weights.
    
    Optional v2 scoring: score_i = exp(-EMA7_Brier_i) × (1 + λ₁·sqrt(usage_i) + λ₂·EMA7(referrals_i))
    """
    result = await distribute_revenue_pool(
        db,
        pool_id=pool_id,
        use_v2_scoring=use_v2_scoring,
        lambda_usage=lambda_usage,
        lambda_referrals=lambda_referrals
    )
    
    return result

