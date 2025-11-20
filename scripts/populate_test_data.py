#!/usr/bin/env python3
"""
Populate validator database with test data.

This script inserts mock validation data into the database
so you can see how it looks when the validator runs.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from wahoo.validator.mock_data import generate_mock_validation_data, create_real_api_format_example
from wahoo.validator.database.validator_db import get_db_path

def populate_database():
    """Populate database with test data."""
    db_path = get_db_path()
    
    print("=" * 70)
    print("Populating Validator Database with Test Data")
    print("=" * 70)
    print(f"Database: {db_path}")
    print()
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get real API format example (your actual data)
    real_data = create_real_api_format_example()
    
    # Also generate some additional mock data
    additional_hotkeys = [
        "5E2WWRc41ekrak33NjqZZ338s2sEX5rLCnZXEGKfD52PMqod",
        "5EaNWwsjZpoM6RDwgKoukSHJZ2yyEHmGGXogRejdBwCNV9SP",
        "5De1Fkvq9g4idEzvr8h8WEEQa1xAeaXfA2TZfYMKgdMm4Qai",
    ]
    mock_data = generate_mock_validation_data(additional_hotkeys)
    
    # Combine real format data with mock data
    all_hotkeys = [item["hotkey"] for item in real_data] + additional_hotkeys
    all_data = []
    
    # Convert real API format to ValidationRecord
    from wahoo.validator.models import ValidationRecord, PerformanceMetrics
    
    for item in real_data:
        perf = PerformanceMetrics(
            total_volume_usd=float(item["performance"]["total_volume_usd"]),
            realized_profit_usd=float(item["performance"]["realized_profit_usd"]),
            unrealized_profit_usd=item["performance"]["unrealized_profit_usd"],
            trade_count=item["performance"]["trade_count"],
            open_positions_count=item["performance"]["open_positions_count"],
        )
        record = ValidationRecord(
            hotkey=item["hotkey"],
            signature=item["signature"],
            message=item["message"],
            performance=perf,
        )
        all_data.append(record)
    
    # Add mock data
    all_data.extend(mock_data)
    
    print(f"Inserting {len(all_data)} miner records...")
    print()
    
    # Insert into miners table
    now = datetime.now(timezone.utc).isoformat() + "Z"
    for i, record in enumerate(all_data, 1):
        cursor.execute("""
            INSERT OR REPLACE INTO miners (
                hotkey, uid, first_seen_ts, last_seen_ts, axon_ip
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            record.hotkey,
            i,  # Mock UID
            now,
            now,
            "127.0.0.1",  # Mock IP
        ))
        print(f"  [{i}/{len(all_data)}] Inserted miner: {record.hotkey[:30]}...")
    
    # Insert into performance_snapshots table
    print()
    print(f"Inserting {len(all_data)} performance snapshots...")
    print()
    
    for i, record in enumerate(all_data, 1):
        perf = record.performance
        cursor.execute("""
            INSERT INTO performance_snapshots (
                hotkey, timestamp,
                total_volume_usd, trade_count,
                realized_profit_usd, unrealized_profit_usd,
                win_rate, total_fees_paid_usd,
                open_positions_count, referral_count, referral_volume
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.hotkey,
            now,
            perf.total_volume_usd,
            perf.trade_count,
            perf.realized_profit_usd,
            perf.unrealized_profit_usd,
            perf.win_rate,
            perf.total_fees_paid_usd,
            perf.open_positions_count,
            perf.referral_count,
            perf.referral_volume_usd,
        ))
        print(f"  [{i}/{len(all_data)}] Inserted snapshot: Volume=${perf.total_volume_usd:,.2f}, Profit=${perf.realized_profit_usd:,.2f}")
    
    # Create validation_cache table if it doesn't exist (for future use)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation_cache (
            hotkey TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    # Insert into validation_cache (simulating cached API responses)
    print()
    print(f"Inserting {len(all_data)} cached validation records...")
    print()
    
    for i, record in enumerate(all_data, 1):
        data_dict = record.model_dump()
        data_json = json.dumps(data_dict)
        cursor.execute("""
            INSERT OR REPLACE INTO validation_cache (
                hotkey, data_json, timestamp
            ) VALUES (?, ?, ?)
        """, (
            record.hotkey,
            data_json,
            now,
        ))
        print(f"  [{i}/{len(all_data)}] Cached validation data for: {record.hotkey[:30]}...")
    
    # Commit all changes
    conn.commit()
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ Database populated successfully!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Miners: {len(all_data)}")
    print(f"  - Performance Snapshots: {len(all_data)}")
    print(f"  - Cached Validation Records: {len(all_data)}")
    print()
    print("View the data:")
    print("  python scripts/explore_database.py")
    print("  sqlite3 validator.db 'SELECT * FROM miners;'")
    print()

if __name__ == "__main__":
    populate_database()

