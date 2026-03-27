#!/bin/bash

# Restore Original UI
# Restores sample-app to Phase 1 baseline

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Restore Original UI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for backups
if [ ! -f "sample-app/index.html.phase1.backup" ]; then
    echo -e "${RED}Error: No Phase 1 backup found${NC}"
    echo ""
    echo "Backup file not found: sample-app/index.html.phase1.backup"
    echo ""
    echo "This means either:"
    echo "  1. Phase 2 was never run"
    echo "  2. Backup files were deleted"
    echo ""
    echo "The current UI is likely already in Phase 1 state."
    exit 1
fi

echo "Found backups:"
if [ -f "sample-app/index.html.phase1.backup" ]; then
    echo "  ✓ Phase 1 backup (original)"
fi
if [ -f "sample-app/index.html.phase2.backup" ]; then
    echo "  ✓ Phase 2 backup (structural changes)"
fi
echo ""
echo "This will restore the original Phase 1 UI"
echo ""

read -p "Press Enter to restore..."
echo ""

# Restore from Phase 1 backup
echo "Restoring original files..."
cp sample-app/index.html.phase1.backup sample-app/index.html
cp sample-app/app.js.phase1.backup sample-app/app.js
echo "✓ Files restored"
echo ""

echo -e "${GREEN}Original UI restored successfully!${NC}"
echo ""
echo "Refresh your browser to see the original UI"
echo "URL: http://localhost:8000/#student"
echo ""
echo "Backup files preserved:"
echo "  • sample-app/index.html.phase1.backup"
if [ -f "sample-app/index.html.phase2.backup" ]; then
    echo "  • sample-app/index.html.phase2.backup"
fi
echo ""
echo "To clean up backup files:"
echo "  rm sample-app/*.backup"
echo ""
