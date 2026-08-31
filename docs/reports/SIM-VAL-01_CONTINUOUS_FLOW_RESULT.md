# SIM-VAL-01 — Continuous Flow Result Report

> **Gate**: SIM-VAL-01  
> **Baseline SHA**: `4204d4f`  
> **Mode**: Phase B — bounded upstream replenishment driver

## Feed Implementation
`DEMO/TEST FEED DRIVER ONLY`

| Field | Value |
|-------|-------|
| Driver file | `tools/run_assy_continuous_validation.py` |
| Production semantic change | NONE |
| Second simulation engine | NO |
| SSO2 target inventory | 10 |
| SSO2 low watermark | 3 |
| RSO2 target buffer | 6 |

Policy: when remaining SSO2 queue < 3, produce `10 - remaining` new SSO2 via public `runtime.produce_sso2_wip()`. RSO2 topped up to 6 via `runtime.produce_rso2_wip()` (in addition to existing on-demand orchestration). SSO2 enters ASSY only through `introduce_to_assy()`. RSO2 consumed only through AP04 JOIN semantics.

## Run Configuration
| Field | Value |
|-------|-------|
| Sub-line | ASSY-SL01 |
| Scenario | HAPPY_PATH |
| Steps | 80 |
| Continuous feed | ON |

## Final Counters

| Metric | Value |
|--------|-------|
| Simulation time | 9600 s |
| Motors created | **76** |
| Motors released | **69** |
| WIPs on line (steady) | 12 |
| Active quality holds | 0 |
| Genealogy joins | 76 |
| SSO2 buffer | 0 (consumed) |
| RSO2 buffer | 5 |
| Starvation | **NONE** |

Target met: ≥40 cycles AND ≥10 released motors (achieved 80 cycles, 69 released).

## Genealogy Proof (first 3)
```
MTR-0001 ← SSO2-0001 + RSO2-0001 @ AP04 t=480s
MTR-0002 ← SSO2-0002 + RSO2-0002 @ AP04 t=600s
MTR-0003 ← SSO2-0003 + RSO2-0003 @ AP04 t=720s
```

## WIP Lifecycle Proof (MTR-0001)
```
Parents: SSO2-0001 + RSO2-0001  (JOIN @ AP04)
Path:    AP05 → AP06 → AP07 → AP08 → AP09 → AP10 → AP11 → RELEASE
```

## Integrity Checks

| Check | Result |
|-------|--------|
| Every introduced SSO2 traceable | ✅ 76 SSO2 parents consumed by 76 joins |
| Every consumed RSO2 maps to one AP04 JOIN | ✅ 76 RSO2 parents, 76 joins (1:1) |
| Each MTR child has correct parents | ✅ `[SSO2-nnnn, RSO2-nnnn]` |
| Released ≤ created | ✅ 69 ≤ 76 |
| HAPPY_PATH quality holds | ✅ 0 |
| Anomalies | NONE |

## Motion Contract (validated)
- `positions[]` sole physical occupancy truth — ✅
- Forward-adjacent same-WIP transitions animate — ✅
- AP04 identity boundary direct-settles (no fake same-ID) — ✅
- Final visual location equals new snapshot — ✅
- No reverse motion — ✅ (I07-C01)
- No duplicate WIPs — ✅
- No animation backlog under AUTO — ✅

## No Exception Routing
LINE OUT / LINE IN / REWORK remain conceptual/inactive. No off-line active WIP, no repair route, no rework, no scrap.
