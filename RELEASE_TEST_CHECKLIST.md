# Release Test Checklist

## Pre-Testing Setup

- [ ] Local chain running (`./start_local_chain.sh`)
- [ ] Wallets registered on subnet (`python register_wallets.py`)
- [ ] Wallets have test tokens (from faucet or alice)
- [ ] Mock API server running (`python -m tests.mock_wahoo_api`)

## Critical Test Areas

### 1. Validator-Miner Connection ✅

**Tests:**
- [ ] Validator detects miner in metagraph
- [ ] Validator queries miner via dendrite
- [ ] Miner responds with valid WAHOOPredict synapse
- [ ] Communication works within 12s timeout

**How to verify:**
```bash
# Run validator and miner
./run_validator_miner_local.sh 1 10

# Check logs for:
# - "Found X active UIDs"
# - "[6/9] Querying miners..."
# - "Responded to query for <event_id>"
```

### 2. Main Loop (9 Steps) ✅

**Steps to verify:**
- [ ] [1/9] Sync metagraph
- [ ] [2/9] Get active UIDs
- [ ] [3/9] Extract hotkeys
- [ ] [4/9] Fetch validation data
- [ ] [5/9] Get event ID
- [ ] [6/9] Query miners
- [ ] [7/9] Compute weights (EMA scoring)
- [ ] [8/9] Calculate rewards
- [ ] [9/9] Set weights on blockchain

**How to verify:**
```bash
# Run validator and watch logs
./run_validator_miner_local.sh 1 10

# Each iteration should show all 9 steps
```

### 3. Database Operations ✅

**Tests:**
- [ ] Database auto-creates
- [ ] EMA scores persist across iterations
- [ ] Cache fallback works
- [ ] Data persists across restarts

**How to verify:**
```bash
# After running validator for several iterations
python verify_database.py

# Should show:
# - EMA scores in database
# - Cached validation data
# - Database file exists
```

### 4. Scoring & Weights ✅

**Tests:**
- [ ] EMAVolumeScorer computes weights
- [ ] Previous scores loaded from DB
- [ ] Weights normalized (sum to 1.0)
- [ ] Weights set on blockchain successfully

**How to verify:**
```bash
# Run full cycle test
./test_full_cycle.sh 1 15 5 3

# Check logs for:
# - "Computing weights..."
# - "Setting weights..."
# - "Weights set successfully"
```

### 5. Error Handling ✅

**Tests:**
- [ ] Handles miner disconnection
- [ ] Handles API timeouts
- [ ] Handles empty data
- [ ] Continues after errors (doesn't crash)

**How to verify:**
```bash
# Run validator, then stop/start miners
# Validator should continue without crashing
```

### 6. End-to-End ✅

**Tests:**
- [ ] Full loop completes successfully
- [ ] Runs 10+ iterations without crashing
- [ ] Weights update on blockchain
- [ ] Database accumulates data over time

**How to verify:**
```bash
# Run comprehensive test
./test_full_cycle.sh 1 15 5 3

# Then verify database
python verify_database.py
```

## Multiple Miners Test

**Setup:**
- [ ] Register multiple miners (or use same wallet for testing)
- [ ] Start multiple miner instances
- [ ] Run validator

**Verify:**
- [ ] Validator detects all active miners
- [ ] Queries all miners successfully
- [ ] Computes weights for all miners
- [ ] Weights sum to 1.0

## Weight Cycle Verification

**After running 10+ iterations:**
```bash
# Check database
python verify_database.py

# Should show:
# - Multiple EMA scores (one per miner)
# - Scores updated over time
# - Database growing with iterations
```

## Scoring Cycle Verification

**Check logs for:**
- [ ] Each iteration computes new scores
- [ ] Previous scores loaded from DB
- [ ] EMA smoothing applied correctly
- [ ] Scores persist between iterations

## Success Criteria

Release ready when:
- ✅ All critical path items pass
- ✅ Validator runs 10+ iterations without crashes
- ✅ Weights successfully set on blockchain
- ✅ Validator and miner communicate successfully
- ✅ Database contains EMA scores
- ✅ Multiple miners work correctly
- ✅ Weight cycles complete successfully

## Quick Test Commands

```bash
# Full comprehensive test
./test_full_cycle.sh 1 15 5 3

# Verify database after test
python verify_database.py

# Check individual components
./run_local_net_tests.sh  # Unit tests
./run_validator_miner_local.sh 1 10  # Manual test
```

