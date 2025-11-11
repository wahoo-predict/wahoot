"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Submission routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from wahoopredict.db import get_db
from wahoopredict.schemas import SubmissionRequest, SubmissionResponse
from wahoopredict.services.submissions import create_submission
from wahoopredict.security import verify_hmac_v1

router = APIRouter(prefix="/submit", tags=["submissions"])


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit(
    request: SubmissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a miner prediction.
    
    Args:
        request: Submission request
        db: Database session
        
    Returns:
        Submission response
        
    Raises:
        HTTPException: If submission is invalid, late, or signature is invalid
    """
    # Verify HMAC signature
    if not verify_hmac_v1(request.manifest_hash, request.sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature"
        )
    
    # Create submission
    submission, error = await create_submission(
        db,
        event_id=request.event_id,
        miner_id=request.miner_id,
        prob_yes=request.prob_yes,
        manifest_hash=request.manifest_hash,
        sig=request.sig
    )
    
    if not submission:
        status_code = status.HTTP_400_BAD_REQUEST
        if "locked" in (error or "").lower():
            status_code = status.HTTP_400_BAD_REQUEST
        elif "not found" in (error or "").lower():
            status_code = status.HTTP_404_NOT_FOUND
        
        raise HTTPException(
            status_code=status_code,
            detail=error or "Failed to create submission"
        )
    
    return submission

