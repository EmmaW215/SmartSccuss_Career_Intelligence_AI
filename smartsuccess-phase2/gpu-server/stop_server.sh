#!/bin/bash
# ============================================================
#  SmartSuccess GPU Server — Stop Script
#
#  Features:
#    - Graceful SIGTERM → wait → force SIGKILL
#    - Cleans up child processes (uvicorn workers)
#    - Frees port if orphan process is found
#    - PID file cleanup
# ============================================================
set -uo pipefail

# ----- Configuration -----
GPU_SERVER_DIR="/home/jovyan/work/gpu-server"
PID_FILE="$GPU_SERVER_DIR/gpu_server.pid"
PORT=8000
GRACEFUL_WAIT=5   # seconds to wait after SIGTERM
FORCE_WAIT=3      # seconds to wait after SIGKILL

# ----- Helper functions -----
info()  { echo "  [INFO]  $*"; }
warn()  { echo "  [WARN]  $*"; }
ok()    { echo "  [ OK ]  $*"; }

echo "======================================================"
echo "  SmartSuccess GPU Server — Stop"
echo "======================================================"
echo ""

STOPPED=false

# ----- 1. Stop by PID file -----
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        info "Sending SIGTERM to PID $PID..."
        kill "$PID" 2>/dev/null

        # Wait for graceful shutdown
        for i in $(seq 1 $GRACEFUL_WAIT); do
            if ! kill -0 "$PID" 2>/dev/null; then
                ok "Server stopped gracefully (PID: $PID)"
                STOPPED=true
                break
            fi
            sleep 1
        done

        # Force kill if still alive
        if [ "$STOPPED" = false ] && kill -0 "$PID" 2>/dev/null; then
            warn "Still running after ${GRACEFUL_WAIT}s — sending SIGKILL..."
            kill -9 "$PID" 2>/dev/null
            sleep $FORCE_WAIT
            # Check one more time with extra wait
            if kill -0 "$PID" 2>/dev/null; then
                sleep 2
            fi
            if ! kill -0 "$PID" 2>/dev/null; then
                ok "Server force-killed (PID: $PID)"
            else
                warn "Process $PID may still be terminating (zombie)"
            fi
            STOPPED=true
        fi
    else
        info "Process $PID not running (stale PID file)"
        STOPPED=true
    fi
    rm -f "$PID_FILE"
else
    info "No PID file found"
fi

# ----- 2. Clean up orphan uvicorn processes -----
ORPHANS=$(ps aux 2>/dev/null | grep "[u]vicorn main:app" | awk '{print $2}' || true)
if [ -n "$ORPHANS" ]; then
    warn "Found orphan uvicorn processes: $ORPHANS"
    echo "$ORPHANS" | xargs kill 2>/dev/null
    sleep 2
    # Force kill any survivors
    SURVIVORS=$(ps aux 2>/dev/null | grep "[u]vicorn main:app" | awk '{print $2}' || true)
    if [ -n "$SURVIVORS" ]; then
        echo "$SURVIVORS" | xargs kill -9 2>/dev/null
        sleep 1
    fi
    ok "Orphan processes cleaned up"
    STOPPED=true
fi

# ----- 3. Free port if still occupied -----
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    warn "Port $PORT still occupied — force freeing..."
    fuser -k $PORT/tcp 2>/dev/null
    sleep 1
    if ! ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
        ok "Port $PORT freed"
    else
        warn "Port $PORT could not be freed"
    fi
fi

# ----- 4. Verify -----
echo ""
if [ "$STOPPED" = true ]; then
    ok "GPU Server stopped"
else
    info "GPU Server was not running"
fi

echo "======================================================"
