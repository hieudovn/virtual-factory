# DDAY-VF-UAT-01 — proposed durable launcher (NOT implemented)

Smallest additive mechanism. Requires a later SA-authorized implementation SHA (FR1 + this launcher). Do not deploy from `320d82f`.

## Process

New CLI, suggested: `virtual-factory dday-bw-runtime`

Loop (after warmup):

1. `BottledWaterFactory.start()`
2. wall-clock wait `tick_interval_s` (pacing only)
3. `factory.step()`  — `dt_s = 1` simulated
4. `factory.publish_live_mqtt(MqttGateway(...))` — FR1 scheduler + C03 cursor + QoS-1 ACK
5. persist last published `simulation_time_s`
6. fail closed on `MqttPublishError` (no mark, restart policy handles process)

Reuse existing `MqttGateway.publish_raw` / ACK / drain. Do not invent a second gateway.

## Docker

```yaml
# proposal only — not added to the repository in this slice
services:
  virtual-factory-dday:
    container_name: virtual-factory-dday
    image: <registry>/virtual-factory:<explicit_accepted_sha>
    restart: unless-stopped
    networks:
      - plantos-net
    environment:
      MQTT_HOST: plantos-emqx
      MQTT_PORT: "1883"
      MQTT_CLIENT_ID: vf-dday-bw-demo-01
      VF_WORKSPACE: bottled-water-dday
      VF_RUNTIME_PROFILE: dday-bw-runtime-fr1
      VF_SOURCE_TIME_FLOOR_S: "<measured_tdengine_max_sim_s + margin>"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    # no ports: no public MQTT, HTTP loopback-only if retained
networks:
  plantos-net:
    external: true
```

Build `ARG SOURCE_SHA=<accepted>` already exists on the root Dockerfile; CMD must not stay `run --steps 60`.

Do not recreate PlantOS Center, Edge, TDengine, or EMQX. Attach only to existing `plantos-net`.

## Auth

Inspect live EMQX/EDGE-DDAY-01 at deploy time. Reuse the existing broker policy exactly. Default: no credential flags (matches prior publisher and current `MqttGateway`). If credentials are required, STOP — gateway cannot configure username/password today.

## Operator commands (once implemented)

- start / stop / restart: `docker compose ... up/down/restart virtual-factory-dday`
- status: container health + `/health` on loopback if kept
- logs: `docker logs virtual-factory-dday`
- RESET: existing Bottled Water reset control, then mandatory warmup before publish
