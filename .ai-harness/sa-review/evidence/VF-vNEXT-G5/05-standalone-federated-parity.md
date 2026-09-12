# VF-vNEXT-G5 · Evidence 05 — Standalone vs federated semantic parity (Issue #50 D)

Two representative parity proofs, both built so the ONLY difference between the
two arms is the federation harness (adapter + G4 coordinator) — the config,
seed and public runtime calls are identical. Canonical domain-state projection
(positions incl. PRE-ASSY/AP01..AP11 literals, WIP lifecycle/position, motor
count, RSO2 buffer, AP04 genealogy with both parents, quality status per WIP,
dwell number, released set, simulation time, event-type trace sequence) must be
equal.

## 1. Fast-config single sub-line (bare runtime standalone vs federated)
- `test_representative_release_scenario_parity`: 16 natural cycles to a
  RELEASED motor. Standalone reaches 160.0 s and releases `MTR-0001`; the
  federated arm runs one coordinator window to the same exact boundary (160.0 s)
  → completed, identical released set, identical canonical state.
- `test_mid_line_join_parity`: 7 natural cycles through the AP04 JOIN
  (genealogy record with both parents, motor_count == 1) → identical canonical
  state.

## 2. Real demo-config six sub-lines (host federated vs standalone replica)
- `test_real_config_six_subline_replica_parity`: the host federates all six
  REAL-config runtimes through one shared NATURAL boundary (first dwell lands
  exactly at 120.0 s for every sub-line → window completed). For each of the six
  sub-lines, a fresh standalone replica (deep-copied isolated config, same
  ordinal seed, demo-equivalent upstream seeding) advanced one natural cycle
  yields an IDENTICAL canonical state to the federated runtime.

## Domain semantics covered (unchanged; ASSY oracle also green — evidence 07)
Literal conveyor positions PRE-ASSY..AP11, SSO2 production/queue + introduction
before PRE-ASSY, RSO2 production + AP04 JOIN consumption, AP04 genealogy with
both parents, AP06 retest-in-place / AP08 reinspect / AP11 final QC scenarios,
`failed_final`, RELEASED / LINE_OUT GOOD-or-REJECT semantics, quality/checklist/
measurement evidence, deterministic timestamps/idempotency — all preserved
because `AssyLineRuntime` was never rewritten and its regression oracle stays
green (354 passed). `FINISHED` is never reinterpreted as a conveyor position.
