# DDAY-VF-UAT-01 — no persistent BW MQTT entrypoint

## Blocker B

At C03 `320d82f` and still at HEAD:

| Artifact | What it does | Bottled Water FR1 MQTT? |
|---|---|---|
| root `Dockerfile` CMD | `virtual-factory run --steps 60 --quiet` | no — generic MVP |
| `virtual-factory serve --mqtt-host` | `RuntimeService.publish_frame` on MVP telemetry | no — not `plantos_export` |
| HTTP Bottled Water autorun | `BottledWaterFactory.step()` only | no — never calls `publish_live_mqtt` |
| `deploy/virtual-factory.service` | Compressor Train OPC UA on port 8002 | no |
| `deploy/vf2.Dockerfile` | VF-2/PIM | no |
| CLI parsers | `run serve validate generate parse` | no `dday-bw` / publish command |

`publish_live_mqtt` exists as a library method on `BottledWaterFactory` (FR1 at dd6cfe4) and is used by tests/smoke/evidence only. There is no restartable process that performs:

`start → autonomous step → FR1 scheduler → QoS-1 MQTT publish`.

PlantOS G3/G4 `vf_publisher.py` one-shot harness is out of this repo and is not a durable VF service.
