import pytest
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Generator

from wahoo.validator.database.core import ValidatorDB


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test_validator.db"


@pytest.fixture
def validator_db(db_path: Path) -> Generator[ValidatorDB, None, None]:
    """Initialize ValidatorDB with a temporary path."""
    db = ValidatorDB(db_path=db_path)
    yield db


def test_cache_validation_data(validator_db: ValidatorDB):
    """Test caching and retrieving validation data."""
    hotkey = "test_hotkey_1"
    data = {
        "hotkey": hotkey,
        "performance": {
            "total_volume_usd": 1000.0,
            "trade_count": 5,
            "realized_profit_usd": 50.0,
            "unrealized_profit_usd": 20.0,
            "win_rate": 0.6,
            "total_fees_paid_usd": 10.0,
            "open_positions_count": 2,
            "referral_count": 1,
            "referral_volume_usd": 100.0,
        },
    }

    validator_db.cache_validation_data(hotkey, data)

    cached = validator_db.get_cached_validation_data([hotkey])
    assert len(cached) == 1
    assert cached[0]["hotkey"] == hotkey
    assert cached[0]["performance"]["total_volume_usd"] == 1000.0
    assert cached[0]["performance"]["referral_count"] == 1


def test_ema_score_persistence(validator_db: ValidatorDB):
    """Test saving and retrieving EMA scores."""
    scores_v1 = {"miner1": 100.0, "miner2": 50.0}

    # Save initial scores
    validator_db.add_scoring_run(scores_v1, reason="epoch_1")

    latest = validator_db.get_latest_scores()
    assert latest["miner1"] == 100.0
    assert latest["miner2"] == 50.0

    # Update scores
    scores_v2 = {"miner1": 110.0, "miner2": 45.0, "miner3": 10.0}  # New miner

    # Sleep briefly to ensure timestamp difference if running fast
    time.sleep(0.1)
    validator_db.add_scoring_run(scores_v2, reason="epoch_2")

    latest_updated = validator_db.get_latest_scores()
    assert latest_updated["miner1"] == 110.0
    assert latest_updated["miner2"] == 45.0
    assert latest_updated["miner3"] == 10.0


def test_cleanup_old_cache(validator_db: ValidatorDB, db_path: Path):
    """Test cleanup of old cache entries."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    old_date = (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z"
    recent_date = datetime.utcnow().isoformat() + "Z"

    cursor.execute(
        "INSERT INTO performance_snapshots (hotkey, timestamp, total_volume_usd) VALUES (?, ?, ?)",
        ("old_miner", old_date, 100.0),
    )

    cursor.execute(
        "INSERT INTO performance_snapshots (hotkey, timestamp, total_volume_usd) VALUES (?, ?, ?)",
        ("new_miner", recent_date, 200.0),
    )

    conn.commit()
    conn.close()

    all_data = validator_db.get_cached_validation_data(
        ["old_miner", "new_miner"], max_age_days=30
    )
    assert len(all_data) == 2

    deleted = validator_db.cleanup_old_cache(max_age_days=7)
    assert deleted >= 1

    remaining = validator_db.get_cached_validation_data(
        ["old_miner", "new_miner"], max_age_days=30
    )
    assert len(remaining) == 1
    assert remaining[0]["hotkey"] == "new_miner"


def test_get_cached_validation_data_filtering(validator_db: ValidatorDB, db_path: Path):
    """Test that get_cached_validation_data respects max_age_days."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    five_days_ago = (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z"
    cursor.execute(
        "INSERT INTO performance_snapshots (hotkey, timestamp, total_volume_usd) VALUES (?, ?, ?)",
        ("miner_5d", five_days_ago, 500.0),
    )
    conn.commit()
    conn.close()

    res_7d = validator_db.get_cached_validation_data(["miner_5d"], max_age_days=7)
    assert len(res_7d) == 1

    res_3d = validator_db.get_cached_validation_data(["miner_5d"], max_age_days=3)
    assert len(res_3d) == 0


def test_empty_inputs(validator_db: ValidatorDB):
    """Test handling of empty inputs."""
    assert validator_db.get_cached_validation_data([]) == []

    validator_db.delete_cached_validation_data([])

    validator_db.add_scoring_run({})
    assert validator_db.get_latest_scores() == {}
