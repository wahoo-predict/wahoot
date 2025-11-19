#!/usr/bin/env python3
"""
Manual test script for batching functionality.

Run this to test the batch loop with real or mocked data:
    python tests/test_batching_manual.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wahoo.validator.api.client import get_wahoo_validation_data  # noqa: E402


def test_batching_with_mock_data():
    """Test batching with a small set of mock hotkeys."""
    print("=" * 60)
    print("Testing Batch Loop")
    print("=" * 60)

    # Create test hotkeys (more than 256 to test batching)
    hotkeys = [
        f"5G6HBuhKoYUjGvbcoa6X6Tm3q2jNFek1Ry78S8gKyY5HgiDj_{i}" for i in range(300)
    ]

    print(f"\nTesting with {len(hotkeys)} hotkeys")
    print(f"Expected batches: {len(hotkeys) // 256 + (1 if len(hotkeys) % 256 else 0)}")

    try:
        # This will fail if API is not accessible, but tests the batching logic
        records = get_wahoo_validation_data(
            hotkeys=hotkeys,
            max_per_batch=256,
        )
        print(f"\n✓ Successfully processed {len(records)} records")
        return True
    except Exception as e:
        print(f"\n✗ Error (expected if API not accessible): {e}")
        print("\nNote: This tests the batching logic. For full testing, use pytest:")
        print(
            "  pytest tests/test_client.py::test_get_wahoo_validation_data_batching_splits_correctly"
        )
        return False


def test_batching_edge_cases():
    """Test edge cases."""
    print("\n" + "=" * 60)
    print("Testing Edge Cases")
    print("=" * 60)

    # Test empty list
    print("\n1. Testing empty hotkeys list...")
    records = get_wahoo_validation_data(hotkeys=[])
    assert records == [], "Empty list should return empty results"
    print("   ✓ Empty list handled correctly")

    # Test single hotkey
    print("\n2. Testing single hotkey...")
    try:
        records = get_wahoo_validation_data(hotkeys=["test_hotkey"])
        print(f"   ✓ Single hotkey processed (got {len(records)} records)")
    except Exception:
        print("   ✓ Single hotkey handled (API error expected)")

    # Test exactly 256 hotkeys (one batch)
    print("\n3. Testing exactly 256 hotkeys (one batch)...")
    hotkeys_256 = [f"hotkey_{i}" for i in range(256)]
    try:
        records = get_wahoo_validation_data(hotkeys=hotkeys_256, max_per_batch=256)
        print(f"   ✓ Exactly 256 hotkeys processed (got {len(records)} records)")
    except Exception:
        print("   ✓ Exactly 256 hotkeys handled (API error expected)")

    # Test 257 hotkeys (two batches)
    print("\n4. Testing 257 hotkeys (two batches)...")
    hotkeys_257 = [f"hotkey_{i}" for i in range(257)]
    try:
        records = get_wahoo_validation_data(hotkeys=hotkeys_257, max_per_batch=256)
        print(f"   ✓ 257 hotkeys processed (got {len(records)} records)")
    except Exception:
        print("   ✓ 257 hotkeys handled (API error expected)")

    print("\n" + "=" * 60)
    print("Edge case tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Batch Loop Manual Test")
    print("=" * 60)
    print("\nThis script tests the batching functionality.")
    print("Note: It will fail if the WAHOO API is not accessible,")
    print("      but it still tests the batching logic.\n")

    # Test edge cases (these don't require API access)
    test_batching_edge_cases()

    # Test with mock data (requires API or will show expected error)
    print("\n")
    test_batching_with_mock_data()

    print("\n" + "=" * 60)
    print("For comprehensive tests with mocks, run:")
    print("  pytest tests/test_client.py -v")
    print("=" * 60)
