"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Add a resolution record.
"""

import asyncio
import argparse
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from wahoopredict.config import settings
from wahoopredict.models import Resolution, Event


async def add_resolution(
    db: AsyncSession,
    event_id: str,
    outcome: bool,
    source: str
) -> None:
    """
    Add a resolution record.
    
    Args:
        db: Database session
        event_id: Event ID
        outcome: True for YES, False for NO
        source: Source URL
    """
    # Check if event exists
    event = await db.get(Event, event_id)
    if not event:
        raise ValueError(f"Event not found: {event_id}")
    
    # Check if resolution already exists
    existing = await db.get(Resolution, event_id)
    if existing:
        print(f"⚠ Resolution already exists for {event_id}, updating...")
        existing.outcome = outcome
        existing.source = source
        existing.resolved_at = datetime.now(timezone.utc)
    else:
        resolution = Resolution(
            event_id=event_id,
            outcome=outcome,
            source=source,
            resolved_at=datetime.now(timezone.utc)
        )
        db.add(resolution)
    
    await db.commit()
    print(f"✓ Resolved {event_id}: {'YES' if outcome else 'NO'}")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Add a resolution record")
    parser.add_argument("--event", required=True, help="Event ID")
    parser.add_argument("--outcome", required=True, choices=["true", "false"], help="Outcome: true or false")
    parser.add_argument("--source", required=True, help="Source URL")
    
    args = parser.parse_args()
    
    outcome = args.outcome == "true"
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        await add_resolution(session, args.event, outcome, args.source)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

