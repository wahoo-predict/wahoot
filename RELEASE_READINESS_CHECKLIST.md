# WaHooNet Release Readiness Checklist

## Pre-Testnet Testing on Local Net

### Setup Complete ✅
- [x] Mock Wahoo API server created (`tests/mock_wahoo_api.py`)
- [x] Comprehensive integration tests (`tests/test_local_net_integration.py`)
- [x] Test runner script (`run_local_net_tests.sh`)
- [x] Local net setup scripts and documentation
- [x] Testing guide created

### Critical Tests (All 6 Areas)

#### 1. Validator-Miner Connection
- [ ] Validator detects miner in metagraph
- [ ] Validator queries miner via dendrite
- [ ] Miner responds with valid WAHOOPredict synapse
- [ ] Communication works within 12s timeout

#### 2. Main Loop (9 Steps)
- [ ] Step 1: Sync metagraph
- [ ] Step 2: Get active UIDs
- [ ] Step 3: Extract hotkeys
- [ ] Step 4: Fetch validation data
- [ ] Step 5: Get event ID
- [ ] Step 6: Query miners
- [ ] Step 7: Compute weights (EMA scoring)
- [ ] Step 8: Calculate rewards
- [ ] Step 9: Set weights on blockchain

#### 3. Database Operations
- [ ] Database auto-creates
- [ ] EMA scores persist across iterations
- [ ] Cache fallback works
- [ ] Data persists across restarts

#### 4. Scoring & Weights
- [ ] EMAVolumeScorer computes weights
- [ ] Previous scores loaded from DB
- [ ] Weights normalized (sum to 1.0)
- [ ] Weights set on blockchain successfully

#### 5. Error Handling
- [ ] Handles miner disconnection
- [ ] Handles API timeouts
- [ ] Handles empty data
- [ ] Continues after errors (doesn't crash)

#### 6. End-to-End
- [ ] Full loop completes successfully
- [ ] Runs 10+ iterations without crashing
- [ ] Weights update on blockchain
- [ ] Database accumulates data over time

### Success Criteria

Release ready when:
- ✅ All critical path items pass
- ✅ Validator runs 10+ iterations without crashes
- ✅ Weights successfully set on blockchain
- ✅ Validator and miner communicate successfully

### How to Run Tests

```bash
# Quick test run
./run_local_net_tests.sh

# Individual test areas
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_1_* -v
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_2_* -v
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_3_* -v
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_4_* -v
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_5_* -v
pytest tests/test_local_net_integration.py::TestLocalNetIntegration::test_6_* -v
```

### Manual Testing

1. Start local chain: `./start_local_chain.sh`
2. Start mock API: `python -m tests.mock_wahoo_api`
3. Run validator: `./run_local_validator.sh <netuid>`
4. Run miner: `./run_local_miner.sh <netuid>`
5. Monitor logs and verify behavior

### Next Steps After Local Net

1. **Testnet Deployment**
   - Register on testnet
   - Monitor for 24-48 hours
   - Verify all functionality

2. **Mainnet Deployment**
   - Only after successful testnet validation
   - Gradual rollout recommended
