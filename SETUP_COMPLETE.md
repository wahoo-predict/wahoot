# Local Net Setup Complete - Ready to Test!

## Wallets Configured

✅ **Validator:**
- Wallet: `test-validator`
- Hotkey: `default`
- Balance: 100,000 TAO

✅ **Miners (3 total):**
- Miner 1: `test-miner/default`
- Miner 2: `test-miner/miner2`
- Miner 3: `test-miner/miner3`
- Balance: 100,000 TAO each

## Step-by-Step Testing

### Step 1: Register All Wallets

```bash
cd ~/wahoonet
source .venv/bin/activate
python register_all_wallets.py
```

This will register:
- 1 validator (test-validator/default)
- 3 miners (test-miner with 3 different hotkeys)

**When prompted:**
- Enter password: `testnet` (for each wallet)

### Step 2: Start Testing (3 Terminals)

#### Terminal 1 - Mock API Server
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m tests.mock_wahoo_api
```

#### Terminal 2 - 3 Miners
```bash
cd ~/wahoonet
./run_3_miners.sh 1
```

This starts all 3 miners with different hotkeys.

#### Terminal 3 - Validator
```bash
cd ~/wahoonet
./run_local_validator.sh 1
```

Or manually:
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m wahoo.validator.validator \
    --wallet.name test-validator \
    --wallet.hotkey default \
    --netuid 1 \
    --chain-endpoint ws://127.0.0.1:9945 \
    --loop-interval 10 \
    --wahoo-api-url http://127.0.0.1:8000 \
    --wahoo-validation-endpoint http://127.0.0.1:8000/api/v2/event/bittensor/statistics \
    --use-validator-db
```

### Step 3: Verify Everything Works

**Watch Terminal 3 (Validator) for:**
- `[2/9] Getting active UIDs...` → Should show "Found 3 active UIDs"
- `[6/9] Querying miners...` → Should query all 3 miners
- `[7/9] Computing weights...` → Should compute weights for all 3
- `[9/9] Setting weights...` → Should set weights successfully

**After 10+ iterations, verify database:**
```bash
python verify_database.py
```

Should show:
- 3 EMA scores (one per miner hotkey)
- Cached validation data
- Database growing with iterations

## Quick Test (Automated)

Or use the automated full cycle test:

```bash
cd ~/wahoonet
./test_full_cycle.sh 1 15 5 3
```

This will:
- Start 3 miners automatically
- Run validator for 15 iterations
- Verify all steps
- Check database

## What to Expect

✅ **Validator should:**
- Detect all 3 miners in metagraph
- Query all 3 miners successfully
- Compute weights for all 3
- Set weights on blockchain
- Store EMA scores in database

✅ **Database should:**
- Contain 3 EMA scores (one per miner)
- Show scores updating over iterations
- Persist data across restarts

✅ **All 9 steps should:**
- Complete successfully each iteration
- Run 10+ times without crashing
- Show proper weight cycles

## Troubleshooting

**If validator shows "0 active UIDs":**
- Make sure all miners are registered: `python register_all_wallets.py`
- Check miners are serving axons (look for "✓ Axon served on blockchain" in miner logs)

**If miners fail to serve axon:**
- Make sure they're registered on subnet
- Check they have sufficient balance for transaction fees

**If database is empty:**
- Make sure `--use-validator-db` flag is set
- Check validator is completing weight computation steps

## Success Criteria

Release ready when:
- ✅ Validator detects all 3 miners
- ✅ All 9 steps complete successfully
- ✅ 10+ iterations without crashes
- ✅ Database contains 3 EMA scores
- ✅ Weights set on blockchain
- ✅ Weight cycles working correctly

## Next Steps

Once local net testing passes:
1. Deploy to testnet
2. Register on testnet subnet
3. Monitor for 24-48 hours
4. Verify all functionality works on testnet
5. Deploy to mainnet (after successful testnet validation)

