#!/bin/bash

# Monitor validator-miner communication logs
# Shows real-time communication between validator and miner

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

echo "=========================================="
echo "WaHooNet Communication Monitor"
echo "=========================================="
echo ""

if [ ! -d "$LOG_DIR" ]; then
    echo "No logs directory found. Run validator/miner first."
    exit 1
fi

# Find latest logs
VALIDATOR_LOG=$(ls -t "$LOG_DIR"/validator_*.log 2>/dev/null | head -1)
MINER_LOG=$(ls -t "$LOG_DIR"/miner_*.log 2>/dev/null | head -1)

if [ -z "$VALIDATOR_LOG" ] && [ -z "$MINER_LOG" ]; then
    echo "No log files found in $LOG_DIR"
    exit 1
fi

echo "Monitoring logs:"
[ -n "$VALIDATOR_LOG" ] && echo "  Validator: $VALIDATOR_LOG"
[ -n "$MINER_LOG" ] && echo "  Miner: $MINER_LOG"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Use multitail if available, otherwise tail
if command -v multitail &> /dev/null; then
    if [ -n "$VALIDATOR_LOG" ] && [ -n "$MINER_LOG" ]; then
        multitail -s 2 -cT ansi "$VALIDATOR_LOG" -cT ansi "$MINER_LOG"
    elif [ -n "$VALIDATOR_LOG" ]; then
        tail -f "$VALIDATOR_LOG"
    elif [ -n "$MINER_LOG" ]; then
        tail -f "$MINER_LOG"
    fi
else
    # Fallback: use tail with colors
    if [ -n "$VALIDATOR_LOG" ] && [ -n "$MINER_LOG" ]; then
        echo "Install 'multitail' for better multi-file monitoring"
        echo "For now, showing validator log (use another terminal for miner log)"
        tail -f "$VALIDATOR_LOG"
    elif [ -n "$VALIDATOR_LOG" ]; then
        tail -f "$VALIDATOR_LOG"
    elif [ -n "$MINER_LOG" ]; then
        tail -f "$MINER_LOG"
    fi
fi

