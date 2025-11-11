"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Weight persistence and export.
"""

from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from wahoopredict.models import Weight


async def get_current_weights(db: AsyncSession) -> List[Weight]:
    """
    Get current normalized weights, ordered by weight descending.
    
    Args:
        db: Database session
        
    Returns:
        List of weights ordered by weight
    """
    query = select(Weight).order_by(desc(Weight.weight))
    result = await db.execute(query)
    return list(result.scalars().all())


async def export_weights_json(db: AsyncSession) -> Dict[str, Any]:
    """
    Export weights as JSON-serializable dictionary.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with weights list and metadata
    """
    weights = await get_current_weights(db)
    
    return {
        "weights": [
            {"miner_id": w.miner_id, "weight": float(w.weight)}
            for w in weights
        ],
        "updated_at": weights[0].updated_at.isoformat() if weights else datetime.utcnow().isoformat(),
        "sum": sum(float(w.weight) for w in weights)
    }

