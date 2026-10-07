# DDAY-VF-UI-DEPLOY — UAT deploy

Host: `157.10.52.54` / `uat.esoft.vn`

## Exact SHA / image

| Kind | Value |
|---|---|
| Deployed VF executable | `fb34d3618d9f51c0aa9b236a5913c8af094e7ac5` |
| Image | `dday-vf-uat-virtual-factory-dday:fb34d36` (`5fee14e2af6d`) |
| Container started | `2026-10-07T04:52:11.522748124Z` |
| MQTT command | `virtual-factory dday-bw-runtime --mqtt-host plantos-emqx --mqtt-port 1883 --mqtt-client-id vf-dday-bw-demo-01` |
| HTTP | env `FACTORIX_SIM_HTTP_HOST=0.0.0.0` `FACTORIX_SIM_HTTP_PORT=8090`, published `127.0.0.1:8090` only |
| PlantOS (unchanged) | backend/frontend/edge `a1695c5` |

Recreate of `virtual-factory-dday` was technically required to load the HTTP listener.
Restart replayed deterministic source timestamps from `2026-10-03T00:00:00Z` (accepted C01).

## Public URL

- http://157.10.52.54/factorix-sim
- http://157.10.52.54/factorix-sim/overview
- aliases: `/bottled-water-demo`, `/bottled-water-demo/overview`

nginx include: `/etc/nginx/snippets/factorix-sim.conf` from `deploy/dday-vf-uat.nginx.conf`,
inserted in `/etc/nginx/sites-available/plantos-uat` before `location /`.

## Health (public)

```json
{"status":"ok","product":"FactoriX Sim","public_route":"/factorix-sim","alias_route":"/bottled-water-demo","workspace_id":"bottled-water-dday","plant_source_id":"BW-DEMO-01","vf_source_sha":"fb34d3618d9f51c0aa9b236a5913c8af094e7ac5","simulation_owner":"dday-bw-runtime","single_factory":true,"run_state":"RUNNING"}
```

`simulation_owner=dday-bw-runtime` and one `factory_object_id` prove a single factory truth.

## MQTT still works (12 s subscribe on plantos-net after fb34d36 recreate)

| Field | Value |
|---|---|
| messages | 226 |
| kinds | signal 226 |
| FAST `BW-FP-CAP01/motor_current` | 28 |
| MEDIUM `BW-FP-FIL01/fill_rate` | 6 |
| SLOW `BW-WT-FEED01/water_flow` | 3 |
| COUNT `BW-FP/total_count` | 3 |
| contract | `dday-bw-b1-v2` |
| workspace | `bottled-water-dday` |
| timestamp_kind | `simulated_source_utc` |
| provenance | `SIMULATED_RAW` |
| QoS | all 1 |
| public 1883 | none |

PlantOS Edge (`plantos-edge-dday:a1695c5`, healthy) continues to receive the topic family
`virtual-factory/bottled-water-dday/#`. Because the recreate replayed Run B source
timestamps, Edge reports `D-Day duplicate delivery ignored` — the accepted C01
idempotent path, not a broken integration. Center `/health` remains
`{"status":"healthy","version":"0.1.0"}`. PlantOS images were not rebuilt.

## Rollback

1. Restore nginx: `cp /root/deploy-vf-uat-ui/plantos-uat.nginx.pre-factorix /etc/nginx/sites-available/plantos-uat && nginx -t && nginx -s reload`
2. Recreate VF from the previous accepted image:
   `COMPOSE_PROJECT_NAME=dday-vf-uat VF_SOURCE_SHA=d7db6d0909da968c2b4a4ea2cdb712e5d7601282 docker compose -f /root/deploy-vf-uat/vf/deploy/dday-vf-uat.compose.yml up -d`
   Image tag `dday-vf-uat-virtual-factory-dday:d7db6d0` (`e7ebab019cc0`) is retained.
3. MQTT client-id / topics / PlantOS stack stay as they are.
