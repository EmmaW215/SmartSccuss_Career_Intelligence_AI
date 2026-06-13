# GPU Server — Production Deployment (Phase 4 PR 4-2)

Hardening added: shared-secret auth, public tunnel, model warm-up, GPU
concurrency cap, and systemd supervision. All of it is backward compatible —
with `INTERNAL_API_TOKEN` unset the server behaves exactly as before.

## 1. Shared-secret auth (`X-Internal-Token`)

Generate a token and set it on **both** sides:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

- GPU host: `INTERNAL_API_TOKEN=<token>` in `/opt/smartsuccess/gpu-server/.env`
- Render backend: `INTERNAL_API_TOKEN=<same token>` in the service env

When set, `/api/*` and `/metrics` require the header; `/health`, `/health/detail`,
`/`, and the docs stay public (so the tunnel/uptime checks keep working). The
Render `gpu_client` attaches the header automatically when its env var is set.

## 2. Public transport (pick one, both free + TLS, no port-forwarding)

**Cloudflare Tunnel**
```bash
cloudflared tunnel login
cloudflared tunnel create smartsuccess-gpu
cloudflared tunnel route dns smartsuccess-gpu gpu.yourdomain.com
cloudflared tunnel run --url http://localhost:8000 smartsuccess-gpu
```
Then set Render `GPU_SERVER_URL=https://gpu.yourdomain.com`.

**Tailscale Funnel**
```bash
tailscale funnel 8000
```
Use the printed `https://<host>.ts.net` URL as Render `GPU_SERVER_URL`.

## 3. Model warm-up

Whisper + XTTS + RAG load at startup (FastAPI `lifespan`); `/health` reports
`services: {stt, tts, rag}` readiness. `systemd` `TimeoutStartSec=300` allows
for model load before health checks fire.

## 4. GPU concurrency cap

`GPU_CONCURRENCY` (default 2) bounds simultaneous GPU inferences via an
`asyncio.Semaphore`, preventing VRAM OOM when transcribe + synthesize overlap.

## 5. systemd supervision

See `smartsuccess-gpu.service` (install steps in its header). Replaces
`start_server.sh` with auto-restart, boot-start, and journald logging.

## Smoke test after bring-up

```bash
# public — no token needed
curl https://gpu.yourdomain.com/health

# protected — 401 without token, 200 with it
curl -s -o /dev/null -w "%{http_code}\n" https://gpu.yourdomain.com/metrics          # 401
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
     https://gpu.yourdomain.com/metrics                                              # 200
```
