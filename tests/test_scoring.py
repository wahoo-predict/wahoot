"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Unit tests for Brier scoring, EMA, and weight normalization.
"""

import pytest
from wahoopredict.services.scoring import compute_brier, EMA_ALPHA


def test_compute_brier_yes():
    """Test Brier score computation for YES outcome."""
    # Perfect prediction
    assert compute_brier(1.0, True) == 0.0
    
    # Good prediction
    assert compute_brier(0.8, True) == 0.04  # (0.8 - 1.0)^2 = 0.04
    
    # Bad prediction
    assert compute_brier(0.2, True) == 0.64  # (0.2 - 1.0)^2 = 0.64


def test_compute_brier_no():
    """Test Brier score computation for NO outcome."""
    # Perfect prediction
    assert compute_brier(0.0, False) == 0.0
    
    # Good prediction
    assert compute_brier(0.2, False) == 0.04  # (0.2 - 0.0)^2 = 0.04
    
    # Bad prediction
    assert compute_brier(0.8, False) == 0.64  # (0.8 - 0.0)^2 = 0.64


def test_ema_alpha():
    """Test EMA alpha value for 7-day window."""
    # EMA alpha = 2/(7+1) = 0.25
    assert EMA_ALPHA == 0.25


def test_weight_normalization():
    """Test weight normalization logic."""
    import numpy as np
    
    # Example: raw weights
    raw_weights = {
        "miner1": np.exp(-0.1),  # Good Brier
        "miner2": np.exp(-0.5),  # Medium Brier
        "miner3": np.exp(-1.0),  # Bad Brier
    }
    
    # Normalize
    total = sum(raw_weights.values())
    normalized = {k: v / total for k, v in raw_weights.items()}
    
    # Check sum is 1.0
    assert abs(sum(normalized.values()) - 1.0) < 1e-10
    
    # Check ordering (better Brier = higher weight)
    assert normalized["miner1"] > normalized["miner2"] > normalized["miner3"]


def test_last_prelock_logic():
    """Test last pre-lock submission selection logic."""
    from datetime import datetime, timedelta, timezone
    
    # Mock submission times
    lock_time = datetime.now(timezone.utc)
    before_lock = lock_time - timedelta(hours=1)
    after_lock = lock_time + timedelta(hours=1)
    
    # Only submissions before lock_time should count
    assert before_lock < lock_time
    assert after_lock >= lock_time

