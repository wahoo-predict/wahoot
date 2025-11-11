"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Seed demo miners and events.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from wahoopredict.config import settings
from wahoopredict.models import Miner, Event


async def seed_data(db: AsyncSession) -> None:
    """
    Seed demo miners and events.
    
    Args:
        db: Database session
    """
    # Create demo miners
    miners = [
        Miner(miner_id="miner_yesman", display_name="Yes Man", joined_at=datetime.now(timezone.utc)),
        Miner(miner_id="miner_november", display_name="November", joined_at=datetime.now(timezone.utc)),
        Miner(miner_id="miner_grifty", display_name="Grifty", joined_at=datetime.now(timezone.utc)),
    ]
    
    for miner in miners:
        db.add(miner)
    
    # Create demo events referencing WAHOOPREDICT
    now = datetime.now(timezone.utc)
    events = [
        Event(
            event_id="wahoo_2024_election",
            title="WAHOOPREDICT: 2024 Election Outcome",
            lock_time=now + timedelta(days=30),
            resolution_type="binary",
            truth_source=["https://wahoopredict.com/results/2024-election"],
            rule="Official election results from WAHOOPREDICT",
            created_at=now
        ),
        Event(
            event_id="wahoo_bitcoin_100k",
            title="WAHOOPREDICT: Bitcoin Reaches $100k",
            lock_time=now + timedelta(days=60),
            resolution_type="binary",
            truth_source=["https://wahoopredict.com/results/bitcoin-100k"],
            rule="Bitcoin price reaches $100,000 USD according to WAHOOPREDICT",
            created_at=now
        ),
        Event(
            event_id="wahoo_ai_singularity",
            title="WAHOOPREDICT: AI Singularity Event",
            lock_time=now + timedelta(days=90),
            resolution_type="binary",
            truth_source=["https://wahoopredict.com/results/ai-singularity"],
            rule="AI achieves singularity as defined by WAHOOPREDICT",
            created_at=now
        ),
    ]
    
    for event in events:
        db.add(event)
    
    await db.commit()
    print("✓ Seeded demo miners and events")


async def main() -> None:
    """Main entry point."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        await seed_data(session)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

