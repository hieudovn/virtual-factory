# MQTT Integration

Virtual Factory can publish MVP-01 industrial telemetry frames to a local MQTT broker. MQTT payloads contain measured and publishable telemetry only. Internal truth is not published.

## Run Local Broker

Using Docker Compose:

```bash
docker compose up --build
```

This starts:

- `mqtt`: Mosquitto on `localhost:1883`
- `virtual-factory`: the MVP simulation publishing telemetry to MQTT and exporting local files under `./out`

## Run Publisher Manually

Install MQTT support:

```bash
pip install -e .[dev,mqtt]
```

Run the simulator against an existing broker:

```bash
virtual-factory run --steps 60 --mqtt-host localhost --mqtt-port 1883 --mqtt-topic-prefix virtual-factory/demo/continuous_mvp_01
```

## Topic Format

Topics use:

```text
{topic_prefix}/{signal_name}
```

Examples:

```text
virtual-factory/demo/continuous_mvp_01/LT102_LEVEL
virtual-factory/demo/continuous_mvp_01/FT101_FLOW
virtual-factory/demo/continuous_mvp_01/T102_LOW_LEVEL_ALARM
```

Subscribe to all MVP telemetry:

```text
virtual-factory/demo/continuous_mvp_01/#
```

## JSON Payload

Each message is a simple JSON object:

```json
{
  "name": "LT102_LEVEL",
  "value": 1.23,
  "unit": "m",
  "category": "industrial_signal",
  "quality": "GOOD",
  "timestamp_s": 12.0,
  "source": "LT102"
}
```

Sparkplug B is future scope.

## Expected Signals

- `LT102_LEVEL`
- `FT101_FLOW`
- `PT101_PRESSURE`
- `LIC102_OUT`
- `V101_OPENING_FEEDBACK`

## Expected Alarm Signals

- `T102_LOW_LEVEL_ALARM`
- `T102_HIGH_LEVEL_ALARM`
- `P101_NO_FLOW_ALARM`
- `V101_POSITION_DEVIATION_ALARM`
- `LT102_BAD_QUALITY_ALARM`

## Verify With MQTT Explorer

1. Start Docker Compose.
2. Open MQTT Explorer.
3. Connect to `localhost:1883`.
4. Subscribe to `virtual-factory/demo/continuous_mvp_01/#`.
5. Confirm changing measured values and alarm events appear.

## Verify With Node-RED Or IIoT Platform

Use an MQTT input/subscriber node or connector:

- Host: `localhost`
- Port: `1883`
- Topic: `virtual-factory/demo/continuous_mvp_01/#`
- Payload: JSON

The subscriber should treat these as industrial telemetry samples. Ground truth values such as `T102.level_true` are not published.

## Troubleshooting Docker DNS Startup

If `virtual-factory` exits with:

```text
socket.gaierror: Temporary failure in name resolution
```

the simulator likely tried to connect before Docker Compose DNS or the MQTT broker was ready. The CLI retries MQTT startup by default, and the Compose deployment uses extra retries, but you can still inspect the network:

```bash
docker compose down --remove-orphans
docker compose up -d mqtt
docker compose run --rm virtual-factory python -c "import socket; print(socket.gethostbyname('mqtt'))"
```

Host names depend on where the client runs:

- `mqtt` is the Docker Compose service DNS name from inside the Compose network.
- `localhost` is for host tools such as MQTT Explorer connecting to the exposed broker port.
- `host.docker.internal` lets a container connect to a broker running on the Windows host.

If you run a broker on the Windows host instead of the Compose `mqtt` service, use:

```bash
virtual-factory run --steps 60 --mqtt-host host.docker.internal --mqtt-port 1883
```
