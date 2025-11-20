#!/bin/bash
# Run validator simulation with mock API

set -e

echo "=========================================="
echo "WaHoo Validator Simulation"
echo "=========================================="
echo ""

# Configuration
MOCK_API_URL=${MOCK_API_URL:-http://localhost:8000}
NETUID=${NETUID:-1}
NETWORK=${NETWORK:-local}

# Check if mock API is running
if ! curl -s "$MOCK_API_URL/events" > /dev/null 2>&1; then
    echo "⚠️  WARNING: Mock API server not running!"
    echo "Start it first: ./scripts/start_mock_api.sh"
    echo ""
    read -p "Start mock API now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./scripts/start_mock_api.sh
        sleep 2
    else
        echo "Exiting. Start mock API first."
        exit 1
    fi
fi

echo "Configuration:"
echo "  Mock API: $MOCK_API_URL"
echo "  Network: $NETWORK"
echo "  Subnet UID: $NETUID"
echo ""

# Set environment variables
export WAHOO_API_URL=$MOCK_API_URL
export WAHOO_VALIDATION_ENDPOINT="$MOCK_API_URL/api/v2/event/bittensor/statistics"
export NETUID=$NETUID
export NETWORK=$NETWORK
export USE_VALIDATOR_DB=true
export VALIDATOR_DB_PATH=validator.db

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "Starting validator..."
echo "Press Ctrl+C to stop"
echo ""

# Run validator in mock mode
python -m wahoo.validator.validator \
    --netuid "$NETUID" \
    --network "$NETWORK" \
    --wahoo-api-url "$MOCK_API_URL" \
    --wahoo-validation-endpoint "$WAHOO_VALIDATION_ENDPOINT" \
    --use-validator-db \
    --loop-interval 30.0 \
    --log-level INFO \
    --mock

