import math
from wahoo.validator.database.core import ValidatorDB


def test_score_validation_negative_values(tmp_path):
    """Test that negative scores are filtered out."""
    db_path = tmp_path / "test.db"
    db = ValidatorDB(db_path=db_path)

    scores = {"miner1": -100.0, "miner2": 50.0}
    db.add_scoring_run(scores, reason="test")

    loaded = db.get_latest_scores()

    assert "miner1" in loaded
    assert "miner2" in loaded

    validated = {}
    invalid_count = 0
    for hotkey, score in loaded.items():
        if score < 0:
            invalid_count += 1
            continue
        if not math.isfinite(score):
            invalid_count += 1
            continue
        validated[hotkey] = score

    assert invalid_count == 1
    assert "miner1" not in validated
    assert "miner2" in validated
    assert validated["miner2"] == 50.0


def test_score_validation_nan_inf(tmp_path):
    """Test that NaN and Inf scores are filtered out."""
    db_path = tmp_path / "test.db"
    ValidatorDB(db_path=db_path)

    raw_scores = {"miner1": float("nan"), "miner2": float("inf"), "miner3": 100.0}

    validated = {}
    invalid_count = 0
    for hotkey, score in raw_scores.items():
        if score < 0:
            invalid_count += 1
            continue
        if not math.isfinite(score):
            invalid_count += 1
            continue
        validated[hotkey] = score

    assert invalid_count == 2
    assert "miner1" not in validated
    assert "miner2" not in validated
    assert "miner3" in validated


def test_score_validation_all_valid(tmp_path):
    """Test that valid scores pass through."""
    db_path = tmp_path / "test.db"
    db = ValidatorDB(db_path=db_path)

    scores = {"miner1": 100.0, "miner2": 0.0, "miner3": 1500.5}
    db.add_scoring_run(scores, reason="test")

    loaded = db.get_latest_scores()

    validated = {}
    invalid_count = 0
    for hotkey, score in loaded.items():
        if score < 0:
            invalid_count += 1
            continue
        if not math.isfinite(score):
            invalid_count += 1
            continue
        validated[hotkey] = score

    assert invalid_count == 0
    assert len(validated) == 3
    assert validated["miner1"] == 100.0
    assert validated["miner2"] == 0.0
    assert validated["miner3"] == 1500.5
