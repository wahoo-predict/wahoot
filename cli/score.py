"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Run update_scores_and_weights.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from wahoopredict.config import settings
from wahoopredict.services.scoring import update_scores_and_weights


async def main() -> None:
    """Main entry point."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        stats = await update_scores_and_weights(session)
        
        print("✓ Scoring complete")
        print(f"  Events processed: {stats['events_processed']}")
        print(f"  Miners scored: {stats['miners_scored']}")
        print(f"  Weights updated: {stats['weights_updated']}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

