#!/bin/bash
# ============================================================
#  SmartSuccess GPU Server — Start Script
#  Location: /home/jovyan/work/gpu-server/
#
#  Features:
#    - Conda + system-python environment setup
#    - Pre-flight checks (CUDA, Python deps, ffmpeg, port)
#    - Separated log streams (app log vs stdout/stderr)
#    - Model load health-check with timeout
# ============================================================
set -uo pipefail

# ----- Configuration -----
GPU_SERVER_DIR="/home/jovyan/work/gpu-server"
PID_FILE="$GPU_SERVER_DIR/gpu_server.pid"
APP_LOG="$GPU_SERVER_DIR/gpu_server.log"        # structured app log (RotatingFileHandler)
STDOUT_LOG="$GPU_SERVER_DIR/gpu_server_out.log"  # stdout/stderr from uvicorn + third-party libs
PORT=8000
PUBLIC_URL="https://extra-8000-8000-1770771480319309978.cluster3.service-inference.ai"
PYTHON="/usr/bin/python3"
STARTUP_TIMEOUT=300   # seconds (5 min max for model loading)
HEALTH_POLL=5         # seconds between polls

# ----- Environment -----
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# Add conda bin to end of PATH (for ffmpeg) without overriding system python
export PATH="$PATH:/home/jovyan/miniconda3/bin"

# ----- Helper functions -----
info()  { echo "  [INFO]  $*"; }
warn()  { echo "  [WARN]  $*"; }
fail()  { echo "  [FAIL]  $*" >&2; exit 1; }
ok()    { echo "  [ OK ]  $*"; }

# =============================================================
echo "======================================================"
echo "  SmartSuccess GPU Server — Start"
echo "======================================================"
echo ""

# ----- 1. Directory check -----
cd "$GPU_SERVER_DIR" || fail "Directory not found: $GPU_SERVER_DIR"
ok "Working directory: $GPU_SERVER_DIR"

# ----- 2. Already running? -----
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        warn "GPU Server already running (PID: $OLD_PID)"
        warn "Use stop_server.sh first, or restart_server.sh"
        exit 1
    else
        info "Removing stale PID file (process $OLD_PID not running)"
        rm -f "$PID_FILE"
    fi
fi

# ----- 3. Pre-flight checks -----
echo ""
echo "--- Pre-flight checks ---"

# Python
if [ -x "$PYTHON" ]; then
    PY_VER=$($PYTHON --version 2>&1)
    ok "Python: $PY_VER ($PYTHON)"
else
    fail "Python not found at $PYTHON"
fi

# Key Python packages
for pkg in uvicorn fastapi torch whisper TTS chromadb sentence_transformers; do
    if $PYTHON -c "import $pkg" 2>/dev/null; then
        ok "Package: $pkg"
    else
        warn "Package: $pkg — NOT INSTALLED (may cause partial failure)"
    fi
done

# ffmpeg (needed by Whisper)
if command -v ffmpeg &>/dev/null; then
    FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    ok "ffmpeg: $FFMPEG_VER"
else
    warn "ffmpeg not found — STT may fail for some audio formats"
fi

# CUDA
if $PYTHON -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    GPU_NAME=$($PYTHON -c "import torch; print(torch.cuda.get_device_name(0))" 2>/dev/null)
    GPU_MEM=$($PYTHON -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB')" 2>/dev/null)
    ok "CUDA: $GPU_NAME ($GPU_MEM)"
else
    warn "CUDA not available — running on CPU (slow)"
fi

# Port
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    warn "Port $PORT is in use. Killing existing process..."
    fuser -k $PORT/tcp 2>/dev/null
    sleep 2
    ok "Port $PORT freed"
else
    ok "Port: $PORT (available)"
fi

# ----- 4. Start server -----
echo ""
echo "--- Starting server ---"
info "Port: $PORT"
info "App log:    $APP_LOG  (structured, rotating)"
info "Stdout log: $STDOUT_LOG"
info "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"

# Rotate stdout log if it's too big (>5MB)
STDOUT_SIZE=$(stat -c%s "$STDOUT_LOG" 2>/dev/null || echo 0)
if [ "$STDOUT_SIZE" -gt 5242880 ] 2>/dev/null; then
    mv "$STDOUT_LOG" "${STDOUT_LOG}.old"
    info "Rotated old stdout log"
fi

nohup $PYTHON -m uvicorn main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 1 \
    >> "$STDOUT_LOG" 2>&1 &

SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
ok "Server process started (PID: $SERVER_PID)"

# ----- 5. Wait for health -----
echo ""
echo "--- Waiting for models to load (up to ${STARTUP_TIMEOUT}s) ---"
ELAPSED=0
while [ $ELAPSED -lt $STARTUP_TIMEOUT ]; do
    sleep $HEALTH_POLL
    ELAPSED=$((ELAPSED + HEALTH_POLL))

    # Process alive?
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo ""
        echo "  [FAIL]  Server process died during startup. Check logs:"
        echo "          tail -50 $STDOUT_LOG"
        echo "          tail -50 $APP_LOG"
        rm -f "$PID_FILE"
        exit 1
    fi

    # Health check
    HEALTH=""
    HEALTH=$(curl -s --max-time 5 http://localhost:$PORT/health 2>/dev/null) || true
    if [ -n "$HEALTH" ]; then
        echo ""
        ok "GPU Server is running! (loaded in ${ELAPSED}s)"
        echo ""

        # Parse and display service status
        echo "$HEALTH" | $PYTHON -c "
import json, sys
d = json.load(sys.stdin)
svcs = d.get('services', {})
print('  Services:')
for s, ok in svcs.items():
    icon = '✅' if ok else '❌'
    print(f'    {icon} {s.upper()}')
print(f'  Uptime: {d.get(\"uptime_seconds\", 0):.0f}s')
" 2>/dev/null || echo "  Health: $HEALTH"

        echo ""
        echo "  📡 Public URL: $PUBLIC_URL"
        echo "  🔗 Local URL:  http://localhost:$PORT"
        echo "  📋 App log:    $APP_LOG"
        echo "  📋 Stdout log: $STDOUT_LOG"
        echo ""
        echo "======================================================"
        exit 0
    fi

    printf "  . (%ds)\n" "$ELAPSED"
done

echo ""
warn "Startup timeout (${STARTUP_TIMEOUT}s). Server may still be loading."
warn "Check logs:"
echo "     tail -50 $STDOUT_LOG"
echo "     tail -50 $APP_LOG"
echo "======================================================"
exit 1
