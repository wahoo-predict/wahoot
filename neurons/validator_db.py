"""
WAHOOPREDICT - Lightweight SQLite database for validator backup.

Validators can use this as a lightweight backup in case AWS/API goes down.
Stores minimal data: hotkeys, validation data cache, and weights.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path


class ValidatorDB:
    """Lightweight SQLite database for validator backup."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize validator database.
        
        Args:
            db_path: Path to SQLite database file (defaults to ~/.wahoo/validator.db)
        """
        if db_path is None:
            # Default to ~/.wahoo/validator.db
            home = Path.home()
            wahoo_dir = home / ".wahoo"
            wahoo_dir.mkdir(exist_ok=True, parents=True)
            db_path = str(wahoo_dir / "validator.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Hotkeys table - stores registered hotkeys
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hotkeys (
                ss58_hotkey TEXT PRIMARY KEY,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                metadata TEXT  -- JSON metadata
            )
        """)
        
        # Validation cache - stores WAHOO API validation data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_cache (
                ss58_hotkey TEXT PRIMARY KEY,
                validation_data TEXT,  -- JSON validation data
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ss58_hotkey) REFERENCES hotkeys(ss58_hotkey)
            )
        """)
        
        # Weights cache - stores weights from API
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weights_cache (
                ss58_hotkey TEXT PRIMARY KEY,
                weight REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ss58_hotkey) REFERENCES hotkeys(ss58_hotkey)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_validation_fetched ON validation_cache(fetched_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weights_updated ON weights_cache(updated_at)")
        
        conn.commit()
        conn.close()
    
    def add_hotkey(self, ss58_hotkey: str, metadata: Optional[Dict[str, Any]] = None):
        """Add or update a hotkey."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT OR REPLACE INTO hotkeys (ss58_hotkey, last_seen, metadata)
            VALUES (?, ?, ?)
        """, (ss58_hotkey, datetime.now(timezone.utc).isoformat(), metadata_json))
        
        conn.commit()
        conn.close()
    
    def get_hotkeys(self) -> List[str]:
        """Get all registered hotkeys."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT ss58_hotkey FROM hotkeys")
        hotkeys = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return hotkeys
    
    def cache_validation_data(self, ss58_hotkey: str, validation_data: Dict[str, Any]):
        """Cache validation data from WAHOO API."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        validation_json = json.dumps(validation_data)
        
        cursor.execute("""
            INSERT OR REPLACE INTO validation_cache (ss58_hotkey, validation_data, fetched_at)
            VALUES (?, ?, ?)
        """, (ss58_hotkey, validation_json, datetime.now(timezone.utc).isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_cached_validation_data(self, ss58_hotkey: str) -> Optional[Dict[str, Any]]:
        """Get cached validation data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT validation_data FROM validation_cache
            WHERE ss58_hotkey = ?
        """, (ss58_hotkey,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def cache_weights(self, weights: Dict[str, float]):
        """Cache weights from API."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        for hotkey, weight in weights.items():
            cursor.execute("""
                INSERT OR REPLACE INTO weights_cache (ss58_hotkey, weight, updated_at)
                VALUES (?, ?, ?)
            """, (hotkey, weight, now))
        
        conn.commit()
        conn.close()
    
    def get_cached_weights(self) -> Dict[str, float]:
        """Get cached weights."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT ss58_hotkey, weight FROM weights_cache")
        weights = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return weights
    
    def cleanup_old_cache(self, days: int = 7):
        """Clean up cache older than specified days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now(timezone.utc).replace(days=-days).isoformat()
        
        cursor.execute("""
            DELETE FROM validation_cache WHERE fetched_at < ?
        """, (cutoff,))
        
        cursor.execute("""
            DELETE FROM weights_cache WHERE updated_at < ?
        """, (cutoff,))
        
        conn.commit()
        conn.close()

