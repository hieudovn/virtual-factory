# DDAY-VF-UAT-02 — UAT host Run A evidence

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or `NEXT SLICE AUTHORIZED`.

**Run A is live. Run B is HOLD.**

## Task interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-VF-UAT-02` |
| Authority | SA Issue `#118` coordinated UAT authorization 2026-10-07T02:19:23Z + user order |
| Frozen VF SHA | `d7db6d0909da968c2b4a4ea2cdb712e5d7601282` |
| PR | `#101` |
| Scope | Inspect UAT host; report Run A; do not change VF; do not start Run B |

## Finding

UAT host `uat.esoft.vn` (`157.10.52.54`) now has `virtual-factory-dday` running the accepted CLI on `plantos-net` → `plantos-emqx:1883` with `VF_SOURCE_SHA=d7db6d0…`. No public MQTT port. Live 12 s MQTT sample showed 22 signals, FAST > MEDIUM > SLOW, COUNT present, zero `operating_state` signals.

Observed PlantOS Edge/Center image: `a1695c5` (`a1695c5457515e2b565a5f9fe107c1e18b3e0879`). Edge is ingesting to Center (`/measurements/ingest` 200). PlantOS PM has not yet confirmed TDengine/UI or `reset_dday_receive_epoch` on this VF PM channel.

Run B is not started.
