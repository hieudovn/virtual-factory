# DDAY-VF-UAT-01-C01 — durable runtime (implemented, not deployed)

Recon reports 01–07 remain historical. This file records the C01 launcher. UAT is not started from this slice.

## Exact CLI

```text
virtual-factory dday-bw-runtime --mqtt-host plantos-emqx --mqtt-port 1883 --mqtt-client-id vf-dday-bw-demo-01
```

Identity (fail-closed):

| Field | Value |
|---|---|
| workspace | `bottled-water-dday` |
| profile | `dday-bw-runtime-fr1` |
| contract | `dday-bw-b1-v2` |
| plant source | `BW-DEMO-01` |
| dictionary SHA-256 | `cbe389ec7d3c022a78b7853044f08ba148a7b8a41e374931973683c8886b07ca` |
| timestamp epoch | `2026-10-03T00:00:00.000Z` |
| reservation / wall-clock sync | false |

Loop: `factory.start()` → `publish_live_mqtt` → optional wall-clock pace (`tick_interval_s`, pacing only) → `factory.step()`. On stop: `factory.stop()` → publish STOPPED `MACHINE_STATE_CHANGED` → `gateway.disconnect()` drain. `MqttPublishError` → exit 1.

## Compose artifact

Path: `deploy/dday-vf-uat.compose.yml`

- service `virtual-factory-dday`
- `restart: unless-stopped`
- external network `plantos-net`
- no public ports, no volumes, no secrets
- command is the exact CLI above
- build `ARG SOURCE_SHA=${VF_SOURCE_SHA}` from repo-root `Dockerfile` (Dockerfile CMD is not changed)

## Operator lifecycle (document only — do not run on UAT from this slice)

```text
VF_SOURCE_SHA=<accepted_sha> docker compose -f deploy/dday-vf-uat.compose.yml build
VF_SOURCE_SHA=<accepted_sha> docker compose -f deploy/dday-vf-uat.compose.yml up -d
docker compose -f deploy/dday-vf-uat.compose.yml stop
docker compose -f deploy/dday-vf-uat.compose.yml restart
docker compose -f deploy/dday-vf-uat.compose.yml ps
docker compose -f deploy/dday-vf-uat.compose.yml logs -f virtual-factory-dday
```

`restart` starts a **fresh** deterministic run. Source timestamps may repeat from `t=0`. There is no checkpoint file and no `VF_SOURCE_TIME_FLOOR`.

## MQTT shutdown trace (accepted ACK harness)

Clean stop:

```json
[
  {
    "phase": "stopped_event_publish",
    "published": 1,
    "simulation_time_s": 0.0
  },
  {
    "phase": "drain",
    "drained": 0,
    "remaining": 0,
    "timed_out": false,
    "ok": true,
    "timeout_s": 2.0
  }
]
```

The STOPPED event (`detail=run_state=STOPPED`) is published and ACKed before disconnect.

MQTT ACK failure remains fail-closed:

```json
{"phase": "publish_fail_closed", "error": "QoS-1 ACK not confirmed within timeout; fail closed"}
```

Process exit code is `1`.

## What this slice does not do

- No UAT build/up
- No live EMQX connection
- No TDengine query
- No PlantOS code change
- No timestamp reservation/warmup
- No topology/signal/scenario/contract/KPI change
