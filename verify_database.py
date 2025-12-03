#!/usr/bin/env python3
"""
Verify validator database after testing
Usage: python verify_database.py
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))  # noqa: E402

from wahoo.validator.database.core import ValidatorDB  # noqa: E402
from wahoo.validator.database.validator_db import get_db_path  # noqa: E402


def verify_database():
    """Verify database contents"""
    print("=" * 60)
    print("Validator Database Verification")
    print("=" * 60)

    db_path = get_db_path()
    print(f"Database path: {db_path}")

    if not Path(db_path).exists():
        print("❌ Database file does not exist!")
        return False

    print("✓ Database file exists")
    print()

    try:
        db = ValidatorDB(db_path=db_path)

        # Check latest scores
        print("Checking EMA scores...")
        scores = db.get_latest_scores()
        if scores:
            print(f"✓ Found {len(scores)} EMA scores:")
            for hotkey, score in list(scores.items())[:10]:  # Show first 10
                print(f"  {hotkey[:20]}... : {score:.6f}")
            if len(scores) > 10:
                print(f"  ... and {len(scores) - 10} more")
        else:
            print("⚠ No EMA scores found in database")
        print()

        # Check cached validation data
        print("Checking cached validation data...")
        # We need hotkeys to check - get from scores or use test hotkeys
        if scores:
            hotkeys = list(scores.keys())[:5]  # Check first 5
            cached = db.get_cached_validation_data(hotkeys, max_age_days=7)
            print(f"✓ Found {len(cached)} cached records for {len(hotkeys)} hotkeys")
        else:
            print("⚠ No hotkeys to check (no scores found)")
        print()

        # Check database size
        db_size = Path(db_path).stat().st_size
        print(f"Database size: {db_size / 1024:.2f} KB")
        print()

        print("=" * 60)
        print("Database Verification Summary")
        print("=" * 60)
        print(f"✓ Database exists: {Path(db_path).exists()}")
        print(f"✓ EMA scores: {len(scores)} records")
        print(f"✓ Database size: {db_size / 1024:.2f} KB")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)
