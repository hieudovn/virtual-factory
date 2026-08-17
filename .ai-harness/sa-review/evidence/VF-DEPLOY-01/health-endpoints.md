# VF-DEPLOY-01 — health-endpoints.md

## Container health (real healthcheck, not just running)

```text
docker compose -f docker-compose.assy.yml ps
NAME                IMAGE            COMMAND                  SERVICE   STATUS
vf-assy-vf-assy-1   vf-assy:latest   "virtual-factory ser…"   vf-assy   Up 33 seconds (healthy)
```

Healthcheck config (from `docker-compose.assy.yml`):

```yaml
healthcheck:
  test: ["CMD", "python", "-c",
         "import urllib.request, json; s=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)); raise SystemExit(0 if s.get('status')=='ok' else 1)"]
  interval: 10s
  timeout: 3s
  retries: 5
  start_period: 10s
```

## Required ASSY endpoint validation (§6) — all HTTP 200

| Endpoint | HTTP status |
|---|---|
| `GET /health` | 200 |
| `GET /assy-demo` | 200 |
| `GET /assy-demo/overview` | 200 |
| `GET /assy-demo/sub-lines` | 200 |
| `GET /assy-demo/sub-line/ASSY-SL01` | 200 |
| `GET /assy-demo/observations` | 200 |

`/health` body: `{"status": "ok", "static_dir": "<container path>"}` — the
healthcheck validates `status == "ok"` and exits non-zero otherwise.

## Main static UI assets (§6) — all HTTP 200

| Asset | status | bytes |
|---|---|---|
| `/assy-demo` (HTML) | 200 | 19563 |
| `/assy-demo/static/assy_demo.js` | 200 | 108740 |
| `/assy-demo/static/assy_demo.css` | 200 | 35136 |
| `/static/assy_demo.js` | 200 | 108740 |
| `/static/assy_demo.css` | 200 | 35136 |
