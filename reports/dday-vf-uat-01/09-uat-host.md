# DDAY-VF-UAT-02 — UAT host / Run A (inspected 2026-10-07T02:44:46Z)

SSH credentials are **not** recorded here.

## Host

- `uat.esoft.vn` / `157.10.52.54`
- Docker 29.1.3, Compose 2.40.3
- Network `plantos-net` members: `virtual-factory-dday`, `plantos-emqx`, `plantos-edge-dday`, `plantos-backend`, `plantos-frontend`, `plantos-tdengine`, `plantos-edge-v2`

## Exact deployed VF SHA

`d7db6d0909da968c2b4a4ea2cdb712e5d7601282` (`VF_SOURCE_SHA` inside `virtual-factory-dday`)

CLI:

```text
virtual-factory dday-bw-runtime --mqtt-host plantos-emqx --mqtt-port 1883 --mqtt-client-id vf-dday-bw-demo-01
```

## Container status

| Field | Value |
|---|---|
| name | `virtual-factory-dday` |
| status | Up (started 2026-10-07T02:35:24Z) |
| restart | `unless-stopped` |
| public ports | none (`PortBindings={}`) |
| network | `plantos-net` only |

## Broker / network proof

- `plantos-emqx` (`emqx/emqx:5.7.2`) Up 9 days
- MQTT `1883/tcp` is **not** published on the host
- VF and Edge share `plantos-net`

## FAST / MEDIUM / SLOW / COUNT (12 s live subscribe)

Topic family `virtual-factory/bottled-water-dday/#` — 211 QoS-1 signal messages, 22 distinct measurements, 0 `operating_state`.

| Class | Example | Count in 12 s |
|---|---|---|
| FAST | `BW-FP-CAP01/motor_current` | 26 |
| MEDIUM | `BW-FP-FIL01/fill_rate` | 5 |
| SLOW | `BW-WT-FEED01/water_flow` | 3 |
| COUNT | `BW-FP/total_count` | 2 |

Source timestamps in sample: `2026-10-03T00:21:46.000Z` … `2026-10-03T00:22:11.000Z` (`timestamp_kind=simulated_source_utc`, contract `dday-bw-b1-v2`).

FAST payload excerpt: `simulation_time_s=1306.0`, `provenance=SIMULATED_RAW`.

## Event evidence

Events remain event-driven. An 8 s subscribe to `.../event/#` received no new events (no phase change in that window). Start `MACHINE_STATE_CHANGED(RUNNING)` occurred at process start before this sample. Zero `signal/.../operating_state`.

## Run A / Run B

| Run | Status |
|---|---|
| Run A | **live** since 2026-10-07T02:35:24Z |
| Run B | **HOLD** — waiting PlantOS PM to confirm Run A reached Center/TDengine/UI and `reset_dday_receive_epoch` succeeded |

`reset_dday_receive_epoch` exists in the deployed PlantOS tree at `a1695c5`. This VF PM has not executed it and has not restarted VF.
