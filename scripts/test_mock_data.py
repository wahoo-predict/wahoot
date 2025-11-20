#!/usr/bin/env python3
"""
Simple script to test mock data generation.
No interactive Python needed!
"""

from wahoo.validator.mock_data import (
    generate_mock_validation_data,
    create_real_api_format_example,
)
import json

print("=" * 70)
print("Mock Data Generator Test")
print("=" * 70)
print()

# Test 1: Generate mock data
print("1. Generating mock validation data...")
hotkeys = [
    "5Dnh2o9x9kTRtfeF5g3W4uzfzWNeGD1EJo4aCtibAESzP2iE",
    "5FddqPQUhEFeLqVNbenAj6EDRKuqgezciN9TmTgBmNABsj53",
]
data = generate_mock_validation_data(hotkeys)

print(f"   Generated {len(data)} records")
print()
for i, record in enumerate(data, 1):
    print(f"   Record {i}:")
    print(f"     Hotkey: {record.hotkey[:30]}...")
    print(f"     Volume: ${record.performance.total_volume_usd:,.2f}")
    print(f"     Profit: ${record.performance.realized_profit_usd:,.2f}")
    print(f"     Trades: {record.performance.trade_count}")
    print(f"     Open Positions: {record.performance.open_positions_count}")
    print()

# Test 2: Real API format example
print("2. Real API format example:")
print()
real_format = create_real_api_format_example()
print(json.dumps(real_format, indent=2))
print()

# Test 3: Test model validation
print("3. Testing model validation with real API format...")
print()
from wahoo.validator.models import ValidationRecord, PerformanceMetrics

perf = PerformanceMetrics(
    total_volume_usd="17581.69866",
    realized_profit_usd="-1517.98587",
    unrealized_profit_usd=0,
    trade_count=781,
    open_positions_count=0,
)
record = ValidationRecord(
    hotkey="5Dnh2o9x9kTRtfeF5g3W4uzfzWNeGD1EJo4aCtibAESzP2iE",
    signature="673PvPKoEEgmnnrH-5p6V",
    message="test message",
    performance=perf,
)

print("   ✅ Record created successfully!")
print(f"   Volume: ${record.performance.total_volume_usd:,.2f} (type: {type(record.performance.total_volume_usd).__name__})")
print(f"   Profit: ${record.performance.realized_profit_usd:,.2f} (type: {type(record.performance.realized_profit_usd).__name__})")
print(f"   Trades: {record.performance.trade_count}")
print()

print("=" * 70)
print("All tests passed! ✅")
print("=" * 70)

