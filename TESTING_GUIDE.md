# WaHooNet Local Net Testing Guide

This guide covers comprehensive testing on Bittensor local net before testnet release.

## Overview

Testing follows the path: **localnet → testnet → mainnet**

We need to verify all critical paths work correctly on local net before deploying to testnet.

## Prerequisites

1. **Docker** - For running local Subtensor chain
2. **Local chain running** - Use `./start_local_chain.sh`
3. **Python environment** - Virtual environment with dependencies
4. **Wallets configured** - `test-validator` and `test-miner` wallets

## Quick Start

### 1. Start Local Chain

```bash
cd ~/wahoonet
./start_local_chain.sh
```

### 2. Run Comprehensive Tests

```bash
./run_local_net_tests.sh
```

This will:
- Start mock Wahoo API server
- Run all integration tests
- Provide test summary

### 3. Manual Testing

```bash
# Terminal 1: Start mock API server
python -m tests.mock_wahoo_api

# Terminal 2: Run validator
./run_local_validator.sh <netuid>

# Terminal 3: Run miner
./run_local_miner.sh <netuid>
```

## Critical Test Areas

### 1. Validator-Miner Connection ✅

**Tests:**
- Validator detects miner in metagraph
- Validator queries miner via dendrite
- Miner responds with valid WAHOOPredict synapse
- Communication works within 12s timeout

**Run:**
```bash
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_1_* -v
```

### 2. Main Loop (9 Steps) ✅

**Steps verified:**
1. Sync metagraph
2. Get active UIDs
3. Extract hotkeys
4. Fetch validation data
5. Get event ID
6. Query miners
7. Compute weights (EMA scoring)
8. Calculate rewards
9. Set weights on blockchain

**Run:**
```bash
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_2_* -v
```

### 3. Database Operations ✅

**Tests:**
- Database auto-creates
- EMA scores persist across iterations
- Cache fallback works
- Data persists across restarts

**Run:**
```bash
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_3_* -v
```

### 4. Scoring & Weights ✅

**Tests:**
- EMAVolumeScorer computes weights
- Previous scores loaded from DB
- Weights normalized (sum to 1.0)
- Weights set on blockchain successfully

**Run:**
```bash
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_4_* -v
```

### 5. Error Handling ✅

**Tests:**
- Handles miner disconnection
- Handles API timeouts
- Handles empty data
- Continues after errors (doesn't crash)

**Run:**
```bash
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_5_* -v
```

### 6. End-to-End ✅

**Tests:**
- Full loop completes successfully
- Runs 10+ iterations without crashing
- Weights update on blockchain
- Database accumulates data over time

**Run:**
```bash
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_6_* -v
```

## Mock API Server

The mock API server (`tests/mock_wahoo_api.py`) provides:

- **Validation endpoint**: `/api/v2/event/bittensor/statistics?hotkeys=<comma_separated>`
- **Active event endpoint**: `/events` (returns `active_event_id`)

**Start manually:**
```bash
python -m tests.mock_wahoo_api [port]
# Default port: 8000
```

**Environment variables:**
```bash
export WAHOO_API_URL="http://127.0.0.1:8000"
export WAHOO_VALIDATION_ENDPOINT="http://127.0.0.1:8000/api/v2/event/bittensor/statistics"
```

## Success Criteria

Release ready if:

- ✅ All critical path items pass
- ✅ Validator runs 10+ iterations without crashes
- ✅ Weights successfully set on blockchain
- ✅ Validator and miner communicate successfully

## Troubleshooting

### Local chain not running
```bash
docker ps | grep local_chain
# If not running:
./start_local_chain.sh
```

### Mock API server not responding
```bash
curl http://127.0.0.1:8000/events
# Should return JSON with active_event_id
```

### Tests failing
```bash
# Check logs
tail -f /tmp/mock_api.log

# Run with verbose output
pytest tests/test_local_net_integration.py -v -s
```

### Database issues
```bash
# Check database exists
ls -la validator.db

# Remove and recreate if needed (WARNING: loses data)
rm validator.db
python -m wahoo.validator.init
```

## Next Steps After Local Net Testing

Once all tests pass on local net:

1. **Deploy to testnet**
   - Register validator/miner on testnet
   - Configure for testnet network
   - Monitor for 24-48 hours

2. **Testnet validation**
   - Verify weights update correctly
   - Check reward distribution
   - Monitor for errors

3. **Mainnet deployment**
   - Only after successful testnet validation
   - Gradual rollout recommended

## Files Created

- `tests/mock_wahoo_api.py` - Mock API server
- `tests/test_local_net_integration.py` - Comprehensive integration tests
- `run_local_net_tests.sh` - Test runner script
- `TESTING_GUIDE.md` - This guide

## Additional Resources

- [Bittensor Local Net Docs](https://docs.learnbittensor.org/local-build/create-subnet)
- [WaHooNet README](README.md)
- [Local Net Setup Guide](LOCAL_NET_SETUP.md)

