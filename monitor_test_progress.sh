#!/bin/bash
# Monitor test progress in real-time
# Shows key metrics from validator logs

cd ~/wahoonet

echo "======================================================================"
echo "TEST PROGRESS MONITOR"
echo "======================================================================"
echo "Press Ctrl+C to stop"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LOG_FILE="${1:-validator.log}"

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    exit 1
fi

tail -f "$LOG_FILE" | while read line; do
    # Highlight important events
    if echo "$line" | grep -q "✓✓✓ WEIGHTS SET SUCCESSFULLY"; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}$line${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    elif echo "$line" | grep -q "Queried.*miners"; then
        echo -e "${GREEN}→${NC} $line"
    elif echo "$line" | grep -q "Rewards sum: 1.000000"; then
        echo -e "${GREEN}→${NC} $line"
    elif echo "$line" | grep -q "EMA Scoring"; then
        echo -e "${BLUE}→${NC} $line"
    elif echo "$line" | grep -q "Setting weights on blockchain"; then
        echo -e "${YELLOW}→${NC} $line"
    elif echo "$line" | grep -qE "Error|Failed|Exception"; then
        echo -e "${YELLOW}⚠${NC} $line"
    fi
done

