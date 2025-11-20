#!/bin/bash
# Test runner for localnet testing
# Orchestrates the full test: setup, registration, and running validator/miners

set -e

echo "=========================================="
echo "WaHoo Predict - Localnet Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."
if ! command -v btcli &> /dev/null; then
    echo -e "${RED}ERROR: btcli not found${NC}"
    echo "Please install bittensor: pip install bittensor"
    exit 1
fi

if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}ERROR: Please run from wahoonet project root${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Configuration
NETUID=${NETUID:-1}
NETWORK=${NETWORK:-local}
NUM_MINERS=${NUM_MINERS:-3}

echo "Test Configuration:"
echo "  Network: $NETWORK"
echo "  Subnet UID: $NETUID"
echo "  Number of miners: $NUM_MINERS"
echo ""

read -p "Continue with localnet test? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Step 1: Setup
echo ""
echo -e "${YELLOW}[Step 1/5] Setting up localnet...${NC}"
./scripts/setup_localnet.sh || {
    echo -e "${RED}Setup failed${NC}"
    exit 1
}

# Step 2: Create wallets
echo ""
echo -e "${YELLOW}[Step 2/5] Creating wallets...${NC}"
./scripts/create_wallets.sh || {
    echo -e "${RED}Wallet creation failed${NC}"
    exit 1
}

# Step 3: Register wallets
echo ""
echo -e "${YELLOW}[Step 3/5] Registering wallets on subnet...${NC}"
NETUID=$NETUID ./scripts/register_localnet.sh || {
    echo -e "${RED}Registration failed${NC}"
    exit 1
}

# Step 4: Instructions for manual testing
echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps (run in separate terminals):"
echo ""
echo -e "${YELLOW}Terminal 1 - Validator:${NC}"
echo "  cd ~/wahoonet"
echo "  NETUID=$NETUID NETWORK=$NETWORK ./scripts/run_validator.sh"
echo ""
echo -e "${YELLOW}Terminal 2 - Miner 1:${NC}"
echo "  cd ~/wahoonet"
echo "  NETUID=$NETUID NETWORK=$NETWORK ./scripts/run_miner.sh miner1"
echo ""
if [ "$NUM_MINERS" -ge 2 ]; then
    echo -e "${YELLOW}Terminal 3 - Miner 2:${NC}"
    echo "  cd ~/wahoonet"
    echo "  NETUID=$NETUID NETWORK=$NETWORK ./scripts/run_miner.sh miner2"
    echo ""
fi
if [ "$NUM_MINERS" -ge 3 ]; then
    echo -e "${YELLOW}Terminal 4 - Miner 3:${NC}"
    echo "  cd ~/wahoonet"
    echo "  NETUID=$NETUID NETWORK=$NETWORK ./scripts/run_miner.sh miner3"
    echo ""
fi
echo ""
echo -e "${GREEN}Testing Tips:${NC}"
echo "  - Watch validator logs for weight computation"
echo "  - Check miner logs for query responses"
echo "  - Validator should query miners every ~100s"
echo "  - Weights should be set on-chain after each loop"
echo ""

