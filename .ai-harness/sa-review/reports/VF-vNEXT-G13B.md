# VF-vNEXT-G13B — SH-WTP T106 Standalone Synthetic Logical Runtime — Report

Status: **READY FOR SA REVIEW** (second authorized SH-WTP executable candidate; T106 LogicalOnly).

## Objective

Implement the second already-authorized SH-WTP standalone candidate:
`UNIT-SHW-L1-T106` at `shwtp/line1/l1_t106` as a standalone synthetic LogicalOnly
zero-storage pass-through, under explicit inputs and truthful provenance, without
modifying T108 or projecting PIM relations into runtime.

## Deliverables

| Deliverable | Path |
| --- | --- |
| Task contract | `.ai-harness/tasks/VF-vNEXT-G13B.json` |
| Logical runtime module | `src/virtual_factory/shwtp/logical_runtime.py` (+ `__init__` exports) |
| Invariant tests | `tests/test_vnext_g13b_t106.py` (19 tests) |
| Evidence | `.ai-harness/sa-review/evidence/VF-vNEXT-G13B/01-t106-logical-runtime.md` |
| Baseline manifest | `.ai-harness/regression/vnext_baseline_manifest.json` (G13B gate context + g13b group) |

## Implementation summary

- Explicit config `dt_s > 0`; per-step `inflow_m3_s >= 0`; `output_flow = inflow`;
  time advances exactly `dt_s`. No attenuation/delay/capacity/efficiency/pressure/
  quality/accumulation/filter/backwash state.
- Locked canonical `UNIT-SHW-L1-T106`; exact target `shwtp/line1/l1_t106` only
  (workspace/container/T108/T110 rejected).
- Lifecycle: fresh attempt, deterministic step, reset, detached immutable snapshot,
  isolated attempts.
- Provenance (step + snapshot): `simulation` / `synthetic` / `logical_only`; no site
  or measurement labels.

## Boundaries honored

- T108 runtime (`runtime.py`) unchanged (G13 T108 28 tests still green).
- No T110 runtime; no G4/BoundaryPort/CompositionBinding/coordinator; G12A/B inert; no
  `FLOWS_TO`/`DISCHARGES_TO`/`CONNECTED_TO` conversion; no T106 -> T108 wiring.
- Admission authority preserved (COMPLETE / CANDIDATE_SCOPED / T106 ALLOWED / T110
  blocked / NOT_AUTHORIZED).

## Regression evidence

- New G13B tests: **19 passed**.
- G13 T108 tests: **28 passed** (unchanged).
- Full suite: **2140 passed**.
- Complete canonical vNext baseline: **PASS** (see below).
- Compile / static / changed-files / preflight: **PASS**.

## Non-objectives honored

No filtration physics/quality/backwash; no T106->T108 projection; no T110; no
BoundaryPort/G4/coordinator/federation; no Workspace-level run; no PIM/legacy/global
engine change; no G14.
