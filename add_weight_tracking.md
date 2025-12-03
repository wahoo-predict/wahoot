# Adding Weight Tracking to Database

## Current State (Confirmed)

✅ **What IS saved:**
- EMA scores (`scoring_runs` table) - used to compute weights
- Validation data (`performance_snapshots` table) - cached from API

❌ **What is NOT saved:**
- Actual weights set on blockchain (the final rewards tensor)
- Transaction hashes from set_weights()
- Block numbers when weights were set
- Weight history over time

## Impact

**Cannot:**
- Query historical weight distributions
- Track which transactions succeeded/failed
- Audit what weights were set in the past
- Recover weight history after restart
- Debug weight setting issues

## Proposed Solution

Add a new table to track weight transactions:

```sql
CREATE TABLE IF NOT EXISTS weight_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,  -- ISO8601 timestamp
    block_number INTEGER,
    transaction_hash TEXT,
    netuid INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    
    -- Weight data (JSON)
    weights_json TEXT NOT NULL,  -- JSON: {uid: weight, ...}
    uids_json TEXT NOT NULL,    -- JSON: [uid1, uid2, ...]
    
    -- Metadata
    iteration_count INTEGER,
    error_message TEXT,
    
    -- Computed from weights_json
    total_weight REAL,  -- Should sum to ~1.0
    num_miners INTEGER
);

CREATE INDEX IF NOT EXISTS idx_weight_ts ON weight_transactions(ts DESC);
CREATE INDEX IF NOT EXISTS idx_weight_block ON weight_transactions(block_number DESC);
CREATE INDEX IF NOT EXISTS idx_weight_hash ON weight_transactions(transaction_hash);
```

## Implementation

Update `wahoo/validator/validator.py` after `set_weights_with_retry()`:

```python
if success:
    logger.info(f"✓ Weights set successfully. Transaction: {transaction_hash}")
    
    # Save weight transaction to database
    if validator_db:
        try:
            import json
            from datetime import datetime
            
            weights_dict = {int(uid): float(weight) for uid, weight in zip(active_uids, rewards)}
            current_block = subtensor.get_current_block() if hasattr(subtensor, 'get_current_block') else None
            
            validator_db.add_weight_transaction(
                block_number=current_block,
                transaction_hash=transaction_hash,
                netuid=netuid,
                success=True,
                weights_json=json.dumps(weights_dict),
                uids_json=json.dumps([int(uid) for uid in active_uids]),
                iteration_count=iteration_count,
            )
        except Exception as e:
            logger.warning(f"Failed to save weight transaction to DB: {e}")
else:
    # Log failed attempt
    if validator_db:
        try:
            validator_db.add_weight_transaction(
                netuid=netuid,
                success=False,
                weights_json=json.dumps({}),
                uids_json=json.dumps([int(uid) for uid in active_uids]),
                iteration_count=iteration_count,
                error_message="Failed to set weights",
            )
        except Exception as e:
            logger.warning(f"Failed to log failed weight transaction: {e}")
```

## Benefits

✅ Track weight history over time
✅ Audit what weights were actually set
✅ Debug weight setting issues
✅ Recover weight history after restart
✅ Query historical weight distributions
✅ Track transaction success/failure rates

## Migration

Add migration to `wahoo/validator/database/alembic/versions/` or update `schema.sql`.

