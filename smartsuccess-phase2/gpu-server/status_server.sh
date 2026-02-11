#!/bin/bash
# ============================================================
#  SmartSuccess GPU Server — Status Script
#
#  Features:
#    - Process info (PID, uptime, memory)
#    - Local + public health checks
#    - GPU hardware metrics (nvidia-smi)
#    - Model load status (/health/detail)
#    - Request statistics (/metrics)
#    - Recent log tail (app + stdout)
#
#  Usage:
#    bash status_server.sh           # full status
#    bash status_server.sh --brief   # one-line summary
#    bash status_server.sh --logs N  # show last N log lines
# ============================================================
set -uo pipefail

# ----- Configuration -----
GPU_SERVER_DIR="/home/jovyan/work/gpu-server"
PID_FILE="$GPU_SERVER_DIR/gpu_server.pid"
APP_LOG="$GPU_SERVER_DIR/gpu_server.log"
STDOUT_LOG="$GPU_SERVER_DIR/gpu_server_out.log"
PORT=8000
PUBLIC_URL="https://extra-8000-8000-1770771480319309978.cluster3.service-inference.ai"
PYTHON="/usr/bin/python3"

# ----- Parse args -----
MODE="full"
LOG_LINES=10
while [[ $# -gt 0 ]]; do
    case "$1" in
        --brief|-b)   MODE="brief"; shift ;;
        --logs|-l)    MODE="logs"; LOG_LINES="${2:-20}"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--brief | --logs N | --help]"
            exit 0 ;;
        *) shift ;;
    esac
done

# ----- Helper -----
check_process() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "$PID"
            return 0
        fi
    fi
    echo ""
    return 1
}

# ======================== BRIEF MODE ========================
if [ "$MODE" = "brief" ]; then
    PID=$(check_process) && true
    if [ -n "$PID" ]; then
        HEALTH=$(curl -s --max-time 3 http://localhost:$PORT/health 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$HEALTH" ]; then
            UPTIME=$(echo "$HEALTH" | $PYTHON -c "import json,sys; print(f'{json.load(sys.stdin).get(\"uptime_seconds\",0):.0f}s')" 2>/dev/null || echo "?")
            REQS=$(echo "$HEALTH" | $PYTHON -c "import json,sys; d=json.load(sys.stdin).get('requests',{}); print(f'{d.get(\"total\",0)} reqs, {d.get(\"errors\",0)} errs')" 2>/dev/null || echo "?")
            echo "🟢 Running | PID=$PID | uptime=$UPTIME | $REQS"
        else
            echo "🟡 Running (PID=$PID) but health check failed"
        fi
    else
        echo "🔴 Stopped"
    fi
    exit 0
fi

# ======================== LOGS MODE =========================
if [ "$MODE" = "logs" ]; then
    echo "=== App log (last $LOG_LINES lines) — $APP_LOG ==="
    if [ -f "$APP_LOG" ]; then
        tail -"$LOG_LINES" "$APP_LOG"
    else
        echo "(no log file)"
    fi
    echo ""
    echo "=== Stdout log (last $LOG_LINES lines) — $STDOUT_LOG ==="
    if [ -f "$STDOUT_LOG" ]; then
        tail -"$LOG_LINES" "$STDOUT_LOG"
    else
        echo "(no log file)"
    fi
    exit 0
fi

# ======================== FULL MODE =========================
echo "======================================================"
echo "  SmartSuccess GPU Server — Status"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================"
echo ""

# ----- 1. Process -----
echo "--- Process ---"
PID=$(check_process) && true
if [ -n "$PID" ]; then
    UPTIME=$(ps -o etime= -p "$PID" 2>/dev/null | xargs)
    MEM=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{printf "%.0f MB", $1/1024}')
    CPU=$(ps -o %cpu= -p "$PID" 2>/dev/null | xargs)
    echo "  Status:   🟢 Running"
    echo "  PID:      $PID"
    echo "  Uptime:   $UPTIME"
    echo "  Memory:   $MEM"
    echo "  CPU:      ${CPU}%"
else
    echo "  Status:   🔴 Not Running"
fi
echo ""

# ----- 2. Health check (local) -----
echo "--- Health Check (local) ---"
HEALTH=$(curl -s --max-time 5 http://localhost:$PORT/health 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$HEALTH" ]; then
    echo "  Endpoint: 🟢 http://localhost:$PORT/health"
    echo "$HEALTH" | $PYTHON -c "
import json, sys
d = json.load(sys.stdin)
svcs = d.get('services', {})
req = d.get('requests', {})
for s, ok in svcs.items():
    icon = '✅' if ok else '❌'
    print(f'  {s.upper():6s}  {icon}')
print(f'  Uptime:   {d.get(\"uptime_seconds\", 0):.0f}s')
print(f'  Requests: {req.get(\"total\", 0)} total, {req.get(\"errors\", 0)} errors ({req.get(\"error_rate_pct\", 0)}% err)')
lst = d.get('last_success_time')
if lst:
    from datetime import datetime
    print(f'  Last OK:  {datetime.fromtimestamp(lst).strftime(\"%H:%M:%S\")}')
" 2>/dev/null || echo "  $HEALTH"
else
    echo "  Endpoint: 🔴 NOT RESPONDING"
fi
echo ""

# ----- 3. Health check (public) -----
echo "--- Health Check (public) ---"
PUB_HEALTH=$(curl -s --max-time 10 "$PUBLIC_URL/health" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$PUB_HEALTH" ]; then
    echo "  Endpoint: 🟢 $PUBLIC_URL"
else
    echo "  Endpoint: 🔴 $PUBLIC_URL → NOT RESPONDING"
fi
echo ""

# ----- 4. GPU hardware -----
echo "--- GPU Hardware ---"
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,driver_version,temperature.gpu,utilization.gpu,memory.used,memory.total \
        --format=csv,noheader,nounits 2>/dev/null | while IFS=, read -r name driver temp util mem_used mem_total; do
        echo "  Device:      $(echo $name | xargs)"
        echo "  Driver:      $(echo $driver | xargs)"
        echo "  Temperature: $(echo $temp | xargs)°C"
        echo "  GPU Util:    $(echo $util | xargs)%"
        echo "  VRAM:        $(echo $mem_used | xargs) / $(echo $mem_total | xargs) MiB"
    done
else
    echo "  nvidia-smi not available"
fi
echo ""

# ----- 5. Model status (from /health/detail) -----
echo "--- Model Status ---"
DETAIL=$(curl -s --max-time 5 http://localhost:$PORT/health/detail 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$DETAIL" ]; then
    echo "$DETAIL" | $PYTHON -c "
import json, sys
d = json.load(sys.stdin)
models = d.get('models', {})
for svc, info in models.items():
    status = info.get('status', '?')
    icon = '✅' if status == 'loaded' else '❌'
    model = info.get('model', 'n/a')
    device = info.get('device', '?')
    extra = ''
    if svc == 'tts':
        if info.get('multilingual'): extra += ' [multilingual]'
        if info.get('multi_speaker'): extra += ' [multi-speaker]'
    if svc == 'rag':
        emb = info.get('embedding_model', '?')
        db = info.get('chromadb', '?')
        extra = f' [embeddings={emb}, chromadb={db}]'
    print(f'  {icon} {svc.upper():5s} {status:15s} model={model}{extra}  ({device})')

gpu = d.get('gpu', {})
mem = gpu.get('memory', {})
if mem:
    print(f'  VRAM: {mem.get(\"allocated_gb\",0):.2f} / {mem.get(\"total_gb\",0):.1f} GB ({mem.get(\"utilization_pct\",0):.1f}% used)')
" 2>/dev/null || echo "  (could not parse /health/detail)"
else
    echo "  (server not responding)"
fi
echo ""

# ----- 6. Request statistics (from /metrics) -----
echo "--- Request Statistics ---"
METRICS=$(curl -s --max-time 5 http://localhost:$PORT/metrics 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$METRICS" ]; then
    echo "$METRICS" | $PYTHON -c "
import json, sys
d = json.load(sys.stdin)
s = d.get('summary', {})
print(f'  Total Requests:  {s.get(\"total_requests\", 0)}')
print(f'  Success:         {s.get(\"total_success\", 0)}')
print(f'  Errors:          {s.get(\"total_errors\", 0)}')
print(f'  Error Rate:      {s.get(\"error_rate_pct\", 0):.1f}%')
print(f'  Uptime:          {s.get(\"uptime_seconds\", 0):.0f}s')
print()

svcs = s.get('services', {})
if svcs:
    print('  Per-Service:')
    for svc, stats in svcs.items():
        lat = stats.get('avg_latency_ms', 0)
        print(f'    {svc.upper():5s}  reqs={stats.get(\"request_count\",0):4d}  ok={stats.get(\"success_count\",0):4d}  err={stats.get(\"error_count\",0):3d}  avg={lat:.0f}ms')

eps = d.get('endpoints', {})
if eps:
    print()
    print('  Per-Endpoint:')
    for ep, stats in eps.items():
        lat = stats.get('avg_latency_ms', 0)
        print(f'    {ep:30s}  reqs={stats.get(\"request_count\",0):4d}  avg={lat:.0f}ms  min={stats.get(\"min_latency_ms\") or 0:.0f}ms  max={stats.get(\"max_latency_ms\") or 0:.0f}ms')
" 2>/dev/null || echo "  (could not parse /metrics)"
else
    echo "  (server not responding)"
fi
echo ""

# ----- 7. Recent logs -----
echo "--- Recent App Logs (last 8 lines) ---"
if [ -f "$APP_LOG" ]; then
    # Filter to show only our app-level log lines
    grep "| gpu\." "$APP_LOG" | tail -8 || tail -8 "$APP_LOG"
else
    echo "  (no log file)"
fi
echo ""

echo "--- Log Files ---"
[ -f "$APP_LOG" ]    && echo "  App log:    $APP_LOG ($(du -h "$APP_LOG" | cut -f1))"    || echo "  App log:    (not found)"
[ -f "$STDOUT_LOG" ] && echo "  Stdout log: $STDOUT_LOG ($(du -h "$STDOUT_LOG" | cut -f1))" || echo "  Stdout log: (not found)"
echo ""
echo "======================================================"
