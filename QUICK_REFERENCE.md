# WaHooNet Local Net Quick Reference

## Wallet Information

**Wallet Passwords:** `testnet`

**Wallets:**
- `test-validator` - Validator wallet
- `test-miner` - Miner wallet

**Location:** `~/.bittensor/wallets/`

## Network Configuration

Local net works **exactly like testnet**, but use:
- `--network local` OR
- `--network ws://127.0.0.1:9945` (or `:9944`)

## Common Commands

### Check Local Chain Status
```bash
docker ps | grep local_chain
```

### Start Local Chain (Persistent Setup)

**If container doesn't exist, create it:**
```bash
docker run -d \
  --name local_chain \
  --restart unless-stopped \
  -p 9944:9944 -p 9945:9945 \
  -v subtensor_data:/data \
  ghcr.io/opentensor/subtensor-localnet:devnet-ready \
  False \
  --base-path /data
```

**If container exists, just start it:**
```bash
docker start local_chain
```

**⚠️ IMPORTANT:** 
- Use `docker stop local_chain` and `docker start local_chain`
- **DO NOT** use `docker rm` or you'll lose wallets and subnet setup!

### List Subnets on Local Net
```bash
cd ~/wahoonet
source .venv/bin/activate
btcli subnet list --network local
# OR
btcli subnet list --network ws://127.0.0.1:9945
```

### Register Validator
```bash
btcli wallet register \
  --wallet.name test-validator \
  --wallet.hotkey default \
  --netuid <netuid> \
  --network local
```

### Register Miner
```bash
btcli wallet register \
  --wallet.name test-miner \
  --wallet.hotkey default \
  --netuid <netuid> \
  --network local
```

### Run Validator (Quick Script)
```bash
cd ~/wahoonet
./run_local_validator.sh <netuid>
```

### Run Miner (Quick Script)
```bash
cd ~/wahoonet
./run_local_miner.sh <netuid>
```

### Run Validator (Manual)
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m wahoo.validator.validator \
  --wallet.name test-validator \
  --wallet.hotkey default \
  --netuid <netuid> \
  --network local
```

### Run Miner (Manual)
```bash
cd ~/wahoonet
source .venv/bin/activate
python -m wahoo.miner.miner \
  --wallet.name test-miner \
  --wallet.hotkey default \
  --netuid <netuid> \
  --network local
```

### Check Wallet Balance
```bash
btcli wallet balance \
  --wallet.name test-validator \
  --network local
```

### Check Metagraph
```bash
btcli metagraph show \
  --netuid <netuid> \
  --network local
```

## API Testing Notes

When testing API stuff with wahoo:
- Make sure the local chain is running
- Validator/miner should be connected to local net
- API endpoints should point to local/test endpoints if needed

## Troubleshooting

**Docker not running:**
```bash
sudo systemctl start docker
```

**Check if local chain is accessible:**
```bash
curl http://127.0.0.1:9944
```

**View container logs (follow mode):**
```bash
docker logs -f local_chain
```

**Stop/Start container (keeps data):**
```bash
docker stop local_chain
docker start local_chain
```

**Check if container exists:**
```bash
docker ps -a | grep local_chain
```

**Check persistent volume:**
```bash
docker volume ls | grep subtensor_data
```

**⚠️ REMEMBER:** Never remove the container or volume - use stop/start only!
