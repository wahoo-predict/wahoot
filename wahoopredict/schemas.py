"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class EventSchema(BaseModel):
    """Event schema for API responses."""
    
    event_id: str
    title: str
    lock_time: datetime
    resolution_type: str = "binary"
    truth_source: Optional[List[str]] = None
    rule: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubmissionRequest(BaseModel):
    """Miner submission request."""
    
    event_id: str
    miner_id: str
    prob_yes: float = Field(..., ge=0.0, le=1.0)
    manifest_hash: str
    sig: str
    
    @field_validator("prob_yes")
    @classmethod
    def validate_prob_yes(cls, v: float) -> float:
        """Validate probability is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("prob_yes must be between 0.0 and 1.0")
        return v


class SubmissionResponse(BaseModel):
    """Submission response."""
    
    submission_id: int
    event_id: str
    miner_id: str
    submitted_at: datetime
    prob_yes: float
    
    class Config:
        from_attributes = True


class AggregatedOddsResponse(BaseModel):
    """Aggregated odds response."""
    
    event_id: str
    mean_prob_yes: float
    miners_count: int
    computed_at: datetime


class WeightItem(BaseModel):
    """Weight item for weights response."""
    
    miner_id: str
    weight: float


class WeightsResponse(BaseModel):
    """Weights response."""
    
    weights: List[WeightItem]
    updated_at: datetime
    sum: float


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "OK"



