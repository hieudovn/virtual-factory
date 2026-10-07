# DDAY-VF-UAT-01-C01 — durable Bottled Water MQTT runtime

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, `NEXT SLICE AUTHORIZED`, or UAT deployment readiness.

This slice adds the durable process. It does **not** deploy UAT.

## Task interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-VF-UAT-01-C01` |
| Authority | SA Issue `#119` + TIME-OWNERSHIP ALIGNMENT 2026-10-07T00:15:46Z + user C01 order |
| Parent | `#118` recon (UAT remains blocked until this launcher is SA-accepted and PlantOS `#92` is accepted) |
| PR | `#101` |
| Recon baseline | `485af9ac24c66f69db29ef308a144cfebe1e054b` |
| Contract | `dday-bw-b1-v2` |
| Scope | Durable CLI + compose artifact. No reservation/warmup. No UAT deploy. |
| Out of scope | PlantOS, TDengine, public MQTT, merge, topology/signal/scenario/KPI change |

## Correction

Issue `#118` Blocker B: no persistent Bottled Water → FR1 scheduler → MQTT process. C01 adds:

```text
virtual-factory dday-bw-runtime --mqtt-host plantos-emqx --mqtt-port 1883 --mqtt-client-id vf-dday-bw-demo-01
```

Compose artifact: `deploy/dday-vf-uat.compose.yml` (not executed here).

SA TIME-OWNERSHIP withdrew source-time floor / STOPPED warmup / reservation. Restart may replay `2026-10-03T00:00:00.000Z`. PlantOS Edge `#92` owns live freshness.

NOT authorized: merge of PR #101, UAT deploy, PlantOS PM handoff.
