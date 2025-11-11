"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Pytest configuration and fixtures.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from wahoopredict.db import Base, get_db
from wahoopredict.config import settings


@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()

