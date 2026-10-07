# DDAY-VF-UI-DEPLOY — FactoriX Sim

## Status

Machine status is derived by `run_task_gate.py` / `derive_status.py`.

The PM does not self-certify COMPLETE, CLOSED, SA APPROVED, or NEXT SLICE AUTHORIZED.

Report line after a READY derivation:

`DDAY-VF-UI-DEPLOY — FACTORIX SIM READY FOR SA REVIEW`

## What shipped

- FactoriX Sim branding on the existing Bottled Water skin
- Public `/factorix-sim` + `/factorix-sim/overview` (aliases `/bottled-water-demo*`)
- HTTP observer on the MQTT `dday-bw-runtime` factory (`factory_autorun=False`)
- UAT nginx + loopback `127.0.0.1:8090`
- MQTT path unchanged; PlantOS images unchanged (`a1695c5`)

## SHA distinction

| Kind | SHA |
|---|---|
| Canonical main / Issue #121 baseline | `ee838b0b00704e8f0ed7cd965ac48440cca2b26e` |
| Deployed VF executable | `fb34d3618d9f51c0aa9b236a5913c8af094e7ac5` |
| Previous MQTT executable | `d7db6d0909da968c2b4a4ea2cdb712e5d7601282` |
| PlantOS UAT | `a1695c5457515e2b565a5f9fe107c1e18b3e0879` |

## Browser

See [10-visual.md](../evidence/DDAY-VF-UI-DEPLOY/10-visual.md).

## Stop

No merge. No Issue #91. SA review next.
