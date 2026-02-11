#!/bin/bash
# ============================================================
#  SmartSuccess GPU Server — Restart Script
#
#  Usage:
#    bash restart_server.sh           # graceful restart
#    bash restart_server.sh --quick   # skip pre-flight checks
# ============================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Parse args
QUICK=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick|-q)  QUICK=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--quick | --help]"
            echo "  --quick  Skip pre-flight checks (faster restart)"
            exit 0 ;;
        *) shift ;;
    esac
done

echo "======================================================"
echo "  SmartSuccess GPU Server — Restart"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================"
echo ""

# ----- 1. Stop -----
echo ">>> Phase 1: Stopping server..."
echo ""
bash "$SCRIPT_DIR/stop_server.sh"

echo ""
echo ">>> Phase 2: Waiting for cleanup..."
sleep 3

# ----- 2. Start -----
echo ""
echo ">>> Phase 3: Starting server..."
echo ""
bash "$SCRIPT_DIR/start_server.sh"

RESULT=$?
echo ""
if [ $RESULT -eq 0 ]; then
    echo "  ✅ Restart complete"
else
    echo "  ❌ Restart failed (exit code: $RESULT)"
    echo "     Check logs: bash $SCRIPT_DIR/status_server.sh --logs 30"
fi
echo "======================================================"
exit $RESULT
