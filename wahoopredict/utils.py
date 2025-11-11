"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

Utility functions: xxhash manifest, time helpers.
"""

import xxhash
from datetime import datetime, timezone
from typing import Any, Dict


def compute_manifest_hash(data: Dict[str, Any]) -> str:
    """
    Compute xxhash manifest hash for submission data.
    
    Args:
        data: Dictionary containing submission data
        
    Returns:
        Hex-encoded xxhash hash
    """
    # Sort keys for deterministic hashing
    sorted_data = sorted(data.items())
    data_str = str(sorted_data)
    
    # Compute xxhash
    hash_obj = xxhash.xxh64()
    hash_obj.update(data_str.encode("utf-8"))
    
    return hash_obj.hexdigest()


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def is_before_lock(submitted_at: datetime, lock_time: datetime) -> bool:
    """
    Check if submission is before lock time.
    
    Args:
        submitted_at: Submission timestamp
        lock_time: Event lock time
        
    Returns:
        True if submitted_at < lock_time, False otherwise
    """
    return submitted_at < lock_time

