#!/bin/bash
# Complete validator setup script
# Does everything needed before running the validator

set -e

echo "=========================================="
echo "WaHoo Predict Validator Setup"
echo "=========================================="
echo ""

# Check if we're in the project directory
if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: Please run this script from the wahoonet project root"
    exit 1
fi

# Step 1: Create virtual environment (if not exists)
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "[1/5] Virtual environment already exists"
fi

# Step 2: Activate virtual environment
echo ""
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"

# Step 3: Install package
echo ""
echo "[3/5] Installing package and dependencies..."
pip install -e ".[dev]" || pip install -e .
echo "✓ Package installed"

# Step 4: Initialize validator
echo ""
echo "[4/5] Initializing validator (database, dependencies, etc.)..."
wahoo-validator-init || python -m wahoo.validator.init
echo "✓ Validator initialized"

# Step 5: Check configuration
echo ""
echo "[5/5] Checking configuration..."
if [ ! -f ".env" ]; then
    echo "⚠ WARNING: .env file not found"
    echo ""
    echo "Create a .env file with:"
    echo "  NETUID=1"
    echo "  NETWORK=finney"
    echo "  WALLET_NAME=your_wallet"
    echo "  HOTKEY_NAME=your_hotkey"
    echo "  USE_VALIDATOR_DB=true"
    echo "  VALIDATOR_DB_PATH=validator.db"
    echo ""
else
    echo "✓ .env file found"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Register on subnet:"
echo "     btcli wallet register --netuid <netuid>"
echo ""
echo "  2. Start validator:"
echo "     python -m wahoo.validator.validator"
echo ""
echo "  3. Or use the run script:"
echo "     ./scripts/run_validator.sh"
echo ""

