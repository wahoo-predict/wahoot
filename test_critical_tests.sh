#!/bin/bash
# Critical Tests Runner for Localnet Testing
# Tests 1, 2, 3, 7 from the test plan

set -e

cd ~/wahoonet

echo "======================================================================"
echo "CRITICAL TESTS: Validator + 3 Miners on Localnet"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Test 1: Basic Connectivity
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Basic Connectivity (First Iteration)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Checking if validator and miners are running..."
VALIDATOR_RUNNING=$(pgrep -f "python.*validator" | wc -l)
MINER_COUNT=$(pgrep -f "python.*miner" | wc -l)

if [ "$VALIDATOR_RUNNING" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Validator is running"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Validator is NOT running"
    ((FAILED++))
fi

if [ "$MINER_COUNT" -ge 3 ]; then
    echo -e "${GREEN}✓${NC} Found $MINER_COUNT miners running (expected 3+)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Found only $MINER_COUNT miners (expected 3)"
    ((FAILED++))
fi

echo ""
echo "Checking recent validator logs for connectivity..."
if tail -100 validator.log 2>/dev/null | grep -q "Queried.*miners"; then
    QUERIED_COUNT=$(tail -100 validator.log | grep "Queried.*miners" | tail -1 | grep -oE "[0-9]+ miners" | grep -oE "[0-9]+" || echo "0")
    if [ "$QUERIED_COUNT" -ge 3 ]; then
        echo -e "${GREEN}✓${NC} Validator queried $QUERIED_COUNT miners"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Validator queried only $QUERIED_COUNT miners (expected 3)"
    fi
else
    echo -e "${YELLOW}⚠${NC} No 'Queried miners' log found yet"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Weight Distribution"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if tail -100 validator.log 2>/dev/null | grep -q "Rewards sum: 1.000000"; then
    echo -e "${GREEN}✓${NC} Weights sum to 1.0"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Weights do not sum to 1.0 (or not found in logs)"
    ((FAILED++))
fi

if tail -100 validator.log 2>/dev/null | grep -q "EMA Scoring.*3 miners"; then
    echo -e "${GREEN}✓${NC} EMA scoring for 3 miners found"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} EMA scoring log not found or not for 3 miners"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Database Operations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

DB_PATH="${WAHOO_DB_PATH:-validator.db}"
if [ -f "$DB_PATH" ]; then
    echo -e "${GREEN}✓${NC} Database file exists: $DB_PATH"
    ((PASSED++))
    
    SCORE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM scoring_runs;" 2>/dev/null || echo "0")
    if [ "$SCORE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Found $SCORE_COUNT scoring runs in database"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} No scoring runs found in database yet"
    fi
else
    echo -e "${RED}✗${NC} Database file not found: $DB_PATH"
    ((FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Weight Setting on Blockchain"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if tail -200 validator.log 2>/dev/null | grep -q "✓✓✓ WEIGHTS SET SUCCESSFULLY"; then
    echo -e "${GREEN}✓${NC} Weights set successfully on blockchain!"
    ((PASSED++))
    
    # Extract transaction hash if available
    TX_HASH=$(tail -200 validator.log | grep "Transaction Hash:" | tail -1 | sed 's/.*Transaction Hash: //' | cut -d' ' -f1)
    if [ -n "$TX_HASH" ]; then
        echo -e "${GREEN}✓${NC} Transaction hash: $TX_HASH"
    fi
else
    echo -e "${RED}✗${NC} Weights NOT set successfully (check tempo/blockchain)"
    echo "   Looking for: '✓✓✓ WEIGHTS SET SUCCESSFULLY ON BLOCKCHAIN ✓✓✓'"
    ((FAILED++))
fi

# Check for failures
if tail -100 validator.log 2>/dev/null | grep -q "Failed to set weights"; then
    FAIL_COUNT=$(tail -100 validator.log | grep -c "Failed to set weights" || echo "0")
    if [ "$FAIL_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}⚠${NC} Found $FAIL_COUNT 'Failed to set weights' messages"
        echo "   This is expected if tempo window hasn't opened yet"
    fi
fi

echo ""
echo "======================================================================"
echo "SUMMARY"
echo "======================================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed or are pending${NC}"
    echo "   This may be normal if validator just started or tempo window hasn't opened"
    exit 1
fi

