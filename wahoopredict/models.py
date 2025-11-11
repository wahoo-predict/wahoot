"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

SQLAlchemy models for WAHOOPREDICT database schema.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from wahoopredict.db import Base


class Miner(Base):
    """Miner registry."""
    
    __tablename__ = "miners"
    
    miner_id = Column(String, primary_key=True, index=True)
    display_name = Column(Text, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Event(Base):
    """Binary events with lock times."""
    
    __tablename__ = "events"
    
    event_id = Column(String, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    lock_time = Column(DateTime(timezone=True), nullable=False, index=True)
    resolution_type = Column(String, default="binary", nullable=False)
    truth_source = Column(ARRAY(Text), nullable=True)  # Array of source URLs
    rule = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    submissions = relationship("Submission", back_populates="event")
    resolution = relationship("Resolution", back_populates="event", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_events_lock_time", "lock_time"),
    )


class Submission(Base):
    """Miner predictions (prob_yes, manifest_hash, sig)."""
    
    __tablename__ = "submissions"
    
    submission_id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String, ForeignKey("events.event_id"), nullable=False, index=True)
    miner_id = Column(String, ForeignKey("miners.miner_id"), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    prob_yes = Column(
        Numeric(6, 5),
        CheckConstraint("prob_yes >= 0 AND prob_yes <= 1"),
        nullable=False
    )
    manifest_hash = Column(String, nullable=False)
    sig = Column(Text, nullable=False)
    
    # Relationships
    event = relationship("Event", back_populates="submissions")
    miner = relationship("Miner")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_submissions_event_submitted", "event_id", "submitted_at"),
        Index("idx_submissions_event_miner_submitted", "event_id", "miner_id", "submitted_at"),
        UniqueConstraint("event_id", "manifest_hash", name="uq_submissions_event_manifest"),
    )


class Resolution(Base):
    """Event outcomes."""
    
    __tablename__ = "resolutions"
    
    event_id = Column(String, ForeignKey("events.event_id"), primary_key=True)
    outcome = Column(Boolean, nullable=False)
    resolved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source = Column(Text, nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="resolution")


class BrierArchive(Base):
    """Historical Brier scores."""
    
    __tablename__ = "brier_archive"
    
    event_id = Column(String, ForeignKey("events.event_id"), primary_key=True)
    miner_id = Column(String, ForeignKey("miners.miner_id"), primary_key=True)
    brier = Column(Double, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    event = relationship("Event")
    miner = relationship("Miner")


class MinerStats(Base):
    """EMA(7d) Brier scores per miner."""
    
    __tablename__ = "miner_stats"
    
    miner_id = Column(String, ForeignKey("miners.miner_id"), primary_key=True)
    ema_brier = Column(Double, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    miner = relationship("Miner")


class Weight(Base):
    """Normalized weights for validators."""
    
    __tablename__ = "weights"
    
    miner_id = Column(String, ForeignKey("miners.miner_id"), primary_key=True)
    weight = Column(
        Double,
        CheckConstraint("weight >= 0"),
        nullable=False
    )
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    miner = relationship("Miner")


class SubmissionAlert(Base):
    """Duplicate manifest warnings."""
    
    __tablename__ = "submission_alerts"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String, nullable=False, index=True)
    miner_id = Column(String, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AffiliateClick(Base):
    """Track clicks to WAHOO via affiliate links."""
    
    __tablename__ = "affiliate_clicks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    miner_id = Column(String, ForeignKey("miners.miner_id"), nullable=False, index=True)
    market_id = Column(String, nullable=True, index=True)
    affid = Column(String, nullable=False, index=True)  # Affiliate ID
    subid = Column(String, nullable=True, index=True)  # Sub ID (miner-specific)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    miner = relationship("Miner")
    
    # Indexes
    __table_args__ = (
        Index("idx_affiliate_clicks_miner_clicked", "miner_id", "clicked_at"),
    )


class AffiliatePostback(Base):
    """S2S postbacks from WAHOO (signup, first_deposit, first_prediction, settled_prediction)."""
    
    __tablename__ = "affiliate_postbacks"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    postback_type = Column(String, nullable=False, index=True)  # signup, first_deposit, first_prediction, settled_prediction
    affid = Column(String, nullable=False, index=True)
    subid = Column(String, nullable=True, index=True)
    market_id = Column(String, nullable=True, index=True)
    amount = Column(Numeric(20, 8), nullable=True)  # Revenue amount
    payload = Column(JSONB, nullable=False)  # Full postback payload
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_affiliate_postbacks_type_received", "postback_type", "received_at"),
        Index("idx_affiliate_postbacks_subid", "subid"),
    )


class MinerUsage(Base):
    """Aggregated usage stats per miner (for v2 scoring)."""
    
    __tablename__ = "miner_usage"
    
    miner_id = Column(String, ForeignKey("miners.miner_id"), primary_key=True)
    unique_clicks = Column(BigInteger, default=0, nullable=False)  # Unique clicks to WAHOO
    total_clicks = Column(BigInteger, default=0, nullable=False)
    referrals = Column(BigInteger, default=0, nullable=False)  # Qualified first deposits
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    miner = relationship("Miner")


class RevenuePool(Base):
    """Affiliate Revenue Pool (ARP) tracking."""
    
    __tablename__ = "revenue_pool"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    week_start = Column(DateTime(timezone=True), nullable=False, index=True)
    week_end = Column(DateTime(timezone=True), nullable=False)
    total_revenue = Column(Numeric(20, 8), default=0, nullable=False)
    miners_share = Column(Numeric(20, 8), default=0, nullable=False)  # 60%
    validators_share = Column(Numeric(20, 8), default=0, nullable=False)  # 20%
    treasury_share = Column(Numeric(20, 8), default=0, nullable=False)  # 20%
    distributed = Column(Boolean, default=False, nullable=False)
    distributed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_revenue_pool_week", "week_start"),
    )


class MinerRevenueShare(Base):
    """Individual miner revenue share allocations."""
    
    __tablename__ = "miner_revenue_share"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    pool_id = Column(BigInteger, ForeignKey("revenue_pool.id"), nullable=False, index=True)
    miner_id = Column(String, ForeignKey("miners.miner_id"), nullable=False, index=True)
    weight = Column(Double, nullable=False)  # Normalized weight at distribution time
    amount = Column(Numeric(20, 8), nullable=False)
    distributed = Column(Boolean, default=False, nullable=False)
    distributed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    pool = relationship("RevenuePool")
    miner = relationship("Miner")
    
    # Indexes
    __table_args__ = (
        Index("idx_miner_revenue_share_pool_miner", "pool_id", "miner_id"),
    )

