"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Health check routes.
"""

from fastapi import APIRouter
from wahoopredict.schemas import HealthResponse

router = APIRouter(prefix="", tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(status="OK")

