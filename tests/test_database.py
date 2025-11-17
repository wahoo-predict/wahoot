"""Tests for database connection and creation."""
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from wahoo.validator.database.validator_db import (
    get_db_path,
    get_or_create_database,
    check_database_exists,
)


class TestDatabasePath:
    """Tests for database path resolution."""
    
    def test_get_db_path_default(self):
        """Test that default database path is returned when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            db_path = get_db_path()
            assert db_path.name == "validator.db"
            assert db_path.is_absolute()
    
    def test_get_db_path_from_env_var(self):
        """Test that database path is read from VALIDATOR_DB_PATH env var."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db_path = Path(tmpdir) / "test.db"
            
            with patch.dict(os.environ, {"VALIDATOR_DB_PATH": str(test_db_path)}):
                db_path = get_db_path()
                assert db_path == test_db_path
    
    def test_get_db_path_relative_becomes_absolute(self):
        """Test that relative paths are converted to absolute."""
        with patch.dict(os.environ, {"VALIDATOR_DB_PATH": "relative.db"}):
            db_path = get_db_path()
            assert db_path.is_absolute()
            assert db_path.name == "relative.db"


class TestDatabaseExists:
    """Tests for database existence checking."""
    
    def test_check_database_exists_when_exists(self):
        """Test that check_database_exists returns True for existing database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create a valid SQLite database
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            conn.close()
            
            assert check_database_exists(db_path) is True
    
    def test_check_database_exists_when_not_exists(self):
        """Test that check_database_exists returns False for non-existent database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nonexistent.db"
            
            assert check_database_exists(db_path) is False
    
    def test_check_database_exists_with_custom_path(self):
        """Test check_database_exists with custom path parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom.db"
            
            # Create database and write something to ensure it's properly initialized
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            conn.close()
            
            assert check_database_exists(db_path) is True
    
    def test_check_database_exists_handles_corrupted_db(self):
        """Test that check_database_exists handles corrupted databases gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "corrupted.db"
            
            # Create a file that's not a valid SQLite database
            db_path.write_text("not a valid database")
            
            # Should return False for corrupted database
            assert check_database_exists(db_path) is False


class TestGetOrCreateDatabase:
    """Tests for database connection and creation."""
    
    def test_get_or_create_database_creates_new_db(self):
        """Test that get_or_create_database creates a new database if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "new.db"
            
            assert not db_path.exists()
            
            conn = get_or_create_database(db_path)
            
            try:
                assert db_path.exists()
                assert conn is not None
                
                # Verify we can execute queries
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result == (1,)
            finally:
                conn.close()
    
    def test_get_or_create_database_returns_existing_db(self):
        """Test that get_or_create_database returns connection to existing database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "existing.db"
            
            # Create database with some data
            conn1 = sqlite3.connect(str(db_path))
            conn1.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            conn1.execute("INSERT INTO test (value) VALUES ('test')")
            conn1.commit()
            conn1.close()
            
            # Get connection using get_or_create_database
            conn2 = get_or_create_database(db_path)
            
            try:
                cursor = conn2.cursor()
                cursor.execute("SELECT value FROM test WHERE id = 1")
                result = cursor.fetchone()
                assert result == ("test",)
            finally:
                conn2.close()
    
    def test_get_or_create_database_initializes_schema(self):
        """Test that new databases are initialized with schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "schema_test.db"
            
            conn = get_or_create_database(db_path)
            
            try:
                cursor = conn.cursor()
                
                # Check that schema tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('miners', 'performance_snapshots', 'scoring_runs')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                assert "miners" in tables
                assert "performance_snapshots" in tables
                assert "scoring_runs" in tables
                
                # Verify table structure
                cursor.execute("PRAGMA table_info(miners)")
                columns = [row[1] for row in cursor.fetchall()]
                assert "hotkey" in columns
                assert "uid" in columns
                
            finally:
                conn.close()
    
    def test_get_or_create_database_creates_parent_directories(self):
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dirs" / "test.db"
            
            assert not db_path.parent.exists()
            
            conn = get_or_create_database(db_path)
            
            try:
                assert db_path.parent.exists()
                assert db_path.exists()
            finally:
                conn.close()
                # TemporaryDirectory will automatically clean up all files and directories
    
    def test_get_or_create_database_uses_env_var_when_path_not_provided(self):
        """Test that get_or_create_database uses VALIDATOR_DB_PATH when path is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "env_var.db"
            
            with patch.dict(os.environ, {"VALIDATOR_DB_PATH": str(db_path)}):
                conn = get_or_create_database()
                
                try:
                    assert db_path.exists()
                finally:
                    conn.close()
    
    def test_get_or_create_database_handles_multiple_connections(self):
        """Test that multiple connections to the same database work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "multi_conn.db"
            
            conn1 = get_or_create_database(db_path)
            conn2 = get_or_create_database(db_path)
            
            try:
                # Both connections should work
                cursor1 = conn1.cursor()
                cursor1.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
                cursor1.execute("INSERT INTO test (id) VALUES (1)")
                conn1.commit()
                
                cursor2 = conn2.cursor()
                cursor2.execute("SELECT id FROM test")
                result = cursor2.fetchone()
                assert result == (1,)
            finally:
                conn1.close()
                conn2.close()
    
    def test_get_or_create_database_preserves_existing_schema(self):
        """Test that existing databases with schema are not re-initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "preserve.db"
            
            # Create database with schema
            conn1 = get_or_create_database(db_path)
            conn1.close()
            
            # Add some data
            conn2 = sqlite3.connect(str(db_path))
            conn2.execute("INSERT INTO miners (hotkey, uid) VALUES ('test_key', 1)")
            conn2.commit()
            conn2.close()
            
            # Get connection again - should preserve data
            conn3 = get_or_create_database(db_path)
            
            try:
                cursor = conn3.cursor()
                cursor.execute("SELECT hotkey FROM miners WHERE uid = 1")
                result = cursor.fetchone()
                assert result == ("test_key",)
            finally:
                conn3.close()

