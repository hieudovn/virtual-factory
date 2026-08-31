# SIM-VAL-01 — Baseline Run Report

> **Gate**: SIM-VAL-01  
> **Baseline SHA**: `4204d4f`  
> **Mode**: Phase A — deterministic batch validation, existing code unchanged

## Configuration
| Field | Value |
|-------|-------|
| Sub-line | ASSY-SL01 |
| Scenario | HAPPY_PATH |
| Steps executed | 60 |
| Continuous feed | OFF (baseline) |
| Runner | `tools/run_assy_continuous_validation.py` |

## Finite-Feed Result

| Metric | Value |
|--------|-------|
| Simulation time reached | 7200 s |
| Motors created | **7** |
| Motors released | **7** |
| WIPs on line at end | 0 |
| Active quality holds | 0 |
| Genealogy joins | 7 |
| SSO2 buffer at end | 0 |
| RSO2 buffer at end | 0 |

## Starvation

| Field | Value |
|-------|-------|
| **Starvation step** | **17** |
| Released before starvation | 7 |

## Root Cause

`AssyDemoComposition.initialize()` seeds each context with exactly **7 SSO2** and **7 RSO2** WIPs. `introduce_next_sso2()` is called after each successful index and pops from the finite `sso2_ids` list. Once the 7 SSO2 are consumed (7 motors created + released), the list is empty, `introduce_next_sso2()` becomes a no-op, and the line empties and stops.

RSO2 does NOT starve in baseline: `step_context()` produces RSO2 on-demand when AP04 is occupied and the RSO2 buffer is empty.

## Conclusion

Baseline finite feed **cannot sustain** the required target window (40+ cycles / 10+ released). Phase B (bounded replenishment driver) is required.
