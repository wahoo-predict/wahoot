#!/usr/bin/env python3
"""
Interactive database explorer for validator database.

Shows cached validation data, hotkeys, and performance metrics.
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


def get_db_path() -> Path:
    """Get database path from environment or default."""
    db_path = os.getenv("VALIDATOR_DB_PATH", "validator.db")
    if not os.path.isabs(db_path):
        project_root = Path(__file__).parent.parent
        db_path = project_root / db_path
    return Path(db_path)


def view_miners(conn: sqlite3.Connection) -> None:
    """View miners table."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM miners ORDER BY last_seen_ts DESC LIMIT 10")
        rows = cursor.fetchall()
        
        if not rows:
            print("No miners found")
            return
        
        print("\n=== Miners ===")
        print(f"{'Hotkey':<50} {'UID':<6} {'First Seen':<20} {'Last Seen':<20}")
        print("-" * 96)
        for row in rows:
            hotkey = row[0] if len(row) > 0 else "N/A"
            uid = row[1] if len(row) > 1 and row[1] is not None else "N/A"
            first_seen = row[4] if len(row) > 4 and row[4] else "N/A"
            last_seen = row[5] if len(row) > 5 and row[5] else "N/A"
            print(f"{hotkey[:48]:<50} {str(uid):<6} {str(first_seen)[:18]:<20} {str(last_seen)[:18]:<20}")
    except sqlite3.OperationalError as e:
        print(f"Miners table not found: {e}")


def view_validation_cache(conn: sqlite3.Connection, limit: int = 10) -> None:
    """View validation cache entries (if table exists)."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT hotkey, timestamp, data_json 
            FROM validation_cache 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        
        if not rows:
            print("No cached validation data found")
            return
        
        print(f"\n=== Validation Cache (Last {limit}) ===")
        for row in rows:
            hotkey, timestamp, data_json = row
            try:
                data = json.loads(data_json)
                # Handle nested performance structure
                if "performance" in data:
                    perf = data["performance"]
                    volume = perf.get("total_volume_usd", 0)
                    profit = perf.get("realized_profit_usd", 0)
                    win_rate = perf.get("win_rate", 0)
                else:
                    # Flat structure
                    volume = data.get("total_volume_usd", 0)
                    profit = data.get("realized_profit_usd", 0)
                    win_rate = data.get("win_rate", 0)
                
                print(f"\nHotkey: {hotkey}")
                print(f"  Timestamp: {timestamp}")
                print(f"  Volume: ${float(volume):,.2f}" if volume else "  Volume: N/A")
                print(f"  Profit: ${float(profit):,.2f}" if profit else "  Profit: N/A")
                print(f"  Win Rate: {float(win_rate):.2%}" if win_rate else "  Win Rate: N/A")
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(f"\nHotkey: {hotkey}")
                print(f"  Timestamp: {timestamp}")
                print(f"  Error parsing data: {e}")
                print(f"  Data preview: {data_json[:100]}...")
    except sqlite3.OperationalError:
        # Table doesn't exist yet (ValidatorDB not fully implemented)
        print("Validation cache table not found (will be created when ValidatorDB is implemented)")


def view_performance_snapshots(conn: sqlite3.Connection, limit: int = 10) -> None:
    """View performance snapshots."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT hotkey, timestamp, total_volume_usd, realized_profit_usd, win_rate
            FROM performance_snapshots
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        
        if not rows:
            print("No performance snapshots found")
            return
        
        print(f"\n=== Performance Snapshots (Last {limit}) ===")
        print(f"{'Hotkey':<50} {'Timestamp':<20} {'Volume':<15} {'Profit':<15} {'Win Rate':<10}")
        print("-" * 110)
        for row in rows:
            hotkey = row[0][:48] if row[0] else "N/A"
            timestamp = row[1][:18] if row[1] else "N/A"
            volume = f"${row[2]:,.2f}" if row[2] else "$0.00"
            profit = f"${row[3]:,.2f}" if row[3] else "$0.00"
            win_rate = f"{row[4]:.2%}" if row[4] else "0.00%"
            print(f"{hotkey:<50} {timestamp:<20} {volume:<15} {profit:<15} {win_rate:<10}")
    except sqlite3.OperationalError as e:
        print(f"Performance snapshots table not found: {e}")


def view_statistics(conn: sqlite3.Connection) -> None:
    """View database statistics."""
    cursor = conn.cursor()
    
    print("\n=== Database Statistics ===")
    
    # Count miners
    try:
        cursor.execute("SELECT COUNT(*) FROM miners")
        miner_count = cursor.fetchone()[0]
        print(f"Miners: {miner_count}")
    except sqlite3.OperationalError:
        print("Miners: Table not found")
    
    # Count cache entries
    try:
        cursor.execute("SELECT COUNT(*) FROM validation_cache")
        cache_count = cursor.fetchone()[0]
        print(f"Cached Validation Records: {cache_count}")
    except sqlite3.OperationalError:
        print("Validation Cache: Table not found")
    
    # Count snapshots
    try:
        cursor.execute("SELECT COUNT(*) FROM performance_snapshots")
        snapshot_count = cursor.fetchone()[0]
        print(f"Performance Snapshots: {snapshot_count}")
    except sqlite3.OperationalError:
        print("Performance Snapshots: Table not found")
    
    # Database size
    db_path = get_db_path()
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"Database Size: {size_mb:.2f} MB")


def main():
    """Main function."""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"Database not found at: {db_path}")
        print("Create one by running the validator or tests")
        return
    
    print("=" * 70)
    print("Validator Database Explorer")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Size: {db_path.stat().st_size / 1024:.2f} KB")
    print()
    
    try:
        conn = sqlite3.connect(str(db_path))
        
        # Show statistics
        view_statistics(conn)
        
        # Show miners (actual table name)
        view_miners(conn)
        
        # Show validation cache (if exists)
        view_validation_cache(conn, limit=5)
        
        # Show performance snapshots
        view_performance_snapshots(conn, limit=5)
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("To explore interactively:")
        print(f"  sqlite3 {db_path}")
        print("=" * 70)
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")


if __name__ == "__main__":
    main()

