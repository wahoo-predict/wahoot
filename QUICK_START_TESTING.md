# Quick Start: Testing on Local Net

## Prerequisites Checklist

- [x] Local chain running (`./start_local_chain.sh`)
- [x] Wallets configured (`test-validator`, `test-miner`)
- [x] Virtual environment activated
- [ ] Mock API server running (optional, for API testing)

## Quick Test: 10+ Iterations

**Single command to test everything:**
```bash
cd ~/wahoonet
./test_10_iterations.sh 1 12 5
```

This will:
- Start miner automatically
- Start validator
- Run 12 iterations (5-second intervals)
- Verify all steps complete
- Report success/failure

## Monitor Communication

**Watch logs in real-time:**
```bash
# Terminal 1: Run validator + miner
./run_validator_miner_local.sh 1 10

# Terminal 2: Monitor logs
./monitor_communication.sh
```

## What Gets Tested

### ✅ Unit Tests (Already Passing)
- All 12 integration tests pass
- Mocked components work correctly

### ✅ Real Integration Test (This Script)
- **Actual validator-miner communication**
- **Real blockchain interaction**
- **10+ iterations without crashes**
- **Database persistence**
- **Weight setting on blockchain**

## Expected Output

### Successful Test:
```
✓ SUCCESS: Completed 12 iterations (target: 12)

Test Results:
  ✓ Validator ran 12 iterations
  ✓ No crashes detected
  ✓ Ready for testnet!
```

### What You'll See:
1. Miner starts and waits for queries
2. Validator starts and begins loop
3. Each iteration shows all 9 steps:
   - [1/9] Syncing metagraph...
   - [2/9] Getting active UIDs...
   - [3/9] Extracting hotkeys...
   - [4/9] Fetching WAHOO validation data...
   - [5/9] Getting active event ID...
   - [6/9] Querying miners... ← **Communication happens here**
   - [7/9] Computing weights...
   - [8/9] Calculating rewards...
   - [9/9] Setting weights...
4. Iteration counter increments
5. Test completes after 10+ iterations

## Port Information

- **Miner Port**: 8091 (serves axon)
- **Validator**: No port needed (only queries)
- **Local Chain**: 9944, 9945 (WebSocket)
- **Mock API**: 8000 (HTTP)

## Next Steps After Success

1. ✅ All unit tests pass
2. ✅ 10+ iterations complete successfully
3. ✅ Ready for testnet deployment!

See `RELEASE_READINESS_CHECKLIST.md` for full checklist.

