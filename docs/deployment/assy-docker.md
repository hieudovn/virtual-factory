# ASSY Docker Runtime — Operator / Developer Guide (VF-DEPLOY-01)

Independent Docker deployment of the accepted TIPA ASSY Virtual Factory
runtime (demo + FastAPI). Containerized from the accepted source; no simulation
semantics changed.

- Accepted contract baseline: `f72cc9564b251c3812c2b6070bddd37e479d5ea5`
- Accepted demo build: `494c12e265d297a389e4463848b9c0b6aafed0b1`
- Deployment file: `docker-compose.assy.yml` (reuses the generic root
  `Dockerfile`; does not modify existing `docker-compose.yml` services)

---

## 1. Prerequisites

- Docker Engine + Docker Compose v2+ (tested: Docker 29.5.3, Compose v5.1.4)
- Port `8000` free on the host (or change `ports` mapping in
  `docker-compose.assy.yml`)
- No host-specific absolute path and no secrets are required anywhere.

## 2. Build

```bash
docker compose -f docker-compose.assy.yml build --no-cache
```

Base image: `python:3.11-slim` (Python 3.11.16). The image installs the
`virtual-factory` package with the `api` + `mqtt` extras from the repository.

## 3. Start

```bash
docker compose -f docker-compose.assy.yml up -d
```

The `vf-assy` service starts the accepted FastAPI runtime:

```text
virtual-factory serve --host 0.0.0.0 --port 8000
```

with:

- `VF_ENABLE_S04B_OVERVIEW=1` (required for M6-S04B Frame A/B + overview)
- `TIPA_ASSY_CONFIG=/app/configs/plants/tipa_assy_demo.yaml` (container path)

## 4. URLs

| Endpoint | Purpose |
|---|---|
| `http://127.0.0.1:8000/assy-demo` | TIPA ASSY UI (Frame A / Frame B) |
| `http://127.0.0.1:8000/health` | health endpoint |
| `http://127.0.0.1:8000/assy-demo/overview` | 6 sub-line overview |
| `http://127.0.0.1:8000/assy-demo/sub-lines` | sub-line list |
| `http://127.0.0.1:8000/assy-demo/sub-line/ASSY-SL01` | sub-line detail |
| `http://127.0.0.1:8000/assy-demo/observations` | P0 observation trace |

## 5. Healthcheck

The container uses a real healthcheck polling `GET /health` (stdlib
`urllib`):

```yaml
healthcheck:
  test: ["CMD", "python", "-c",
         "import urllib.request, json; s=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)); raise SystemExit(0 if s.get('status')=='ok' else 1)"]
  interval: 10s
  timeout: 3s
  retries: 5
  start_period: 10s
```

Wait until status is `healthy` (not merely `running`).

```bash
docker compose -f docker-compose.assy.yml ps
# NAME              STATUS
# vf-assy-vf-assy-1 Up ... (healthy)
```

## 6. Logs

```bash
docker compose -f docker-compose.assy.yml logs -f vf-assy
docker compose -f docker-compose.assy.yml logs --tail 100 vf-assy
```

## 7. Runtime control (Reset / Step / Auto / Pause)

| Action | UI | API |
|---|---|---|
| Reset line | Frame A sidebar **↻ Reset Line** / Frame B **↻ RESET** | `POST /assy-demo/reset` |
| Scenario selection | Footer scenario select | `POST /assy-demo/reset` body `{"scenario": "AP06_FAIL_RETEST_PASS"}` |
| Step | **▶ STEP** | `POST /assy-demo/step` |
| Auto / Stop | **▶▶ AUTO** / **⏹ STOP** (client-side pacing) | repeated `POST /assy-demo/step` |
| Pause | **⏸ PAUSE** (client-side) | n/a (accepted behavior) |
| Run mode | Mode select AUTO/MANUAL/ASSISTED | `POST /assy-demo/run-mode` `{"mode": "MANUAL"}` |
| Select sub-line | click / double-click card | `POST /assy-demo/select` `{"sub_line_id": "ASSY-SL03"}` |

Scenarios: `HAPPY_PATH`, `AP06_FAIL_RETEST_PASS`, `AP08_NG_REINSPECT_PASS`,
`FAILED_FINAL`.

## 8. Restart / reset

```bash
# Restart the container (in-memory runtime state resets deterministically)
docker compose -f docker-compose.assy.yml restart

# Full teardown and re-create
docker compose -f docker-compose.assy.yml down
docker compose -f docker-compose.assy.yml up -d
```

State model: simulation state is **intentionally ephemeral** — all runtime
state lives in the process memory. A restart returns to a clean, valid
HAPPY_PATH runtime at t=0. Nothing is persisted (no volume mounts for
simulation state); this is the preferred clean-deterministic-restart behavior.

## 9. Debug shell

```bash
docker exec -it vf-assy-vf-assy-1 bash        # shell into the container
docker exec -it vf-assy-vf-assy-1 env         # inspect environment
docker exec -it vf-assy-vf-assy-1 python -c "import virtual_factory; print(virtual_factory.__file__)"
```

## 10. Querying endpoints

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/assy-demo/overview
curl http://127.0.0.1:8000/assy-demo/sub-lines
curl -X POST http://127.0.0.1:8000/assy-demo/reset -H 'Content-Type: application/json' -d '{"scenario":"HAPPY_PATH"}'
curl -X POST http://127.0.0.1:8000/assy-demo/step
```

## 11. Shared network for MES E2E (future, documented only)

`vf-assy` currently runs on its own default network (`vf-assy_default`). To
join a shared external network with the MES stack later (no MES integration is
added in this gate), make the **exact one-line change** below:

```bash
# 1. create the shared network (once, on the host)
docker network create manufacturing-demo
```

```yaml
# 2. in docker-compose.assy.yml, uncomment the trailing block:
networks:
  default:
    name: manufacturing-demo
    external: true
```

```bash
# 3. re-create the stack
docker compose -f docker-compose.assy.yml down
docker compose -f docker-compose.assy.yml up -d
```

Then the MES compose stack joins the same `manufacturing-demo` external
network and reaches `vf-assy:8000` by service name. No MES URL/auth is added
in this gate.
