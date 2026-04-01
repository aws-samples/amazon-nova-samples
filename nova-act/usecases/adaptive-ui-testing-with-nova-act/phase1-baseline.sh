#!/bin/bash

# Phase 1: Baseline Testing
# Tests original UI with both Playwright and Nova Act

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PHASE 1: Baseline Testing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Testing original UI (v1.0) with 5 fields:"
echo "  • First Name, Last Name, Student ID"
echo "  • Major, Enrollment Date"
echo ""
echo "Both frameworks should pass ✓"
echo ""

# Check if server is running
if ! curl -s http://localhost:8000 > /dev/null; then
    echo -e "${RED}Error: Application server not running${NC}"
    echo ""
    echo "Please start the server in another terminal:"
    echo "  cd sample-app"
    echo "  python3 -m http.server 8000"
    echo ""
    exit 1
fi

read -p "Press Enter to start testing..."
echo ""

#############################################
# TEST PLAYWRIGHT
#############################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing with Playwright${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd playwright-tests
PLAYWRIGHT_OUTPUT=$(npx playwright test tests/phase1_student.spec.js --reporter=line 2>&1)
PLAYWRIGHT_EXIT=$?
echo "$PLAYWRIGHT_OUTPUT"
cd ..

echo ""
echo -e "${YELLOW}Validating Playwright results...${NC}"

PLAYWRIGHT_VERIFIED=false
if echo "$PLAYWRIGHT_OUTPUT" | grep -q "1 passed"; then
    echo -e "${GREEN}✓ VERIFIED: Playwright test passed${NC}"
    PLAYWRIGHT_VERIFIED=true
elif echo "$PLAYWRIGHT_OUTPUT" | grep -qi "passed"; then
    echo -e "${GREEN}✓ VERIFIED: Playwright test passed${NC}"
    PLAYWRIGHT_VERIFIED=true
else
    echo -e "${RED}✗ WARNING: Could not verify Playwright success${NC}"
    echo -e "${RED}  Please review output above carefully${NC}"
fi

echo ""
read -p "Press Enter to continue to Nova Act tests..."
echo ""

#############################################
# TEST NOVA ACT
#############################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Testing with Nova Act${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd nova-act-tests

# Check authentication (IAM or API key)
if aws sts get-caller-identity &>/dev/null; then
    echo "Using IAM authentication"
elif [ -f ".env" ] && grep -q "NOVA_ACT_API_KEY=..*" .env 2>/dev/null; then
    echo "Using API key authentication"
else
    echo -e "${RED}✗ No Nova Act authentication configured${NC}"
    echo "Configure AWS IAM credentials (aws configure) or add API key to nova-act-tests/.env"
    cd ..
    exit 1
fi

source venv/bin/activate
NOVA_OUTPUT=$(pytest tests/test_runner.py::test_with_nova_act -k "NA-01" -v --tb=line --no-header --quiet 2>&1)
NOVA_EXIT=$?

# Show only relevant output (filter out pytest noise)
echo "$NOVA_OUTPUT" | grep -E "(✓|✗|Test|Error|Possible|PASSED|FAILED|passed|failed)" || echo "$NOVA_OUTPUT"

deactivate
cd ..

echo ""
echo -e "${YELLOW}Validating Nova Act results...${NC}"

NOVA_VERIFIED=false
if echo "$NOVA_OUTPUT" | grep -q "1 passed"; then
    echo -e "${GREEN}✓ VERIFIED: Nova Act test passed${NC}"
    NOVA_VERIFIED=true
elif echo "$NOVA_OUTPUT" | grep -qi "passed"; then
    echo -e "${GREEN}✓ VERIFIED: Nova Act test passed${NC}"
    NOVA_VERIFIED=true
else
    echo -e "${RED}✗ WARNING: Could not verify Nova Act success${NC}"
    echo -e "${RED}  Please review output above carefully${NC}"
fi

#############################################
# SUMMARY
#############################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Phase 1 Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$PLAYWRIGHT_VERIFIED" = true ]; then
    echo -e "  Playwright: ${GREEN}✓ PASSED (verified)${NC}"
else
    echo -e "  Playwright: ${YELLOW}? UNCERTAIN (review output)${NC}"
fi

if [ "$NOVA_VERIFIED" = true ]; then
    echo -e "  Nova Act:   ${GREEN}✓ PASSED (verified)${NC}"
else
    echo -e "  Nova Act:   ${YELLOW}? UNCERTAIN (review output)${NC}"
fi

echo ""
echo "Screenshots saved:"
echo "  Playwright: playwright-tests/test-results/"
echo "  Nova Act:   nova-act-tests/screenshots/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Step"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Run Phase 2 to see how structural changes affect tests:"
echo "  ./phase2-structural.sh"
echo ""
