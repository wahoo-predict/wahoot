#!/bin/bash
# Start mock API server in background

set -e

PORT=${MOCK_API_PORT:-8000}
HOST=${MOCK_API_HOST:-localhost}
DURATION=${MOCK_API_DURATION:-0}  # 0 = forever

echo "=========================================="
echo "Starting Mock WAHOO API Server"
echo "=========================================="
echo "Port: $PORT"
echo "Host: $HOST"
echo "Duration: ${DURATION}s (0 = forever)"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start server in background
python scripts/mock_api_server.py --port "$PORT" --host "$HOST" --duration "$DURATION" &
API_PID=$!

# Save PID to file
echo $API_PID > .mock_api.pid

echo "Mock API server started (PID: $API_PID)"
echo ""
echo "Test it:"
echo "  curl http://$HOST:$PORT/events"
echo "  curl 'http://$HOST:$PORT/api/v2/event/bittensor/statistics?hotkeys=5Dnh2o9x9kTRtfeF5g3W4uzfzWNeGD1EJo4aCtibAESzP2iE'"
echo ""
echo "Stop it:"
echo "  ./scripts/stop_mock_api.sh"
echo "  OR: kill $API_PID"
echo ""

# Wait a moment to ensure server started
sleep 2

# Test if server is running
if curl -s "http://$HOST:$PORT/events" > /dev/null 2>&1; then
    echo "✅ Server is running!"
else
    echo "⚠️  Server may not have started properly"
fi

