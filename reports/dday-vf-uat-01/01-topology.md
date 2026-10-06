# DDAY-VF-UAT-01 — UAT runtime topology (recon)

Deployment is **not** running and is **not** started by this slice.

## Intended path (VF SA stated; not independently live-verified here)

```text
virtual-factory-dday (proposed, does not exist)
        │  plantos-net only, no public MQTT port
        ▼
plantos-emqx:1883
        ▼
plantos-edge-dday / EDGE-DDAY-01
        ▼
plantos-backend → TDengine → PlantOS Live UI (BW-DEMO-01)
```

## Observed from this recon environment

| Surface | Result |
|---|---|
| Docker CLI | not installed |
| Self-hosted Cursor workers | none |
| SSH | none |
| `plantos-emqx:1883` TCP | unreachable |
| TDengine | not queried; historian not modified |
| MQTT credentials | none present; none invented |

VF `MqttGateway` has no username/password API. SA states the prior D-Day publisher used the internal broker path without credential flags. If UAT later requires credentials the gateway cannot set, that is a new blocker — not claimed resolved here.
