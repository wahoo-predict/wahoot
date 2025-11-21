import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest
import json

from wahoo.validator.database.validator_db import (
    get_or_create_database,
    check_database_exists,
)


class TestDatabaseOperations:
    @pytest.fixture
    def temp_db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    def test_database_creation(self, temp_db_path):
        if temp_db_path.exists():
            temp_db_path.unlink()
        assert not check_database_exists(temp_db_path)

        conn = get_or_create_database(temp_db_path)
        assert conn is not None

        assert check_database_exists(temp_db_path)

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "miners" in tables

        conn.close()

    def test_cache_validation_data(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cache (
                hotkey TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        test_data = {
            "hotkey": hotkey,
            "total_volume_usd": 1000.0,
            "realized_profit_usd": 50.0,
            "win_rate": 0.65,
        }
        data_json = json.dumps(test_data)
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        cursor.execute(
            """
            INSERT OR REPLACE INTO validation_cache (hotkey, data_json, timestamp)
            VALUES (?, ?, ?)
        """,
            (hotkey, data_json, timestamp),
        )
        conn.commit()

        cursor.execute(
            """
            SELECT data_json, timestamp FROM validation_cache
            WHERE hotkey = ?
        """,
            (hotkey,),
        )
        row = cursor.fetchone()

        assert row is not None
        retrieved_data = json.loads(row[0])
        assert retrieved_data["hotkey"] == hotkey
        assert retrieved_data["total_volume_usd"] == 1000.0

        conn.close()

    def test_get_cached_validation_data(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cache (
                hotkey TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        hotkeys = [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        ]

        now = datetime.now(timezone.utc)
        for i, hotkey in enumerate(hotkeys):
            test_data = {
                "hotkey": hotkey,
                "total_volume_usd": 1000.0 * (i + 1),
            }
            data_json = json.dumps(test_data)
            timestamp = (now - timedelta(days=i)).isoformat() + "Z"

            cursor.execute(
                """
                INSERT OR REPLACE INTO validation_cache (hotkey, data_json, timestamp)
                VALUES (?, ?, ?)
            """,
                (hotkey, data_json, timestamp),
            )

        conn.commit()

        seven_days_ago = (now - timedelta(days=7)).isoformat() + "Z"
        cursor.execute(
            """
            SELECT hotkey, data_json FROM validation_cache
            WHERE hotkey IN ({})
            AND timestamp > ?
        """.format(
                ",".join("?" * len(hotkeys))
            ),
            hotkeys + [seven_days_ago],
        )

        rows = cursor.fetchall()
        assert len(rows) == 2

        conn.close()

    def test_cleanup_old_cache(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cache (
                hotkey TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        now = datetime.now(timezone.utc)

        old_hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        old_timestamp = (now - timedelta(days=8)).isoformat() + "Z"
        cursor.execute(
            """
            INSERT INTO validation_cache (hotkey, data_json, timestamp)
            VALUES (?, ?, ?)
        """,
            (old_hotkey, json.dumps({"hotkey": old_hotkey}), old_timestamp),
        )

        new_hotkey = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
        new_timestamp = (now - timedelta(days=1)).isoformat() + "Z"
        cursor.execute(
            """
            INSERT INTO validation_cache (hotkey, data_json, timestamp)
            VALUES (?, ?, ?)
        """,
            (new_hotkey, json.dumps({"hotkey": new_hotkey}), new_timestamp),
        )

        conn.commit()

        seven_days_ago = (now - timedelta(days=7)).isoformat() + "Z"
        cursor.execute(
            """
            DELETE FROM validation_cache
            WHERE timestamp < ?
        """,
            (seven_days_ago,),
        )
        conn.commit()

        cursor.execute("SELECT hotkey FROM validation_cache")
        remaining = [row[0] for row in cursor.fetchall()]

        assert old_hotkey not in remaining
        assert new_hotkey in remaining

        conn.close()

    def test_vacuum_database(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)

        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """
        )

        for i in range(100):
            cursor.execute("INSERT INTO test_table (data) VALUES (?)", (f"data_{i}",))
        conn.commit()

        cursor.execute("DELETE FROM test_table WHERE id % 2 = 0")
        conn.commit()

        size_before = temp_db_path.stat().st_size

        conn.execute("VACUUM")
        conn.commit()

        size_after = temp_db_path.stat().st_size

        assert size_after <= size_before

        conn.close()

    def test_hotkey_tracking(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS hotkeys (
                hotkey TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """
        )

        hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        now = datetime.now(timezone.utc).isoformat() + "Z"

        cursor.execute(
            """
            INSERT OR IGNORE INTO hotkeys (hotkey, first_seen, last_seen)
            VALUES (?, ?, ?)
        """,
            (hotkey, now, now),
        )
        conn.commit()

        new_time = datetime.now(timezone.utc).isoformat() + "Z"
        cursor.execute(
            """
            UPDATE hotkeys
            SET last_seen = ?
            WHERE hotkey = ?
        """,
            (new_time, hotkey),
        )
        conn.commit()

        cursor.execute("SELECT last_seen FROM hotkeys WHERE hotkey = ?", (hotkey,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == new_time

        conn.close()


class TestDatabasePerformance:
    @pytest.fixture
    def temp_db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    def test_batch_insert_performance(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cache (
                hotkey TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        import time

        start = time.time()

        hotkeys = [
            f"5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694t{i}" for i in range(1000)
        ]
        now = datetime.now(timezone.utc).isoformat() + "Z"

        for hotkey in hotkeys:
            cursor.execute(
                """
                INSERT INTO validation_cache (hotkey, data_json, timestamp)
                VALUES (?, ?, ?)
            """,
                (hotkey, json.dumps({"hotkey": hotkey}), now),
            )

        conn.commit()
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Batch insert took {elapsed}s, expected < 5.0s"

        conn.close()

    def test_query_performance_with_index(self, temp_db_path):
        conn = get_or_create_database(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_cache (
                hotkey TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_validation_cache_timestamp
            ON validation_cache(timestamp)
        """
        )

        hotkeys = [
            f"5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694t{i}" for i in range(100)
        ]
        now = datetime.now(timezone.utc)

        for i, hotkey in enumerate(hotkeys):
            timestamp = (now - timedelta(days=i % 10)).isoformat() + "Z"
            cursor.execute(
                """
                INSERT INTO validation_cache (hotkey, data_json, timestamp)
                VALUES (?, ?, ?)
            """,
                (hotkey, json.dumps({"hotkey": hotkey}), timestamp),
            )

        conn.commit()

        import time

        start = time.time()

        seven_days_ago = (now - timedelta(days=7)).isoformat() + "Z"
        cursor.execute(
            """
            SELECT hotkey FROM validation_cache
            WHERE timestamp > ?
        """,
            (seven_days_ago,),
        )

        results = cursor.fetchall()
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Query took {elapsed}s, expected < 0.1s"
        assert len(results) > 0

        conn.close()
