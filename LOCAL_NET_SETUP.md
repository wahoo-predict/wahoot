# WaHooNet Local Bittensor Network Setup Guide

This guide helps you set up and test WaHooNet on a local Bittensor network.

## Quick Status Check

Run the verification script:
```bash
cd ~/wahoonet
bash check_local_net.sh
```

## Setup Steps

### 1. Docker Setup (Required)

Docker is **required** to run the local Subtensor blockchain. Your coworker may have set this up, but you need to verify.

**Check if Docker is installed:**
```bash
docker --version
```

**Start Docker daemon (if not running):**
```bash
sudo systemctl start docker
# Or on some systems:
sudo service docker start
```

### 2. Pull Subtensor Docker Image

If the image isn't already pulled:
```bash
docker pull ghcr.io/opentensor/subtensor-localnet:devnet-ready
```

### 3. Start Local Subtensor Chain (Persistent Setup)

**IMPORTANT:** Use this persistent setup to keep your wallets and subnet configuration across restarts.

**First, check if container already exists:**
```bash
docker ps -a | grep local_chain
```

**If container doesn't exist, create it with persistent volume:**
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

**If container already exists, just start it:**
```bash
docker start local_chain
```

**⚠️ CRITICAL WARNING:** 
- **DO NOT** remove the container (`docker rm local_chain`) or the volume
- **DO NOT** use `--rm` flag
- If you remove them, you'll need to set up wallets and local subnet all over again!
- Use `docker stop local_chain` and `docker start local_chain` instead

**View logs:**
```bash
docker logs -f local_chain
```

**For more details, see:** https://docs.learnbittensor.org/local-build/create-subnet

### 4. Verify Local Chain is Running

Check if the container is running:
```bash
docker ps | grep local_chain
```

Verify connectivity:
```bash
cd ~/wahoonet
source .venv/bin/activate
btcli subnet list --network ws://127.0.0.1:9944
```

### 5. Configure WaHooNet for Local Net

When running your validator/miner, make sure to use the `local` network:

```bash
# For validator
python -m wahoo.validator.validator --network local --netuid <netuid>

# Or set in your config
export BT_SUBTENSOR_NETWORK=local
export BT_SUBTENSOR_CHAIN_ENDPOINT=ws://127.0.0.1:9944
```

## Troubleshooting

### Docker daemon not running
```bash
sudo systemctl start docker
sudo systemctl enable docker  # Enable on boot
```

### Docker container not starting
- Check Docker daemon: `sudo systemctl status docker`
- Check ports: `netstat -tuln | grep 9944`
- View logs: `docker logs local_chain`

### Cannot connect to local chain
- Verify container is running: `docker ps`
- Check firewall settings
- Try: `curl http://127.0.0.1:9944`

### btcli not found
- Activate virtual environment: `source ~/wahoonet/.venv/bin/activate`
- Install: `pip install bittensor`

## Useful Commands

**Stop local chain (keeps data):**
```bash
docker stop local_chain
```

**Start local chain:**
```bash
docker start local_chain
```

**View container logs (follow mode):**
```bash
docker logs -f local_chain
```

**Check container status:**
```bash
docker ps -a | grep local_chain
```

**Check persistent volume:**
```bash
docker volume ls | grep subtensor_data
```

**⚠️ REMEMBER:** Use `stop`/`start`, NOT `rm` - removing the container will lose your setup!
