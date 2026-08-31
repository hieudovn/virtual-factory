# VF-DEPLOY-01 — docker-run.md

## Start

```text
docker compose --project-directory d:\Project\Github\virtual-factory \
  -f d:\Project\Github\virtual-factory\docker-compose.assy.yml up -d
```

Result (machine output):

```text
[+] up 2/2
 ✔ Network vf-assy_default     Created
 ✔ Container vf-assy-vf-assy-1 Started
```

## Service identity

```text
NAME                IMAGE            COMMAND                  SERVICE   STATUS
vf-assy-vf-assy-1   vf-assy:latest   "virtual-factory ser…"   vf-assy   Up ... (healthy)

PORTS: 0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
```

Container command (from compose override):

```text
virtual-factory serve --host 0.0.0.0 --port 8000
```

Environment inside the container:

- `VF_ENABLE_S04B_OVERVIEW=1`
- `TIPA_ASSY_CONFIG=/app/configs/plants/tipa_assy_demo.yaml`

Server log:

```text
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:xxxxx - "GET /health HTTP/1.1" 200 OK   (healthcheck polling)
```

No MQTT / OPC UA ports are exposed (P0 ASSY runtime does not need them). Only
`8000` is published.
