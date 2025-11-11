"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Export weights to JSON file.
"""

import asyncio
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from wahoopredict.config import settings
from wahoopredict.services.weights import export_weights_json


async def main() -> None:
    """Main entry point."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        weights_data = await export_weights_json(session)
        
        # Create data directory if it doesn't exist
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        # Write to file
        output_file = data_dir / "weights.json"
        with open(output_file, "w") as f:
            json.dump(weights_data, f, indent=2)
        
        print(f"✓ Exported weights to {output_file}")
        print(f"  Total miners: {len(weights_data['weights'])}")
        print(f"  Weight sum: {weights_data['sum']:.6f}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

