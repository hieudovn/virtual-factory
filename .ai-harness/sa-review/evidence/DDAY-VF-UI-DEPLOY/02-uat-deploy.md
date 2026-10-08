# DDAY-VF-UI-DEPLOY — UAT deploy (evidence refresh)

Host: `157.10.52.54` / `uat.esoft.vn`

SA comments `6050598056` / `6050598477`: product/UX at `2a50760` already PASS.
This file records live UAT after that SHA. Product code was not changed in this pass.
The container was **not** recreated for this evidence refresh.

## Exact SHA / image

| Kind | Value |
|---|---|
| Product / UX SHA (operator surface) | `2a507606bd63fbc7a27ef543cbaaf54469cc631b` |
| Deployed VF executable | `2a507606bd63fbc7a27ef543cbaaf54469cc631b` |
| Image | `dday-vf-uat-virtual-factory-dday:2a50760` (`e3b6009acac2`) |
| Container started | `2026-10-07T07:48:35.161105434Z` |
| Evidence captured | `2026-10-08T02:09:00Z` |
| MQTT command | `virtual-factory dday-bw-runtime --mqtt-host plantos-emqx --mqtt-port 1883 --mqtt-client-id vf-dday-bw-demo-01` |
| HTTP | env `FACTORIX_SIM_HTTP_HOST=0.0.0.0` `FACTORIX_SIM_HTTP_PORT=8090`, published `127.0.0.1:8090` only |
| PlantOS (unchanged) | backend/frontend/edge `a1695c5` |

`VF_SOURCE_SHA` inside the container equals the deployed executable above.
Retained previous image `dday-vf-uat-virtual-factory-dday:fb34d36` (`5fee14e2af6d`) is not running.

## Public URL

- http://157.10.52.54/factorix-sim
- http://157.10.52.54/factorix-sim/overview
- aliases: `/bottled-water-demo`, `/bottled-water-demo/overview`

## Health (public, evidence capture)

```json
{"status":"ok","product":"FactoriX Sim","public_route":"/factorix-sim","alias_route":"/bottled-water-demo","workspace_id":"bottled-water-dday","plant_source_id":"BW-DEMO-01","vf_source_sha":"2a507606bd63fbc7a27ef543cbaaf54469cc631b","simulation_owner":"dday-bw-runtime","single_factory":true,"factory_object_id":132483478832016,"run_state":"RUNNING","simulation_time_s":101996.0}
```

`simulation_owner=dday-bw-runtime` and one `factory_object_id` prove a single factory truth.

## MQTT still healthy (12 s subscribe on plantos-net, 2026-10-08)

| Field | Value |
|---|---|
| messages | 127 |
| kinds | signal 127 |
| FAST `BW-FP-CAP01/motor_current` | 15 |
| MEDIUM `BW-FP-FIL01/fill_rate` | 3 |
| SLOW `BW-WT-FEED01/water_flow` | 2 |
| COUNT `BW-FP/total_count` | 2 |
| contract | `dday-bw-b1-v2` |
| workspace | `bottled-water-dday` |
| timestamp_kind | `simulated_source_utc` |
| provenance | `SIMULATED_RAW` |
| QoS | all 1 |
| public 1883 | none |

PlantOS Edge (`plantos-edge-dday:a1695c5`, healthy) continues to receive
`virtual-factory/bottled-water-dday/#`. Center `/health` remains
`{"status":"healthy","version":"0.1.0"}`. PlantOS images were not rebuilt.

## Rollback

1. Restore nginx: `cp /root/deploy-vf-uat-ui/plantos-uat.nginx.pre-factorix /etc/nginx/sites-available/plantos-uat && nginx -t && nginx -s reload`
2. Recreate VF from the previous accepted MQTT image:
   `COMPOSE_PROJECT_NAME=dday-vf-uat VF_SOURCE_SHA=d7db6d0909da968c2b4a4ea2cdb712e5d7601282 docker compose -f /root/deploy-vf-uat/vf/deploy/dday-vf-uat.compose.yml up -d`
   Image tag `dday-vf-uat-virtual-factory-dday:d7db6d0` (`e7ebab019cc0`) is retained.
3. MQTT client-id / topics / PlantOS stack stay as they are.
