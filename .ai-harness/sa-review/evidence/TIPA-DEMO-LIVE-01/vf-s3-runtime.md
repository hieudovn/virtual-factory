# TIPA-DEMO-LIVE-01 — VF-S3 runtime record

## Container / image identity

| Item | Value |
|---|---|
| Container name | `vf-assy-vf-assy-1` |
| Image | `vf-assy:latest` |
| Container ID | `0fccc5a23fe7132a926a9a9a5552304e926c9eebc9b34b6db5e3db97f818fb2a` |
| Status | `Up … (healthy)` |

## Health response

```text
GET /health -> 200
{"status":"ok","static_dir":"/app/src/virtual_factory/ui/static"}
```

## Config path (inside container)

```text
TIPA_ASSY_CONFIG=/app/configs/plants/tipa_assy_demo.yaml
```

## Endpoint checks

| Endpoint | Status |
|---|---|
| `GET /health` | 200 |
| `GET /assy-demo` | 200 |

## Six sub-lines

```text
ASSY-SL01 ASSY-SL02 ASSY-SL03 ASSY-SL04 ASSY-SL05 ASSY-SL06
```

## Station tokens (ASSY-SL01, 12 stations)

```text
PRE-ASSY AP01 AP02 AP03 AP04 AP05 AP06 AP07 AP08 AP09 AP10 AP11
```

Exact token `PRE-ASSY` present; `AP01`..`AP11` present.
