# Test Execution Guide for Localnet

## Quick Start

### 1. Run Critical Tests
```bash
cd ~/wahoonet
./test_critical_tests.sh
```

### 2. Check Comprehensive Status
```bash
python3 check_test_status.py
```

## Test Execution Order

### Phase 1: Critical Tests (Must Pass)

1. **Start Everything**
   ```bash
   # Terminal 1: Start mock API
   python3 tests/mock_wahoo_api.py
   
   # Terminal 2: Start 3 miners
   ./run_multiple_miners.sh
   
   # Terminal 3: Start validator
   ./run_local_validator.sh
   ```

2. **Wait for First Iteration** (~2 minutes)
   - Watch validator logs
   - Should see: "✓ Queried 3 miners"
   - Should see: "✓ Rewards sum: 1.000000"

3. **Run Critical Test Checker**
   ```bash
   ./test_critical_tests.sh
   ```

4. **Check Detailed Status**
   ```bash
   python3 check_test_status.py
   ```

### Phase 2: Extended Testing

5. **Run for 10+ Iterations**
   - Let validator run for ~20 minutes
   - Monitor logs for errors
   - Check database growth

6. **Verify Weight Setting**
   - Watch for: "✓✓✓ WEIGHTS SET SUCCESSFULLY"
   - This may take 8-16 minutes due to tempo

7. **Test Error Handling**
   - Stop 1 miner mid-iteration
   - Verify validator continues
   - Restart miner
   - Verify it's queried again

## What to Look For

### ✅ Success Indicators

- **Logs show**: "✓ Queried 3 miners"
- **Logs show**: "✓ Rewards sum: 1.000000"
- **Logs show**: "✓✓✓ WEIGHTS SET SUCCESSFULLY ON BLOCKCHAIN ✓✓✓"
- **Database has**: Scoring runs for all 3 miners
- **No crashes**: Validator runs continuously

### ⚠️ Expected Warnings (OK)

- "Failed to set weights (will retry next iteration)" - Normal if tempo window hasn't opened
- "Error querying miners: object of type 'NoneType' has no len()" - Known issue, handled gracefully
- "too soon to commit weights" - Normal tempo restriction

### ❌ Red Flags (Need Fix)

- Validator crashes
- No miners queried after 5+ minutes
- Weights never set after 20+ minutes
- Database errors
- All weights are zero when they shouldn't be

## Monitoring Commands

```bash
# Watch validator logs in real-time
tail -f validator.log | grep -E "Queried|Rewards|WEIGHTS SET|Error|Failed"

# Check database
sqlite3 validator.db "SELECT COUNT(*) FROM scoring_runs;"
sqlite3 validator.db "SELECT hotkey, score, ts FROM scoring_runs ORDER BY ts DESC LIMIT 10;"

# Check process status
pgrep -f "python.*validator"
pgrep -f "python.*miner"

# Check for errors
grep -i "error\|exception\|traceback" validator.log | tail -20
```

## Troubleshooting

### Weights Not Setting

If weights haven't been set after 10+ minutes:

1. **Check tempo status**:
   ```bash
   ./check_tempo.sh
   ```

2. **Verify validator is trying**:
   ```bash
   tail -50 validator.log | grep "Setting weights"
   ```

3. **Wait longer**: On localnet, first commit can take 8-16 minutes

### Miners Not Responding

1. **Check miner logs**:
   ```bash
   tail -f miner*.log
   ```

2. **Verify miners are registered**:
   ```bash
   btcli wallet list --network ws://127.0.0.1:9945
   ```

3. **Restart miners** if needed

### Database Issues

1. **Check database exists**:
   ```bash
   ls -lh validator.db
   ```

2. **Check permissions**:
   ```bash
   sqlite3 validator.db "SELECT COUNT(*) FROM scoring_runs;"
   ```

3. **Backup and recreate if corrupted**:
   ```bash
   mv validator.db validator.db.backup
   # Restart validator to recreate
   ```

## Success Criteria Checklist

- [ ] All 3 miners running
- [ ] Validator running
- [ ] Validator queries all 3 miners
- [ ] Weights computed (sum to 1.0)
- [ ] Weights set on blockchain (transaction hash logged)
- [ ] Database persists scores
- [ ] Validator runs 10+ iterations without crashes
- [ ] Error handling works (tested with miner disconnection)

## Next Steps After Tests Pass

1. ✅ Document any issues found
2. ✅ Verify all critical tests pass
3. ✅ Run extended stability test (20+ iterations)
4. ✅ Prepare for testnet deployment

