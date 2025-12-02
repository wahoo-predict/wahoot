# Monitoring Validator-Miner Communication

## Port Configuration

**Miner**: Uses port **8091** (hardcoded in `wahoo/miner/miner.py`)
- The miner serves an axon on this port
- Validators query this port via dendrite

**Validator**: Does NOT need a port
- Validators don't serve - they only query miners
- They use dendrite to connect to miner axons

## Viewing Logs

### Option 1: Real-time Monitoring

**Terminal 1 - Run validator + miner:**
```bash
cd ~/wahoonet
./run_validator_miner_local.sh <netuid> [loop_interval]
```

**Terminal 2 - Monitor communication:**
```bash
cd ~/wahoonet
./monitor_communication.sh
```

This shows real-time logs from both validator and miner.

### Option 2: View Log Files

Logs are saved to `~/wahoonet/logs/`:
```bash
# View validator log
tail -f ~/wahoonet/logs/validator_*.log

# View miner log
tail -f ~/wahoonet/logs/miner_*.log

# View both with multitail (if installed)
multitail ~/wahoonet/logs/validator_*.log ~/wahoonet/logs/miner_*.log
```

### Option 3: Manual Run (Separate Terminals)

**Terminal 1 - Mock API:**
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m tests.mock_wahoo_api
```

**Terminal 2 - Miner:**
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m wahoo.miner.miner \
    --wallet.name test-miner \
    --wallet.hotkey default \
    --netuid <netuid> \
    --network local
```

**Terminal 3 - Validator:**
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m wahoo.validator.validator \
    --wallet.name test-validator \
    --wallet.hotkey default \
    --netuid <netuid> \
    --network local \
    --loop-interval 10
```

## What to Look For in Logs

### Validator Logs
- `[1/9] Syncing metagraph...` - Step 1
- `[2/9] Getting active UIDs...` - Step 2
- `[3/9] Extracting hotkeys...` - Step 3
- `[4/9] Fetching WAHOO validation data...` - Step 4
- `[5/9] Getting active event ID...` - Step 5
- `[6/9] Querying miners...` - Step 6 (this is where communication happens!)
- `[7/9] Computing weights...` - Step 7
- `[8/9] Calculating rewards...` - Step 8
- `[9/9] Setting weights...` - Step 9
- `Starting main loop iteration` - New iteration starting

### Miner Logs
- `Responded to query for <event_id>` - Miner received and processed query
- `Generated prediction for <event_id>` - Prediction generated

### Communication Indicators
- Validator: `Querying X miners...` followed by responses
- Miner: `Responded to query...` messages
- Both should show successful communication within 12s timeout

## Testing 10+ Iterations

Run the dedicated test script:

```bash
cd ~/wahoonet
./test_10_iterations.sh <netuid> [iterations] [loop_interval]
```

Example:
```bash
# Test 12 iterations with 5-second intervals
./test_10_iterations.sh 1 12 5
```

This will:
1. Start miner in background
2. Start validator
3. Count iterations
4. Verify 10+ iterations complete successfully
5. Report results

## Troubleshooting

### No Communication
- Check miner is running: `ps aux | grep miner`
- Check miner port: `netstat -tuln | grep 8091`
- Check validator can see miner in metagraph

### Timeouts
- Check network connectivity
- Verify miner axon is properly started
- Check firewall settings

### Logs Not Appearing
- Check log directory exists: `ls -la ~/wahoonet/logs/`
- Verify write permissions
- Check disk space: `df -h`

## Port Conflicts

If port 8091 is already in use:
1. Find what's using it: `sudo lsof -i :8091`
2. Kill the process or change miner port (requires code change)
3. For multiple miners, each needs a different port

## Success Indicators

✅ **Validator-Miner Connection:**
- Validator logs show "Querying X miners..."
- Miner logs show "Responded to query..."
- No timeout errors

✅ **10+ Iterations:**
- Validator log shows "Starting main loop iteration" 10+ times
- No crashes or errors
- Weights being set successfully

✅ **All 9 Steps:**
- Each iteration shows all 9 steps completing
- No step failures

