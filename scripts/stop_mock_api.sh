#!/bin/bash
# Stop mock API server

if [ -f ".mock_api.pid" ]; then
    PID=$(cat .mock_api.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping mock API server (PID: $PID)..."
        kill $PID
        rm .mock_api.pid
        echo "✅ Server stopped"
    else
        echo "Server not running (PID file exists but process not found)"
        rm .mock_api.pid
    fi
else
    echo "No PID file found. Server may not be running."
    echo "Try: pkill -f mock_api_server.py"
fi

