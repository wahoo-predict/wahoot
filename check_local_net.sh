#!/bin/bash

# WaHooNet Local Bittensor Network Setup Checker
# This script verifies your local net setup and provides instructions

set -e

echo "=========================================="
echo "WaHooNet Local Bittensor Network Checker"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✓${NC} Docker is installed: $DOCKER_VERSION"
else
    echo -e "${RED}✗${NC} Docker is NOT installed"
    echo "   Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker daemon is running
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker daemon is running"
else
    echo -e "${RED}✗${NC} Docker daemon is NOT running"
    echo "   Start Docker: sudo systemctl start docker"
    exit 1
fi

# Check for Subtensor Docker image
echo ""
echo "2. Checking for Subtensor Docker image..."
if docker images | grep -q "subtensor-localnet"; then
    echo -e "${GREEN}✓${NC} Subtensor Docker image found"
    docker images | grep "subtensor-localnet"
else
    echo -e "${YELLOW}⚠${NC} Subtensor Docker image NOT found"
    echo "   You need to pull it with:"
    echo "   docker pull ghcr.io/opentensor/subtensor-localnet:devnet-ready"
fi

# Check for Subtensor container (running or stopped)
echo ""
echo "3. Checking for Subtensor container..."
if docker ps -a | grep -q "local_chain"; then
    if docker ps | grep -q "local_chain"; then
        echo -e "${GREEN}✓${NC} Subtensor container is running"
        docker ps | grep "local_chain"
    else
        echo -e "${YELLOW}⚠${NC} Subtensor container exists but is NOT running"
        echo "   Start it with: docker start local_chain"
    fi
    # Check for persistent volume
    if docker volume ls | grep -q "subtensor_data"; then
        echo -e "${GREEN}✓${NC} Persistent volume 'subtensor_data' exists"
    else
        echo -e "${YELLOW}⚠${NC} Persistent volume not found (container may be using old setup)"
    fi
else
    echo -e "${RED}✗${NC} Subtensor container does NOT exist"
    echo "   Create it with persistent volume:"
    echo "   docker run -d \\"
    echo "     --name local_chain \\"
    echo "     --restart unless-stopped \\"
    echo "     -p 9944:9944 -p 9945:9945 \\"
    echo "     -v subtensor_data:/data \\"
    echo "     ghcr.io/opentensor/subtensor-localnet:devnet-ready \\"
    echo "     False \\"
    echo "     --base-path /data"
    echo ""
    echo "   See: https://docs.learnbittensor.org/local-build/create-subnet"
fi

# Check if local chain is accessible
echo ""
echo "4. Checking local chain connectivity..."
if command -v curl &> /dev/null; then
    if curl -s http://127.0.0.1:9944 &> /dev/null || curl -s http://127.0.0.1:9945 &> /dev/null; then
        echo -e "${GREEN}✓${NC} Local chain is accessible on port 9944 or 9945"
    else
        echo -e "${YELLOW}⚠${NC} Cannot connect to local chain (container may not be running)"
    fi
else
    echo -e "${YELLOW}⚠${NC} curl not available, skipping connectivity check"
fi

# Check btcli
echo ""
echo "5. Checking btcli availability..."
if command -v btcli &> /dev/null; then
    echo -e "${GREEN}✓${NC} btcli found in PATH"
elif [ -d "$HOME/wahoonet/.venv" ]; then
    if source "$HOME/wahoonet/.venv/bin/activate" && command -v btcli &> /dev/null; then
        echo -e "${GREEN}✓${NC} btcli found in virtual environment"
    else
        echo -e "${YELLOW}⚠${NC} btcli not found, but virtual environment exists"
        echo "   Install with: pip install bittensor"
    fi
else
    echo -e "${YELLOW}⚠${NC} btcli not found in PATH"
    echo "   Install with: pip install bittensor"
fi

# Check Bittensor wallets
echo ""
echo "6. Checking Bittensor wallets..."
if [ -d "$HOME/.bittensor/wallets" ]; then
    WALLET_COUNT=$(ls -d "$HOME/.bittensor/wallets"/*/ 2>/dev/null | wc -l)
    echo -e "${GREEN}✓${NC} Bittensor wallets directory exists"
    echo "   Found $WALLET_COUNT wallet(s):"
    ls -1 "$HOME/.bittensor/wallets" 2>/dev/null | sed 's/^/     - /' || echo "     (none)"
else
    echo -e "${YELLOW}⚠${NC} Bittensor wallets directory not found at ~/.bittensor/wallets"
fi

# Check WaHooNet setup
echo ""
echo "7. Checking WaHooNet setup..."
if [ -d "$HOME/wahoonet" ]; then
    echo -e "${GREEN}✓${NC} WaHooNet directory exists"
    if [ -f "$HOME/wahoonet/.venv/bin/activate" ]; then
        echo -e "${GREEN}✓${NC} Virtual environment exists"
    else
        echo -e "${YELLOW}⚠${NC} Virtual environment not found"
    fi
else
    echo -e "${RED}✗${NC} WaHooNet directory not found"
fi

# Summary and next steps
echo ""
echo "=========================================="
echo "Summary & Next Steps"
echo "=========================================="
echo ""

# Check if everything is ready
READY=true

if ! docker ps | grep -q "local_chain"; then
    READY=false
    if docker ps -a | grep -q "local_chain"; then
        echo -e "${YELLOW}⚠${NC} Container exists but is stopped. Start it with:"
        echo "   docker start local_chain"
    else
        echo -e "${YELLOW}⚠${NC} To create the local Subtensor chain (persistent setup):"
        echo "   docker run -d \\"
        echo "     --name local_chain \\"
        echo "     --restart unless-stopped \\"
        echo "     -p 9944:9944 -p 9945:9945 \\"
        echo "     -v subtensor_data:/data \\"
        echo "     ghcr.io/opentensor/subtensor-localnet:devnet-ready \\"
        echo "     False \\"
        echo "     --base-path /data"
        echo ""
        echo "   ⚠️  IMPORTANT: Use stop/start, NOT rm - removing loses your setup!"
    fi
    echo ""
fi

if ! docker images | grep -q "subtensor-localnet"; then
    READY=false
    echo -e "${YELLOW}⚠${NC} To pull the Subtensor image:"
    echo "   docker pull ghcr.io/opentensor/subtensor-localnet:devnet-ready"
    echo ""
fi

if [ "$READY" = true ]; then
    echo -e "${GREEN}✓${NC} Your local net appears to be set up!"
    echo ""
    echo "To verify the local chain is working:"
    echo "  cd ~/wahoonet"
    echo "  source .venv/bin/activate"
    echo "  btcli subnet list --network ws://127.0.0.1:9944"
    echo ""
    echo "To test WaHooNet on local net:"
    echo "  # Make sure your validator/miner is configured for 'local' network"
    echo "  # Check your config or use: --network local"
else
    echo -e "${YELLOW}⚠${NC} Some setup steps are needed (see above)"
fi

echo ""
echo "For more info, see: https://docs.bittensor.com"

