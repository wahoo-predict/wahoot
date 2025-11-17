import os
import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    """Get the database path from environment or use default."""
    db_path = os.getenv("VALIDATOR_DB_PATH", "validator.db")
    if not os.path.isabs(db_path):
        # Default to project root
        project_root = Path(__file__).parent.parent.parent.parent
        db_path = project_root / db_path
    return Path(db_path)


def get_or_create_database(db_path: Optional[Path] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    # If database is new (empty), initialize with schema
    if not tables:
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            with open(schema_file, "r") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
    
    return conn


def check_database_exists(db_path: Optional[Path] = None) -> bool:
    if db_path is None:
        db_path = get_db_path()
    
    db_path = Path(db_path)
    
    if not db_path.exists():
        return False
    
    # Try to connect and verify it's a valid SQLite database
    try:
        conn = sqlite3.connect(str(db_path))
        # Try to query sqlite_master to verify it's a valid database
        conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        conn.close()
        
        # Also check magic header if file has content (for corrupted file detection)
        if db_path.stat().st_size > 0:
            try:
                with open(db_path, "rb") as f:
                    header = f.read(16)
                    # If file has content but doesn't have SQLite header, it's corrupted
                    if len(header) >= 16 and not header.startswith(b"SQLite format 3\x00"):
                        return False
            except (IOError, OSError):
                pass  # If we can't read, but connection worked, assume it's OK
        return True
    except sqlite3.Error:
        return False

