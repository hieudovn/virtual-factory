# VF-vNEXT-G5 · Evidence 01 — Repo-first discovery + scope

## Authorization
GitHub Issue #50 (`VF-vNEXT-G5 — Migrate TIPA Workspace / ASSY Federation onto
G1–G4`). Required base `ae0a86e4ad8add77c731fbd597534f24a2f7b575` (accepted G4
final head). Branch `feature/vf-vnext-g5` created from that base. Model Flash.

## Repo-first facts confirmed (unchanged, reused)
- `AssyLineRuntime` (`src/virtual_factory/assembly/line_runtime.py`) is the
  authoritative ASSY runtime: it owns WIP/conveyor/quality/genealogy/time truth.
  Simulation time advances ONLY via `execute_dwell()` (+= actual_dwell =
  max(nominal, max_remaining)) and `index_line()` (+= index_movement_duration_s).
- `AssyDemoComposition` (`assembly/demo_composition.py`) creates six isolated
  `AssyLineRuntime` contexts (deepcopy config + per-sub-line ordinal seed +
  scenario quality normalize); it is demo presentation composition, not plant
  synchronization truth.
- `sub_line_identity.py` supplies canonical TIPA/ASSY/ASSY-SL01..06 deployment
  metadata (plant_id=TIPA, line=ASSY, exactly six sub-lines, hydraulic/thermal
  variants) — reused only as the source of canonical sub-line ids.
- G1 `workspace` provides immutable `StructuralPath`/`Workspace`/`ScopeMode`
  structural identity (path `TIPA/ASSY/ASSY-SLxx`).
- G4 `composition` provides `Coordinator`/`ExecutableParticipant`/empty-graph
  seams with fail-closed exact-boundary + identity revalidation rules
  (C01/C02/C03 preserved).
- Canonical demo config: `configs/plants/tipa_assy_demo.yaml`.

## Design decisions (conservative; recorded)
- No modification of `assembly/`, `workspace/`, `composition/`, or any other
  existing module. All G5 production code is a NEW additive package
  `src/virtual_factory/federation/` + one new test file.
- Adapter advancement replicates the ASSY regression-oracle driver order
  (`execute_dwell()` then `index_line()` when `READY_TO_INDEX`), using existing
  public runtime operations ONLY. It never fabricates fractional dwell/index.
- Supported coordination boundaries are NATURAL ASSY boundaries the wrapped
  runtime lands on EXACTLY (fast config: each 10s dwell lands on 10s multiples;
  real demo config: first dwell lands exactly on 120s). Unreachable targets fail
  closed via the existing G4 coordinator (no new synchronization policy).
- G1 `StructuralPath` is the runtime structural identity; TIPA demo identity is
  deployment metadata only (structural ≠ PIM canonical identity; no PIM
  fabrication).

## Changed files (scope)
New: `.ai-harness/tasks/VF-vNEXT-G5.json`,
`src/virtual_factory/federation/{__init__,tipa_workspace,assy_participant,
assy_host}.py`, `tests/test_federation_tipa_assy.py`, plus G5 evidence/report/
CURRENT. No file outside the G5 allowlist was modified.
